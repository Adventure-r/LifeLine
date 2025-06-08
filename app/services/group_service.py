"""
Group management service
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.crud import group_crud, user_crud, invite_token_crud
from app.database.models import User, Group, UserRole
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService


class GroupService:
    """
    Service for group management operations
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    async def create_group(
        self, 
        db: AsyncSession, 
        name: str, 
        leader_id: UUID, 
        description: Optional[str] = None
    ) -> Optional[Group]:
        """
        Create a new group
        
        Args:
            db: Database session
            name: Group name
            leader_id: ID of group leader
            description: Optional group description
            
        Returns:
            Group: Created group or None if failed
        """
        try:
            # Check if user can create group
            leader = await user_crud.get_by_id(db, leader_id)
            if not leader:
                logger.error(f"Leader not found: {leader_id}")
                return None
            
            # Create group
            group = await group_crud.create_group(db, name, leader_id, description)
            
            # Update leader role and assign to group
            await user_crud.update(
                db, 
                leader_id, 
                role=UserRole.GROUP_LEADER,
                group_id=group.id
            )
            
            logger.info(f"Group '{name}' created by user {leader.full_name}")
            return group
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return None
    
    async def add_member_to_group(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        group_id: UUID,
        notify_leader: bool = True
    ) -> bool:
        """
        Add member to group
        
        Args:
            db: Database session
            user_id: User ID to add
            group_id: Group ID
            notify_leader: Whether to notify group leader
            
        Returns:
            bool: Success status
        """
        try:
            # Get user and group
            user = await user_crud.get_by_id(db, user_id)
            group = await group_crud.get_by_id(db, group_id)
            
            if not user or not group:
                return False
            
            # Check if user is already in a group
            if user.group_id:
                logger.warning(f"User {user.full_name} is already in group {user.group_id}")
                return False
            
            # Add user to group
            await user_crud.update(db, user_id, group_id=group_id)
            
            # Notify group leader if requested
            if notify_leader:
                await self._notify_leader_about_new_member(db, user, group)
            
            logger.info(f"User {user.full_name} added to group {group.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding member to group: {e}")
            return False
    
    async def remove_member_from_group(
        self, 
        db: AsyncSession, 
        user_id: UUID,
        notify_user: bool = True
    ) -> bool:
        """
        Remove member from group
        
        Args:
            db: Database session
            user_id: User ID to remove
            notify_user: Whether to notify the user
            
        Returns:
            bool: Success status
        """
        try:
            user = await user_crud.get_by_id(db, user_id)
            if not user or not user.group_id:
                return False
            
            group_name = user.group.name if user.group else "группы"
            
            # Remove user from group and reset role
            await user_crud.update(
                db, 
                user_id, 
                group_id=None, 
                role=UserRole.MEMBER
            )
            
            # Notify user if requested
            if notify_user:
                await self.notification_service.send_immediate_notification(
                    user.telegram_id,
                    "⚠️ Исключение из группы",
                    f"Вы были исключены из группы «{group_name}»."
                )
            
            logger.info(f"User {user.full_name} removed from group {group_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing member from group: {e}")
            return False
    
    async def promote_to_assistant(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        promoted_by_id: UUID
    ) -> bool:
        """
        Promote user to assistant role
        
        Args:
            db: Database session
            user_id: User ID to promote
            promoted_by_id: ID of user doing the promotion
            
        Returns:
            bool: Success status
        """
        try:
            user = await user_crud.get_by_id(db, user_id)
            promoter = await user_crud.get_by_id(db, promoted_by_id)
            
            if not user or not promoter:
                return False
            
            # Check permissions
            if promoter.role != UserRole.GROUP_LEADER:
                logger.warning(f"User {promoter.full_name} tried to promote without permissions")
                return False
            
            # Check if users are in same group
            if user.group_id != promoter.group_id:
                logger.warning(f"User {user.full_name} not in same group as promoter")
                return False
            
            # Promote user
            await user_crud.update_role(db, user_id, UserRole.ASSISTANT)
            
            # Notify user
            await self.notification_service.send_immediate_notification(
                user.telegram_id,
                "🤝 Назначение помощником",
                f"Вы назначены помощником старосты в группе «{user.group.name}»!"
            )
            
            logger.info(f"User {user.full_name} promoted to assistant by {promoter.full_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error promoting to assistant: {e}")
            return False
    
    async def demote_from_assistant(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        demoted_by_id: UUID
    ) -> bool:
        """
        Demote user from assistant role
        
        Args:
            db: Database session
            user_id: User ID to demote
            demoted_by_id: ID of user doing the demotion
            
        Returns:
            bool: Success status
        """
        try:
            user = await user_crud.get_by_id(db, user_id)
            demoter = await user_crud.get_by_id(db, demoted_by_id)
            
            if not user or not demoter:
                return False
            
            # Check permissions
            if demoter.role != UserRole.GROUP_LEADER:
                return False
            
            # Check if users are in same group
            if user.group_id != demoter.group_id:
                return False
            
            # Demote user
            await user_crud.update_role(db, user_id, UserRole.MEMBER)
            
            # Notify user
            await self.notification_service.send_immediate_notification(
                user.telegram_id,
                "📝 Снятие с должности",
                f"Вы больше не являетесь помощником старосты в группе «{user.group.name}»."
            )
            
            logger.info(f"User {user.full_name} demoted from assistant by {demoter.full_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error demoting from assistant: {e}")
            return False
    
    async def get_group_statistics(self, db: AsyncSession, group_id: UUID) -> Dict[str, Any]:
        """
        Get group statistics
        
        Args:
            db: Database session
            group_id: Group ID
            
        Returns:
            Dict: Group statistics
        """
        try:
            group = await group_crud.get_with_members(db, group_id)
            if not group:
                return {}
            
            members = group.members
            
            stats = {
                'total_members': len(members),
                'leaders': len([m for m in members if m.role == UserRole.GROUP_LEADER]),
                'assistants': len([m for m in members if m.role == UserRole.ASSISTANT]),
                'regular_members': len([m for m in members if m.role == UserRole.MEMBER]),
                'active_members': len([m for m in members if m.is_active]),
                'created_date': group.created_at,
                'leader_name': group.leader.full_name if group.leader else "Неизвестно"
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting group statistics: {e}")
            return {}
    
    async def generate_invite_link(
        self, 
        db: AsyncSession, 
        group_id: UUID, 
        created_by_id: UUID,
        hours_valid: int = 24,
        max_uses: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate invite link for group
        
        Args:
            db: Database session
            group_id: Group ID
            created_by_id: ID of user creating invite
            hours_valid: Hours the invite is valid
            max_uses: Maximum number of uses (None = unlimited)
            
        Returns:
            str: Invite token or None if failed
        """
        try:
            from datetime import datetime, timedelta
            
            # Generate token
            token = AuthService.generate_invite_token()
            expires_at = datetime.now() + timedelta(hours=hours_valid)
            
            # Create invite in database
            invite = await invite_token_crud.create_invite(
                db, group_id, created_by_id, token, expires_at, max_uses
            )
            
            logger.info(f"Invite token created for group {group_id} by user {created_by_id}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating invite link: {e}")
            return None
    
    async def use_invite_token(
        self, 
        db: AsyncSession, 
        token: str, 
        user_id: UUID
    ) -> Optional[Group]:
        """
        Use invite token to join group
        
        Args:
            db: Database session
            token: Invite token
            user_id: User ID
            
        Returns:
            Group: Group joined or None if failed
        """
        try:
            # Get and validate token
            invite = await invite_token_crud.get_by_token(db, token)
            if not invite or not AuthService.is_token_valid(invite):
                return None
            
            # Add user to group
            success = await self.add_member_to_group(db, user_id, invite.group_id)
            if not success:
                return None
            
            # Use the token (increment counter)
            await invite_token_crud.use_token(db, token)
            
            # Get group info
            group = await group_crud.get_by_id(db, invite.group_id)
            
            logger.info(f"User {user_id} joined group {group.name} via invite token")
            return group
            
        except Exception as e:
            logger.error(f"Error using invite token: {e}")
            return None
    
    async def _notify_leader_about_new_member(
        self, 
        db: AsyncSession, 
        user: User, 
        group: Group
    ) -> None:
        """
        Notify group leader about new member
        
        Args:
            db: Database session
            user: New member
            group: Group
        """
        try:
            leader = await user_crud.get_by_id(db, group.leader_id)
            if leader and leader.notifications_enabled:
                await self.notification_service.send_immediate_notification(
                    leader.telegram_id,
                    "👥 Новый участник",
                    f"Пользователь {user.full_name} присоединился к группе «{group.name}»."
                )
        except Exception as e:
            logger.error(f"Error notifying leader about new member: {e}")
    
    async def cleanup_expired_invites(self, db: AsyncSession) -> int:
        """
        Clean up expired invite tokens
        
        Args:
            db: Database session
            
        Returns:
            int: Number of cleaned up tokens
        """
        try:
            count = await invite_token_crud.cleanup_expired(db)
            if count > 0:
                logger.info(f"Cleaned up {count} expired invite tokens")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired invites: {e}")
            return 0
    
    async def get_group_members_with_roles(
        self, 
        db: AsyncSession, 
        group_id: UUID
    ) -> Dict[str, List[User]]:
        """
        Get group members grouped by roles
        
        Args:
            db: Database session
            group_id: Group ID
            
        Returns:
            Dict: Members grouped by roles
        """
        try:
            members = await user_crud.get_users_by_group(db, group_id)
            
            grouped = {
                'leaders': [m for m in members if m.role == UserRole.GROUP_LEADER],
                'assistants': [m for m in members if m.role == UserRole.ASSISTANT],
                'members': [m for m in members if m.role == UserRole.MEMBER]
            }
            
            return grouped
            
        except Exception as e:
            logger.error(f"Error getting group members with roles: {e}")
            return {'leaders': [], 'assistants': [], 'members': []}

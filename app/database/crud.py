"""
CRUD operations for database models
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID
from sqlalchemy import select, delete, update, and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from loguru import logger

from app.database.models import (
    User, Group, Event, Topic, Queue, QueueEntry, 
    InviteToken, Notification, UserEventView, 
    UserRole, EventType, NotificationType,
    user_topics
)


class BaseCRUD:
    """Base CRUD class with common operations"""
    
    def __init__(self, model):
        self.model = model
    
    async def create(self, db: AsyncSession, **kwargs) -> Any:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[Any]:
        """Get record by ID"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def update(self, db: AsyncSession, id: UUID, **kwargs) -> Optional[Any]:
        """Update record by ID"""
        await db.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await db.commit()
        return await self.get_by_id(db, id)
    
    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        """Delete record by ID"""
        result = await db.execute(delete(self.model).where(self.model.id == id))
        await db.commit()
        return result.rowcount > 0


class UserCRUD(BaseCRUD):
    """CRUD operations for User model"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        result = await db.execute(
            select(User)
            .options(selectinload(User.group))
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, db: AsyncSession, telegram_id: int, full_name: str, 
                         username: Optional[str] = None, group_id: Optional[UUID] = None) -> User:
        """Create a new user"""
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            group_id=group_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def get_users_by_group(self, db: AsyncSession, group_id: UUID) -> List[User]:
        """Get all users in a group"""
        result = await db.execute(
            select(User)
            .where(User.group_id == group_id)
            .order_by(User.role.desc(), User.full_name)
        )
        return result.scalars().all()
    
    async def update_role(self, db: AsyncSession, user_id: UUID, role: UserRole) -> Optional[User]:
        """Update user role"""
        await db.execute(
            update(User).where(User.id == user_id).values(role=role)
        )
        await db.commit()
        return await self.get_by_id(db, user_id)
    
    async def get_admins(self, db: AsyncSession) -> List[User]:
        """Get all admin users"""
        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        return result.scalars().all()
    
    async def update_notification_settings(self, db: AsyncSession, user_id: UUID, 
                                         settings: Dict[str, Any]) -> Optional[User]:
        """Update user notification settings"""
        await db.execute(
            update(User).where(User.id == user_id).values(**settings)
        )
        await db.commit()
        return await self.get_by_id(db, user_id)


class GroupCRUD(BaseCRUD):
    """CRUD operations for Group model"""
    
    def __init__(self):
        super().__init__(Group)
    
    async def create_group(self, db: AsyncSession, name: str, leader_id: UUID, 
                          description: Optional[str] = None) -> Group:
        """Create a new group"""
        group = Group(
            name=name,
            leader_id=leader_id,
            description=description
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group
    
    async def get_with_members(self, db: AsyncSession, group_id: UUID) -> Optional[Group]:
        """Get group with members"""
        result = await db.execute(
            select(Group)
            .options(
                selectinload(Group.members),
                selectinload(Group.leader)
            )
            .where(Group.id == group_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_groups(self, db: AsyncSession, user_id: UUID) -> List[Group]:
        """Get all groups where user is leader or assistant"""
        result = await db.execute(
            select(Group)
            .join(User, User.group_id == Group.id)
            .where(
                and_(
                    User.id == user_id,
                    or_(
                        Group.leader_id == user_id,
                        User.role == UserRole.ASSISTANT
                    )
                )
            )
        )
        return result.scalars().all()
    
    async def get_all_active(self, db: AsyncSession) -> List[Group]:
        """Get all active groups"""
        result = await db.execute(
            select(Group)
            .options(selectinload(Group.leader))
            .where(Group.is_active == True)
            .order_by(Group.name)
        )
        return result.scalars().all()


class EventCRUD(BaseCRUD):
    """CRUD operations for Event model"""
    
    def __init__(self):
        super().__init__(Event)
    
    async def create_event(self, db: AsyncSession, **kwargs) -> Event:
        """Create a new event"""
        event = Event(**kwargs)
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event
    
    async def get_group_events(self, db: AsyncSession, group_id: UUID, 
                              limit: int = 20, offset: int = 0) -> List[Event]:
        """Get events for a group with pagination"""
        result = await db.execute(
            select(Event)
            .options(selectinload(Event.creator))
            .where(and_(Event.group_id == group_id, Event.is_active == True))
            .order_by(desc(Event.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_upcoming_events(self, db: AsyncSession, group_id: UUID) -> List[Event]:
        """Get upcoming events for a group"""
        today = date.today()
        result = await db.execute(
            select(Event)
            .where(
                and_(
                    Event.group_id == group_id,
                    Event.is_active == True,
                    or_(
                        Event.event_date >= today,
                        Event.deadline_end >= datetime.now()
                    )
                )
            )
            .order_by(asc(Event.event_date), asc(Event.deadline_end))
        )
        return result.scalars().all()
    
    async def mark_as_viewed(self, db: AsyncSession, user_id: UUID, event_id: UUID) -> None:
        """Mark event as viewed by user"""
        # Check if already viewed
        existing = await db.execute(
            select(UserEventView).where(
                and_(
                    UserEventView.user_id == user_id,
                    UserEventView.event_id == event_id
                )
            )
        )
        
        if not existing.scalar_one_or_none():
            view = UserEventView(user_id=user_id, event_id=event_id)
            db.add(view)
            await db.commit()
    
    async def get_events_by_date(self, db: AsyncSession, group_id: UUID, 
                                event_date: date) -> List[Event]:
        """Get events for a specific date"""
        result = await db.execute(
            select(Event)
            .where(
                and_(
                    Event.group_id == group_id,
                    Event.event_date == event_date,
                    Event.is_active == True
                )
            )
            .order_by(Event.start_time)
        )
        return result.scalars().all()
    
    async def get_deadlines_approaching(self, db: AsyncSession, days: int) -> List[Event]:
        """Get deadlines approaching in specified days"""
        target_date = datetime.now().replace(hour=23, minute=59, second=59)
        from datetime import timedelta
        target_date += timedelta(days=days)
        
        result = await db.execute(
            select(Event)
            .options(selectinload(Event.group))
            .where(
                and_(
                    Event.event_type == EventType.DEADLINE,
                    Event.deadline_end <= target_date,
                    Event.deadline_end > datetime.now(),
                    Event.is_active == True
                )
            )
        )
        return result.scalars().all()


class TopicCRUD(BaseCRUD):
    """CRUD operations for Topic model"""
    
    def __init__(self):
        super().__init__(Topic)
    
    async def get_group_topics(self, db: AsyncSession, group_id: UUID) -> List[Topic]:
        """Get all topics for a group"""
        result = await db.execute(
            select(Topic)
            .options(selectinload(Topic.selected_by))
            .where(and_(Topic.group_id == group_id, Topic.is_active == True))
            .order_by(Topic.title)
        )
        return result.scalars().all()
    
    async def select_topic(self, db: AsyncSession, user_id: UUID, topic_id: UUID) -> bool:
        """Select a topic for a user"""
        try:
            # Check if topic exists and has available slots
            topic = await self.get_by_id(db, topic_id)
            if not topic:
                return False
            
            # Count current selections
            result = await db.execute(
                select(func.count()).select_from(user_topics)
                .where(user_topics.c.topic_id == topic_id)
            )
            current_selections = result.scalar() or 0
            
            if current_selections >= topic.max_selections:
                return False
            
            # Add selection
            await db.execute(
                user_topics.insert().values(
                    user_id=user_id,
                    topic_id=topic_id,
                    approved=not topic.requires_approval
                )
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error selecting topic: {e}")
            await db.rollback()
            return False
    
    async def approve_selection(self, db: AsyncSession, user_id: UUID, topic_id: UUID) -> bool:
        """Approve user's topic selection"""
        try:
            await db.execute(
                update(user_topics)
                .where(
                    and_(
                        user_topics.c.user_id == user_id,
                        user_topics.c.topic_id == topic_id
                    )
                )
                .values(approved=True)
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error approving topic selection: {e}")
            await db.rollback()
            return False


class QueueCRUD(BaseCRUD):
    """CRUD operations for Queue model"""
    
    def __init__(self):
        super().__init__(Queue)
    
    async def get_group_queues(self, db: AsyncSession, group_id: UUID) -> List[Queue]:
        """Get all queues for a group"""
        result = await db.execute(
            select(Queue)
            .options(selectinload(Queue.entries).selectinload(QueueEntry.user))
            .where(and_(Queue.group_id == group_id, Queue.is_active == True))
            .order_by(desc(Queue.created_at))
        )
        return result.scalars().all()
    
    async def join_queue(self, db: AsyncSession, queue_id: UUID, user_id: UUID, 
                        notes: Optional[str] = None) -> Optional[QueueEntry]:
        """Join a queue"""
        try:
            # Check if user is already in queue
            existing = await db.execute(
                select(QueueEntry).where(
                    and_(
                        QueueEntry.queue_id == queue_id,
                        QueueEntry.user_id == user_id
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                return None  # Already in queue
            
            # Get next position
            result = await db.execute(
                select(func.max(QueueEntry.position))
                .where(QueueEntry.queue_id == queue_id)
            )
            max_position = result.scalar() or 0
            
            # Create entry
            entry = QueueEntry(
                queue_id=queue_id,
                user_id=user_id,
                position=max_position + 1,
                notes=notes
            )
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return entry
        except Exception as e:
            logger.error(f"Error joining queue: {e}")
            await db.rollback()
            return None
    
    async def leave_queue(self, db: AsyncSession, queue_id: UUID, user_id: UUID) -> bool:
        """Leave a queue and reorder positions"""
        try:
            # Get user's entry
            result = await db.execute(
                select(QueueEntry).where(
                    and_(
                        QueueEntry.queue_id == queue_id,
                        QueueEntry.user_id == user_id
                    )
                )
            )
            entry = result.scalar_one_or_none()
            
            if not entry:
                return False
            
            position = entry.position
            
            # Delete entry
            await db.execute(
                delete(QueueEntry).where(QueueEntry.id == entry.id)
            )
            
            # Reorder remaining entries
            await db.execute(
                update(QueueEntry)
                .where(
                    and_(
                        QueueEntry.queue_id == queue_id,
                        QueueEntry.position > position
                    )
                )
                .values(position=QueueEntry.position - 1)
            )
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error leaving queue: {e}")
            await db.rollback()
            return False


class InviteTokenCRUD(BaseCRUD):
    """CRUD operations for InviteToken model"""
    
    def __init__(self):
        super().__init__(InviteToken)
    
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[InviteToken]:
        """Get invite token by token string"""
        result = await db.execute(
            select(InviteToken)
            .options(selectinload(InviteToken.group))
            .where(InviteToken.token == token)
        )
        return result.scalar_one_or_none()
    
    async def create_invite(self, db: AsyncSession, group_id: UUID, created_by: UUID,
                           token: str, expires_at: datetime, max_uses: Optional[int] = None) -> InviteToken:
        """Create a new invite token"""
        invite = InviteToken(
            token=token,
            group_id=group_id,
            created_by=created_by,
            expires_at=expires_at,
            max_uses=max_uses
        )
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        return invite
    
    async def use_token(self, db: AsyncSession, token: str) -> Optional[InviteToken]:
        """Use an invite token (increment uses_count)"""
        invite = await self.get_by_token(db, token)
        if not invite or not invite.is_active:
            return None
        
        if invite.expires_at < datetime.now():
            return None
        
        if invite.max_uses and invite.uses_count >= invite.max_uses:
            return None
        
        invite.uses_count += 1
        await db.commit()
        return invite
    
    async def cleanup_expired(self, db: AsyncSession) -> int:
        """Clean up expired tokens"""
        result = await db.execute(
            delete(InviteToken).where(InviteToken.expires_at < datetime.now())
        )
        await db.commit()
        return result.rowcount


class NotificationCRUD(BaseCRUD):
    """CRUD operations for Notification model"""
    
    def __init__(self):
        super().__init__(Notification)
    
    async def create_notification(self, db: AsyncSession, user_id: UUID, 
                                 notification_type: NotificationType, title: str, 
                                 message: str, scheduled_for: Optional[datetime] = None,
                                 **related_ids) -> Notification:
        """Create a new notification"""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            scheduled_for=scheduled_for,
            **related_ids
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification
    
    async def get_pending_notifications(self, db: AsyncSession) -> List[Notification]:
        """Get notifications that need to be sent"""
        result = await db.execute(
            select(Notification)
            .options(selectinload(Notification.user))
            .where(
                and_(
                    Notification.is_sent == False,
                    or_(
                        Notification.scheduled_for <= datetime.now(),
                        Notification.scheduled_for.is_(None)
                    )
                )
            )
        )
        return result.scalars().all()
    
    async def mark_as_sent(self, db: AsyncSession, notification_id: UUID) -> None:
        """Mark notification as sent"""
        await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_sent=True, sent_at=datetime.now())
        )
        await db.commit()


# Create CRUD instances
user_crud = UserCRUD()
group_crud = GroupCRUD()
event_crud = EventCRUD()
topic_crud = TopicCRUD()
queue_crud = QueueCRUD()
invite_token_crud = InviteTokenCRUD()
notification_crud = NotificationCRUD()

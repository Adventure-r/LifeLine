"""
Event management service
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.crud import event_crud, user_crud, notification_crud
from app.database.models import Event, User, EventType, NotificationType
from app.services.notification_service import NotificationService


class EventService:
    """
    Service for event management operations
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    async def create_event(
        self,
        db: AsyncSession,
        creator_id: UUID,
        title: str,
        event_type: EventType,
        description: Optional[str] = None,
        event_date: Optional[date] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        deadline_end: Optional[datetime] = None,
        is_important: bool = False,
        media_file_id: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> Optional[Event]:
        """
        Create a new event
        
        Args:
            db: Database session
            creator_id: ID of event creator
            title: Event title
            event_type: Type of event
            description: Event description
            event_date: Date of event
            start_time: Start time
            end_time: End time
            deadline_end: Deadline end datetime
            is_important: Whether event is important
            media_file_id: Telegram file ID for media
            media_type: Type of media (photo, video, document)
            
        Returns:
            Event: Created event or None if failed
        """
        try:
            # Get creator
            creator = await user_crud.get_by_id(db, creator_id)
            if not creator or not creator.group_id:
                logger.error(f"Creator not found or not in group: {creator_id}")
                return None
            
            # Create event
            event_data = {
                'title': title,
                'description': description,
                'event_type': event_type,
                'group_id': creator.group_id,
                'creator_id': creator_id,
                'event_date': event_date,
                'start_time': start_time,
                'end_time': end_time,
                'deadline_end': deadline_end,
                'is_important': is_important,
                'has_media': bool(media_file_id),
                'media_file_id': media_file_id,
                'media_type': media_type
            }
            
            event = await event_crud.create_event(db, **event_data)
            
            # Send notifications to group members
            await self._notify_group_about_new_event(db, event, creator)
            
            # Schedule deadline reminders if it's a deadline event
            if event_type == EventType.DEADLINE and deadline_end:
                await self._schedule_deadline_reminders(db, event)
            
            logger.info(f"Event '{title}' created by user {creator.full_name}")
            return event
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None
    
    async def update_event(
        self,
        db: AsyncSession,
        event_id: UUID,
        user_id: UUID,
        **update_data
    ) -> Optional[Event]:
        """
        Update an existing event
        
        Args:
            db: Database session
            event_id: Event ID to update
            user_id: ID of user making update
            **update_data: Fields to update
            
        Returns:
            Event: Updated event or None if failed
        """
        try:
            # Get event and user
            event = await event_crud.get_by_id(db, event_id)
            user = await user_crud.get_by_id(db, user_id)
            
            if not event or not user:
                return None
            
            # Check permissions (creator or group leader)
            if event.creator_id != user_id and user.role.value != 'group_leader':
                logger.warning(f"User {user.full_name} tried to update event without permissions")
                return None
            
            # Update event
            updated_event = await event_crud.update(db, event_id, **update_data)
            
            # Notify group if significant changes
            if self._is_significant_update(update_data):
                await self._notify_group_about_event_update(db, updated_event, user)
            
            logger.info(f"Event '{event.title}' updated by user {user.full_name}")
            return updated_event
            
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return None
    
    async def delete_event(
        self,
        db: AsyncSession,
        event_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete an event
        
        Args:
            db: Database session
            event_id: Event ID to delete
            user_id: ID of user making deletion
            
        Returns:
            bool: Success status
        """
        try:
            # Get event and user
            event = await event_crud.get_by_id(db, event_id)
            user = await user_crud.get_by_id(db, user_id)
            
            if not event or not user:
                return False
            
            # Check permissions
            if event.creator_id != user_id and user.role.value != 'group_leader':
                return False
            
            # Soft delete (set is_active to False)
            await event_crud.update(db, event_id, is_active=False)
            
            logger.info(f"Event '{event.title}' deleted by user {user.full_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False
    
    async def mark_event_as_viewed(
        self,
        db: AsyncSession,
        user_id: UUID,
        event_id: UUID
    ) -> bool:
        """
        Mark event as viewed by user
        
        Args:
            db: Database session
            user_id: User ID
            event_id: Event ID
            
        Returns:
            bool: Success status
        """
        try:
            await event_crud.mark_as_viewed(db, user_id, event_id)
            return True
        except Exception as e:
            logger.error(f"Error marking event as viewed: {e}")
            return False
    
    async def get_user_events(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        filter_type: Optional[str] = None
    ) -> List[Event]:
        """
        Get events for user's group with optional filtering
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of events
            offset: Offset for pagination
            filter_type: Filter type (upcoming, important, viewed)
            
        Returns:
            List[Event]: List of events
        """
        try:
            user = await user_crud.get_by_id(db, user_id)
            if not user or not user.group_id:
                return []
            
            if filter_type == 'upcoming':
                return await event_crud.get_upcoming_events(db, user.group_id)
            else:
                return await event_crud.get_group_events(db, user.group_id, limit, offset)
                
        except Exception as e:
            logger.error(f"Error getting user events: {e}")
            return []
    
    async def get_events_by_date(
        self,
        db: AsyncSession,
        group_id: UUID,
        target_date: date
    ) -> List[Event]:
        """
        Get events for specific date
        
        Args:
            db: Database session
            group_id: Group ID
            target_date: Target date
            
        Returns:
            List[Event]: Events for the date
        """
        try:
            return await event_crud.get_events_by_date(db, group_id, target_date)
        except Exception as e:
            logger.error(f"Error getting events by date: {e}")
            return []
    
    async def get_approaching_deadlines(
        self,
        db: AsyncSession,
        days_ahead: int = 7
    ) -> List[Event]:
        """
        Get deadlines approaching in specified days
        
        Args:
            db: Database session
            days_ahead: Number of days to look ahead
            
        Returns:
            List[Event]: Approaching deadlines
        """
        try:
            return await event_crud.get_deadlines_approaching(db, days_ahead)
        except Exception as e:
            logger.error(f"Error getting approaching deadlines: {e}")
            return []
    
    async def toggle_event_importance(
        self,
        db: AsyncSession,
        event_id: UUID,
        user_id: UUID
    ) -> Optional[bool]:
        """
        Toggle event importance status
        
        Args:
            db: Database session
            event_id: Event ID
            user_id: User ID making the change
            
        Returns:
            bool: New importance status or None if failed
        """
        try:
            event = await event_crud.get_by_id(db, event_id)
            user = await user_crud.get_by_id(db, user_id)
            
            if not event or not user:
                return None
            
            # Check permissions
            if event.creator_id != user_id and user.role.value not in ['group_leader', 'assistant']:
                return None
            
            new_importance = not event.is_important
            await event_crud.update(db, event_id, is_important=new_importance)
            
            logger.info(f"Event '{event.title}' importance toggled to {new_importance}")
            return new_importance
            
        except Exception as e:
            logger.error(f"Error toggling event importance: {e}")
            return None
    
    async def _notify_group_about_new_event(
        self,
        db: AsyncSession,
        event: Event,
        creator: User
    ) -> None:
        """
        Send notifications about new event to group members
        
        Args:
            db: Database session
            event: Created event
            creator: Event creator
        """
        try:
            members = await user_crud.get_users_by_group(db, event.group_id)
            
            for member in members:
                if member.id != creator.id and member.event_notifications:
                    title = "📅 Новое событие"
                    if event.is_important:
                        title = "⭐ Важное событие"
                    
                    message = f"В группе создано новое событие:\n\n{event.title}"
                    
                    if event.event_date:
                        message += f"\n📅 {event.event_date.strftime('%d.%m.%Y')}"
                    
                    if event.start_time:
                        message += f" в {event.start_time}"
                    
                    if event.deadline_end:
                        message += f"\n⏰ Дедлайн: {event.deadline_end.strftime('%d.%m.%Y %H:%M')}"
                    
                    await self.notification_service.send_immediate_notification(
                        member.telegram_id, title, message
                    )
                    
        except Exception as e:
            logger.error(f"Error notifying group about new event: {e}")
    
    async def _notify_group_about_event_update(
        self,
        db: AsyncSession,
        event: Event,
        updater: User
    ) -> None:
        """
        Send notifications about event update to group members
        
        Args:
            db: Database session
            event: Updated event
            updater: User who updated the event
        """
        try:
            members = await user_crud.get_users_by_group(db, event.group_id)
            
            for member in members:
                if member.id != updater.id and member.event_notifications:
                    await self.notification_service.send_immediate_notification(
                        member.telegram_id,
                        "📝 Событие обновлено",
                        f"Событие «{event.title}» было изменено."
                    )
                    
        except Exception as e:
            logger.error(f"Error notifying group about event update: {e}")
    
    async def _schedule_deadline_reminders(
        self,
        db: AsyncSession,
        event: Event
    ) -> None:
        """
        Schedule deadline reminder notifications
        
        Args:
            db: Database session
            event: Deadline event
        """
        try:
            if not event.deadline_end:
                return
            
            # Get group members
            members = await user_crud.get_users_by_group(db, event.group_id)
            
            # Schedule reminders for different time periods
            reminder_days = [7, 3, 1]  # Days before deadline
            
            for days in reminder_days:
                reminder_time = event.deadline_end - timedelta(days=days)
                
                # Skip if reminder time is in the past
                if reminder_time <= datetime.now():
                    continue
                
                # Create reminder notifications for all group members
                for member in members:
                    if member.deadline_reminders:
                        await notification_crud.create_notification(
                            db,
                            user_id=member.id,
                            notification_type=NotificationType.DEADLINE_REMINDER,
                            title=f"⏰ Напоминание о дедлайне",
                            message=f"До дедлайна «{event.title}» осталось {days} дн.",
                            scheduled_for=reminder_time,
                            related_event_id=event.id
                        )
                        
        except Exception as e:
            logger.error(f"Error scheduling deadline reminders: {e}")
    
    def _is_significant_update(self, update_data: Dict[str, Any]) -> bool:
        """
        Check if update is significant enough to notify users
        
        Args:
            update_data: Update data
            
        Returns:
            bool: True if significant
        """
        significant_fields = {
            'title', 'event_date', 'start_time', 'end_time', 
            'deadline_end', 'is_important'
        }
        
        return any(field in update_data for field in significant_fields)
    
    async def get_event_statistics(
        self,
        db: AsyncSession,
        group_id: UUID
    ) -> Dict[str, Any]:
        """
        Get event statistics for group
        
        Args:
            db: Database session
            group_id: Group ID
            
        Returns:
            Dict: Event statistics
        """
        try:
            events = await event_crud.get_group_events(db, group_id, limit=1000)
            
            stats = {
                'total_events': len(events),
                'upcoming_events': len([e for e in events if e.event_date and e.event_date >= date.today()]),
                'important_events': len([e for e in events if e.is_important]),
                'events_with_media': len([e for e in events if e.has_media]),
                'events_by_type': {}
            }
            
            # Count events by type
            for event_type in EventType:
                count = len([e for e in events if e.event_type == event_type])
                stats['events_by_type'][event_type.value] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting event statistics: {e}")
            return {}

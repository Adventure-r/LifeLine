"""
Notification service for sending messages
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from aiogram import Bot

from app.database.crud import notification_crud, user_crud
from app.database.models import NotificationType, User
from app.config import settings


class NotificationService:
    """
    Service for handling notifications and messaging
    """
    
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
    
    async def send_immediate_notification(
        self,
        telegram_id: int,
        title: str,
        message: str,
        parse_mode: Optional[str] = "HTML"
    ) -> bool:
        """
        Send immediate notification to user
        
        Args:
            telegram_id: Telegram user ID
            title: Notification title
            message: Notification message
            parse_mode: Message parse mode
            
        Returns:
            bool: Success status
        """
        try:
            if not self.bot:
                logger.error("Bot instance not available for sending notifications")
                return False
            
            # Format message with title
            full_message = f"<b>{title}</b>\n\n{message}"
            
            # Send message
            await self.bot.send_message(
                chat_id=telegram_id,
                text=full_message,
                parse_mode=parse_mode
            )
            
            logger.info(f"Immediate notification sent to {telegram_id}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending immediate notification to {telegram_id}: {e}")
            return False
    
    async def create_scheduled_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        scheduled_for: datetime,
        related_event_id: Optional[UUID] = None,
        related_topic_id: Optional[UUID] = None,
        related_queue_id: Optional[UUID] = None
    ) -> bool:
        """
        Create a scheduled notification
        
        Args:
            db: Database session
            user_id: User ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            scheduled_for: When to send notification
            related_event_id: Related event ID
            related_topic_id: Related topic ID
            related_queue_id: Related queue ID
            
        Returns:
            bool: Success status
        """
        try:
            await notification_crud.create_notification(
                db,
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                scheduled_for=scheduled_for,
                related_event_id=related_event_id,
                related_topic_id=related_topic_id,
                related_queue_id=related_queue_id
            )
            
            logger.info(f"Scheduled notification created for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating scheduled notification: {e}")
            return False
    
    async def send_pending_notifications(self, db: AsyncSession) -> int:
        """
        Send all pending scheduled notifications
        
        Args:
            db: Database session
            
        Returns:
            int: Number of notifications sent
        """
        try:
            if not self.bot:
                logger.error("Bot instance not available for sending notifications")
                return 0
            
            # Get pending notifications
            notifications = await notification_crud.get_pending_notifications(db)
            sent_count = 0
            
            for notification in notifications:
                try:
                    # Check if user has notifications enabled
                    if not notification.user.notifications_enabled:
                        await notification_crud.mark_as_sent(db, notification.id)
                        continue
                    
                    # Send notification
                    success = await self.send_immediate_notification(
                        notification.user.telegram_id,
                        notification.title,
                        notification.message
                    )
                    
                    if success:
                        await notification_crud.mark_as_sent(db, notification.id)
                        sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Error sending notification {notification.id}: {e}")
                    continue
            
            if sent_count > 0:
                logger.info(f"Sent {sent_count} pending notifications")
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending pending notifications: {e}")
            return 0
    
    async def send_bulk_notification(
        self,
        db: AsyncSession,
        user_ids: List[UUID],
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.GROUP_INVITE
    ) -> int:
        """
        Send notification to multiple users
        
        Args:
            db: Database session
            user_ids: List of user IDs
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            
        Returns:
            int: Number of notifications sent
        """
        try:
            sent_count = 0
            
            for user_id in user_ids:
                user = await user_crud.get_by_id(db, user_id)
                if user and user.notifications_enabled:
                    success = await self.send_immediate_notification(
                        user.telegram_id,
                        title,
                        message
                    )
                    if success:
                        sent_count += 1
            
            logger.info(f"Sent bulk notification to {sent_count} users")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
            return 0
    
    async def send_group_notification(
        self,
        db: AsyncSession,
        group_id: UUID,
        title: str,
        message: str,
        exclude_user_id: Optional[UUID] = None,
        notification_type: NotificationType = NotificationType.EVENT_CREATED
    ) -> int:
        """
        Send notification to all group members
        
        Args:
            db: Database session
            group_id: Group ID
            title: Notification title
            message: Notification message
            exclude_user_id: User ID to exclude from notification
            notification_type: Type of notification
            
        Returns:
            int: Number of notifications sent
        """
        try:
            # Get group members
            members = await user_crud.get_users_by_group(db, group_id)
            sent_count = 0
            
            for member in members:
                # Skip excluded user
                if exclude_user_id and member.id == exclude_user_id:
                    continue
                
                # Check if user has notifications enabled
                if not member.notifications_enabled:
                    continue
                
                # Check specific notification type settings
                if notification_type == NotificationType.EVENT_CREATED and not member.event_notifications:
                    continue
                
                if notification_type == NotificationType.DEADLINE_REMINDER and not member.deadline_reminders:
                    continue
                
                # Send notification
                success = await self.send_immediate_notification(
                    member.telegram_id,
                    title,
                    message
                )
                
                if success:
                    sent_count += 1
            
            logger.info(f"Sent group notification to {sent_count} members")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending group notification: {e}")
            return 0
    
    async def send_deadline_reminders(self, db: AsyncSession) -> int:
        """
        Send deadline reminder notifications
        
        Args:
            db: Database session
            
        Returns:
            int: Number of reminders sent
        """
        try:
            from app.database.crud import event_crud
            from datetime import date, timedelta
            
            sent_count = 0
            
            # Check for deadlines in the next few days
            for days in settings.DEADLINE_REMINDER_DAYS:
                deadlines = await event_crud.get_deadlines_approaching(db, days)
                
                for event in deadlines:
                    # Get group members
                    members = await user_crud.get_users_by_group(db, event.group_id)
                    
                    for member in members:
                        if member.deadline_reminders and member.notifications_enabled:
                            title = f"⏰ Напоминание о дедлайне"
                            message = f"До дедлайна «{event.title}» осталось {days} дн.\n\n"
                            
                            if event.deadline_end:
                                message += f"Окончание: {event.deadline_end.strftime('%d.%m.%Y %H:%M')}"
                            
                            success = await self.send_immediate_notification(
                                member.telegram_id,
                                title,
                                message
                            )
                            
                            if success:
                                sent_count += 1
            
            if sent_count > 0:
                logger.info(f"Sent {sent_count} deadline reminders")
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending deadline reminders: {e}")
            return 0
    
    async def send_daily_digest(self, db: AsyncSession, user_id: UUID) -> bool:
        """
        Send daily digest to user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            bool: Success status
        """
        try:
            user = await user_crud.get_by_id(db, user_id)
            if not user or not user.notifications_enabled or not user.group_id:
                return False
            
            from app.database.crud import event_crud
            from datetime import date, timedelta
            
            # Get today's and tomorrow's events
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            today_events = await event_crud.get_events_by_date(db, user.group_id, today)
            tomorrow_events = await event_crud.get_events_by_date(db, user.group_id, tomorrow)
            
            if not today_events and not tomorrow_events:
                return False  # No events to report
            
            # Build digest message
            digest = "📅 Ваша сводка на сегодня:\n\n"
            
            if today_events:
                digest += f"🔥 Сегодня ({today.strftime('%d.%m')}):\n"
                for event in today_events:
                    digest += f"• {event.title}"
                    if event.start_time:
                        digest += f" в {event.start_time}"
                    if event.is_important:
                        digest += " ⭐"
                    digest += "\n"
                digest += "\n"
            
            if tomorrow_events:
                digest += f"📅 Завтра ({tomorrow.strftime('%d.%m')}):\n"
                for event in tomorrow_events:
                    digest += f"• {event.title}"
                    if event.start_time:
                        digest += f" в {event.start_time}"
                    if event.is_important:
                        digest += " ⭐"
                    digest += "\n"
            
            # Send digest
            success = await self.send_immediate_notification(
                user.telegram_id,
                "📊 Ежедневная сводка",
                digest
            )
            
            if success:
                logger.info(f"Daily digest sent to user {user.full_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily digest: {e}")
            return False
    
    async def notify_about_topic_selection(
        self,
        db: AsyncSession,
        topic_id: UUID,
        user_id: UUID,
        group_leader_id: UUID
    ) -> bool:
        """
        Notify group leader about topic selection
        
        Args:
            db: Database session
            topic_id: Topic ID
            user_id: User who selected topic
            group_leader_id: Group leader ID
            
        Returns:
            bool: Success status
        """
        try:
            from app.database.crud import topic_crud
            
            user = await user_crud.get_by_id(db, user_id)
            leader = await user_crud.get_by_id(db, group_leader_id)
            topic = await topic_crud.get_by_id(db, topic_id)
            
            if not user or not leader or not topic:
                return False
            
            if not leader.notifications_enabled:
                return False
            
            title = "📚 Выбор темы"
            message = f"Участник {user.full_name} выбрал тему:\n\n«{topic.title}»"
            
            if topic.requires_approval:
                message += "\n\n⏳ Требуется ваше одобрение."
            
            return await self.send_immediate_notification(
                leader.telegram_id,
                title,
                message
            )
            
        except Exception as e:
            logger.error(f"Error notifying about topic selection: {e}")
            return False
    
    async def notify_about_queue_join(
        self,
        db: AsyncSession,
        queue_id: UUID,
        user_id: UUID,
        position: int
    ) -> bool:
        """
        Notify user about successful queue join
        
        Args:
            db: Database session
            queue_id: Queue ID
            user_id: User ID
            position: Position in queue
            
        Returns:
            bool: Success status
        """
        try:
            from app.database.crud import queue_crud
            
            user = await user_crud.get_by_id(db, user_id)
            queue = await queue_crud.get_by_id(db, queue_id)
            
            if not user or not queue:
                return False
            
            title = "🏃‍♂️ Очередь"
            message = f"Вы присоединились к очереди:\n\n«{queue.title}»\n\n📍 Ваша позиция: {position}"
            
            if queue.queue_date:
                message += f"\n📅 Дата: {queue.queue_date.strftime('%d.%m.%Y')}"
            
            if queue.start_time:
                message += f"\n🕐 Время: {queue.start_time}"
            
            return await self.send_immediate_notification(
                user.telegram_id,
                title,
                message
            )
            
        except Exception as e:
            logger.error(f"Error notifying about queue join: {e}")
            return False
    
    def set_bot_instance(self, bot: Bot) -> None:
        """
        Set bot instance for sending messages
        
        Args:
            bot: Aiogram Bot instance
        """
        self.bot = bot

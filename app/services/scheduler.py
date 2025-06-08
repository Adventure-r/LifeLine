"""
Notification scheduler service
"""

import asyncio
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from aiogram import Bot

from app.config import settings
from app.database.database import get_db
from app.services.notification_service import NotificationService


class NotificationScheduler:
    """
    Scheduler for automated notifications and reminders
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone_obj)
        self.notification_service = NotificationService(bot)
        self.is_running = False
    
    async def start(self) -> None:
        """
        Start the notification scheduler
        """
        try:
            if self.is_running:
                logger.warning("Scheduler is already running")
                return
            
            # Add scheduled jobs
            await self._add_scheduled_jobs()
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Notification scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Error starting notification scheduler: {e}")
            raise
    
    async def stop(self) -> None:
        """
        Stop the notification scheduler
        """
        try:
            if not self.is_running:
                return
            
            self.scheduler.shutdown()
            self.is_running = False
            
            logger.info("Notification scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping notification scheduler: {e}")
    
    async def _add_scheduled_jobs(self) -> None:
        """
        Add all scheduled jobs to the scheduler
        """
        try:
            # Send pending notifications every 5 minutes
            self.scheduler.add_job(
                self._send_pending_notifications,
                trigger=IntervalTrigger(minutes=5),
                id='send_pending_notifications',
                name='Send Pending Notifications',
                max_instances=1,
                coalesce=True
            )
            
            # Check for deadline reminders every hour
            self.scheduler.add_job(
                self._check_deadline_reminders,
                trigger=IntervalTrigger(hours=1),
                id='check_deadline_reminders',
                name='Check Deadline Reminders',
                max_instances=1,
                coalesce=True
            )
            
            # Send daily digests at 9:00 AM
            self.scheduler.add_job(
                self._send_daily_digests,
                trigger=CronTrigger(hour=9, minute=0),
                id='send_daily_digests',
                name='Send Daily Digests',
                max_instances=1,
                coalesce=True
            )
            
            # Clean up expired invite tokens daily at 2:00 AM
            self.scheduler.add_job(
                self._cleanup_expired_invites,
                trigger=CronTrigger(hour=2, minute=0),
                id='cleanup_expired_invites',
                name='Cleanup Expired Invites',
                max_instances=1,
                coalesce=True
            )
            
            # System health check every 30 minutes
            self.scheduler.add_job(
                self._system_health_check,
                trigger=IntervalTrigger(minutes=30),
                id='system_health_check',
                name='System Health Check',
                max_instances=1,
                coalesce=True
            )
            
            logger.info("Scheduled jobs added successfully")
            
        except Exception as e:
            logger.error(f"Error adding scheduled jobs: {e}")
            raise
    
    async def _send_pending_notifications(self) -> None:
        """
        Send all pending scheduled notifications
        """
        try:
            async for db in get_db():
                sent_count = await self.notification_service.send_pending_notifications(db)
                
                if sent_count > 0:
                    logger.info(f"Sent {sent_count} pending notifications")
                
                break  # Exit after first iteration
                
        except Exception as e:
            logger.error(f"Error in send_pending_notifications job: {e}")
    
    async def _check_deadline_reminders(self) -> None:
        """
        Check and send deadline reminder notifications
        """
        try:
            async for db in get_db():
                sent_count = await self.notification_service.send_deadline_reminders(db)
                
                if sent_count > 0:
                    logger.info(f"Sent {sent_count} deadline reminders")
                
                break  # Exit after first iteration
                
        except Exception as e:
            logger.error(f"Error in check_deadline_reminders job: {e}")
    
    async def _send_daily_digests(self) -> None:
        """
        Send daily digest notifications to users
        """
        try:
            async for db in get_db():
                from app.database.crud import user_crud
                
                # Get all active users
                users = await user_crud.get_all_users(db)
                sent_count = 0
                
                for user in users:
                    if user.is_active and user.notifications_enabled and user.group_id:
                        # Check if user wants digests at this time
                        if user.notification_time:
                            notification_time = datetime.strptime(user.notification_time, "%H:%M").time()
                            current_time = datetime.now().time()
                            
                            # Send digest within 1 hour window
                            if abs((datetime.combine(datetime.today(), current_time) - 
                                   datetime.combine(datetime.today(), notification_time)).total_seconds()) <= 3600:
                                
                                success = await self.notification_service.send_daily_digest(db, user.id)
                                if success:
                                    sent_count += 1
                
                if sent_count > 0:
                    logger.info(f"Sent {sent_count} daily digests")
                
                break  # Exit after first iteration
                
        except Exception as e:
            logger.error(f"Error in send_daily_digests job: {e}")
    
    async def _cleanup_expired_invites(self) -> None:
        """
        Clean up expired invite tokens
        """
        try:
            async for db in get_db():
                from app.services.group_service import GroupService
                
                group_service = GroupService()
                cleaned_count = await group_service.cleanup_expired_invites(db)
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired invite tokens")
                
                break  # Exit after first iteration
                
        except Exception as e:
            logger.error(f"Error in cleanup_expired_invites job: {e}")
    
    async def _system_health_check(self) -> None:
        """
        Perform system health check
        """
        try:
            # Check database connection
            async for db in get_db():
                from app.database.crud import user_crud
                
                # Simple query to test database
                await user_crud.get_all_users(db)
                
                logger.debug("System health check passed")
                break  # Exit after first iteration
                
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            
            # Optionally notify administrators about system issues
            # This could be implemented to send alerts to admin users
    
    async def schedule_one_time_notification(
        self,
        user_telegram_id: int,
        title: str,
        message: str,
        send_at: datetime,
        job_id: Optional[str] = None
    ) -> str:
        """
        Schedule a one-time notification
        
        Args:
            user_telegram_id: Telegram user ID
            title: Notification title
            message: Notification message
            send_at: When to send the notification
            job_id: Optional job ID (auto-generated if not provided)
            
        Returns:
            str: Job ID
        """
        try:
            if not job_id:
                job_id = f"notification_{user_telegram_id}_{int(send_at.timestamp())}"
            
            self.scheduler.add_job(
                self._send_scheduled_notification,
                trigger='date',
                run_date=send_at,
                args=[user_telegram_id, title, message],
                id=job_id,
                name=f'Scheduled Notification for {user_telegram_id}',
                max_instances=1
            )
            
            logger.info(f"Scheduled one-time notification for {send_at}: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling one-time notification: {e}")
            raise
    
    async def cancel_scheduled_notification(self, job_id: str) -> bool:
        """
        Cancel a scheduled notification
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            bool: Success status
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.remove()
                logger.info(f"Cancelled scheduled notification: {job_id}")
                return True
            else:
                logger.warning(f"Scheduled notification not found: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling scheduled notification: {e}")
            return False
    
    async def _send_scheduled_notification(
        self,
        user_telegram_id: int,
        title: str,
        message: str
    ) -> None:
        """
        Send a scheduled notification
        
        Args:
            user_telegram_id: Telegram user ID
            title: Notification title
            message: Notification message
        """
        try:
            await self.notification_service.send_immediate_notification(
                user_telegram_id, title, message
            )
            logger.info(f"Sent scheduled notification to {user_telegram_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error sending scheduled notification: {e}")
    
    def get_scheduler_status(self) -> dict:
        """
        Get scheduler status and job information
        
        Returns:
            dict: Scheduler status information
        """
        try:
            jobs = self.scheduler.get_jobs()
            
            status = {
                'running': self.is_running,
                'total_jobs': len(jobs),
                'job_details': []
            }
            
            for job in jobs:
                job_info = {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                status['job_details'].append(job_info)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {'running': False, 'error': str(e)}
    
    async def reschedule_job(
        self,
        job_id: str,
        trigger=None,
        **trigger_args
    ) -> bool:
        """
        Reschedule an existing job
        
        Args:
            job_id: Job ID to reschedule
            trigger: New trigger type
            **trigger_args: Trigger arguments
            
        Returns:
            bool: Success status
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.reschedule_job(job_id, trigger=trigger, **trigger_args)
                logger.info(f"Rescheduled job: {job_id}")
                return True
            else:
                logger.warning(f"Job not found for rescheduling: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error rescheduling job: {e}")
            return False

"""
Logging middleware
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger
import time


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware to log user actions and performance metrics
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Main middleware function
        """
        start_time = time.time()
        
        # Extract information from event
        user_id = None
        event_type = type(event).__name__
        event_data = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
            event_data = {
                'text': event.text[:100] if event.text else None,
                'chat_id': event.chat.id,
                'message_id': event.message_id
            }
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            event_data = {
                'data': event.data,
                'chat_id': event.message.chat.id if event.message else None,
                'message_id': event.message.message_id if event.message else None
            }
        
        # Get user info from middleware data
        user = data.get('user')
        user_info = {}
        if user:
            user_info = {
                'user_id': str(user.id),
                'telegram_id': user.telegram_id,
                'full_name': user.full_name,
                'role': user.role.value,
                'group_id': str(user.group_id) if user.group_id else None
            }
        
        # Log incoming event
        logger.info(
            f"Incoming {event_type}",
            extra={
                'event_type': event_type,
                'telegram_user_id': user_id,
                'user_info': user_info,
                'event_data': event_data
            }
        )
        
        try:
            # Process the event
            result = await handler(event, data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log successful processing
            logger.info(
                f"Processed {event_type} successfully",
                extra={
                    'event_type': event_type,
                    'telegram_user_id': user_id,
                    'processing_time': round(processing_time, 3),
                    'status': 'success'
                }
            )
            
            return result
            
        except Exception as e:
            # Calculate processing time for failed requests
            processing_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Error processing {event_type}: {str(e)}",
                extra={
                    'event_type': event_type,
                    'telegram_user_id': user_id,
                    'processing_time': round(processing_time, 3),
                    'status': 'error',
                    'error': str(e),
                    'user_info': user_info,
                    'event_data': event_data
                }
            )
            
            # Re-raise the exception
            raise


class PerformanceMiddleware(BaseMiddleware):
    """
    Middleware specifically for performance monitoring
    """
    
    def __init__(self, slow_threshold: float = 1.0):
        """
        Initialize performance middleware
        
        Args:
            slow_threshold: Threshold in seconds to consider request as slow
        """
        self.slow_threshold = slow_threshold
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Main middleware function
        """
        start_time = time.time()
        
        try:
            result = await handler(event, data)
            processing_time = time.time() - start_time
            
            # Log slow requests
            if processing_time > self.slow_threshold:
                event_type = type(event).__name__
                user_id = getattr(event.from_user, 'id', None) if hasattr(event, 'from_user') else None
                
                logger.warning(
                    f"Slow request detected: {event_type}",
                    extra={
                        'event_type': event_type,
                        'telegram_user_id': user_id,
                        'processing_time': round(processing_time, 3),
                        'threshold': self.slow_threshold
                    }
                )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Log failed requests with timing
            event_type = type(event).__name__
            user_id = getattr(event.from_user, 'id', None) if hasattr(event, 'from_user') else None
            
            logger.error(
                f"Failed request: {event_type}",
                extra={
                    'event_type': event_type,
                    'telegram_user_id': user_id,
                    'processing_time': round(processing_time, 3),
                    'error': str(e)
                }
            )
            
            raise

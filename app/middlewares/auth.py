"""
Authentication middleware
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger

from app.database.database import get_db
from app.database.crud import user_crud


class AuthMiddleware(BaseMiddleware):
    """
    Middleware to check user authentication and add user object to handler data
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
        # Extract user ID from event
        telegram_id = None
        
        if isinstance(event, (Message, CallbackQuery)):
            telegram_id = event.from_user.id
        
        if telegram_id:
            try:
                # Get user from database
                async for db in get_db():
                    user = await user_crud.get_by_telegram_id(db, telegram_id)
                    
                    # Add user to handler data
                    data['user'] = user
                    break
                    
            except Exception as e:
                logger.error(f"Error in auth middleware: {e}")
                data['user'] = None
        else:
            data['user'] = None
        
        # Continue processing
        return await handler(event, data)

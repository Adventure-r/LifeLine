"""
Main entry point for the Telegram bot
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
import redis.asyncio as redis

from app.config import settings
from app.database.database import init_db
from app.middlewares.auth import AuthMiddleware
from app.middlewares.logging import LoggingMiddleware
from app.services.scheduler import NotificationScheduler

# Import all handlers
from app.handlers import (
    common,
    auth,
    admin,
    groups,
    events,
    calendar,
    topics,
    queues,
    notifications
)


async def main() -> None:
    """
    Main function to start the bot
    """
    # Configure logging
    logger.add(
        "logs/bot.log",
        rotation="1 day",
        retention="30 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    logger.info("Starting Telegram bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize storage for FSM (fallback to memory if Redis unavailable)
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        # Test Redis connection
        await redis_client.ping()
        storage = RedisStorage(redis_client)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Redis not available ({e}), using memory storage for FSM")
        storage = MemoryStorage()
        redis_client = None
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=storage)
    
    # Register middlewares
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    
    # Register handlers
    dp.include_router(common.router)
    dp.include_router(auth.router)
    dp.include_router(admin.router)
    dp.include_router(groups.router)
    dp.include_router(events.router)
    dp.include_router(calendar.router)
    dp.include_router(topics.router)
    dp.include_router(queues.router)
    dp.include_router(notifications.router)
    
    # Initialize scheduler
    scheduler = NotificationScheduler(bot)
    await scheduler.start()
    logger.info("Notification scheduler started")
    
    try:
        # Start polling
        logger.info("Bot started successfully")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
    finally:
        await scheduler.stop()
        await bot.session.close()
        if redis_client:
            await redis_client.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

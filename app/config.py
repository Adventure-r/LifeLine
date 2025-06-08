"""
Configuration settings for the bot
"""

import os
from typing import List
from pydantic import BaseSettings, validator
from datetime import timezone
import pytz


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Bot configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/telegram_bot")
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Admin codes for admin authentication
    ADMIN_CODES: str = os.getenv("ADMIN_CODES", "admin123,super456,master789")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Timezone
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-token-generation")
    
    # Invitation token settings
    INVITE_TOKEN_EXPIRE_HOURS: int = int(os.getenv("INVITE_TOKEN_EXPIRE_HOURS", "24"))
    
    # Notification settings
    NOTIFICATION_CHECK_INTERVAL: int = int(os.getenv("NOTIFICATION_CHECK_INTERVAL", "3600"))  # seconds
    DEADLINE_REMINDER_DAYS: List[int] = [7, 3, 1]  # Days before deadline to send reminders
    
    @validator('ADMIN_CODES')
    def parse_admin_codes(cls, v):
        """Parse admin codes from comma-separated string"""
        return [code.strip() for code in v.split(',') if code.strip()]
    
    @property
    def timezone_obj(self):
        """Get timezone object"""
        return pytz.timezone(self.TIMEZONE)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

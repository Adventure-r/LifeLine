"""
Database connection and session management
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from loguru import logger

from app.config import settings
from app.database.models import Base

# Create async engine with proper asyncpg URL
database_url = settings.DATABASE_URL
if not database_url.startswith("postgresql+asyncpg://"):
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

# Handle SSL parameters for asyncpg
if "sslmode=require" in database_url:
    database_url = database_url.replace("?sslmode=require", "?ssl=require")
    database_url = database_url.replace("&sslmode=require", "&ssl=require")

engine = create_async_engine(
    database_url,
    poolclass=NullPool,
    echo=False,  # Set to True for SQL query logging
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)


async def init_db() -> None:
    """
    Initialize database - create all tables
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered
            from app.database import models  # noqa: F401
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """
    Close database connections
    """
    await engine.dispose()
    logger.info("Database connections closed")

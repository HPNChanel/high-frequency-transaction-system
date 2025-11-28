"""Async database session management using SQLAlchemy."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def get_async_engine():
    """Create and return the async database engine.
    
    Uses asyncpg driver for PostgreSQL as specified in requirements.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create and return the async session maker."""
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session.
    
    Yields an async session and ensures proper cleanup after use.
    Use this as a FastAPI dependency for database operations.
    """
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

"""API dependency injection.

Provides FastAPI dependencies for database sessions and other
shared resources used across API endpoints.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session.
    
    This wraps the session management from app.db.session
    for use as a FastAPI dependency.
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async for session in get_async_session():
        yield session


# Type alias for cleaner dependency injection syntax
DBSession = Annotated[AsyncSession, Depends(get_db)]

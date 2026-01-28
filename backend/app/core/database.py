"""
Database Connection Module
==========================

Handles database connection, session management, and initialization.

Author: Manus AI
Date: January 28, 2026
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.models.database import Base

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Enable connection health checks
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_database():
    """
    Initialize database tables.
    
    This should only be used in development.
    In production, use Alembic migrations.
    """
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def get_db_session() -> AsyncSession:
    """
    Dependency function to get database session.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            # Use db here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_context():
    """
    Context manager for database session.
    
    Usage:
        async with get_db_session_context() as db:
            # Use db here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# For use in middleware and services
def get_db_session_factory():
    """
    Factory function that returns a context manager for database sessions.
    
    This is used by the BillingMiddleware.
    """
    return get_db_session_context

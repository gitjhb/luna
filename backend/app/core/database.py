"""
Database Connection Module - with SQLite fallback for development
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Check if we're in mock/development mode
MOCK_MODE = os.getenv("MOCK_DATABASE", "true").lower() == "true"

_engine = None
_session_factory = None


class MockDB:
    """Mock database for development without actual PostgreSQL"""

    def __init__(self):
        self._data = {}

    async def execute(self, query, *args):
        logger.debug(f"MockDB execute: {query[:100]}...")
        return "UPDATE 1"

    async def fetch(self, query, *args):
        logger.debug(f"MockDB fetch: {query[:100]}...")
        return []

    async def fetchrow(self, query, *args):
        logger.debug(f"MockDB fetchrow: {query[:100]}...")
        return None

    async def fetchval(self, query, *args):
        logger.debug(f"MockDB fetchval: {query[:100]}...")
        return 1

    @asynccontextmanager
    async def transaction(self):
        yield


async def init_db():
    """Initialize database connection"""
    global _engine, _session_factory

    if MOCK_MODE:
        logger.info("Using mock database (development mode)")
        return

    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")
        
        # Convert postgres:// to postgresql:// if needed
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        
        # Use SQLite for development
        if "sqlite" in database_url:
            os.makedirs("./data", exist_ok=True)
            _engine = create_async_engine(database_url, echo=False)
        else:
            _engine = create_async_engine(
                database_url,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
            )

        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("Database connection initialized")

    except Exception as e:
        logger.warning(f"Database init failed, using mock: {e}")


async def close_db():
    """Close database connection"""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


@asynccontextmanager
async def get_db() -> AsyncGenerator:
    """
    Get database connection/session.
    Returns mock in development mode.
    """
    if MOCK_MODE or _session_factory is None:
        yield MockDB()
        return

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

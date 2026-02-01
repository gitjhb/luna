"""
Database Connection Module - with SQLite fallback for development
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Check if we're in mock/development mode - default to FALSE now (use SQLite)
MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

_engine = None
_session_factory = None


class MockDBResult:
    """Mock result for SQLAlchemy-style queries"""
    def scalar_one_or_none(self):
        return None
    def scalars(self):
        return self
    def all(self):
        return []
    def first(self):
        return None


class MockDB:
    """Mock database for development without actual PostgreSQL"""

    def __init__(self):
        self._data = {}

    async def execute(self, query, *args):
        try:
            query_str = str(query)[:100]
        except:
            query_str = "query"
        logger.debug(f"MockDB execute: {query_str}...")
        return MockDBResult()

    async def fetch(self, query, *args):
        try:
            query_str = str(query)[:100]
        except:
            query_str = "query"
        logger.debug(f"MockDB fetch: {query_str}...")
        return []

    async def fetchrow(self, query, *args):
        try:
            query_str = str(query)[:100]
        except:
            query_str = "query"
        logger.debug(f"MockDB fetchrow: {query_str}...")
        return None

    async def fetchval(self, query, *args):
        try:
            query_str = str(query)[:100]
        except:
            query_str = "query"
        logger.debug(f"MockDB fetchval: {query_str}...")
        return 1

    def add(self, obj):
        logger.debug(f"MockDB add: {type(obj).__name__}")
        pass

    async def commit(self):
        logger.debug("MockDB commit")
        pass

    async def refresh(self, obj):
        logger.debug(f"MockDB refresh: {type(obj).__name__}")
        pass

    async def rollback(self):
        logger.debug("MockDB rollback")
        pass

    async def close(self):
        logger.debug("MockDB close")
        pass

    @asynccontextmanager
    async def transaction(self):
        yield


async def init_db():
    """Initialize database connection and create tables"""
    global _engine, _session_factory

    if MOCK_MODE:
        logger.info("Using mock database (development mode)")
        return

    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        # Import all model Bases to create all tables
        from app.models.database.chat_models import Base as ChatBase
        from app.models.database.billing_models import Base as BillingBase
        # Import models to register them with Base.metadata
        from app.models.database import intimacy_models, gift_models, payment_models, emotion_models, stats_models, user_settings_models, referral_models

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

        # Create all tables from both model bases
        async with _engine.begin() as conn:
            await conn.run_sync(ChatBase.metadata.create_all)
            await conn.run_sync(BillingBase.metadata.create_all)
        
        logger.info("Database connection initialized and tables created")

    except Exception as e:
        logger.warning(f"Database init failed, using mock: {e}")
        import traceback
        traceback.print_exc()


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
    logger.debug(f"get_db called: MOCK_MODE={MOCK_MODE}, _session_factory={_session_factory}")
    if MOCK_MODE:
        logger.warning("Using MockDB because MOCK_MODE is True")
        yield MockDB()
        return
    if _session_factory is None:
        logger.error("Using MockDB because _session_factory is None - init_db() may not have been called!")
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

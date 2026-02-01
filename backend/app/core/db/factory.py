"""
Database Factory
================

Creates the appropriate database backend based on configuration.

Backends:
- sqlite: SQLite with SQLAlchemy (development)
- supabase: Supabase Postgres + pgvector (production)
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.core.db.base import RepositoryManager

logger = logging.getLogger(__name__)

# Backend selection from environment
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")  # sqlite | supabase


def get_db_backend() -> str:
    """Get current database backend name"""
    return DB_BACKEND


@asynccontextmanager
async def get_repository() -> AsyncGenerator[RepositoryManager, None]:
    """
    Get repository manager for database operations.
    
    Usage:
        async with get_repository() as repo:
            user = await repo.users.get_by_id(user_id)
            await repo.messages.create(...)
    
    The appropriate backend is selected based on DB_BACKEND env var.
    """
    if DB_BACKEND == "supabase":
        # Future: Supabase implementation
        # from app.core.db.supabase_impl import SupabaseRepositoryManager
        # manager = SupabaseRepositoryManager()
        raise NotImplementedError(
            "Supabase backend not yet implemented. "
            "Set DB_BACKEND=sqlite for now."
        )
    else:
        # Default: SQLite
        from app.core.db.sqlite_impl import SQLiteRepositoryManager
        manager = SQLiteRepositoryManager()
    
    try:
        await manager.connect()
        yield manager
    except Exception as e:
        await manager.rollback()
        raise
    finally:
        await manager.close()


async def init_database():
    """
    Initialize database (create tables, indexes, etc.)
    
    Called on application startup.
    """
    logger.info(f"Initializing database with backend: {DB_BACKEND}")
    
    if DB_BACKEND == "supabase":
        # Supabase tables are managed via migrations
        logger.info("Supabase backend - tables managed externally")
        return
    
    # SQLite: Create tables
    from app.core.db.sqlite_impl import init_sqlite
    await init_sqlite()
    logger.info("SQLite database initialized")


async def close_database():
    """
    Close database connections.
    
    Called on application shutdown.
    """
    logger.info(f"Closing database backend: {DB_BACKEND}")
    
    if DB_BACKEND == "sqlite":
        from app.core.db.sqlite_impl import close_sqlite
        await close_sqlite()

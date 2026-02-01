"""
Database Abstraction Layer
==========================

Current: SQLite (development)
Future: Supabase (Postgres + pgvector)

This layer provides a unified interface for database operations,
making it easy to switch between different backends.

Usage:
    from app.core.db import get_repository

    async with get_repository() as repo:
        user = await repo.users.get_by_id(user_id)
        await repo.messages.create(message_data)
"""

from app.core.db.base import (
    BaseRepository,
    UserRepositoryProtocol,
    MessageRepositoryProtocol,
    SessionRepositoryProtocol,
    MemoryRepositoryProtocol,
    VectorRepositoryProtocol,
)
from app.core.db.factory import get_repository, get_db_backend

__all__ = [
    "BaseRepository",
    "UserRepositoryProtocol",
    "MessageRepositoryProtocol", 
    "SessionRepositoryProtocol",
    "MemoryRepositoryProtocol",
    "VectorRepositoryProtocol",
    "get_repository",
    "get_db_backend",
]

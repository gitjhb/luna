"""
SQLite Repository Implementation
================================

Development database using SQLite with SQLAlchemy async.

This implementation follows the repository protocols defined in base.py,
making it easy to swap for Supabase in production.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.orm import selectinload

from app.core.db.base import (
    RepositoryManager,
    UserRepositoryProtocol,
    MessageRepositoryProtocol,
    SessionRepositoryProtocol,
    MemoryRepositoryProtocol,
    VectorRepositoryProtocol,
)

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_session_factory = None


async def init_sqlite():
    """Initialize SQLite database"""
    global _engine, _session_factory
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")
    
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    
    _engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )
    
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Import models and create tables
    from app.models.database.chat_models import Base as ChatBase
    from app.models.database.billing_models import Base as BillingBase
    from app.models.database import (
        intimacy_models, gift_models, payment_models,
        emotion_models, stats_models, user_settings_models,
        referral_models
    )
    
    async with _engine.begin() as conn:
        await conn.run_sync(ChatBase.metadata.create_all)
        await conn.run_sync(BillingBase.metadata.create_all)
    
    logger.info(f"SQLite initialized: {database_url}")


async def close_sqlite():
    """Close SQLite connection"""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("SQLite connection closed")


class SQLiteUserRepository:
    """SQLite implementation of UserRepositoryProtocol"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        from app.models.database.billing_models import User
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return self._to_dict(user) if user else None
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        from app.models.database.billing_models import User
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return self._to_dict(user) if user else None
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.database.billing_models import User
        user = User(**user_data)
        self.session.add(user)
        await self.session.flush()
        return self._to_dict(user)
    
    async def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from app.models.database.billing_models import User
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(**data)
        )
        return await self.get_by_id(user_id)
    
    async def delete(self, user_id: str) -> bool:
        from app.models.database.billing_models import User
        result = await self.session.execute(
            delete(User).where(User.user_id == user_id)
        )
        return result.rowcount > 0
    
    def _to_dict(self, user) -> Dict[str, Any]:
        if not user:
            return None
        return {
            "user_id": user.user_id,
            "email": user.email,
            "name": getattr(user, "name", None),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


class SQLiteMessageRepository:
    """SQLite implementation of MessageRepositoryProtocol"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        from app.models.database.chat_models import ChatMessage
        from uuid import uuid4
        
        message = ChatMessage(
            message_id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            created_at=datetime.utcnow(),
        )
        self.session.add(message)
        await self.session.flush()
        return self._to_dict(message)
    
    async def get_by_session(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        from app.models.database.chat_models import ChatMessage
        
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .offset(offset)
            .limit(limit)
        )
        messages = result.scalars().all()
        return [self._to_dict(m) for m in messages]
    
    async def get_recent(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        from app.models.database.chat_models import ChatMessage
        
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        # Reverse to get chronological order
        return [self._to_dict(m) for m in reversed(messages)]
    
    async def delete_by_session(self, session_id: str) -> int:
        from app.models.database.chat_models import ChatMessage
        
        result = await self.session.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        return result.rowcount
    
    def _to_dict(self, message) -> Dict[str, Any]:
        return {
            "message_id": message.message_id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "tokens_used": message.tokens_used,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }


class SQLiteSessionRepository:
    """SQLite implementation of SessionRepositoryProtocol"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        character_id: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        from app.models.database.chat_models import ChatSession
        from uuid import uuid4
        
        session = ChatSession(
            session_id=str(uuid4()),
            user_id=user_id,
            character_id=character_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(session)
        await self.session.flush()
        return self._to_dict(session)
    
    async def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        from app.models.database.chat_models import ChatSession
        
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        return self._to_dict(session) if session else None
    
    async def get_by_user_and_character(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[Dict[str, Any]]:
        from app.models.database.chat_models import ChatSession
        
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.character_id == character_id)
        )
        session = result.scalar_one_or_none()
        return self._to_dict(session) if session else None
    
    async def update(
        self,
        session_id: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        from app.models.database.chat_models import ChatSession
        
        data["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(ChatSession)
            .where(ChatSession.session_id == session_id)
            .values(**data)
        )
        return await self.get_by_id(session_id)
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        from app.models.database.chat_models import ChatSession
        
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        sessions = result.scalars().all()
        return [self._to_dict(s) for s in sessions]
    
    def _to_dict(self, session) -> Dict[str, Any]:
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "character_id": session.character_id,
            "total_messages": getattr(session, "total_messages", 0),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }


class SQLiteMemoryRepository:
    """SQLite implementation of MemoryRepositoryProtocol"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def store(
        self,
        user_id: str,
        character_id: str,
        content: str,
        memory_type: str = "conversation",
        importance: float = 0.5,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        # For now, use a simple table or JSON file
        # This would be replaced with proper memory model
        from uuid import uuid4
        
        memory = {
            "memory_id": str(uuid4()),
            "user_id": user_id,
            "character_id": character_id,
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # TODO: Implement proper memory storage
        logger.debug(f"Memory stored: {memory['memory_id']}")
        return memory
    
    async def get_by_user_character(
        self,
        user_id: str,
        character_id: str,
        limit: int = 20,
        memory_type: str = None,
    ) -> List[Dict[str, Any]]:
        # TODO: Implement proper memory retrieval
        return []
    
    async def delete(self, memory_id: str) -> bool:
        # TODO: Implement
        return True
    
    async def update_importance(
        self,
        memory_id: str,
        importance: float,
    ) -> bool:
        # TODO: Implement
        return True


class SQLiteVectorRepository:
    """
    SQLite implementation of VectorRepositoryProtocol
    
    Note: SQLite doesn't have native vector support.
    This uses brute-force cosine similarity for development.
    For production, use Supabase with pgvector.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._vectors: Dict[str, Dict] = {}  # In-memory for dev
    
    async def upsert(
        self,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        namespace: str = "default",
    ) -> bool:
        key = f"{namespace}:{vector_id}"
        self._vectors[key] = {
            "id": vector_id,
            "embedding": embedding,
            "metadata": metadata,
            "namespace": namespace,
        }
        return True
    
    async def search(
        self,
        query_embedding: List[float],
        namespace: str = "default",
        top_k: int = 10,
        filter: Dict[str, Any] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Brute-force cosine similarity search"""
        import math
        
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        
        results = []
        for key, data in self._vectors.items():
            if not key.startswith(f"{namespace}:"):
                continue
            
            # Apply filter
            if filter:
                match = all(
                    data["metadata"].get(k) == v
                    for k, v in filter.items()
                )
                if not match:
                    continue
            
            score = cosine_similarity(query_embedding, data["embedding"])
            if score >= min_score:
                results.append({
                    "id": data["id"],
                    "score": score,
                    "metadata": data["metadata"],
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    async def delete(
        self,
        vector_id: str,
        namespace: str = "default",
    ) -> bool:
        key = f"{namespace}:{vector_id}"
        if key in self._vectors:
            del self._vectors[key]
            return True
        return False
    
    async def delete_by_filter(
        self,
        filter: Dict[str, Any],
        namespace: str = "default",
    ) -> int:
        to_delete = []
        for key, data in self._vectors.items():
            if not key.startswith(f"{namespace}:"):
                continue
            match = all(
                data["metadata"].get(k) == v
                for k, v in filter.items()
            )
            if match:
                to_delete.append(key)
        
        for key in to_delete:
            del self._vectors[key]
        
        return len(to_delete)


class SQLiteRepositoryManager(RepositoryManager):
    """SQLite implementation of RepositoryManager"""
    
    def __init__(self):
        self._session: Optional[AsyncSession] = None
        self._users: Optional[SQLiteUserRepository] = None
        self._messages: Optional[SQLiteMessageRepository] = None
        self._sessions: Optional[SQLiteSessionRepository] = None
        self._memories: Optional[SQLiteMemoryRepository] = None
        self._vectors: Optional[SQLiteVectorRepository] = None
    
    async def connect(self):
        """Get a session from the pool"""
        if _session_factory is None:
            await init_sqlite()
        self._session = _session_factory()
    
    @property
    def users(self) -> SQLiteUserRepository:
        if self._users is None:
            self._users = SQLiteUserRepository(self._session)
        return self._users
    
    @property
    def messages(self) -> SQLiteMessageRepository:
        if self._messages is None:
            self._messages = SQLiteMessageRepository(self._session)
        return self._messages
    
    @property
    def sessions(self) -> SQLiteSessionRepository:
        if self._sessions is None:
            self._sessions = SQLiteSessionRepository(self._session)
        return self._sessions
    
    @property
    def memories(self) -> SQLiteMemoryRepository:
        if self._memories is None:
            self._memories = SQLiteMemoryRepository(self._session)
        return self._memories
    
    @property
    def vectors(self) -> SQLiteVectorRepository:
        if self._vectors is None:
            self._vectors = SQLiteVectorRepository(self._session)
        return self._vectors
    
    async def begin_transaction(self):
        """SQLAlchemy auto-begins transactions"""
        pass
    
    async def commit(self):
        if self._session:
            await self._session.commit()
    
    async def rollback(self):
        if self._session:
            await self._session.rollback()
    
    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

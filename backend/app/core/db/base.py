"""
Database Repository Protocols (Abstract Interfaces)
===================================================

These protocols define the interface for database operations.
Implementations can be swapped without changing business logic.

Current implementations:
- SQLiteRepository (development)

Future implementations:
- SupabaseRepository (production with Postgres + pgvector)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol, TypeVar, Generic
from datetime import datetime
from contextlib import asynccontextmanager

T = TypeVar('T')


class BaseRepository(ABC):
    """Base class for all repositories"""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        pass


class UserRepositoryProtocol(Protocol):
    """Protocol for user data operations"""
    
    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        ...
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        ...
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user"""
        ...
    
    async def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user data"""
        ...
    
    async def delete(self, user_id: str) -> bool:
        """Delete user"""
        ...


class MessageRepositoryProtocol(Protocol):
    """Protocol for chat message operations"""
    
    async def create(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create a new message"""
        ...
    
    async def get_by_session(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        ...
    
    async def get_recent(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get most recent messages"""
        ...
    
    async def delete_by_session(self, session_id: str) -> int:
        """Delete all messages in a session, returns count"""
        ...


class SessionRepositoryProtocol(Protocol):
    """Protocol for chat session operations"""
    
    async def create(
        self,
        user_id: str,
        character_id: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create new chat session"""
        ...
    
    async def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        ...
    
    async def get_by_user_and_character(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get existing session for user+character pair"""
        ...
    
    async def update(
        self,
        session_id: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update session data"""
        ...
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List user's sessions"""
        ...


class MemoryRepositoryProtocol(Protocol):
    """Protocol for long-term memory operations"""
    
    async def store(
        self,
        user_id: str,
        character_id: str,
        content: str,
        memory_type: str = "conversation",
        importance: float = 0.5,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Store a memory"""
        ...
    
    async def get_by_user_character(
        self,
        user_id: str,
        character_id: str,
        limit: int = 20,
        memory_type: str = None,
    ) -> List[Dict[str, Any]]:
        """Get memories for user+character"""
        ...
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        ...
    
    async def update_importance(
        self,
        memory_id: str,
        importance: float,
    ) -> bool:
        """Update memory importance score"""
        ...


class VectorRepositoryProtocol(Protocol):
    """
    Protocol for vector/embedding operations
    
    Note: This will use different backends:
    - Development: In-memory or SQLite with manual similarity
    - Production: Supabase pgvector
    """
    
    async def upsert(
        self,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        namespace: str = "default",
    ) -> bool:
        """Insert or update a vector"""
        ...
    
    async def search(
        self,
        query_embedding: List[float],
        namespace: str = "default",
        top_k: int = 10,
        filter: Dict[str, Any] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Returns list of {id, score, metadata}
        """
        ...
    
    async def delete(
        self,
        vector_id: str,
        namespace: str = "default",
    ) -> bool:
        """Delete a vector"""
        ...
    
    async def delete_by_filter(
        self,
        filter: Dict[str, Any],
        namespace: str = "default",
    ) -> int:
        """Delete vectors matching filter, returns count"""
        ...


class RepositoryManager(ABC):
    """
    Unified repository manager providing access to all repositories.
    
    Usage:
        async with get_repository() as repo:
            user = await repo.users.get_by_id(user_id)
            messages = await repo.messages.get_by_session(session_id)
    """
    
    @property
    @abstractmethod
    def users(self) -> UserRepositoryProtocol:
        """User repository"""
        pass
    
    @property
    @abstractmethod
    def messages(self) -> MessageRepositoryProtocol:
        """Message repository"""
        pass
    
    @property
    @abstractmethod
    def sessions(self) -> SessionRepositoryProtocol:
        """Session repository"""
        pass
    
    @property
    @abstractmethod
    def memories(self) -> MemoryRepositoryProtocol:
        """Memory repository"""
        pass
    
    @property
    @abstractmethod
    def vectors(self) -> VectorRepositoryProtocol:
        """Vector/embedding repository"""
        pass
    
    @abstractmethod
    async def begin_transaction(self):
        """Begin a transaction"""
        pass
    
    @abstractmethod
    async def commit(self):
        """Commit current transaction"""
        pass
    
    @abstractmethod
    async def rollback(self):
        """Rollback current transaction"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close connection"""
        pass

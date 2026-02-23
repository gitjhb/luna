"""
Memory Database Service
=======================

Connects the memory_system_v2 to the SQLAlchemy database.
This service provides the db_service interface that MemoryManager expects.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.database.memory_v2_models import (
    SemanticMemory,
    EpisodicMemory,
    MemoryExtractionLog,
)

logger = logging.getLogger(__name__)


class MemoryDBService:
    """
    Database service for the memory system.
    
    Provides CRUD operations for semantic and episodic memories
    using the SQLAlchemy async session.
    """
    
    async def get_semantic_memory(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get semantic memory for a user-character pair."""
        try:
            async with get_db() as session:
                result = await session.execute(
                    select(SemanticMemory).where(
                        and_(
                            SemanticMemory.user_id == user_id,
                            SemanticMemory.character_id == character_id,
                        )
                    )
                )
                record = result.scalar_one_or_none()
                
                if record:
                    return record.to_dict()
                return None
        except Exception as e:
            logger.error(f"Failed to get semantic memory: {e}")
            return None
    
    async def save_semantic_memory(
        self,
        user_id: str,
        character_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Save or update semantic memory."""
        try:
            async with get_db() as session:
                result = await session.execute(
                    select(SemanticMemory).where(
                        and_(
                            SemanticMemory.user_id == user_id,
                            SemanticMemory.character_id == character_id,
                        )
                    )
                )
                record = result.scalar_one_or_none()
                
                if record:
                    # Update existing record
                    for key, value in data.items():
                        if key not in ["user_id", "character_id", "updated_at", "created_at", "id"]:
                            if hasattr(record, key):
                                setattr(record, key, value)
                    record.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    clean_data = {k: v for k, v in data.items() 
                                 if k not in ["user_id", "character_id", "updated_at", "created_at", "id"]}
                    record = SemanticMemory(
                        user_id=user_id,
                        character_id=character_id,
                        **clean_data
                    )
                    session.add(record)
                
                # Note: get_db() context manager auto-commits on exit
                logger.info(f"Saved semantic memory for user={user_id}, char={character_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save semantic memory: {e}")
            return False
    
    async def get_episodic_memories(
        self,
        user_id: str,
        character_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get episodic memories for a user-character pair."""
        try:
            async with get_db() as session:
                result = await session.execute(
                    select(EpisodicMemory)
                    .where(
                        and_(
                            EpisodicMemory.user_id == user_id,
                            EpisodicMemory.character_id == character_id,
                        )
                    )
                    .order_by(EpisodicMemory.created_at.desc())
                    .limit(limit)
                )
                records = result.scalars().all()
                return [r.to_dict() for r in records]
        except Exception as e:
            logger.error(f"Failed to get episodic memories: {e}")
            return []
    
    async def save_episodic_memory(
        self,
        user_id: str,
        character_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Save or update an episodic memory."""
        try:
            async with get_db() as session:
                memory_id = data.get("memory_id")
                
                # Check if exists
                result = await session.execute(
                    select(EpisodicMemory).where(
                        EpisodicMemory.memory_id == memory_id
                    )
                )
                record = result.scalar_one_or_none()
                
                if record:
                    # Update existing
                    record.strength = data.get("strength", record.strength)
                    record.recall_count = data.get("recall_count", record.recall_count)
                    if data.get("last_recalled"):
                        try:
                            record.last_recalled = datetime.fromisoformat(
                                data["last_recalled"].replace("Z", "+00:00")
                            )
                        except:
                            record.last_recalled = datetime.utcnow()
                else:
                    # Create new
                    record = EpisodicMemory(
                        memory_id=memory_id,
                        user_id=user_id,
                        character_id=character_id,
                        event_type=data.get("event_type", "other"),
                        summary=data.get("summary", ""),
                        key_dialogue=data.get("key_dialogue", []),
                        emotion_state=data.get("emotion_state"),
                        importance=data.get("importance", 2),
                        strength=data.get("strength", 1.0),
                        recall_count=data.get("recall_count", 0),
                    )
                    session.add(record)
                
                # Note: get_db() context manager auto-commits on exit
                logger.info(f"Saved episodic memory: {memory_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save episodic memory: {e}")
            return False
    
    async def delete_weak_memories(
        self,
        user_id: str,
        character_id: str,
        min_strength: float = 0.3,
        keep_important: bool = True,
    ) -> int:
        """Delete weak memories, returns count deleted."""
        try:
            async with get_db() as session:
                from sqlalchemy import delete
                
                conditions = [
                    EpisodicMemory.user_id == user_id,
                    EpisodicMemory.character_id == character_id,
                    EpisodicMemory.strength < min_strength,
                ]
                
                if keep_important:
                    conditions.append(EpisodicMemory.importance < 3)
                
                result = await session.execute(
                    delete(EpisodicMemory).where(and_(*conditions))
                )
                # Note: get_db() context manager auto-commits on exit
                count = result.rowcount
                logger.info(f"Deleted {count} weak memories for user={user_id}")
                return count
        except Exception as e:
            logger.error(f"Failed to delete weak memories: {e}")
            return 0
    
    async def log_extraction(
        self,
        user_id: str,
        character_id: str,
        source_message: str,
        extracted_semantic: Dict[str, Any],
        extracted_episodic: Dict[str, Any],
    ) -> bool:
        """Log memory extraction for debugging."""
        try:
            async with get_db() as session:
                log = MemoryExtractionLog(
                    user_id=user_id,
                    character_id=character_id,
                    source_message=source_message,
                    extracted_semantic=extracted_semantic,
                    extracted_episodic=extracted_episodic,
                )
                session.add(log)
                # Note: get_db() context manager auto-commits on exit
                return True
        except Exception as e:
            logger.error(f"Failed to log extraction: {e}")
            return False


# Singleton instance
memory_db_service = MemoryDBService()

"""
Vector Database Service for RAG - pgvector (Neon) Implementation
================================================================

Uses Neon PostgreSQL with pgvector extension for semantic search.
Embeddings generated via OpenAI text-embedding-3-small.
"""

import os
import logging
import asyncpg
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from app.core.exceptions import VectorDBError
from app.services.llm_service import OpenAIEmbeddingService

logger = logging.getLogger(__name__)


class VectorService:
    """
    pgvector-based semantic search for Luna memories.
    
    Uses Neon PostgreSQL with pgvector extension.
    Embeddings: OpenAI text-embedding-3-small (1536 dimensions)
    """
    
    def __init__(self):
        self.embedding_service = OpenAIEmbeddingService()
        self._pool: Optional[asyncpg.Pool] = None
        self._db_url = os.getenv("DATABASE_URL", "")
        
        # Convert SQLAlchemy URL format to asyncpg format
        if self._db_url.startswith("postgresql+asyncpg://"):
            self._db_url = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        logger.info("VectorService initialized with pgvector")
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            if not self._db_url or "sqlite" in self._db_url:
                raise VectorDBError("pgvector requires PostgreSQL DATABASE_URL")
            
            self._pool = await asyncpg.create_pool(
                self._db_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            logger.info("pgvector connection pool created")
        return self._pool
    
    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        return await self.embedding_service.embed_single(text)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return await self.embedding_service.embed_texts(texts)
    
    # =========================================================================
    # Episodic Memory Vector Operations
    # =========================================================================
    
    async def save_episode_embedding(
        self,
        memory_id: str,
        embedding: List[float],
    ) -> None:
        """
        Save embedding for an episodic memory.
        
        Args:
            memory_id: The episodic memory ID
            embedding: 1536-dim embedding vector
        """
        try:
            pool = await self._get_pool()
            
            # Format embedding as pgvector string
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            await pool.execute(
                """
                UPDATE episodic_memories 
                SET embedding = $1::vector
                WHERE memory_id = $2
                """,
                embedding_str,
                memory_id,
            )
            logger.debug(f"Saved embedding for memory {memory_id}")
            
        except Exception as e:
            logger.error(f"Failed to save episode embedding: {e}")
            raise VectorDBError(f"pgvector save failed: {e}")
    
    async def search_similar_episodes(
        self,
        user_id: str,
        character_id: str,
        query_text: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> List[Dict]:
        """
        Search for similar episodic memories using cosine similarity.
        
        Args:
            user_id: User ID
            character_id: Character ID
            query_text: Query text to embed and search
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
        
        Returns:
            List of episodic memories with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embed_text(query_text)
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            pool = await self._get_pool()
            
            # Cosine similarity search
            # Note: pgvector's <=> is cosine distance, so similarity = 1 - distance
            rows = await pool.fetch(
                """
                SELECT 
                    memory_id,
                    event_type,
                    summary,
                    key_dialogue,
                    emotion_state,
                    importance,
                    strength,
                    created_at,
                    1 - (embedding <=> $1::vector) as similarity
                FROM episodic_memories
                WHERE user_id = $2 
                  AND character_id = $3
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> $1::vector) >= $4
                ORDER BY embedding <=> $1::vector
                LIMIT $5
                """,
                embedding_str,
                user_id,
                character_id,
                min_similarity,
                top_k,
            )
            
            results = []
            for row in rows:
                results.append({
                    "memory_id": row["memory_id"],
                    "event_type": row["event_type"],
                    "summary": row["summary"],
                    "key_dialogue": row["key_dialogue"],
                    "emotion_state": row["emotion_state"],
                    "importance": row["importance"],
                    "strength": row["strength"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "similarity": float(row["similarity"]),
                })
            
            logger.debug(f"Found {len(results)} similar episodes for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            # Return empty list on failure (graceful degradation)
            return []
    
    async def backfill_embeddings(
        self,
        user_id: str,
        character_id: str,
        batch_size: int = 10,
    ) -> int:
        """
        Backfill embeddings for episodes that don't have them.
        
        Returns:
            Number of episodes updated
        """
        try:
            pool = await self._get_pool()
            
            # Get episodes without embeddings
            rows = await pool.fetch(
                """
                SELECT memory_id, summary, key_dialogue
                FROM episodic_memories
                WHERE user_id = $1 
                  AND character_id = $2
                  AND embedding IS NULL
                LIMIT $3
                """,
                user_id,
                character_id,
                batch_size,
            )
            
            if not rows:
                return 0
            
            # Generate embeddings for summaries
            texts = []
            memory_ids = []
            for row in rows:
                # Combine summary and key dialogue for richer embedding
                text = row["summary"]
                if row["key_dialogue"]:
                    text += " " + " ".join(row["key_dialogue"][:2])
                texts.append(text)
                memory_ids.append(row["memory_id"])
            
            embeddings = await self.embed_texts(texts)
            
            # Save embeddings
            for memory_id, embedding in zip(memory_ids, embeddings):
                await self.save_episode_embedding(memory_id, embedding)
            
            logger.info(f"Backfilled {len(memory_ids)} embeddings for user {user_id}")
            return len(memory_ids)
            
        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            return 0
    
    # =========================================================================
    # Legacy API (backward compatibility with old VectorService interface)
    # =========================================================================
    
    async def upsert_memory(
        self,
        user_id: UUID,
        message_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        embedding: List[float],
    ) -> None:
        """
        Legacy API - not used with new memory system.
        Kept for backward compatibility.
        """
        logger.warning("upsert_memory is deprecated - use save_episode_embedding instead")
    
    async def search_memories(
        self,
        user_id: UUID,
        query_text: str,
        top_k: int = 5,
        session_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """
        Legacy API for searching memories.
        Redirects to search_similar_episodes with default character.
        """
        # This needs a character_id, so we return empty for now
        # The new code should use search_similar_episodes directly
        logger.warning("search_memories is deprecated - use search_similar_episodes instead")
        return []
    
    async def delete_session_memories(self, user_id: UUID, session_id: UUID) -> None:
        """Legacy API - not implemented for pgvector."""
        pass
    
    async def delete_user_memories(self, user_id: UUID) -> None:
        """Legacy API - not implemented for pgvector."""
        pass


# Singleton instance
vector_service = VectorService()

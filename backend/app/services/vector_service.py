"""
Vector Database Service for RAG (Retrieval-Augmented Generation)
Supports Pinecone (production) and ChromaDB (development)
"""

import os
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from app.core.exceptions import VectorDBError
from app.services.llm_service import OpenAIEmbeddingService


class VectorService:
    """
    Abstraction layer for vector database operations.
    Automatically selects Pinecone or ChromaDB based on environment.
    """
    
    def __init__(self):
        self.embedding_service = OpenAIEmbeddingService()
        self.provider = os.getenv("VECTOR_DB_PROVIDER", "chromadb")  # 'pinecone' or 'chromadb'
        
        if self.provider == "pinecone":
            self.client = PineconeClient()
        else:
            self.client = ChromaDBClient()
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        """
        return await self.embedding_service.embed_single(text)
    
    async def upsert_memory(
        self,
        user_id: UUID,
        message_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        embedding: List[float]
    ) -> None:
        """
        Store a message embedding in vector DB.
        
        Args:
            user_id: User UUID (for namespace isolation)
            message_id: Message UUID
            session_id: Session UUID
            role: Message role ('user' or 'assistant')
            content: Message content
            embedding: Embedding vector
        """
        metadata = {
            "user_id": str(user_id),
            "message_id": str(message_id),
            "session_id": str(session_id),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.client.upsert(
            namespace=f"user_{user_id}",
            vector_id=str(message_id),
            embedding=embedding,
            metadata=metadata
        )
    
    async def search_memories(
        self,
        user_id: UUID,
        query_text: str,
        top_k: int = 5,
        session_id: Optional[UUID] = None
    ) -> List[Dict]:
        """
        Search for relevant memories using semantic similarity.
        
        Args:
            user_id: User UUID
            query_text: Query text to search for
            top_k: Number of results to return
            session_id: Optional session filter
        
        Returns:
            List of relevant memories with metadata
        """
        # Embed query
        query_embedding = await self.embed_text(query_text)
        
        # Build filter
        filter_dict = {"user_id": str(user_id)}
        if session_id:
            filter_dict["session_id"] = str(session_id)
        
        # Search
        results = await self.client.search(
            namespace=f"user_{user_id}",
            query_embedding=query_embedding,
            top_k=top_k,
            filter_dict=filter_dict
        )
        
        return results
    
    async def delete_session_memories(self, user_id: UUID, session_id: UUID) -> None:
        """
        Delete all memories for a session.
        """
        await self.client.delete_by_filter(
            namespace=f"user_{user_id}",
            filter_dict={"session_id": str(session_id)}
        )
    
    async def delete_user_memories(self, user_id: UUID) -> None:
        """
        Delete all memories for a user.
        """
        await self.client.delete_namespace(namespace=f"user_{user_id}")


class PineconeClient:
    """
    Pinecone vector database client.
    Production-ready, serverless, scalable.
    """
    
    def __init__(self):
        try:
            import pinecone
            from pinecone import Pinecone, ServerlessSpec
        except ImportError:
            raise ImportError("pinecone-client not installed. Run: pip install pinecone-client")
        
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        self.pc = Pinecone(api_key=api_key)
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "ai-companion-memories")
        
        # Create index if doesn't exist
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,  # text-embedding-3-small
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        self.index = self.pc.Index(self.index_name)
    
    async def upsert(
        self,
        namespace: str,
        vector_id: str,
        embedding: List[float],
        metadata: Dict
    ) -> None:
        """
        Upsert a vector with metadata.
        """
        try:
            self.index.upsert(
                vectors=[(vector_id, embedding, metadata)],
                namespace=namespace
            )
        except Exception as e:
            raise VectorDBError(f"Pinecone upsert failed: {str(e)}")
    
    async def search(
        self,
        namespace: str,
        query_embedding: List[float],
        top_k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors.
        """
        try:
            results = self.index.query(
                namespace=namespace,
                vector=query_embedding,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True
            )
            
            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "role": match.metadata.get("role"),
                    "content": match.metadata.get("content"),
                    "timestamp": match.metadata.get("timestamp")
                }
                for match in results.matches
            ]
        except Exception as e:
            raise VectorDBError(f"Pinecone search failed: {str(e)}")
    
    async def delete_by_filter(self, namespace: str, filter_dict: Dict) -> None:
        """
        Delete vectors by metadata filter.
        """
        try:
            self.index.delete(namespace=namespace, filter=filter_dict)
        except Exception as e:
            raise VectorDBError(f"Pinecone delete failed: {str(e)}")
    
    async def delete_namespace(self, namespace: str) -> None:
        """
        Delete entire namespace.
        """
        try:
            self.index.delete(namespace=namespace, delete_all=True)
        except Exception as e:
            raise VectorDBError(f"Pinecone namespace delete failed: {str(e)}")


class ChromaDBClient:
    """
    ChromaDB vector database client.
    Lightweight, local/self-hosted, good for development.
    """
    
    def __init__(self):
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError("chromadb not installed. Run: pip install chromadb")
        
        # Use persistent storage
        persist_directory = os.getenv("CHROMADB_PERSIST_DIR", "/var/lib/chromadb")
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection_name = "ai_companion_memories"
    
    def _get_collection(self, namespace: str):
        """
        Get or create collection for namespace.
        ChromaDB doesn't have native namespaces, so we use collection per user.
        """
        collection_name = f"{self.collection_name}_{namespace}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    async def upsert(
        self,
        namespace: str,
        vector_id: str,
        embedding: List[float],
        metadata: Dict
    ) -> None:
        """
        Upsert a vector with metadata.
        """
        try:
            collection = self._get_collection(namespace)
            collection.upsert(
                ids=[vector_id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
        except Exception as e:
            raise VectorDBError(f"ChromaDB upsert failed: {str(e)}")
    
    async def search(
        self,
        namespace: str,
        query_embedding: List[float],
        top_k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors.
        """
        try:
            collection = self._get_collection(namespace)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_dict if filter_dict else None,
                include=["metadatas", "distances"]
            )
            
            if not results["ids"][0]:
                return []
            
            return [
                {
                    "id": results["ids"][0][i],
                    "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "role": results["metadatas"][0][i].get("role"),
                    "content": results["metadatas"][0][i].get("content"),
                    "timestamp": results["metadatas"][0][i].get("timestamp")
                }
                for i in range(len(results["ids"][0]))
            ]
        except Exception as e:
            raise VectorDBError(f"ChromaDB search failed: {str(e)}")
    
    async def delete_by_filter(self, namespace: str, filter_dict: Dict) -> None:
        """
        Delete vectors by metadata filter.
        """
        try:
            collection = self._get_collection(namespace)
            collection.delete(where=filter_dict)
        except Exception as e:
            raise VectorDBError(f"ChromaDB delete failed: {str(e)}")
    
    async def delete_namespace(self, namespace: str) -> None:
        """
        Delete entire namespace (collection).
        """
        try:
            collection_name = f"{self.collection_name}_{namespace}"
            self.client.delete_collection(name=collection_name)
        except Exception as e:
            raise VectorDBError(f"ChromaDB namespace delete failed: {str(e)}")

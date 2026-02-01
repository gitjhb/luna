"""
OpenAI Embedding Service
========================

⚠️  IMPORTANT: This is the ONLY use of OpenAI API in this project!
    Do NOT use OpenAI for chat/completion. Use Grok instead.

Model: text-embedding-3-small
Cost: $0.02/M tokens
Dimensions: 1536

Used for:
- Memory/RAG vector embeddings
- Semantic search
- Message similarity

NOT used for:
- Chat/conversation (use Grok)
- Image generation (use Grok)
- Emotion analysis (use Grok)
"""

import logging
from typing import List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMServiceError
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService:
    """
    OpenAI Embedding API Service
    
    ⚠️  THIS IS THE ONLY OPENAI SERVICE - DO NOT ADD MORE!
    
    Model: text-embedding-3-small
    - Cost: $0.02 per 1M tokens
    - Dimensions: 1536
    - Max input: 8191 tokens
    
    If you need chat/completion, use GrokChatService instead!
    """
    
    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    COST_PER_MILLION_TOKENS = 0.02
    MAX_TOKENS = 8191
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - embedding service will fail")
        
        self.base_url = settings.OPENAI_BASE_URL
        self.timeout = 30.0
        
        logger.info(f"OpenAIEmbeddingService initialized (model: {self.MODEL})")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors (1536 dimensions each)
        
        Raises:
            LLMServiceError: If API call fails
        """
        if not texts:
            return []
        
        if not self.api_key:
            raise LLMServiceError("OPENAI_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "input": texts,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise LLMServiceError(
                        f"OpenAI Embedding API error: {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                
                # Log usage for cost tracking
                usage = data.get("usage", {})
                if usage:
                    tokens = usage.get("total_tokens", 0)
                    cost = tokens / 1_000_000 * self.COST_PER_MILLION_TOKENS
                    logger.debug(f"Embedding tokens: {tokens}, cost: ${cost:.6f}")
                
                # Sort by index to ensure correct order
                embeddings_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in embeddings_data]
        
        except httpx.TimeoutException:
            raise LLMServiceError("OpenAI Embedding API timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"OpenAI Embedding API request failed: {str(e)}")
    
    async def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
        
        Returns:
            Embedding vector (1536 dimensions)
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        
        embeddings = await self.embed([text])
        return embeddings[0]
    
    async def embed_for_memory(
        self,
        content: str,
        metadata: dict = None,
    ) -> dict:
        """
        Generate embedding for memory storage.
        
        Args:
            content: Memory content text
            metadata: Optional metadata (timestamp, user_id, etc.)
        
        Returns:
            Dict with embedding and metadata ready for vector DB
        """
        embedding = await self.embed_single(content)
        
        return {
            "content": content,
            "embedding": embedding,
            "dimensions": self.DIMENSIONS,
            "model": self.MODEL,
            "metadata": metadata or {},
        }
    
    def estimate_cost(self, texts: List[str]) -> float:
        """
        Estimate embedding cost before calling API.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            Estimated cost in USD
        """
        # Rough estimate: 1 token ≈ 4 characters
        total_chars = sum(len(t) for t in texts)
        estimated_tokens = total_chars / 4
        return estimated_tokens / 1_000_000 * self.COST_PER_MILLION_TOKENS


# Singleton instance
openai_embedding = OpenAIEmbeddingService()


# =============================================================================
# ⚠️  REMINDER: DO NOT ADD CHAT/COMPLETION METHODS HERE!
#     This service is ONLY for embeddings.
#     For chat, use: from app.services.llm import grok_chat
# =============================================================================

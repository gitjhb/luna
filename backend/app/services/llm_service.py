"""
xAI Grok API Service Wrapper
"""

from typing import List, Dict, Optional, AsyncGenerator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMServiceError
from app.config import settings


class GrokService:
    """
    Wrapper for xAI Grok API.
    
    Documentation: https://docs.x.ai/api
    """
    
    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set in settings")
        
        self.base_url = settings.XAI_BASE_URL
        self.model = settings.XAI_MODEL
        self.timeout = 60.0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: int = 500,
        top_p: float = 0.9,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stream: bool = False
    ) -> Dict:
        """
        Call Grok chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalize frequent tokens (-2 to 2)
            presence_penalty: Penalize present tokens (-2 to 2)
            stream: Enable streaming (not implemented yet)
        
        Returns:
            API response dict
        
        Raises:
            LLMServiceError: If API call fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Note: Grok doesn't support frequency_penalty, presence_penalty, top_p
            "stream": stream
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    raise LLMServiceError(
                        f"Grok API error: {error_detail}",
                        status_code=response.status_code
                    )
                
                return response.json()
        
        except httpx.TimeoutException:
            raise LLMServiceError("Grok API timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"Grok API request failed: {str(e)}")
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: int = 500
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion (for real-time responses).
        
        Yields:
            Content chunks as they arrive
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        raise LLMServiceError(
                            f"Grok API error: {response.text}",
                            status_code=response.status_code
                        )
                    
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            # Parse SSE format
                            if chunk.startswith("data: "):
                                data = chunk[6:]
                                if data.strip() == "[DONE]":
                                    break
                                yield data
        
        except httpx.TimeoutException:
            raise LLMServiceError("Grok API timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"Grok API request failed: {str(e)}")
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for texts.
        Note: xAI may not have a dedicated embedding endpoint.
        Fallback to OpenAI or use a separate embedding service.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors
        """
        # TODO: Implement if xAI provides embedding endpoint
        # For now, use OpenAI's embedding API
        raise NotImplementedError(
            "Grok doesn't provide embeddings. Use OpenAI text-embedding-3-small instead."
        )
    
    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation.
        Rule of thumb: 1 token ≈ 4 characters.
        """
        return max(1, len(text) // 4)


class OpenAIEmbeddingService:
    """
    OpenAI embedding service for RAG.
    Using text-embedding-3-small (1536 dimensions).
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in settings")
        
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.timeout = 30.0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: List of text strings
        
        Returns:
            List of embedding vectors (1536 dimensions each)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": texts
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
                        f"OpenAI embedding error: {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings
        
        except httpx.TimeoutException:
            raise LLMServiceError("OpenAI embedding timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"OpenAI embedding request failed: {str(e)}")
    
    async def embed_single(self, text: str) -> List[float]:
        """
        Get embedding for a single text.
        
        Args:
            text: Text string
        
        Returns:
            Embedding vector (1536 dimensions)
        """
        embeddings = await self.embed_texts([text])
        return embeddings[0]

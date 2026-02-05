"""
LLM Service Compatibility Layer
===============================

⚠️  DEPRECATED: This file is kept for backward compatibility.
    New code should import from app.services.llm instead:
    
    from app.services.llm import grok_chat, grok_image, openai_embedding

Architecture:
- Chat: Grok grok-4-1-fast-non-reasoning ($0.2/M tokens)
- Image: Grok grok-2-image ($0.07/image)
- Embedding: OpenAI text-embedding-3-small ($0.02/M tokens) - ONLY OpenAI use!
"""

import logging
from typing import List, Dict, Optional, AsyncGenerator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMServiceError
from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# GrokService - Main Chat (backward compatible)
# =============================================================================

class GrokService:
    """
    Grok Chat API Service (backward compatible wrapper)
    
    ⚠️  Consider using: from app.services.llm import grok_chat
    """
    
    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set in settings")
        
        self.base_url = settings.XAI_BASE_URL
        self.model = settings.XAI_MODEL  # grok-4-1-fast-non-reasoning
        self.timeout = 60.0
        
        logger.debug(f"GrokService initialized with model: {self.model}")
    
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
        stream: bool = False,
        response_format: Dict = None
    ) -> Dict:
        """Call Grok chat completion API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise LLMServiceError(
                        f"Grok API error: {response.text}",
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
        """Stream chat completion."""
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
                            if chunk.startswith("data: "):
                                data = chunk[6:]
                                if data.strip() == "[DONE]":
                                    break
                                yield data
        
        except httpx.TimeoutException:
            raise LLMServiceError("Grok API timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"Grok API request failed: {str(e)}")


# =============================================================================
# OpenAIEmbeddingService - ONLY OpenAI use in this project!
# =============================================================================

class OpenAIEmbeddingService:
    """
    OpenAI Embedding Service for memory/RAG.
    
    ⚠️  THIS IS THE ONLY LEGITIMATE USE OF OPENAI API!
        Do not add chat/completion methods here.
    
    Model: text-embedding-3-small ($0.02/M tokens)
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - embeddings will fail")
        
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.timeout = 30.0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        if not self.api_key:
            raise LLMServiceError("OPENAI_API_KEY not configured")
            
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
        """Get embedding for a single text."""
        embeddings = await self.embed_texts([text])
        return embeddings[0]


# =============================================================================
# MiniLLMService - Now uses Grok instead of OpenAI!
# =============================================================================

class MiniLLMService:
    """
    快速轻量 LLM 服务 - 用于情绪分析等任务
    
    ⚠️  CHANGED: Now uses Grok instead of OpenAI GPT-4o-mini
        Model: grok-4-1-fast-non-reasoning ($0.2/M tokens)
        
    This keeps costs on Grok and reserves OpenAI for embeddings only.
    """
    
    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set for MiniLLM (now using Grok)")
        
        self.base_url = settings.XAI_BASE_URL
        self.model = settings.XAI_MODEL  # grok-4-1-fast-non-reasoning
        self.timeout = 15.0
        
        logger.info(f"MiniLLMService initialized with Grok model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3)
    )
    async def analyze(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 200,
    ) -> str:
        """
        快速分析 - 用于情绪检测等轻量任务
        
        Now uses Grok API instead of OpenAI.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise LLMServiceError(
                        f"MiniLLM (Grok) error: {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
        
        except httpx.TimeoutException:
            raise LLMServiceError("MiniLLM (Grok) timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"MiniLLM (Grok) request failed: {str(e)}")


# =============================================================================
# Singletons (backward compatible)
# =============================================================================

mini_llm = MiniLLMService()

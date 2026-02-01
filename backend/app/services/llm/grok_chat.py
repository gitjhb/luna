"""
Grok Chat Service
=================

Main conversation model: grok-4-1-fast-non-reasoning
Cost: $0.2/M tokens (input + output)

Documentation: https://docs.x.ai/api
"""

import logging
from typing import List, Dict, Optional, AsyncGenerator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMServiceError
from app.config import settings

logger = logging.getLogger(__name__)


class GrokChatService:
    """
    Grok Chat API Service
    
    Models available:
    - grok-4-1-fast-non-reasoning: Fast, cheap ($0.2/M tokens) - DEFAULT
    - grok-4-1: Full reasoning capability
    - grok-beta: Legacy model
    """
    
    # Model pricing (per 1M tokens)
    PRICING = {
        "grok-4-1-fast-non-reasoning": {"input": 0.1, "output": 0.1},  # $0.2 total
        "grok-4-1": {"input": 2.0, "output": 8.0},
        "grok-beta": {"input": 0.5, "output": 1.5},
    }
    
    DEFAULT_MODEL = "grok-4-1-fast-non-reasoning"
    
    def __init__(self, model: str = None):
        self.api_key = settings.XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set")
        
        self.base_url = settings.XAI_BASE_URL
        self.model = model or self.DEFAULT_MODEL
        self.timeout = 60.0
        
        logger.info(f"GrokChatService initialized with model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: int = 500,
        stream: bool = False,
        model: str = None,
    ) -> Dict:
        """
        Chat completion API call.
        
        Args:
            messages: List of {"role": "system/user/assistant", "content": "..."}
            temperature: 0-2, higher = more creative
            max_tokens: Maximum response length
            stream: Enable streaming (returns AsyncGenerator)
            model: Override default model
        
        Returns:
            API response dict with choices[0].message.content
        """
        use_model = model or self.model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
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
                    raise LLMServiceError(
                        f"Grok API error: {response.text}",
                        status_code=response.status_code
                    )
                
                result = response.json()
                
                # Log usage for cost tracking
                usage = result.get("usage", {})
                if usage:
                    pricing = self.PRICING.get(use_model, self.PRICING[self.DEFAULT_MODEL])
                    input_cost = usage.get("prompt_tokens", 0) / 1_000_000 * pricing["input"]
                    output_cost = usage.get("completion_tokens", 0) / 1_000_000 * pricing["output"]
                    logger.debug(f"Grok usage: {usage}, cost: ${input_cost + output_cost:.6f}")
                
                return result
        
        except httpx.TimeoutException:
            raise LLMServiceError("Grok API timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"Grok API request failed: {str(e)}")
    
    async def chat_simple(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 200,
    ) -> str:
        """
        Simple chat for quick tasks (emotion analysis, etc.)
        
        Args:
            system_prompt: System instruction
            user_message: User input
            temperature: Lower = more deterministic
            max_tokens: Max output length
        
        Returns:
            Response text only
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return result["choices"][0]["message"]["content"]
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: int = 500,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion.
        
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
                            f"Grok API error: {response.status_code}",
                            status_code=response.status_code
                        )
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        
        except httpx.TimeoutException:
            raise LLMServiceError("Grok streaming timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"Grok streaming failed: {str(e)}")


# Singleton instance
grok_chat = GrokChatService()

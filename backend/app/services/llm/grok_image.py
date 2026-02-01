"""
Grok Image Service
==================

Image generation model: grok-imagine-image
Cost: $0.07/image

Documentation: https://docs.x.ai/api
"""

import logging
import base64
from typing import Optional, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMServiceError
from app.config import settings

logger = logging.getLogger(__name__)


class GrokImageService:
    """
    Grok Image Generation API Service
    
    Model: grok-imagine-image
    Cost: $0.07 per image
    
    Supports:
    - Text to image generation
    - Multiple sizes (1024x1024, 1024x1792, 1792x1024)
    - Base64 or URL output
    """
    
    MODEL = "grok-2-image"  # or grok-imagine-image when available
    COST_PER_IMAGE = 0.07
    
    SUPPORTED_SIZES = [
        "1024x1024",   # Square
        "1024x1792",   # Portrait
        "1792x1024",   # Landscape
    ]
    
    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set")
        
        self.base_url = settings.XAI_BASE_URL
        self.timeout = 120.0  # Image generation can be slow
        
        logger.info(f"GrokImageService initialized")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        response_format: str = "url",
        quality: str = "standard",
    ) -> List[dict]:
        """
        Generate images from text prompt.
        
        Args:
            prompt: Text description of the image
            size: Image size (1024x1024, 1024x1792, 1792x1024)
            n: Number of images to generate (1-4)
            response_format: "url" or "b64_json"
            quality: "standard" or "hd"
        
        Returns:
            List of {"url": "..."} or {"b64_json": "..."}
        """
        if size not in self.SUPPORTED_SIZES:
            raise ValueError(f"Unsupported size: {size}. Use one of {self.SUPPORTED_SIZES}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "prompt": prompt,
            "size": size,
            "n": min(n, 4),  # Max 4 images
            "response_format": response_format,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise LLMServiceError(
                        f"Grok Image API error: {response.text}",
                        status_code=response.status_code
                    )
                
                result = response.json()
                images = result.get("data", [])
                
                # Log cost
                cost = len(images) * self.COST_PER_IMAGE
                logger.info(f"Generated {len(images)} images, cost: ${cost:.2f}")
                
                return images
        
        except httpx.TimeoutException:
            raise LLMServiceError("Grok Image API timeout")
        except httpx.RequestError as e:
            raise LLMServiceError(f"Grok Image API request failed: {str(e)}")
    
    async def generate_one(
        self,
        prompt: str,
        size: str = "1024x1024",
        as_base64: bool = False,
    ) -> str:
        """
        Generate a single image.
        
        Args:
            prompt: Text description
            size: Image size
            as_base64: Return base64 instead of URL
        
        Returns:
            Image URL or base64 string
        """
        response_format = "b64_json" if as_base64 else "url"
        images = await self.generate(
            prompt=prompt,
            size=size,
            n=1,
            response_format=response_format,
        )
        
        if not images:
            raise LLMServiceError("No image generated")
        
        return images[0].get("b64_json" if as_base64 else "url", "")
    
    async def generate_character_image(
        self,
        character_name: str,
        character_description: str,
        scene: str = None,
        style: str = "anime",
        emotion: str = "happy",
    ) -> str:
        """
        Generate character image with consistent style.
        
        Args:
            character_name: Character's name
            character_description: Physical appearance
            scene: Optional scene/background
            style: Art style (anime, realistic, etc.)
            emotion: Character's emotion
        
        Returns:
            Image URL
        """
        prompt_parts = [
            f"{style} style illustration",
            f"of {character_name}",
            f"({character_description})",
            f"with {emotion} expression",
        ]
        
        if scene:
            prompt_parts.append(f"in {scene}")
        
        prompt_parts.extend([
            "high quality",
            "detailed",
            "beautiful lighting",
        ])
        
        prompt = ", ".join(prompt_parts)
        
        return await self.generate_one(prompt=prompt, size="1024x1024")


# Singleton instance
grok_image = GrokImageService()

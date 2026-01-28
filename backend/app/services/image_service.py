"""
Image Generation Service - OpenAI DALL-E 3
"""

import os
import httpx
from typing import Optional, Literal


class ImageGenerationService:
    """OpenAI DALL-E 3 图片生成"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.timeout = 120  # 图片生成可能较慢

    async def generate(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
        quality: Literal["standard", "hd"] = "standard",
        style: Literal["vivid", "natural"] = "vivid",
        n: int = 1,
    ) -> list[dict]:
        """
        生成图片
        
        Args:
            prompt: 图片描述
            model: dall-e-3 或 dall-e-2
            size: 图片尺寸
            quality: standard 或 hd (仅 dall-e-3)
            style: vivid(超现实) 或 natural(自然)
            n: 生成数量 (dall-e-3 只支持 1)
        
        Returns:
            [{"url": "...", "revised_prompt": "..."}]
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": min(n, 1) if model == "dall-e-3" else n,
        }

        if model == "dall-e-3":
            payload["quality"] = quality
            payload["style"] = style

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=payload,
            )

            if resp.status_code != 200:
                raise Exception(f"Image generation failed: {resp.text}")

            data = resp.json()
            return [
                {
                    "url": item["url"],
                    "revised_prompt": item.get("revised_prompt", prompt),
                }
                for item in data["data"]
            ]

    async def generate_avatar(
        self,
        description: str,
        style: str = "anime",
    ) -> str:
        """
        生成角色头像
        
        Args:
            description: 角色描述
            style: anime / realistic / cartoon
        
        Returns:
            图片 URL
        """
        style_prompts = {
            "anime": "anime style, high quality illustration, detailed, vibrant colors",
            "realistic": "photorealistic portrait, professional photography, studio lighting",
            "cartoon": "cartoon style, fun and colorful, exaggerated features",
        }
        
        style_suffix = style_prompts.get(style, style_prompts["anime"])
        full_prompt = f"Portrait of {description}. {style_suffix}. Centered composition, clean background."

        results = await self.generate(
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
        )
        return results[0]["url"]

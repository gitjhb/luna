"""
Image Generation Service - xAI Grok Image API
==============================================

Complete image generation service with:
- xAI Grok API integration
- Mock mode for development
- Prompt template management
- Cost tracking
- History recording

Author: Luna AI
Date: January 2026
"""

import os
import httpx
import uuid
import logging
from datetime import datetime
from typing import Optional, Literal, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

logger = logging.getLogger(__name__)


# ============================================================================
# Constants and Configuration
# ============================================================================

class ImageStyle(str, Enum):
    """Image style enumeration"""
    SELFIE = "selfie"           # 自拍
    LIFESTYLE = "lifestyle"     # 生活照
    ARTISTIC = "artistic"       # 艺术风格
    PORTRAIT = "portrait"       # 肖像
    CASUAL = "casual"           # 日常
    ROMANTIC = "romantic"       # 浪漫
    PLAYFUL = "playful"         # 俏皮
    ELEGANT = "elegant"         # 优雅


class GenerationType(str, Enum):
    """Image generation type"""
    USER_REQUEST = "user_request"
    CHARACTER_GIFT = "character_gift"
    MILESTONE_REWARD = "milestone_reward"
    SPECIAL_EVENT = "special_event"


# Cost configuration
IMAGE_COST_CONFIG = {
    "base_cost": 50,           # 基础图片成本 (金币)
    "hd_multiplier": 2.0,      # HD 质量倍数
    "portrait_multiplier": 1.0,
    "landscape_multiplier": 1.2,
    "styles": {
        "selfie": 50,
        "lifestyle": 50,
        "artistic": 80,
        "portrait": 60,
        "casual": 50,
        "romantic": 70,
        "playful": 50,
        "elegant": 70,
    }
}


@dataclass
class ImageGenerationResult:
    """Result of image generation"""
    success: bool
    image_id: str
    image_url: str
    thumbnail_url: Optional[str] = None
    final_prompt: str = ""
    cost_credits: int = 0
    is_free: bool = False
    error: Optional[str] = None
    model_used: str = "grok-2-image"
    aspect_ratio: str = "1:1"


# ============================================================================
# Prompt Templates
# ============================================================================

# Character appearance templates - customize per character
CHARACTER_APPEARANCE_TEMPLATES = {
    "default": {
        "base": "a beautiful young woman",
        "hair": "long dark hair",
        "eyes": "expressive eyes",
        "skin": "clear skin",
        "style": "elegant and charming",
    },
    # Add more character-specific templates here
}


# Style-specific prompt templates
STYLE_PROMPT_TEMPLATES = {
    ImageStyle.SELFIE: {
        "base": "{character_desc}, taking a selfie, looking directly at camera with a warm smile",
        "modifiers": [
            "smartphone selfie perspective",
            "natural lighting",
            "candid expression",
            "close-up shot",
            "soft focus background",
        ],
        "aspect_ratio": "1:1",
    },
    ImageStyle.LIFESTYLE: {
        "base": "{character_desc}, in a lifestyle scene",
        "modifiers": [
            "natural candid pose",
            "everyday setting",
            "warm ambient lighting",
            "photorealistic style",
            "high quality photography",
        ],
        "aspect_ratio": "4:3",
    },
    ImageStyle.ARTISTIC: {
        "base": "{character_desc}, artistic portrait",
        "modifiers": [
            "digital art style",
            "dramatic lighting",
            "vibrant colors",
            "detailed illustration",
            "professional artwork quality",
        ],
        "aspect_ratio": "1:1",
    },
    ImageStyle.PORTRAIT: {
        "base": "{character_desc}, professional portrait",
        "modifiers": [
            "studio lighting",
            "professional photography",
            "elegant pose",
            "high resolution",
            "shallow depth of field",
        ],
        "aspect_ratio": "3:4",
    },
    ImageStyle.CASUAL: {
        "base": "{character_desc}, casual everyday look",
        "modifiers": [
            "relaxed natural pose",
            "comfortable setting",
            "warm friendly expression",
            "natural daylight",
            "candid photography style",
        ],
        "aspect_ratio": "1:1",
    },
    ImageStyle.ROMANTIC: {
        "base": "{character_desc}, romantic mood",
        "modifiers": [
            "soft golden hour lighting",
            "dreamy atmosphere",
            "gentle smile",
            "warm color tones",
            "intimate feeling",
        ],
        "aspect_ratio": "3:4",
    },
    ImageStyle.PLAYFUL: {
        "base": "{character_desc}, playful expression",
        "modifiers": [
            "fun energetic vibe",
            "bright lighting",
            "joyful smile",
            "dynamic pose",
            "colorful background",
        ],
        "aspect_ratio": "1:1",
    },
    ImageStyle.ELEGANT: {
        "base": "{character_desc}, elegant and sophisticated",
        "modifiers": [
            "refined pose",
            "classy setting",
            "subtle lighting",
            "graceful expression",
            "high fashion quality",
        ],
        "aspect_ratio": "3:4",
    },
}


# Negative prompts for quality control
DEFAULT_NEGATIVE_PROMPT = (
    "deformed, distorted, disfigured, poorly drawn, bad anatomy, "
    "wrong anatomy, extra limb, missing limb, floating limbs, "
    "mutated hands, extra fingers, fused fingers, "
    "blurry, low quality, watermark, text, logo"
)


# ============================================================================
# Image Generation Service
# ============================================================================

class ImageGenerationService:
    """
    xAI Grok Image Generation Service
    
    Supports:
    - Real API calls to xAI
    - Mock mode for development
    - Multiple image styles
    - Cost tracking
    - History recording
    """
    
    def __init__(self):
        from app.config import settings
        
        self.api_key = settings.XAI_API_KEY
        self.base_url = settings.XAI_BASE_URL
        self.mock_mode = settings.MOCK_IMAGE
        self.timeout = 120  # Image generation can be slow
        
        # Default model
        self.model = settings.XAI_IMAGE_MODEL
        
        logger.info(f"ImageGenerationService initialized - Mock mode: {self.mock_mode}")
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    async def generate_image(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.SELFIE,
        character_id: str = "default",
        user_id: str = "",
        generation_type: GenerationType = GenerationType.USER_REQUEST,
        db: Optional[AsyncSession] = None,
        context: Optional[Dict[str, Any]] = None,
        aspect_ratio: str = "1:1",
        n: int = 1,
    ) -> ImageGenerationResult:
        """
        Generate an image with the specified parameters.
        
        Args:
            prompt: User's description or request (can be empty for auto-generated)
            style: Image style from ImageStyle enum
            character_id: Character identifier for customization
            user_id: User ID for history tracking
            generation_type: Type of generation (user request, gift, etc.)
            db: Database session for recording history
            context: Additional context (e.g., relationship level, mood)
            aspect_ratio: Image aspect ratio (1:1, 4:3, 3:4, etc.)
            n: Number of images to generate (1-10)
        
        Returns:
            ImageGenerationResult with image URL and metadata
        """
        # Build the final prompt
        final_prompt = self._build_prompt(
            user_prompt=prompt,
            style=style,
            character_id=character_id,
            context=context,
        )
        
        # Calculate cost
        is_free = generation_type in [
            GenerationType.CHARACTER_GIFT,
            GenerationType.MILESTONE_REWARD,
        ]
        cost_credits = 0 if is_free else self.get_image_cost(style)
        
        # Generate image
        if self.mock_mode:
            result = await self._generate_mock_image(
                final_prompt=final_prompt,
                style=style,
                aspect_ratio=aspect_ratio,
            )
        else:
            result = await self._generate_real_image(
                final_prompt=final_prompt,
                aspect_ratio=aspect_ratio,
                n=n,
            )
        
        if not result.success:
            return result
        
        # Update result with cost info
        result.cost_credits = cost_credits
        result.is_free = is_free
        result.final_prompt = final_prompt
        
        # Record to database if session provided
        if db and user_id:
            await self._record_generation(
                db=db,
                user_id=user_id,
                character_id=character_id,
                result=result,
                generation_type=generation_type,
                style=style,
                original_prompt=prompt,
            )
        
        return result
    
    async def generate_character_gift(
        self,
        character_id: str,
        user_id: str,
        intimacy_level: int = 1,
        mood: str = "happy",
        db: Optional[AsyncSession] = None,
    ) -> ImageGenerationResult:
        """
        Generate a gift image from a character to user.
        These are free and triggered by the character AI.
        
        Args:
            character_id: Character sending the gift
            user_id: Recipient user
            intimacy_level: Current relationship level (affects style)
            mood: Character's current mood
            db: Database session
        
        Returns:
            ImageGenerationResult
        """
        # Select appropriate style based on intimacy level
        if intimacy_level >= 80:
            style = ImageStyle.ROMANTIC
        elif intimacy_level >= 50:
            style = ImageStyle.PLAYFUL
        elif intimacy_level >= 30:
            style = ImageStyle.CASUAL
        else:
            style = ImageStyle.SELFIE
        
        context = {
            "intimacy_level": intimacy_level,
            "mood": mood,
            "is_gift": True,
        }
        
        return await self.generate_image(
            prompt="",  # Auto-generate based on context
            style=style,
            character_id=character_id,
            user_id=user_id,
            generation_type=GenerationType.CHARACTER_GIFT,
            db=db,
            context=context,
        )
    
    def get_image_cost(self, style: ImageStyle = ImageStyle.SELFIE) -> int:
        """
        Get the cost in credits for generating an image.
        
        Args:
            style: Image style
        
        Returns:
            Cost in credits (金币)
        """
        style_str = style.value if isinstance(style, ImageStyle) else style
        return IMAGE_COST_CONFIG["styles"].get(style_str, IMAGE_COST_CONFIG["base_cost"])
    
    def get_available_styles(self) -> List[Dict[str, Any]]:
        """Get list of available image styles with their costs."""
        return [
            {
                "style": style.value,
                "name": self._get_style_display_name(style),
                "description": self._get_style_description(style),
                "cost": self.get_image_cost(style),
                "aspect_ratio": STYLE_PROMPT_TEMPLATES[style]["aspect_ratio"],
            }
            for style in ImageStyle
        ]
    
    async def get_user_history(
        self,
        user_id: str,
        db: AsyncSession,
        character_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get user's image generation history.
        
        Args:
            user_id: User ID
            db: Database session
            character_id: Optional filter by character
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of image history records
        """
        from app.models.database.image_models import GeneratedImage
        
        query = select(GeneratedImage).where(
            and_(
                GeneratedImage.user_id == user_id,
                GeneratedImage.is_deleted == False,
            )
        )
        
        if character_id:
            query = query.where(GeneratedImage.character_id == character_id)
        
        query = query.order_by(desc(GeneratedImage.created_at))
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        images = result.scalars().all()
        
        return [
            {
                "image_id": img.image_id,
                "character_id": img.character_id,
                "image_url": img.image_url,
                "thumbnail_url": img.thumbnail_url,
                "style": img.style,
                "generation_type": img.generation_type,
                "cost_credits": img.cost_credits,
                "is_free": img.is_free,
                "created_at": img.created_at.isoformat(),
            }
            for img in images
        ]
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _build_prompt(
        self,
        user_prompt: str,
        style: ImageStyle,
        character_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the final prompt from components."""
        # Get character appearance
        char_template = CHARACTER_APPEARANCE_TEMPLATES.get(
            character_id, CHARACTER_APPEARANCE_TEMPLATES["default"]
        )
        character_desc = (
            f"{char_template['base']} with {char_template['hair']}, "
            f"{char_template['eyes']}, {char_template['skin']}, "
            f"{char_template['style']}"
        )
        
        # Get style template
        style_template = STYLE_PROMPT_TEMPLATES.get(style, STYLE_PROMPT_TEMPLATES[ImageStyle.SELFIE])
        
        # Build base prompt
        base_prompt = style_template["base"].format(character_desc=character_desc)
        
        # Add modifiers
        modifiers = ", ".join(style_template["modifiers"])
        
        # Add user prompt if provided
        if user_prompt:
            final_prompt = f"{base_prompt}, {user_prompt}, {modifiers}"
        else:
            final_prompt = f"{base_prompt}, {modifiers}"
        
        # Add context-based enhancements
        if context:
            if context.get("mood"):
                final_prompt += f", {context['mood']} expression"
            if context.get("is_gift"):
                final_prompt += ", personal and intimate feeling"
            if context.get("intimacy_level", 0) >= 50:
                final_prompt += ", warm affectionate look"
        
        return final_prompt
    
    async def _generate_real_image(
        self,
        final_prompt: str,
        aspect_ratio: str = "1:1",
        n: int = 1,
    ) -> ImageGenerationResult:
        """Call the real xAI API to generate image."""
        if not self.api_key:
            logger.error("XAI_API_KEY not configured")
            return ImageGenerationResult(
                success=False,
                image_id="",
                image_url="",
                error="API key not configured",
            )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "prompt": final_prompt,
            "n": min(n, 10),  # Max 10 images per request
            "response_format": "url",  # Get URL instead of base64
        }
        
        # Add aspect ratio if not 1:1
        if aspect_ratio != "1:1":
            payload["aspect_ratio"] = aspect_ratio
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json=payload,
                )
                
                if resp.status_code != 200:
                    error_msg = f"API error: {resp.status_code} - {resp.text}"
                    logger.error(error_msg)
                    return ImageGenerationResult(
                        success=False,
                        image_id="",
                        image_url="",
                        error=error_msg,
                    )
                
                data = resp.json()
                
                # Extract first image
                if "data" in data and len(data["data"]) > 0:
                    image_data = data["data"][0]
                    image_url = image_data.get("url", "")
                    
                    return ImageGenerationResult(
                        success=True,
                        image_id=str(uuid.uuid4()),
                        image_url=image_url,
                        final_prompt=final_prompt,
                        model_used=self.model,
                        aspect_ratio=aspect_ratio,
                    )
                else:
                    return ImageGenerationResult(
                        success=False,
                        image_id="",
                        image_url="",
                        error="No image data in response",
                    )
                    
        except httpx.TimeoutException:
            logger.error("Image generation timed out")
            return ImageGenerationResult(
                success=False,
                image_id="",
                image_url="",
                error="Request timed out",
            )
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return ImageGenerationResult(
                success=False,
                image_id="",
                image_url="",
                error=str(e),
            )
    
    async def _generate_mock_image(
        self,
        final_prompt: str,
        style: ImageStyle,
        aspect_ratio: str = "1:1",
    ) -> ImageGenerationResult:
        """Generate a mock/placeholder image for development."""
        # Parse aspect ratio for dimensions
        dimensions = {
            "1:1": "512x512",
            "4:3": "640x480",
            "3:4": "480x640",
            "16:9": "640x360",
            "9:16": "360x640",
        }
        size = dimensions.get(aspect_ratio, "512x512")
        
        # Generate placeholder URL with style indicator
        style_colors = {
            ImageStyle.SELFIE: "FF6B6B/FFFFFF",      # Coral
            ImageStyle.LIFESTYLE: "4ECDC4/FFFFFF",   # Teal
            ImageStyle.ARTISTIC: "9B59B6/FFFFFF",    # Purple
            ImageStyle.PORTRAIT: "3498DB/FFFFFF",    # Blue
            ImageStyle.CASUAL: "2ECC71/FFFFFF",      # Green
            ImageStyle.ROMANTIC: "E91E63/FFFFFF",    # Pink
            ImageStyle.PLAYFUL: "F39C12/FFFFFF",     # Orange
            ImageStyle.ELEGANT: "1A1A2E/E94560",     # Dark
        }
        colors = style_colors.get(style, "1a1a2e/e94560")
        
        # Create placeholder URL
        style_name = style.value.replace("_", "+")
        mock_url = f"https://placehold.co/{size}/{colors}?text={style_name}+Photo"
        
        image_id = str(uuid.uuid4())
        
        logger.info(f"Generated mock image: {image_id} (style: {style.value})")
        
        return ImageGenerationResult(
            success=True,
            image_id=image_id,
            image_url=mock_url,
            thumbnail_url=f"https://placehold.co/150x150/{colors}?text=thumb",
            final_prompt=final_prompt,
            model_used="mock",
            aspect_ratio=aspect_ratio,
        )
    
    async def _record_generation(
        self,
        db: AsyncSession,
        user_id: str,
        character_id: str,
        result: ImageGenerationResult,
        generation_type: GenerationType,
        style: ImageStyle,
        original_prompt: str,
    ) -> None:
        """Record the generation to database."""
        try:
            from app.models.database.image_models import GeneratedImage
            
            record = GeneratedImage(
                image_id=result.image_id,
                user_id=user_id,
                character_id=character_id,
                generation_type=generation_type.value,
                style=style.value,
                original_prompt=original_prompt,
                final_prompt=result.final_prompt,
                image_url=result.image_url,
                thumbnail_url=result.thumbnail_url,
                aspect_ratio=result.aspect_ratio,
                cost_credits=result.cost_credits,
                is_free=result.is_free,
                model_used=result.model_used,
            )
            
            db.add(record)
            await db.commit()
            
            logger.info(f"Recorded image generation: {result.image_id}")
            
        except Exception as e:
            logger.error(f"Failed to record image generation: {e}")
            await db.rollback()
    
    def _get_style_display_name(self, style: ImageStyle) -> str:
        """Get display name for style."""
        names = {
            ImageStyle.SELFIE: "自拍",
            ImageStyle.LIFESTYLE: "生活照",
            ImageStyle.ARTISTIC: "艺术风格",
            ImageStyle.PORTRAIT: "肖像",
            ImageStyle.CASUAL: "日常",
            ImageStyle.ROMANTIC: "浪漫",
            ImageStyle.PLAYFUL: "俏皮",
            ImageStyle.ELEGANT: "优雅",
        }
        return names.get(style, style.value)
    
    def _get_style_description(self, style: ImageStyle) -> str:
        """Get description for style."""
        descriptions = {
            ImageStyle.SELFIE: "手机自拍风格，亲密自然",
            ImageStyle.LIFESTYLE: "日常生活场景，真实自然",
            ImageStyle.ARTISTIC: "艺术插画风格，创意独特",
            ImageStyle.PORTRAIT: "专业肖像照，精致优美",
            ImageStyle.CASUAL: "休闲日常，轻松随意",
            ImageStyle.ROMANTIC: "浪漫氛围，温馨甜蜜",
            ImageStyle.PLAYFUL: "活泼俏皮，充满活力",
            ImageStyle.ELEGANT: "优雅高贵，气质出众",
        }
        return descriptions.get(style, "")


# Singleton instance
_image_service: Optional[ImageGenerationService] = None


def get_image_service() -> ImageGenerationService:
    """Get or create the image service singleton."""
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService()
    return _image_service

"""
Image Generation API Routes
============================

API endpoints for image generation:
- POST /api/v1/images/generate - Generate a new image
- GET /api/v1/images/history - Get user's image history
- GET /api/v1/images/styles - Get available styles and costs
- GET /api/v1/images/{image_id} - Get single image details

Author: Luna AI
Date: January 2026
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import UserContext
from app.services.image_service import (
    get_image_service,
    ImageStyle,
    GenerationType,
    ImageGenerationResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["Images"])

# Default user ID for demo mode
DEMO_USER_ID = "demo-user-123"


def get_user_from_request(request: Request) -> UserContext:
    """Extract user from request state (set by auth middleware)"""
    user = getattr(request.state, "user", None)
    if user:
        return user
    # Fallback to demo user
    return UserContext(
        user_id=DEMO_USER_ID,
        email="demo@example.com",
        subscription_tier="free",
        is_subscribed=False,
    )


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ImageGenerateRequest(BaseModel):
    """Request to generate an image"""
    character_id: str = Field(..., description="Character ID to generate image for")
    style: str = Field(default="selfie", description="Image style (selfie, lifestyle, artistic, etc.)")
    prompt: Optional[str] = Field(default=None, max_length=500, description="Optional custom prompt/request")
    aspect_ratio: str = Field(default="1:1", description="Image aspect ratio")
    
    class Config:
        json_schema_extra = {
            "example": {
                "character_id": "char_luna_001",
                "style": "selfie",
                "prompt": "wearing a cute summer dress",
                "aspect_ratio": "1:1"
            }
        }


class ImageGenerateResponse(BaseModel):
    """Response from image generation"""
    success: bool
    image_id: str
    image_url: str
    thumbnail_url: Optional[str] = None
    style: str
    cost_credits: int
    is_free: bool = False
    remaining_credits: Optional[float] = None
    error: Optional[str] = None


class ImageHistoryItem(BaseModel):
    """Single image in history"""
    image_id: str
    character_id: str
    image_url: str
    thumbnail_url: Optional[str] = None
    style: str
    generation_type: str
    cost_credits: int
    is_free: bool
    created_at: str


class ImageHistoryResponse(BaseModel):
    """Response for image history"""
    images: List[ImageHistoryItem]
    total: int
    has_more: bool


class ImageStyleInfo(BaseModel):
    """Information about an image style"""
    style: str
    name: str
    description: str
    cost: int
    aspect_ratio: str


class StylesResponse(BaseModel):
    """Response for available styles"""
    styles: List[ImageStyleInfo]


class ImageCostResponse(BaseModel):
    """Response for image cost query"""
    style: str
    cost_credits: int
    user_balance: float
    can_afford: bool


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(
    request: ImageGenerateRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an image for a character.
    
    - Costs credits based on the style chosen
    - Users must have sufficient balance
    - Free tier users may have limited generations
    
    **Styles available:**
    - selfie: 自拍 (50 credits)
    - lifestyle: 生活照 (50 credits)
    - artistic: 艺术风格 (80 credits)
    - portrait: 肖像 (60 credits)
    - casual: 日常 (50 credits)
    - romantic: 浪漫 (70 credits)
    - playful: 俏皮 (50 credits)
    - elegant: 优雅 (70 credits)
    """
    user = get_user_from_request(req)
    service = get_image_service()
    
    # Validate style
    try:
        style = ImageStyle(request.style)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style: {request.style}. Available: {[s.value for s in ImageStyle]}"
        )
    
    # Check cost and balance
    cost = service.get_image_cost(style)
    
    # TODO: Get user balance from wallet service
    # For now, we'll proceed assuming user has enough credits
    # In production, add balance check here:
    # user_balance = await wallet_service.get_balance(user.user_id, db)
    # if user_balance < cost:
    #     raise HTTPException(status_code=402, detail="Insufficient credits")
    
    # Generate image
    result = await service.generate_image(
        prompt=request.prompt or "",
        style=style,
        character_id=request.character_id,
        user_id=user.user_id,
        generation_type=GenerationType.USER_REQUEST,
        db=db,
        aspect_ratio=request.aspect_ratio,
    )
    
    if not result.success:
        logger.error(f"Image generation failed: {result.error}")
        raise HTTPException(
            status_code=500,
            detail=result.error or "Image generation failed"
        )
    
    # TODO: Deduct credits from user wallet
    # await wallet_service.deduct_credits(user.user_id, cost, db, "image_generation")
    
    return ImageGenerateResponse(
        success=True,
        image_id=result.image_id,
        image_url=result.image_url,
        thumbnail_url=result.thumbnail_url,
        style=style.value,
        cost_credits=result.cost_credits,
        is_free=result.is_free,
        remaining_credits=None,  # TODO: Get from wallet
    )


@router.get("/history", response_model=ImageHistoryResponse)
async def get_image_history(
    req: Request,
    character_id: Optional[str] = Query(default=None, description="Filter by character"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's image generation history.
    
    - Sorted by most recent first
    - Can filter by character
    - Supports pagination
    """
    user = get_user_from_request(req)
    service = get_image_service()
    
    images = await service.get_user_history(
        user_id=user.user_id,
        db=db,
        character_id=character_id,
        limit=limit + 1,  # Get one extra to check has_more
        offset=offset,
    )
    
    has_more = len(images) > limit
    if has_more:
        images = images[:limit]
    
    return ImageHistoryResponse(
        images=[
            ImageHistoryItem(
                image_id=img["image_id"],
                character_id=img["character_id"],
                image_url=img["image_url"],
                thumbnail_url=img.get("thumbnail_url"),
                style=img["style"],
                generation_type=img["generation_type"],
                cost_credits=img["cost_credits"],
                is_free=img["is_free"],
                created_at=img["created_at"],
            )
            for img in images
        ],
        total=len(images),
        has_more=has_more,
    )


@router.get("/styles", response_model=StylesResponse)
async def get_available_styles():
    """
    Get all available image styles with their costs.
    
    No authentication required.
    """
    service = get_image_service()
    styles = service.get_available_styles()
    
    return StylesResponse(
        styles=[
            ImageStyleInfo(
                style=s["style"],
                name=s["name"],
                description=s["description"],
                cost=s["cost"],
                aspect_ratio=s["aspect_ratio"],
            )
            for s in styles
        ]
    )


@router.get("/cost", response_model=ImageCostResponse)
async def get_image_cost(
    req: Request,
    style: str = Query(default="selfie", description="Image style to check cost for"),
):
    """
    Get the cost for generating an image with a specific style.
    
    Returns whether the user can afford it.
    """
    user = get_user_from_request(req)
    service = get_image_service()
    
    # Validate style
    try:
        image_style = ImageStyle(style)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style: {style}"
        )
    
    cost = service.get_image_cost(image_style)
    
    # TODO: Get actual user balance from wallet service
    user_balance = 100.0  # Placeholder
    
    return ImageCostResponse(
        style=style,
        cost_credits=cost,
        user_balance=user_balance,
        can_afford=user_balance >= cost,
    )


# ============================================================================
# Character Gift Endpoint (Internal use)
# ============================================================================

class CharacterGiftRequest(BaseModel):
    """Request for character to send gift image"""
    character_id: str
    user_id: str
    intimacy_level: int = Field(default=1, ge=1, le=100)
    mood: str = Field(default="happy")


class CharacterGiftResponse(BaseModel):
    """Response for character gift"""
    success: bool
    image_id: str
    image_url: str
    style: str
    message: Optional[str] = None


@router.post("/gift", response_model=CharacterGiftResponse, include_in_schema=False)
async def create_character_gift(
    request: CharacterGiftRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal endpoint for character AI to send gift images.
    
    This is called by the chat service when the character decides
    to send a photo as a gift.
    
    Not exposed in public API docs.
    """
    service = get_image_service()
    
    result = await service.generate_character_gift(
        character_id=request.character_id,
        user_id=request.user_id,
        intimacy_level=request.intimacy_level,
        mood=request.mood,
        db=db,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error or "Gift generation failed"
        )
    
    # Generate a cute message based on intimacy level
    messages = {
        "low": "这是给你的小礼物～ 希望你喜欢！",
        "medium": "想你了，给你发张照片～",
        "high": "今天很开心，想把这一刻和你分享 ❤️",
    }
    
    if request.intimacy_level >= 70:
        message = messages["high"]
    elif request.intimacy_level >= 40:
        message = messages["medium"]
    else:
        message = messages["low"]
    
    return CharacterGiftResponse(
        success=True,
        image_id=result.image_id,
        image_url=result.image_url,
        style=result.aspect_ratio,  # Return style used
        message=message,
    )

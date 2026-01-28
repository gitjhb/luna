"""
Image Generation API Routes
"""

from fastapi import APIRouter, HTTPException
import os

from app.models.schemas import ImageGenerationRequest, ImageGenerationResponse
from app.services.image_service import ImageGenerationService

router = APIRouter(prefix="/image")

image_service = ImageGenerationService()

MOCK_MODE = os.getenv("MOCK_IMAGE", "true").lower() == "true"


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image using DALL-E 3.
    Costs 10 credits per image.
    """
    if MOCK_MODE:
        return ImageGenerationResponse(
            url="https://placehold.co/1024x1024/1a1a2e/e94560?text=Mock+Image",
            revised_prompt=request.prompt,
        )

    try:
        results = await image_service.generate(
            prompt=request.prompt,
            size=request.size,
            quality=request.quality,
            style=request.style,
        )
        return ImageGenerationResponse(
            url=results[0]["url"],
            revised_prompt=results[0]["revised_prompt"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/avatar")
async def generate_avatar(description: str, style: str = "anime"):
    """Generate a character avatar"""
    if MOCK_MODE:
        return {
            "url": f"https://placehold.co/512x512/1a1a2e/e94560?text={style}+Avatar",
            "description": description,
        }

    try:
        url = await image_service.generate_avatar(description, style)
        return {"url": url, "description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

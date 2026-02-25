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


@router.post("/generate", response_model=ImageGenerationResponse,
            summary="Generate AI image from text prompt",
            description="""
            Create high-quality AI-generated images using advanced text-to-image models.
            
            **Features:**
            - Powered by DALL-E 3 for photorealistic and artistic images
            - Support for multiple sizes and quality levels
            - Style options for different artistic approaches
            - Automatic prompt enhancement for better results
            
            **Cost:** 10 credits per image (Premium users get 50% discount)
            
            **Supported Sizes:**
            - `1024x1024`: Square format (default, best for portraits)
            - `1792x1024`: Landscape format (great for backgrounds)
            - `1024x1792`: Portrait format (ideal for character art)
            
            **Quality Options:**
            - `standard`: Faster generation, good quality
            - `hd`: Higher detail, slower generation, premium quality
            
            **Style Options:**
            - `vivid`: More artistic and creative interpretation
            - `natural`: More realistic and photographic style
            
            **Content Policy:**
            Images must comply with AI safety guidelines. Adult content requires Premium subscription.
            
            **Generation Time:** 15-45 seconds depending on complexity and queue
            
            **Example Prompts:**
            - "A cute anime girl with long pink hair in a school uniform"
            - "Cyberpunk cityscape at night with neon lights"
            - "Cozy cafe interior with warm lighting and books"
            - "Fantasy landscape with mountains and magical aurora"
            """,
            responses={
                200: {"description": "Image generated successfully with download URL"},
                400: {"description": "Invalid prompt or parameters"},
                402: {"description": "Insufficient credits for image generation"},
                429: {"description": "Rate limit exceeded or generation queue full"},
                500: {"description": "Image generation service error"}
            })
async def generate_image(request: ImageGenerationRequest):
    """Generate high-quality AI image from text description."""
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

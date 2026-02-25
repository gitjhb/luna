"""
Voice API Routes - TTS (豆包) and STT
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import os

from app.models.schemas import TTSRequest, VoiceListResponse
from app.services.voice_service import DoubaoTTSService

router = APIRouter(prefix="/voice")

tts_service = DoubaoTTSService()

MOCK_MODE = os.getenv("MOCK_TTS", "true").lower() == "true"


@router.post("/tts",
            summary="Convert text to speech",
            description="""
            Generate natural-sounding voice audio from text using advanced TTS technology.
            
            **Features:**
            - High-quality neural voices with emotion support
            - Adjustable speech speed (0.2x to 3.0x)
            - Multiple voice options for different characters
            - Emotion modulation for expressive speech
            
            **Supported Languages:**
            - Chinese (Mandarin) with various regional accents
            - English with native pronunciation
            - Japanese for anime-style character voices
            
            **Available Voices:**
            - **灿灿**: Sweet, gentle female voice (default)
            - **晓梦**: Energetic, youthful tone
            - **云希**: Mature, sophisticated style
            - **妙妙**: Playful, cute character voice
            
            **Emotions:**
            - `happy`: Cheerful and upbeat tone
            - `sad`: Melancholic and softer delivery
            - `excited`: High energy and enthusiasm  
            - `neutral`: Balanced, natural speech (default)
            - `romantic`: Warm, intimate tone
            
            **Cost:** 2-5 credits depending on text length
            
            **Output Format:** MP3 audio (128kbps, 22kHz)
            **Max Length:** 2000 characters per request
            **Generation Time:** 2-8 seconds depending on text length
            
            **Usage Tips:**
            - Add punctuation for natural pauses
            - Use shorter sentences for better pronunciation
            - Emojis and emoticons may affect voice emotion
            """,
            responses={
                200: {
                    "description": "Generated audio file",
                    "content": {"audio/mpeg": {"schema": {"type": "string", "format": "binary"}}}
                },
                400: {"description": "Text too long or invalid parameters"},
                402: {"description": "Insufficient credits"},
                500: {"description": "TTS service error"}
            })
async def text_to_speech(request: TTSRequest):
    """Convert text to natural-sounding speech audio."""
    if MOCK_MODE:
        # Return empty audio in mock mode
        return Response(
            content=b"",
            media_type="audio/mpeg",
            headers={"X-Mock": "true"},
        )

    try:
        audio = await tts_service.synthesize_long(
            text=request.text,
            voice=request.voice,
            speed_ratio=request.speed,
            emotion=request.emotion,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(content=audio, media_type="audio/mpeg")


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """List available voice options"""
    return VoiceListResponse(voices=tts_service.list_voices())

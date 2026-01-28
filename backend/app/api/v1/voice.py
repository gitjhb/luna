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


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using 豆包 TTS.
    Returns audio/mpeg.
    """
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

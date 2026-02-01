"""
Emotion API Routes
==================

Endpoints for character emotion state (VIP feature).
"""

from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

router = APIRouter(prefix="/emotion")

MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"


class EmotionStatusResponse(BaseModel):
    user_id: str
    character_id: str
    emotional_state: str
    emotion_intensity: float
    emotion_reason: Optional[str]
    times_angered: int
    times_hurt: int
    emotion_changed_at: Optional[datetime]


# Mock emotion data for development
_MOCK_EMOTIONS = {}


def _get_mock_emotion(user_id: str, character_id: str) -> dict:
    """Get or create mock emotion data."""
    key = f"{user_id}:{character_id}"
    if key not in _MOCK_EMOTIONS:
        _MOCK_EMOTIONS[key] = {
            "emotional_state": "neutral",
            "emotion_intensity": 0.0,
            "emotion_reason": None,
            "times_angered": 0,
            "times_hurt": 0,
            "emotion_changed_at": None,
        }
    return _MOCK_EMOTIONS[key]


@router.get("/{character_id}", response_model=EmotionStatusResponse)
async def get_emotion_status(character_id: UUID, request: Request):
    """
    Get current emotion status with a character.
    
    This is a VIP-only feature. Non-VIP users will receive 403.
    For testing: guest users and demo mode always have access.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
        is_vip = True  # Demo mode: always VIP
    else:
        user_id = str(user.user_id)
        
        # Testing bypass: guest users, demo user, and MOCK_MODE always have access
        if user_id.startswith("guest-") or user_id.startswith("demo-") or MOCK_MODE:
            is_vip = True
        else:
            # Use unified subscription service to check VIP status
            from app.services.subscription_service import subscription_service
            is_vip = await subscription_service.is_subscribed(user_id)
    
    # Check VIP status
    if not is_vip:
        raise HTTPException(
            status_code=403,
            detail="情绪状态是 VIP 专属功能，升级后可查看角色的真实情绪。"
        )
    
    char_id = str(character_id)
    
    # Use emotion engine v2
    try:
        from app.services.emotion_engine_v2 import emotion_engine
        
        score = await emotion_engine.get_score(user_id, char_id)
        state = emotion_engine.score_to_state(score)
        
        # Map state to API format
        state_mapping = {
            "loving": "loving", "happy": "happy", "content": "happy",
            "neutral": "neutral", "annoyed": "annoyed",
            "angry": "angry", "cold_war": "cold", "blocked": "blocked",
        }
        emotional_state = state_mapping.get(state.value, "neutral")
        
        return EmotionStatusResponse(
            user_id=user_id,
            character_id=char_id,
            emotional_state=emotional_state,
            emotion_intensity=abs(score),
            emotion_reason=None,
            times_angered=0,
            times_hurt=0,
            emotion_changed_at=None,
        )
    except Exception as e:
        import logging
        logging.warning(f"Failed to get emotion from emotion_engine_v2: {e}")
    
    if MOCK_MODE:
        emotion = _get_mock_emotion(user_id, char_id)
    else:
        # Fallback: Database mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.emotion_models import UserCharacterEmotion
        
        async with get_db() as db:
            result = await db.execute(
                select(UserCharacterEmotion).where(
                    UserCharacterEmotion.user_id == user_id,
                    UserCharacterEmotion.character_id == char_id
                )
            )
            db_emotion = result.scalar_one_or_none()
            
            if db_emotion:
                emotion = {
                    "emotional_state": db_emotion.emotional_state,
                    "emotion_intensity": db_emotion.emotion_intensity,
                    "emotion_reason": db_emotion.emotion_reason,
                    "times_angered": db_emotion.times_angered,
                    "times_hurt": db_emotion.times_hurt,
                    "emotion_changed_at": db_emotion.emotion_changed_at,
                }
            else:
                # Default neutral state
                emotion = {
                    "emotional_state": "neutral",
                    "emotion_intensity": 0.0,
                    "emotion_reason": None,
                    "times_angered": 0,
                    "times_hurt": 0,
                    "emotion_changed_at": None,
                }
    
    return EmotionStatusResponse(
        user_id=user_id,
        character_id=char_id,
        emotional_state=emotion["emotional_state"],
        emotion_intensity=emotion["emotion_intensity"],
        emotion_reason=emotion["emotion_reason"],
        times_angered=emotion["times_angered"],
        times_hurt=emotion["times_hurt"],
        emotion_changed_at=emotion["emotion_changed_at"],
    )


@router.post("/{character_id}/update")
async def update_emotion(character_id: UUID, request: Request):
    """
    Update emotion based on interaction (internal use, called by chat service).
    """
    # This would be called internally by the chat service
    # For now, just return success
    return {"success": True, "message": "Emotion update endpoint - implement with chat service"}


@router.post("/{character_id}/reset")
async def reset_emotion(character_id: UUID, request: Request):
    """
    Reset emotion to neutral (costs credits or requires gift).
    Used to break out of cold war state.
    """
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    char_id = str(character_id)
    
    try:
        from app.services.emotion_engine_v2 import emotion_engine
        
        # Reset to neutral (score = 0)
        new_score = await emotion_engine.reset_score(user_id, char_id)
        new_state = emotion_engine.score_to_state(new_score)
        
        return {
            "success": True,
            "message": "情绪已重置，冷战解除！",
            "new_state": new_state.value,
            "new_score": new_score,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

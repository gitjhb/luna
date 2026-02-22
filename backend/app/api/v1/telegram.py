"""
Telegram Integration API - Full ChatService Pipeline

Uses the same chat logic as iOS:
- Persistent user/session in database
- Full V4 chat pipeline with memory, intimacy, emotions
- Shared character personality system
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import uuid4
import os
import logging

from sqlalchemy import select

from app.core.database import get_db
from app.models.database.user_models import User
from app.models.database.billing_models import UserWallet
from app.services.chat_repository import chat_repo
from app.services.v4.chat_pipeline_v4 import chat_pipeline_v4, ChatRequestV4
from app.api.v1.characters import CHARACTERS, get_character_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Default character for Telegram bot
DEFAULT_CHARACTER_ID = "luna"


class TelegramChatRequest(BaseModel):
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    message: str


class TelegramChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    is_new_user: bool = False
    emotion: Optional[int] = None
    intimacy_level: Optional[int] = None


async def get_or_create_telegram_user(
    telegram_id: str,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Get or create a Luna user for a Telegram user.
    
    Returns:
        tuple of (user_id, is_new_user)
    """
    firebase_uid = f"telegram_{telegram_id}"
    email = f"telegram_{telegram_id}@telegram.luna"
    display_name = first_name or username or f"Telegram User {telegram_id}"
    
    async with get_db() as db:
        # Check if user exists
        result = await db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update last login
            user.last_login_at = datetime.utcnow()
            await db.commit()
            return user.user_id, False
        
        # Create new user
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            is_subscribed=False,
            subscription_tier="free",
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()  # Get user_id
        
        # Create wallet with default credits
        from app.config import settings
        wallet = UserWallet(
            user_id=user.user_id,
            free_credits=settings.DAILY_REFRESH_AMOUNT,
            purchased_credits=0.0,
            total_credits=settings.DAILY_REFRESH_AMOUNT,
            daily_refresh_amount=settings.DAILY_REFRESH_AMOUNT,
        )
        db.add(wallet)
        
        await db.commit()
        
        logger.info(f"🆕 Created Telegram user: {user.user_id} (telegram: {telegram_id})")
        return user.user_id, True


async def get_or_create_session(
    user_id: str,
    character_id: str = DEFAULT_CHARACTER_ID,
) -> tuple[str, bool]:
    """
    Get or create a chat session for user + character.
    
    Returns:
        tuple of (session_id, is_new_session)
    """
    # Get character info
    character = get_character_by_id(character_id)
    if not character:
        # Fallback to first character if not found
        character = CHARACTERS[0] if CHARACTERS else {
            "character_id": "luna",
            "name": "Luna",
            "avatar_url": None,
            "background_url": None,
        }
    
    # Check for existing session
    existing = await chat_repo.get_session_by_character(user_id, character_id)
    if existing:
        return existing["session_id"], False
    
    # Create new session
    session = await chat_repo.create_session(
        user_id=user_id,
        character_id=character_id,
        character_name=character.get("name", "Luna"),
        character_avatar=character.get("avatar_url"),
        character_background=character.get("background_url"),
    )
    
    # Insert greeting if character has one
    greeting = character.get("greeting")
    if greeting:
        await chat_repo.add_message(
            session_id=session["session_id"],
            role="assistant",
            content=greeting,
            tokens_used=0,
        )
        logger.info(f"💬 Inserted greeting for new session: {session['session_id']}")
    
    logger.info(f"🆕 Created session: {session['session_id']} for user {user_id}")
    return session["session_id"], True


async def get_intimacy_level(user_id: str, character_id: str) -> int:
    """Get current intimacy level for user + character."""
    try:
        from app.services.intimacy_service import intimacy_service
        data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
        return data.get("current_level", 1)
    except Exception as e:
        logger.warning(f"Failed to get intimacy level: {e}")
        return 1


@router.post("/chat", response_model=TelegramChatResponse)
async def telegram_chat(request: TelegramChatRequest):
    """
    Telegram chat endpoint using full ChatService pipeline.
    
    Same logic as iOS app:
    - Persistent user/session in database
    - Memory system, intimacy, emotions
    - Full character personality
    """
    logger.info(f"📱 Telegram: {request.telegram_id} ({request.first_name}): {request.message[:50]}...")
    
    try:
        # 1. Get or create user
        user_id, is_new_user = await get_or_create_telegram_user(
            telegram_id=request.telegram_id,
            username=request.username,
            first_name=request.first_name,
        )
        
        # 2. Get or create session
        session_id, is_new_session = await get_or_create_session(
            user_id=user_id,
            character_id=DEFAULT_CHARACTER_ID,
        )
        
        # 3. Get current intimacy level
        intimacy_level = await get_intimacy_level(user_id, DEFAULT_CHARACTER_ID)
        
        # 4. Build V4 request
        v4_request = ChatRequestV4(
            user_id=user_id,
            character_id=DEFAULT_CHARACTER_ID,
            session_id=session_id,
            message=request.message,
            intimacy_level=intimacy_level,
            client_message_id=str(uuid4()),  # Generate message ID
        )
        
        # 5. Process through full pipeline
        v4_response = await chat_pipeline_v4.process_message(v4_request)
        
        # 6. Extract response data
        reply = v4_response.content
        emotion = v4_response.extra_data.get("user_state", {}).get("emotion", 0) if v4_response.extra_data else 0
        level = v4_response.extra_data.get("user_state", {}).get("intimacy_level", 1) if v4_response.extra_data else 1
        
        logger.info(f"📱 Luna → {request.telegram_id}: {reply[:50]}... (emotion: {emotion}, level: {level})")
        
        return TelegramChatResponse(
            reply=reply,
            user_id=user_id,
            session_id=session_id,
            is_new_user=is_new_user,
            emotion=emotion,
            intimacy_level=level,
        )
        
    except Exception as e:
        logger.error(f"❌ Telegram chat error: {e}", exc_info=True)
        
        # Return a friendly error response
        return TelegramChatResponse(
            reply="抱歉，我走神了... 再说一遍好吗？💭",
            user_id=f"tg_{request.telegram_id}",
            session_id="error",
            is_new_user=False,
        )


@router.get("/health")
async def telegram_health():
    """Health check with pipeline status."""
    # Count active telegram users
    telegram_user_count = 0
    try:
        async with get_db() as db:
            from sqlalchemy import func
            result = await db.execute(
                select(func.count(User.user_id)).where(
                    User.firebase_uid.like("telegram_%")
                )
            )
            telegram_user_count = result.scalar() or 0
    except Exception as e:
        logger.warning(f"Failed to count telegram users: {e}")
    
    return {
        "status": "ok",
        "pipeline": "v4",
        "telegram_users": telegram_user_count,
        "default_character": DEFAULT_CHARACTER_ID,
    }


@router.post("/clear/{telegram_id}")
async def clear_history(telegram_id: str):
    """Clear conversation history for a Telegram user."""
    try:
        firebase_uid = f"telegram_{telegram_id}"
        
        async with get_db() as db:
            # Find user
            result = await db.execute(
                select(User).where(User.firebase_uid == firebase_uid)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Find session
            session = await chat_repo.get_session_by_character(
                user.user_id, DEFAULT_CHARACTER_ID
            )
            
            if not session:
                return {"success": False, "message": "No session found"}
            
            # Delete session (cascades to messages)
            await chat_repo.delete_session(session["session_id"])
            
            logger.info(f"🗑️ Cleared history for telegram user: {telegram_id}")
            return {"success": True, "message": "History cleared"}
            
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        return {"success": False, "message": str(e)}


@router.get("/user/{telegram_id}")
async def get_telegram_user_info(telegram_id: str):
    """Get info about a Telegram user (for debugging)."""
    try:
        firebase_uid = f"telegram_{telegram_id}"
        
        async with get_db() as db:
            result = await db.execute(
                select(User).where(User.firebase_uid == firebase_uid)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"exists": False}
            
            # Get session info
            session = await chat_repo.get_session_by_character(
                user.user_id, DEFAULT_CHARACTER_ID
            )
            
            # Get intimacy
            intimacy_level = await get_intimacy_level(user.user_id, DEFAULT_CHARACTER_ID)
            
            # Get emotion
            emotion = 0
            try:
                from app.services.emotion_engine_v2 import emotion_engine
                emotion = await emotion_engine.get_score(user.user_id, DEFAULT_CHARACTER_ID)
            except:
                pass
            
            return {
                "exists": True,
                "user_id": user.user_id,
                "display_name": user.display_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "has_session": session is not None,
                "session_id": session["session_id"] if session else None,
                "total_messages": session.get("total_messages", 0) if session else 0,
                "intimacy_level": intimacy_level,
                "emotion": int(emotion),
            }
            
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return {"exists": False, "error": str(e)}

"""
Telegram Integration API

Thin endpoint for Telegram bot to call Luna backend.
Handles: user mapping, session management, chat.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os
import logging
import httpx

from app.services.chat_service import ChatService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Bot token for verification
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "5056039560")

# Default character for Telegram (single character strategy)
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


# In-memory mapping (use DB in production)
_telegram_to_luna: dict = {}
_telegram_sessions: dict = {}


async def get_or_create_luna_user(telegram_id: str, username: str = None, first_name: str = None) -> tuple[str, bool]:
    """
    Get or create Luna user_id from telegram_id.
    Returns (user_id, is_new)
    """
    # Check cache first
    if telegram_id in _telegram_to_luna:
        return _telegram_to_luna[telegram_id], False
    
    # Check database
    async with get_db() as db:
        try:
            from sqlalchemy import text
            result = await db.execute(
                text("SELECT user_id FROM users WHERE telegram_id = :tid"),
                {"tid": telegram_id}
            )
            row = result.fetchone()
            
            if row:
                user_id = row[0]
                _telegram_to_luna[telegram_id] = user_id
                return user_id, False
            
            # Create new user
            import uuid
            user_id = f"tg_{telegram_id}"
            
            await db.execute(
                text("""
                    INSERT INTO users (user_id, telegram_id, display_name, created_at)
                    VALUES (:uid, :tid, :name, NOW())
                    ON CONFLICT (telegram_id) DO UPDATE SET display_name = :name
                """),
                {"uid": user_id, "tid": telegram_id, "name": first_name or username or "Telegram User"}
            )
            await db.commit()
            
            _telegram_to_luna[telegram_id] = user_id
            logger.info(f"Created new Luna user {user_id} for Telegram {telegram_id}")
            return user_id, True
            
        except Exception as e:
            logger.error(f"DB error in get_or_create_luna_user: {e}")
            # Fallback to simple mapping
            user_id = f"tg_{telegram_id}"
            _telegram_to_luna[telegram_id] = user_id
            return user_id, True


async def get_or_create_session(user_id: str, character_id: str = DEFAULT_CHARACTER_ID) -> str:
    """
    Get or create chat session for user + character.
    """
    cache_key = f"{user_id}:{character_id}"
    
    if cache_key in _telegram_sessions:
        return _telegram_sessions[cache_key]
    
    # Check database for existing session
    async with get_db() as db:
        try:
            from sqlalchemy import text
            result = await db.execute(
                text("""
                    SELECT session_id FROM chat_sessions 
                    WHERE user_id = :uid AND character_id = :cid
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"uid": user_id, "cid": character_id}
            )
            row = result.fetchone()
            
            if row:
                session_id = row[0]
                _telegram_sessions[cache_key] = session_id
                return session_id
            
            # Create new session
            import uuid
            session_id = str(uuid.uuid4())
            
            await db.execute(
                text("""
                    INSERT INTO chat_sessions (session_id, user_id, character_id, character_name, created_at)
                    VALUES (:sid, :uid, :cid, :cname, NOW())
                """),
                {"sid": session_id, "uid": user_id, "cid": character_id, "cname": "Luna"}
            )
            await db.commit()
            
            _telegram_sessions[cache_key] = session_id
            logger.info(f"Created new session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"DB error in get_or_create_session: {e}")
            # Fallback
            import uuid
            session_id = str(uuid.uuid4())
            _telegram_sessions[cache_key] = session_id
            return session_id


@router.post("/chat", response_model=TelegramChatResponse)
async def telegram_chat(request: TelegramChatRequest):
    """
    Main Telegram chat endpoint.
    
    1. Maps telegram_id → Luna user
    2. Gets/creates session
    3. Calls chat service
    4. Returns reply
    """
    logger.info(f"📱 Telegram chat from {request.telegram_id}: {request.message[:50]}...")
    
    # Get or create user
    user_id, is_new = await get_or_create_luna_user(
        request.telegram_id,
        request.username,
        request.first_name
    )
    
    # Get or create session
    session_id = await get_or_create_session(user_id)
    
    # Call chat service
    try:
        chat_service = ChatService()
        
        # Build chat request
        from app.models.schemas import ChatCompletionRequest
        chat_request = ChatCompletionRequest(
            session_id=session_id,
            message=request.message,
        )
        
        # Get response (simplified - you may need to adapt based on ChatService API)
        response = await chat_service.process_message(
            session_id=session_id,
            user_id=user_id,
            message=request.message,
            character_id=DEFAULT_CHARACTER_ID,
        )
        
        reply = response.get("content", response.get("reply", "..."))
        
        return TelegramChatResponse(
            reply=reply,
            user_id=user_id,
            session_id=session_id,
            is_new_user=is_new,
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback response
        return TelegramChatResponse(
            reply="抱歉，我现在有点迷糊... 再跟我说一遍？",
            user_id=user_id,
            session_id=session_id,
            is_new_user=is_new,
        )


@router.get("/health")
async def telegram_health():
    """Health check for Telegram integration"""
    return {
        "status": "ok",
        "character": DEFAULT_CHARACTER_ID,
        "cached_users": len(_telegram_to_luna),
        "cached_sessions": len(_telegram_sessions),
    }


@router.post("/link")
async def link_telegram_to_email(telegram_id: str, email: str):
    """
    Link Telegram account to email (for Pro status).
    Called when user does /link email@example.com
    """
    async with get_db() as db:
        try:
            from sqlalchemy import text
            
            # Find user by email
            result = await db.execute(
                text("SELECT user_id, is_pro FROM users WHERE email = :email"),
                {"email": email}
            )
            email_user = result.fetchone()
            
            if not email_user:
                return {"success": False, "message": "Email not found. Please sign up first."}
            
            # Update telegram_id on that user
            await db.execute(
                text("UPDATE users SET telegram_id = :tid WHERE email = :email"),
                {"tid": telegram_id, "email": email}
            )
            await db.commit()
            
            # Update cache
            _telegram_to_luna[telegram_id] = email_user[0]
            
            is_pro = email_user[1] if len(email_user) > 1 else False
            
            return {
                "success": True,
                "message": "Account linked!" + (" Welcome back, Pro member! 💎" if is_pro else ""),
                "is_pro": is_pro,
            }
            
        except Exception as e:
            logger.error(f"Link error: {e}")
            return {"success": False, "message": "Link failed. Try again later."}

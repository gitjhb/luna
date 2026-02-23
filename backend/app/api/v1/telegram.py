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
# Luna 的正确 character_id (与 characters.py 一致)
DEFAULT_CHARACTER_ID = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"


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
        default_credits = settings.DAILY_CREDITS_FREE
        wallet = UserWallet(
            user_id=user.user_id,
            free_credits=default_credits,
            purchased_credits=0.0,
            total_credits=default_credits,
            daily_refresh_amount=default_credits,
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


# ========== Telegram Bot Webhook ==========
import httpx
from app.config import settings


async def send_telegram_message(chat_id: str, text: str):
    """Send a message via Telegram Bot API."""
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                logger.error(f"Telegram API error: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


async def send_chat_action(chat_id: str, action: str = "typing"):
    """Send chat action (typing indicator) via Telegram Bot API."""
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendChatAction"
    payload = {"chat_id": chat_id, "action": action}
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5.0)
            return True
    except:
        return False


class TelegramUpdate(BaseModel):
    """Telegram webhook update payload."""
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None


@router.post("/webhook")
async def telegram_webhook(update: TelegramUpdate):
    """
    Telegram Bot Webhook endpoint.
    
    Receives updates from Telegram and processes them through Luna's chat pipeline.
    """
    logger.info(f"📥 Telegram webhook: update_id={update.update_id}")
    
    # Handle callback queries (button clicks)
    if update.callback_query:
        # TODO: Handle button callbacks
        return {"ok": True}
    
    # Handle messages
    if not update.message:
        return {"ok": True}
    
    message = update.message
    chat_id = str(message.get("chat", {}).get("id", ""))
    user_id = str(message.get("from", {}).get("id", ""))
    username = message.get("from", {}).get("username")
    first_name = message.get("from", {}).get("first_name")
    text = message.get("text", "")
    
    if not chat_id or not user_id:
        return {"ok": True}
    
    # Handle /start command
    if text == "/start":
        character = get_character_by_id(DEFAULT_CHARACTER_ID)
        greeting = character.get("greeting", "你好呀！我是Luna~ 💕") if character else "你好呀！我是Luna~ 💕"
        await send_telegram_message(chat_id, greeting)
        return {"ok": True}
    
    # Handle /clear command
    if text == "/clear":
        await clear_history(user_id)
        await send_telegram_message(chat_id, "记忆已清除，让我们重新开始吧~ 💫")
        return {"ok": True}
    
    # Handle /help command
    if text == "/help":
        help_text = """💕 Luna AI 伴侣

可用命令：
/start - 开始聊天
/me - 查看Luna记住的关于你
/link <邮箱> - 关联Luna App账号
/clear - 清除聊天记录
/help - 显示帮助

直接发消息就可以和我聊天啦~ 💬"""
        await send_telegram_message(chat_id, help_text)
        return {"ok": True}
    
    # Handle /me command - show what Luna remembers
    if text == "/me":
        try:
            user_info = await get_telegram_user_info(user_id)
            if not user_info.get("exists"):
                await send_telegram_message(chat_id, "我们才刚认识，多聊聊我就能记住你啦~ 💕")
                return {"ok": True}
            
            # Get semantic memory
            from app.services.memory_db_service import memory_db_service
            luna_user_id = user_info.get("user_id")
            memories = await memory_db_service.get_semantic_memory(luna_user_id, DEFAULT_CHARACTER_ID)
            
            if not memories:
                await send_telegram_message(chat_id, "我们聊得还不够多，继续聊天让我更了解你吧~ 💕")
                return {"ok": True}
            
            info = "📝 我记得的关于你：\n\n"
            for mem in memories[:10]:  # Limit to 10 items
                if mem.get("content"):
                    info += f"• {mem['content'][:50]}...\n" if len(mem.get('content', '')) > 50 else f"• {mem['content']}\n"
            
            await send_telegram_message(chat_id, info)
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            await send_telegram_message(chat_id, "记忆系统暂时出了点问题，等会再试试~ 💭")
        return {"ok": True}
    
    # Handle /link command - link to Luna App account
    if text.startswith("/link"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await send_telegram_message(chat_id, "用法：/link 你的邮箱\n\n例如：/link example@gmail.com")
            return {"ok": True}
        
        email = parts[1].strip().lower()
        
        # Validate email format
        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            await send_telegram_message(chat_id, "这个邮箱格式好像不对诶，再检查一下？")
            return {"ok": True}
        
        try:
            # Check if email exists in Luna users table
            async with get_db() as db:
                result = await db.execute(
                    select(User).where(User.email == email)
                )
                luna_user = result.scalar_one_or_none()
                
                if not luna_user:
                    await send_telegram_message(chat_id, f"没有找到 {email} 的Luna账号哦~\n\n先下载Luna App注册一个吧！💕")
                    return {"ok": True}
                
                # Check if already linked
                telegram_uid = f"telegram_{user_id}"
                if luna_user.firebase_uid == telegram_uid:
                    await send_telegram_message(chat_id, "你已经关联过这个账号啦~ 💕")
                    return {"ok": True}
                
                # Link: update the telegram user to point to Luna user
                tg_result = await db.execute(
                    select(User).where(User.firebase_uid == telegram_uid)
                )
                tg_user = tg_result.scalar_one_or_none()
                
                if tg_user:
                    # Merge: update telegram user's data to Luna user
                    # For now, just update the telegram user's email to link them
                    tg_user.email = email
                    tg_user.display_name = luna_user.display_name or tg_user.display_name
                    await db.commit()
                    
                    await send_telegram_message(chat_id, f"✅ 成功关联到 {email}！\n\n现在你在Telegram和App的记忆会同步啦~ 💕")
                else:
                    await send_telegram_message(chat_id, "请先发送一条消息，然后再试试关联~")
                    
        except Exception as e:
            logger.error(f"Link error: {e}", exc_info=True)
            await send_telegram_message(chat_id, "关联失败了，稍后再试试？💭")
        
        return {"ok": True}
    
    # Ignore empty messages and unknown commands
    if not text or text.startswith("/"):
        return {"ok": True}
    
    # Send typing indicator
    await send_chat_action(chat_id, "typing")
    
    # Process through chat API
    try:
        request = TelegramChatRequest(
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            message=text,
        )
        response = await telegram_chat(request)
        
        # Send reply
        await send_telegram_message(chat_id, response.reply)
        
    except Exception as e:
        logger.error(f"Webhook chat error: {e}", exc_info=True)
        await send_telegram_message(chat_id, "抱歉，我走神了... 再说一遍好吗？💭")
    
    return {"ok": True}


@router.post("/set-webhook")
async def set_webhook(webhook_url: str):
    """
    Set Telegram bot webhook URL.
    
    Call this endpoint to configure the bot webhook.
    Example: POST /api/v1/telegram/set-webhook?webhook_url=https://your-domain.com/api/v1/telegram/webhook
    """
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")
    
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"✅ Webhook set to: {webhook_url}")
                return {"success": True, "webhook_url": webhook_url}
            else:
                raise HTTPException(status_code=400, detail=result.get("description", "Failed to set webhook"))
                
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@router.get("/webhook-info")
async def get_webhook_info():
    """Get current webhook configuration."""
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return {"configured": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            result = response.json()
            
            if result.get("ok"):
                info = result.get("result", {})
                return {
                    "configured": True,
                    "url": info.get("url", ""),
                    "has_custom_certificate": info.get("has_custom_certificate", False),
                    "pending_update_count": info.get("pending_update_count", 0),
                    "last_error_date": info.get("last_error_date"),
                    "last_error_message": info.get("last_error_message"),
                }
            else:
                return {"configured": False, "error": result.get("description")}
                
    except Exception as e:
        return {"configured": False, "error": str(e)}


# ========== Account Linking API ==========

class LinkAccountRequest(BaseModel):
    telegram_id: str
    email: str
    language_code: Optional[str] = None


class LinkAccountResponse(BaseModel):
    success: bool
    message: str
    is_pro: bool = False
    display_name: Optional[str] = None


@router.post("/link", response_model=LinkAccountResponse)
async def link_telegram_account(request: LinkAccountRequest):
    """
    Link a Telegram account to an existing Luna account via email.
    
    This enables:
    - Shared memories between iOS and Telegram
    - Synced subscription/Pro status
    - Unified identity
    """
    import re
    
    telegram_id = request.telegram_id.strip()
    email = request.email.strip().lower()
    language_code = request.language_code or 'en'
    
    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return LinkAccountResponse(
            success=False,
            message="邮箱格式不正确，请检查后重试。" if language_code.startswith('zh') else "Invalid email format."
        )
    
    async with get_db() as db:
        # 1. Check if email exists in Luna users table
        result = await db.execute(
            select(User).where(User.email == email)
        )
        luna_user = result.scalar_one_or_none()
        
        if not luna_user:
            return LinkAccountResponse(
                success=False,
                message=f"没有找到 {email} 的Luna账号，请先下载Luna App注册。" if language_code.startswith('zh') 
                        else f"No Luna account found for {email}. Please download Luna App to register first."
            )
        
        # 2. Check if this email is already linked to another telegram
        if luna_user.telegram_id and luna_user.telegram_id != telegram_id:
            return LinkAccountResponse(
                success=False,
                message="这个邮箱已经绑定了另一个Telegram账号。" if language_code.startswith('zh')
                        else "This email is already linked to another Telegram account."
            )
        
        # 3. Check if this telegram_id is already linked to another email
        tg_check = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing_tg_user = tg_check.scalar_one_or_none()
        
        if existing_tg_user and existing_tg_user.email != email:
            # This telegram is linked to a different account
            return LinkAccountResponse(
                success=False,
                message=f"你的Telegram已绑定到 {existing_tg_user.email}，如需更换请联系客服。" if language_code.startswith('zh')
                        else f"Your Telegram is already linked to {existing_tg_user.email}."
            )
        
        # 4. Link the accounts
        luna_user.telegram_id = telegram_id
        if language_code:
            luna_user.preferred_language = language_code[:2]  # Store just 'en', 'zh', etc.
        
        # 5. If there's a temporary telegram user, just log it
        # Don't delete - cascade deletion has schema issues
        # TODO: Implement proper data migration later
        temp_firebase_uid = f"telegram_{telegram_id}"
        temp_result = await db.execute(
            select(User).where(User.firebase_uid == temp_firebase_uid)
        )
        temp_user = temp_result.scalar_one_or_none()
        
        if temp_user and temp_user.user_id != luna_user.user_id:
            logger.info(f"🔗 Found temp user {temp_user.user_id}, will merge later (not deleting now)")
        
        await db.commit()
        
        is_pro = luna_user.is_subscribed or luna_user.subscription_tier != 'free'
        
        logger.info(f"✅ Linked Telegram {telegram_id} to Luna account {luna_user.email} (Pro: {is_pro})")
        
        return LinkAccountResponse(
            success=True,
            message=f"🎉 绑定成功！你的iOS记忆和{'Pro' if is_pro else ''}权益已同步。" if language_code.startswith('zh')
                    else f"🎉 Account linked! Your iOS memories and {'Pro ' if is_pro else ''}benefits are now synced.",
            is_pro=is_pro,
            display_name=luna_user.display_name
        )


@router.get("/user-by-telegram/{telegram_id}")
async def get_user_by_telegram(telegram_id: str):
    """Get Luna user info by Telegram ID (for debugging)."""
    async with get_db() as db:
        # First try to find by telegram_id field
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        # Fallback to firebase_uid
        if not user:
            result = await db.execute(
                select(User).where(User.firebase_uid == f"telegram_{telegram_id}")
            )
            user = result.scalar_one_or_none()
        
        if not user:
            return {"found": False}
        
        return {
            "found": True,
            "user_id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "is_linked": user.telegram_id == telegram_id and not user.email.endswith('@telegram.luna'),
            "is_pro": user.is_subscribed or user.subscription_tier != 'free',
            "preferred_language": user.preferred_language,
        }

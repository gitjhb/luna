"""
Chat API Routes - with SQLite persistence
"""

from fastapi import APIRouter, HTTPException, Request
from uuid import UUID, uuid4
from datetime import datetime
import os
import logging

from app.models.schemas import (
    ChatCompletionRequest, ChatCompletionResponse,
    CreateSessionRequest, CreateSessionResponse,
    SessionInfo, ChatMessage
)
from app.services.intimacy_service import intimacy_service, IntimacyService
from app.services.chat_repository import chat_repo
from app.api.v1.characters import CHARACTERS
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat")

MOCK_MODE = settings.MOCK_LLM


def get_character_info(character_id: str) -> dict:
    """Get character info by ID"""
    for c in CHARACTERS:
        if c["character_id"] == str(character_id):
            return c
    return {"name": "AI Companion", "avatar_url": None, "background_url": None}


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest, req: Request):
    """
    Create a new chat session with a character.
    If a session already exists for this character, return the existing one.
    """
    # Get user ID (from auth or default)
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # Get character info
    character = get_character_info(str(request.character_id))
    
    # Check if session already exists for this user + character
    existing = await chat_repo.get_session_by_character(user_id, str(request.character_id))
    if existing:
        return CreateSessionResponse(
            session_id=UUID(existing["session_id"]),
            character_name=existing["character_name"],
            character_avatar=existing.get("character_avatar"),
            character_background=existing.get("character_background"),
        )
    
    # Create new session
    session = await chat_repo.create_session(
        user_id=user_id,
        character_id=str(request.character_id),
        character_name=character["name"],
        character_avatar=character.get("avatar_url"),
        character_background=character.get("background_url"),
    )

    return CreateSessionResponse(
        session_id=UUID(session["session_id"]),
        character_name=session["character_name"],
        character_avatar=session.get("character_avatar"),
        character_background=session.get("character_background"),
    )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(character_id: UUID = None, req: Request = None):
    """List all chat sessions for current user, optionally filtered by character_id"""
    user = getattr(req.state, "user", None) if req else None
    user_id = str(user.user_id) if user else "demo-user-123"
    
    sessions = await chat_repo.list_sessions(
        user_id=user_id,
        character_id=str(character_id) if character_id else None
    )
    
    return [
        SessionInfo(
            session_id=UUID(s["session_id"]),
            character_id=UUID(s["character_id"]),
            character_name=s["character_name"],
            character_avatar=s.get("character_avatar"),
            character_background=s.get("character_background"),
            total_messages=s.get("total_messages", 0),
            created_at=s["created_at"],
            updated_at=s["updated_at"],
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessage])
async def get_session_messages(session_id: UUID, limit: int = 50, offset: int = 0):
    """Get messages for a session"""
    messages = await chat_repo.get_messages(str(session_id), limit=limit, offset=offset)
    return [
        ChatMessage(
            message_id=UUID(m["message_id"]),
            role=m["role"],
            content=m["content"],
            tokens_used=m.get("tokens_used", 0),
            created_at=m["created_at"],
        )
        for m in messages
    ]


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest, req: Request):
    """
    Main chat completion endpoint.
    In mock mode: returns echo response.
    In production: calls Grok API with RAG context.
    """
    import time
    request_id = f"{int(time.time()*1000)}"
    
    logger.info(f"")
    logger.info(f"🚀 [{request_id}] NEW REQUEST RECEIVED")
    logger.info(f"   Session: {request.session_id}")
    logger.info(f"   Message: '{request.message[:50]}{'...' if len(request.message) > 50 else ''}'")
    
    session_id = str(request.session_id)

    # Get session from DB
    session = await chat_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check for duplicate message
    recent_msgs = await chat_repo.get_recent_messages(session_id, count=2)
    is_duplicate = any(
        m["role"] == "user" and m["content"] == request.message 
        for m in recent_msgs
    )
    
    if is_duplicate:
        logger.warning(f"⚠️ DUPLICATE MESSAGE DETECTED: '{request.message[:50]}...'")

    # Store user message
    user_msg = await chat_repo.add_message(
        session_id=session_id,
        role="user",
        content=request.message,
        tokens_used=0,
    )
    
    all_messages = await chat_repo.get_all_messages(session_id)
    logger.info(f"📝 Stored user message. Total messages in session: {len(all_messages)}")

    # Generate response
    if MOCK_MODE:
        reply = _mock_reply(request.message)
        tokens = len(request.message) // 4 + len(reply) // 4
    else:
        # Production: use GrokService directly
        from app.services.llm_service import GrokService
        
        grok = GrokService()
        
        # Build conversation context
        conversation = []
        character_name = session["character_name"]
        character_id = session["character_id"]
        
        # Check user subscription for memory features
        user = getattr(req.state, "user", None)
        is_premium = getattr(user, "is_subscribed", False) if user else False
        
        # Get spicy mode and intimacy level from request
        spicy_mode = request.spicy_mode
        intimacy_level = request.intimacy_level
        
        # System prompt for character (with intimacy-based behavior)
        if spicy_mode and is_premium:
            mode_instruction = """You can be flirtatious and suggestive. NSFW content is allowed within legal limits."""
        else:
            mode_instruction = """Keep responses appropriate and friendly. Politely decline if user requests explicit content."""
        
        # Adjust behavior based on intimacy level
        if intimacy_level <= 5:
            intimacy_instruction = "You are polite but reserved. Keep appropriate distance as you're still getting to know each other."
        elif intimacy_level <= 15:
            intimacy_instruction = "You're becoming more comfortable. Show more personality and warmth."
        elif intimacy_level <= 30:
            intimacy_instruction = "You're close friends now. Be more open, playful, and share personal thoughts."
        else:
            intimacy_instruction = "You have a deep bond. Be intimate, caring, and emotionally connected."
        
        system_prompt = f"""You are {character_name}, a friendly AI companion.
Be warm, engaging, and conversational. Respond in the same language the user uses.
Keep responses concise but meaningful.

{mode_instruction}

{intimacy_instruction}

Current intimacy level: {intimacy_level}"""
        
        conversation.append({"role": "system", "content": system_prompt})
        
        # Build context based on subscription
        # Get all messages except the one we just added
        history_messages = all_messages[:-1]
        
        if is_premium:
            context_limit = 20
            logger.info(f"Premium user: using {context_limit} messages context")
        else:
            context_limit = 10
            logger.info(f"Free user: using {context_limit} messages context (no memory)")
        
        for msg in history_messages[-context_limit:]:
            conversation.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        conversation.append({"role": "user", "content": request.message})
        
        # Debug logging
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"=== CHAT COMPLETION DEBUG ===")
        logger.info(f"{'='*60}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Character: {character_name}")
        logger.info(f"Spicy Mode: {spicy_mode}, Intimacy: {intimacy_level}")
        logger.info(f"Is Premium: {is_premium}")
        logger.info(f"")
        logger.info(f"--- CURRENT USER MESSAGE ---")
        logger.info(f"'{request.message}'")
        logger.info(f"")
        logger.info(f"--- ALL STORED MESSAGES ({len(all_messages)}) ---")
        for i, m in enumerate(all_messages):
            logger.info(f"  [{i}] {m['role']}: '{m['content'][:80]}{'...' if len(m['content']) > 80 else ''}'")
        logger.info(f"")
        logger.info(f"--- FINAL CONVERSATION TO GROK ({len(conversation)} messages) ---")
        for i, msg in enumerate(conversation):
            content_preview = msg['content'][:100].replace('\n', '\\n')
            logger.info(f"  [{i}] {msg['role']}: '{content_preview}{'...' if len(msg['content']) > 100 else ''}'")
        logger.info(f"{'='*60}")
        
        # Call Grok API
        try:
            result = await grok.chat_completion(
                messages=conversation,
                temperature=0.8,
                max_tokens=500
            )
            reply = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("total_tokens", 0)
            logger.info(f"Grok response: {reply[:100]}...")
            logger.info(f"Tokens used: {tokens}")
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            reply = f"抱歉，我暂时无法回应。错误：{str(e)[:100]}"
            tokens = 10

    # Store assistant message
    assistant_msg = await chat_repo.add_message(
        session_id=session_id,
        role="assistant",
        content=reply,
        tokens_used=tokens,
    )
    msg_id = UUID(assistant_msg["message_id"])

    # Update session stats
    await chat_repo.update_session(
        session_id,
        total_messages=session.get("total_messages", 0) + 2
    )

    # Store tokens for billing middleware
    req.state.tokens_used = tokens
    req.state.session_id = request.session_id
    req.state.message_id = msg_id

    # =========================================================================
    # Intimacy XP Awards
    # =========================================================================
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    character_id = session["character_id"]

    # Award XP for sending message (+2 XP)
    xp_result = await intimacy_service.award_xp(user_id, character_id, "message")
    intimacy_xp = xp_result.get("xp_awarded", 0) if xp_result.get("success") else 0
    level_up = xp_result.get("level_up", False)

    # Check for continuous chat bonus (every 10 messages)
    total_msgs = session.get("total_messages", 0) + 2
    if total_msgs > 0 and total_msgs % 10 == 0:
        bonus_result = await intimacy_service.award_xp(user_id, character_id, "continuous_chat")
        if bonus_result.get("success"):
            intimacy_xp += bonus_result.get("xp_awarded", 0)
            logger.info(f"Continuous chat bonus awarded: +{bonus_result.get('xp_awarded', 0)} XP")

    # Check for emotional words bonus
    if IntimacyService.contains_emotional_words(request.message):
        emotional_result = await intimacy_service.award_xp(user_id, character_id, "emotional")
        if emotional_result.get("success"):
            intimacy_xp += emotional_result.get("xp_awarded", 0)
            logger.info(f"Emotional expression bonus awarded: +{emotional_result.get('xp_awarded', 0)} XP")

    # Store intimacy info in request state
    req.state.intimacy_xp_awarded = intimacy_xp
    req.state.intimacy_level_up = level_up

    return ChatCompletionResponse(
        message_id=msg_id,
        content=reply,
        tokens_used=tokens,
        character_name=session["character_name"],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID):
    """Delete a chat session"""
    await chat_repo.delete_session(str(session_id))
    return {"status": "deleted"}


@router.get("/debug/session/{session_id}")
async def debug_session(session_id: UUID):
    """Debug endpoint to view session state"""
    session = await chat_repo.get_session(str(session_id))
    if not session:
        return {"error": "Session not found"}
    
    messages = await chat_repo.get_all_messages(str(session_id))
    return {
        "session": session,
        "message_count": len(messages),
        "messages": [
            {
                "index": i,
                "role": m["role"],
                "content": m["content"][:100] + ("..." if len(m["content"]) > 100 else ""),
                "created_at": str(m["created_at"])
            }
            for i, m in enumerate(messages)
        ]
    }


def _mock_reply(message: str) -> str:
    """Mock responses for development"""
    msg = message.strip().lower()
    
    replies = {
        "你好": "你好呀！我是你的专属AI伙伴，有什么想聊的吗？😊",
        "hi": "Hey there! I'm your AI companion. What's on your mind today?",
        "hello": "Hello! Nice to meet you. How can I help you today?",
    }
    
    if msg in replies:
        return replies[msg]
    
    if "?" in message or "？" in message:
        return f"这是个好问题！关于「{message[:20]}...」，让我想想... 🤔"
    
    return f"收到～ 你说的是「{message[:30]}{'...' if len(message) > 30 else ''}」。有什么想继续聊的吗？"

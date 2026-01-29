"""
Chat API Routes
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat")

# In-memory storage for demo (replace with DB in production)
_sessions = {}
_messages = {}

MOCK_MODE = os.getenv("MOCK_LLM", "true").lower() == "true"


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new chat session with a character.
    If a session already exists for this character, return the existing one.
    This ensures each user has only one session per character.
    """
    # Check if session already exists for this character
    for session in _sessions.values():
        if str(session["character_id"]) == str(request.character_id):
            return CreateSessionResponse(
                session_id=session["session_id"],
                character_name=session["character_name"],
                character_avatar=None,
            )
    
    # Create new session if none exists
    session_id = uuid4()
    _sessions[str(session_id)] = {
        "session_id": session_id,
        "character_id": request.character_id,
        "character_name": "AI Companion",
        "total_messages": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    _messages[str(session_id)] = []

    return CreateSessionResponse(
        session_id=session_id,
        character_name="AI Companion",
        character_avatar=None,
    )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(character_id: UUID = None):
    """List all chat sessions for current user, optionally filtered by character_id"""
    sessions = _sessions.values()
    
    # Filter by character_id if provided
    if character_id:
        sessions = [s for s in sessions if str(s["character_id"]) == str(character_id)]
    
    return [
        SessionInfo(
            session_id=s["session_id"],
            character_id=s["character_id"],
            character_name=s["character_name"],
            total_messages=s["total_messages"],
            created_at=s["created_at"],
            updated_at=s["updated_at"],
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessage])
async def get_session_messages(session_id: UUID, limit: int = 50, offset: int = 0):
    """Get messages for a session"""
    msgs = _messages.get(str(session_id), [])
    return msgs[offset : offset + limit]


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest, req: Request):
    """
    Main chat completion endpoint.
    In mock mode: returns echo response.
    In production: calls Grok API with RAG context.
    """
    session_id = str(request.session_id)

    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store user message
    user_msg = ChatMessage(
        message_id=uuid4(),
        role="user",
        content=request.message,
        tokens_used=0,
        created_at=datetime.utcnow(),
    )
    if session_id not in _messages:
        _messages[session_id] = []
    _messages[session_id].append(user_msg)

    # Generate response
    if MOCK_MODE:
        reply = _mock_reply(request.message)
        tokens = len(request.message) // 4 + len(reply) // 4
    else:
        # Production: use ChatService with Grok
        from app.services.chat_service import ChatService
        from app.models.schemas import UserContext
        
        chat_service = ChatService()
        user_context = UserContext(
            user_id=uuid4(),
            subscription_tier="free",
            is_subscribed=False,
        )
        response = await chat_service.chat_completion(request, user_context)
        reply = response.content
        tokens = response.tokens_used

    # Store assistant message
    msg_id = uuid4()
    assistant_msg = ChatMessage(
        message_id=msg_id,
        role="assistant",
        content=reply,
        tokens_used=tokens,
        created_at=datetime.utcnow(),
    )
    _messages[session_id].append(assistant_msg)

    # Update session stats
    _sessions[session_id]["total_messages"] += 2
    _sessions[session_id]["updated_at"] = datetime.utcnow()

    # Store tokens for billing middleware
    req.state.tokens_used = tokens
    req.state.session_id = request.session_id
    req.state.message_id = msg_id

    # =========================================================================
    # Intimacy XP Awards
    # =========================================================================
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    character_id = str(_sessions[session_id]["character_id"])

    # Award XP for sending message (+2 XP)
    xp_result = await intimacy_service.award_xp(user_id, character_id, "message")
    intimacy_xp = xp_result.get("xp_awarded", 0) if xp_result.get("success") else 0
    level_up = xp_result.get("level_up", False)

    # Check for continuous chat bonus (every 10 messages)
    total_msgs = _sessions[session_id]["total_messages"]
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

    # Store intimacy info in request state for potential use
    req.state.intimacy_xp_awarded = intimacy_xp
    req.state.intimacy_level_up = level_up

    return ChatCompletionResponse(
        message_id=msg_id,
        content=reply,
        tokens_used=tokens,
        character_name=_sessions[session_id]["character_name"],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID):
    """Delete a chat session"""
    sid = str(session_id)
    if sid in _sessions:
        del _sessions[sid]
    if sid in _messages:
        del _messages[sid]
    return {"status": "deleted"}


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

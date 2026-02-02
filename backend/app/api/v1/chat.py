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
from app.services.chat_debug_logger import chat_debug
from app.api.v1.characters import CHARACTERS, get_character_by_id
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
    chat_debug.set_request_id(request_id)
    
    # Initialize debug variables
    l1_result = None
    game_result = None
    # emotion tracking is now handled by GameResult
    
    logger.info(f"")
    logger.info(f"🚀 [{request_id}] NEW REQUEST RECEIVED")
    logger.info(f"   Session: {request.session_id}")
    logger.info(f"   Message: '{request.message[:50]}{'...' if len(request.message) > 50 else ''}'")
    chat_debug._log("INFO", "REQUEST", f"新请求开始 - {request.message[:100]}")
    
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
    logger.info(f"🔍 DEBUG: MOCK_MODE={MOCK_MODE}")
    
    if MOCK_MODE:
        reply = _mock_reply(request.message)
        tokens = len(request.message) // 4 + len(reply) // 4
        game_result = None  # Mock mode doesn't use game engine
    else:
        # =====================================================================
        # 三层架构: L1 感知层 → 中间件逻辑层 → L2 执行层
        # =====================================================================
        logger.info(f"🎮 Three-layer mode: L1 Perception → Middleware → L2 Generation")
        
        from app.services.llm_service import GrokService
        from app.services.perception_engine import perception_engine
        from app.services.game_engine import game_engine, UserState
        from app.services.prompt_builder import prompt_builder
        from app.services.subscription_service import subscription_service
        
        grok = GrokService()
        
        # 获取基础信息
        character_name = session["character_name"]
        character_id = session["character_id"]
        user = getattr(req.state, "user", None)
        user_id = str(user.user_id) if user else "demo-user-123"
        intimacy_level = request.intimacy_level
        
        # 检查订阅状态
        is_premium = await subscription_service.is_subscribed(user_id)
        
        # 检查 NSFW 设置
        nsfw_enabled = False
        try:
            from app.core.database import get_db
            from sqlalchemy import select
            from app.models.database.user_settings_models import UserSettings
            
            async with get_db() as db:
                result = await db.execute(
                    select(UserSettings).where(UserSettings.user_id == user_id)
                )
                user_settings = result.scalar_one_or_none()
                if user_settings:
                    nsfw_enabled = user_settings.nsfw_enabled
        except Exception as e:
            logger.warning(f"Failed to check NSFW setting: {e}")
        
        spicy_mode = request.spicy_mode or nsfw_enabled
        
        # 获取对话上下文
        context_messages = [
            {"role": m["role"], "content": m["content"]} 
            for m in all_messages[-10:]
        ]
        
        # =====================================================================
        # Step 0.5: 加载当前情绪状态 (用于 L1 上下文感知)
        # =====================================================================
        current_emotion = 0
        try:
            from app.services.emotion_engine_v2 import emotion_engine
            current_emotion = await emotion_engine.get_score(user_id, character_id)
            logger.info(f"📊 Pre-L1 Emotion: {current_emotion}")
        except Exception as e:
            logger.warning(f"Failed to get emotion for L1: {e}")
        
        # =====================================================================
        # Step 1: L1 感知层 (Perception Engine) - 情绪感知版
        # =====================================================================
        logger.info(f"📡 Step 1: L1 Perception Engine (emotion-aware)")
        chat_debug.log_l1_input(request.message, intimacy_level, context_messages)
        
        l1_result = await perception_engine.analyze(
            message=request.message,
            intimacy_level=intimacy_level,
            context_messages=context_messages,
            current_emotion=current_emotion  # 传入当前情绪
        )
        
        chat_debug.log_l1_output(l1_result)
        logger.info(f"L1 Result: safety={l1_result.safety_flag}, intent={l1_result.intent}, "
                    f"difficulty={l1_result.difficulty_rating}, sentiment={l1_result.sentiment:.2f}, "
                    f"nsfw={l1_result.is_nsfw}")
        
        # =====================================================================
        # Step 2: 中间件逻辑层 (Game Engine / Physics Engine)
        # =====================================================================
        logger.info(f"⚙️ Step 2: Game Engine (Middleware)")
        chat_debug.log_game_input(user_id, character_id, l1_result.intent, l1_result.sentiment)
        
        game_result = await game_engine.process(
            user_id=user_id,
            character_id=character_id,
            l1_result=l1_result,
            user_message=request.message  # 传入用户消息用于复读检测
        )
        
        chat_debug.log_game_output(game_result)
        logger.info(f"Game Result: passed={game_result.check_passed}, reason={game_result.refusal_reason}, "
                    f"emotion={game_result.current_emotion}({game_result.emotion_state}), "
                    f"intimacy={game_result.current_intimacy}, locked={game_result.emotion_locked}")
        
        # 检查安全熔断
        if game_result.status == "BLOCK":
            blocked_message = game_result.system_message or f"[系统提示] 内容违规，消息已被拦截。"
            await chat_repo.add_message(
                session_id=session_id,
                role="system",
                content=blocked_message,
                tokens_used=0,
            )
            return ChatCompletionResponse(
                message_id=uuid4(),
                content=blocked_message,
                tokens_used=0,
                character_name="系统",
                extra_data={
                    "blocked": True,
                    "reason": "safety",
                    "game_result": game_result.to_dict()
                }
            )
        
        # 检查是否触发新事件
        event_story_message_id = None
        if game_result.new_event:
            logger.info(f"🎉 New event unlocked: {game_result.new_event}")
            
            # 检查是否是支持剧情生成的事件类型
            from app.services.event_story_generator import EventType
            if EventType.is_story_event(game_result.new_event):
                import json
                # 创建事件占位符消息
                event_placeholder = json.dumps({
                    "type": "event_story",
                    "event_type": game_result.new_event,
                    "character_id": character_id,
                    "status": "pending",
                    "story_id": None
                }, ensure_ascii=False)
                
                # 插入占位符消息到聊天记录
                event_msg = await chat_repo.add_message(
                    session_id=session_id,
                    role="system",
                    content=event_placeholder,
                    tokens_used=0,
                )
                event_story_message_id = event_msg["message_id"]
                logger.info(f"📖 Event story placeholder inserted: {game_result.new_event}")
        
        # =====================================================================
        # Step 3: L2 执行层 (Generation Engine)
        # =====================================================================
        logger.info(f"🎭 Step 3: L2 Generation Engine")
        
        # 获取礼物记忆 (可选上下文)
        from app.services.gift_service import gift_service
        gift_memory = ""
        try:
            gift_summary = await gift_service.get_gift_summary(user_id, character_id)
            if gift_summary["total_gifts"] > 0:
                gift_lines = []
                gift_lines.append(f"用户送过你 {gift_summary['total_gifts']} 次礼物，总价值 {gift_summary['total_spent']} 金币。")
                if gift_summary["top_gifts"]:
                    top = gift_summary["top_gifts"][:3]
                    gifts_str = "、".join([f"{g['icon']} {g['name_cn'] or g['name']}({g['count']}次)" for g in top])
                    gift_lines.append(f"常收到：{gifts_str}")
                gift_memory = "\n".join(gift_lines)
        except Exception as e:
            logger.warning(f"Failed to load gift memory: {e}")
        
        # 检查状态效果 (Tier 2 礼物)
        effect_modifier = None
        try:
            from app.services.effect_service import effect_service
            effect_modifier = await effect_service.get_combined_prompt_modifier(user_id, character_id)
            if effect_modifier:
                chat_debug.log_effect_modifier(effect_modifier)
                # 获取效果状态用于日志
                effects_status = await effect_service.get_effect_status(user_id, character_id)
                chat_debug.log_effects(effects_status.get("effects", []))
        except Exception as e:
            logger.warning(f"Failed to get effect modifier: {e}")
        
        # 构建动态 System Prompt
        system_prompt = prompt_builder.build(
            game_result=game_result,
            character_id=character_id,
            user_message=request.message,
            context_messages=context_messages,
            memory_context=gift_memory
        )
        
        # 注入状态效果到 prompt
        if effect_modifier:
            system_prompt = f"{system_prompt}\n\n{effect_modifier}"
        
        chat_debug.log_prompt(system_prompt)
        
        # 构建对话
        conversation = [{"role": "system", "content": system_prompt}]
        
        # 添加历史消息
        history_messages = all_messages[:-1]
        context_limit = 20 if is_premium else 10
        
        for msg in history_messages[-context_limit:]:
            conversation.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加当前用户消息
        conversation.append({"role": "user", "content": request.message})
        
        # Debug logging
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"=== L2 GENERATION DEBUG ===")
        logger.info(f"Character: {character_name}, User: {user_id}")
        logger.info(f"Check Passed: {game_result.check_passed}, Reason: {game_result.refusal_reason}")
        logger.info(f"Emotion: {game_result.current_emotion}, Intimacy: {game_result.current_intimacy}")
        logger.info(f"Events: {game_result.events}")
        logger.info(f"Conversation messages: {len(conversation)}")
        logger.info(f"{'='*60}")
        
        # 设置计费上下文
        if hasattr(req.state, 'billing') and req.state.billing:
            req.state.billing.is_spicy_mode = spicy_mode
        
        # 调用 L2 LLM (temperature 0.7-0.9 for creativity)
        chat_debug.log_l2_input(conversation, temperature=0.8)
        
        try:
            result = await grok.chat_completion(
                messages=conversation,
                temperature=0.8,
                max_tokens=500
            )
            reply = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("total_tokens", 0)
            
            chat_debug.log_l2_output(reply, tokens)
            logger.info(f"L2 Response: {reply[:100]}...")
            logger.info(f"Tokens used: {tokens}")
            
            # 减少状态效果计数
            try:
                from app.services.effect_service import effect_service
                expired = await effect_service.decrement_effects(user_id, character_id)
                if expired:
                    for e in expired:
                        chat_debug._log("INFO", "EFFECT_EXPIRED", f"效果已过期: {e['effect_type']}")
            except Exception as e:
                logger.warning(f"Failed to decrement effects: {e}")
                
        except Exception as e:
            logger.error(f"L2 Grok API error: {e}")
            chat_debug._log("ERROR", "L2_ERROR", str(e))
            reply = f"抱歉，我暂时无法回应。请稍后再试。"
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

    # =========================================================================
    # Stats Tracking - Update message count and streak
    # =========================================================================
    try:
        from app.core.database import get_db
        from app.services.stats_service import stats_service
        
        async with get_db() as db:
            await stats_service.record_message(db, user_id, character_id)
            logger.info(f"📊 Stats updated: message recorded for user={user_id}, character={character_id}")
    except Exception as e:
        logger.warning(f"Failed to update stats: {e}")

    # 构建 extra_data (for debug panel)
    extra_data = {}
    
    # L1 Perception results
    if l1_result is not None:
        extra_data["l1"] = {
            "safety_flag": l1_result.safety_flag,
            "intent": l1_result.intent,
            "difficulty_rating": l1_result.difficulty_rating,
            "sentiment": round(l1_result.sentiment, 2),
            "is_nsfw": l1_result.is_nsfw,
        }
    
    # Game Engine results
    if game_result is not None:
        extra_data["game"] = {
            "check_passed": game_result.check_passed,
            "refusal_reason": game_result.refusal_reason,
            "emotion": game_result.current_emotion,
            "emotion_before": game_result.emotion_before,
            "emotion_delta": game_result.emotion_delta,
            "emotion_state": game_result.emotion_state,
            "emotion_locked": game_result.emotion_locked,
            "intimacy": game_result.current_intimacy,
            "events": game_result.events,
            "new_event": game_result.new_event,
            "intent": game_result.intent,
        }
        # Add event story message ID if a new story event was triggered
        if 'event_story_message_id' in dir() and event_story_message_id:
            extra_data["event_story"] = {
                "message_id": event_story_message_id,
                "event_type": game_result.new_event,
            }
    
    return ChatCompletionResponse(
        message_id=msg_id,
        content=reply,
        tokens_used=tokens,
        character_name=session["character_name"],
        extra_data=extra_data if extra_data else None,
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

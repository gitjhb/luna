"""
Chat API Routes - with SQLite persistence
"""

from typing import Optional
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


def _get_user_id(request: Request) -> str:
    """从请求中获取用户ID，支持认证和header fallback"""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "user_id"):
        return str(user.user_id)
    # Fallback to header for testing/development
    return request.headers.get("X-User-ID", "demo-user-123")


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest, req: Request):
    """
    Create a new chat session with a character.
    If a session already exists for this character, return the existing one.
    """
    # Get user ID (from auth or header)
    user_id = _get_user_id(req)
    
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


@router.get("/sessions")
async def list_sessions(
    character_id: UUID = None, 
    include_messages: int = 0,
    req: Request = None
):
    """
    List all chat sessions for current user.
    
    Args:
        character_id: Optional filter by character
        include_messages: If > 0, include latest N messages per session (for batch loading)
    
    When include_messages > 0, returns dict with sessions and messages.
    Otherwise returns list of SessionInfo for backward compatibility.
    """
    user_id = _get_user_id(req) if req else "demo-user-123"
    
    sessions = await chat_repo.list_sessions(
        user_id=user_id,
        character_id=str(character_id) if character_id else None
    )
    
    session_list = [
        {
            "session_id": s["session_id"],
            "character_id": s["character_id"],
            "character_name": s["character_name"],
            "character_avatar": s.get("character_avatar"),
            "character_background": s.get("character_background"),
            "total_messages": s.get("total_messages", 0),
            "last_message": s.get("last_message"),
            "last_message_at": s.get("last_message_at"),
            "created_at": s["created_at"].isoformat() if hasattr(s["created_at"], 'isoformat') else str(s["created_at"]),
            "updated_at": s["updated_at"].isoformat() if hasattr(s["updated_at"], 'isoformat') else str(s["updated_at"]),
        }
        for s in sessions
    ]
    
    # 批量获取消息（用于 app 启动时一次性加载）
    if include_messages > 0:
        messages_by_session = {}
        for s in sessions:
            session_id = s["session_id"]
            msgs = await chat_repo.get_messages_paginated(session_id, limit=include_messages)
            messages_by_session[session_id] = [
                {
                    "message_id": m["message_id"],
                    "role": m["role"],
                    "content": m["content"],
                    "created_at": m["created_at"].isoformat() if hasattr(m["created_at"], 'isoformat') else str(m["created_at"]),
                }
                for m in msgs
            ]
        
        return {
            "sessions": session_list,
            "messages": messages_by_session,
        }
    
    return session_list


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: UUID, 
    limit: int = 20,
    before_id: Optional[str] = None,
    after_id: Optional[str] = None,
):
    """
    Get messages for a session with cursor-based pagination.
    
    分页加载聊天记录（类似微信）：
    - 默认返回最新的 20 条
    - before_id: 获取该消息之前的历史（用户上滑加载更多）
    - after_id: 获取该消息之后的新消息（检查新消息）
    
    返回格式：
    {
        "messages": [...],
        "has_more": true/false,
        "oldest_id": "xxx",  // 用于下次加载更多
        "newest_id": "xxx"
    }
    """
    messages = await chat_repo.get_messages_paginated(
        str(session_id), 
        limit=limit, 
        before_id=before_id,
        after_id=after_id,
    )
    
    msg_list = [
        ChatMessage(
            message_id=UUID(m["message_id"]),
            role=m["role"],
            content=m["content"],
            tokens_used=m.get("tokens_used", 0),
            created_at=m["created_at"],
        )
        for m in messages
    ]
    
    # 检查是否还有更多历史消息
    has_more = False
    if msg_list:
        oldest_msg_id = str(msg_list[0].message_id)
        has_more = await chat_repo.has_messages_before(str(session_id), oldest_msg_id)
    
    return {
        "messages": msg_list,
        "has_more": has_more,
        "oldest_id": str(msg_list[0].message_id) if msg_list else None,
        "newest_id": str(msg_list[-1].message_id) if msg_list else None,
    }


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
    v4_response = None  # Initialize to avoid UnboundLocalError
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

    # =====================================================================
    # 体力系统 - 仅 Debug 记录，不阻塞聊天
    # =====================================================================
    user_id = _get_user_id(req)
    
    try:
        from app.services.stamina_service import stamina_service, STAMINA_COST_PER_MESSAGE
        stamina_result = await stamina_service.consume_stamina(user_id, STAMINA_COST_PER_MESSAGE)
        logger.debug(f"⚡ [DEBUG] Stamina: consumed={STAMINA_COST_PER_MESSAGE}, remaining={stamina_result.get('current_stamina', '?')}")
    except Exception as e:
        logger.debug(f"⚡ [DEBUG] Stamina tracking skipped: {e}")

    # Check for duplicate message
    recent_msgs = await chat_repo.get_recent_messages(session_id, count=2)
    is_duplicate = any(
        m["role"] == "user" and m["content"] == request.message 
        for m in recent_msgs
    )
    
    if is_duplicate:
        logger.warning(f"⚠️ DUPLICATE MESSAGE DETECTED: '{request.message[:50]}...'")

    # V4.0 Pipeline flag - set to True to enable single-call architecture
    USE_V4_PIPELINE = os.getenv("USE_V4_PIPELINE", "true").lower() == "true"
    logger.info(f"🔍 DEBUG: USE_V4_PIPELINE={USE_V4_PIPELINE}")

    # Store user message — V4 pipeline handles its own storage, skip here to avoid duplicates
    if not USE_V4_PIPELINE:
        user_msg = await chat_repo.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            tokens_used=0,
        )
    
    all_messages = await chat_repo.get_all_messages(session_id)
    logger.info(f"📝 Total messages in session: {len(all_messages)}")
    
    effects_status = None  # 初始化，避免分支遗漏
    date_info = None
    
    if MOCK_MODE:
        reply = _mock_reply(request.message)
        tokens = len(request.message) // 4 + len(reply) // 4
        game_result = None  # Mock mode doesn't use game engine
    elif USE_V4_PIPELINE:
        # =====================================================================
        # V4.0 Single Call Pipeline: 前置计算 → Prompt注入 → 单次LLM → 后置更新
        # =====================================================================
        logger.info(f"🚀 V4.0 Single-call pipeline")
        
        from app.services.v4.chat_pipeline_v4 import chat_pipeline_v4, ChatRequestV4
        
        # 获取基础信息
        character_name = session["character_name"]
        character_id = session["character_id"]
        user_id = _get_user_id(req)
        intimacy_level = request.intimacy_level
        
        # 构建V4请求
        v4_request = ChatRequestV4(
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
            message=request.message,
            intimacy_level=intimacy_level
        )
        
        # 处理请求
        v4_response = await chat_pipeline_v4.process_message(v4_request)
        
        # 转换为旧格式响应
        reply = v4_response.content
        tokens = v4_response.tokens_used
        
        # 构建兼容的extra_data
        user_state_data = v4_response.extra_data.get("user_state", {})
        current_emotion = user_state_data.get("emotion", 0)
        
        game_result = type('MockGameResult', (), {
            'check_passed': not v4_response.is_nsfw_blocked,
            'refusal_reason': "NSFW_BLOCKED" if v4_response.is_nsfw_blocked else "",
            'current_emotion': current_emotion,
            'current_intimacy': user_state_data.get("intimacy", 0),
            'current_level': user_state_data.get("intimacy_level", 1),
            'emotion_before': current_emotion,  # V4 doesn't track before/after, use same value
            'emotion_delta': v4_response.emotion_delta,
            'emotion_state': "HAPPY" if current_emotion > 0 else "NEUTRAL" if current_emotion >= -20 else "ANGRY",
            'emotion_locked': current_emotion <= -75,
            'intent': v4_response.intent,
            'is_nsfw': v4_response.intent == "REQUEST_NSFW",
            'difficulty': v4_response.extra_data.get("precompute", {}).get("difficulty", 20),
            'new_event': "",
            'events': user_state_data.get("events", []),
            'power': 0.0,  # V4 doesn't calculate power
            'stage': "stranger",  # Simplified
            'archetype': "normal",
            'adjusted_difficulty': v4_response.extra_data.get("precompute", {}).get("difficulty", 20),
            'difficulty_modifier': 1.0,
            'power_breakdown': {'intimacy': 0, 'emotion': 0, 'chaos': 0, 'pure': 0, 'buff': 0, 'effect': 0},
            'to_dict': lambda: v4_response.extra_data
        })()
    else:
        # =====================================================================
        # 三层架构: L1 感知层 → 中间件逻辑层 → L2 执行层 (Legacy)
        # =====================================================================
        logger.info(f"🎮 Legacy Three-layer mode: L1 Perception → Middleware → L2 Generation")
        
        from app.services.llm_service import GrokService
        from app.services.perception_engine import perception_engine
        from app.services.game_engine import game_engine, UserState
        from app.services.prompt_builder import prompt_builder
        from app.services.subscription_service import subscription_service
        
        grok = GrokService()
        
        # 获取基础信息
        character_name = session["character_name"]
        character_id = session["character_id"]
        user_id = _get_user_id(req)
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
            current_emotion=current_emotion,  # 传入当前情绪
            spicy_mode=spicy_mode  # 传入 Spicy 模式状态
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
        effects_status = None
        try:
            from app.services.effect_service import effect_service
            effect_modifier = await effect_service.get_combined_prompt_modifier(user_id, character_id)
            # 获取效果状态 (用于日志和返回给前端)
            effects_status = await effect_service.get_effect_status(user_id, character_id)
            if effect_modifier:
                chat_debug.log_effect_modifier(effect_modifier)
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
        
        # 检查是否在约会中，注入约会场景
        date_info = None
        try:
            from app.services.date_service import date_service
            date_info = await date_service.get_active_date(user_id, character_id)
            if date_info:
                date_prompt = date_info.get("prompt_modifier") or date_service._build_date_prompt(
                    type("Scenario", (), {
                        "name": date_info.get("scenario_name", "约会"),
                        "context": date_info.get("scenario_context", ""),
                    })()
                )
                system_prompt = f"{system_prompt}\n\n{date_prompt}"
                logger.info(f"💕 Date mode active: {date_info.get('scenario_name')}")
        except Exception as e:
            logger.warning(f"Failed to check date status: {e}")
        
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
            
            # 约会进度更新
            if date_info:
                try:
                    from app.services.date_service import date_service
                    date_result = await date_service.increment_date_progress(user_id, character_id)
                    if date_result and date_result.get("status") == "completed":
                        chat_debug._log("INFO", "DATE_COMPLETED", "🎉 约会完成！first_date 事件已触发")
                        logger.info(f"💕 Date completed! first_date event triggered")
                except Exception as e:
                    logger.warning(f"Failed to update date progress: {e}")
                
        except Exception as e:
            logger.error(f"L2 Grok API error: {e}")
            chat_debug._log("ERROR", "L2_ERROR", str(e))
            reply = f"抱歉，我暂时无法回应。请稍后再试。"
            tokens = 10

    # Store assistant message — V4 pipeline already saved, skip to avoid duplicates
    if USE_V4_PIPELINE:
        # V4 already stored both user + assistant messages in _store_messages()
        # We just need the message_id for the response
        msg_id = uuid4()  # V4 response has its own ID
    else:
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
    # Intimacy XP Awards (V4 pipeline handles its own XP in _async_post_update)
    # =========================================================================
    user_id = _get_user_id(req)
    character_id = session["character_id"]

    intimacy_xp = 0
    level_up = False

    if not USE_V4_PIPELINE:
        # Legacy path: award XP here
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
    
    # Game Engine results (v3.0)
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
            # v3.0 新增
            "power": round(game_result.power, 1) if hasattr(game_result, 'power') else 0,
            "stage": game_result.stage if hasattr(game_result, 'stage') else "",
            "archetype": game_result.archetype if hasattr(game_result, 'archetype') else "",
            "adjusted_difficulty": game_result.adjusted_difficulty if hasattr(game_result, 'adjusted_difficulty') else 0,
            "difficulty_modifier": game_result.difficulty_modifier if hasattr(game_result, 'difficulty_modifier') else 1.0,
            "is_nsfw": game_result.is_nsfw if hasattr(game_result, 'is_nsfw') else False,
            "level": game_result.current_level if hasattr(game_result, 'current_level') else 1,
            # Power 计算明细
            "power_breakdown": {
                "intimacy": round(game_result.power_intimacy, 1) if hasattr(game_result, 'power_intimacy') else 0,
                "emotion": round(game_result.power_emotion, 1) if hasattr(game_result, 'power_emotion') else 0,
                "chaos": round(game_result.power_chaos, 1) if hasattr(game_result, 'power_chaos') else 0,
                "pure": round(game_result.power_pure, 1) if hasattr(game_result, 'power_pure') else 0,
                "buff": round(game_result.power_buff, 1) if hasattr(game_result, 'power_buff') else 0,
                "effect": round(game_result.power_effect, 1) if hasattr(game_result, 'power_effect') else 0,
            },
        }
        # Add event story message ID if a new story event was triggered
        if 'event_story_message_id' in dir() and event_story_message_id:
            extra_data["event_story"] = {
                "message_id": event_story_message_id,
                "event_type": game_result.new_event,
            }
    
    # 添加激活效果信息 (Tier 2 礼物状态)
    if effects_status and effects_status.get("has_effects"):
        extra_data["active_effects"] = effects_status.get("effects", [])
    
    # 添加瓶颈锁状态 (V4)
    if USE_V4_PIPELINE and v4_response and v4_response.extra_data:
        bottleneck_data = v4_response.extra_data.get("bottleneck")
        if bottleneck_data and bottleneck_data.get("is_locked"):
            extra_data["bottleneck"] = bottleneck_data
        
        # 添加临时升阶状态
        stage_boost_data = v4_response.extra_data.get("stage_boost")
        if stage_boost_data and stage_boost_data.get("active"):
            extra_data["stage_boost"] = stage_boost_data
    
    # 添加约会状态信息
    if date_info:
        extra_data["date"] = {
            "is_active": True,
            "scenario_name": date_info.get("scenario_name"),
            "scenario_icon": date_info.get("scenario_icon"),
            "message_count": date_info.get("message_count", 0),
            "required_messages": date_info.get("required_messages", 5),
            "status": date_info.get("status"),
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

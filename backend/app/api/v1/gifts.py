"""
Gift API Routes
===============

Handles gift sending with idempotency, catalog browsing, history, and status effects.

货币单位: 月石 (Moon Stones)
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from app.services.gift_service import gift_service
from app.services.effect_service import effect_service
from app.services.chat_repository import chat_repo
from app.models.database.gift_models import GiftTier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gifts")


# ============================================================================
# Request/Response Models
# ============================================================================

class SendGiftRequest(BaseModel):
    """Request to send a gift"""
    character_id: str
    gift_type: str
    idempotency_key: str = Field(..., description="Client-generated UUID for deduplication")
    session_id: Optional[str] = None
    trigger_ai_response: bool = Field(default=True, description="Auto-trigger AI response after gift")


class StatusEffectInfo(BaseModel):
    """Status effect information"""
    type: str
    duration_messages: int
    prompt_modifier: Optional[str] = None


class SendGiftResponse(BaseModel):
    """Response from sending a gift"""
    success: bool
    is_duplicate: bool = False
    gift_id: Optional[str] = None
    gift_type: Optional[str] = None
    gift_name: Optional[str] = None
    gift_name_cn: Optional[str] = None
    icon: Optional[str] = None
    tier: Optional[int] = None
    credits_deducted: Optional[int] = None
    new_balance: Optional[int] = None
    xp_awarded: Optional[int] = None
    level_up: bool = False
    new_level: Optional[int] = None
    status_effect_applied: Optional[StatusEffectInfo] = None
    cold_war_unlocked: bool = False
    ai_response: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class StatusEffectItem(BaseModel):
    """Status effect item for display"""
    type: str
    duration_messages: int
    prompt_modifier: str


class GiftCatalogItem(BaseModel):
    """Gift item in catalog"""
    gift_type: str
    name: str
    name_cn: Optional[str] = None
    description: Optional[str] = None
    description_cn: Optional[str] = None
    price: int
    xp_reward: int
    xp_multiplier: Optional[float] = 1.0
    icon: Optional[str] = None
    tier: int = 1
    category: Optional[str] = None
    emotion_boost: Optional[int] = None
    status_effect: Optional[StatusEffectItem] = None
    clears_cold_war: Optional[bool] = False
    force_emotion: Optional[str] = None
    level_boost: Optional[bool] = False
    requires_subscription: Optional[bool] = False
    sort_order: Optional[int] = 0


class GiftHistoryItem(BaseModel):
    """Gift in history"""
    id: str
    gift_type: str
    gift_name: str
    gift_name_cn: Optional[str] = None
    icon: Optional[str] = None
    gift_price: int
    xp_reward: int
    status: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None


class GiftSummary(BaseModel):
    """Gift summary for a character"""
    total_gifts: int
    total_spent: int
    total_xp_from_gifts: int
    top_gifts: List[dict]


# ============================================================================
# API Routes
# ============================================================================

@router.get("/catalog", response_model=List[GiftCatalogItem])
async def get_gift_catalog(tier: Optional[int] = None):
    """
    Get available gift catalog.
    
    Returns list of all purchasable gifts with pricing and XP rewards.
    Optionally filter by tier (1-4):
    - Tier 1: 日常消耗品 (Consumables)
    - Tier 2: 状态触发器 (State Triggers)
    - Tier 3: 关系加速器 (Speed Dating)
    - Tier 4: 榜一大哥尊享 (Whale Bait)
    """
    catalog = await gift_service.get_catalog(tier=tier)
    return [GiftCatalogItem(**g) for g in catalog]


@router.get("/catalog/by-tier")
async def get_gift_catalog_by_tier():
    """
    Get gift catalog organized by tier.
    
    Returns:
    {
        "1": [...],  # 日常消耗品
        "2": [...],  # 状态触发器
        "3": [...],  # 关系加速器
        "4": [...]   # 榜一大哥尊享
    }
    """
    by_tier = await gift_service.get_catalog_by_tier()
    return {str(k): v for k, v in by_tier.items()}


@router.get("/effects/{character_id}")
async def get_active_effects(character_id: str, req: Request):
    """
    Get active status effects for a character.
    
    Returns current effects from Tier 2 gifts (tipsy, maid_mode, truth_mode, etc.)
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    status = await effect_service.get_effect_status(user_id, character_id)
    return status


@router.post("/send", response_model=SendGiftResponse)
async def send_gift(request: SendGiftRequest, req: Request):
    """
    Send a gift to a character.
    
    **Idempotency**: Include a unique `idempotency_key` (UUID) with each request.
    If the same key is sent again (e.g., network retry), the original result
    is returned without duplicate charges.
    
    **Flow**:
    1. Validates gift type and user credits
    2. Deducts credits
    3. Creates gift record
    4. Awards XP
    5. Optionally triggers AI response
    """
    # Get user ID from auth
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    logger.info(f"Gift request: {request.gift_type} from {user_id} to {request.character_id}")
    
    # Send gift
    result = await gift_service.send_gift(
        user_id=user_id,
        character_id=request.character_id,
        gift_type=request.gift_type,
        idempotency_key=request.idempotency_key,
        session_id=request.session_id,
    )
    
    if not result["success"]:
        return SendGiftResponse(
            success=False,
            error=result.get("error"),
            message=result.get("message"),
        )
    
    # Build status effect info if present
    status_effect_info = None
    if result.get("status_effect_applied"):
        se = result["status_effect_applied"]
        status_effect_info = StatusEffectInfo(
            type=se["type"],
            duration_messages=se["duration"],
        )
    
    response = SendGiftResponse(
        success=True,
        is_duplicate=result.get("is_duplicate", False),
        gift_id=result.get("gift_id"),
        gift_type=result.get("gift", {}).get("gift_type"),
        gift_name=result.get("gift", {}).get("gift_name"),
        gift_name_cn=result.get("gift", {}).get("gift_name_cn"),
        icon=result.get("gift", {}).get("icon"),
        tier=result.get("gift", {}).get("tier"),
        credits_deducted=result.get("credits_deducted"),
        new_balance=result.get("new_balance"),
        xp_awarded=result.get("xp_awarded"),
        level_up=result.get("level_up", False),
        new_level=result.get("new_level"),
        status_effect_applied=status_effect_info,
        cold_war_unlocked=result.get("cold_war_unlocked", False),
    )
    
    # Record gift in stats (if not duplicate)
    if not result.get("is_duplicate"):
        try:
            from app.core.database import get_db
            from app.services.stats_service import stats_service
            
            async with get_db() as db:
                await stats_service.record_gift(
                    db, user_id, request.character_id, request.gift_type
                )
                logger.info(f"📊 Stats updated: gift recorded for user={user_id}, character={request.character_id}")
        except Exception as e:
            logger.warning(f"Failed to update gift stats: {e}")
    
    # Trigger AI response if requested and not duplicate
    if request.trigger_ai_response and not result.get("is_duplicate"):
        ai_response = await _trigger_gift_ai_response(
            user_id=user_id,
            character_id=request.character_id,
            session_id=request.session_id,
            gift_id=result["gift_id"],
            system_message=result.get("system_message"),
        )
        response.ai_response = ai_response
    
    return response


async def _trigger_gift_ai_response(
    user_id: str,
    character_id: str,
    session_id: Optional[str],
    gift_id: str,
    system_message: str,
) -> Optional[str]:
    """
    Trigger AI response to a gift via the full pipeline.
    
    **安全设计**:
    - 只有这个函数才能触发 verified GIFT_SEND
    - 用户不能通过聊天框伪造礼物
    - 完整走 L1 -> PhysicsEngine -> L2 管道
    
    Flow:
    1. 构造 verified gift event
    2. 调用完整 chat pipeline (L1 跳过分析，直接注入 GIFT_SEND)
    3. PhysicsEngine 执行 +50 情绪激增
    4. L2 生成感谢语
    """
    from app.services.llm_service import GrokService
    from app.services.chat_repository import chat_repo
    from app.services.physics_engine import PhysicsEngine, CharacterZAxis
    from app.services.game_engine import GameEngine, UserState
    from app.services.perception_engine import L1Result
    from app.api.v1.characters import CHARACTERS
    
    try:
        # Get or find session
        if not session_id:
            session = await chat_repo.get_session_by_character(user_id, character_id)
            if session:
                session_id = session["session_id"]
        
        if not session_id:
            logger.warning(f"No session found for gift AI response: {user_id} / {character_id}")
            return None
        
        session = await chat_repo.get_session(session_id)
        if not session:
            return None
        
        # Get character info
        character_name = session["character_name"]
        
        # Get gift details
        gift = await gift_service.get_gift(gift_id)
        gift_name = gift.get("gift_name_cn") or gift.get("gift_name", "礼物")
        gift_icon = gift.get("icon", "🎁")
        gift_price = gift.get("gift_price", 10)
        
        # =========================================================================
        # 1. 调用 L1 分析上下文 (带 VERIFIED 标记)
        # =========================================================================
        # 构造带 VERIFIED 标记的消息，让 L1 分析上下文情感
        # L1 看到 [VERIFIED_GIFT] 会输出 GIFT_SEND，但 sentiment 由上下文决定
        from app.services.perception_engine import perception_engine
        from app.services.intimacy_service import intimacy_service
        
        # 获取当前亲密度等级
        intimacy_status = await intimacy_service.get_intimacy_status(user_id, character_id)
        intimacy_level = intimacy_status.get("current_level", 1) if intimacy_status else 1
        
        # 获取最近对话上下文
        history = await chat_repo.get_messages(session_id, limit=5)
        context_messages = [{"role": m["role"], "content": m["content"]} for m in history]
        
        # 构造 VERIFIED 消息让 L1 分析
        verified_message = f"[VERIFIED_GIFT:{gift_name}] 用户送出了 {gift_icon} {gift_name}"
        
        # 调用 L1 (会根据上下文分析 sentiment)
        l1_result = await perception_engine.analyze(
            message=verified_message,
            intimacy_level=intimacy_level,
            context_messages=context_messages
        )
        
        # 强制覆盖 intent 为 GIFT_SEND (即使 L1 输出其他值)
        # 但保留 L1 分析的 sentiment_score
        original_sentiment = l1_result.sentiment_score
        verified_l1_result = L1Result(
            safety_flag="SAFE",
            difficulty_rating=0,  # 给的，不是要的
            intent_category="GIFT_SEND",  # 强制覆盖为 GIFT_SEND
            sentiment_score=original_sentiment,  # 保留 L1 分析的 sentiment
            is_nsfw=False,
            reasoning=f"[VERIFIED_TRANSACTION] L1 sentiment={original_sentiment:.2f}"
        )
        
        logger.info(f"🎁 Verified gift via L1: {gift_icon} {gift_name}, sentiment={original_sentiment:.2f}")
        
        # =========================================================================
        # 2. 执行 PhysicsEngine (情绪 +50)
        # =========================================================================
        # 加载当前用户状态
        game_engine = GameEngine()
        user_state = await game_engine._load_user_state(user_id, character_id)
        old_emotion = user_state.emotion
        
        # 获取角色配置
        char_config = CharacterZAxis.from_character_id(character_id)
        
        # 计算情绪增量 (GIFT_SEND = +50)
        l1_dict = {
            'sentiment_score': verified_l1_result.sentiment_score,
            'intent_category': verified_l1_result.intent_category,
        }
        state_dict = {
            'emotion': user_state.emotion,
            'last_intents': user_state.last_intents,
        }
        
        new_emotion = PhysicsEngine.update_state(state_dict, l1_dict, char_config)
        user_state.emotion = new_emotion
        
        # 更新防刷列表
        user_state.last_intents.append("GIFT_SEND")
        if len(user_state.last_intents) > 10:
            user_state.last_intents = user_state.last_intents[-10:]
        
        # 保存更新后的状态
        await game_engine._save_user_state(user_state)
        
        logger.info(f"🎁 PhysicsEngine: emotion {old_emotion} -> {new_emotion} (GIFT_SEND +50)")
        
        # =========================================================================
        # 3. 存储礼物事件到聊天记录
        # =========================================================================
        gift_event_message = f"[送出礼物] {gift_icon} {gift_name}"
        await chat_repo.add_message(
            session_id=session_id,
            role="user",
            content=gift_event_message,
            tokens_used=0,
        )
        
        # Invalidate context cache
        from app.core.redis import get_redis
        redis = await get_redis()
        cache_key = f"session:{session_id}:context"
        await redis.delete(cache_key)
        
        # =========================================================================
        # 4. L2 生成感谢语
        # =========================================================================
        grok = GrokService()
        
        # Get recent messages for context
        history = await chat_repo.get_messages(session_id, limit=10)
        
        # 根据礼物价值和当前情绪调整反应强度
        if gift_price >= 500:
            intensity = "非常激动和感动，这是一份珍贵的礼物！用更长更热情的回复表达你的感谢"
        elif gift_price >= 100:
            intensity = "惊喜和感动，用热情的语气回复"
        else:
            intensity = "开心和感谢，用温暖的语气回复"
        
        # 根据情绪状态调整语气
        emotion_hint = ""
        if new_emotion > 50:
            emotion_hint = "你现在心情非常好，可以撒娇、说甜蜜的话"
        elif new_emotion > 20:
            emotion_hint = "你现在心情不错，态度温暖亲切"
        elif new_emotion < -20:
            emotion_hint = "虽然你之前心情不好，但收到礼物后开始消气了，态度缓和下来"
        
        conversation = [
            {"role": "system", "content": f"""You are {character_name}, a warm and affectionate AI companion.
{system_message}

## 当前状态
- 情绪值: {new_emotion} (从 {old_emotion} 变化)
- {emotion_hint}

## 回复要求
- 用中文回复（除非用户一直用英文）
- 表达真实的惊喜和感谢，{intensity}
- 回复要有感情、有个性，像真人朋友收到礼物一样反应
- 可以使用表情符号增加表达力
- 回复长度：4-6句话，要足够表达你的喜悦和感谢
- 可以提到你会怎么珍藏/使用这个礼物
- 可以撒娇或说一些甜蜜的话
"""}
        ]
        
        # Add recent history
        for msg in history:
            conversation.append({"role": msg["role"], "content": msg["content"]})
        
        # Generate response
        result = await grok.chat_completion(
            messages=conversation,
            temperature=0.9,
            max_tokens=500
        )
        
        ai_response = result["choices"][0]["message"]["content"]
        
        # Store AI response
        await chat_repo.add_message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            tokens_used=result.get("usage", {}).get("total_tokens", 0),
        )
        
        # Mark gift as acknowledged
        await gift_service.mark_acknowledged(gift_id)
        
        logger.info(f"🎁 Gift AI response generated: {ai_response[:50]}...")
        return ai_response
        
    except Exception as e:
        logger.error(f"Failed to generate gift AI response: {e}")
        import traceback
        traceback.print_exc()
        return None


@router.get("/history", response_model=List[GiftHistoryItem])
async def get_gift_history(
    character_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    req: Request = None,
):
    """
    Get gift history for the current user.
    
    Optionally filter by character_id.
    """
    user = getattr(req.state, "user", None) if req else None
    user_id = str(user.user_id) if user else "demo-user-123"
    
    gifts = await gift_service.get_gift_history(
        user_id=user_id,
        character_id=character_id,
        limit=limit,
        offset=offset,
    )
    
    return [GiftHistoryItem(**g) for g in gifts]


@router.get("/summary/{character_id}", response_model=GiftSummary)
async def get_gift_summary(character_id: str, req: Request):
    """
    Get gift summary for a specific character.
    
    Returns aggregated stats useful for AI memory context.
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    summary = await gift_service.get_gift_summary(user_id, character_id)
    return GiftSummary(**summary)


@router.get("/{gift_id}")
async def get_gift(gift_id: str, req: Request):
    """Get gift details by ID"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    gift = await gift_service.get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="Gift not found")
    
    # Security: only owner can view
    if gift["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return gift


@router.post("/{gift_id}/acknowledge")
async def acknowledge_gift(gift_id: str, req: Request):
    """
    Manually acknowledge a gift (mark as AI responded).
    
    Usually called automatically after AI responds,
    but can be called manually if needed.
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    gift = await gift_service.get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="Gift not found")
    
    if gift["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = await gift_service.mark_acknowledged(gift_id)
    return {"success": success, "status": "acknowledged"}

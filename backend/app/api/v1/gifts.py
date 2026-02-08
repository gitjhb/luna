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
    bottleneck_unlocked: bool = False
    bottleneck_unlock_message: Optional[str] = None
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
        bottleneck_unlocked=result.get("bottleneck_unlocked", False),
        bottleneck_unlock_message=result.get("bottleneck_unlock_message"),
    )
    
    # Record gift in stats (if not duplicate)
    if not result.get("is_duplicate"):
        try:
            from app.core.database import get_db
            from app.services.stats_service import stats_service
            
            # 获取礼物中文名称（优先用中文，fallback 到英文）
            gift_display_name = (
                result.get("gift", {}).get("gift_name_cn") or 
                result.get("gift", {}).get("gift_name") or 
                request.gift_type
            )
            gift_icon = result.get("gift", {}).get("icon", "🎁")
            
            async with get_db() as db:
                await stats_service.record_gift(
                    db, user_id, request.character_id, 
                    gift_type=request.gift_type,
                    gift_name=gift_display_name,
                    gift_icon=gift_icon
                )
                logger.info(f"📊 Stats updated: gift recorded for user={user_id}, character={request.character_id}")
        except Exception as e:
            logger.warning(f"Failed to update gift stats: {e}")
    
    # 使用 gift_service 生成的 AI 回复（已包含角色人设）
    if not result.get("is_duplicate"):
        response.ai_response = result.get("ai_response")
        
        # 自动插入礼物消息到聊天记录
        if request.session_id:
            try:
                gift_icon = result.get("gift", {}).get("icon", "🎁")
                gift_name = result.get("gift", {}).get("gift_name_cn") or result.get("gift", {}).get("gift_name", "礼物")
                
                # 插入礼物事件消息
                await chat_repo.add_message(
                    session_id=request.session_id,
                    role="system",
                    content=f"[送出礼物] {gift_icon} {gift_name}",
                    tokens_used=0,
                )
                
                # 插入 AI 回复消息
                if result.get("ai_response"):
                    await chat_repo.add_message(
                        session_id=request.session_id,
                        role="assistant",
                        content=result["ai_response"],
                        tokens_used=0,
                    )
                
                logger.info(f"💾 Gift messages saved to session {request.session_id}")
            except Exception as e:
                logger.warning(f"Failed to save gift messages: {e}")
    
    return response


# NOTE: _trigger_gift_ai_response 已删除 (P3 清理)
# 礼物AI回复现在由 gift_service.generate_ai_gift_response() 处理


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

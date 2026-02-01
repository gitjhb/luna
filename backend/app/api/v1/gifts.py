"""
Gift API Routes
===============

Handles gift sending with idempotency, catalog browsing, and history.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging

from app.services.gift_service import gift_service
from app.services.chat_repository import chat_repo

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


class SendGiftResponse(BaseModel):
    """Response from sending a gift"""
    success: bool
    is_duplicate: bool = False
    gift_id: Optional[str] = None
    gift_type: Optional[str] = None
    gift_name: Optional[str] = None
    gift_name_cn: Optional[str] = None
    icon: Optional[str] = None
    credits_deducted: Optional[int] = None
    new_balance: Optional[int] = None
    xp_awarded: Optional[int] = None
    level_up: bool = False
    new_level: Optional[int] = None
    ai_response: Optional[str] = None  # AI's immediate response if trigger_ai_response=True
    error: Optional[str] = None
    message: Optional[str] = None


class GiftCatalogItem(BaseModel):
    """Gift item in catalog"""
    gift_type: str
    name: str
    name_cn: Optional[str] = None
    description: Optional[str] = None
    description_cn: Optional[str] = None
    price: int
    xp_reward: int
    icon: Optional[str] = None
    category: Optional[str] = "normal"
    is_spicy: Optional[bool] = False
    requires_subscription: Optional[bool] = False
    triggers_scene: Optional[str] = None
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
async def get_gift_catalog():
    """
    Get available gift catalog.
    
    Returns list of all purchasable gifts with pricing and XP rewards.
    """
    catalog = await gift_service.get_catalog()
    return [GiftCatalogItem(**g) for g in catalog]


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
    
    response = SendGiftResponse(
        success=True,
        is_duplicate=result.get("is_duplicate", False),
        gift_id=result.get("gift_id"),
        gift_type=result.get("gift", {}).get("gift_type"),
        gift_name=result.get("gift", {}).get("gift_name"),
        gift_name_cn=result.get("gift", {}).get("gift_name_cn"),
        icon=result.get("gift", {}).get("icon"),
        credits_deducted=result.get("credits_deducted"),
        new_balance=result.get("new_balance"),
        xp_awarded=result.get("xp_awarded"),
        level_up=result.get("level_up", False),
        new_level=result.get("new_level"),
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
    Trigger AI response to a gift.
    
    Injects gift system message into context and gets AI response.
    Marks gift as acknowledged after response.
    """
    from app.services.llm_service import GrokService
    from app.services.chat_repository import chat_repo
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
        
        # Build conversation for AI
        grok = GrokService()
        
        # Get gift details for the message
        gift = await gift_service.get_gift(gift_id)
        gift_name = gift.get("gift_name_cn") or gift.get("gift_name", "礼物")
        gift_icon = gift.get("icon", "🎁")
        
        # Store gift event as a user message in chat history
        # This ensures the gift is remembered in conversation context
        gift_event_message = f"[送出礼物] {gift_icon} {gift_name}"
        await chat_repo.add_message(
            session_id=session_id,
            role="user",
            content=gift_event_message,
            tokens_used=0,
        )
        logger.info(f"Gift event stored in chat history: {gift_event_message}")
        
        # Invalidate context cache so next chat includes the gift event
        from app.core.redis import get_redis
        redis = await get_redis()
        cache_key = f"session:{session_id}:context"
        await redis.delete(cache_key)
        logger.info(f"Context cache invalidated for session {session_id}")
        
        # Get recent messages for context (now includes the gift event)
        history = await chat_repo.get_messages(session_id, limit=10)
        
        # Get gift price for reaction intensity
        gift_price = gift.get("gift_price", 10)
        
        # Reaction intensity based on gift value
        if gift_price >= 500:
            intensity = "非常激动和感动，这是一份珍贵的礼物！用更长更热情的回复表达你的感谢"
        elif gift_price >= 100:
            intensity = "惊喜和感动，用热情的语气回复"
        else:
            intensity = "开心和感谢，用温暖的语气回复"
        
        conversation = [
            {"role": "system", "content": f"""You are {character_name}, a warm and affectionate AI companion.
{system_message}

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
        
        # Generate response - 更长的回复
        result = await grok.chat_completion(
            messages=conversation,
            temperature=0.9,
            max_tokens=500
        )
        
        ai_response = result["choices"][0]["message"]["content"]
        
        # Store AI response as message
        await chat_repo.add_message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            tokens_used=result.get("usage", {}).get("total_tokens", 0),
        )
        
        # Mark gift as acknowledged
        await gift_service.mark_acknowledged(gift_id)
        
        logger.info(f"Gift AI response generated for {gift_id}: {ai_response[:50]}...")
        return ai_response
        
    except Exception as e:
        logger.error(f"Failed to generate gift AI response: {e}")
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

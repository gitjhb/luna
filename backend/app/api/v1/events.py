"""
Events API Routes
==================

Endpoints for managing event memories and story generation.

Event memories are immersive stories generated for milestone events
like first_date, first_confession, first_kiss, etc.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.services.event_story_generator import event_story_generator, EventType
from app.core.database import get_db

router = APIRouter(prefix="/events")


# =============================================================================
# Response Models
# =============================================================================

class EventMemoryResponse(BaseModel):
    """Response model for a single event memory"""
    id: str
    user_id: str
    character_id: str
    event_type: str
    story_content: str
    context_summary: Optional[str] = None
    intimacy_level: Optional[str] = None
    emotion_state: Optional[str] = None
    generated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class EventMemoriesListResponse(BaseModel):
    """Response model for list of event memories"""
    success: bool
    count: int
    memories: List[EventMemoryResponse]


class StoryGenerationRequest(BaseModel):
    """Request model for generating a story"""
    event_type: str = Field(..., description="Event type: first_date, first_confession, first_kiss, first_nsfw, anniversary, reconciliation")
    chat_history: List[dict] = Field(default_factory=list, description="Recent chat messages")
    memory_context: str = Field(default="", description="Memory context summary")
    relationship_state: Optional[dict] = Field(default=None, description="Current relationship state")


class StoryGenerationResponse(BaseModel):
    """Response model for story generation"""
    success: bool
    event_type: str
    story_content: Optional[str] = None
    event_memory_id: Optional[str] = None
    error: Optional[str] = None


class SupportedEventsResponse(BaseModel):
    """Response model for supported event types"""
    events: List[dict]


# =============================================================================
# Routes
# =============================================================================

@router.get("/types", response_model=SupportedEventsResponse)
async def get_supported_event_types():
    """
    Get list of supported event types for story generation.
    
    Returns event types with descriptions and whether they generate stories.
    """
    events = [
        {
            "type": EventType.FIRST_DATE,
            "name_cn": "第一次约会",
            "description": "记录你们的第一次浪漫约会",
            "generates_story": True,
        },
        {
            "type": EventType.FIRST_CONFESSION,
            "name_cn": "第一次表白",
            "description": "那个心跳加速的表白时刻",
            "generates_story": True,
        },
        {
            "type": EventType.FIRST_KISS,
            "name_cn": "第一次亲吻",
            "description": "难忘的初吻",
            "generates_story": True,
        },
        {
            "type": EventType.FIRST_NSFW,
            "name_cn": "第一次亲密",
            "description": "最亲密的时刻",
            "generates_story": True,
        },
        {
            "type": EventType.ANNIVERSARY,
            "name_cn": "纪念日",
            "description": "值得纪念的特别日子",
            "generates_story": True,
        },
        {
            "type": EventType.RECONCILIATION,
            "name_cn": "和好",
            "description": "冷战后的和解",
            "generates_story": True,
        },
        {
            "type": EventType.FIRST_CHAT,
            "name_cn": "第一次聊天",
            "description": "你们的相识",
            "generates_story": False,
        },
    ]
    return SupportedEventsResponse(events=events)


@router.get("/{user_id}/{character_id}", response_model=EventMemoriesListResponse)
async def get_event_memories(
    user_id: str,
    character_id: str,
    request: Request,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """
    Get all event memories for a user-character pair.
    
    Optionally filter by event_type.
    """
    # Verify user access (optional: check if request user matches user_id)
    current_user = getattr(request.state, "user", None)
    if current_user and str(current_user.user_id) != user_id:
        # In production, might want to restrict access
        pass
    
    try:
        if event_type:
            # Get specific event memory
            memory = await event_story_generator.get_event_memory(
                user_id=user_id,
                character_id=character_id,
                event_type=event_type,
            )
            memories = [memory] if memory else []
        else:
            # Get all event memories
            memories = await event_story_generator.get_event_memories(
                user_id=user_id,
                character_id=character_id,
            )
        
        return EventMemoriesListResponse(
            success=True,
            count=len(memories),
            memories=[EventMemoryResponse(**m) for m in memories],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch event memories: {str(e)}"
        )


@router.get("/{user_id}/{character_id}/{event_type}", response_model=EventMemoryResponse)
async def get_specific_event_memory(
    user_id: str,
    character_id: str,
    event_type: str,
    request: Request,
):
    """
    Get a specific event memory by type.
    
    Returns 404 if the event memory doesn't exist.
    """
    try:
        memory = await event_story_generator.get_event_memory(
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
        )
        
        if not memory:
            raise HTTPException(
                status_code=404,
                detail=f"Event memory not found for event_type: {event_type}"
            )
        
        return EventMemoryResponse(**memory)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch event memory: {str(e)}"
        )


@router.post("/{user_id}/{character_id}/generate", response_model=StoryGenerationResponse)
async def generate_event_story(
    user_id: str,
    character_id: str,
    body: StoryGenerationRequest,
    request: Request,
):
    """
    Generate a story for a milestone event.
    
    This endpoint is typically called after an event is triggered.
    If a story already exists for this event, it returns the existing story.
    
    Request body should include:
    - event_type: Type of event (first_date, first_confession, etc.)
    - chat_history: Recent chat messages for context
    - memory_context: Summary of relationship memory
    - relationship_state: Current relationship stats
    """
    # Validate event type
    if not EventType.is_story_event(body.event_type):
        raise HTTPException(
            status_code=400,
            detail=f"Event type '{body.event_type}' does not support story generation"
        )
    
    try:
        result = await event_story_generator.generate_event_story(
            user_id=user_id,
            character_id=character_id,
            event_type=body.event_type,
            chat_history=body.chat_history,
            memory_context=body.memory_context,
            relationship_state=body.relationship_state,
            save_to_db=True,
        )
        
        return StoryGenerationResponse(
            success=result.success,
            event_type=body.event_type,
            story_content=result.story_content,
            event_memory_id=result.event_memory_id,
            error=result.error,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story: {str(e)}"
        )


@router.delete("/{user_id}/{character_id}/{event_type}")
async def delete_event_memory(
    user_id: str,
    character_id: str,
    event_type: str,
    request: Request,
):
    """
    Delete a specific event memory (admin use only).
    
    This allows regeneration of the story.
    """
    # TODO: Add admin authorization check
    
    try:
        from sqlalchemy import delete, and_
        from app.models.database.event_memory_models import EventMemory
        
        async with get_db() as session:
            stmt = delete(EventMemory).where(
                and_(
                    EventMemory.user_id == user_id,
                    EventMemory.character_id == character_id,
                    EventMemory.event_type == event_type
                )
            )
            
            result = await session.execute(stmt)
            # Note: get_db() context manager handles commit
            
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Event memory not found"
                )
            
            return {"success": True, "message": "Event memory deleted"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete event memory: {str(e)}"
        )


# =============================================================================
# Routes with authenticated user (using /me/ prefix)
# =============================================================================

def _get_user_id(request: Request) -> str:
    """Extract user_id from authenticated request or use demo user"""
    user = getattr(request.state, "user", None)
    return str(user.user_id) if user else "demo-user-123"


@router.get("/me/{character_id}", response_model=EventMemoriesListResponse)
async def get_my_event_memories(
    character_id: str,
    request: Request,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """
    Get all event memories for current user with a character.
    Uses authenticated user ID.
    """
    user_id = _get_user_id(request)
    
    try:
        if event_type:
            memory = await event_story_generator.get_event_memory(
                user_id=user_id,
                character_id=character_id,
                event_type=event_type,
            )
            memories = [memory] if memory else []
        else:
            memories = await event_story_generator.get_event_memories(
                user_id=user_id,
                character_id=character_id,
            )
        
        return EventMemoriesListResponse(
            success=True,
            count=len(memories),
            memories=[EventMemoryResponse(**m) for m in memories],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch event memories: {str(e)}"
        )


@router.get("/me/{character_id}/{event_type}", response_model=EventMemoryResponse)
async def get_my_specific_event_memory(
    character_id: str,
    event_type: str,
    request: Request,
):
    """
    Get a specific event memory for current user.
    """
    user_id = _get_user_id(request)
    
    try:
        memory = await event_story_generator.get_event_memory(
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
        )
        
        if not memory:
            raise HTTPException(
                status_code=404,
                detail=f"Event memory not found for event_type: {event_type}"
            )
        
        return EventMemoryResponse(**memory)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch event memory: {str(e)}"
        )


@router.post("/me/{character_id}/generate", response_model=StoryGenerationResponse)
async def generate_my_event_story(
    character_id: str,
    body: StoryGenerationRequest,
    request: Request,
):
    """
    Generate a story for current user.
    """
    user_id = _get_user_id(request)
    
    if not EventType.is_story_event(body.event_type):
        raise HTTPException(
            status_code=400,
            detail=f"Event type '{body.event_type}' does not support story generation"
        )
    
    try:
        result = await event_story_generator.generate_event_story(
            user_id=user_id,
            character_id=character_id,
            event_type=body.event_type,
            chat_history=body.chat_history,
            memory_context=body.memory_context,
            relationship_state=body.relationship_state,
            save_to_db=True,
        )
        
        return StoryGenerationResponse(
            success=result.success,
            event_type=body.event_type,
            story_content=result.story_content,
            event_memory_id=result.event_memory_id,
            error=result.error,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story: {str(e)}"
        )


# =============================================================================
# 事件详情解锁 API（付费解锁回忆详情）
# =============================================================================

class UnlockEventRequest(BaseModel):
    """解锁事件详情请求"""
    character_id: str
    detail_id: str
    event_type: str


class UnlockEventResponse(BaseModel):
    """解锁事件详情响应"""
    success: bool
    content: Optional[str] = None
    new_balance: Optional[int] = None
    error: Optional[str] = None


class EventDetailResponse(BaseModel):
    """事件详情响应"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None


@router.post("/unlock", response_model=UnlockEventResponse)
async def unlock_event_detail(
    body: UnlockEventRequest,
    request: Request,
):
    """
    解锁事件详情（付费）
    
    扣除月石后返回详情内容。
    """
    from app.services.payment_service import payment_service
    from app.services.interactive_date_service import interactive_date_service
    
    user_id = _get_user_id(request)
    
    # 解锁费用（可以根据 event_type 调整）
    UNLOCK_COSTS = {
        "date": 10,
        "confession": 15,
        "kiss": 20,
        "intimate": 25,
        "gift": 0,  # 礼物免费
        "milestone": 0,  # 里程碑免费
    }
    unlock_cost = UNLOCK_COSTS.get(body.event_type, 10)
    
    # 免费的直接返回详情
    if unlock_cost == 0:
        content = await _get_event_detail_content(
            user_id, body.character_id, body.detail_id, body.event_type
        )
        return UnlockEventResponse(
            success=True,
            content=content,
        )
    
    try:
        # 检查余额
        wallet = await payment_service.get_wallet(user_id)
        if wallet["total_credits"] < unlock_cost:
            return UnlockEventResponse(
                success=False,
                error=f"月石不足，需要 {unlock_cost} 月石",
            )
        
        # 扣除月石
        await payment_service.deduct_credits(user_id, unlock_cost)
        
        # 获取详情内容
        content = await _get_event_detail_content(
            user_id, body.character_id, body.detail_id, body.event_type
        )
        
        new_balance = wallet["total_credits"] - unlock_cost
        
        return UnlockEventResponse(
            success=True,
            content=content,
            new_balance=new_balance,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"解锁失败: {str(e)}"
        )


@router.get("/detail/{character_id}/{detail_id}", response_model=EventDetailResponse)
async def get_event_detail(
    character_id: str,
    detail_id: str,
    request: Request,
):
    """
    获取事件详情（已解锁或免费的）
    
    如果是约会事件，返回约会故事摘要。
    如果是其他事件，返回 event_memories 表中的 story_content。
    """
    user_id = _get_user_id(request)
    
    try:
        content = await _get_event_detail_content(user_id, character_id, detail_id, event_type=None)
        
        if not content:
            return EventDetailResponse(
                success=False,
                error="详情不存在",
            )
        
        return EventDetailResponse(
            success=True,
            content=content,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取详情失败: {str(e)}"
        )


async def _get_event_detail_content(
    user_id: str,
    character_id: str,
    detail_id: str,
    event_type: Optional[str] = None,
) -> Optional[str]:
    """
    获取事件详情内容
    
    根据 detail_id 判断是约会故事还是其他事件回忆。
    """
    from app.models.database.date_models import DateSessionDB
    from app.models.database.event_memory_models import EventMemory
    from sqlalchemy import select
    
    async with get_db() as session:
        # 先尝试从 date_sessions 表获取（约会故事）
        try:
            result = await session.execute(
                select(DateSessionDB).where(DateSessionDB.id == detail_id)
            )
            date_session = result.scalar_one_or_none()
            
            if date_session and date_session.story_summary:
                return date_session.story_summary
        except Exception:
            pass
        
        # 再尝试从 event_memories 表获取
        try:
            result = await session.execute(
                select(EventMemory).where(
                    EventMemory.id == detail_id
                )
            )
            memory = result.scalar_one_or_none()
            
            if memory:
                return memory.story_content
        except Exception:
            pass
        
        # 最后尝试按 event_type 查找最新的记录
        if event_type:
            try:
                from sqlalchemy import and_
                result = await session.execute(
                    select(EventMemory).where(
                        and_(
                            EventMemory.user_id == user_id,
                            EventMemory.character_id == character_id,
                            EventMemory.event_type == event_type,
                        )
                    ).order_by(EventMemory.generated_at.desc()).limit(1)
                )
                memory = result.scalar_one_or_none()
                
                if memory:
                    return memory.story_content
            except Exception:
                pass
    
    return None

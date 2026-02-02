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

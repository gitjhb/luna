"""
Stories API Routes - 故事模式
=============================

Interactive branching narrative system with LLM-generated content.

Endpoints:
- POST /stories/start - Begin a new story
- POST /stories/choice - Make a story choice
- GET /stories/current - Get current story state
- POST /stories/end - End story session
- GET /stories/types - Get available story types
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from pydantic import BaseModel

from app.services.story_mode_service import story_mode_service

router = APIRouter(prefix="/stories")


def _get_user_id(req: Request) -> str:
    """Extract user_id from request state (set by auth middleware)."""
    user = getattr(req.state, "user", None)
    return str(user.user_id) if user else "demo-user-123"


def _get_intimacy_stage(user_id: str, character_id: str) -> str:
    """Get user's intimacy stage with character."""
    try:
        # This would normally call intimacy service
        # For now return a default
        return "friend"
    except Exception:
        return "strangers"


# =============================================================================
# Request Models
# =============================================================================

class StartStoryRequest(BaseModel):
    character_id: str
    story_type: Optional[str] = "romance"
    setup_request: Optional[str] = None  # User's specific story request


class StoryChoiceRequest(BaseModel):
    session_id: str
    action: str  # continue, hotter, softer, faster, end, new


class EndStoryRequest(BaseModel):
    session_id: str


# =============================================================================
# Story Type Endpoints
# =============================================================================

@router.get("/types")
async def get_story_types(
    req: Request,
    character_id: Optional[str] = None,
):
    """
    Get available story types.
    
    Returns types filtered by user's intimacy stage with the character.
    Some spicy story types require higher intimacy levels.
    """
    user_id = _get_user_id(req)
    
    # Get intimacy stage to filter available types
    intimacy_stage = "friend"  # Default
    if character_id:
        intimacy_stage = _get_intimacy_stage(user_id, character_id)
    
    types = story_mode_service.get_story_types(intimacy_stage)
    
    return {
        "success": True,
        "types": types,
        "total": len(types),
        "intimacy_stage": intimacy_stage,
    }


# =============================================================================
# Story Session Endpoints
# =============================================================================

@router.post("/start")
async def start_story(request: StartStoryRequest, req: Request):
    """
    Begin a new story session.
    
    Creates a new interactive story with the specified type and character.
    Returns the story introduction and first segment.
    
    Args:
        character_id: The AI character to feature in the story
        story_type: Type of story (romance, adventure, emotional, etc.)
        setup_request: Optional specific setup request from user
    
    Returns:
        session_id: Unique story session ID
        intro: Story introduction/setup
        content: First story segment
        buttons: Navigation choices for user
    """
    user_id = _get_user_id(req)
    
    # Check if user already has an active story
    active = await story_mode_service.get_active_session(user_id, request.character_id)
    if active:
        return {
            "success": False,
            "error": "已有进行中的故事",
            "active_session": {
                "id": active["id"],
                "title": active.get("story_title", ""),
                "segment": active.get("current_segment", 0),
            },
            "hint": "请先结束当前故事，或使用 /stories/end 接口",
        }
    
    # Validate story type
    available_types = story_mode_service.get_story_types()
    type_ids = [t["id"] for t in available_types if not t.get("locked")]
    
    if request.story_type not in type_ids:
        # Check if locked
        locked_types = [t for t in available_types if t.get("locked")]
        for t in locked_types:
            if t["id"] == request.story_type:
                raise HTTPException(
                    status_code=403,
                    detail=t.get("unlock_hint", "该故事类型尚未解锁"),
                )
        # Invalid type
        raise HTTPException(
            status_code=400,
            detail=f"无效的故事类型: {request.story_type}",
        )
    
    result = await story_mode_service.start_story(
        user_id=user_id,
        character_id=request.character_id,
        story_type=request.story_type,
        setup_request=request.setup_request,
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "故事生成失败"),
        )
    
    return result


@router.post("/choice")
async def make_story_choice(request: StoryChoiceRequest, req: Request):
    """
    Make a choice in the current story.
    
    Progresses the narrative based on user's choice:
    - continue: Continue with current style
    - hotter: Make the narrative more intense
    - softer: Make the narrative more gentle
    - faster: Speed up the pacing
    - end: End the story gracefully
    - new: Clear and start fresh
    
    Returns:
        content: Next story segment or ending
        buttons: Available choices for next action
        is_ending: Whether the story has concluded
        rewards: XP/intimacy rewards (if ending)
    """
    valid_actions = ["continue", "hotter", "softer", "faster", "end", "new"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"无效的选择: {request.action}。可用选项: {valid_actions}",
        )
    
    result = await story_mode_service.continue_story(
        session_id=request.session_id,
        action=request.action,
    )
    
    return result


@router.get("/current")
async def get_current_story(
    req: Request,
    character_id: Optional[str] = None,
):
    """
    Get the current active story session.
    
    Returns the user's in-progress story with all segments and state.
    """
    user_id = _get_user_id(req)
    
    session = await story_mode_service.get_active_session(user_id, character_id)
    
    if not session:
        return {
            "has_active_story": False,
            "message": "没有进行中的故事",
        }
    
    return {
        "has_active_story": True,
        "session": session,
        "buttons": story_mode_service.STORY_BUTTONS,
    }


@router.get("/session/{session_id}")
async def get_story_session(session_id: str, req: Request):
    """
    Get a specific story session by ID.
    
    Can retrieve both active and completed stories for history.
    """
    session = await story_mode_service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="故事会话不存在",
        )
    
    return {
        "success": True,
        "session": session,
    }


@router.post("/end")
async def end_story(request: EndStoryRequest, req: Request):
    """
    End the current story session.
    
    Completes the story and awards XP/intimacy based on engagement:
    - Base reward: 10 XP
    - Per segment: +2 XP
    
    Returns:
        content: Ending message
        rewards: XP and intimacy rewards earned
    """
    result = await story_mode_service.continue_story(
        session_id=request.session_id,
        action="end",
    )
    
    return result


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.post("/abandon")
async def abandon_story(request: EndStoryRequest, req: Request):
    """
    Abandon the current story without rewards.
    
    Use this when user wants to quit without completing.
    """
    session = await story_mode_service.get_session(request.session_id)
    
    if not session:
        return {
            "success": True,
            "message": "故事已不存在",
        }
    
    await story_mode_service._clear_session(request.session_id)
    
    return {
        "success": True,
        "message": "故事已放弃",
    }


@router.get("/detect")
async def detect_story_trigger(text: str):
    """
    Check if text would trigger story mode.
    
    Utility endpoint for detecting story mode activation phrases.
    """
    should_trigger = story_mode_service.should_enter_story_mode(text)
    
    return {
        "trigger": should_trigger,
        "text": text,
    }

"""
User Insights API Routes
========================

API endpoints for accessing and managing user learning/insights data.

Endpoints:
- GET /insights/{user_id} - Get learned user profile
- POST /insights/{user_id}/feedback - Apply manual corrections
- DELETE /insights/{user_id} - Clear user learning data
- GET /insights/{user_id}/style-hints - Get style hints for prompts
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from app.services.user_learning_service import user_learning_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights")


# =============================================================================
# Request/Response Models
# =============================================================================

class StyleInfo(BaseModel):
    """User communication style information"""
    message_length: Optional[str] = Field(None, description="short/medium/long")
    emoji_usage: Optional[str] = Field(None, description="none/rare/moderate/frequent")
    tone: Optional[str] = Field(None, description="formal/casual/playful/romantic")
    punctuation: Optional[str] = Field(None, description="minimal/normal/expressive")
    communication_style: Optional[str] = Field(None, description="direct/indirect/expressive")
    emotional_expression: Optional[str] = Field(None, description="reserved/moderate/expressive")
    common_phrases: Optional[List[str]] = None
    analysis_count: Optional[int] = None
    last_analysis: Optional[str] = None


class ActivityInfo(BaseModel):
    """User activity pattern information"""
    peak_hours: Optional[List[int]] = Field(None, description="Top 3 active hours (0-23)")
    preferred_slots: Optional[List[str]] = Field(None, description="morning/afternoon/evening/night")
    total_messages: Optional[int] = None


class TopicInterest(BaseModel):
    """User topic interest"""
    topic: str
    score: float
    count: int
    category: Optional[str] = None
    last_mentioned: Optional[str] = None


class UserInsightsResponse(BaseModel):
    """Complete user insights profile"""
    user_id: str
    has_data: bool
    style: Optional[Dict[str, Any]] = None
    activity: Optional[ActivityInfo] = None
    interests: List[TopicInterest] = []
    updated_at: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request to apply manual feedback"""
    feedback_type: str = Field(
        ..., 
        description="Type of feedback: style_tone, style_length, style_emoji, style_expression"
    )
    value: Any = Field(
        ..., 
        description="Value to set (e.g., 'playful' for style_tone)"
    )


class FeedbackResponse(BaseModel):
    """Response for feedback application"""
    success: bool
    message: str


class StyleHintsResponse(BaseModel):
    """Style hints for prompt building"""
    user_id: str
    hints: str
    has_hints: bool


class TopicRecordRequest(BaseModel):
    """Request to record topic interest"""
    topic: str = Field(..., description="Topic name")
    category: Optional[str] = Field(None, description="Topic category")
    weight: float = Field(1.0, description="Weight to add")


class GoodTimeResponse(BaseModel):
    """Response for good time check"""
    user_id: str
    is_good_time: bool
    current_hour: int
    peak_hours: Optional[List[int]] = None


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/{user_id}", response_model=UserInsightsResponse)
async def get_user_insights(user_id: str):
    """
    Get complete learned profile for a user.
    
    Returns communication style, activity patterns, and topic interests.
    """
    try:
        profile = await user_learning_service.get_user_profile(user_id)
        
        # Transform activity data
        activity = None
        if profile.get("activity"):
            activity = ActivityInfo(**profile["activity"])
        
        # Transform interests
        interests = [
            TopicInterest(**i) for i in profile.get("interests", [])
        ]
        
        return UserInsightsResponse(
            user_id=user_id,
            has_data=profile.get("has_data", False),
            style=profile.get("style"),
            activity=activity,
            interests=interests,
            updated_at=profile.get("updated_at"),
        )
    
    except Exception as e:
        logger.error(f"Error getting insights for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/feedback", response_model=FeedbackResponse)
async def apply_user_feedback(user_id: str, feedback: FeedbackRequest):
    """
    Apply manual feedback/correction to user learning data.
    
    Supported feedback types:
    - style_tone: formal/casual/playful/romantic
    - style_length: short/medium/long
    - style_emoji: none/rare/moderate/frequent
    - style_expression: reserved/moderate/expressive
    """
    try:
        success = await user_learning_service.apply_feedback(
            user_id=user_id,
            feedback_type=feedback.feedback_type,
            feedback_value=feedback.value
        )
        
        if success:
            return FeedbackResponse(
                success=True,
                message=f"Applied {feedback.feedback_type}={feedback.value}"
            )
        else:
            return FeedbackResponse(
                success=False,
                message=f"Unknown feedback type: {feedback.feedback_type}"
            )
    
    except Exception as e:
        logger.error(f"Error applying feedback for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def clear_user_insights(user_id: str):
    """
    Clear all learning data for a user.
    
    ⚠️ Use with caution - this removes all learned preferences.
    """
    try:
        await user_learning_service.clear_user_data(user_id)
        return {"success": True, "message": f"Cleared all data for {user_id}"}
    
    except Exception as e:
        logger.error(f"Error clearing insights for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/style-hints", response_model=StyleHintsResponse)
async def get_style_hints(user_id: str):
    """
    Get style hints formatted for prompt building.
    
    Returns a pre-formatted string that can be appended to AI system prompts.
    """
    try:
        hints = await user_learning_service.generate_style_hints(user_id)
        
        return StyleHintsResponse(
            user_id=user_id,
            hints=hints,
            has_hints=bool(hints.strip())
        )
    
    except Exception as e:
        logger.error(f"Error getting style hints for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/topic")
async def record_topic_interest(user_id: str, topic: TopicRecordRequest):
    """
    Record user's interest in a topic.
    
    Use this to manually track topic interests from conversation analysis.
    """
    try:
        await user_learning_service.record_topic_interest(
            user_id=user_id,
            topic=topic.topic,
            category=topic.category,
            weight=topic.weight
        )
        
        return {
            "success": True,
            "message": f"Recorded interest in '{topic.topic}'"
        }
    
    except Exception as e:
        logger.error(f"Error recording topic for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/interests")
async def get_user_interests(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None)
):
    """
    Get user's top topic interests.
    
    Optionally filter by category.
    """
    try:
        interests = await user_learning_service.get_top_interests(
            user_id=user_id,
            limit=limit,
            category=category
        )
        
        return {
            "user_id": user_id,
            "interests": interests,
            "count": len(interests)
        }
    
    except Exception as e:
        logger.error(f"Error getting interests for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/good-time")
async def check_good_time(user_id: str):
    """
    Check if now is a good time to send a proactive message.
    
    Based on user's learned activity patterns.
    """
    from datetime import datetime
    
    try:
        is_good = await user_learning_service.is_good_time_to_message(user_id)
        activity = await user_learning_service.get_peak_activity_times(user_id)
        
        return GoodTimeResponse(
            user_id=user_id,
            is_good_time=is_good,
            current_hour=datetime.utcnow().hour,
            peak_hours=activity.get("peak_hours") if activity else None
        )
    
    except Exception as e:
        logger.error(f"Error checking good time for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/activity")
async def get_activity_pattern(user_id: str):
    """
    Get user's activity pattern data.
    
    Returns hourly and weekly activity distributions.
    """
    try:
        profile = await user_learning_service.get_user_profile(user_id)
        schedule = profile.get("schedule", {})
        activity = profile.get("activity")
        
        return {
            "user_id": user_id,
            "hourly_activity": schedule.get("hourly_activity", [0] * 24),
            "weekday_activity": schedule.get("weekday_activity", [0] * 7),
            "total_messages": schedule.get("total_messages", 0),
            "last_active": schedule.get("last_active"),
            "peak_hours": activity.get("peak_hours") if activity else None,
            "preferred_slots": activity.get("preferred_slots") if activity else None,
        }
    
    except Exception as e:
        logger.error(f"Error getting activity for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

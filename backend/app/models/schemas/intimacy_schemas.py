"""
Pydantic Schemas for Intimacy System
=====================================

Request/Response schemas for the intimacy API endpoints.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ActionAvailability(BaseModel):
    """Availability status for a specific XP action"""
    action_type: str
    action_name: str
    xp_reward: int
    daily_limit: Optional[int] = None  # None means unlimited
    used_today: int = 0
    available: bool = True
    cooldown_seconds: Optional[int] = None  # Seconds until available again


class IntimacyStatus(BaseModel):
    """Current intimacy status with a character"""
    character_id: UUID
    character_name: Optional[str] = None

    # Level info
    current_level: int
    total_xp: float
    xp_for_current_level: float  # XP threshold for current level
    xp_for_next_level: float  # XP threshold for next level
    xp_progress_in_level: float  # XP earned within current level
    progress_percent: float  # 0-100%

    # Stage info
    intimacy_stage: str  # strangers, acquaintances, close_friends, ambiguous, soulmates
    stage_name_cn: str  # Chinese name

    # Streak info
    streak_days: int
    last_interaction_date: Optional[datetime] = None

    # Daily limits
    daily_xp_earned: float
    daily_xp_limit: float = 500.0
    daily_xp_remaining: float

    # Available actions
    available_actions: List[ActionAvailability] = []

    # Unlocked features at current level
    unlocked_features: List[str] = []

    # Statistics
    total_messages: int = 0
    gifts_count: int = 0
    special_events: int = 0


class XPAwardResponse(BaseModel):
    """Response after awarding XP"""
    success: bool = True
    action_type: str
    xp_awarded: float
    xp_before: float
    new_total_xp: float
    level_before: int
    new_level: int
    level_up: bool = False
    levels_gained: int = 0

    # Stage change
    stage_before: Optional[str] = None
    new_stage: Optional[str] = None
    stage_changed: bool = False

    # Daily tracking
    daily_xp_earned: float
    daily_xp_remaining: float

    # Streak
    streak_days: int

    # Optional celebration message on level up
    celebration_message: Optional[str] = None
    unlocked_features: List[str] = []


class LevelUpEvent(BaseModel):
    """Level up event details"""
    old_level: int
    new_level: int
    levels_gained: int = 1
    old_stage: Optional[str] = None
    new_stage: Optional[str] = None
    stage_changed: bool = False
    unlocked_features: List[str] = []
    celebration_message: str


class DailyCheckinResponse(BaseModel):
    """Response for daily check-in"""
    success: bool
    message: str
    xp_awarded: float
    streak_days: int
    streak_bonus: float = 0.0  # Extra XP for streaks
    total_xp_awarded: float  # Base + bonus
    new_total_xp: float
    new_level: int
    level_up: bool = False


class IntimacyHistoryEntry(BaseModel):
    """Single entry in XP history"""
    action_type: str
    action_name: str
    xp_awarded: float
    created_at: datetime


class IntimacyHistoryResponse(BaseModel):
    """XP history response"""
    character_id: UUID
    entries: List[IntimacyHistoryEntry]
    total: int
    limit: int
    offset: int
    has_more: bool


class StageInfo(BaseModel):
    """Information about an intimacy stage"""
    stage_id: str
    stage_name: str
    stage_name_cn: str
    level_range: str  # e.g., "0-3"
    min_level: int
    max_level: int
    description: str
    ai_attitude: str
    key_unlocks: List[str]


class AllStagesResponse(BaseModel):
    """Response with all intimacy stages info"""
    stages: List[StageInfo]
    current_stage: str
    current_level: int


class FeatureUnlock(BaseModel):
    """Feature unlock information"""
    level: int
    feature_id: str
    feature_name: str
    feature_name_cn: str
    description: str
    is_unlocked: bool = False


class AllFeaturesResponse(BaseModel):
    """Response with all unlockable features"""
    features: List[FeatureUnlock]
    current_level: int
    total_unlocked: int
    total_features: int

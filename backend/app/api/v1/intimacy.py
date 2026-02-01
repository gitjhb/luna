"""
Intimacy API Routes
====================

Endpoints for managing user-character intimacy progression.
"""

from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
from typing import List
from datetime import datetime

from app.services.intimacy_service import intimacy_service, IntimacyService, _MOCK_ACTION_LOGS
from app.models.schemas.intimacy_schemas import (
    IntimacyStatus,
    XPAwardResponse,
    DailyCheckinResponse,
    ActionAvailability,
    IntimacyHistoryResponse,
    IntimacyHistoryEntry,
    StageInfo,
    AllStagesResponse,
    FeatureUnlock,
    AllFeaturesResponse,
)

router = APIRouter(prefix="/intimacy")


@router.get("/{character_id}", response_model=IntimacyStatus)
async def get_intimacy_status(character_id: UUID, request: Request):
    """
    Get current intimacy status with a specific character.

    Returns level, XP progress, stage, streak, and available actions.
    """
    # Get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if not user:
        # Mock user for development
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    status = await intimacy_service.get_intimacy_status(user_id, str(character_id))

    return IntimacyStatus(
        character_id=character_id,
        character_name=None,  # Could be populated from character service
        current_level=status["current_level"],
        total_xp=status["total_xp"],
        xp_for_current_level=status["xp_for_current_level"],
        xp_for_next_level=status["xp_for_next_level"],
        xp_progress_in_level=status["xp_progress_in_level"],
        progress_percent=status["progress_percent"],
        intimacy_stage=status["intimacy_stage"],
        stage_name_cn=status["stage_name_cn"],
        streak_days=status["streak_days"],
        last_interaction_date=status["last_interaction_date"],
        daily_xp_earned=status["daily_xp_earned"],
        daily_xp_limit=status["daily_xp_limit"],
        total_messages=status.get("total_messages", 0),
        gifts_count=status.get("gifts_count", 0),
        special_events=status.get("special_events", 0),
        daily_xp_remaining=status["daily_xp_remaining"],
        available_actions=[ActionAvailability(**a) for a in status["available_actions"]],
        unlocked_features=status["unlocked_features"],
    )


@router.post("/{character_id}/checkin", response_model=DailyCheckinResponse)
async def daily_checkin(character_id: UUID, request: Request):
    """
    Perform daily check-in with a character.

    Awards 20 XP base + streak bonus (up to 50% extra for consecutive days).
    Can only be done once per day per character.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    result = await intimacy_service.daily_checkin(user_id, str(character_id))

    return DailyCheckinResponse(
        success=result["success"],
        message=result["message"],
        xp_awarded=result["xp_awarded"],
        streak_days=result["streak_days"],
        streak_bonus=result["streak_bonus"],
        total_xp_awarded=result["total_xp_awarded"],
        new_total_xp=result["new_total_xp"],
        new_level=result["new_level"],
        level_up=result["level_up"],
    )


@router.get("/{character_id}/actions", response_model=List[ActionAvailability])
async def get_available_actions(character_id: UUID, request: Request):
    """
    Get all available XP actions and their current status.

    Shows which actions are available, on cooldown, or at daily limit.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    actions = []
    for action_type, config in IntimacyService.ACTION_REWARDS.items():
        available, cooldown, used_today = await intimacy_service.check_action_available(
            user_id, str(character_id), action_type
        )
        actions.append(ActionAvailability(
            action_type=action_type,
            action_name=config["name"],
            xp_reward=config["xp"],
            daily_limit=config.get("daily_limit"),
            used_today=used_today,
            available=available,
            cooldown_seconds=cooldown,
        ))

    return actions


@router.get("/{character_id}/history", response_model=IntimacyHistoryResponse)
async def get_xp_history(
    character_id: UUID,
    request: Request,
    limit: int = 20,
    offset: int = 0
):
    """
    Get XP earning history for a character.

    Returns recent actions and XP awarded.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    # Filter logs for this user/character
    all_logs = [
        log for log in _MOCK_ACTION_LOGS
        if log["user_id"] == user_id and log["character_id"] == str(character_id)
    ]

    # Sort by created_at descending
    all_logs.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(all_logs)
    paginated = all_logs[offset:offset + limit]

    entries = []
    for log in paginated:
        action_config = IntimacyService.ACTION_REWARDS.get(log["action_type"], {})
        entries.append(IntimacyHistoryEntry(
            action_type=log["action_type"],
            action_name=action_config.get("name", log["action_type"]),
            xp_awarded=log["xp_awarded"],
            created_at=log["created_at"],
        ))

    return IntimacyHistoryResponse(
        character_id=character_id,
        entries=entries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + limit < total,
    )


@router.get("/stages/all", response_model=AllStagesResponse)
async def get_all_stages(request: Request, character_id: UUID = None):
    """
    Get information about all intimacy stages.

    Optionally pass character_id to see current stage highlighted.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    current_stage = "strangers"
    current_level = 1

    if character_id:
        status = await intimacy_service.get_intimacy_status(user_id, str(character_id))
        current_stage = status["intimacy_stage"]
        current_level = status["current_level"]

    stages = []
    for stage_id, info in IntimacyService.STAGES.items():
        stages.append(StageInfo(
            stage_id=stage_id,
            stage_name=info["name"],
            stage_name_cn=info["name_cn"],
            level_range=f"{info['min_level']}-{info['max_level']}",
            min_level=info["min_level"],
            max_level=info["max_level"],
            description=info["description"],
            ai_attitude=info["ai_attitude"],
            key_unlocks=_get_stage_unlocks(info["min_level"], info["max_level"]),
        ))

    return AllStagesResponse(
        stages=stages,
        current_stage=current_stage,
        current_level=current_level,
    )


@router.get("/features/all", response_model=AllFeaturesResponse)
async def get_all_features(request: Request, character_id: UUID = None):
    """
    Get information about all unlockable features.

    Optionally pass character_id to see which features are unlocked.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    current_level = 1
    if character_id:
        status = await intimacy_service.get_intimacy_status(user_id, str(character_id))
        current_level = status["current_level"]

    features = []
    for level, info in sorted(IntimacyService.FEATURE_UNLOCKS.items()):
        features.append(FeatureUnlock(
            level=level,
            feature_id=info["id"],
            feature_name=info["name"],
            feature_name_cn=info["name_cn"],
            description=f"Unlocked at Level {level}",
            is_unlocked=level <= current_level,
        ))

    total_unlocked = sum(1 for f in features if f.is_unlocked)

    return AllFeaturesResponse(
        features=features,
        current_level=current_level,
        total_unlocked=total_unlocked,
        total_features=len(features),
    )


@router.post("/{character_id}/award/{action_type}", response_model=XPAwardResponse)
async def award_xp_manually(character_id: UUID, action_type: str, request: Request):
    """
    Manually award XP for a specific action.

    This endpoint is primarily for testing and special cases.
    Normal XP is awarded automatically through chat/voice interactions.
    """
    user = getattr(request.state, "user", None)
    if not user:
        user_id = "demo-user-123"
    else:
        user_id = str(user.user_id)

    if action_type not in IntimacyService.ACTION_REWARDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {action_type}. Valid types: {list(IntimacyService.ACTION_REWARDS.keys())}"
        )

    result = await intimacy_service.award_xp(user_id, str(character_id), action_type)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Failed to award XP")
        )

    return XPAwardResponse(
        success=result["success"],
        action_type=result["action_type"],
        xp_awarded=result["xp_awarded"],
        xp_before=result["xp_before"],
        new_total_xp=result["new_total_xp"],
        level_before=result["level_before"],
        new_level=result["new_level"],
        level_up=result["level_up"],
        levels_gained=result["levels_gained"],
        stage_before=result["stage_before"],
        new_stage=result["new_stage"],
        stage_changed=result["stage_changed"],
        daily_xp_earned=result["daily_xp_earned"],
        daily_xp_remaining=result["daily_xp_remaining"],
        streak_days=result["streak_days"],
        celebration_message=result.get("celebration_message"),
        unlocked_features=result.get("unlocked_features", []),
    )


def _get_stage_unlocks(min_level: int, max_level: int) -> List[str]:
    """Helper to get feature unlocks within a level range."""
    unlocks = []
    for level, info in IntimacyService.FEATURE_UNLOCKS.items():
        if min_level <= level <= max_level:
            unlocks.append(f"Lv{level}: {info['name']}")
    return unlocks

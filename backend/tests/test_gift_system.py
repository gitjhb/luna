"""
Gift System Tests - Mock Mode
=============================
Tests for the complete gift system overhaul.
All tests run in mock mode (no DB/Redis/LLM needed).
"""

import os
os.environ["MOCK_DATABASE"] = "true"
os.environ["MOCK_REDIS"] = "true"
os.environ["MOCK_LLM"] = "true"
os.environ["MOCK_AUTH"] = "true"

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def reset_mock_storage():
    """Reset all mock storage between tests."""
    from app.services.effect_service import _MOCK_EFFECTS
    from app.services.gift_service import _MOCK_GIFTS, _MOCK_IDEMPOTENCY_KEYS
    from app.services.intimacy_service import _MOCK_INTIMACY_STORAGE, _MOCK_ACTION_LOGS
    _MOCK_EFFECTS.clear()
    _MOCK_GIFTS.clear()
    _MOCK_IDEMPOTENCY_KEYS.clear()
    _MOCK_INTIMACY_STORAGE.clear()
    _MOCK_ACTION_LOGS.clear()
    yield


# ============================================================================
# Task 2: Effect Service DB Persistence Tests
# ============================================================================

@pytest.mark.asyncio
async def test_effect_apply_stores_stage_boost():
    """stage_boost should be persisted and retrievable."""
    from app.services.effect_service import effect_service

    await effect_service.apply_effect(
        user_id="u1",
        character_id="c1",
        effect_type="tipsy",
        prompt_modifier="微醺...",
        duration_messages=30,
        stage_boost=1,
    )

    effects = await effect_service.get_active_effects("u1", "c1")
    assert len(effects) == 1
    assert effects[0]["stage_boost"] == 1


@pytest.mark.asyncio
async def test_effect_apply_stores_allows_nsfw():
    """allows_nsfw should be persisted and retrievable."""
    from app.services.effect_service import effect_service

    await effect_service.apply_effect(
        user_id="u1",
        character_id="c1",
        effect_type="deeply_tipsy",
        prompt_modifier="醉了...",
        duration_messages=20,
        allows_nsfw=True,
    )

    effects = await effect_service.get_active_effects("u1", "c1")
    assert len(effects) == 1
    assert effects[0]["allows_nsfw"] is True


@pytest.mark.asyncio
async def test_effect_apply_stores_xp_multiplier():
    """xp_multiplier should be persisted and retrievable."""
    from app.services.effect_service import effect_service

    await effect_service.apply_effect(
        user_id="u1",
        character_id="c1",
        effect_type="xp_boost",
        prompt_modifier="经验加速...",
        duration_messages=30,
        xp_multiplier=2.0,
    )

    effects = await effect_service.get_active_effects("u1", "c1")
    assert len(effects) == 1
    assert effects[0]["xp_multiplier"] == 2.0


@pytest.mark.asyncio
async def test_get_stage_boost_returns_from_effect():
    """get_stage_boost should return the max stage_boost from active effects."""
    from app.services.effect_service import effect_service

    await effect_service.apply_effect(
        user_id="u1", character_id="c1",
        effect_type="tipsy", prompt_modifier="...",
        duration_messages=30, stage_boost=1,
    )

    boost = await effect_service.get_stage_boost("u1", "c1")
    assert boost == 1


@pytest.mark.asyncio
async def test_get_nsfw_override_returns_true():
    """get_nsfw_override should return True if any effect has allows_nsfw."""
    from app.services.effect_service import effect_service

    await effect_service.apply_effect(
        user_id="u1", character_id="c1",
        effect_type="deeply_tipsy", prompt_modifier="...",
        duration_messages=20, allows_nsfw=True,
    )

    result = await effect_service.get_nsfw_override("u1", "c1")
    assert result is True

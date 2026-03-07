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
os.environ["MOCK_PAYMENT"] = "true"

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def reset_mock_storage():
    """Reset all mock storage between tests."""
    from app.services.effect_service import _MOCK_EFFECTS
    from app.services.gift_service import _MOCK_GIFTS, _MOCK_IDEMPOTENCY_KEYS
    from app.services.intimacy_service import _MOCK_INTIMACY_STORAGE, _MOCK_ACTION_LOGS
    from app.services.payment_service import _wallets, _transactions
    _MOCK_EFFECTS.clear()
    _MOCK_GIFTS.clear()
    _MOCK_IDEMPOTENCY_KEYS.clear()
    _MOCK_INTIMACY_STORAGE.clear()
    _MOCK_ACTION_LOGS.clear()
    _wallets.clear()
    _transactions.clear()
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


# ============================================================================
# Task 3: XP Multiplier Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_xp_multiplier_applied_to_award():
    """When xp_boost effect is active, award_xp should multiply XP."""
    from app.services.effect_service import effect_service
    from app.services.intimacy_service import intimacy_service

    # Apply 2x XP boost
    await effect_service.apply_effect(
        user_id="u1", character_id="c1",
        effect_type="xp_boost", prompt_modifier="...",
        duration_messages=30, xp_multiplier=2.0,
    )

    # Award XP for a message (base: 2 XP)
    result = await intimacy_service.award_xp("u1", "c1", "message")

    assert result["success"] is True
    assert result["xp_awarded"] == 4  # 2 * 2.0 = 4


@pytest.mark.asyncio
async def test_xp_no_multiplier_when_no_effect():
    """Without active effects, XP should be normal."""
    from app.services.intimacy_service import intimacy_service

    result = await intimacy_service.award_xp("u1", "c1", "message")

    assert result["success"] is True
    assert result["xp_awarded"] == 2  # base XP for message


# ============================================================================
# Task 4: Character Exclusive Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_character_exclusive_wrong_character():
    """Sending a character-exclusive gift to wrong character should fail."""
    from app.services.gift_service import gift_service

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="wrong-character-id",
        gift_type="vera_sunglasses",
        idempotency_key="test-key-exclusive-1",
    )

    assert result["success"] is False
    assert "exclusive" in result.get("error", "").lower() or "专属" in result.get("message", "")


@pytest.mark.asyncio
async def test_character_exclusive_correct_character():
    """Sending a character-exclusive gift to correct character should succeed."""
    from app.services.gift_service import gift_service
    from app.services.payment_service import payment_service

    await payment_service.add_credits("u1", 5000, description="test")

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e",
        gift_type="vera_sunglasses",
        idempotency_key="test-key-exclusive-2",
    )

    assert result["success"] is True

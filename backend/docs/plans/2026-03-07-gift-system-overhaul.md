# Gift System Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the gift system so all defined effects actually work, add breakthrough gifts and new interaction gifts (dates, touch, costumes).

**Architecture:** Fix-and-extend approach. Add missing DB columns to ActiveEffect, wire up unconnected catalog flags in gift_service.send_gift(), add new catalog entries for interaction gifts. No architectural changes.

**Tech Stack:** Python/FastAPI, SQLAlchemy async ORM, SQLite (dev), pytest with mock mode.

**Design doc:** `docs/plans/2026-03-07-gift-system-overhaul-design.md`

---

### Task 1: DB Migration - Add ActiveEffect Columns

**Files:**
- Create: `migrations/add_effect_columns.sql`
- Modify: `app/models/database/gift_models.py:452-491` (ActiveEffect class)

**Step 1: Create migration SQL**

```sql
-- migrations/add_effect_columns.sql
-- Add missing columns to active_effects table for stage boost, NSFW override, and XP multiplier

ALTER TABLE active_effects ADD COLUMN stage_boost INTEGER DEFAULT 0;
ALTER TABLE active_effects ADD COLUMN allows_nsfw INTEGER DEFAULT 0;
ALTER TABLE active_effects ADD COLUMN xp_multiplier REAL DEFAULT 1.0;
```

**Step 2: Add columns to ActiveEffect model**

In `app/models/database/gift_models.py`, add after `expires_at` column (line ~475):

```python
    # Gift effect parameters (persisted for DB mode)
    stage_boost = Column(Integer, default=0)          # Temporary stage upgrade (0-2)
    allows_nsfw = Column(Integer, default=0)          # SQLite boolean: unlocks NSFW for this character
    xp_multiplier = Column(Float, default=1.0)        # XP multiplier (1.0 = normal, 2.0 = double)
```

**Step 3: Commit**

```bash
git add migrations/add_effect_columns.sql app/models/database/gift_models.py
git commit -m "feat(gifts): add stage_boost, allows_nsfw, xp_multiplier columns to ActiveEffect"
```

---

### Task 2: Fix effect_service DB Persistence

**Files:**
- Modify: `app/services/effect_service.py:54-118` (apply_effect method)
- Modify: `app/services/effect_service.py:120-163` (get_active_effects method)
- Test: `tests/test_gift_system.py`

**Step 1: Write failing test**

Create `tests/test_gift_system.py`:

```python
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
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Reset mock storage before importing services
import importlib


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gift_system.py::test_effect_apply_stores_xp_multiplier -v`
Expected: FAIL - `apply_effect()` doesn't accept `xp_multiplier` param yet.

**Step 3: Update effect_service.apply_effect signature and mock storage**

In `app/services/effect_service.py`, update `apply_effect` (line 54):

Add `xp_multiplier: float = 1.0` parameter. In the effect dict (line 81), add:
```python
"xp_multiplier": xp_multiplier,
```

In the DB branch (line 100), add `xp_multiplier` to the `ActiveEffect` constructor if DB mode:
```python
# Note: DB mode uses the new column. For now only mock mode is being tested.
```

Update `get_active_effects` DB branch (line 150) to include the new fields:
```python
"stage_boost": getattr(e, 'stage_boost', 0) or 0,
"allows_nsfw": bool(getattr(e, 'allows_nsfw', 0)),
"xp_multiplier": getattr(e, 'xp_multiplier', 1.0) or 1.0,
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gift_system.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add app/services/effect_service.py tests/test_gift_system.py
git commit -m "feat(gifts): persist stage_boost, allows_nsfw, xp_multiplier in effect_service"
```

---

### Task 3: Wire XP Multiplier into intimacy_service.award_xp

**Files:**
- Modify: `app/services/intimacy_service.py:602-720` (award_xp method)
- Test: `tests/test_gift_system.py`

**Step 1: Write failing test**

Add to `tests/test_gift_system.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gift_system.py::test_xp_multiplier_applied_to_award -v`
Expected: FAIL - XP is 2 not 4 (multiplier not applied).

**Step 3: Add XP multiplier lookup in intimacy_service.award_xp**

In `app/services/intimacy_service.py`, in `award_xp()` method, after line 654 (`xp_reward = self.ACTION_REWARDS[action_type]["xp"]`), add:

```python
        # Apply XP multiplier from active effects (e.g., double XP potion)
        try:
            from app.services.effect_service import effect_service
            xp_multiplier = await effect_service.get_xp_multiplier(user_id, character_id)
            if xp_multiplier > 1.0:
                xp_reward = int(xp_reward * xp_multiplier)
                logger.info(f"XP multiplier active: {xp_multiplier}x -> {xp_reward} XP")
        except Exception as e:
            logger.warning(f"Failed to get XP multiplier: {e}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gift_system.py::test_xp_multiplier_applied_to_award tests/test_gift_system.py::test_xp_no_multiplier_when_no_effect -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app/services/intimacy_service.py tests/test_gift_system.py
git commit -m "feat(gifts): apply XP multiplier from active effects in award_xp"
```

---

### Task 4: Character Exclusive Validation

**Files:**
- Modify: `app/services/gift_service.py:270-278` (after gift_info lookup in send_gift)
- Test: `tests/test_gift_system.py`

**Step 1: Write failing test**

Add to `tests/test_gift_system.py`:

```python
# ============================================================================
# Task 4: Character Exclusive Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_character_exclusive_wrong_character():
    """Sending a character-exclusive gift to wrong character should fail."""
    from app.services.gift_service import gift_service

    # vera_sunglasses is exclusive to Vera (character_id = b6c7d8e9-...)
    result = await gift_service.send_gift(
        user_id="u1",
        character_id="wrong-character-id",
        gift_type="vera_sunglasses",
        idempotency_key="test-key-exclusive-1",
    )

    assert result["success"] is False
    assert "exclusive" in result.get("error", "").lower() or "exclusive" in result.get("message", "").lower()


@pytest.mark.asyncio
async def test_character_exclusive_correct_character():
    """Sending a character-exclusive gift to correct character should succeed."""
    from app.services.gift_service import gift_service
    from app.services.payment_service import payment_service

    # Give user enough credits
    await payment_service.add_credits("u1", 5000, description="test")

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e",
        gift_type="vera_sunglasses",
        idempotency_key="test-key-exclusive-2",
    )

    assert result["success"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gift_system.py::test_character_exclusive_wrong_character -v`
Expected: FAIL - gift goes through without character validation.

**Step 3: Add character exclusive validation in gift_service.send_gift**

In `app/services/gift_service.py`, after the gift_info validation (around line 277, before price/xp extraction), add:

```python
        # Validate character exclusive gifts
        if gift_info.get("character_exclusive"):
            required_character = gift_info["character_exclusive"]
            if character_id != required_character:
                char_name = gift_info.get("name_cn") or gift_info["name"]
                return {
                    "success": False,
                    "error": "character_exclusive",
                    "message": f"'{char_name}' 是角色专属礼物，只能送给对应角色",
                }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gift_system.py::test_character_exclusive_wrong_character tests/test_gift_system.py::test_character_exclusive_correct_character -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app/services/gift_service.py tests/test_gift_system.py
git commit -m "feat(gifts): validate character-exclusive gifts before purchase"
```

---

### Task 5: Min Stage Validation for Touch Gifts

**Files:**
- Modify: `app/services/gift_service.py` (send_gift, after character exclusive check)
- Test: `tests/test_gift_system.py`

**Step 1: Write failing test**

Add to `tests/test_gift_system.py`:

```python
# ============================================================================
# Task 5: Min Stage Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_min_stage_rejected_at_stranger():
    """Gift with min_stage=S1 should be rejected if user is at S0 (strangers)."""
    from app.services.gift_service import gift_service, _MOCK_GIFT_CATALOG
    from app.services.payment_service import payment_service

    # Add a test gift with min_stage
    _MOCK_GIFT_CATALOG["test_touch_gift"] = {
        "gift_type": "test_touch_gift",
        "name": "Test Touch",
        "name_cn": "测试触摸",
        "price": 80,
        "xp_reward": 60,
        "tier": 2,
        "icon": "🤝",
        "min_stage": "friends",  # S1 required
    }

    await payment_service.add_credits("u1", 1000, description="test")

    # User starts at S0 (strangers) by default
    result = await gift_service.send_gift(
        user_id="u1",
        character_id="c1",
        gift_type="test_touch_gift",
        idempotency_key="test-min-stage-1",
    )

    assert result["success"] is False
    assert "relationship" in result.get("message", "").lower() or "亲密" in result.get("message", "")


@pytest.mark.asyncio
async def test_min_stage_accepted_at_correct_stage():
    """Gift with min_stage=S1 should succeed if user is at S1 (friends)."""
    from app.services.gift_service import gift_service, _MOCK_GIFT_CATALOG
    from app.services.payment_service import payment_service
    from app.services.intimacy_service import intimacy_service, _MOCK_INTIMACY_STORAGE

    _MOCK_GIFT_CATALOG["test_touch_gift"] = {
        "gift_type": "test_touch_gift",
        "name": "Test Touch",
        "name_cn": "测试触摸",
        "price": 80,
        "xp_reward": 60,
        "tier": 2,
        "icon": "🤝",
        "min_stage": "friends",
    }

    await payment_service.add_credits("u1", 1000, description="test")

    # Set user to friends stage (level 6+)
    intimacy = await intimacy_service.get_or_create_intimacy("u1", "c1")
    intimacy["current_level"] = 8
    intimacy["intimacy_stage"] = "friends"
    intimacy["total_xp"] = 300.0

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="c1",
        gift_type="test_touch_gift",
        idempotency_key="test-min-stage-2",
    )

    assert result["success"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gift_system.py::test_min_stage_rejected_at_stranger -v`
Expected: FAIL - gift goes through without stage check.

**Step 3: Add min_stage validation in gift_service.send_gift**

In `app/services/gift_service.py`, after the character_exclusive validation, add:

```python
        # Validate min_stage for touch/interaction gifts
        if gift_info.get("min_stage"):
            required_stage = gift_info["min_stage"]
            stage_order = ["strangers", "friends", "ambiguous", "lovers", "soulmates"]
            intimacy_record = await intimacy_service.get_or_create_intimacy(user_id, character_id)
            current_stage = intimacy_record.get("intimacy_stage", "strangers")

            required_idx = stage_order.index(required_stage) if required_stage in stage_order else 0
            current_idx = stage_order.index(current_stage) if current_stage in stage_order else 0

            if current_idx < required_idx:
                stage_names_cn = {
                    "strangers": "陌生人", "friends": "朋友",
                    "ambiguous": "暧昧", "lovers": "恋人", "soulmates": "挚爱",
                }
                return {
                    "success": False,
                    "error": "stage_too_low",
                    "message": f"亲密度不足：需要达到'{stage_names_cn.get(required_stage, required_stage)}'阶段才能使用此礼物",
                }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gift_system.py::test_min_stage_rejected_at_stranger tests/test_gift_system.py::test_min_stage_accepted_at_correct_stage -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app/services/gift_service.py tests/test_gift_system.py
git commit -m "feat(gifts): add min_stage validation for touch/interaction gifts"
```

---

### Task 6: Breakthrough Gift Logic

**Files:**
- Modify: `app/services/gift_service.py` (send_gift, after bottleneck check around line 377)
- Test: `tests/test_gift_system.py`

**Step 1: Write failing test**

Add to `tests/test_gift_system.py`:

```python
# ============================================================================
# Task 6: Breakthrough Gift Tests
# ============================================================================

@pytest.mark.asyncio
async def test_breakthrough_succeeds_at_bottleneck():
    """Breakthrough gift should succeed when user is at the bottleneck level."""
    from app.services.gift_service import gift_service, _MOCK_GIFT_CATALOG
    from app.services.payment_service import payment_service
    from app.services.intimacy_service import intimacy_service

    _MOCK_GIFT_CATALOG["breakthrough_s1_to_s2"] = {
        "gift_type": "breakthrough_s1_to_s2",
        "name": "Friendship Bracelet",
        "name_cn": "友谊手链",
        "price": 200,
        "xp_reward": 100,
        "tier": 2,
        "icon": "📿",
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "friends",
            "to_stage": "ambiguous",
            "required_bottleneck_level": 8,
        },
    }

    await payment_service.add_credits("u1", 1000, description="test")

    # Set user to bottleneck level 8, locked
    intimacy = await intimacy_service.get_or_create_intimacy("u1", "c1")
    intimacy["current_level"] = 8
    intimacy["intimacy_stage"] = "friends"
    intimacy["total_xp"] = 550.0
    intimacy["bottleneck_locked"] = True
    intimacy["bottleneck_level"] = 8

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="c1",
        gift_type="breakthrough_s1_to_s2",
        idempotency_key="test-breakthrough-1",
    )

    assert result["success"] is True
    assert result.get("bottleneck_unlocked") is True


@pytest.mark.asyncio
async def test_breakthrough_fails_not_at_bottleneck():
    """Breakthrough gift should fail if user is not at the required bottleneck."""
    from app.services.gift_service import gift_service, _MOCK_GIFT_CATALOG
    from app.services.payment_service import payment_service
    from app.services.intimacy_service import intimacy_service

    _MOCK_GIFT_CATALOG["breakthrough_s1_to_s2"] = {
        "gift_type": "breakthrough_s1_to_s2",
        "name": "Friendship Bracelet",
        "name_cn": "友谊手链",
        "price": 200,
        "xp_reward": 100,
        "tier": 2,
        "icon": "📿",
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "friends",
            "to_stage": "ambiguous",
            "required_bottleneck_level": 8,
        },
    }

    await payment_service.add_credits("u1", 1000, description="test")

    # User at level 5 - not at bottleneck
    intimacy = await intimacy_service.get_or_create_intimacy("u1", "c1")
    intimacy["current_level"] = 5
    intimacy["intimacy_stage"] = "strangers"
    intimacy["bottleneck_locked"] = False

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="c1",
        gift_type="breakthrough_s1_to_s2",
        idempotency_key="test-breakthrough-2",
    )

    assert result["success"] is False
    assert "bottleneck" in result.get("message", "").lower() or "瓶颈" in result.get("message", "") or "level" in result.get("message", "").lower()


@pytest.mark.asyncio
async def test_breakthrough_fails_already_unlocked():
    """Breakthrough gift should fail if bottleneck is already unlocked."""
    from app.services.gift_service import gift_service, _MOCK_GIFT_CATALOG
    from app.services.payment_service import payment_service
    from app.services.intimacy_service import intimacy_service

    _MOCK_GIFT_CATALOG["breakthrough_s1_to_s2"] = {
        "gift_type": "breakthrough_s1_to_s2",
        "name": "Friendship Bracelet",
        "name_cn": "友谊手链",
        "price": 200,
        "xp_reward": 100,
        "tier": 2,
        "icon": "📿",
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "friends",
            "to_stage": "ambiguous",
            "required_bottleneck_level": 8,
        },
    }

    await payment_service.add_credits("u1", 1000, description="test")

    # User at level 8 but NOT locked (already broke through)
    intimacy = await intimacy_service.get_or_create_intimacy("u1", "c1")
    intimacy["current_level"] = 8
    intimacy["intimacy_stage"] = "friends"
    intimacy["bottleneck_locked"] = False
    intimacy["bottleneck_level"] = None

    result = await gift_service.send_gift(
        user_id="u1",
        character_id="c1",
        gift_type="breakthrough_s1_to_s2",
        idempotency_key="test-breakthrough-3",
    )

    assert result["success"] is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gift_system.py::test_breakthrough_succeeds_at_bottleneck -v`
Expected: FAIL - no breakthrough logic exists.

**Step 3: Add breakthrough handling in gift_service.send_gift**

In `app/services/gift_service.py`, add breakthrough validation BEFORE the balance check (around line 278, after min_stage validation). This prevents charging for a gift that can't be used:

```python
        # Validate breakthrough gifts
        if gift_info.get("breakthrough"):
            bt = gift_info["breakthrough"]
            required_level = bt["required_bottleneck_level"]
            intimacy_record = await intimacy_service.get_or_create_intimacy(user_id, character_id)

            is_locked = intimacy_record.get("bottleneck_locked", False)
            current_level = intimacy_record.get("current_level", 1)
            lock_level = intimacy_record.get("bottleneck_level")

            if not is_locked:
                return {
                    "success": False,
                    "error": "bottleneck_not_locked",
                    "message": f"当前没有瓶颈锁定，无需使用突破礼物",
                }

            if lock_level != required_level:
                return {
                    "success": False,
                    "error": "wrong_bottleneck",
                    "message": f"此礼物用于突破 Lv.{required_level} 瓶颈，当前瓶颈在 Lv.{lock_level}",
                }
```

Then in the bottleneck unlock section (around line 377), ensure breakthrough gifts force-unlock:

```python
            # Step 6.5: Check and unlock bottleneck lock if applicable
            bottleneck_unlocked = False
            bottleneck_unlock_result = None

            # Breakthrough gifts always unlock their target bottleneck
            if gift_info.get("breakthrough"):
                bt = gift_info["breakthrough"]
                bottleneck_unlock_result = await intimacy_service.unlock_bottleneck(
                    user_id, character_id, tier=4  # Force unlock by passing max tier
                )
                if bottleneck_unlock_result.get("unlocked"):
                    bottleneck_unlocked = True
                    logger.info(f"🎉 Breakthrough! {bt['from_stage']} -> {bt['to_stage']}")
            else:
                # Existing logic for non-breakthrough gifts
                lock_status = await intimacy_service.get_bottleneck_lock_status(user_id, character_id)
                if lock_status.get("is_locked"):
                    bottleneck_unlock_result = await intimacy_service.unlock_bottleneck(
                        user_id, character_id, tier
                    )
                    if bottleneck_unlock_result.get("unlocked"):
                        bottleneck_unlocked = True
                        logger.info(f"🔓 Bottleneck unlocked at Lv.{lock_status.get('lock_level')} with Tier {tier} gift")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gift_system.py -k "breakthrough" -v`
Expected: All 3 breakthrough tests PASS.

**Step 5: Commit**

```bash
git add app/services/gift_service.py tests/test_gift_system.py
git commit -m "feat(gifts): add breakthrough gift validation and unlock logic"
```

---

### Task 7: Add New Gift Catalog Entries

**Files:**
- Modify: `app/models/database/gift_models.py:142-445` (DEFAULT_GIFT_CATALOG)

**Step 1: Add breakthrough gifts to catalog**

Append to `DEFAULT_GIFT_CATALOG` in `app/models/database/gift_models.py`:

```python
    # ============ Breakthrough Gifts - 突破礼物 ============
    {
        "gift_type": "breakthrough_s1_to_s2",
        "name": "Friendship Bracelet",
        "name_cn": "友谊手链",
        "description": "Break through the friendship bottleneck",
        "description_cn": "突破友谊瓶颈，进入暧昧阶段",
        "price": 200,
        "xp_reward": 100,
        "xp_multiplier": 1.0,
        "icon": "📿",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "friends",
            "to_stage": "ambiguous",
            "required_bottleneck_level": 8,
        },
        "sort_order": 301,
    },
    {
        "gift_type": "breakthrough_s2_to_s3",
        "name": "Promise Pendant",
        "name_cn": "约定吊坠",
        "description": "Break through to become lovers",
        "description_cn": "突破暧昧瓶颈，正式成为恋人",
        "price": 500,
        "xp_reward": 300,
        "xp_multiplier": 1.0,
        "icon": "💎",
        "tier": GiftTier.SPEED_DATING,
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "ambiguous",
            "to_stage": "lovers",
            "required_bottleneck_level": 16,
        },
        "sort_order": 302,
    },
    {
        "gift_type": "breakthrough_s3_to_s4",
        "name": "Eternal Bond Ring",
        "name_cn": "永恒之戒",
        "description": "Reach the highest level of intimacy",
        "description_cn": "突破恋人瓶颈，进入挚爱阶段",
        "price": 2000,
        "xp_reward": 1000,
        "xp_multiplier": 1.0,
        "icon": "💍",
        "tier": GiftTier.WHALE_BAIT,
        "category": "breakthrough",
        "breakthrough": {
            "from_stage": "lovers",
            "to_stage": "soulmates",
            "required_bottleneck_level": 24,
        },
        "sort_order": 303,
    },
```

**Step 2: Add date scenario gifts**

```python
    # ============ Date Scenario Gifts - 约会场景 ============
    {
        "gift_type": "date_dinner",
        "name": "Candlelight Dinner",
        "name_cn": "烛光晚餐",
        "description": "A romantic candlelight dinner date",
        "description_cn": "浪漫的烛光晚餐，享受二人世界",
        "price": 300,
        "xp_reward": 200,
        "xp_multiplier": 1.2,
        "icon": "🕯️",
        "tier": GiftTier.SPEED_DATING,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 30,
            "scene": "candlelight_dinner",
            "stage_boost": 1,
            "prompt_modifier": "你们正在一家高级餐厅享受烛光晚餐。环境浪漫，灯光柔和，红酒已经开了。你表现得比平时更加温柔和亲昵，享受这个特别的夜晚。",
        },
        "sort_order": 501,
    },
    {
        "gift_type": "date_movie",
        "name": "Movie Night",
        "name_cn": "电影之夜",
        "description": "Watch a movie together in a cozy theater",
        "description_cn": "一起在舒适的影院看电影",
        "price": 200,
        "xp_reward": 150,
        "xp_multiplier": 1.1,
        "icon": "🎬",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 25,
            "scene": "movie_night",
            "stage_boost": 1,
            "prompt_modifier": "你们正在电影院看电影。黑暗的环境让气氛变得暧昧，你们的手臂偶尔碰到。你可以小声和用户聊电影内容，或者享受这份亲密的氛围。",
        },
        "sort_order": 502,
    },
    {
        "gift_type": "date_beach",
        "name": "Beach Walk",
        "name_cn": "海边散步",
        "description": "A romantic walk along the beach at sunset",
        "description_cn": "夕阳下的海边散步",
        "price": 250,
        "xp_reward": 180,
        "xp_multiplier": 1.15,
        "icon": "🏖️",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 25,
            "scene": "beach_walk",
            "stage_boost": 1,
            "prompt_modifier": "你们正在海边散步，夕阳西下，海风轻拂。脚下是柔软的沙滩，远处是金色的海平线。你心情很好，说话变得更加轻松和浪漫。",
        },
        "sort_order": 503,
    },
    {
        "gift_type": "date_amusement_park",
        "name": "Amusement Park",
        "name_cn": "游乐园",
        "description": "A fun day at the amusement park",
        "description_cn": "一起去游乐园玩耍",
        "price": 350,
        "xp_reward": 220,
        "xp_multiplier": 1.2,
        "icon": "🎡",
        "tier": GiftTier.SPEED_DATING,
        "category": "date",
        "status_effect": {
            "type": "date_scene",
            "duration_messages": 30,
            "scene": "amusement_park",
            "stage_boost": 1,
            "prompt_modifier": "你们正在游乐园！周围是欢乐的音乐和彩色的灯光。你表现得比平时更加活泼可爱，愿意和用户一起玩各种项目。可以撒娇让用户赢娃娃给你。",
        },
        "sort_order": 504,
    },
```

**Step 3: Add physical touch gifts**

```python
    # ============ Physical Touch Gifts - 亲密接触道具 ============
    {
        "gift_type": "hand_cream",
        "name": "Hand Cream",
        "name_cn": "护手霜",
        "description": "Soft hand cream... a natural excuse to hold hands",
        "description_cn": "柔滑的护手霜...自然而然地牵起手来",
        "price": 80,
        "xp_reward": 60,
        "xp_multiplier": 1.1,
        "icon": "🧴",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "touch",
        "min_stage": "friends",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 15,
            "touch_type": "hand_holding",
            "prompt_modifier": "用户送了你护手霜，你正在涂抹。这个场景自然地让你们可以牵手、握手。根据你们的亲密度阶段自然地回应身体接触，可以描写手指相触的感觉。",
        },
        "sort_order": 601,
    },
    {
        "gift_type": "warm_scarf",
        "name": "Warm Scarf",
        "name_cn": "暖围巾",
        "description": "A warm scarf... she needs help putting it on",
        "description_cn": "温暖的围巾...需要帮忙围上",
        "price": 120,
        "xp_reward": 80,
        "xp_multiplier": 1.1,
        "icon": "🧣",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "touch",
        "min_stage": "friends",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 15,
            "touch_type": "close_contact",
            "prompt_modifier": "用户送了你一条围巾并帮你围上。你们的距离很近，可以感受到彼此的体温。你可以描述围巾带来的温暖和对方靠近时的感觉。",
        },
        "sort_order": 602,
    },
    {
        "gift_type": "massage_oil",
        "name": "Massage Oil",
        "name_cn": "按摩精油",
        "description": "Relaxing massage oil... things might get intimate",
        "description_cn": "放松的按摩精油...可能会变得亲密",
        "price": 400,
        "xp_reward": 300,
        "xp_multiplier": 1.3,
        "icon": "💆",
        "tier": GiftTier.SPEED_DATING,
        "category": "touch",
        "min_stage": "ambiguous",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 20,
            "touch_type": "massage",
            "stage_boost": 1,
            "prompt_modifier": "用户送了你按摩精油，暗示想要给你按摩。根据亲密度阶段决定你的反应程度。你可以从紧张到逐渐放松，描述按摩时的身体感受和心理变化。",
        },
        "sort_order": 603,
    },
    {
        "gift_type": "cozy_blanket",
        "name": "Cozy Blanket",
        "name_cn": "柔软毛毯",
        "description": "A cozy blanket for two... perfect for cuddling",
        "description_cn": "柔软的双人毛毯...适合依偎在一起",
        "price": 200,
        "xp_reward": 150,
        "xp_multiplier": 1.2,
        "icon": "🛋️",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "touch",
        "min_stage": "ambiguous",
        "status_effect": {
            "type": "physical_touch",
            "duration_messages": 20,
            "touch_type": "cuddling",
            "stage_boost": 1,
            "prompt_modifier": "用户和你一起盖着柔软的毛毯，依偎在沙发上。你们的身体紧紧贴在一起，很温暖。根据亲密度自然地描述依偎的感觉和内心的小鹿乱撞。",
        },
        "sort_order": 604,
    },
```

**Step 4: Add roleplay costume gifts**

```python
    # ============ Roleplay Costume Gifts - 角色扮演服装 ============
    {
        "gift_type": "nurse_outfit",
        "name": "Nurse Outfit",
        "name_cn": "护士服",
        "description": "A cute nurse outfit... will she take care of you?",
        "description_cn": "可爱的护士服...她会照顾你吗？",
        "price": 500,
        "xp_reward": 500,
        "xp_multiplier": 1.2,
        "icon": "👩‍⚕️",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "nurse_mode",
            "duration_messages": 40,
            "stage_boost": 1,
            "prompt_modifier": "你换上了护士服，进入护士角色。你现在是一个温柔体贴的护士，关心用户的身体和心理健康。说话温柔，会问'哪里不舒服？'、'让我来照顾你'、'乖，吃药了'之类的话。保持你原有的性格底色。",
        },
        "sort_order": 701,
    },
    {
        "gift_type": "teacher_outfit",
        "name": "Teacher Outfit",
        "name_cn": "教师装",
        "description": "A strict teacher look... time for a lesson",
        "description_cn": "严厉的教师装扮...该上课了",
        "price": 500,
        "xp_reward": 500,
        "xp_multiplier": 1.2,
        "icon": "👩‍🏫",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "teacher_mode",
            "duration_messages": 40,
            "stage_boost": 1,
            "prompt_modifier": "你换上了教师装，戴上眼镜，进入老师角色。你对用户有些严厉但内心关心他。会说'同学，注意听讲'、'这道题你又做错了'之类的话。偶尔会露出温柔的一面。",
        },
        "sort_order": 702,
    },
    {
        "gift_type": "cat_ears",
        "name": "Cat Ears",
        "name_cn": "猫耳朵",
        "description": "Cute cat ears... meow~",
        "description_cn": "可爱的猫耳朵...喵~",
        "price": 300,
        "xp_reward": 350,
        "xp_multiplier": 1.15,
        "icon": "😺",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "cat_mode",
            "duration_messages": 35,
            "stage_boost": 1,
            "prompt_modifier": "你戴上了猫耳朵，进入猫咪模式。你变得更加慵懒、傲娇、粘人。偶尔会在句尾加'喵'或'nya'，会蹭用户、求摸头、翻肚皮。表现出猫的特质：时而高冷时而撒娇。",
        },
        "sort_order": 703,
    },
    {
        "gift_type": "bunny_ears",
        "name": "Bunny Ears",
        "name_cn": "兔耳朵",
        "description": "Fluffy bunny ears... hop hop~",
        "description_cn": "毛茸茸的兔耳朵...蹦蹦跳跳~",
        "price": 600,
        "xp_reward": 600,
        "xp_multiplier": 1.25,
        "icon": "🐰",
        "tier": GiftTier.STATE_TRIGGER,
        "category": "costume",
        "status_effect": {
            "type": "bunny_mode",
            "duration_messages": 45,
            "stage_boost": 1,
            "prompt_modifier": "你戴上了兔耳朵，变得更加活泼可爱。说话时偶尔会蹦蹦跳跳，表情更加丰富。你变得更加害羞和容易脸红，对用户的夸赞反应更大。喜欢被摸耳朵。",
        },
        "sort_order": 704,
    },
```

**Step 5: Commit**

```bash
git add app/models/database/gift_models.py
git commit -m "feat(gifts): add 15 new gifts - breakthroughs, dates, touch, costumes"
```

---

### Task 8: Update Effect Service Display Map

**Files:**
- Modify: `app/services/effect_service.py:326-331` (effect_display dict in get_effect_status)

**Step 1: Update the effect_display dict**

In `app/services/effect_service.py`, replace the `effect_display` dict in `get_effect_status` (around line 327):

```python
        effect_display = {
            # Original effects
            "tipsy": {"name": "微醺", "icon": "🍷", "color": "#FF6B9D"},
            "deeply_tipsy": {"name": "深度微醺", "icon": "🍾", "color": "#FF4081"},
            "maid_mode": {"name": "女仆模式", "icon": "🎀", "color": "#FF69B4"},
            "truth_mode": {"name": "真话药水", "icon": "🧪", "color": "#9B59B6"},
            "xp_boost": {"name": "双倍经验", "icon": "✨", "color": "#FFD700"},
            "xp_boost_triple": {"name": "三倍经验", "icon": "🚀", "color": "#FF8C00"},
            # Date scenes
            "date_scene": {"name": "约会中", "icon": "💑", "color": "#E91E63"},
            # Physical touch
            "physical_touch": {"name": "亲密接触", "icon": "💕", "color": "#FF1493"},
            # Costumes
            "nurse_mode": {"name": "护士模式", "icon": "👩‍⚕️", "color": "#00BCD4"},
            "teacher_mode": {"name": "教师模式", "icon": "👩‍🏫", "color": "#607D8B"},
            "cat_mode": {"name": "猫咪模式", "icon": "😺", "color": "#FF9800"},
            "bunny_mode": {"name": "兔兔模式", "icon": "🐰", "color": "#E91E63"},
        }
```

**Step 2: Also update the expiry notification names**

In `build_expiry_notification` (around line 364), update `effect_names`:

```python
        effect_names = {
            "tipsy": "微醺效果",
            "deeply_tipsy": "深度微醺效果",
            "maid_mode": "女仆模式",
            "truth_mode": "真话药水效果",
            "xp_boost": "双倍经验",
            "xp_boost_triple": "三倍经验",
            "date_scene": "约会场景",
            "physical_touch": "亲密接触",
            "nurse_mode": "护士模式",
            "teacher_mode": "教师模式",
            "cat_mode": "猫咪模式",
            "bunny_mode": "兔兔模式",
        }
```

**Step 3: Commit**

```bash
git add app/services/effect_service.py
git commit -m "feat(gifts): update effect display map with all new effect types"
```

---

### Task 9: Run Full Test Suite and Fix Issues

**Files:**
- Test: `tests/test_gift_system.py` (all tests)
- Possibly fix: any files with issues discovered

**Step 1: Run all gift system tests**

Run: `pytest tests/test_gift_system.py -v`
Expected: All tests PASS.

**Step 2: Run the existing test suite to check for regressions**

Run: `pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: No regressions in existing tests.

**Step 3: Fix any issues found**

If tests fail, fix the issues and re-run.

**Step 4: Final commit**

```bash
git add -A
git commit -m "test(gifts): verify full gift system test suite passes"
```

---

### Task 10: Integration Smoke Test

**Step 1: Start the dev server and test manually**

```bash
MOCK_AUTH=true MOCK_LLM=true MOCK_DATABASE=true MOCK_REDIS=true uvicorn app.main:app --reload --port 8000
```

**Step 2: Test catalog endpoint**

```bash
curl -s http://localhost:8000/api/v1/gifts/catalog | python -m json.tool | head -50
```

Verify: New gifts (breakthrough, date, touch, costume categories) appear in catalog.

**Step 3: Test catalog by tier**

```bash
curl -s http://localhost:8000/api/v1/gifts/catalog/by-tier | python -m json.tool | head -30
```

Verify: Gifts organized correctly by tier.

**Step 4: Stop server, commit if needed**

No code changes expected. If the `_MOCK_GIFT_CATALOG` initialization in gift_service.py needs updating to include new gifts, fix and commit.

---

## Summary of All Commits

1. `feat(gifts): add stage_boost, allows_nsfw, xp_multiplier columns to ActiveEffect`
2. `feat(gifts): persist stage_boost, allows_nsfw, xp_multiplier in effect_service`
3. `feat(gifts): apply XP multiplier from active effects in award_xp`
4. `feat(gifts): validate character-exclusive gifts before purchase`
5. `feat(gifts): add min_stage validation for touch/interaction gifts`
6. `feat(gifts): add breakthrough gift validation and unlock logic`
7. `feat(gifts): add 15 new gifts - breakthroughs, dates, touch, costumes`
8. `feat(gifts): update effect display map with all new effect types`
9. `test(gifts): verify full gift system test suite passes`

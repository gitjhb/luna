# Gift System Overhaul Design

**Date:** 2026-03-07
**Approach:** Fix-and-Extend (build on existing architecture)

## Goals

1. Fix DB gaps so effects work in production (not just mock mode)
2. Complete the effect pipeline - every catalog flag actually executes
3. Add permanent breakthrough gifts for bottleneck advancement
4. Add new interaction gifts: date scenarios, physical touch items, roleplay costumes

## Decisions

- **Permanent breakthrough** requires being AT the bottleneck level. No skipping ahead.
- **Stage boost** (temporary) affects conversation tone ONLY, not feature gates (photos, spicy mode).
- **Approach A** chosen: fix and extend existing code, no architecture rewrite.

---

## Section 1: Fix DB & Effect Pipeline

### Problem
`ActiveEffect` DB model missing `stage_boost`, `allows_nsfw`, `xp_multiplier` columns. These only work in mock mode. XP multiplier from effects not consumed by `intimacy_service.award_xp`.

### Changes

**`app/models/database/gift_models.py` - ActiveEffect:**
- Add `stage_boost = Column(Integer, default=0)`
- Add `allows_nsfw = Column(Integer, default=0)` (SQLite boolean)
- Add `xp_multiplier = Column(Float, default=1.0)`

**`app/services/effect_service.py`:**
- `apply_effect()` persists `stage_boost`, `allows_nsfw`, `xp_multiplier` to DB
- `get_active_effects()` returns these fields from DB records
- `get_stage_boost()` reads from DB field, fallback to legacy dict

**`app/services/intimacy_service.py` - `award_xp()`:**
- Call `effect_service.get_xp_multiplier(user_id, character_id)` before awarding XP
- Multiply base XP by active multiplier

**Migration:** `migrations/add_effect_columns.sql` - ALTER TABLE to add 3 columns.

---

## Section 2: Complete Gift Effect Execution

### Problem
Catalog defines flags (`restores_energy`, `unlocks_memory`, `character_exclusive`, `can_calm_anger`) that aren't consumed in code.

### Execution order in `gift_service.send_gift()`:
```
1. Idempotency check
2. Balance check + deduct
3. Record gift in DB
4. Character exclusive validation
5. XP award (with multiplier from active effects)
6. Bottleneck unlock check
7. Emotion effects (boost / force / cold war clear / calm anger)
8. Status effect activation (prompt modifier, stage boost, NSFW override)
9. Energy restore (stamina_service)
10. Memory unlock
11. AI response generation
12. Chat history insertion
```

### New handler code:
- **`restores_energy`** -> `stamina_service.restore_stamina(user_id, amount)`
- **`character_exclusive`** -> Validate character_id matches, error if wrong character
- **`unlocks_memory`** -> Store unlock flag in user-character state
- **`can_calm_anger`** -> Verify emotion_engine integration works
- **`global_broadcast`** -> Deferred. Log TODO, no social infrastructure exists.

---

## Section 3: Permanent Breakthrough Gifts

### Design

New `"category": "breakthrough"` gifts with a `breakthrough` config:

```python
"breakthrough": {
    "from_stage": "S1",
    "to_stage": "S2",
    "required_bottleneck_level": 8,
}
```

### Gift types:
| Gift | Price | Bottleneck | Transition |
|------|-------|-----------|------------|
| Friendship Bracelet (友谊手链) | 200 | Lv.8 | S1->S2 |
| Promise Pendant (约定吊坠) | 500 | Lv.16 | S2->S3 |
| Eternal Bond Ring (永恒之戒) | 2000 | Lv.24 | S3->S4 |

### Logic:
1. Check user is at `required_bottleneck_level` and bottleneck is locked
2. If not -> error "You need to reach Level X first"
3. If yes -> `intimacy_service.unlock_bottleneck()` + bonus XP to push past
4. AI generates special breakthrough response (milestone moment)

---

## Section 4: New Interaction Gifts

### A. Date Scenario Gifts

Use existing `status_effect` mechanism with a `scene` metadata field for frontend.

| Gift | Price | Duration | Scene |
|------|-------|----------|-------|
| Candlelight Dinner (烛光晚餐) | 300 | 30 msgs | candlelight_dinner |
| Movie Night (电影之夜) | 200 | 25 msgs | movie_night |
| Beach Walk (海边散步) | 250 | 25 msgs | beach_walk |
| Amusement Park (游乐园) | 350 | 30 msgs | amusement_park |

Each injects a scene-specific prompt_modifier + stage_boost=1.

### B. Physical Touch Gifts

Items that unlock physical interaction dialogue. Requires `min_stage` validation.

| Gift | Price | Min Stage | Touch Type |
|------|-------|-----------|------------|
| Hand Cream (护手霜) | 80 | S1 | hand_holding |
| Warm Scarf (暖围巾) | 120 | S1 | close_contact |
| Massage Oil (按摩精油) | 400 | S2 | massage |
| Cozy Blanket (柔软毛毯) | 200 | S2 | cuddling |

### C. Roleplay Costume Gifts

Extend the maid_mode pattern. Pure catalog additions.

| Gift | Price | Duration | Mode |
|------|-------|----------|------|
| Nurse Outfit (护士服) | 500 | 40 msgs | nurse_mode |
| Teacher Outfit (教师装) | 500 | 40 msgs | teacher_mode |
| Cat Ears (猫耳朵) | 300 | 35 msgs | cat_mode |
| Bunny Ears (兔耳朵) | 600 | 45 msgs | bunny_mode |

### New validation logic:
- `min_stage` in `gift_service.send_gift()` - reject if user's stage is below required
- Update `effect_service.get_effect_status()` display map with new effect types

---

## Section 5: Testing

### Unit tests:
- `test_active_effect_db_persistence` - stage_boost, allows_nsfw, xp_multiplier saved/loaded
- `test_xp_multiplier_applied` - intimacy_service uses effect multiplier
- `test_character_exclusive_validation` - wrong character rejected
- `test_energy_restore` - stamina restored
- `test_min_stage_validation` - touch gifts rejected at wrong stage
- `test_emotion_effects_complete` - all emotion flags work
- `test_breakthrough_at_bottleneck` - succeeds
- `test_breakthrough_not_at_bottleneck` - fails with clear error
- `test_breakthrough_already_unlocked` - fails

### Integration test:
- `test_full_gift_flow` - send gift -> effect active -> chat uses modifier -> countdown -> expiry

All tests use mock mode.

---

## Files Changed

### Modified:
- `app/models/database/gift_models.py` - ActiveEffect columns, new catalog entries (~20 gifts)
- `app/services/effect_service.py` - DB persistence for new fields, display map updates
- `app/services/gift_service.py` - Complete effect execution, min_stage/character_exclusive/breakthrough logic
- `app/services/intimacy_service.py` - XP multiplier integration

### New:
- `migrations/add_effect_columns.sql` - DB migration
- `tests/test_gift_system.py` - Comprehensive test suite

"""
Effect Service - Status Effect Management
==========================================

Handles Tier 2 gift status effects:
- tipsy (微醺红酒)
- maid_mode (女仆发带)
- truth_mode (真话药水)

Effects last for a certain number of messages and modify AI prompts.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Check if database is available, default to mock if not
def _check_mock_mode() -> bool:
    env_mock = os.getenv("MOCK_DATABASE", "false").lower() == "true"
    if env_mock:
        return True
    # Also check if database is initialized
    try:
        from app.core.database import _session_factory
        return _session_factory is None
    except:
        return True

MOCK_MODE = _check_mock_mode()

# In-memory storage for mock mode
_MOCK_EFFECTS: Dict[str, dict] = {}


class EffectService:
    """
    Manages active status effects from Tier 2 gifts.
    
    Effects modify the AI's behavior through prompt injection.
    Each effect has a message countdown - once it reaches 0, the effect expires.
    """
    
    def __init__(self):
        self.mock_mode = MOCK_MODE
    
    # =========================================================================
    # Core Effect Operations
    # =========================================================================
    
    async def apply_effect(
        self,
        user_id: str,
        character_id: str,
        effect_type: str,
        prompt_modifier: str,
        duration_messages: int,
        gift_id: Optional[str] = None,
        stage_boost: int = 0,
        allows_nsfw: bool = False,
        xp_multiplier: float = 1.0,
    ) -> dict:
        """
        Apply a new status effect.
        
        If an effect of the same type already exists, it will be replaced
        (not stacked) to prevent exploit.
        
        Args:
            stage_boost: 临时升阶数量 (0-2)
            allows_nsfw: 是否解锁NSFW内容（角色特定）
        """
        effect_id = str(uuid4())
        now = datetime.utcnow()
        
        # Remove existing effect of same type (no stacking)
        await self.remove_effect_by_type(user_id, character_id, effect_type)
        
        effect = {
            "id": effect_id,
            "user_id": user_id,
            "character_id": character_id,
            "effect_type": effect_type,
            "prompt_modifier": prompt_modifier,
            "remaining_messages": duration_messages,
            "gift_id": gift_id,
            "started_at": now,
            "expires_at": None,  # No hard expiry, only message-based
            "stage_boost": stage_boost,
            "allows_nsfw": allows_nsfw,
            "xp_multiplier": xp_multiplier,
        }
        
        if self.mock_mode:
            key = f"{user_id}:{character_id}:{effect_type}"
            _MOCK_EFFECTS[key] = effect
            logger.info(f"Applied effect {effect_type} for {duration_messages} messages (mock)")
        else:
            from app.core.database import get_db
            from app.models.database.gift_models import ActiveEffect
            
            async with get_db() as db:
                effect_obj = ActiveEffect(
                    id=effect_id,
                    user_id=user_id,
                    character_id=character_id,
                    effect_type=effect_type,
                    prompt_modifier=prompt_modifier,
                    remaining_messages=duration_messages,
                    gift_id=gift_id,
                    started_at=now,
                    stage_boost=stage_boost,
                    allows_nsfw=1 if allows_nsfw else 0,
                    xp_multiplier=xp_multiplier,
                )
                db.add(effect_obj)
                await db.commit()
                logger.info(f"Applied effect {effect_type} for {duration_messages} messages (db)")
        
        return effect
    
    async def get_active_effects(
        self,
        user_id: str,
        character_id: str,
    ) -> List[dict]:
        """
        Get all active effects for a user-character pair.
        
        Returns only non-expired effects.
        """
        if self.mock_mode:
            prefix = f"{user_id}:{character_id}:"
            effects = [
                e for key, e in _MOCK_EFFECTS.items()
                if key.startswith(prefix) and e["remaining_messages"] > 0
            ]
            return effects
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.gift_models import ActiveEffect
        
        async with get_db() as db:
            result = await db.execute(
                select(ActiveEffect).where(
                    ActiveEffect.user_id == user_id,
                    ActiveEffect.character_id == character_id,
                    ActiveEffect.remaining_messages > 0
                )
            )
            effects = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "user_id": e.user_id,
                    "character_id": e.character_id,
                    "effect_type": e.effect_type,
                    "prompt_modifier": e.prompt_modifier,
                    "remaining_messages": e.remaining_messages,
                    "gift_id": e.gift_id,
                    "started_at": e.started_at,
                    "stage_boost": getattr(e, 'stage_boost', 0) or 0,
                    "allows_nsfw": bool(getattr(e, 'allows_nsfw', 0)),
                    "xp_multiplier": getattr(e, 'xp_multiplier', 1.0) or 1.0,
                }
                for e in effects
            ]
    
    async def get_combined_prompt_modifier(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[str]:
        """
        Get combined prompt modifier from all active effects.
        
        Multiple effects are combined with newlines.
        Returns None if no active effects.
        """
        effects = await self.get_active_effects(user_id, character_id)
        
        if not effects:
            return None
        
        modifiers = [e["prompt_modifier"] for e in effects]
        combined = "\n\n".join(modifiers)
        
        # Add header for AI context
        header = f"[状态效果 - 当前有 {len(effects)} 个效果生效中]"
        
        return f"{header}\n{combined}"
    
    async def decrement_effects(
        self,
        user_id: str,
        character_id: str,
    ) -> List[dict]:
        """
        Decrement remaining messages for all active effects.
        
        Call this after each message exchange.
        Returns list of expired effects (for notification).
        """
        expired = []
        
        if self.mock_mode:
            prefix = f"{user_id}:{character_id}:"
            keys_to_remove = []
            
            for key, effect in _MOCK_EFFECTS.items():
                if key.startswith(prefix):
                    effect["remaining_messages"] -= 1
                    
                    if effect["remaining_messages"] <= 0:
                        expired.append(effect.copy())
                        keys_to_remove.append(key)
                        logger.info(f"Effect {effect['effect_type']} expired")
            
            for key in keys_to_remove:
                del _MOCK_EFFECTS[key]
        else:
            from app.core.database import get_db
            from sqlalchemy import select
            from app.models.database.gift_models import ActiveEffect
            
            async with get_db() as db:
                result = await db.execute(
                    select(ActiveEffect).where(
                        ActiveEffect.user_id == user_id,
                        ActiveEffect.character_id == character_id,
                        ActiveEffect.remaining_messages > 0
                    )
                )
                effects = result.scalars().all()
                
                for effect in effects:
                    effect.remaining_messages -= 1
                    
                    if effect.remaining_messages <= 0:
                        expired.append({
                            "id": effect.id,
                            "effect_type": effect.effect_type,
                            "prompt_modifier": effect.prompt_modifier,
                        })
                        await db.delete(effect)
                        logger.info(f"Effect {effect.effect_type} expired")
                
                await db.commit()
        
        return expired
    
    async def remove_effect_by_type(
        self,
        user_id: str,
        character_id: str,
        effect_type: str,
    ) -> bool:
        """
        Remove a specific effect type.
        
        Used when applying a new effect of the same type (no stacking).
        """
        if self.mock_mode:
            key = f"{user_id}:{character_id}:{effect_type}"
            if key in _MOCK_EFFECTS:
                del _MOCK_EFFECTS[key]
                return True
            return False
        
        from app.core.database import get_db
        from sqlalchemy import select, delete
        from app.models.database.gift_models import ActiveEffect
        
        async with get_db() as db:
            result = await db.execute(
                delete(ActiveEffect).where(
                    ActiveEffect.user_id == user_id,
                    ActiveEffect.character_id == character_id,
                    ActiveEffect.effect_type == effect_type
                )
            )
            await db.commit()
            return result.rowcount > 0
    
    async def clear_all_effects(
        self,
        user_id: str,
        character_id: str,
    ) -> int:
        """
        Clear all active effects for a user-character pair.
        
        Returns number of effects cleared.
        """
        if self.mock_mode:
            prefix = f"{user_id}:{character_id}:"
            keys_to_remove = [k for k in _MOCK_EFFECTS.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del _MOCK_EFFECTS[key]
            return len(keys_to_remove)
        
        from app.core.database import get_db
        from sqlalchemy import delete
        from app.models.database.gift_models import ActiveEffect
        
        async with get_db() as db:
            result = await db.execute(
                delete(ActiveEffect).where(
                    ActiveEffect.user_id == user_id,
                    ActiveEffect.character_id == character_id
                )
            )
            await db.commit()
            return result.rowcount
    
    # =========================================================================
    # Effect Status for UI
    # =========================================================================
    
    async def get_effect_status(
        self,
        user_id: str,
        character_id: str,
    ) -> dict:
        """
        Get effect status summary for UI display.
        """
        effects = await self.get_active_effects(user_id, character_id)
        
        # Map effect types to display names
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
        
        active = []
        for effect in effects:
            etype = effect["effect_type"]
            display = effect_display.get(etype, {"name": etype, "icon": "✨", "color": "#888"})
            
            active.append({
                "type": etype,
                "name": display["name"],
                "icon": display["icon"],
                "color": display["color"],
                "remaining": effect["remaining_messages"],
                "started_at": effect["started_at"].isoformat() if effect.get("started_at") else None,
            })
        
        return {
            "has_effects": len(active) > 0,
            "count": len(active),
            "effects": active,
        }
    
    # =========================================================================
    # Utility: Build System Message for Effect Expiry
    # =========================================================================
    
    def build_expiry_notification(self, expired_effects: List[dict]) -> Optional[str]:
        """
        Build a system message notifying the AI that effects have expired.
        """
        if not expired_effects:
            return None
        
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
        
        expired_names = [
            effect_names.get(e["effect_type"], e["effect_type"])
            for e in expired_effects
        ]
        
        if len(expired_names) == 1:
            return f"[系统提示：{expired_names[0]}已经结束，恢复正常状态]"
        else:
            return f"[系统提示：以下效果已结束 - {', '.join(expired_names)}，恢复正常状态]"

    # =========================================================================
    # Stage Boost & XP Multiplier System
    # =========================================================================
    
    # Effect type -> Stage boost (fallback for old effects without stage_boost field)
    EFFECT_STAGE_BOOSTS_FALLBACK = {
        "tipsy": 1,        # 微醺红酒: 临时升1阶
        "maid_mode": 1,    # 女仆模式: 临时升1阶
        "deeply_tipsy": 2, # 珍藏红酒: 临时升2阶
    }
    
    # Effect type -> XP multiplier
    EFFECT_XP_MULTIPLIERS = {
        "xp_boost": 2.0,        # 双倍经验
        "xp_boost_triple": 3.0, # 三倍经验
    }
    
    async def get_stage_boost(
        self,
        user_id: str,
        character_id: str,
    ) -> int:
        """
        Get the maximum stage boost from all active effects.
        
        Returns number of stages to temporarily boost (0 = no boost).
        Now reads from effect record's stage_boost field, with fallback to legacy dict.
        """
        effects = await self.get_active_effects(user_id, character_id)
        
        max_boost = 0
        for effect in effects:
            # 优先使用效果记录中的 stage_boost 字段
            boost = effect.get("stage_boost", 0)
            if boost == 0:
                # fallback 到旧的硬编码映射
                etype = effect["effect_type"]
                boost = self.EFFECT_STAGE_BOOSTS_FALLBACK.get(etype, 0)
            max_boost = max(max_boost, boost)
        
        return max_boost
    
    async def get_nsfw_override(
        self,
        user_id: str,
        character_id: str,
    ) -> bool:
        """
        Check if any active effect grants NSFW access for this character.
        
        Returns True if user has an active effect with allows_nsfw=True.
        This is character-specific (e.g., Vera with wine).
        """
        effects = await self.get_active_effects(user_id, character_id)
        
        for effect in effects:
            if effect.get("allows_nsfw", False):
                return True
        
        return False
    
    async def get_xp_multiplier(
        self,
        user_id: str,
        character_id: str,
    ) -> float:
        """
        Get XP multiplier from active effects.
        
        Returns multiplier (1.0 = no boost, 2.0 = double XP).
        Multiple XP effects do NOT stack (use max).
        """
        effects = await self.get_active_effects(user_id, character_id)
        
        max_mult = 1.0
        for effect in effects:
            etype = effect["effect_type"]
            mult = self.EFFECT_XP_MULTIPLIERS.get(etype, 1.0)
            max_mult = max(max_mult, mult)
        
        return max_mult
    
    # =========================================================================
    # Power Buff System
    # =========================================================================
    
    # Effect type -> Power buff value
    EFFECT_POWER_BUFFS = {
        "tipsy": 15.0,       # 微醺红酒: +15 Power (降低戒备心)
        "maid_mode": 5.0,    # 女仆模式: +5 Power (轻微加成)
        "truth_mode": 10.0,  # 真话药水: +10 Power (更坦诚)
        "apology": 20.0,     # 悔过书: +20 Power (解除冷战buff)
    }
    
    async def get_power_buff(
        self,
        user_id: str,
        character_id: str,
    ) -> tuple[float, list[dict]]:
        """
        Get total power buff from all active effects.
        
        Returns:
            (total_buff, list of {effect_type, buff_value, remaining})
        """
        effects = await self.get_active_effects(user_id, character_id)
        
        total_buff = 0.0
        buff_details = []
        
        for effect in effects:
            etype = effect["effect_type"]
            buff_value = self.EFFECT_POWER_BUFFS.get(etype, 0.0)
            
            if buff_value > 0:
                total_buff += buff_value
                buff_details.append({
                    "effect_type": etype,
                    "buff_value": buff_value,
                    "remaining": effect["remaining_messages"],
                })
        
        return total_buff, buff_details


# Global service instance
effect_service = EffectService()

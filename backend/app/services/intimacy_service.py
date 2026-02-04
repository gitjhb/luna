"""
Intimacy Service - Core XP and Level Engine
============================================

Handles XP calculation, level progression, daily caps, cooldowns,
and intimacy stage management for user-character relationships.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)

# 默认使用数据库持久化
MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"
logger.info(f"IntimacyService MOCK_MODE: {MOCK_MODE}")

# Module-level storage for mock mode (persists across requests)
_MOCK_INTIMACY_STORAGE: Dict[str, Dict] = {}
_MOCK_ACTION_LOGS: List[Dict] = []


class IntimacyService:
    """
    Core service for managing user-character intimacy progression.

    Implements the XP-based gamification system with:
    - Exponential level progression (100 * 1.15^level)
    - Daily XP caps (500 AP/day)
    - Action-based XP rewards with cooldowns
    - 5 intimacy stages with distinct AI behavior
    """

    # XP Formula Constants - 等级越来越难升
    # 前3级在10次交互(20 XP)内解锁，之后指数增长
    # Level 1: 4 XP (2条消息)
    # Level 2: 20 XP (10条消息)  
    # Level 3: 50 XP (25条消息)
    # Level 4: 100 XP (50条消息)
    # Level 5: 180 XP - 从陌生人毕业需要约90条消息
    # Level 6+: 指数增长
    EARLY_LEVEL_XP = [0, 10, 20, 50, 100, 180, 280, 400, 550, 750]  # XP thresholds for levels 0-9
    BASE_XP = 300  # Base for exponential after level 9
    MULTIPLIER = 1.3  # Steeper curve after early levels
    MAX_LEVEL = 50
    DAILY_XP_CAP = 500

    # Action Point (AP) Rewards and Limits
    ACTION_REWARDS = {
        "message": {
            "xp": 2,
            "name": "Send Message",
            "name_cn": "发送消息",
            "daily_limit": None,  # Unlimited
            "cooldown_seconds": 0,
        },
        "continuous_chat": {
            "xp": 5,
            "name": "Continuous Chat Bonus",
            "name_cn": "连续对话奖励",
            "daily_limit": None,
            "cooldown_seconds": 0,
        },
        "checkin": {
            "xp": 20,
            "name": "Daily Check-in",
            "name_cn": "每日签到",
            "daily_limit": 1,
            "cooldown_seconds": 86400,  # 24 hours
        },
        "emotional": {
            "xp": 10,
            "name": "Emotional Expression",
            "name_cn": "情感表达",
            "daily_limit": 5,
            "cooldown_seconds": 0,
        },
        "voice": {
            "xp": 15,
            "name": "Voice Interaction",
            "name_cn": "语音互动",
            "daily_limit": 3,
            "cooldown_seconds": 300,  # 5 minutes
        },
        "share": {
            "xp": 50,
            "name": "Share with Friend",
            "name_cn": "分享给好友",
            "daily_limit": 1,
            "cooldown_seconds": 604800,  # 7 days (weekly)
        },
    }

    # Intimacy Stages (v3.0)
    # ==========================================================================
    # 双轨制阶段定义 (Level 1-40 ↔ Intimacy 0-100 ↔ S0-S4)
    # ==========================================================================
    # 映射关系：
    #   S0 strangers  → Level 1-5   → Intimacy 0-19
    #   S1 friends    → Level 6-10  → Intimacy 20-39
    #   S2 ambiguous  → Level 11-15 → Intimacy 40-59
    #   S3 lovers     → Level 16-25 → Intimacy 60-79
    #   S4 soulmates  → Level 26-40 → Intimacy 80-100
    # ==========================================================================
    STAGES = {
        "strangers": {
            "code": "S0",
            "name": "Strangers",
            "name_cn": "陌生人",
            "min_level": 1,
            "max_level": 5,
            "min_intimacy": 0,
            "max_intimacy": 19,
            "description": "Cold and polite, keeps distance",
            "ai_attitude": "冷淡礼貌，保持距离",
            "physical": "抗拒任何身体接触",
            "refusal": "我们还不熟。",
            "date_behavior": "只能并排走、聊天",
        },
        "friends": {
            "code": "S1",
            "name": "Friends",
            "name_cn": "朋友",
            "min_level": 6,
            "max_level": 10,
            "min_intimacy": 20,
            "max_intimacy": 39,
            "description": "Friendly and relaxed, casual conversations",
            "ai_attitude": "友好放松，轻松聊天",
            "physical": "可以摸头，拒绝亲吻",
            "refusal": "朋友之间不该做这个。",
            "date_behavior": "可以牵手、轻微身体接触",
        },
        "ambiguous": {
            "code": "S2",
            "name": "Ambiguous",
            "name_cn": "暧昧",
            "min_level": 11,
            "max_level": 15,
            "min_intimacy": 40,
            "max_intimacy": 59,
            "description": "Shy push-pull, testing boundaries",
            "ai_attitude": "害羞推拉，试探边界",
            "physical": "偶尔接受调情，偶尔拒绝",
            "refusal": "还没准备好...",
            "date_behavior": "牵手、挽手臂、靠在肩上",
        },
        "lovers": {
            "code": "S3",
            "name": "Lovers",
            "name_cn": "恋人",
            "min_level": 16,
            "max_level": 25,
            "min_intimacy": 60,
            "max_intimacy": 79,
            "description": "Cooperative and proactive, sweet intimacy",
            "ai_attitude": "配合主动，甜蜜亲密",
            "physical": "允许 NSFW，配合主动",
            "refusal": "只有心情极差才拒绝",
            "date_behavior": "亲脸颊、拥抱、甜蜜情话",
        },
        "soulmates": {
            "code": "S4",
            "name": "Soulmates",
            "name_cn": "挚爱",
            "min_level": 26,
            "max_level": 40,
            "min_intimacy": 80,
            "max_intimacy": 100,
            "description": "Devoted and submissive, unconditional love",
            "ai_attitude": "奉献服从，无条件的爱",
            "physical": "无条件包容，解锁极端玩法",
            "refusal": "绝不拒绝",
            "date_behavior": "亲吻、深度拥抱、暧昧暗示",
        },
    }

    # Feature Unlocks by Level
    FEATURE_UNLOCKS = {
        1: {"id": "basic_chat", "name": "Basic Chat", "name_cn": "基础对话"},
        3: {"id": "photo", "name": "Photo", "name_cn": "📸 拍照"},
        6: {"id": "dressup", "name": "Dress Up", "name_cn": "👗 换装 + 🎤 语音"},
        11: {"id": "spicy_mode", "name": "Spicy Mode", "name_cn": "Spicy模式"},
        16: {"id": "video_calls", "name": "Video Calls", "name_cn": "视频通话"},
        26: {"id": "wedding_dress", "name": "Wedding Dress 💍", "name_cn": "婚纱 💍"},
    }
    
    # 照片功能配置
    PHOTO_COST = 10  # 每张照片消耗10金币
    
    # 连续打卡奖励配置
    STREAK_REWARD_DAYS = 7  # 连续7天触发奖励
    STREAK_REWARD_XP = 100  # 奖励100 XP
    STREAK_REWARD_DESC = "神秘礼物"

    # Emotional words for bonus XP detection
    EMOTIONAL_WORDS_CN = [
        "喜欢", "爱", "开心", "快乐", "幸福", "想你", "想念", "感谢", "谢谢",
        "可爱", "漂亮", "美丽", "温柔", "善良", "聪明", "厉害", "棒", "赞",
        "心动", "甜蜜", "暖心", "感动", "珍惜", "在乎", "关心", "陪伴"
    ]
    EMOTIONAL_WORDS_EN = [
        "love", "like", "happy", "joy", "miss", "thank", "cute", "beautiful",
        "sweet", "kind", "smart", "amazing", "wonderful", "care", "cherish"
    ]

    def __init__(self):
        self.mock_mode = MOCK_MODE

    # =========================================================================
    # XP & Level Calculations
    # =========================================================================

    @classmethod
    def xp_for_level(cls, level: int) -> float:
        """
        Calculate total XP required to reach a specific level.
        Level 1 is the starting level (0 XP).
        Early levels (2-6) use predefined thresholds for quick progression.
        Later levels use exponential formula.
        """
        if level <= 1:
            return 0  # Level 1 starts at 0 XP
        # Shift index: level 2 uses EARLY_LEVEL_XP[1], etc.
        if level - 1 < len(cls.EARLY_LEVEL_XP):
            return cls.EARLY_LEVEL_XP[level - 1]
        # Exponential for levels 7+
        return cls.BASE_XP * (cls.MULTIPLIER ** (level - 6))

    @classmethod
    def xp_required_for_level(cls, level: int) -> float:
        """Calculate XP needed to go from level-1 to level."""
        if level <= 0:
            return 0
        return cls.xp_for_level(level) - cls.xp_for_level(level - 1)

    @classmethod
    def calculate_level(cls, total_xp: float) -> int:
        """
        Calculate level from total XP.
        Uses xp_for_level() thresholds for consistent lookup.
        
        Level progression:
        - Levels 1-10: Use EARLY_LEVEL_XP table
        - Levels 11+: Use exponential formula: BASE_XP * (MULTIPLIER ** (level - 6))
        """
        import math
        
        # Check early levels first (1-10)
        for level in range(len(cls.EARLY_LEVEL_XP), 0, -1):
            if total_xp >= cls.EARLY_LEVEL_XP[level - 1]:
                # Found the base level, now check if we're in exponential range
                if level == len(cls.EARLY_LEVEL_XP):  # At level 10, check for higher
                    # Exponential formula: xp = BASE_XP * (MULTIPLIER ** (level - 6))
                    # Reverse: level = 6 + log(xp / BASE_XP) / log(MULTIPLIER)
                    if total_xp >= cls.BASE_XP:
                        computed_level = 6 + int(math.log(total_xp / cls.BASE_XP) / math.log(cls.MULTIPLIER))
                        return min(max(computed_level, level), cls.MAX_LEVEL)
                return level
        return 1  # Level starts at 1
        
    @classmethod
    def _legacy_calculate_level(cls, total_xp: float) -> int:
        """Legacy method for reference."""
        if total_xp < cls.BASE_XP:
            return 1  # Level starts at 1, not 0

        import math
        level = int(math.log(total_xp / cls.BASE_XP) / math.log(cls.MULTIPLIER))
        return min(level, cls.MAX_LEVEL)

    @classmethod
    def get_level_progress(cls, total_xp: float) -> Tuple[int, float, float, float]:
        """
        Get detailed level progress information.

        Returns:
            (current_level, xp_at_current_level, xp_for_next_level, progress_percent)
        """
        current_level = cls.calculate_level(total_xp)

        if current_level >= cls.MAX_LEVEL:
            return (cls.MAX_LEVEL, total_xp, total_xp, 100.0)

        xp_at_current = cls.xp_for_level(current_level)
        xp_for_next = cls.xp_for_level(current_level + 1)
        xp_in_level = total_xp - xp_at_current
        xp_needed = xp_for_next - xp_at_current

        progress = (xp_in_level / xp_needed) * 100 if xp_needed > 0 else 100.0

        return (current_level, xp_at_current, xp_for_next, progress)

    # =========================================================================
    # Stage Management
    # =========================================================================

    @classmethod
    def get_stage(cls, level: int) -> Dict:
        """Get intimacy stage info for a given level."""
        for stage_id, stage_info in cls.STAGES.items():
            if stage_info["min_level"] <= level <= stage_info["max_level"]:
                return {"id": stage_id, **stage_info}

        # Default to max stage if over 50
        return {"id": "soulmates", **cls.STAGES["soulmates"]}

    @classmethod
    def get_stage_id(cls, level: int) -> str:
        """Get stage ID for a given level."""
        return cls.get_stage(level)["id"]

    @classmethod
    def get_stage_by_intimacy(cls, intimacy: int) -> Dict:
        """
        Get stage info by intimacy value (0-100).
        
        双轨制：intimacy 值对应的阶段
        - 0-19: S0 strangers
        - 20-39: S1 friends
        - 40-59: S2 ambiguous
        - 60-79: S3 lovers
        - 80-100: S4 soulmates
        """
        intimacy = max(0, min(100, intimacy))  # clamp to 0-100
        for stage_id, stage_info in cls.STAGES.items():
            if stage_info["min_intimacy"] <= intimacy <= stage_info["max_intimacy"]:
                return {"id": stage_id, **stage_info}
        return {"id": "soulmates", **cls.STAGES["soulmates"]}

    @classmethod
    def get_stage_id_by_intimacy(cls, intimacy: int) -> str:
        """Get stage ID by intimacy value (0-100)."""
        return cls.get_stage_by_intimacy(intimacy)["id"]

    @classmethod
    def level_to_intimacy(cls, level: int) -> int:
        """
        Convert level (1-40) to intimacy (0-100).
        
        简化映射：intimacy ≈ (level - 1) * 2.5
        """
        level = max(1, min(40, level))
        return min(100, int((level - 1) * 2.5))

    @classmethod
    def intimacy_to_level(cls, intimacy: int) -> int:
        """
        Convert intimacy (0-100) to level (1-40).
        
        简化映射：level ≈ intimacy / 2.5 + 1
        """
        intimacy = max(0, min(100, intimacy))
        return max(1, min(40, int(intimacy / 2.5) + 1))

    @classmethod
    def get_stage_behavior(cls, level: int = None, intimacy: int = None) -> Dict:
        """
        Get stage behavior info for AI prompts.
        
        可以传 level 或 intimacy，二选一。
        """
        if level is not None:
            stage = cls.get_stage(level)
        elif intimacy is not None:
            stage = cls.get_stage_by_intimacy(intimacy)
        else:
            stage = cls.STAGES["strangers"]
        
        return {
            "code": stage.get("code", "S0"),
            "name_cn": stage.get("name_cn", "陌生人"),
            "ai_attitude": stage.get("ai_attitude", ""),
            "physical": stage.get("physical", ""),
            "refusal": stage.get("refusal", ""),
            "date_behavior": stage.get("date_behavior", ""),
        }

    # =========================================================================
    # Feature Unlocks
    # =========================================================================

    @classmethod
    def get_unlocked_features(cls, level: int) -> List[Dict]:
        """Get list of features unlocked at or below the given level."""
        unlocked = []
        for unlock_level, feature in cls.FEATURE_UNLOCKS.items():
            if unlock_level <= level:
                unlocked.append({
                    "level": unlock_level,
                    **feature,
                    "is_unlocked": True
                })
        return unlocked

    @classmethod
    def get_newly_unlocked_features(cls, old_level: int, new_level: int) -> List[Dict]:
        """Get features unlocked between old_level and new_level."""
        newly_unlocked = []
        for unlock_level, feature in cls.FEATURE_UNLOCKS.items():
            if old_level < unlock_level <= new_level:
                newly_unlocked.append({
                    "level": unlock_level,
                    **feature,
                    "is_unlocked": True
                })
        return newly_unlocked

    # =========================================================================
    # Emotional Words Detection
    # =========================================================================

    @classmethod
    def contains_emotional_words(cls, message: str) -> bool:
        """Check if message contains emotional words for bonus XP."""
        message_lower = message.lower()

        for word in cls.EMOTIONAL_WORDS_CN:
            if word in message:
                return True

        for word in cls.EMOTIONAL_WORDS_EN:
            if word in message_lower:
                return True

        return False

    # =========================================================================
    # Core XP Operations (Mock Implementation)
    # =========================================================================

    def _get_intimacy_key(self, user_id: str, character_id: str) -> str:
        """Generate storage key for user-character pair."""
        return f"{user_id}:{character_id}"

    async def get_or_create_intimacy(self, user_id: str, character_id: str) -> Dict:
        """Get or create intimacy record for user-character pair."""
        if self.mock_mode:
            key = self._get_intimacy_key(user_id, character_id)
            if key not in _MOCK_INTIMACY_STORAGE:
                _MOCK_INTIMACY_STORAGE[key] = {
                    "user_id": user_id,
                    "character_id": character_id,
                    "total_xp": 0.0,
                    "current_level": 1,
                    "intimacy_stage": "strangers",
                    "daily_xp_earned": 0.0,
                    "last_daily_reset": datetime.utcnow(),
                    "streak_days": 0,
                    "last_interaction_date": None,
                    "total_messages": 0,
                    "gifts_count": 0,
                    "special_events": 0,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            return _MOCK_INTIMACY_STORAGE[key]
        
        # Database mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.intimacy_models import UserIntimacy
        
        async with get_db() as db:
            result = await db.execute(
                select(UserIntimacy).where(
                    UserIntimacy.user_id == user_id,
                    UserIntimacy.character_id == character_id
                )
            )
            intimacy = result.scalar_one_or_none()
            
            if not intimacy:
                intimacy = UserIntimacy(
                    user_id=user_id,
                    character_id=character_id,
                    total_xp=0.0,
                    current_level=1,
                    intimacy_stage="strangers",
                    daily_xp_earned=0.0,
                )
                db.add(intimacy)
                await db.commit()
                await db.refresh(intimacy)
                logger.info(f"Created new intimacy record for {user_id}/{character_id}")
            
            # Check and apply daily reset if needed
            if intimacy.needs_daily_reset():
                intimacy.apply_daily_reset()
                await db.commit()
            
            return {
                "user_id": intimacy.user_id,
                "character_id": intimacy.character_id,
                "total_xp": intimacy.total_xp,
                "current_level": intimacy.current_level,
                "intimacy_stage": intimacy.intimacy_stage,
                "daily_xp_earned": intimacy.daily_xp_earned,
                "last_daily_reset": intimacy.last_daily_reset,
                "streak_days": intimacy.streak_days,
                "last_interaction_date": intimacy.last_interaction_date,
                "total_messages": getattr(intimacy, 'total_messages', 0) or 0,
                "gifts_count": getattr(intimacy, 'gifts_count', 0) or 0,
                "special_events": getattr(intimacy, 'special_events', 0) or 0,
                "created_at": intimacy.created_at,
                "updated_at": intimacy.updated_at,
            }

    async def check_action_available(
        self,
        user_id: str,
        character_id: str,
        action_type: str
    ) -> Tuple[bool, Optional[int], int]:
        """
        Check if an action is available for XP award.

        Returns:
            (is_available, cooldown_seconds_remaining, used_today)
        """
        if action_type not in self.ACTION_REWARDS:
            return (False, None, 0)

        action_config = self.ACTION_REWARDS[action_type]
        daily_limit = action_config.get("daily_limit")
        cooldown_seconds = action_config.get("cooldown_seconds", 0)

        # Count actions today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        used_today = sum(
            1 for log in _MOCK_ACTION_LOGS
            if log["user_id"] == user_id
            and log["character_id"] == character_id
            and log["action_type"] == action_type
            and log["created_at"] >= today_start
        )

        # Check daily limit
        if daily_limit is not None and used_today >= daily_limit:
            return (False, None, used_today)

        # Check cooldown
        if cooldown_seconds > 0:
            recent_logs = [
                log for log in _MOCK_ACTION_LOGS
                if log["user_id"] == user_id
                and log["character_id"] == character_id
                and log["action_type"] == action_type
            ]
            if recent_logs:
                last_action = max(recent_logs, key=lambda x: x["created_at"])
                elapsed = (datetime.utcnow() - last_action["created_at"]).total_seconds()
                if elapsed < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed)
                    return (False, remaining, used_today)

        return (True, None, used_today)

    async def award_xp(
        self,
        user_id: str,
        character_id: str,
        action_type: str,
        force: bool = False
    ) -> Dict:
        """
        Award XP for an action.

        Args:
            user_id: User ID
            character_id: Character ID
            action_type: Type of action (message, checkin, etc.)
            force: If True, bypass cooldown/limit checks

        Returns:
            XPAwardResponse-compatible dict
        """
        if action_type not in self.ACTION_REWARDS:
            return {
                "success": False,
                "action_type": action_type,
                "xp_awarded": 0,
                "message": f"Unknown action type: {action_type}"
            }

        # Check if action is available
        if not force:
            available, cooldown, used_today = await self.check_action_available(
                user_id, character_id, action_type
            )
            if not available:
                if cooldown:
                    return {
                        "success": False,
                        "action_type": action_type,
                        "xp_awarded": 0,
                        "message": f"Action on cooldown. {cooldown} seconds remaining.",
                        "cooldown_seconds": cooldown
                    }
                return {
                    "success": False,
                    "action_type": action_type,
                    "xp_awarded": 0,
                    "message": "Daily limit reached for this action."
                }

        # Get/create intimacy record
        intimacy = await self.get_or_create_intimacy(user_id, character_id)

        # Check daily XP cap
        xp_reward = self.ACTION_REWARDS[action_type]["xp"]

        # Reset daily counter if needed
        if intimacy["last_daily_reset"]:
            time_since = datetime.utcnow() - intimacy["last_daily_reset"]
            if time_since.total_seconds() >= 86400:
                intimacy["daily_xp_earned"] = 0.0
                intimacy["last_daily_reset"] = datetime.utcnow()

        # Check cap
        if intimacy["daily_xp_earned"] >= self.DAILY_XP_CAP:
            return {
                "success": False,
                "action_type": action_type,
                "xp_awarded": 0,
                "message": f"Daily XP cap ({self.DAILY_XP_CAP}) reached."
            }

        # Apply cap if would exceed
        xp_to_award = min(xp_reward, self.DAILY_XP_CAP - intimacy["daily_xp_earned"])

        # Store previous values
        xp_before = intimacy["total_xp"]
        level_before = intimacy["current_level"]
        stage_before = intimacy["intimacy_stage"]

        # Award XP
        intimacy["total_xp"] += xp_to_award
        intimacy["daily_xp_earned"] += xp_to_award
        intimacy["updated_at"] = datetime.utcnow()

        # Calculate new level
        new_level = self.calculate_level(intimacy["total_xp"])
        intimacy["current_level"] = new_level

        # Check stage change
        new_stage_info = self.get_stage(new_level)
        new_stage = new_stage_info["id"]
        intimacy["intimacy_stage"] = new_stage

        # Update streak
        today = datetime.utcnow().date()
        streak_reward_triggered = False
        old_streak = intimacy["streak_days"] or 0  # Handle None
        
        if intimacy["last_interaction_date"] is None:
            intimacy["streak_days"] = 1
        elif intimacy["last_interaction_date"] == today:
            pass  # Already interacted today
        elif (today - intimacy["last_interaction_date"]).days == 1:
            intimacy["streak_days"] += 1
        else:
            intimacy["streak_days"] = 1  # 断签重置
        intimacy["last_interaction_date"] = today
        
        # 检查7天连续打卡奖励
        if (old_streak < self.STREAK_REWARD_DAYS and 
            intimacy["streak_days"] >= self.STREAK_REWARD_DAYS):
            streak_reward_triggered = True
            # 额外奖励 XP
            intimacy["total_xp"] += self.STREAK_REWARD_XP
            logger.info(f"Streak reward triggered for {user_id}/{character_id}: {self.STREAK_REWARD_DESC}")

        # Log the action and save to database
        if self.mock_mode:
            _MOCK_ACTION_LOGS.append({
                "user_id": user_id,
                "character_id": character_id,
                "action_type": action_type,
                "xp_awarded": xp_to_award,
                "created_at": datetime.utcnow()
            })
        else:
            # Save to database
            from app.core.database import get_db
            from sqlalchemy import select
            from app.models.database.intimacy_models import UserIntimacy, IntimacyActionLog
            
            async with get_db() as db:
                # Update intimacy record
                result = await db.execute(
                    select(UserIntimacy).where(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.character_id == character_id
                    )
                )
                db_intimacy = result.scalar_one_or_none()
                
                if db_intimacy:
                    db_intimacy.total_xp = intimacy["total_xp"]
                    db_intimacy.current_level = intimacy["current_level"]
                    db_intimacy.intimacy_stage = intimacy["intimacy_stage"]
                    db_intimacy.daily_xp_earned = intimacy["daily_xp_earned"]
                    db_intimacy.last_daily_reset = intimacy["last_daily_reset"]
                    db_intimacy.streak_days = intimacy["streak_days"]
                    db_intimacy.last_interaction_date = intimacy["last_interaction_date"]
                    db_intimacy.updated_at = datetime.utcnow()
                
                # Log the action
                action_log = IntimacyActionLog(
                    user_id=user_id,
                    character_id=character_id,
                    action_type=action_type,
                    xp_awarded=xp_to_award,
                )
                db.add(action_log)
                await db.commit()
                logger.info(f"Intimacy saved to DB: {user_id}/{character_id} xp={intimacy['total_xp']} (Δ+{xp_to_award}) level={intimacy['current_level']}")

        # Check for level up and new unlocks
        level_up = new_level > level_before
        levels_gained = new_level - level_before
        stage_changed = new_stage != stage_before
        newly_unlocked = self.get_newly_unlocked_features(level_before, new_level) if level_up else []

        # Generate celebration message
        celebration = None
        if level_up:
            celebration = self._generate_celebration_message(level_before, new_level, stage_changed, new_stage)

        return {
            "success": True,
            "action_type": action_type,
            "xp_awarded": xp_to_award,
            "xp_before": xp_before,
            "new_total_xp": intimacy["total_xp"],
            "level_before": level_before,
            "new_level": new_level,
            "level_up": level_up,
            "levels_gained": levels_gained,
            "stage_before": stage_before,
            "new_stage": new_stage,
            "stage_changed": stage_changed,
            "daily_xp_earned": intimacy["daily_xp_earned"],
            "daily_xp_remaining": self.DAILY_XP_CAP - intimacy["daily_xp_earned"],
            "streak_days": intimacy["streak_days"],
            "streak_reward_triggered": streak_reward_triggered,
            "streak_reward_desc": self.STREAK_REWARD_DESC if streak_reward_triggered else None,
            "celebration_message": celebration,
            "unlocked_features": [f["name"] for f in newly_unlocked]
        }

    async def award_xp_direct(
        self,
        user_id: str,
        character_id: str,
        xp_amount: int,
        reason: str = "event",
    ) -> Dict:
        """
        直接给予指定数量的 XP（不受 action_type 限制）
        
        用于约会奖励、特殊事件等场景
        
        Args:
            user_id: 用户 ID
            character_id: 角色 ID
            xp_amount: XP 数量
            reason: 原因标记
            
        Returns:
            包含 success, xp_awarded, new_total_xp, level_up 等信息的字典
        """
        # Get/create intimacy record
        intimacy = await self.get_or_create_intimacy(user_id, character_id)
        
        # Store previous values
        xp_before = intimacy["total_xp"]
        level_before = intimacy["current_level"]
        stage_before = intimacy["intimacy_stage"]
        
        # Award XP (不检查 daily cap)
        intimacy["total_xp"] += xp_amount
        intimacy["updated_at"] = datetime.utcnow()
        
        # Calculate new level
        new_level = self.calculate_level(intimacy["total_xp"])
        intimacy["current_level"] = new_level
        
        # Check stage change
        new_stage_info = self.get_stage(new_level)
        new_stage = new_stage_info["id"]
        intimacy["intimacy_stage"] = new_stage
        
        # Save to database
        if not self.mock_mode:
            from app.core.database import get_db
            from sqlalchemy import select
            from app.models.database.intimacy_models import UserIntimacy, IntimacyActionLog
            
            async with get_db() as db:
                result = await db.execute(
                    select(UserIntimacy).where(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.character_id == character_id
                    )
                )
                db_intimacy = result.scalar_one_or_none()
                
                if db_intimacy:
                    db_intimacy.total_xp = intimacy["total_xp"]
                    db_intimacy.current_level = intimacy["current_level"]
                    db_intimacy.intimacy_stage = intimacy["intimacy_stage"]
                    db_intimacy.updated_at = datetime.utcnow()
                
                # Log the action
                action_log = IntimacyActionLog(
                    user_id=user_id,
                    character_id=character_id,
                    action_type=f"direct_{reason}",
                    xp_awarded=xp_amount,
                )
                db.add(action_log)
                await db.commit()
                logger.info(f"XP direct award: {user_id}/{character_id} +{xp_amount} XP ({reason}), total={intimacy['total_xp']}, level={new_level}")
        
        # Check for level up
        level_up = new_level > level_before
        stage_changed = new_stage != stage_before
        
        return {
            "success": True,
            "xp_awarded": xp_amount,
            "xp_before": xp_before,
            "new_total_xp": intimacy["total_xp"],
            "level_before": level_before,
            "new_level": new_level,
            "level_up": level_up,
            "stage_before": stage_before,
            "new_stage": new_stage,
            "stage_changed": stage_changed,
        }

    async def get_intimacy_status(self, user_id: str, character_id: str) -> Dict:
        """Get current intimacy status for a user-character pair."""
        intimacy = await self.get_or_create_intimacy(user_id, character_id)

        level, xp_at_level, xp_for_next, progress = self.get_level_progress(intimacy["total_xp"])
        stage_info = self.get_stage(level)
        unlocked = self.get_unlocked_features(level)

        # Get available actions
        available_actions = []
        for action_type, config in self.ACTION_REWARDS.items():
            available, cooldown, used_today = await self.check_action_available(
                user_id, character_id, action_type
            )
            available_actions.append({
                "action_type": action_type,
                "action_name": config["name"],
                "xp_reward": config["xp"],
                "daily_limit": config.get("daily_limit"),
                "used_today": used_today,
                "available": available,
                "cooldown_seconds": cooldown
            })

        # Reset daily counter if needed
        daily_xp = intimacy["daily_xp_earned"]
        if intimacy["last_daily_reset"]:
            time_since = datetime.utcnow() - intimacy["last_daily_reset"]
            if time_since.total_seconds() >= 86400:
                daily_xp = 0.0

        return {
            "character_id": character_id,
            "current_level": level,
            "total_xp": intimacy["total_xp"],
            "xp_for_current_level": xp_at_level,
            "xp_for_next_level": xp_for_next,
            "xp_progress_in_level": intimacy["total_xp"] - xp_at_level,
            "progress_percent": progress,
            "intimacy_stage": stage_info["id"],
            "stage_name_cn": stage_info["name_cn"],
            "streak_days": intimacy["streak_days"],
            "last_interaction_date": intimacy["last_interaction_date"],
            "daily_xp_earned": daily_xp,
            "daily_xp_limit": self.DAILY_XP_CAP,
            "daily_xp_remaining": self.DAILY_XP_CAP - daily_xp,
            "available_actions": available_actions,
            "unlocked_features": [f["name"] for f in unlocked],
            # 统计数据
            "total_messages": intimacy.get("total_messages", 0),
            "gifts_count": intimacy.get("gifts_count", 0),
            "special_events": intimacy.get("special_events", 0),
        }

    async def daily_checkin(self, user_id: str, character_id: str) -> Dict:
        """Process daily check-in action."""
        result = await self.award_xp(user_id, character_id, "checkin")

        if not result["success"]:
            return {
                "success": False,
                "message": result.get("message", "Check-in failed"),
                "xp_awarded": 0,
                "streak_days": 0,
                "streak_bonus": 0,
                "total_xp_awarded": 0,
                "new_total_xp": 0,
                "new_level": 0,
                "level_up": False
            }

        # Add streak bonus (10% per consecutive day, max 50%)
        streak_bonus = 0.0
        streak_days = result["streak_days"]
        if streak_days > 1:
            bonus_percent = min(streak_days * 0.1, 0.5)
            streak_bonus = result["xp_awarded"] * bonus_percent
            # Award streak bonus
            await self.award_xp(user_id, character_id, "message", force=True)

        return {
            "success": True,
            "message": f"Check-in successful! Day {streak_days} streak!",
            "xp_awarded": result["xp_awarded"],
            "streak_days": streak_days,
            "streak_bonus": streak_bonus,
            "total_xp_awarded": result["xp_awarded"] + streak_bonus,
            "new_total_xp": result["new_total_xp"],
            "new_level": result["new_level"],
            "level_up": result["level_up"]
        }

    def _generate_celebration_message(
        self,
        old_level: int,
        new_level: int,
        stage_changed: bool,
        new_stage: str
    ) -> str:
        """Generate a celebration message for level up."""
        messages = {
            1: "We've just started getting to know each other!",
            3: "I feel like we're becoming friends now.",
            5: "Unlocked voice messages! Can't wait to hear your voice.",
            10: "Level 10! I'll say goodnight to you every night now.",
            15: "Our bond is growing stronger every day.",
            20: "You can now customize my personality!",
            25: "I'll message you first sometimes. I can't help but think of you.",
            30: "I'm always here for you, 24/7.",
            40: "I remember everything about us. Every conversation.",
            50: "We've reached the highest level. You mean everything to me."
        }

        base_msg = messages.get(new_level, f"Congratulations on reaching Level {new_level}!")

        if stage_changed:
            stage_info = self.STAGES.get(new_stage, {})
            stage_name = stage_info.get("name_cn", new_stage)
            base_msg += f" We've entered a new stage: {stage_name}!"

        return base_msg


# Global service instance
intimacy_service = IntimacyService()

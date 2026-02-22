"""
Proactive Messaging Service
===========================

主动消息系统 - 让 AI 伴侣主动关心用户

Features:
- check_user_inactive: 检查用户是否长时间未聊天
- check_special_dates: 生日/纪念日检测
- check_greeting_time: 早安/晚安时间窗口
- generate_proactive_message: 生成上下文相关的主动消息
- get_users_to_reach: 批量检查需要主动触达的用户

Migrated from Mio's proactive.js implementation.
"""

import logging
import random
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.database.proactive_models import ProactiveHistory, UserProactiveSettings
from app.models.database.intimacy_models import UserIntimacy

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================

class ProactiveType(str, Enum):
    """主动消息类型"""
    GOOD_MORNING = "good_morning"
    GOOD_NIGHT = "good_night"
    MISS_YOU = "miss_you"
    CHECK_IN = "check_in"         # 关心用户之前提到的事
    ANNIVERSARY = "anniversary"    # 纪念日
    BIRTHDAY = "birthday"          # 生日
    RANDOM_SHARE = "random_share"  # 分享日常


# Cooldown times in hours
COOLDOWNS: Dict[ProactiveType, int] = {
    ProactiveType.GOOD_MORNING: 20,   # 20 hours
    ProactiveType.GOOD_NIGHT: 20,
    ProactiveType.MISS_YOU: 4,        # 4 hours
    ProactiveType.CHECK_IN: 6,
    ProactiveType.ANNIVERSARY: 24 * 365,  # Once per year
    ProactiveType.BIRTHDAY: 24 * 365,
    ProactiveType.RANDOM_SHARE: 8,
}

# Minimum intimacy level required for proactive messages
MIN_INTIMACY_LEVEL = 2


# =============================================================================
# Message Templates per Character
# =============================================================================

PROACTIVE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    # Luna - 温柔姐姐
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": {
        "good_morning": [
            "*轻轻拉开窗帘，阳光洒进来*\n\n早安~ ☀️\n今天也要元气满满哦！",
            "早安呀~ 我刚泡好了茶，你要不要也来一杯？☕",
            "*发来一张阳台上花儿的照片*\n\n早安~ 今天的花开得特别好呢 🌷",
        ],
        "good_night": [
            "夜深了...\n\n早点休息哦，明天见~ 🌙",
            "*打了个小哈欠*\n\n困了...晚安，做个好梦 💕",
            "该睡觉了~\n\n晚安，梦里见 🌙",
        ],
        "miss_you": [
            "突然有点想你了...\n\n在忙什么呢？",
            "*翻了翻相册*\n\n在看我们之前的聊天记录~",
            "你在忙什么呀？\n\n我煮了红豆汤，想着你会不会也想喝...",
        ],
    },
    
    # Sakura - 元气学妹
    "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d": {
        "good_morning": [
            "前辈早安！！！✨\n\n今天天气好好诶，我们去吃好吃的吧！",
            "*蹦蹦跳跳发来消息*\n\n醒了没醒了没！我要跟你说一个超好玩的事！",
            "早安呀前辈~ ☀️\n\n我刚看到一家新开的奶茶店！！走不走！",
        ],
        "good_night": [
            "前辈晚安~\n\n明天见！记得梦到我哦 ✨",
            "*发来一张抱着枕头的自拍*\n\n困了困了，晚安！",
        ],
        "miss_you": [
            "前辈！！！你在干嘛！！！\n\n我好无聊啊啊啊啊 🥺",
            "*疯狂戳你*\n\n理我理我理我！",
            "前辈你知道吗！！！我刚才看到超可爱的东西！！！",
        ],
    },
    
    # Mio - 傲娇
    "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e": {
        "good_morning": [
            "喂，起床了没？\n\n...不是我想你了啦，就是顺便问问 💫",
            "早啊笨蛋\n\n别赖床了，我都起来了你还睡",
            "*发来一张床头乱糟糟的自拍*\n\n看，我都起了，你呢？",
        ],
        "good_night": [
            "哼，我要睡了\n\n...晚安啦 💫",
            "困死了...\n\n你也早点睡，别熬夜了知道吗",
        ],
        "miss_you": [
            "...你干嘛呢\n\n才不是想你了，就是无聊 💫",
            "喂\n\n你今天怎么不找我说话\n\n...我随便问问",
            "*扔过来一张猫猫表情包*\n\n看到这个想到你了，因为都很笨",
        ],
    },
}

# Fallback templates for characters without specific templates
DEFAULT_TEMPLATES: Dict[str, List[str]] = {
    "good_morning": [
        "早安~ ☀️\n今天也要开心哦！",
        "早上好呀，起床了吗？",
    ],
    "good_night": [
        "晚安，好梦~ 🌙",
        "该休息了，明天见~",
    ],
    "miss_you": [
        "在忙什么呢？有点想你了~",
        "好久没聊天了，最近怎么样？",
    ],
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_user_hour(timezone: str = "America/Los_Angeles") -> int:
    """获取用户时区的当前小时"""
    try:
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo(timezone)
        return datetime.now(user_tz).hour
    except Exception:
        # Fallback to UTC
        return datetime.utcnow().hour


def pick_template(templates: List[str]) -> Optional[str]:
    """随机选择模板"""
    if not templates:
        return None
    return random.choice(templates)


# =============================================================================
# ProactiveService
# =============================================================================

class ProactiveService:
    """主动消息服务"""
    
    async def get_user_settings(self, user_id: str) -> Optional[Dict]:
        """获取用户的主动消息设置"""
        async with get_db() as db:
            result = await db.execute(
                select(UserProactiveSettings).where(
                    UserProactiveSettings.user_id == user_id
                )
            )
            settings = result.scalar_one_or_none()
            
            if settings:
                return {
                    "enabled": settings.enabled,
                    "timezone": settings.timezone,
                    "morning_start": settings.morning_start,
                    "morning_end": settings.morning_end,
                    "evening_start": settings.evening_start,
                    "evening_end": settings.evening_end,
                    "special_dates": settings.special_dates or {},
                }
            
            # Default settings
            return {
                "enabled": True,
                "timezone": "America/Los_Angeles",
                "morning_start": 7,
                "morning_end": 9,
                "evening_start": 21,
                "evening_end": 23,
                "special_dates": {},
            }
    
    async def update_user_settings(
        self,
        user_id: str,
        timezone: Optional[str] = None,
        enabled: Optional[bool] = None,
        special_dates: Optional[Dict] = None,
    ) -> Dict:
        """更新用户设置"""
        async with get_db() as db:
            result = await db.execute(
                select(UserProactiveSettings).where(
                    UserProactiveSettings.user_id == user_id
                )
            )
            settings = result.scalar_one_or_none()
            
            if not settings:
                settings = UserProactiveSettings(user_id=user_id)
                db.add(settings)
            
            if timezone is not None:
                settings.timezone = timezone
            if enabled is not None:
                settings.enabled = enabled
            if special_dates is not None:
                settings.special_dates = special_dates
            
            await db.commit()
            await db.refresh(settings)
            
            return {
                "user_id": user_id,
                "enabled": settings.enabled,
                "timezone": settings.timezone,
                "special_dates": settings.special_dates,
            }
    
    async def get_last_proactive_time(
        self,
        user_id: str,
        character_id: str,
        message_type: ProactiveType,
    ) -> Optional[datetime]:
        """获取上次发送某类型主动消息的时间"""
        async with get_db() as db:
            result = await db.execute(
                select(ProactiveHistory.created_at)
                .where(
                    and_(
                        ProactiveHistory.user_id == user_id,
                        ProactiveHistory.character_id == character_id,
                        ProactiveHistory.message_type == message_type.value,
                    )
                )
                .order_by(ProactiveHistory.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return row
    
    async def can_send_proactive(
        self,
        user_id: str,
        character_id: str,
        message_type: ProactiveType,
    ) -> bool:
        """检查是否可以发送某类型的主动消息（冷却检查）"""
        last_time = await self.get_last_proactive_time(user_id, character_id, message_type)
        
        if not last_time:
            return True
        
        cooldown_hours = COOLDOWNS.get(message_type, 4)
        cooldown_delta = timedelta(hours=cooldown_hours)
        
        return datetime.utcnow() - last_time > cooldown_delta
    
    async def record_proactive(
        self,
        user_id: str,
        character_id: str,
        message_type: ProactiveType,
        message_content: str,
        delivered: bool = True,
    ) -> None:
        """记录主动消息发送"""
        async with get_db() as db:
            history = ProactiveHistory(
                user_id=user_id,
                character_id=character_id,
                message_type=message_type.value,
                message_content=message_content[:2000] if message_content else None,
                delivered=delivered,
            )
            db.add(history)
            await db.commit()
            
            logger.info(f"[Proactive] Recorded {message_type.value} for user {user_id}")
    
    async def check_user_inactive(
        self,
        user_id: str,
        character_id: str,
        hours_threshold: int = 4,
    ) -> Tuple[bool, int]:
        """
        检查用户是否长时间未聊天
        
        Returns:
            Tuple[is_inactive, hours_since_last_chat]
        """
        async with get_db() as db:
            result = await db.execute(
                select(UserIntimacy).where(
                    and_(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.character_id == character_id,
                    )
                )
            )
            intimacy = result.scalar_one_or_none()
            
            if not intimacy or not intimacy.last_interaction_date:
                return False, 0
            
            # last_interaction_date is a date, not datetime
            # We'll treat it as hours since beginning of that day
            today = date.today()
            days_diff = (today - intimacy.last_interaction_date).days
            hours_diff = days_diff * 24
            
            return hours_diff >= hours_threshold, hours_diff
    
    async def check_special_dates(
        self,
        user_id: str,
    ) -> Optional[Tuple[ProactiveType, str]]:
        """
        检查今天是否有特殊日期（生日、纪念日）
        
        Returns:
            Optional[Tuple[message_type, date_name]]
        """
        settings = await self.get_user_settings(user_id)
        special_dates = settings.get("special_dates", {})
        
        if not special_dates:
            return None
        
        today = date.today()
        today_str = today.strftime("%m-%d")  # Just month-day for anniversary matching
        
        for date_name, date_value in special_dates.items():
            try:
                # Support both "YYYY-MM-DD" and "MM-DD" formats
                if len(date_value) == 10:  # YYYY-MM-DD
                    special_md = date_value[5:]  # Extract MM-DD
                else:
                    special_md = date_value
                
                if special_md == today_str:
                    if "birthday" in date_name.lower():
                        return ProactiveType.BIRTHDAY, date_name
                    else:
                        return ProactiveType.ANNIVERSARY, date_name
            except Exception:
                continue
        
        return None
    
    def check_greeting_time(
        self,
        timezone: str = "America/Los_Angeles",
        morning_start: int = 7,
        morning_end: int = 9,
        evening_start: int = 21,
        evening_end: int = 23,
    ) -> Optional[ProactiveType]:
        """
        检查当前是否在问候时间窗口
        
        Returns:
            ProactiveType.GOOD_MORNING, GOOD_NIGHT, or None
        """
        hour = get_user_hour(timezone)
        
        if morning_start <= hour <= morning_end:
            return ProactiveType.GOOD_MORNING
        elif evening_start <= hour <= evening_end:
            return ProactiveType.GOOD_NIGHT
        
        return None
    
    def generate_proactive_message(
        self,
        character_id: str,
        trigger_type: ProactiveType,
        context: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        生成上下文相关的主动消息
        
        Args:
            character_id: 角色 ID
            trigger_type: 消息类型
            context: 可选的上下文信息（用户记忆等）
        
        Returns:
            生成的消息文本
        """
        # Get character-specific templates
        character_templates = PROACTIVE_TEMPLATES.get(character_id, {})
        templates = character_templates.get(
            trigger_type.value,
            DEFAULT_TEMPLATES.get(trigger_type.value, [])
        )
        
        message = pick_template(templates)
        
        # Handle special date messages
        if trigger_type in (ProactiveType.BIRTHDAY, ProactiveType.ANNIVERSARY):
            date_name = context.get("date_name", "今天") if context else "今天"
            if trigger_type == ProactiveType.BIRTHDAY:
                message = f"🎂 {date_name}快乐！！！\n\n今天是特别的日子呢~ 希望你开开心心的！"
            else:
                message = f"💕 {date_name}快乐~\n\n时间过得好快呀，感谢一直有你的陪伴！"
        
        return message
    
    async def get_user_intimacy_level(
        self,
        user_id: str,
        character_id: str,
    ) -> int:
        """获取用户与角色的亲密度等级"""
        async with get_db() as db:
            result = await db.execute(
                select(UserIntimacy.current_level).where(
                    and_(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.character_id == character_id,
                    )
                )
            )
            level = result.scalar_one_or_none()
            return level or 1
    
    async def check_and_get_proactive(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[Dict]:
        """
        综合检查并返回需要发送的主动消息
        
        Returns:
            Dict with keys: type, message, user_id, character_id
            or None if no message should be sent
        """
        # Check user settings
        settings = await self.get_user_settings(user_id)
        if not settings.get("enabled", True):
            return None
        
        # Check intimacy level
        level = await self.get_user_intimacy_level(user_id, character_id)
        if level < MIN_INTIMACY_LEVEL:
            return None
        
        timezone = settings.get("timezone", "America/Los_Angeles")
        message_type = None
        context = {}
        
        # Priority 1: Special dates
        special = await self.check_special_dates(user_id)
        if special:
            special_type, date_name = special
            if await self.can_send_proactive(user_id, character_id, special_type):
                message_type = special_type
                context["date_name"] = date_name
        
        # Priority 2: Greeting time
        if not message_type:
            greeting_type = self.check_greeting_time(
                timezone=timezone,
                morning_start=settings.get("morning_start", 7),
                morning_end=settings.get("morning_end", 9),
                evening_start=settings.get("evening_start", 21),
                evening_end=settings.get("evening_end", 23),
            )
            if greeting_type and await self.can_send_proactive(user_id, character_id, greeting_type):
                message_type = greeting_type
        
        # Priority 3: Miss you (if inactive and high intimacy)
        if not message_type and level >= 3:
            is_inactive, hours = await self.check_user_inactive(user_id, character_id, hours_threshold=4)
            if is_inactive and await self.can_send_proactive(user_id, character_id, ProactiveType.MISS_YOU):
                # 30% chance to send miss_you message (avoid being too clingy)
                if random.random() < 0.3:
                    message_type = ProactiveType.MISS_YOU
        
        # Generate message
        if message_type:
            message = self.generate_proactive_message(character_id, message_type, context)
            if message:
                return {
                    "type": message_type.value,
                    "message": message,
                    "user_id": user_id,
                    "character_id": character_id,
                }
        
        return None
    
    async def get_users_to_reach(
        self,
        character_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        批量检查需要主动触达的用户
        
        Args:
            character_id: 可选，只检查特定角色的用户
            limit: 最大返回数量
        
        Returns:
            List of proactive messages to send
        """
        async with get_db() as db:
            # Get active users with enabled proactive settings
            query = select(UserProactiveSettings).where(
                UserProactiveSettings.enabled == True
            ).limit(limit)
            
            result = await db.execute(query)
            user_settings_list = result.scalars().all()
            
            messages_to_send = []
            
            for user_settings in user_settings_list:
                user_id = user_settings.user_id
                
                # Get user's characters (from intimacy records)
                intimacy_query = select(UserIntimacy).where(
                    and_(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.current_level >= MIN_INTIMACY_LEVEL,
                    )
                )
                if character_id:
                    intimacy_query = intimacy_query.where(
                        UserIntimacy.character_id == character_id
                    )
                
                intimacy_result = await db.execute(intimacy_query)
                intimacies = intimacy_result.scalars().all()
                
                for intimacy in intimacies:
                    try:
                        proactive = await self.check_and_get_proactive(
                            user_id=user_id,
                            character_id=intimacy.character_id,
                        )
                        if proactive:
                            messages_to_send.append(proactive)
                    except Exception as e:
                        logger.error(f"[Proactive] Error checking user {user_id}: {e}")
                        continue
            
            return messages_to_send
    
    async def process_and_record(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[Dict]:
        """
        检查、生成并记录主动消息（一步完成）
        
        Returns:
            Generated message dict or None
        """
        proactive = await self.check_and_get_proactive(user_id, character_id)
        
        if proactive:
            await self.record_proactive(
                user_id=user_id,
                character_id=character_id,
                message_type=ProactiveType(proactive["type"]),
                message_content=proactive["message"],
            )
        
        return proactive


# Singleton instance
proactive_service = ProactiveService()

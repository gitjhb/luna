"""
主动消息系统 (Proactive Message System)
======================================

让 AI 伴侣主动关心用户，而不是只被动回复。
移植自 Mio 项目，适配 Luna 后端。

功能：
- 早安/晚安消息（按用户时区）
- 想念消息（超过N小时没聊天）
- 角色专属模板
- 冷却机制（防止刷屏）
- 亲密度门槛
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ProactiveType(str, Enum):
    GOOD_MORNING = "good_morning"
    GOOD_NIGHT = "good_night"
    MISS_YOU = "miss_you"
    CHECK_IN = "check_in"        # 关心用户之前提到的事
    ANNIVERSARY = "anniversary"   # 纪念日
    RANDOM_SHARE = "random_share" # 分享日常


# 冷却时间（秒）
COOLDOWNS = {
    ProactiveType.GOOD_MORNING: 20 * 60 * 60,   # 20小时
    ProactiveType.GOOD_NIGHT: 20 * 60 * 60,
    ProactiveType.MISS_YOU: 4 * 60 * 60,        # 4小时
    ProactiveType.CHECK_IN: 6 * 60 * 60,
    ProactiveType.RANDOM_SHARE: 8 * 60 * 60,
}

# 角色专属模板
PROACTIVE_TEMPLATES = {
    "luna": {
        "good_morning": [
            "*轻轻推开窗帘，阳光洒进来*\n\n早安~ 🌙\n今天也要好好照顾自己哦",
            "早安呀~ ☀️\n\n昨晚睡得好吗？我梦到你了呢...",
            "*发来一张窗边的照片*\n\n早安~ 今天的阳光很温柔，就像你一样 🌸",
        ],
        "good_night": [
            "夜深了...\n\n早点休息哦，我会在梦里等你~ 🌙",
            "*打了个小哈欠*\n\n困了...晚安，做个好梦 💕",
            "今天辛苦了~\n\n晚安，明天见 🌙",
        ],
        "miss_you": [
            "在吗...\n\n突然有点想你了 🥺",
            "*翻了翻我们的聊天记录*\n\n嘿嘿，在回味呢~",
            "你在忙什么呀？\n\n我有点想找你聊天...",
        ],
    },
    "sakura": {
        "good_morning": [
            "*轻轻推开窗户，阳光洒进来*\n\n早安呀，前辈~ 🌸\n今天也要元气满满哦！",
            "前辈早安~ ☀️\n\n我刚泡好了茶，你要不要也来一杯？",
            "*发来一张阳台上花儿的照片*\n\n早安~ 今天的花开得特别好呢 🌷",
        ],
        "good_night": [
            "前辈，夜深了...\n\n早点休息哦，明天见~ 🌙",
            "*打了个小哈欠*\n\n困了...晚安，做个好梦 💕",
        ],
        "miss_you": [
            "前辈...\n\n突然有点想你了 🥺",
            "*翻了翻相册*\n\n诶嘿，在看我们之前的聊天记录~",
            "你在忙什么呀？\n\n我煮了红豆汤，想着你会不会也想喝...",
        ],
    },
    "nova": {
        "good_morning": [
            "早安！！！✨\n\n今天好天气诶，我们去吃好吃的吧！",
            "*狂敲你的对话框*\n\n醒了没醒了没！我要跟你说一个超好玩的事！",
            "早安呀~ ☀️\n\n我刚看到一家新开的奶茶店！！走不走！",
        ],
        "good_night": [
            "晚安~\n\n明天见！记得梦到我哦 ✨",
            "*发来一张抱着枕头的自拍*\n\n困了困了，晚安！",
        ],
        "miss_you": [
            "你在干嘛！！！\n\n我好无聊啊啊啊啊 🥺",
            "*疯狂@你*\n\n理我理我理我！",
            "你知道吗！！！我刚才看到超可爱的东西！！！",
        ],
    },
    # 默认模板（用于未定义的角色）
    "default": {
        "good_morning": [
            "早安~ ☀️\n\n新的一天开始了，加油哦！",
            "早上好呀~\n\n今天有什么计划吗？",
        ],
        "good_night": [
            "晚安~\n\n好好休息，明天见 🌙",
            "夜深了，早点睡哦~\n\n晚安 💫",
        ],
        "miss_you": [
            "在吗？\n\n有点想找你聊天~",
            "好久没聊了...\n\n你最近怎么样？",
        ],
    },
}


class ProactiveMessageService:
    """主动消息服务"""
    
    def __init__(self, db_service=None):
        self.db = db_service
        # 内存缓存（生产环境应该用 Redis）
        self._last_proactive: Dict[str, Dict[str, float]] = {}
    
    def _cache_key(self, user_id: str, character_id: str) -> str:
        return f"{user_id}:{character_id}"
    
    async def get_last_proactive_time(
        self, user_id: str, character_id: str, msg_type: ProactiveType
    ) -> float:
        """获取上次发送某类型主动消息的时间戳"""
        key = self._cache_key(user_id, character_id)
        user_data = self._last_proactive.get(key, {})
        return user_data.get(msg_type.value, 0)
    
    async def record_proactive(
        self, user_id: str, character_id: str, msg_type: ProactiveType
    ) -> None:
        """记录主动消息发送时间"""
        key = self._cache_key(user_id, character_id)
        if key not in self._last_proactive:
            self._last_proactive[key] = {}
        self._last_proactive[key][msg_type.value] = datetime.now().timestamp()
    
    async def can_send_proactive(
        self, user_id: str, character_id: str, msg_type: ProactiveType
    ) -> bool:
        """检查是否可以发送某类型的主动消息（冷却检查）"""
        last_time = await self.get_last_proactive_time(user_id, character_id, msg_type)
        cooldown = COOLDOWNS.get(msg_type, 4 * 60 * 60)
        return datetime.now().timestamp() - last_time > cooldown
    
    def get_user_hour(self, timezone: str = "America/Los_Angeles") -> int:
        """获取用户时区的当前小时"""
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone)
            return datetime.now(tz).hour
        except Exception:
            return datetime.now().hour
    
    def pick_template(self, character_id: str, msg_type: ProactiveType) -> Optional[str]:
        """选择随机模板"""
        templates = PROACTIVE_TEMPLATES.get(character_id, {}).get(msg_type.value)
        if not templates:
            templates = PROACTIVE_TEMPLATES.get("default", {}).get(msg_type.value)
        if not templates:
            return None
        return random.choice(templates)
    
    async def check_and_generate(
        self,
        user_id: str,
        character_id: str,
        intimacy_level: int = 1,
        last_chat_time: Optional[datetime] = None,
        timezone: str = "America/Los_Angeles",
        muted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        检查是否应该发送主动消息，如果应该则生成消息
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            intimacy_level: 亲密度等级 (1-100)
            last_chat_time: 上次聊天时间
            timezone: 用户时区
            muted: 用户是否静音
        
        Returns:
            如果应该发送，返回 {"type": ProactiveType, "message": str}
            否则返回 None
        """
        # 静音用户不发消息
        if muted:
            return None
        
        # 亲密度低于2级不发主动消息
        if intimacy_level < 2:
            logger.debug(f"Intimacy level {intimacy_level} < 2, skip proactive")
            return None
        
        hour = self.get_user_hour(timezone)
        
        # 计算距离上次聊天多久了
        hours_since_chat = 999
        if last_chat_time:
            delta = datetime.now() - last_chat_time
            hours_since_chat = delta.total_seconds() / 3600
        
        msg_type = None
        
        # 早安消息 (7-9点)
        if 7 <= hour <= 9:
            if await self.can_send_proactive(user_id, character_id, ProactiveType.GOOD_MORNING):
                msg_type = ProactiveType.GOOD_MORNING
        
        # 晚安消息 (22-23点)
        elif 22 <= hour <= 23:
            if await self.can_send_proactive(user_id, character_id, ProactiveType.GOOD_NIGHT):
                msg_type = ProactiveType.GOOD_NIGHT
        
        # 想念消息（超过4小时没聊天，亲密度3级以上）
        elif hours_since_chat > 4 and intimacy_level >= 3:
            if await self.can_send_proactive(user_id, character_id, ProactiveType.MISS_YOU):
                # 30% 概率发想念消息
                if random.random() < 0.3:
                    msg_type = ProactiveType.MISS_YOU
        
        if msg_type:
            message = self.pick_template(character_id, msg_type)
            if message:
                await self.record_proactive(user_id, character_id, msg_type)
                logger.info(f"Generated proactive message: {msg_type.value} for user={user_id}")
                return {
                    "type": msg_type.value,
                    "message": message,
                    "user_id": user_id,
                    "character_id": character_id,
                }
        
        return None
    
    async def process_all_users(
        self, users: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量处理所有用户的主动消息
        
        Args:
            users: 用户列表，每个用户包含 user_id, character_id, intimacy_level, last_chat_time, timezone, muted
        
        Returns:
            需要发送的消息列表
        """
        results = []
        
        for user in users:
            try:
                result = await self.check_and_generate(
                    user_id=user["user_id"],
                    character_id=user.get("character_id", "luna"),
                    intimacy_level=user.get("intimacy_level", 1),
                    last_chat_time=user.get("last_chat_time"),
                    timezone=user.get("timezone", "America/Los_Angeles"),
                    muted=user.get("muted", False),
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error processing proactive for user {user.get('user_id')}: {e}")
        
        return results


# 单例服务
proactive_service = ProactiveMessageService()


# ============================================================
# API Helpers
# ============================================================

async def check_proactive_for_user(
    user_id: str,
    character_id: str = "luna",
    intimacy_level: int = 1,
    last_chat_time: Optional[datetime] = None,
    timezone: str = "America/Los_Angeles",
) -> Optional[Dict[str, Any]]:
    """便捷函数：检查单个用户的主动消息"""
    return await proactive_service.check_and_generate(
        user_id=user_id,
        character_id=character_id,
        intimacy_level=intimacy_level,
        last_chat_time=last_chat_time,
        timezone=timezone,
    )

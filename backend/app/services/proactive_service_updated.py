"""
Enhanced Proactive Messaging Service
===================================

主动消息系统增强版 - 基于现有系统优化
- 更新了Luna和Vera的消息模板，符合任务要求
- 简化了配置结构
- 优化了Redis缓存机制
- 增强了错误处理

Features:
- 消息类型：good_morning, good_night, miss_you, check_in
- 角色模板：Luna (温柔治愈系) 和 Vera (高冷御姐) 的专属消息风格
- 冷却机制：Redis 记录上次发送时间
- 亲密度门槛：Lv.2+ 才触发
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

try:
    from app.core.redis_client import get_redis_client
    from app.core.database import get_db
    from sqlalchemy import select, and_
    from app.models.database.proactive_models import ProactiveHistory, UserProactiveSettings
    from app.models.database.intimacy_models import UserIntimacy
    DEPS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some dependencies not available: {e}")
    DEPS_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# 配置
# =============================================================================

class ProactiveType(str, Enum):
    """主动消息类型"""
    GOOD_MORNING = "good_morning"
    GOOD_NIGHT = "good_night"
    MISS_YOU = "miss_you"
    CHECK_IN = "check_in"         # 关心用户之前提到的事


# 冷却时间（小时）
COOLDOWNS: Dict[ProactiveType, int] = {
    ProactiveType.GOOD_MORNING: 20,   # 20小时
    ProactiveType.GOOD_NIGHT: 20,     # 20小时  
    ProactiveType.MISS_YOU: 4,        # 4小时
    ProactiveType.CHECK_IN: 6,        # 6小时
}

# 最小亲密度等级
MIN_INTIMACY_LEVEL = 2


# =============================================================================
# 角色消息模板 - 按任务要求优化
# =============================================================================

CHARACTER_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    
    # Luna - 温柔治愈系
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": {  # Luna的UUID
        "good_morning": [
            "早安呀~ 今天也要加油哦 ☀️",
            "*轻轻拉开窗帘* 早安，愿你今天被温柔以待~",
            "早上好呢~ 昨晚休息得好吗？",
            "*微笑着给你递上一杯温水* 早安，记得好好照顾自己~",
        ],
        "good_night": [
            "夜深了，早点休息吧...晚安 🌙",
            "*轻抚着你的头发* 今天辛苦了，好好睡一觉吧~",
            "晚安，愿你有个甜美的梦境~ 💫",
            "*关掉台灯，给你盖好被子* 晚安，我会在梦里陪着你的~",
        ],
        "miss_you": [
            "在想你呢...你在忙什么呀？",
            "*托着腮帮子* 好像有点想你了...现在方便聊天吗？",
            "*看着窗外* 突然想起你了，在做什么呢？",
            "有点想找你说说话...你现在忙吗？",
        ],
        "check_in": [
            "今天过得怎么样呀？有什么想分享的吗？",
            "*关切地看着你* 最近感觉你好像有些累，还好吗？",
            "想听听你今天的故事~",
            "*温柔地握住你的手* 有什么烦恼都可以跟我说哦~",
        ],
    },
    
    # Vera - 高冷御姐
    "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e": {  # Vera的UUID
        "good_morning": [
            "...早。记得吃早餐。",
            "*慵懒地坐起身* 起这么早？还挺有精神。",
            "早安。昨晚的酒还没醒透。",
            "*瞥了一眼* ...早。今天有什么计划？",
        ],
        "good_night": [
            "该睡了。晚安。",
            "*放下手中的酒杯* 深夜了...去睡吧。",
            "晚安。别熬太晚。",
            "*关掉酒吧的灯* ...晚安。",
        ],
        "miss_you": [
            "...没什么，就是有点无聊。",
            "*点燃一支烟* 店里太安静了...你在干什么？",
            "...你今天没来？还以为你会过来。",
            "*靠在吧台上* 想找个人喝酒，你有时间吗？",
        ],
        "check_in": [
            "最近怎么样？",
            "*若有所思地看着你* 看起来心情不错？",
            "有什么新鲜事吗？",
            "*倒了一杯酒* 来聊聊？",
        ],
    },
    
    # 默认模板（其他角色）
    "default": {
        "good_morning": [
            "早安~ 新的一天开始了！☀️",
            "早上好呀~ 今天要加油哦！",
        ],
        "good_night": [
            "晚安，好梦~ 🌙", 
            "该休息了，明天见~",
        ],
        "miss_you": [
            "在想你呢~",
            "有点想找你聊天~",
        ],
        "check_in": [
            "最近过得怎么样？",
            "今天过得好吗？",
        ],
    },
}


# =============================================================================
# 增强版主动消息服务
# =============================================================================

class EnhancedProactiveService:
    """增强版主动消息服务"""
    
    def __init__(self):
        self.redis_prefix = "luna_proactive"
        
    async def _get_redis_key(self, user_id: str, character_id: str, msg_type: ProactiveType) -> str:
        """生成Redis键"""
        return f"{self.redis_prefix}:{user_id}:{character_id}:{msg_type.value}"
    
    async def get_last_proactive_time(
        self, 
        user_id: str, 
        character_id: str, 
        msg_type: ProactiveType
    ) -> Optional[datetime]:
        """从Redis获取上次发送时间"""
        try:
            redis = await get_redis_client()
            key = await self._get_redis_key(user_id, character_id, msg_type)
            timestamp = await redis.get(key)
            
            if timestamp:
                return datetime.fromisoformat(timestamp)
                
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            
        # Redis失败时回退到数据库
        return await self._get_last_proactive_from_db(user_id, character_id, msg_type)
    
    async def _get_last_proactive_from_db(
        self,
        user_id: str,
        character_id: str, 
        msg_type: ProactiveType
    ) -> Optional[datetime]:
        """从数据库获取上次发送时间"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(ProactiveHistory.created_at)
                    .where(
                        and_(
                            ProactiveHistory.user_id == user_id,
                            ProactiveHistory.character_id == character_id,
                            ProactiveHistory.message_type == msg_type.value,
                        )
                    )
                    .order_by(ProactiveHistory.created_at.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"DB query failed: {e}")
            return None
    
    async def record_proactive(
        self,
        user_id: str,
        character_id: str,
        msg_type: ProactiveType,
        message_content: str
    ) -> bool:
        """记录主动消息发送（Redis + 数据库）"""
        now = datetime.utcnow()
        success = True
        
        # 记录到Redis（带过期时间）
        try:
            redis = await get_redis_client()
            key = await self._get_redis_key(user_id, character_id, msg_type)
            cooldown_seconds = COOLDOWNS.get(msg_type, 4) * 3600
            
            await redis.setex(key, cooldown_seconds, now.isoformat())
            logger.debug(f"Recorded to Redis: {key}")
            
        except Exception as e:
            logger.warning(f"Redis record failed: {e}")
            success = False
        
        # 记录到数据库（持久化）
        try:
            async with get_db() as db:
                history = ProactiveHistory(
                    user_id=user_id,
                    character_id=character_id,
                    message_type=msg_type.value,
                    message_content=message_content[:2000] if message_content else None,
                    delivered=True,
                )
                db.add(history)
                await db.commit()
                
                logger.info(f"Recorded proactive: {msg_type.value} for {user_id}")
                
        except Exception as e:
            logger.error(f"DB record failed: {e}")
            success = False
        
        return success
    
    async def can_send_proactive(
        self,
        user_id: str,
        character_id: str,
        msg_type: ProactiveType
    ) -> bool:
        """检查是否可以发送某类型消息（冷却检查）"""
        last_time = await self.get_last_proactive_time(user_id, character_id, msg_type)
        
        if not last_time:
            return True
        
        cooldown_hours = COOLDOWNS.get(msg_type, 4)
        cooldown_delta = timedelta(hours=cooldown_hours)
        
        return datetime.utcnow() - last_time > cooldown_delta
    
    def get_user_timezone_hour(self, timezone: str = "America/Los_Angeles") -> int:
        """获取用户时区的当前小时"""
        try:
            from zoneinfo import ZoneInfo
            user_tz = ZoneInfo(timezone)
            return datetime.now(user_tz).hour
        except Exception:
            return datetime.utcnow().hour
    
    def pick_message_template(
        self, 
        character_id: str, 
        msg_type: ProactiveType
    ) -> Optional[str]:
        """随机选择消息模板"""
        # 优先使用角色专属模板
        templates = CHARACTER_TEMPLATES.get(character_id, {}).get(msg_type.value)
        
        # 回退到默认模板
        if not templates:
            templates = CHARACTER_TEMPLATES.get("default", {}).get(msg_type.value, [])
        
        if not templates:
            return None
            
        return random.choice(templates)
    
    async def get_user_intimacy_level(
        self,
        user_id: str,
        character_id: str
    ) -> int:
        """获取用户与角色的亲密度等级"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(UserIntimacy.current_level)
                    .where(
                        and_(
                            UserIntimacy.user_id == user_id,
                            UserIntimacy.character_id == character_id,
                        )
                    )
                )
                level = result.scalar_one_or_none()
                return level or 1
        except Exception as e:
            logger.error(f"Failed to get intimacy level: {e}")
            return 1
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """获取用户主动消息设置"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(UserProactiveSettings)
                    .where(UserProactiveSettings.user_id == user_id)
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
                    }
        except Exception as e:
            logger.error(f"Failed to get user settings: {e}")
        
        # 默认设置
        return {
            "enabled": True,
            "timezone": "America/Los_Angeles",
            "morning_start": 7,
            "morning_end": 9,
            "evening_start": 21,
            "evening_end": 23,
        }
    
    def determine_message_type(
        self, 
        timezone: str = "America/Los_Angeles",
        morning_start: int = 7,
        morning_end: int = 9,
        evening_start: int = 21,
        evening_end: int = 23,
    ) -> Optional[ProactiveType]:
        """根据时间确定消息类型"""
        hour = self.get_user_timezone_hour(timezone)
        
        if morning_start <= hour <= morning_end:
            return ProactiveType.GOOD_MORNING
        elif evening_start <= hour <= evening_end:
            return ProactiveType.GOOD_NIGHT
            
        return None
    
    async def check_user_inactive(
        self,
        user_id: str,
        character_id: str,
        hours_threshold: int = 4
    ) -> bool:
        """检查用户是否长时间未活跃"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(UserIntimacy.last_interaction_date)
                    .where(
                        and_(
                            UserIntimacy.user_id == user_id,
                            UserIntimacy.character_id == character_id,
                        )
                    )
                )
                last_date = result.scalar_one_or_none()
                
                if not last_date:
                    return False
                
                # 简化处理：如果今天没有互动就算inactive
                from datetime import date
                today = date.today()
                days_diff = (today - last_date).days
                
                return days_diff > 0  # 不是今天就算inactive
                
        except Exception as e:
            logger.error(f"Failed to check user activity: {e}")
            return False
    
    async def check_and_generate_proactive(
        self,
        user_id: str,
        character_id: str
    ) -> Optional[Dict[str, Any]]:
        """检查并生成主动消息"""
        # 1. 检查用户设置
        settings = await self.get_user_settings(user_id)
        if not settings.get("enabled", True):
            logger.debug(f"Proactive disabled for user {user_id}")
            return None
        
        # 2. 检查亲密度
        intimacy_level = await self.get_user_intimacy_level(user_id, character_id)
        if intimacy_level < MIN_INTIMACY_LEVEL:
            logger.debug(f"Intimacy level {intimacy_level} < {MIN_INTIMACY_LEVEL}")
            return None
        
        timezone = settings.get("timezone", "America/Los_Angeles")
        msg_type = None
        
        # 3. 优先级检查
        
        # Priority 1: 时间问候（早安/晚安）
        greeting_type = self.determine_message_type(
            timezone=timezone,
            morning_start=settings.get("morning_start", 7),
            morning_end=settings.get("morning_end", 9),
            evening_start=settings.get("evening_start", 21),
            evening_end=settings.get("evening_end", 23),
        )
        
        if greeting_type and await self.can_send_proactive(user_id, character_id, greeting_type):
            msg_type = greeting_type
        
        # Priority 2: 想念消息（高亲密度 + 长时间无互动）
        if not msg_type and intimacy_level >= 3:
            is_inactive = await self.check_user_inactive(user_id, character_id, 4)
            if is_inactive and await self.can_send_proactive(user_id, character_id, ProactiveType.MISS_YOU):
                # 30%概率发送，避免太频繁
                if random.random() < 0.3:
                    msg_type = ProactiveType.MISS_YOU
        
        # 4. 生成消息
        if msg_type:
            message = self.pick_message_template(character_id, msg_type)
            if message:
                return {
                    "type": msg_type.value,
                    "message": message,
                    "user_id": user_id,
                    "character_id": character_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        
        return None
    
    async def process_user_proactive(
        self,
        user_id: str,
        character_id: str
    ) -> Optional[Dict[str, Any]]:
        """完整流程：检查、生成、记录主动消息"""
        proactive = await self.check_and_generate_proactive(user_id, character_id)
        
        if proactive:
            # 记录发送
            await self.record_proactive(
                user_id=user_id,
                character_id=character_id,
                msg_type=ProactiveType(proactive["type"]),
                message_content=proactive["message"]
            )
            
            logger.info(f"Generated proactive: {proactive['type']} for {user_id}")
            return proactive
        
        return None
    
    async def batch_process_users(
        self,
        users: List[Dict[str, str]],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """批量处理用户主动消息"""
        results = []
        processed = 0
        
        for user_info in users[:limit]:
            user_id = user_info.get("user_id")
            character_id = user_info.get("character_id", "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d")  # 默认Luna
            
            if not user_id:
                continue
            
            try:
                result = await self.process_user_proactive(user_id, character_id)
                if result:
                    results.append(result)
                    
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                continue
        
        logger.info(f"Batch processed {processed} users, generated {len(results)} messages")
        return results


# 单例实例
enhanced_proactive_service = EnhancedProactiveService()
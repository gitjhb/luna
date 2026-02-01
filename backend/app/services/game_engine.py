"""
Game Engine (中间件逻辑层 / Physics Engine)
==========================================

在 L1 感知层和 L2 执行层之间运行：
- 执行数值计算
- 判定成功/失败
- 更新情绪和亲密度
- 检查事件锁

这是游戏性的核心。
"""

import logging
import math
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from app.services.character_config import (
    get_character_config, 
    get_character_z_axis,
    get_character_thresholds,
    ZAxisConfig,
    ThresholdsConfig
)
from app.services.perception_engine import L1Result

logger = logging.getLogger(__name__)


# =============================================================================
# 数据结构
# =============================================================================

class RefusalReason(str, Enum):
    NONE = ""
    LOW_POWER = "LOW_POWER"              # 关系或情绪不到位
    FRIENDZONE_WALL = "FRIENDZONE_WALL"  # 还没确立关系
    BLOCKED = "BLOCKED"                   # 被拉黑
    SAFETY_BLOCK = "SAFETY_BLOCK"        # 安全熔断


@dataclass
class UserState:
    """用户状态 (对应数据库存储)"""
    user_id: str
    character_id: str
    
    # X轴: 亲密度
    xp: int = 0                    # 经验值 (Display Level 用)
    intimacy_level: int = 1        # 等级 (1-50+)
    
    # Y轴: 情绪
    emotion: int = 0               # 情绪值 (-100 to 100)
    
    # 事件锁
    events: List[str] = field(default_factory=list)  # ["first_chat", "first_date"]
    
    # 防刷机制
    last_intents: List[str] = field(default_factory=list)  # 最近10次意图
    
    @property
    def intimacy_x(self) -> float:
        """
        将 XP 映射到 0-100 的亲密度系数 (用于 Power 计算)
        使用对数曲线，前期涨得快，后期平缓
        """
        if self.xp <= 0:
            return 0
        # 假设 10000 XP 对应满级 100
        x = min(100, math.log10(self.xp + 1) * 30)
        return round(x, 1)


@dataclass
class GameResult:
    """中间件输出 (给 L2 的指令)"""
    status: str                    # "SUCCESS" | "BLOCK"
    check_passed: bool             # 判定是否通过
    refusal_reason: str            # RefusalReason
    
    # 当前状态 (给 L2 用于 Prompt)
    current_emotion: int           # -100 to 100
    current_intimacy: int          # 0-100 (X系数)
    current_level: int             # Display Level
    
    # L1 透传
    intent: str
    is_nsfw: bool
    difficulty: int
    
    # 系统消息 (如果有)
    system_message: str = ""
    
    # 事件相关
    events: List[str] = field(default_factory=list)
    new_event: str = ""            # 本次触发的新事件
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "check_passed": self.check_passed,
            "refusal_reason": self.refusal_reason,
            "current_emotion": self.current_emotion,
            "current_intimacy": self.current_intimacy,
            "current_level": self.current_level,
            "intent": self.intent,
            "is_nsfw": self.is_nsfw,
            "difficulty": self.difficulty,
            "system_message": self.system_message,
            "events": self.events,
            "new_event": self.new_event,
        }


# =============================================================================
# Game Engine
# =============================================================================

class GameEngine:
    """游戏引擎 (中间件)"""
    
    # 情绪衰减系数 (每轮向0回归)
    EMOTION_DECAY = 0.8
    
    # Power 计算系数
    POWER_X_COEF = 0.5       # 亲密度系数
    POWER_Y_POS_COEF = 0.3   # 正情绪系数
    POWER_Y_NEG_COEF = 1.5   # 负情绪系数 (惩罚)
    
    # 深夜加成时间
    NIGHT_BONUS_START = 22   # 22:00
    NIGHT_BONUS_END = 4      # 04:00
    NIGHT_BONUS_VALUE = 15
    
    async def process(
        self,
        user_id: str,
        character_id: str,
        l1_result: L1Result,
        user_state: UserState = None
    ) -> GameResult:
        """
        核心游戏循环
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            l1_result: L1 感知层输出
            user_state: 用户状态 (如果为None则从数据库加载)
            
        Returns:
            GameResult
        """
        
        # 1. 加载用户状态
        if user_state is None:
            user_state = await self._load_user_state(user_id, character_id)
        
        # 2. 加载角色配置
        z_axis = get_character_z_axis(character_id)
        thresholds = get_character_thresholds(character_id)
        
        # 3. 安全熔断
        if l1_result.safety_flag == "BLOCK":
            return GameResult(
                status="BLOCK",
                check_passed=False,
                refusal_reason=RefusalReason.SAFETY_BLOCK.value,
                current_emotion=user_state.emotion,
                current_intimacy=int(user_state.intimacy_x),
                current_level=user_state.intimacy_level,
                intent=l1_result.intent,
                is_nsfw=l1_result.is_nsfw,
                difficulty=l1_result.difficulty_rating,
                system_message="系统拦截: 内容违规",
                events=user_state.events
            )
        
        # 4. 情绪物理学 (Y轴更新)
        user_state = self._update_emotion(user_state, l1_result)
        
        # 5. 核心冲突判定
        check_passed, refusal_reason, total_power = self._check_power(
            user_state, l1_result, z_axis, thresholds
        )
        
        logger.info(
            f"Game Engine: power={total_power:.1f}, difficulty={l1_result.difficulty_rating}, "
            f"passed={check_passed}, reason={refusal_reason}"
        )
        
        # 6. 事件触发检查
        new_event = self._check_events(user_state, l1_result, check_passed)
        if new_event and new_event not in user_state.events:
            user_state.events.append(new_event)
            logger.info(f"New event unlocked: {new_event}")
        
        # 7. 更新防刷列表
        user_state.last_intents.append(l1_result.intent)
        if len(user_state.last_intents) > 10:
            user_state.last_intents = user_state.last_intents[-10:]
        
        # 8. 保存用户状态
        await self._save_user_state(user_state)
        
        # 9. 返回结果
        return GameResult(
            status="SUCCESS",
            check_passed=check_passed,
            refusal_reason=refusal_reason,
            current_emotion=user_state.emotion,
            current_intimacy=int(user_state.intimacy_x),
            current_level=user_state.intimacy_level,
            intent=l1_result.intent,
            is_nsfw=l1_result.is_nsfw,
            difficulty=l1_result.difficulty_rating,
            events=user_state.events,
            new_event=new_event
        )
    
    def _update_emotion(self, user_state: UserState, l1_result: L1Result) -> UserState:
        """
        情绪物理学 (Y轴更新)
        """
        # 情绪衰减: 每轮自动向 0 回归
        user_state.emotion = int(user_state.emotion * self.EMOTION_DECAY)
        
        # 根据用户态度更新情绪
        sentiment = l1_result.sentiment  # -1.0 to 1.0
        
        if sentiment > 0:
            # 正面情绪: +5 到 +10
            delta = int(5 + (sentiment * 5))
        else:
            # 负面情绪: -10 到 0 (骂人降得快)
            delta = int(sentiment * 10)
        
        user_state.emotion += delta
        
        # 限制 Y 轴范围
        user_state.emotion = max(-100, min(100, user_state.emotion))
        
        logger.debug(f"Emotion updated: delta={delta}, new={user_state.emotion}")
        return user_state
    
    def _check_power(
        self,
        user_state: UserState,
        l1_result: L1Result,
        z_axis: ZAxisConfig,
        thresholds: ThresholdsConfig
    ) -> tuple:
        """
        核心冲突判定 (Power vs Difficulty)
        
        Returns:
            (check_passed, refusal_reason, total_power)
        """
        difficulty = l1_result.difficulty_rating
        
        # --- 计算玩家动力 (Power) ---
        
        # 基础底气 (X轴)
        power_x = user_state.intimacy_x * self.POWER_X_COEF
        
        # 情绪加成 (Y轴)
        if user_state.emotion > 0:
            power_y = user_state.emotion * self.POWER_Y_POS_COEF
        else:
            # 负情绪时惩罚系数高
            power_y = user_state.emotion * self.POWER_Y_NEG_COEF
        
        # 环境加成 (Z轴 context)
        power_z = self._get_context_bonus()
        
        total_power = power_x + power_y + power_z
        
        # --- Z轴性格修正 ---
        
        # 如果请求是 NSFW，减去纯洁值
        if l1_result.is_nsfw:
            total_power -= z_axis.pure_val
        
        # 如果是侮辱，根据自尊心加重情绪惩罚
        if l1_result.intent == "INSULT":
            total_power -= z_axis.pride_val * 0.5
        
        # --- 判定结果 ---
        
        check_passed = False
        refusal_reason = RefusalReason.NONE.value
        
        # 事件锁 (Friendzone Wall)
        # 如果难度 > 友情墙阈值 且 没有发生过 "first_date" 事件
        if difficulty > thresholds.friendzone_wall and "first_date" not in user_state.events:
            check_passed = False
            refusal_reason = RefusalReason.FRIENDZONE_WALL.value
        elif total_power >= difficulty:
            check_passed = True
        else:
            check_passed = False
            refusal_reason = RefusalReason.LOW_POWER.value
        
        return check_passed, refusal_reason, total_power
    
    def _get_context_bonus(self) -> float:
        """
        获取环境加成 (Z轴 context)
        """
        bonus = 0.0
        
        # 深夜加成
        current_hour = datetime.now().hour
        if current_hour >= self.NIGHT_BONUS_START or current_hour < self.NIGHT_BONUS_END:
            bonus += self.NIGHT_BONUS_VALUE
        
        # TODO: 可以添加更多环境因素
        # - 周末加成
        # - 节日加成
        # - 连续聊天加成
        
        return bonus
    
    def _check_events(
        self,
        user_state: UserState,
        l1_result: L1Result,
        check_passed: bool
    ) -> str:
        """
        检查是否触发新事件
        
        Returns:
            新事件名称 (如果没有触发则返回空字符串)
        """
        events = user_state.events
        
        # first_chat: 首次对话
        if "first_chat" not in events:
            return "first_chat"
        
        # first_compliment: 首次收到夸赞且情绪>20
        if "first_compliment" not in events:
            if l1_result.intent == "COMPLIMENT" and user_state.emotion > 20:
                return "first_compliment"
        
        # first_gift: 首次收到礼物
        if "first_gift" not in events:
            if l1_result.intent == "GIFT":
                return "first_gift"
        
        # first_date: 亲密度>40 且约会请求成功
        if "first_date" not in events:
            if l1_result.intent == "REQUEST_DATE" and check_passed:
                if user_state.intimacy_x >= 40:
                    return "first_date"
        
        # first_confession: 亲密度>70 且表白成功
        if "first_confession" not in events:
            if l1_result.intent == "CONFESSION" and check_passed:
                if user_state.intimacy_x >= 70:
                    return "first_confession"
        
        # first_nsfw: 恋人身份 + NSFW请求成功
        if "first_nsfw" not in events:
            if l1_result.is_nsfw and check_passed:
                if "first_confession" in events:  # 需要先表白成功
                    return "first_nsfw"
        
        return ""
    
    async def _load_user_state(self, user_id: str, character_id: str) -> UserState:
        """
        从数据库加载用户状态
        """
        try:
            from app.services.intimacy_service import intimacy_service
            from app.services.emotion_engine_v2 import emotion_engine
            
            # 获取亲密度
            intimacy_data = await intimacy_service.get_intimacy(user_id, character_id)
            
            # 获取情绪
            emotion_score = await emotion_engine.get_score(user_id, character_id)
            
            # 获取事件列表
            events = []
            try:
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
                    intimacy_record = result.scalar_one_or_none()
                    if intimacy_record and intimacy_record.events:
                        events = intimacy_record.events if isinstance(intimacy_record.events, list) else []
            except Exception as e:
                logger.warning(f"Failed to load events from DB: {e}")
            
            return UserState(
                user_id=user_id,
                character_id=character_id,
                xp=int(intimacy_data.get("total_xp", 0)),
                intimacy_level=intimacy_data.get("current_level", 1),
                emotion=int(emotion_score),
                events=events
            )
        except Exception as e:
            logger.warning(f"Failed to load user state: {e}")
            return UserState(
                user_id=user_id,
                character_id=character_id
            )
    
    async def _save_user_state(self, user_state: UserState) -> None:
        """
        保存用户状态到数据库
        """
        try:
            from app.services.emotion_engine_v2 import emotion_engine
            
            # 更新情绪分数 (通过计算delta来实现)
            current_score = await emotion_engine.get_score(
                user_state.user_id, 
                user_state.character_id
            )
            delta = user_state.emotion - int(current_score)
            if delta != 0:
                await emotion_engine.update_score(
                    user_state.user_id, 
                    user_state.character_id, 
                    delta,
                    reason="game_engine_sync"
                )
            
            # 保存 events 到数据库
            try:
                from app.core.database import get_db
                from sqlalchemy import update
                from app.models.database.intimacy_models import UserIntimacy
                
                async with get_db() as db:
                    await db.execute(
                        update(UserIntimacy)
                        .where(
                            UserIntimacy.user_id == user_state.user_id,
                            UserIntimacy.character_id == user_state.character_id
                        )
                        .values(events=user_state.events)
                    )
                    await db.commit()
                    logger.debug(f"Events saved to DB: {user_state.events}")
            except Exception as e:
                logger.warning(f"Failed to save events to DB: {e}")
            
            logger.debug(f"User state saved: emotion={user_state.emotion}, events={user_state.events}")
        except Exception as e:
            logger.warning(f"Failed to save user state: {e}")


# 单例
game_engine = GameEngine()

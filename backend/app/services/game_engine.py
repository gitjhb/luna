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
from app.services.event_state_machine import (
    event_state_machine,
    EventType,
    is_friendzone_broken
)

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
    message_history: List[str] = field(default_factory=list)  # 最近10条消息哈希（用于复读检测）
    
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
    
    # 有默认值的字段必须放后面
    emotion_before: int = 0        # 处理前的情绪值
    emotion_delta: int = 0         # 情绪变化量
    emotion_state: str = ""        # EmotionState: LOVING/HAPPY/.../COLD_WAR/BLOCKED
    emotion_locked: bool = False   # 是否处于锁定状态 (冷战/拉黑)
    system_message: str = ""       # 系统消息 (如果有)
    events: List[str] = field(default_factory=list)  # 事件相关
    new_event: str = ""            # 本次触发的新事件
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "check_passed": self.check_passed,
            "refusal_reason": self.refusal_reason,
            "current_emotion": self.current_emotion,
            "emotion_before": self.emotion_before,
            "emotion_delta": self.emotion_delta,
            "emotion_state": self.emotion_state,
            "emotion_locked": self.emotion_locked,
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
        user_state: UserState = None,
        user_message: str = ""
    ) -> GameResult:
        """
        核心游戏循环
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            l1_result: L1 感知层输出
            user_state: 用户状态 (如果为None则从数据库加载)
            user_message: 用户原始消息 (用于复读检测)
            
        Returns:
            GameResult
        """
        self._current_user_message = user_message  # 暂存，供 _update_emotion 使用
        
        # 1. 加载用户状态
        if user_state is None:
            user_state = await self._load_user_state(user_id, character_id)
        
        # 2. 加载角色配置
        z_axis = get_character_z_axis(character_id)
        thresholds = get_character_thresholds(character_id)
        # 获取完整角色配置用于日志
        char_full_config = get_character_config(character_id)
        if char_full_config:
            logger.info(f"📊 Character Config [{char_full_config.name}]: "
                        f"sensitivity={char_full_config.sensitivity}, forgiveness={char_full_config.forgiveness_rate}, "
                        f"temperament={char_full_config.base_temperament}")
        logger.info(f"📊 Z-Axis: pure={z_axis.pure_val}, pride={z_axis.pride_val}, chaos={z_axis.chaos_val}, "
                    f"greed={z_axis.greed_val}, jealousy={z_axis.jealousy_val}")
        
        # 3. 安全熔断
        if l1_result.safety_flag == "BLOCK":
            from app.services.physics_engine import EmotionState
            emotion_state = EmotionState.get_state(user_state.emotion)
            return GameResult(
                status="BLOCK",
                check_passed=False,
                refusal_reason=RefusalReason.SAFETY_BLOCK.value,
                current_emotion=user_state.emotion,
                current_intimacy=int(user_state.intimacy_x),
                current_level=user_state.intimacy_level,
                emotion_state=emotion_state,
                emotion_locked=emotion_state in EmotionState.LOCKED_STATES,
                intent=l1_result.intent,
                is_nsfw=l1_result.is_nsfw,
                difficulty=l1_result.difficulty_rating,
                system_message="系统拦截: 内容违规",
                events=user_state.events
            )
        
        # 4. 情绪物理学 (Y轴更新) - 使用 PhysicsEngine v2.2
        emotion_before = user_state.emotion  # 记录变化前的情绪
        user_state = self._update_emotion(user_state, l1_result, character_id)
        emotion_delta = user_state.emotion - emotion_before
        
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
        from app.services.physics_engine import EmotionState
        emotion_state = EmotionState.get_state(user_state.emotion)
        
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
            emotion_before=emotion_before,
            emotion_delta=emotion_delta,
            emotion_state=emotion_state,
            emotion_locked=emotion_state in EmotionState.LOCKED_STATES,
            events=user_state.events,
            new_event=new_event
        )
    
    def _update_emotion(self, user_state: UserState, l1_result: L1Result, character_id: str) -> UserState:
        """
        情绪物理学 (Y轴更新) - 使用 PhysicsEngine v2.3
        
        基于"阻尼滑块"模型：
        - 衰减: 每轮向 0 回归 (decay_factor)
        - 推力: sentiment * 10 + intent_mod
        - 伤害加倍: 负面情绪 x2
        - 状态锁: 冷战/拉黑时普通对话无效
        - [v2.3] 智能防刷: 复读检测 + 意图防刷
        """
        from app.services.physics_engine import PhysicsEngine, CharacterZAxis, EmotionState
        
        # 获取角色 Z 轴配置
        char_config = CharacterZAxis.from_character_id(character_id)
        logger.info(f"📊 Physics Config: sensitivity={char_config.sensitivity}, decay={char_config.decay_rate:.2f}, "
                    f"pride={char_config.pride}, optimism={char_config.optimism}")
        
        # 构建 L1 结果字典 (PhysicsEngine 需要的格式)
        l1_dict = {
            'sentiment_score': l1_result.sentiment_score if hasattr(l1_result, 'sentiment_score') else l1_result.sentiment,
            'intent_category': l1_result.intent_category if hasattr(l1_result, 'intent_category') else l1_result.intent,
            'intimacy_x': user_state.intimacy_x,  # 传给 PhysicsEngine 做流氓检测
        }
        
        # 构建用户状态字典（包含消息历史用于防刷检测）
        state_dict = {
            'emotion': user_state.emotion,
            'last_intents': list(user_state.last_intents),  # 复制一份
            'message_history': list(user_state.message_history),  # 复制一份
        }
        
        old_emotion = user_state.emotion
        old_state = EmotionState.get_state(old_emotion)
        
        # 获取用户消息（从 process 方法暂存）
        user_message = getattr(self, '_current_user_message', '')
        
        # 使用 PhysicsEngine 计算新情绪值（传入用户消息用于复读检测）
        new_emotion = PhysicsEngine.update_state(state_dict, l1_dict, char_config, user_message)
        new_state = EmotionState.get_state(new_emotion)
        
        # 更新用户状态
        user_state.emotion = new_emotion
        user_state.last_intents = state_dict.get('last_intents', user_state.last_intents)
        user_state.message_history = state_dict.get('message_history', user_state.message_history)
        
        logger.info(f"📊 Emotion: {old_emotion}({old_state}) → {new_emotion}({new_state})")
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
        
        # 详细日志：Power 计算分解
        logger.info(f"📊 Power Calc: X={user_state.intimacy_x:.1f}×{self.POWER_X_COEF}={power_x:.1f} | "
                    f"Y={user_state.emotion}×{self.POWER_Y_POS_COEF if user_state.emotion > 0 else self.POWER_Y_NEG_COEF}={power_y:.1f} | "
                    f"Z(ctx)={power_z:.1f} → base={total_power:.1f}")
        
        # --- Z轴性格修正 ---
        z_penalty = 0.0
        
        # 如果请求是 NSFW，减去纯洁值
        if l1_result.is_nsfw:
            total_power -= z_axis.pure_val
            z_penalty += z_axis.pure_val
        
        # 如果是侮辱，根据自尊心加重情绪惩罚
        if l1_result.intent == "INSULT":
            total_power -= z_axis.pride_val * 0.5
            z_penalty += z_axis.pride_val * 0.5
        
        if z_penalty > 0:
            logger.info(f"📊 Z-Axis Penalty: pure={z_axis.pure_val}, pride={z_axis.pride_val} → penalty={z_penalty:.1f}, final_power={total_power:.1f}")
        
        # --- 判定结果 ---
        
        check_passed = False
        refusal_reason = RefusalReason.NONE.value
        
        # 事件锁 (Friendzone Wall) - 使用状态机判断
        # 不同角色有不同的友情墙突破条件
        is_beyond_friendzone = is_friendzone_broken(
            user_state.character_id, 
            user_state.events
        )
        
        if difficulty > thresholds.friendzone_wall and not is_beyond_friendzone:
            check_passed = False
            refusal_reason = RefusalReason.FRIENDZONE_WALL.value
            logger.info(f"📊 Friendzone Wall: difficulty={difficulty} > threshold={thresholds.friendzone_wall}, "
                       f"events={user_state.events}")
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
        检查是否触发新事件 (使用事件状态机)
        
        Returns:
            新事件名称 (如果没有触发则返回空字符串)
        """
        events = user_state.events
        character_id = user_state.character_id
        
        # 定义事件触发条件（与意图/状态的映射）
        event_triggers = {
            # first_chat: 首次对话，无条件
            EventType.FIRST_CHAT: lambda: True,
            
            # first_compliment: 收到夸赞且情绪>20
            EventType.FIRST_COMPLIMENT: lambda: (
                l1_result.intent == "COMPLIMENT" and user_state.emotion > 20
            ),
            
            # first_gift: 收到真实礼物（verified）
            EventType.FIRST_GIFT: lambda: (
                l1_result.intent in ["GIFT", "GIFT_SEND"] and 
                getattr(l1_result, 'transaction_verified', False)
            ),
            
            # first_date: 约会请求成功且亲密度足够
            EventType.FIRST_DATE: lambda: (
                l1_result.intent in ["REQUEST_DATE", "INVITATION"] and 
                check_passed and user_state.intimacy_x >= 40
            ),
            
            # first_kiss: 亲吻请求成功（需要高亲密度）
            EventType.FIRST_KISS: lambda: (
                l1_result.intent in ["REQUEST_KISS", "KISS"] and 
                check_passed and user_state.intimacy_x >= 60
            ),
            
            # first_confession: 表白成功
            EventType.FIRST_CONFESSION: lambda: (
                l1_result.intent in ["CONFESSION", "LOVE_CONFESSION"] and 
                check_passed and user_state.intimacy_x >= 70
            ),
            
            # first_nsfw: NSFW请求成功
            EventType.FIRST_NSFW: lambda: (
                l1_result.is_nsfw and check_passed
            ),
        }
        
        # 按优先级检查事件（first_chat 最优先）
        priority_order = [
            EventType.FIRST_CHAT,
            EventType.FIRST_COMPLIMENT,
            EventType.FIRST_GIFT,
            EventType.FIRST_DATE,
            EventType.FIRST_KISS,
            EventType.FIRST_CONFESSION,
            EventType.FIRST_NSFW,
        ]
        
        for event_type in priority_order:
            # 1. 检查状态机是否允许触发
            if not event_state_machine.can_trigger_event(
                character_id, event_type, events
            ):
                continue
            
            # 2. 检查具体触发条件
            trigger_check = event_triggers.get(event_type, lambda: False)
            if trigger_check():
                logger.info(
                    f"Event triggered via state machine: {event_type} "
                    f"(chain={event_state_machine.get_chain_type(character_id)})"
                )
                return event_type
        
        return ""
    
    async def _load_user_state(self, user_id: str, character_id: str) -> UserState:
        """
        从数据库加载用户状态
        """
        try:
            from app.services.intimacy_service import intimacy_service
            from app.services.emotion_engine_v2 import emotion_engine
            
            # 获取亲密度
            intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
            
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
            
            xp = int(intimacy_data.get("total_xp", 0))
            level = intimacy_data.get("current_level", 1)
            emotion = int(emotion_score)
            
            state = UserState(
                user_id=user_id,
                character_id=character_id,
                xp=xp,
                intimacy_level=level,
                emotion=emotion,
                events=events
            )
            logger.info(f"📊 User State Loaded: xp={xp}, level={level}, intimacy_x={state.intimacy_x:.1f}, emotion={emotion}, events={events}")
            return state
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

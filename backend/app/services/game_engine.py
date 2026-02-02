"""
Game Engine (中间件逻辑层 / Physics Engine) v3.0
================================================

在 L1 感知层和 L2 执行层之间运行：
- 执行数值计算
- 判定成功/失败
- 更新情绪和亲密度
- 检查事件锁

v3.0 更新：
- 使用 intimacy_system 的 Power 公式
- 整合角色原型系统 (NORMAL/PHANTOM/YUKI)
- 新的 Stage 系统 (5个阶段)
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
    get_character_archetype,
    get_difficulty_modifier,
    ZAxisConfig,
    ThresholdsConfig,
    CharacterArchetype
)
from app.services.perception_engine import L1Result
from app.services.intimacy_constants import (
    calculate_power as calc_power_v3,
    get_stage,
    RelationshipStage,
    STAGE_NAMES_CN,
    STAGE_BEHAVIORS,
    EVENT_DIFFICULTY,
    POWER_PASS_THRESHOLD
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
    intimacy_level: int = 1        # 等级 (1-40)
    
    # Y轴: 情绪
    emotion: int = 0               # 情绪值 (-100 to 100)
    
    # 事件锁
    events: List[str] = field(default_factory=list)  # ["first_chat", "first_date"]
    
    # 防刷机制
    last_intents: List[str] = field(default_factory=list)  # 最近10次意图
    message_history: List[str] = field(default_factory=list)  # 最近10条消息哈希
    
    @property
    def intimacy_x(self) -> float:
        """
        将等级映射到 0-100 的亲密度 (用于 Power 计算)
        
        v3.0 映射：
        - Lv.1-5   → Intimacy 0-19  (S0 陌生人)
        - Lv.6-10  → Intimacy 20-39 (S1 朋友)
        - Lv.11-15 → Intimacy 40-59 (S2 暧昧)
        - Lv.16-25 → Intimacy 60-79 (S3 恋人)
        - Lv.26-40 → Intimacy 80-100 (S4 挚爱)
        """
        level = self.intimacy_level
        
        if level <= 5:
            # Lv1-5 → 0-19
            return round((level - 1) * 4.75, 1)
        elif level <= 10:
            # Lv6-10 → 20-39
            return round(20 + (level - 6) * 4, 1)
        elif level <= 15:
            # Lv11-15 → 40-59
            return round(40 + (level - 11) * 4, 1)
        elif level <= 25:
            # Lv16-25 → 60-79
            return round(60 + (level - 16) * 2, 1)
        else:
            # Lv26-40 → 80-100
            return round(min(100, 80 + (level - 26) * 1.4), 1)
    
    @property
    def stage(self) -> RelationshipStage:
        """获取当前关系阶段"""
        return get_stage(int(self.intimacy_x))


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
    
    # v3.0 新增
    power: float = 0.0             # 当前 Power 值
    stage: str = ""                # 当前关系阶段
    archetype: str = ""            # 角色原型
    adjusted_difficulty: int = 0   # 调整后的难度 (base × archetype modifier)
    difficulty_modifier: float = 1.0  # 角色难度系数
    
    # Power 计算明细
    power_intimacy: float = 0.0    # Intimacy × 0.5
    power_emotion: float = 0.0     # Emotion × 0.5
    power_chaos: float = 0.0       # Chaos 值
    power_pure: float = 0.0        # Pure 值 (会被减掉)
    power_buff: float = 0.0        # 环境加成 (深夜等)
    power_effect: float = 0.0      # 道具效果加成 (Tier 2 礼物)
    
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
            "power": self.power,
            "stage": self.stage,
            "archetype": self.archetype,
        }


# =============================================================================
# Game Engine
# =============================================================================

class GameEngine:
    """游戏引擎 (中间件) v3.0"""
    
    # 情绪衰减系数 (每轮向0回归)
    EMOTION_DECAY = 0.8
    
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
        archetype = get_character_archetype(character_id)
        difficulty_mod = get_difficulty_modifier(character_id)
        
        # 获取完整角色配置用于日志
        char_full_config = get_character_config(character_id)
        if char_full_config:
            logger.info(f"📊 Character [{char_full_config.name}]: archetype={archetype.value}, "
                        f"difficulty_mod={difficulty_mod}, chaos={z_axis.chaos_val}, pure={z_axis.pure_val}")
        
        # 3. 安全熔断
        if l1_result.safety_flag == "BLOCK":
            from app.services.physics_engine import EmotionState
            emotion_state = EmotionState.get_state(user_state.emotion)
            stage = get_stage(int(user_state.intimacy_x))
            return GameResult(
                status="BLOCK",
                check_passed=False,
                refusal_reason=RefusalReason.SAFETY_BLOCK.value,
                current_emotion=user_state.emotion,
                current_intimacy=int(user_state.intimacy_x),
                current_level=user_state.intimacy_level,
                emotion_state=emotion_state,
                emotion_locked=emotion_state in ["COLD_WAR", "BLOCKED"],
                intent=l1_result.intent,
                is_nsfw=l1_result.is_nsfw,
                difficulty=l1_result.difficulty_rating,
                system_message="系统拦截: 内容违规",
                events=user_state.events,
                stage=stage.value,
                archetype=archetype.value,
            )
        
        # 4. 情绪物理学 (Y轴更新) - 使用 PhysicsEngine v2.3
        emotion_before = user_state.emotion
        user_state = self._update_emotion(user_state, l1_result, character_id)
        emotion_delta = user_state.emotion - emotion_before
        
        # 4.5. 获取道具效果 buff (Tier 2 礼物)
        effect_buff = 0.0
        effect_buff_details = []
        try:
            from app.services.effect_service import effect_service
            effect_buff, effect_buff_details = await effect_service.get_power_buff(user_id, character_id)
            if effect_buff > 0:
                logger.info(f"📊 Effect Buff: +{effect_buff:.1f} from {[e['effect_type'] for e in effect_buff_details]}")
        except Exception as e:
            logger.warning(f"Failed to get effect buff: {e}")
        
        # 5. 核心冲突判定 (v3.0 Power 公式)
        check_passed, refusal_reason, total_power, adjusted_difficulty, power_breakdown = self._check_power_v3(
            user_state, l1_result, z_axis, archetype, difficulty_mod, effect_buff
        )
        
        logger.info(
            f"Game Engine: power={total_power:.1f}, difficulty={l1_result.difficulty_rating}×{difficulty_mod}={adjusted_difficulty}, "
            f"passed={check_passed}, reason={refusal_reason}, archetype={archetype.value}"
        )
        
        # 6. 事件触发检查
        new_event = self._check_events_v3(user_state, l1_result, check_passed, archetype)
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
        stage = get_stage(int(user_state.intimacy_x))
        
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
            emotion_locked=emotion_state in ["COLD_WAR", "BLOCKED"],
            events=user_state.events,
            new_event=new_event,
            power=total_power,
            stage=stage.value,
            archetype=archetype.value,
            adjusted_difficulty=adjusted_difficulty,
            difficulty_modifier=difficulty_mod,
            power_intimacy=power_breakdown['intimacy'],
            power_emotion=power_breakdown['emotion'],
            power_chaos=power_breakdown['chaos'],
            power_pure=power_breakdown['pure'],
            power_buff=power_breakdown['buff'],
            power_effect=power_breakdown['effect'],
        )
    
    def _update_emotion(self, user_state: UserState, l1_result: L1Result, character_id: str) -> UserState:
        """
        情绪物理学 (Y轴更新) - 使用 PhysicsEngine v2.3
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
            'intimacy_x': user_state.intimacy_x,
        }
        
        # 构建用户状态字典
        state_dict = {
            'emotion': user_state.emotion,
            'last_intents': list(user_state.last_intents),
            'message_history': list(user_state.message_history),
        }
        
        old_emotion = user_state.emotion
        old_state = EmotionState.get_state(old_emotion)
        
        # 获取用户消息
        user_message = getattr(self, '_current_user_message', '')
        
        # 使用 PhysicsEngine 计算新情绪值
        new_emotion = PhysicsEngine.update_state(state_dict, l1_dict, char_config, user_message)
        new_state = EmotionState.get_state(new_emotion)
        
        # 更新用户状态
        user_state.emotion = new_emotion
        user_state.last_intents = state_dict.get('last_intents', user_state.last_intents)
        user_state.message_history = state_dict.get('message_history', user_state.message_history)
        
        logger.info(f"📊 Emotion: {old_emotion}({old_state}) → {new_emotion}({new_state})")
        return user_state
    
    def _check_power_v3(
        self,
        user_state: UserState,
        l1_result: L1Result,
        z_axis: ZAxisConfig,
        archetype: CharacterArchetype,
        difficulty_mod: float,
        effect_buff: float = 0.0
    ) -> tuple:
        """
        核心冲突判定 (Power vs Difficulty) - v3.0 公式
        
        Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff + EffectBuff
        
        Returns:
            (check_passed, refusal_reason, total_power, adjusted_difficulty, power_breakdown)
        """
        # 原始难度
        base_difficulty = l1_result.difficulty_rating
        
        # 应用角色难度系数
        # PHANTOM: 难度×0.7 (更容易)
        # YUKI: 难度×1.5 (更难)
        adjusted_difficulty = int(base_difficulty * difficulty_mod)
        
        logger.info(f"📊 Difficulty: base={base_difficulty}, modifier={difficulty_mod}, adjusted={adjusted_difficulty}")
        
        # --- 计算 Power (v3.0 公式) ---
        # Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff
        
        intimacy = int(user_state.intimacy_x)
        emotion = user_state.emotion
        chaos_val = z_axis.chaos_val
        pure_val = z_axis.pure_val
        
        # 环境加成 (Buff)
        buff_bonus = self._get_context_bonus()
        
        # 计算各项贡献
        intimacy_contrib = intimacy * 0.5
        emotion_contrib = emotion * 0.5
        
        # 基础 Power (不含 effect buff)
        base_power = calc_power_v3(intimacy, emotion, chaos_val, pure_val, buff_bonus)
        
        # 总 Power = 基础 + 道具效果
        total_power = base_power + effect_buff
        
        # Power 计算明细
        power_breakdown = {
            'intimacy': intimacy_contrib,
            'emotion': emotion_contrib,
            'chaos': chaos_val,
            'pure': pure_val,
            'buff': buff_bonus,
            'effect': effect_buff,  # 道具效果加成
        }
        
        logger.info(f"📊 Power Calc: intimacy={intimacy}×0.5={intimacy_contrib:.1f} | "
                    f"emotion={emotion}×0.5={emotion_contrib:.1f} | "
                    f"chaos={chaos_val} | pure=-{pure_val} | buff={buff_bonus} | effect=+{effect_buff:.1f} → total={total_power:.1f}")
        
        # --- 判定结果 ---
        
        check_passed = False
        refusal_reason = RefusalReason.NONE.value
        
        # 获取当前阶段
        stage = get_stage(intimacy)
        
        # 友情墙检查：恋人阶段以下，NSFW 请求需要特殊事件
        if l1_result.is_nsfw and stage.value in ["stranger", "friend", "crush"]:
            # 检查是否已完成表白事件
            has_confession = "confession" in user_state.events or "first_confession" in user_state.events
            
            if not has_confession:
                check_passed = False
                refusal_reason = RefusalReason.FRIENDZONE_WALL.value
                logger.info(f"📊 Friendzone Wall: stage={stage.value}, no confession event")
                return check_passed, refusal_reason, total_power, adjusted_difficulty, power_breakdown
        
        # Power vs Difficulty 判定
        if total_power >= adjusted_difficulty:
            check_passed = True
        else:
            check_passed = False
            refusal_reason = RefusalReason.LOW_POWER.value
        
        return check_passed, refusal_reason, total_power, adjusted_difficulty, power_breakdown
    
    def _get_context_bonus(self) -> float:
        """
        获取环境加成 (Buff)
        """
        bonus = 0.0
        
        # 深夜加成
        current_hour = datetime.now().hour
        if current_hour >= self.NIGHT_BONUS_START or current_hour < self.NIGHT_BONUS_END:
            bonus += self.NIGHT_BONUS_VALUE
        
        return bonus
    
    def _check_events_v3(
        self,
        user_state: UserState,
        l1_result: L1Result,
        check_passed: bool,
        archetype: CharacterArchetype
    ) -> str:
        """
        检查是否触发新事件 (v3.0 - 使用角色原型)
        
        Returns:
            新事件名称 (如果没有触发则返回空字符串)
        """
        from app.services.intimacy_system import (
            can_trigger_event as can_trigger_v3,
            GateEvent,
            get_event_difficulty
        )
        
        events = user_state.events
        intimacy = int(user_state.intimacy_x)
        emotion = user_state.emotion
        z_axis = get_character_z_axis(user_state.character_id)
        
        # 计算当前 Power
        power = calc_power_v3(intimacy, emotion, z_axis.chaos_val, z_axis.pure_val)
        
        # 事件触发映射
        event_triggers = {
            GateEvent.FIRST_CHAT: lambda: True,
            GateEvent.FIRST_GIFT: lambda: l1_result.intent in ["GIFT", "GIFT_SEND"],
            GateEvent.FIRST_DATE: lambda: l1_result.intent in ["INVITATION", "DATE_REQUEST"] and check_passed,
            GateEvent.CONFESSION: lambda: l1_result.intent in ["CONFESSION", "LOVE_CONFESSION"] and check_passed,
            GateEvent.FIRST_KISS: lambda: l1_result.intent in ["REQUEST_KISS", "KISS"] and check_passed,
            GateEvent.FIRST_NSFW: lambda: l1_result.is_nsfw and check_passed,
            GateEvent.PROPOSAL: lambda: l1_result.intent in ["PROPOSAL"] and check_passed,
        }
        
        # 按优先级检查事件
        for gate_event, trigger_check in event_triggers.items():
            event_name = gate_event.value
            
            # 已完成不能重复
            if event_name in events:
                continue
            
            # 使用 intimacy_system 的状态机检查
            can_trigger, reason = can_trigger_v3(
                archetype, gate_event, events, power
            )
            
            if can_trigger and trigger_check():
                logger.info(f"Event triggered: {event_name} (archetype={archetype.value}, power={power:.1f})")
                return event_name
        
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
            logger.info(f"📊 User State Loaded: xp={xp}, level={level}, intimacy_x={state.intimacy_x:.1f}, "
                       f"emotion={emotion}, stage={state.stage.value}, events={events}")
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
            
            # 更新情绪分数
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

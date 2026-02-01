"""
Luna Physics Engine v2.0
========================

基于"阻尼滑块"模型的情绪计算引擎。

核心思想：
- 情绪像一个有阻尼的滑块
- 用户推力 (Stimulus) = sentiment * 10 + intent_mod
- 负面情绪伤害加倍 (Loss Aversion)
- 每轮自然衰减向 0 回归 (decay_factor = 0.9)
- 角色敏感度 (dependency) 放大/缩小所有情绪变化

协议文档: docs/Luna_Intent_Protocol.md
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# Intent 枚举 (必须与 L1 输出严格对应)
# =============================================================================

class IntentCategory:
    """Intent 枚举值 - L1 必须严格从这个列表选择"""
    
    # 基础交互类 (Low Impact)
    GREETING = "GREETING"
    SMALL_TALK = "SMALL_TALK"
    CLOSING = "CLOSING"
    
    # 正向激励类 (Positive Stimulus)
    COMPLIMENT = "COMPLIMENT"
    FLIRT = "FLIRT"
    LOVE_CONFESSION = "LOVE_CONFESSION"
    COMFORT = "COMFORT"
    
    # 负面打击类 (Negative Stimulus)
    CRITICISM = "CRITICISM"
    INSULT = "INSULT"
    IGNORE = "IGNORE"
    
    # 修复与特殊类 (Special Mechanics)
    APOLOGY = "APOLOGY"
    GIFT_SEND = "GIFT_SEND"
    REQUEST_NSFW = "REQUEST_NSFW"
    INVITATION = "INVITATION"
    
    # 所有有效值
    ALL_VALUES = [
        GREETING, SMALL_TALK, CLOSING,
        COMPLIMENT, FLIRT, LOVE_CONFESSION, COMFORT,
        CRITICISM, INSULT, IGNORE,
        APOLOGY, GIFT_SEND, REQUEST_NSFW, INVITATION
    ]
    
    # 正向意图 (用于防刷检测)
    POSITIVE_INTENTS = [COMPLIMENT, FLIRT, LOVE_CONFESSION, COMFORT]


# =============================================================================
# Intent Stimulus 修正值
# =============================================================================

INTENT_STIMULUS_MAP = {
    # 基础交互类 - 0 修正
    IntentCategory.GREETING: 0,
    IntentCategory.SMALL_TALK: 0,
    IntentCategory.CLOSING: 0,
    
    # 正向激励类
    IntentCategory.COMPLIMENT: 5,
    IntentCategory.FLIRT: 10,
    IntentCategory.LOVE_CONFESSION: 15,
    IntentCategory.COMFORT: 20,  # 动态调整见代码
    
    # 负面打击类
    IntentCategory.CRITICISM: -10,
    IntentCategory.INSULT: -30,
    IntentCategory.IGNORE: -5,
    
    # 修复与特殊类
    IntentCategory.APOLOGY: 15,  # 动态调整见代码
    IntentCategory.GIFT_SEND: 50,
    IntentCategory.REQUEST_NSFW: 0,
    IntentCategory.INVITATION: 0,
}


# =============================================================================
# 角色配置
# =============================================================================

@dataclass
class CharacterZAxis:
    """角色 Z 轴配置 (影响情绪物理)"""
    dependency: float = 1.0  # 情绪敏感度: Nana=1.5, Luna=1.0, Vesper=0.5
    pride: float = 10.0      # 自尊心: 影响道歉效果
    
    @classmethod
    def from_character_id(cls, character_id: str) -> "CharacterZAxis":
        """根据角色 ID 返回配置"""
        # TODO: 从数据库/配置文件读取
        # 暂时硬编码
        configs = {
            "550e8400-e29b-41d4-a716-446655440001": cls(dependency=1.2, pride=8),   # 苏糖糖 - 稍微敏感
            "550e8400-e29b-41d4-a716-446655440002": cls(dependency=0.8, pride=15),  # 林悦 - 稍微高冷
            "550e8400-e29b-41d4-a716-446655440003": cls(dependency=1.5, pride=5),   # 小萌 - 很敏感
            "550e8400-e29b-41d4-a716-446655440004": cls(dependency=1.0, pride=10),  # 默认
            "550e8400-e29b-41d4-a716-446655440005": cls(dependency=0.6, pride=20),  # 高冷型
        }
        return configs.get(character_id, cls())


# =============================================================================
# 物理引擎核心
# =============================================================================

class PhysicsEngine:
    """
    Luna 核心物理引擎 v2.0
    负责计算情绪的"阻尼滑块"运动
    """
    
    # 衰减因子: 每轮对话，情绪向 0 回归 10%
    DECAY_FACTOR = 0.9
    
    # 情绪边界
    EMOTION_MIN = -100
    EMOTION_MAX = 100
    
    # 防刷阈值
    ANTI_GRIND_THRESHOLD = 3
    ANTI_GRIND_MULTIPLIER = 0.1
    
    @classmethod
    def calculate_emotion_delta(
        cls,
        current_emotion: int,
        l1_result: Dict[str, Any],
        char_config: CharacterZAxis,
        recent_intents: Optional[List[str]] = None
    ) -> int:
        """
        计算本轮对话的情绪增量 (Delta)
        
        Args:
            current_emotion: 当前情绪值 (-100 ~ +100)
            l1_result: L1 分析结果 (sentiment_score, intent_category)
            char_config: 角色 Z 轴配置
            recent_intents: 最近几轮的 intent 列表 (用于防刷)
        
        Returns:
            情绪增量 (int)
        """
        sentiment = l1_result.get('sentiment_score', 0.0)  # -1.0 ~ 1.0
        intent = l1_result.get('intent_category', IntentCategory.SMALL_TALK)
        
        # 验证 intent 是否合法
        if intent not in IntentCategory.ALL_VALUES:
            logger.warning(f"Unknown intent '{intent}', falling back to SMALL_TALK")
            intent = IntentCategory.SMALL_TALK
        
        # 1. 基础推力 (Base Force)
        # 将 sentiment (-1~1) 映射放大到 -10~+10
        base_force = sentiment * 10.0
        
        # 2. 心理学修正: 伤害加倍 (Loss Aversion)
        # 负面情绪的权重是正面的 2 倍
        if base_force < 0:
            base_force *= 2.0
        
        # 3. 意图修正 (Intent Modifiers)
        intent_mod = cls._get_intent_modifier(intent, current_emotion, char_config)
        
        # 4. 计算总推力 (Total Stimulus)
        total_stimulus = base_force + intent_mod
        
        # 5. 应用角色敏感度 (Sensitivity)
        final_delta = total_stimulus * char_config.dependency
        
        # 6. 防刷机制 (Anti-Grind)
        if recent_intents:
            final_delta = cls._apply_anti_grind(final_delta, intent, recent_intents)
        
        logger.info(
            f"PhysicsEngine: sentiment={sentiment:.2f}, intent={intent}, "
            f"base_force={base_force:.1f}, intent_mod={intent_mod}, "
            f"sensitivity={char_config.dependency}, final_delta={final_delta:.1f}"
        )
        
        return int(final_delta)
    
    @classmethod
    def _get_intent_modifier(
        cls,
        intent: str,
        current_emotion: int,
        char_config: CharacterZAxis
    ) -> float:
        """获取意图修正值 (带特殊规则)"""
        
        # 基础修正值
        base_mod = INTENT_STIMULUS_MAP.get(intent, 0)
        
        # COMFORT: 只有当 AI 心情不好时才高效
        if intent == IntentCategory.COMFORT:
            if current_emotion < 0:
                return 20  # 高效回血
            else:
                return 5   # 普通效果
        
        # APOLOGY: 只有生气时道歉才有用，且受自尊心影响
        if intent == IntentCategory.APOLOGY:
            if current_emotion < 0:
                # 自尊心越高，道歉效果越差 (Pride Penalty)
                pride_penalty = char_config.pride * 0.5
                return max(5, 20 - pride_penalty)
            else:
                return 2  # 心情好时道歉没啥用
        
        return base_mod
    
    @classmethod
    def _apply_anti_grind(
        cls,
        delta: float,
        intent: str,
        recent_intents: List[str]
    ) -> float:
        """应用防刷机制"""
        
        # 只对正向意图生效
        if intent not in IntentCategory.POSITIVE_INTENTS:
            return delta
        
        # 检查最近 N 轮是否都是同一个 intent
        if len(recent_intents) >= cls.ANTI_GRIND_THRESHOLD:
            recent = recent_intents[-cls.ANTI_GRIND_THRESHOLD:]
            if recent.count(intent) == cls.ANTI_GRIND_THRESHOLD:
                logger.info(f"Anti-grind triggered: {intent} repeated {cls.ANTI_GRIND_THRESHOLD} times")
                return delta * cls.ANTI_GRIND_MULTIPLIER
        
        return delta
    
    @classmethod
    def update_emotion(
        cls,
        current_emotion: int,
        delta: int
    ) -> int:
        """
        更新情绪值 (应用衰减 + 增量 + 钳位)
        
        Args:
            current_emotion: 当前情绪值
            delta: 本轮增量 (来自 calculate_emotion_delta)
        
        Returns:
            新的情绪值 (-100 ~ +100)
        """
        # 衰减 + 增量
        new_emotion = (current_emotion * cls.DECAY_FACTOR) + delta
        
        # 钳位
        new_emotion = max(cls.EMOTION_MIN, min(cls.EMOTION_MAX, int(new_emotion)))
        
        return new_emotion
    
    @classmethod
    def update_state(
        cls,
        user_state: Dict[str, Any],
        l1_result: Dict[str, Any],
        char_config: CharacterZAxis
    ) -> int:
        """
        更新用户状态的主循环 (每轮对话调用一次)
        
        Args:
            user_state: 用户状态 dict，包含 'emotion' 和 'last_intents'
            l1_result: L1 分析结果
            char_config: 角色 Z 轴配置
            
        Returns:
            新的情绪值
        """
        current_y = user_state.get('emotion', 0)
        last_intents = user_state.get('last_intents', [])
        
        # 1. 计算增量
        delta = cls.calculate_emotion_delta(
            current_emotion=current_y,
            l1_result=l1_result,
            char_config=char_config,
            recent_intents=last_intents
        )
        
        # 2. 应用衰减 + 增量 + 钳位
        new_y = cls.update_emotion(current_y, delta)
        
        logger.info(f"PhysicsEngine.update_state: {current_y} -> {new_y} (delta={delta})")
        
        return new_y


# =============================================================================
# 便捷入口
# =============================================================================

physics_engine = PhysicsEngine()


def calculate_emotion(
    current_emotion: int,
    l1_result: Dict[str, Any],
    character_id: str,
    recent_intents: Optional[List[str]] = None
) -> int:
    """
    便捷函数: 计算新的情绪值
    
    Args:
        current_emotion: 当前情绪值
        l1_result: L1 分析结果
        character_id: 角色 ID
        recent_intents: 最近的 intent 列表
    
    Returns:
        新的情绪值
    """
    char_config = CharacterZAxis.from_character_id(character_id)
    
    delta = PhysicsEngine.calculate_emotion_delta(
        current_emotion=current_emotion,
        l1_result=l1_result,
        char_config=char_config,
        recent_intents=recent_intents
    )
    
    new_emotion = PhysicsEngine.update_emotion(current_emotion, delta)
    
    logger.info(f"Emotion updated: {current_emotion} -> {new_emotion} (delta={delta})")
    
    return new_emotion

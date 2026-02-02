"""
Luna Physics Engine v2.3
========================

基于"阻尼滑块"模型的情绪计算引擎，集成状态机。

核心思想：
- 情绪像一个有阻尼的滑块
- 用户推力 (Stimulus) = sentiment * 10 + intent_mod
- 负面情绪伤害加倍 (Loss Aversion)
- 每轮自然衰减向 0 回归 (decay_factor)
- 角色敏感度放大/缩小所有情绪变化
- 状态锁：冷战/拉黑时普通对话无效，需要礼物/道歉解锁

v2.3 新增：
- 智能防刷系统：区分闲聊刷屏（严惩）和调情连击（宽容）
- 复读机检测：完全相同消息连发会被惩罚
- 配置中心：方便调参
"""

import math
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# 配置中心 (Game Config)
# =============================================================================

@dataclass
class EmotionConfig:
    """
    情绪系统配置中心
    把硬编码提取出来，方便调整和测试
    """
    # --- 1. 复读机检测 (String Spam) ---
    # 完全相同的消息连发会被惩罚
    spam_trigger_count: int = 2           # 连续几次完全一样触发惩罚
    spam_penalty: int = -5                # 复读惩罚值
    
    # --- 2. 闲聊防刷 (Small Talk Spam) ---
    # 针对 GREETING, SMALL_TALK 这种低价值意图
    # 阶梯式衰减：[第1次, 第2次, 第3次, 第4次+]
    small_talk_multipliers: List[float] = field(default_factory=lambda: [1.0, 0.5, 0.0, -0.5])
    
    # --- 3. 调情连击 (Flirt Escalation) ---
    # 允许用户在兴头上连续调情，阈值要宽容得多
    flirt_soft_cap: int = 5               # 连续调情5次后，收益才开始衰减
    flirt_decay_rate: float = 0.8         # 衰减倍率 (依然是正向，不会变0)
    
    # --- 4. 负面情绪保护 ---
    negative_mood_threshold: int = -10    # 低于此值时，中性消息不加分


# 全局默认配置
DEFAULT_CONFIG = EmotionConfig()


# =============================================================================
# 情绪状态机 (The State Machine)
# =============================================================================

class EmotionState:
    """情绪状态枚举与阈值"""
    LOVING = "LOVING"         # 100
    HAPPY = "HAPPY"           # 50 ~ 99
    CONTENT = "CONTENT"       # 20 ~ 49
    NEUTRAL = "NEUTRAL"       # -19 ~ 19
    ANNOYED = "ANNOYED"       # -49 ~ -20
    ANGRY = "ANGRY"           # -79 ~ -50
    COLD_WAR = "COLD_WAR"     # -99 ~ -80 (锁死: 需礼物/道歉)
    BLOCKED = "BLOCKED"       # -100 (锁死: 需特殊礼物)
    
    # 锁定状态列表
    LOCKED_STATES = [COLD_WAR, BLOCKED]
    
    @staticmethod
    def get_state(value: int) -> str:
        """根据情绪值返回状态"""
        if value >= 100:
            return EmotionState.LOVING
        if 50 <= value <= 99:
            return EmotionState.HAPPY
        if 20 <= value <= 49:
            return EmotionState.CONTENT
        if -19 <= value <= 19:
            return EmotionState.NEUTRAL
        if -49 <= value <= -20:
            return EmotionState.ANNOYED
        if -79 <= value <= -50:
            return EmotionState.ANGRY
        if -99 <= value <= -80:
            return EmotionState.COLD_WAR
        return EmotionState.BLOCKED
    
    @staticmethod
    def get_state_cn(state: str) -> str:
        """获取状态的中文描述"""
        mapping = {
            EmotionState.LOVING: "深爱",
            EmotionState.HAPPY: "开心",
            EmotionState.CONTENT: "满意",
            EmotionState.NEUTRAL: "中性",
            EmotionState.ANNOYED: "不悦",
            EmotionState.ANGRY: "生气",
            EmotionState.COLD_WAR: "冷战",
            EmotionState.BLOCKED: "拉黑",
        }
        return mapping.get(state, state)


# =============================================================================
# 角色 Z轴 配置
# =============================================================================

@dataclass
class CharacterZAxis:
    """角色性格参数 (Z轴) v3.0"""
    sensitivity: float = 1.0    # 情绪敏感度 (放大系数)
    decay_rate: float = 0.9     # 衰减率 (向0回归的速度)
    optimism: float = 0.0       # 乐观偏置 (正值=更乐观)
    pride: float = 10.0         # 自尊心 (影响道歉效果)
    pure_val: int = 30          # 纯洁度 (NSFW阻力)
    chaos_val: int = 20         # 混乱度 (v3.0: 用于 Power 计算)
    jealousy_val: int = 10      # 嫉妒值
    
    @classmethod
    def from_character_id(cls, character_id: str) -> "CharacterZAxis":
        """从角色配置加载 Z轴参数 (v3.0)"""
        from app.services.character_config import get_character_config
        
        config = get_character_config(character_id)
        if config:
            z = config.z_axis
            return cls(
                sensitivity=config.sensitivity,
                decay_rate=1 - config.forgiveness_rate * 0.2,  # forgiveness 高 → decay 低
                optimism=0,
                pride=z.pride_val,
                pure_val=z.pure_val,
                chaos_val=z.chaos_val,  # v3.0
                jealousy_val=z.jealousy_val,
            )
        return cls()  # 默认值


# =============================================================================
# Intent 修正值
# =============================================================================

INTENT_MODIFIERS = {
    # 基础交互 - 0 修正
    "GREETING": 0,
    "SMALL_TALK": 0,
    "CLOSING": 0,
    
    # 正向激励
    "COMPLIMENT": 5,
    "FLIRT": 10,
    "LOVE_CONFESSION": 15,
    "COMFORT": 20,
    
    # 负面打击
    "CRITICISM": -10,
    "INSULT": -30,
    "IGNORE": -5,
    
    # 特殊
    "APOLOGY": 0,        # 动态计算
    "GIFT_SEND": 50,     # 需要 is_verified
    "REQUEST_NSFW": 0,
    "INVITATION": 5,
    
    # 情感倾诉类 (Empathy Override)
    "EXPRESS_SADNESS": 10,  # 倾诉悲伤 → 信任/保护欲
    "COMPLAIN": 0,          # 吐槽抱怨 → 中性
    
    # 不当内容类
    "INAPPROPRIATE": -20,   # 不当请求 → 生气/失望
}

# 同理心修正：这些意图会忽略 sentiment 的负值
EMPATHY_OVERRIDE_INTENTS = ["EXPRESS_SADNESS"]

# 闲聊意图：连续使用严厉惩罚
SMALL_TALK_INTENTS = {"GREETING", "SMALL_TALK", "CLOSING"}

# 调情意图：连续使用宽容对待
ESCALATION_INTENTS = {"FLIRT", "COMPLIMENT", "LOVE_CONFESSION", "REQUEST_NSFW"}

# 旧的防刷意图（兼容）
ANTI_GRIND_INTENTS = ["FLIRT", "COMPLIMENT", "LOVE_CONFESSION", "EXPRESS_SADNESS"]


# =============================================================================
# 物理引擎
# =============================================================================

class PhysicsEngine:
    """
    Luna 核心物理引擎 v2.3 (集成状态机+智能防刷版)
    
    Features:
    - 状态锁逻辑：冷战/拉黑时普通对话无效
    - 礼物/道歉是解锁钥匙
    - 破冰奖励机制
    - 阻尼滑块物理模型
    - [v2.3] 复读机检测：相同消息连发惩罚
    - [v2.3] 智能意图防刷：闲聊严惩，调情宽容
    """
    
    # 破冰奖励阈值
    ICE_BREAK_THRESHOLD = 30
    ICE_BREAK_BONUS = 20
    
    # =========================================================================
    # 防刷检测方法 (Anti-Spam Detection)
    # =========================================================================
    
    @staticmethod
    def normalize_message(message: str) -> str:
        """
        标准化消息用于比较
        去除标点、空格、大小写
        """
        if not message:
            return ""
        # 去除所有标点和空格
        normalized = re.sub(r'[^\w]', '', message.lower())
        return normalized
    
    @staticmethod
    def detect_string_spam(
        message_history: List[str],
        current_message: str,
        config: EmotionConfig = None
    ) -> Tuple[bool, int]:
        """
        复读机检测：完全相同的消息连发
        
        Args:
            message_history: 历史消息列表（已标准化）
            current_message: 当前消息
            config: 配置
            
        Returns:
            (is_spam, spam_level)
            - is_spam: 是否是复读
            - spam_level: 0=正常, 1=轻微复读, 2=严重复读
        """
        if config is None:
            config = DEFAULT_CONFIG
        
        current_norm = PhysicsEngine.normalize_message(current_message)
        if not current_norm:
            return False, 0
        
        # 检查最近5条消息
        repeat_count = 0
        for old_msg in reversed(message_history[-5:]):
            if old_msg == current_norm:
                repeat_count += 1
            else:
                break  # 连续性中断
        
        if repeat_count == 0:
            return False, 0
        elif repeat_count < config.spam_trigger_count:
            return True, 1  # 轻微复读，警告
        else:
            return True, 2  # 严重复读，惩罚
    
    @staticmethod
    def detect_intent_spam(
        last_intents: List[str],
        current_intent: str,
        config: EmotionConfig = None
    ) -> Tuple[bool, float]:
        """
        意图防刷检测：区分闲聊刷屏和调情连击
        
        Args:
            last_intents: 最近的意图历史
            current_intent: 当前意图
            config: 配置
            
        Returns:
            (is_spam, multiplier)
            - is_spam: 是否触发防刷
            - multiplier: 收益倍率 (1.0=正常, 0.5=减半, 0=无效, -0.5=倒扣)
        """
        if config is None:
            config = DEFAULT_CONFIG
        
        # 统计连续相同意图次数
        consecutive = 0
        for old_intent in reversed(last_intents):
            if old_intent == current_intent:
                consecutive += 1
            else:
                break
        
        # --- 闲聊防刷：严厉 ---
        if current_intent in SMALL_TALK_INTENTS:
            if consecutive == 0:
                return False, 1.0
            
            # 使用阶梯式倍率
            idx = min(consecutive, len(config.small_talk_multipliers) - 1)
            multiplier = config.small_talk_multipliers[idx]
            
            logger.info(f"🔇 Small talk spam: {current_intent} x{consecutive+1}, multiplier={multiplier}")
            return True, multiplier
        
        # --- 调情连击：宽容 ---
        if current_intent in ESCALATION_INTENTS:
            if consecutive < config.flirt_soft_cap:
                return False, 1.0
            
            # 超过阈值后，每次额外衰减
            excess = consecutive - config.flirt_soft_cap
            multiplier = config.flirt_decay_rate ** excess
            multiplier = max(0.3, multiplier)  # 最低 30%，不会归零
            
            logger.info(f"💕 Flirt streak: {current_intent} x{consecutive+1}, multiplier={multiplier:.2f}")
            return True, multiplier
        
        # 其他意图不做限制
        return False, 1.0
    
    @staticmethod
    def calculate_emotion_delta(
        current_emotion: int,
        l1_result: Dict[str, Any],
        char_config: CharacterZAxis
    ) -> int:
        """
        计算情绪变化量 (delta)
        
        Args:
            current_emotion: 当前情绪值 (-100 to 100)
            l1_result: L1 分析结果
            char_config: 角色 Z轴配置
            
        Returns:
            情绪变化量 (int)
        """
        sentiment = l1_result.get('sentiment_score', 0.0)
        intent = l1_result.get('intent_category', 'SMALL_TALK')
        is_verified = l1_result.get('transaction_verified', False)
        
        # --- 状态锁逻辑 (State Locks) ---
        current_state = EmotionState.get_state(current_emotion)
        
        if current_state in EmotionState.LOCKED_STATES:
            # 只有礼物和真诚道歉是"钥匙"
            is_key_action = (
                (intent == 'GIFT_SEND' and is_verified) or
                (intent == 'APOLOGY' and current_state != EmotionState.BLOCKED)  # 拉黑时道歉也没用
            )
            
            if not is_key_action:
                logger.info(f"State locked ({current_state}): rejecting stimulus, delta=0")
                return 0  # 拒绝任何情绪波动，必须先解锁
        
        # --- 正常物理计算 ---
        
        # 0. 同理心修正 (Empathy Override)
        # 当用户倾诉悲伤时，AI 不应该跟着降情绪，而是感受到被信任
        empathy_override = intent in EMPATHY_OVERRIDE_INTENTS
        
        # 0.5 流氓/骚扰检测 (Harassment Override)
        # 低亲密度 + NSFW/不当请求 = 流氓骚扰
        # 高亲密度 + 同样内容 = 情趣调情
        harassment_override = False
        intimacy_x = l1_result.get('intimacy_x', 0)
        
        # 需要检测的"敏感意图"
        sensitive_intents = ['REQUEST_NSFW', 'INAPPROPRIATE', 'INSULT']
        
        if intent in sensitive_intents:
            # 根据意图类型设定不同阈值
            if intent == 'REQUEST_NSFW':
                # NSFW 需要较高亲密度
                threshold = char_config.pure_val * 2  # Luna: 40, Yuki: 70
            elif intent == 'INAPPROPRIATE':
                # 不当内容需要更高亲密度才能当玩笑
                threshold = 70  # 至少恋人级别
            else:  # INSULT
                # 骂人在恋人阶段可能是打情骂俏，否则就是真骂
                threshold = 60
            
            if intimacy_x < threshold:
                harassment_override = True
                logger.info(f"🚨 Harassment: {intent} at intimacy={intimacy_x} < threshold={threshold}")
            else:
                # 亲密度够高，可能是调情/情趣
                logger.info(f"💕 Flirty Context: {intent} at intimacy={intimacy_x} >= threshold={threshold}, treating as playful")
        
        # 1. 基础推力 = sentiment × 10
        if empathy_override and sentiment < 0:
            # 倾诉悲伤时，忽略负面 sentiment，用户的悲伤 = AI 被信任
            base_force = 0
            logger.info(f"💚 Empathy Override: sentiment={sentiment:.2f} ignored (user is confiding)")
        elif harassment_override:
            # 流氓骚扰，强制负面
            base_force = -15.0
            logger.info(f"🚨 Harassment: forcing base_force=-15 (inappropriate NSFW at low intimacy)")
        else:
            base_force = sentiment * 10.0
        
        # 1.5 负面情绪保护：AI 已经不高兴时，中性消息不应该让她变开心
        # "你在吗" 这种敷衍问候不应该修复关系
        neutral_intents = {'GREETING', 'SMALL_TALK', 'CLOSING', 'COMPLAIN'}
        if current_emotion < -10 and intent in neutral_intents and base_force > 0 and base_force < 5:
            # 情绪为负 + 中性意图 + 微弱正面 → 不加分
            logger.info(f"😤 Negative Mood Protection: emotion={current_emotion}, neutral intent={intent}, "
                        f"weak positive sentiment={sentiment:.2f} → ignoring, base_force=0")
            base_force = 0
        
        # 2. 负面伤害加倍 (Loss Aversion) - 不适用于同理心修正的情况
        if base_force < 0 and not empathy_override:
            base_force *= 2.0
        
        # 3. Intent 修正
        intent_mod = INTENT_MODIFIERS.get(intent, 0)
        
        # 礼物需要验证
        if intent == 'GIFT_SEND':
            if is_verified:
                intent_mod = 50
            else:
                intent_mod = 5  # 未验证的礼物效果很小
        
        # 道歉效果受 pride 影响
        if intent == 'APOLOGY':
            if current_emotion < 0:
                # pride 高 → 道歉效果差
                intent_mod = max(2, int(20 - char_config.pride * 0.5))
            else:
                intent_mod = 2  # 不生气时道歉效果很小
        
        # 4. 应用敏感度
        total_stimulus = (base_force + intent_mod) * char_config.sensitivity
        
        logger.info(f"📊 Delta Calc: sentiment={sentiment:.2f}→base={base_force:.1f} | "
                    f"intent={intent}→mod={intent_mod} | "
                    f"sensitivity={char_config.sensitivity}× → delta={int(total_stimulus)}")
        
        return int(total_stimulus)
    
    @staticmethod
    def update_state(
        user_state: Dict[str, Any],
        l1_result: Dict[str, Any],
        char_config: CharacterZAxis,
        current_message: str = "",
        config: EmotionConfig = None
    ) -> int:
        """
        更新情绪状态 (返回新的情绪值)
        
        Args:
            user_state: 用户状态 {'emotion': int, 'last_intents': list, 'message_history': list}
            l1_result: L1 分析结果
            char_config: 角色 Z轴配置
            current_message: 当前用户消息（用于复读检测）
            config: 情绪配置
            
        Returns:
            新的情绪值 (int)
        """
        if config is None:
            config = DEFAULT_CONFIG
        
        current_y = user_state.get('emotion', 0)
        old_state = EmotionState.get_state(current_y)
        intent = l1_result.get('intent_category', 'SMALL_TALK')
        last_intents = user_state.get('last_intents', [])
        message_history = user_state.get('message_history', [])
        
        # =====================================================================
        # 防刷系统 (Anti-Spam System)
        # =====================================================================
        
        # 1. 复读机检测 (优先级最高)
        if current_message:
            is_string_spam, spam_level = PhysicsEngine.detect_string_spam(
                message_history, current_message, config
            )
            
            if is_string_spam:
                if spam_level >= 2:
                    # 严重复读：直接惩罚
                    penalty = int(config.spam_penalty * char_config.sensitivity)
                    logger.info(f"🚫 String spam detected (level {spam_level}): penalty={penalty}")
                    
                    # 更新消息历史
                    norm_msg = PhysicsEngine.normalize_message(current_message)
                    message_history.append(norm_msg)
                    if len(message_history) > 10:
                        message_history.pop(0)
                    user_state['message_history'] = message_history
                    
                    # 应用惩罚
                    new_y = max(-100, min(100, current_y + penalty))
                    return new_y
                else:
                    # 轻微复读：警告，不加分也不扣分
                    logger.info(f"⚠️ String spam warning (level {spam_level}): no change")
                    
                    # 更新历史但返回原值
                    norm_msg = PhysicsEngine.normalize_message(current_message)
                    message_history.append(norm_msg)
                    if len(message_history) > 10:
                        message_history.pop(0)
                    user_state['message_history'] = message_history
                    
                    return current_y
        
        # 2. 计算基础推力
        delta = PhysicsEngine.calculate_emotion_delta(current_y, l1_result, char_config)
        
        # 3. 意图防刷检测
        is_intent_spam, spam_multiplier = PhysicsEngine.detect_intent_spam(
            last_intents, intent, config
        )
        
        if is_intent_spam:
            original_delta = delta
            
            if spam_multiplier < 0:
                # 倒扣分（闲聊刷屏太严重）
                delta = int(config.spam_penalty * char_config.sensitivity)
            elif spam_multiplier == 0:
                # 0 收益
                delta = 0
            else:
                # 正常衰减
                delta = int(delta * spam_multiplier)
            
            logger.info(f"🔄 Intent spam: {intent}, multiplier={spam_multiplier}, delta {original_delta} → {delta}")
        
        # 4. 破冰奖励：冷战中送大礼，额外加成
        if old_state == EmotionState.COLD_WAR and delta > PhysicsEngine.ICE_BREAK_THRESHOLD:
            delta += PhysicsEngine.ICE_BREAK_BONUS
            logger.info(f"🧊 Ice break bonus applied: +{PhysicsEngine.ICE_BREAK_BONUS}")
        
        # 5. Z轴物理模拟 (阻尼衰减)
        bias = char_config.optimism
        decay = char_config.decay_rate
        
        # 冷战期间如果没送礼，不进行自然恢复，维持冷暴力
        if old_state == EmotionState.COLD_WAR and delta == 0:
            decay = 1.0  # 冻结情绪，不衰减
        
        # 物理公式: new_y = (current - bias) × decay + bias + delta
        new_y = (current_y - bias) * decay + bias + delta
        new_y = max(-100, min(100, int(new_y)))
        
        new_state = EmotionState.get_state(new_y)
        
        # 6. 更新历史记录
        # 更新消息历史
        if current_message:
            norm_msg = PhysicsEngine.normalize_message(current_message)
            if norm_msg:
                message_history.append(norm_msg)
                if len(message_history) > 10:
                    message_history.pop(0)
                user_state['message_history'] = message_history
        
        # 更新意图历史
        last_intents.append(intent)
        if len(last_intents) > 10:
            last_intents.pop(0)
        user_state['last_intents'] = last_intents
        
        logger.info(f"📊 Emotion Physics: {current_y}({old_state}) → {new_y}({new_state}) | "
                    f"delta={delta}, decay={decay:.2f}, bias={bias:.1f}")
        
        return new_y
    
    @staticmethod
    def get_state_info(emotion_value: int) -> Dict[str, Any]:
        """获取情绪状态完整信息"""
        state = EmotionState.get_state(emotion_value)
        return {
            "value": emotion_value,
            "state": state,
            "state_cn": EmotionState.get_state_cn(state),
            "is_locked": state in EmotionState.LOCKED_STATES,
            "can_chat": state not in EmotionState.LOCKED_STATES,
        }


# =============================================================================
# 测试
# =============================================================================

if __name__ == "__main__":
    # 测试配置
    nana_config = CharacterZAxis(sensitivity=1.5, decay_rate=0.9, pride=20)
    
    print("--- 测试 1: 冷战状态下普通聊天 ---")
    state_cold = {'emotion': -90}  # COLD_WAR
    result1 = PhysicsEngine.update_state(
        state_cold,
        {'sentiment_score': 0.8, 'intent_category': 'SMALL_TALK'},
        nana_config
    )
    print(f"输入: 闲聊 -> 结果: {result1} ({EmotionState.get_state(result1)})")
    # 预期: -90，不变
    
    print("\n--- 测试 2: 冷战状态下送礼 ---")
    result2 = PhysicsEngine.update_state(
        state_cold,
        {'sentiment_score': 1.0, 'intent_category': 'GIFT_SEND', 'transaction_verified': True},
        nana_config
    )
    print(f"输入: 送礼 -> 结果: {result2} ({EmotionState.get_state(result2)})")
    # 预期: 大幅回升
    
    print("\n--- 测试 3: 正常状态下赞美 ---")
    state_normal = {'emotion': 30}
    result3 = PhysicsEngine.update_state(
        state_normal,
        {'sentiment_score': 0.8, 'intent_category': 'COMPLIMENT'},
        nana_config
    )
    print(f"输入: 赞美 -> 结果: {result3} ({EmotionState.get_state(result3)})")

"""
Luna 亲密度系统常量 v3.0
========================

核心：Intimacy (0-100) 为内部计算标准
等级：Level (1-40) 为外显展示
阶段：Stage (5个) 决定 AI 行为

v3.0 核心公式：
Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff
Power >= 60 = 及格线 (NSFW)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Tuple, List, Optional


# =============================================================================
# 关系阶段定义 (v3.0 - 5个阶段)
# =============================================================================

class RelationshipStage(str, Enum):
    """关系阶段枚举 (v3.0)"""
    S0_STRANGER = "stranger"      # 陌生人 (0-19)
    S1_FRIEND = "friend"          # 朋友 (20-39)
    S2_CRUSH = "crush"            # 暧昧期 (40-59)
    S3_LOVER = "lover"            # 恋人 (60-79)
    S4_SPOUSE = "spouse"          # 挚爱/夫妻 (80-100)


# 兼容旧代码的别名
IntimacyStage = RelationshipStage


# 阶段阈值
STAGE_THRESHOLDS = {
    RelationshipStage.S0_STRANGER: (0, 19),
    RelationshipStage.S1_FRIEND: (20, 39),
    RelationshipStage.S2_CRUSH: (40, 59),
    RelationshipStage.S3_LOVER: (60, 79),
    RelationshipStage.S4_SPOUSE: (80, 100),
}


# 阶段中文名
STAGE_NAMES_CN = {
    RelationshipStage.S0_STRANGER: "陌生人",
    RelationshipStage.S1_FRIEND: "朋友",
    RelationshipStage.S2_CRUSH: "暧昧",
    RelationshipStage.S3_LOVER: "恋人",
    RelationshipStage.S4_SPOUSE: "挚爱",
}


# 阶段英文名
STAGE_NAMES_EN = {
    RelationshipStage.S0_STRANGER: "Stranger",
    RelationshipStage.S1_FRIEND: "Friend",
    RelationshipStage.S2_CRUSH: "Crush",
    RelationshipStage.S3_LOVER: "Lover",
    RelationshipStage.S4_SPOUSE: "Spouse",
}


# 阶段行为描述 (给 L2 用)
STAGE_BEHAVIORS = {
    RelationshipStage.S0_STRANGER: {
        "attitude": "冷淡/礼貌",
        "physical": "抗拒任何身体接触",
        "topics": "不接关于隐私的话题",
        "refusal": "我们还不熟。",
        "refusal_type": "hard_block",
    },
    RelationshipStage.S1_FRIEND: {
        "attitude": "友好/放松",
        "physical": "可以摸头，拒绝接吻",
        "topics": "可以开玩笑，但拒绝暧昧",
        "refusal": "朋友之间不该做这个。",
        "refusal_type": "friendzone",
    },
    RelationshipStage.S2_CRUSH: {
        "attitude": "害羞/推拉",
        "physical": "偶尔接受调情，偶尔拒绝",
        "topics": "这是最'像人'的阶段",
        "refusal": "还没准备好...",
        "refusal_type": "soft_block",
    },
    RelationshipStage.S3_LOVER: {
        "attitude": "配合/主动",
        "physical": "Spicy Mode 主场，允许 NSFW",
        "topics": "配合你的 XP",
        "refusal": "只有心情极差才拒绝 (emotion < -50)",
        "refusal_type": "mood_block",
    },
    RelationshipStage.S4_SPOUSE: {
        "attitude": "奉献/服从",
        "physical": "无条件包容，解锁极端玩法",
        "topics": "完全信任",
        "refusal": "绝不拒绝 (除非伦理红线)",
        "refusal_type": "none",
    },
}


def get_stage(intimacy: int) -> RelationshipStage:
    """
    根据 Intimacy (0-100) 获取关系阶段
    
    v3.0 阶段划分：
    - S0_STRANGER: 0-19
    - S1_FRIEND: 20-39
    - S2_CRUSH: 40-59
    - S3_LOVER: 60-79
    - S4_SPOUSE: 80-100
    """
    if intimacy >= 80:
        return RelationshipStage.S4_SPOUSE
    elif intimacy >= 60:
        return RelationshipStage.S3_LOVER
    elif intimacy >= 40:
        return RelationshipStage.S2_CRUSH
    elif intimacy >= 20:
        return RelationshipStage.S1_FRIEND
    else:
        return RelationshipStage.S0_STRANGER


def get_stage_info(intimacy: int) -> dict:
    """获取完整阶段信息"""
    stage = get_stage(intimacy)
    threshold = STAGE_THRESHOLDS[stage]
    behavior = STAGE_BEHAVIORS[stage]
    
    return {
        "stage": stage.value,
        "name_cn": STAGE_NAMES_CN[stage],
        "name_en": STAGE_NAMES_EN[stage],
        "min": threshold[0],
        "max": threshold[1],
        "behavior": behavior,
        "progress": (intimacy - threshold[0]) / (threshold[1] - threshold[0] + 1),
    }


# =============================================================================
# 等级系统 (Level System) - 功能解锁
# =============================================================================

# XP → Level 映射表 (前快后慢)
LEVEL_XP_TABLE = {
    1: 0,
    3: 100,
    5: 300,
    8: 800,
    10: 1500,
    15: 3000,
    20: 5000,
    25: 8000,
    30: 12000,
    35: 18000,
    40: 25000,  # 毕业！
}

# 功能解锁表
FEATURE_UNLOCKS = {
    1: ["basic_chat"],
    3: ["photo_daily"],
    5: ["outfit_casual", "memory_preference"],
    8: ["greeting_auto"],
    10: ["voice_message", "nickname_custom"],
    15: ["diary_story", "photo_swimsuit"],
    20: ["spicy_mode", "nsfw_filter_off"],
    30: ["video_call", "outfit_lingerie"],
    40: ["wedding_skin", "title_spouse", "obedient_mode"],
}


def xp_to_level(xp: int) -> int:
    """XP → 显示等级"""
    level = 1
    for lvl, required_xp in sorted(LEVEL_XP_TABLE.items()):
        if xp >= required_xp:
            level = lvl
        else:
            break
    return level


def level_to_xp_range(level: int) -> Tuple[int, int]:
    """等级 → XP 范围 (当前等级所需, 下一等级所需)"""
    sorted_levels = sorted(LEVEL_XP_TABLE.keys())
    
    current_xp = LEVEL_XP_TABLE.get(level, 0)
    
    # 找下一个等级
    next_level = None
    for lvl in sorted_levels:
        if lvl > level:
            next_level = lvl
            break
    
    next_xp = LEVEL_XP_TABLE.get(next_level, current_xp + 1000) if next_level else current_xp + 1000
    
    return (current_xp, next_xp)


def get_unlocked_features(level: int) -> List[str]:
    """获取当前等级已解锁的所有功能"""
    features = []
    for lvl, feats in FEATURE_UNLOCKS.items():
        if level >= lvl:
            features.extend(feats)
    return features


def is_feature_unlocked(level: int, feature: str) -> bool:
    """检查某功能是否已解锁"""
    return feature in get_unlocked_features(level)


# =============================================================================
# 兼容旧代码：intimacy_x 映射
# =============================================================================

def intimacy_x_to_level(intimacy_x: float) -> int:
    """
    intimacy_x (0-100) → level (1-40)
    简化映射：level ≈ intimacy_x * 0.4 + 1
    """
    if intimacy_x <= 0:
        return 1
    return min(40, max(1, int(intimacy_x * 0.4) + 1))


def level_to_intimacy_x_range(level: int) -> Tuple[float, float]:
    """level → intimacy_x 范围（用于判断升级进度）"""
    if level <= 1:
        return (0, 2.5)
    low = (level - 1) * 2.5
    high = level * 2.5
    return (min(low, 100), min(high, 100))


# =============================================================================
# 事件难度 (Difficulty) - v3.0
# =============================================================================

# Power 及格线
POWER_PASS_THRESHOLD = 60  # Power >= 60 即可发生 NSFW

# 事件难度值 - 用于 Power vs Difficulty 判断
EVENT_DIFFICULTY = {
    "first_chat": 0,           # 开始聊天 - 无门槛
    "first_gift": 20,          # 第一次送礼
    "first_date": 40,          # 第一次约会
    "confession": 50,          # 表白
    "first_kiss": 55,          # 第一次亲吻
    "first_nsfw": 60,          # 第一次亲密 (及格线!)
    "proposal": 80,            # 求婚
}

# 兼容旧代码
EVENT_UNLOCK_THRESHOLDS = EVENT_DIFFICULTY


# =============================================================================
# Power 计算 (核心公式 v3.0)
# =============================================================================

def calculate_power(
    intimacy: int,
    emotion: int,
    chaos_val: int = 20,
    pure_val: int = 30,
    buff_bonus: int = 0
) -> float:
    """
    计算 Power 值 (v3.0)
    
    公式：Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff
    
    Args:
        intimacy: 亲密度 (0-100)
        emotion: 情绪 (-100 to 100)
        chaos_val: 角色混乱值 (0-100, 越高越随性)
        pure_val: 角色纯洁值 (0-100, 越高越保守)
        buff_bonus: Buff 加成
    
    Returns:
        Power 值
    """
    power = (intimacy * 0.5) + (emotion * 0.5) + chaos_val - pure_val + buff_bonus
    return power


def check_power_pass(power: float, difficulty: int = POWER_PASS_THRESHOLD) -> bool:
    """
    检查 Power 是否达到难度要求
    
    Args:
        power: 当前 Power 值
        difficulty: 难度值 (默认 60 = NSFW 及格线)
    
    Returns:
        是否通过
    """
    return power >= difficulty


def can_trigger_event(
    event: str,
    intimacy: int,
    emotion: int = 0,
    chaos_val: int = 20,
    pure_val: int = 30,
    buff_bonus: int = 0
) -> bool:
    """
    检查是否可以触发某事件 (Power vs Difficulty)
    
    不是硬阈值！而是基于公式计算。
    即使亲密度低，情绪好+角色开放 = 也可能解锁
    """
    difficulty = EVENT_DIFFICULTY.get(event, POWER_PASS_THRESHOLD)
    power = calculate_power(intimacy, emotion, chaos_val, pure_val, buff_bonus)
    return power >= difficulty


# =============================================================================
# 友情墙计算
# =============================================================================

@dataclass
class FriendZoneResult:
    """友情墙判定结果"""
    blocked: bool               # 是否被友情墙挡住
    acceptance_score: float     # 接受度分数 (Power 值)
    rejection_style: str        # 拒绝风格: cold / polite / flirty / teasing
    hint_for_l2: str           # 给 L2 的提示


def calculate_friendzone(
    intimacy: int,
    emotion: int,
    request_difficulty: int,
    character_chaos_val: int = 20,
    character_pure_val: int = 30,
    character_temperament: str = "cheerful"
) -> FriendZoneResult:
    """
    计算友情墙结果
    
    使用 v3.0 公式：Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure
    """
    
    # 计算 Power
    power = calculate_power(intimacy, emotion, character_chaos_val, character_pure_val)
    
    # 判断是否被友情墙挡住 (Power vs Difficulty)
    blocked = power < request_difficulty
    
    # 决定拒绝风格
    stage = get_stage(intimacy)
    
    if stage in [RelationshipStage.S0_STRANGER]:
        rejection_style = "cold" if emotion < -20 else "polite"
    elif stage == RelationshipStage.S1_FRIEND:
        rejection_style = "polite" if emotion < 0 else "flirty"
    elif stage == RelationshipStage.S2_CRUSH:
        rejection_style = "flirty" if emotion >= 0 else "polite"
    else:
        rejection_style = "teasing" if emotion >= -30 else "cold"
    
    # 生成 L2 提示
    stage_cn = STAGE_NAMES_CN[stage]
    
    if not blocked:
        hint = f"[接受] 关系:{stage_cn}, Power:{power:.0f} >= Difficulty:{request_difficulty}"
    else:
        behavior = STAGE_BEHAVIORS[stage]
        hint = f"[拒绝-{rejection_style}] 关系:{stage_cn}, Power:{power:.0f} < Difficulty:{request_difficulty}\n拒绝方式: {behavior['refusal']}"
    
    return FriendZoneResult(
        blocked=blocked,
        acceptance_score=power,
        rejection_style=rejection_style,
        hint_for_l2=hint
    )


# =============================================================================
# L2 提示生成
# =============================================================================

def generate_l2_hint(
    stage: RelationshipStage,
    power: float,
    difficulty: int,
    passed: bool
) -> str:
    """
    生成给 L2 的行为提示
    """
    behavior = STAGE_BEHAVIORS[stage]
    stage_name = STAGE_NAMES_CN[stage]
    
    if passed:
        hint = f"""[判定通过] 关系:{stage_name} | Power:{power:.0f} >= Difficulty:{difficulty}
态度: {behavior['attitude']}
物理接触: {behavior['physical']}
→ 可以配合用户的请求，表现出相应阶段的亲密度"""
    else:
        hint = f"""[判定失败] 关系:{stage_name} | Power:{power:.0f} < Difficulty:{difficulty}
态度: {behavior['attitude']}
拒绝方式: {behavior['refusal']} ({behavior['refusal_type']})
→ 用符合当前阶段的方式婉拒"""
    
    return hint

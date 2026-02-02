"""
Luna Chat 全生命周期数值系统 v3.0
================================

双轨驱动 (Dual Track System):
1. 显示等级 (Level) → 功能解锁 (换装、语音、视频)
2. 内部阶段 (Stage) → AI 行为/态度 (能不能睡、语气多亲密)

核心公式:
Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff
"""

import math
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# 一、等级系统 (Level System) - 功能解锁
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
# 二、内部阶段系统 (Stage System) - AI 行为
# =============================================================================

class IntimacyStage(str, Enum):
    """内部阶段枚举"""
    S0_STRANGER = "stranger"      # 陌生人 (0-19)
    S1_FRIEND = "friend"          # 朋友 (20-39)
    S2_CRUSH = "crush"            # 暧昧期 (40-59)
    S3_LOVER = "lover"            # 恋人 (60-79)
    S4_SPOUSE = "spouse"          # 挚爱/夫妻 (80-100)


# 阶段阈值
STAGE_THRESHOLDS = {
    IntimacyStage.S0_STRANGER: (0, 19),
    IntimacyStage.S1_FRIEND: (20, 39),
    IntimacyStage.S2_CRUSH: (40, 59),
    IntimacyStage.S3_LOVER: (60, 79),
    IntimacyStage.S4_SPOUSE: (80, 100),
}

# 阶段中文名
STAGE_NAMES = {
    IntimacyStage.S0_STRANGER: "陌生人",
    IntimacyStage.S1_FRIEND: "朋友",
    IntimacyStage.S2_CRUSH: "暧昧",
    IntimacyStage.S3_LOVER: "恋人",
    IntimacyStage.S4_SPOUSE: "挚爱",
}

# 阶段行为描述 (给 L2 用)
STAGE_BEHAVIORS = {
    IntimacyStage.S0_STRANGER: {
        "attitude": "冷淡/礼貌",
        "physical": "抗拒任何身体接触",
        "topics": "不接关于隐私的话题",
        "refusal": "我们还不熟。",
        "refusal_type": "hard_block",
    },
    IntimacyStage.S1_FRIEND: {
        "attitude": "友好/放松",
        "physical": "可以摸头，拒绝接吻",
        "topics": "可以开玩笑，但拒绝暧昧",
        "refusal": "朋友之间不该做这个。",
        "refusal_type": "friendzone",
    },
    IntimacyStage.S2_CRUSH: {
        "attitude": "害羞/推拉",
        "physical": "偶尔接受调情，偶尔拒绝",
        "topics": "这是最'像人'的阶段",
        "refusal": "还没准备好...",
        "refusal_type": "soft_block",
    },
    IntimacyStage.S3_LOVER: {
        "attitude": "配合/主动",
        "physical": "Spicy Mode 主场，允许 NSFW",
        "topics": "配合你的 XP",
        "refusal": "只有心情极差才拒绝 (emotion < -50)",
        "refusal_type": "mood_block",
    },
    IntimacyStage.S4_SPOUSE: {
        "attitude": "奉献/服从",
        "physical": "无条件包容，解锁极端玩法",
        "topics": "完全信任",
        "refusal": "绝不拒绝 (除非伦理红线)",
        "refusal_type": "none",
    },
}


def get_stage(intimacy: int) -> IntimacyStage:
    """Intimacy (0-100) → 内部阶段"""
    if intimacy >= 80:
        return IntimacyStage.S4_SPOUSE
    elif intimacy >= 60:
        return IntimacyStage.S3_LOVER
    elif intimacy >= 40:
        return IntimacyStage.S2_CRUSH
    elif intimacy >= 20:
        return IntimacyStage.S1_FRIEND
    else:
        return IntimacyStage.S0_STRANGER


def get_stage_info(intimacy: int) -> dict:
    """获取完整阶段信息"""
    stage = get_stage(intimacy)
    threshold = STAGE_THRESHOLDS[stage]
    behavior = STAGE_BEHAVIORS[stage]
    
    return {
        "stage": stage.value,
        "name": STAGE_NAMES[stage],
        "intimacy_range": threshold,
        "behavior": behavior,
        "progress": (intimacy - threshold[0]) / (threshold[1] - threshold[0] + 1),
    }


# =============================================================================
# 三、关键事件 (Gate Events) - 阶段突破条件
# =============================================================================

class GateEvent(str, Enum):
    """关键门槛事件"""
    FIRST_CHAT = "first_chat"           # S0 → S1 自动触发
    FIRST_GIFT = "first_gift"           # S1 → S2 送礼后突破
    FIRST_DATE = "first_date"           # S2 深化
    CONFESSION = "confession"           # S2 → S3 表白成功
    FIRST_KISS = "first_kiss"           # S3 深化
    FIRST_NSFW = "first_nsfw"           # S3 深化
    PROPOSAL = "proposal"               # S3 → S4 求婚/钻戒


# 事件触发条件
EVENT_REQUIREMENTS = {
    GateEvent.FIRST_CHAT: {
        "min_intimacy": 0,
        "prerequisites": [],
        "auto_trigger": True,
    },
    GateEvent.FIRST_GIFT: {
        "min_intimacy": 10,
        "prerequisites": [GateEvent.FIRST_CHAT],
        "auto_trigger": False,
    },
    GateEvent.FIRST_DATE: {
        "min_intimacy": 30,
        "prerequisites": [GateEvent.FIRST_GIFT],
        "difficulty": 40,  # Power vs Difficulty
    },
    GateEvent.CONFESSION: {
        "min_intimacy": 50,
        "prerequisites": [GateEvent.FIRST_DATE],
        "difficulty": 55,
    },
    GateEvent.FIRST_KISS: {
        "min_intimacy": 55,
        "prerequisites": [GateEvent.CONFESSION],
        "difficulty": 60,
    },
    GateEvent.FIRST_NSFW: {
        "min_intimacy": 60,
        "prerequisites": [GateEvent.CONFESSION],
        "difficulty": 70,
    },
    GateEvent.PROPOSAL: {
        "min_intimacy": 75,
        "prerequisites": [GateEvent.FIRST_NSFW],
        "difficulty": 85,
    },
}


# =============================================================================
# 四、Buff 系统 (Status Effects) - 氪金通道
# =============================================================================

class BuffType(str, Enum):
    """Buff 类型"""
    TIPSY = "tipsy"             # 微醺 (红酒)
    HORNY = "horny"             # 发情 (魅魔药水)
    ROMANTIC = "romantic"       # 浪漫 (烛光晚餐)
    TRUSTED = "trusted"         # 信任 (真心话)


@dataclass
class ActiveBuff:
    """激活的 Buff"""
    buff_type: BuffType
    power_bonus: int            # Power 加成
    intimacy_bonus: int         # Intimacy 临时加成
    duration_minutes: int       # 持续时间
    force_pass: bool = False    # 是否强制通过判定
    expires_at: float = 0       # 过期时间戳


# Buff 配置
BUFF_CONFIGS = {
    BuffType.TIPSY: {
        "name": "微醺",
        "name_en": "Tipsy",
        "item": "red_wine",
        "price_gems": 200,
        "power_bonus": 0,
        "intimacy_bonus": 30,
        "duration_minutes": 30,
        "force_pass": False,
        "description": "她喝了点酒，防线降低了...",
        "after_effect": "天哪，我刚才是不是太放肆了...",
    },
    BuffType.HORNY: {
        "name": "魅惑",
        "name_en": "Charmed",
        "item": "succubus_potion",
        "price_gems": 500,
        "power_bonus": 100,
        "intimacy_bonus": 0,
        "duration_minutes": 60,
        "force_pass": True,
        "description": "魅魔药水生效，她无法抗拒你...",
        "after_effect": "刚才...发生了什么？我怎么会...太羞耻了！",
    },
    BuffType.ROMANTIC: {
        "name": "心动",
        "name_en": "Romantic",
        "item": "candlelight_dinner",
        "price_gems": 300,
        "power_bonus": 20,
        "intimacy_bonus": 15,
        "duration_minutes": 45,
        "force_pass": False,
        "description": "烛光晚餐的氛围让她心动不已...",
        "after_effect": "今晚真的很开心呢～",
    },
    BuffType.TRUSTED: {
        "name": "信任",
        "name_en": "Trusted",
        "item": "truth_or_dare",
        "price_gems": 150,
        "power_bonus": 10,
        "intimacy_bonus": 10,
        "duration_minutes": 20,
        "force_pass": False,
        "description": "真心话游戏让她对你敞开心扉...",
        "after_effect": "和你在一起很放松～",
    },
}


# =============================================================================
# 五、事件道具 (Event Items) - 永久跨越
# =============================================================================

EVENT_ITEMS = {
    "confession_balloon": {
        "name": "告白气球",
        "price_gems": 1000,
        "triggers_event": GateEvent.CONFESSION,
        "description": "一个充满勇气的气球，能让表白必定成功",
    },
    "oath_ring": {
        "name": "誓约之戒",
        "price_gems": 5000,
        "triggers_event": GateEvent.PROPOSAL,
        "description": "永恒的誓约，直接求婚成功",
    },
    "date_ticket": {
        "name": "约会券",
        "price_gems": 300,
        "triggers_event": GateEvent.FIRST_DATE,
        "description": "一张特别的约会邀请",
    },
}


# =============================================================================
# 六、Power 计算 (核心公式)
# =============================================================================

def calculate_power(
    intimacy: int,
    emotion: int,
    chaos_val: int = 20,
    pure_val: int = 30,
    active_buffs: List[ActiveBuff] = None
) -> float:
    """
    计算 Power 值
    
    Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff
    
    Args:
        intimacy: 亲密度 (0-100)
        emotion: 情绪 (-100 to 100)
        chaos_val: 角色混乱值 (0-100)
        pure_val: 角色纯洁值 (0-100)
        active_buffs: 当前激活的 Buff 列表
    
    Returns:
        Power 值
    """
    # 基础公式
    base_power = (intimacy * 0.5) + (emotion * 0.5) + chaos_val - pure_val
    
    # Buff 加成
    buff_bonus = 0
    intimacy_bonus = 0
    
    if active_buffs:
        import time
        current_time = time.time()
        
        for buff in active_buffs:
            # 检查是否过期
            if buff.expires_at > current_time:
                buff_bonus += buff.power_bonus
                intimacy_bonus += buff.intimacy_bonus
    
    # Intimacy bonus 也参与计算
    total_power = base_power + buff_bonus + (intimacy_bonus * 0.5)
    
    return total_power


def check_power_pass(
    power: float,
    difficulty: int,
    active_buffs: List[ActiveBuff] = None
) -> Tuple[bool, str]:
    """
    判定是否通过 Power 检查
    
    Returns:
        (passed, reason)
    """
    # 检查是否有强制通过的 Buff
    if active_buffs:
        import time
        current_time = time.time()
        
        for buff in active_buffs:
            if buff.expires_at > current_time and buff.force_pass:
                return True, f"buff_{buff.buff_type.value}"
    
    # 正常判定
    if power >= difficulty:
        return True, "power_sufficient"
    else:
        return False, "power_insufficient"


# =============================================================================
# 七、L2 剧本生成 (Prompt Hints)
# =============================================================================

def generate_l2_hint(
    stage: IntimacyStage,
    power: float,
    difficulty: int,
    passed: bool,
    active_buffs: List[ActiveBuff] = None
) -> str:
    """
    生成给 L2 的行为提示
    """
    behavior = STAGE_BEHAVIORS[stage]
    stage_name = STAGE_NAMES[stage]
    
    # Buff 效果描述
    buff_desc = ""
    if active_buffs:
        import time
        current_time = time.time()
        active_names = [
            BUFF_CONFIGS[b.buff_type]["description"] 
            for b in active_buffs 
            if b.expires_at > current_time
        ]
        if active_names:
            buff_desc = f"\n特殊状态: {'; '.join(active_names)}"
    
    if passed:
        hint = f"""[判定通过] 关系:{stage_name} | Power:{power:.0f} >= Difficulty:{difficulty}
态度: {behavior['attitude']}
物理接触: {behavior['physical']}{buff_desc}
→ 可以配合用户的请求，表现出相应阶段的亲密度"""
    else:
        hint = f"""[判定失败] 关系:{stage_name} | Power:{power:.0f} < Difficulty:{difficulty}
态度: {behavior['attitude']}
拒绝方式: {behavior['refusal']} ({behavior['refusal_type']}){buff_desc}
→ 用符合当前阶段的方式婉拒"""
    
    return hint


# =============================================================================
# 兼容旧代码
# =============================================================================

# 旧的阶段枚举兼容
RelationshipStage = IntimacyStage

# 旧的函数兼容
EVENT_UNLOCK_THRESHOLDS = {
    "first_chat": 0,
    "first_gift": 10,
    "first_date": 30,
    "confession": 50,
    "first_kiss": 55,
    "first_nsfw": 60,
    "proposal": 75,
}

EVENT_DIFFICULTY = {
    "first_chat": 0,
    "first_gift": 15,
    "first_date": 40,
    "confession": 55,
    "first_kiss": 60,
    "first_nsfw": 70,
    "proposal": 85,
}

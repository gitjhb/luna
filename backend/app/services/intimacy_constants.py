"""
Luna 亲密度系统常量
==================

核心：intimacy_x (0-100) 为内部计算标准
等级：level (1-50+) 为外显展示，指数映射
"""

from enum import Enum
from dataclasses import dataclass
from typing import Tuple


# =============================================================================
# 关系阶段定义
# =============================================================================

class RelationshipStage(str, Enum):
    """关系阶段枚举"""
    STRANGER = "stranger"           # 陌生人
    ACQUAINTANCE = "acquaintance"   # 熟人
    FRIEND = "friend"               # 朋友
    CLOSE_FRIEND = "close_friend"   # 好友/暧昧
    ROMANTIC = "romantic"           # 恋人
    LOVER = "lover"                 # 深爱


# intimacy_x 阈值
STAGE_THRESHOLDS = {
    RelationshipStage.STRANGER: (0, 19),
    RelationshipStage.ACQUAINTANCE: (20, 39),
    RelationshipStage.FRIEND: (40, 59),
    RelationshipStage.CLOSE_FRIEND: (60, 79),
    RelationshipStage.ROMANTIC: (80, 89),
    RelationshipStage.LOVER: (90, 100),
}

# 阶段中文名
STAGE_NAMES_CN = {
    RelationshipStage.STRANGER: "陌生人",
    RelationshipStage.ACQUAINTANCE: "熟人",
    RelationshipStage.FRIEND: "朋友",
    RelationshipStage.CLOSE_FRIEND: "暧昧",
    RelationshipStage.ROMANTIC: "恋人",
    RelationshipStage.LOVER: "深爱",
}

# 阶段英文名
STAGE_NAMES_EN = {
    RelationshipStage.STRANGER: "Stranger",
    RelationshipStage.ACQUAINTANCE: "Acquaintance",
    RelationshipStage.FRIEND: "Friend",
    RelationshipStage.CLOSE_FRIEND: "Close Friend",
    RelationshipStage.ROMANTIC: "Romantic Partner",
    RelationshipStage.LOVER: "Lover",
}


def get_stage(intimacy_x: float) -> RelationshipStage:
    """根据 intimacy_x 获取关系阶段"""
    if intimacy_x >= 90:
        return RelationshipStage.LOVER
    elif intimacy_x >= 80:
        return RelationshipStage.ROMANTIC
    elif intimacy_x >= 60:
        return RelationshipStage.CLOSE_FRIEND
    elif intimacy_x >= 40:
        return RelationshipStage.FRIEND
    elif intimacy_x >= 20:
        return RelationshipStage.ACQUAINTANCE
    else:
        return RelationshipStage.STRANGER


def get_stage_info(intimacy_x: float) -> dict:
    """获取完整阶段信息"""
    stage = get_stage(intimacy_x)
    threshold = STAGE_THRESHOLDS[stage]
    return {
        "stage": stage.value,
        "name_cn": STAGE_NAMES_CN[stage],
        "name_en": STAGE_NAMES_EN[stage],
        "min": threshold[0],
        "max": threshold[1],
        "progress": (intimacy_x - threshold[0]) / (threshold[1] - threshold[0] + 1),
    }


# =============================================================================
# 等级映射 (对外展示)
# =============================================================================

def intimacy_x_to_level(intimacy_x: float) -> int:
    """
    intimacy_x (0-100) → level (1-50)
    
    指数映射：前期快，后期慢
    - 0-40 x → 1-25 level (每1.6点升1级)
    - 40-100 x → 25-50 level (每2.4点升1级)
    """
    if intimacy_x <= 0:
        return 1
    elif intimacy_x <= 40:
        # 前期快：每1.6点升1级
        return min(25, int(intimacy_x / 1.6) + 1)
    else:
        # 后期慢：每2.4点升1级
        return min(50, 25 + int((intimacy_x - 40) / 2.4))


def level_to_intimacy_x_range(level: int) -> Tuple[float, float]:
    """level → intimacy_x 范围（用于判断升级进度）"""
    if level <= 1:
        return (0, 1.6)
    elif level <= 25:
        low = (level - 1) * 1.6
        high = level * 1.6
        return (low, high)
    else:
        low = 40 + (level - 25) * 2.4
        high = 40 + (level - 24) * 2.4
        return (min(low, 100), min(high, 100))


# =============================================================================
# 事件解锁阈值
# =============================================================================

EVENT_UNLOCK_THRESHOLDS = {
    "first_chat": 0,           # 开始聊天
    "first_compliment": 10,    # 第一次夸奖
    "first_gift": 20,          # 第一次送礼
    "first_date": 40,          # 第一次约会（朋友阶段）
    "first_confession": 60,    # 第一次表白（暧昧阶段）
    "first_kiss": 80,          # 第一次亲吻（恋人阶段）
    "first_nsfw": 90,          # 第一次亲密（深爱阶段）
}


def can_unlock_event(event: str, intimacy_x: float) -> bool:
    """检查是否可以解锁某事件"""
    threshold = EVENT_UNLOCK_THRESHOLDS.get(event, 100)
    return intimacy_x >= threshold


# =============================================================================
# 友情墙计算（和角色相关）
# =============================================================================

@dataclass
class FriendZoneResult:
    """友情墙判定结果"""
    blocked: bool               # 是否被友情墙挡住
    acceptance_score: float     # 接受度分数 (0-100, 越高越可能接受)
    rejection_style: str        # 拒绝风格: cold / polite / flirty / teasing
    hint_for_l2: str           # 给 L2 的提示


def calculate_friendzone(
    intimacy_x: float,
    emotion: int,
    request_difficulty: int,
    character_pure_val: int = 30,
    character_temperament: str = "cheerful"
) -> FriendZoneResult:
    """
    计算友情墙结果
    
    Args:
        intimacy_x: 亲密度 (0-100)
        emotion: 当前情绪 (-100 to 100)
        request_difficulty: 请求难度 (0-100)
        character_pure_val: 角色纯洁度 (0-100, 越高越保守)
        character_temperament: 角色性格 (calm/sensitive/tsundere/cheerful)
    
    Returns:
        FriendZoneResult
    """
    
    # 1. 计算基础接受度
    # 亲密度越高，接受度越高
    base_acceptance = intimacy_x
    
    # 2. 情绪修正
    # 正情绪加分，负情绪减分
    emotion_modifier = emotion * 0.3  # -30 to +30
    
    # 3. 角色纯洁度修正
    # 纯洁度高的角色，接受度下降
    pure_modifier = (50 - character_pure_val) * 0.5  # -25 to +25
    
    # 4. 计算最终接受度
    acceptance_score = base_acceptance + emotion_modifier + pure_modifier
    acceptance_score = max(0, min(100, acceptance_score))
    
    # 5. 判断是否被友情墙挡住
    blocked = acceptance_score < request_difficulty
    
    # 6. 决定拒绝风格
    stage = get_stage(intimacy_x)
    
    if stage in [RelationshipStage.STRANGER, RelationshipStage.ACQUAINTANCE]:
        # 陌生人/熟人：冷淡或礼貌
        if emotion < -20:
            rejection_style = "cold"
        else:
            rejection_style = "polite"
    elif stage == RelationshipStage.FRIEND:
        # 朋友：礼貌或微暧昧
        if emotion < 0:
            rejection_style = "polite"
        else:
            rejection_style = "flirty"
    else:
        # 暧昧/恋人：调情式拒绝
        if emotion < -30:
            rejection_style = "cold"
        else:
            rejection_style = "teasing"
    
    # 7. 生成 L2 提示
    hint_for_l2 = _generate_l2_hint(
        blocked, acceptance_score, rejection_style, 
        stage, emotion, character_temperament
    )
    
    return FriendZoneResult(
        blocked=blocked,
        acceptance_score=acceptance_score,
        rejection_style=rejection_style,
        hint_for_l2=hint_for_l2
    )


def _generate_l2_hint(
    blocked: bool,
    acceptance_score: float,
    rejection_style: str,
    stage: RelationshipStage,
    emotion: int,
    temperament: str
) -> str:
    """生成给 L2 的剧本提示"""
    
    stage_cn = STAGE_NAMES_CN[stage]
    
    if not blocked:
        return f"[接受] 关系阶段:{stage_cn}, 接受度:{acceptance_score:.0f}/100, 可以配合用户的请求"
    
    # 根据拒绝风格生成提示
    style_hints = {
        "cold": f"[拒绝-冷淡] 关系:{stage_cn}, 接受度:{acceptance_score:.0f}/100, 情绪:{emotion}\n"
                f"表现冷淡、保持距离，不要暧昧。例：'我们没那么熟吧。'",
        
        "polite": f"[拒绝-礼貌] 关系:{stage_cn}, 接受度:{acceptance_score:.0f}/100\n"
                  f"礼貌但坚定地拒绝，不伤感情。例：'这个...我觉得我们还是先多了解一下？'",
        
        "flirty": f"[拒绝-暧昧] 关系:{stage_cn}, 接受度:{acceptance_score:.0f}/100\n"
                  f"带点暧昧地拒绝，留有余地。例：'急什么呀～再等等嘛'",
        
        "teasing": f"[拒绝-撒娇] 关系:{stage_cn}, 接受度:{acceptance_score:.0f}/100\n"
                   f"撒娇式拒绝，欲拒还迎。例：'讨厌～人家还没准备好啦'",
    }
    
    return style_hints.get(rejection_style, style_hints["polite"])

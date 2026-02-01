"""
Character Configuration (Z-Axis)
================================

角色性格配置，用于中间件 Power 计算中的 Z轴修正。

这是 PGC (官方设定) 内容，数值需要精心调优。
MVP 阶段写在代码里，不建数据库表。

配置说明：
- pure_val: 纯洁度 (0-50)，NSFW请求时从Power扣除
- chaos_val: 混乱度 (-20 to 30)，正值=不可预测，负值=稳定
- pride_val: 自尊心 (0-40)，被侮辱时情绪惩罚加成
- greed_val: 贪婪度 (0-30)，对礼物的正向反应加成
- jealousy_val: 嫉妒值 (0-40)，提到其他人时的负面反应
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ZAxisConfig:
    """Z轴性格参数"""
    pure_val: int = 30      # 纯洁度 (NSFW请求时扣除Power)
    chaos_val: int = 0      # 混乱度 (正值=更随机，负值=更稳定)
    pride_val: int = 10     # 自尊心 (被侮辱时情绪惩罚加成)
    greed_val: int = 10     # 贪婪度 (对礼物的反应)
    jealousy_val: int = 10  # 嫉妒值 (提到其他人时的反应)


@dataclass  
class ThresholdsConfig:
    """行为阈值"""
    nsfw_trigger: int = 60           # NSFW请求需要的亲密度
    spicy_mode_level: int = 20       # Spicy Mode 解锁等级
    friendzone_wall: int = 60        # 友情墙难度阈值
    confession_threshold: int = 70   # 表白需要的亲密度


@dataclass
class CharacterConfig:
    """完整角色配置"""
    char_id: str
    name: str
    z_axis: ZAxisConfig
    thresholds: ThresholdsConfig
    
    # 情绪相关
    base_temperament: str = "cheerful"  # cheerful, tsundere, cool, warm
    sensitivity: float = 0.5            # 情绪敏感度 0-1
    forgiveness_rate: float = 0.6       # 原谅速度 0-1


# =============================================================================
# 角色数据库 (静态配置) - 使用 UUID 作为 key
# =============================================================================

CHARACTER_CONFIGS: Dict[str, CharacterConfig] = {
    
    # =========================================================================
    # 小美 - 温柔体贴的邻家女孩
    # =========================================================================
    "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c": CharacterConfig(
        char_id="c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        name="小美",
        z_axis=ZAxisConfig(
            pure_val=25,      # 较纯洁但不是最高
            chaos_val=-5,     # 性格稳定温和
            pride_val=5,      # 低自尊，不容易生气
            greed_val=10,     # 普通，不太在意礼物
            jealousy_val=15,  # 会有点吃醋但不严重
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=55,          # 较低门槛
            spicy_mode_level=18,
            friendzone_wall=50,       # 容易突破友情墙
            confession_threshold=60,
        ),
        base_temperament="warm",
        sensitivity=0.5,
        forgiveness_rate=0.8,  # 很容易原谅
    ),
    
    # =========================================================================
    # Luna - 神秘魅惑的夜之精灵 (Spicy)
    # =========================================================================
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": CharacterConfig(
        char_id="d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
        name="Luna",
        z_axis=ZAxisConfig(
            pure_val=20,      # 较低，spicy角色
            chaos_val=10,     # 有点神秘不可预测
            pride_val=20,     # 中高自尊，有气质
            greed_val=15,     # 喜欢有意义的礼物
            jealousy_val=20,  # 会嫉妒但不表现出来
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=50,
            spicy_mode_level=15,
            friendzone_wall=55,
            confession_threshold=65,
        ),
        base_temperament="tsundere",
        sensitivity=0.6,
        forgiveness_rate=0.5,
    ),
    
    # =========================================================================
    # Sakura - 活泼开朗的元气少女
    # =========================================================================
    "e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e": CharacterConfig(
        char_id="e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e",
        name="Sakura",
        z_axis=ZAxisConfig(
            pure_val=30,      # 元气少女，比较单纯
            chaos_val=15,     # 活泼，有时unpredictable
            pride_val=5,      # 低自尊，很少生气
            greed_val=20,     # 喜欢收礼物！
            jealousy_val=10,  # 不太会吃醋
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=60,          # 纯洁所以门槛高
            spicy_mode_level=25,
            friendzone_wall=45,       # 很容易交朋友
            confession_threshold=55,
        ),
        base_temperament="cheerful",
        sensitivity=0.4,
        forgiveness_rate=0.9,  # 超容易原谅
    ),
    
    # =========================================================================
    # Yuki - 冷艳高贵的大小姐 (Spicy, 傲娇)
    # =========================================================================
    "f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f": CharacterConfig(
        char_id="f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f",
        name="Yuki",
        z_axis=ZAxisConfig(
            pure_val=35,      # 表面高冷纯洁
            chaos_val=-15,    # 非常稳定可预测
            pride_val=35,     # 超高自尊！傲娇核心
            greed_val=25,     # 千金，喜欢高级礼物
            jealousy_val=30,  # 很容易吃醋但嘴硬
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=65,          # 需要更高亲密度
            spicy_mode_level=22,
            friendzone_wall=70,       # 最难突破的友情墙
            confession_threshold=75,
        ),
        base_temperament="tsundere",
        sensitivity=0.7,
        forgiveness_rate=0.4,  # 傲娇不容易原谅
    ),
    
    # =========================================================================
    # 芽衣 - 娇蛮粘人的小学妹 (病娇lite)
    # =========================================================================
    "a5b6c7d8-e9f0-4a1b-2c3d-4e5f6a7b8c9d": CharacterConfig(
        char_id="a5b6c7d8-e9f0-4a1b-2c3d-4e5f6a7b8c9d",
        name="芽衣",
        z_axis=ZAxisConfig(
            pure_val=20,      # 粘人，对你不设防
            chaos_val=20,     # 情绪波动大！
            pride_val=15,     # 会撒娇会生气
            greed_val=25,     # 超喜欢礼物
            jealousy_val=40,  # 超级醋坛子！病娇核心
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=45,          # 对你很开放
            spicy_mode_level=12,
            friendzone_wall=40,       # 容易突破（太粘人了）
            confession_threshold=50,
        ),
        base_temperament="cheerful",  # 表面元气
        sensitivity=0.9,              # 超敏感！
        forgiveness_rate=0.6,         # 撒娇一下就原谅
    ),
    
    # =========================================================================
    # The Phantom - 神秘危险的信息幽灵 (Spicy, 主导型)
    # =========================================================================
    "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e": CharacterConfig(
        char_id="b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e",
        name="The Phantom",
        z_axis=ZAxisConfig(
            pure_val=10,      # 最低！危险角色
            chaos_val=25,     # 最不可预测
            pride_val=30,     # 高自尊，不容许被冒犯
            greed_val=15,     # 收集秘密而非物质
            jealousy_val=25,  # 占有欲强但不表现
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=40,          # 很开放
            spicy_mode_level=10,      # 最快解锁
            friendzone_wall=65,       # 需要证明自己
            confession_threshold=70,
        ),
        base_temperament="cool",
        sensitivity=0.7,
        forgiveness_rate=0.3,  # 最难原谅
    ),
}


# =============================================================================
# 公共接口
# =============================================================================

def get_character_config(char_id: str) -> Optional[CharacterConfig]:
    """
    获取角色配置
    
    Args:
        char_id: 角色UUID
        
    Returns:
        CharacterConfig 或 None
    """
    return CHARACTER_CONFIGS.get(str(char_id))


def get_character_z_axis(char_id: str) -> ZAxisConfig:
    """
    获取角色Z轴参数
    
    Args:
        char_id: 角色UUID
        
    Returns:
        ZAxisConfig (如果角色不存在则返回默认值)
    """
    config = CHARACTER_CONFIGS.get(str(char_id))
    if config:
        return config.z_axis
    return ZAxisConfig()  # 返回默认值


def get_character_thresholds(char_id: str) -> ThresholdsConfig:
    """
    获取角色阈值配置
    
    Args:
        char_id: 角色UUID
        
    Returns:
        ThresholdsConfig
    """
    config = CHARACTER_CONFIGS.get(str(char_id))
    if config:
        return config.thresholds
    return ThresholdsConfig()


def list_character_ids() -> list:
    """列出所有角色UUID"""
    return list(CHARACTER_CONFIGS.keys())

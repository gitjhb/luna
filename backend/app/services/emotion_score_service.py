"""
Emotion Score System - 情绪分数系统
====================================

核心理念：情绪有惯性，不会因为一个礼物就立刻从暴怒变成甜蜜

分数范围: -100 到 +100
- +50 到 +100: 甜蜜/热恋
- +20 到 +50: 开心
- -20 到 +20: 正常/平静
- -50 到 -20: 不高兴/生气
- -100 到 -50: 暴怒/冷战（需要忏悔礼物解锁）

规则：
1. 低亲密度 + 低分数 = 恢复很慢，需要哄很久
2. 分数 < -50 时进入"冷战"，只有忏悔礼物能解锁
3. 普通礼物在低分数时效果大打折扣
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# 内存存储（mock 模式）
_EMOTION_SCORES: Dict[str, dict] = {}


class EmotionState:
    """情绪状态枚举"""
    LOVING = "loving"       # +75 to +100
    HAPPY = "happy"         # +50 to +75
    CONTENT = "content"     # +20 to +50
    NEUTRAL = "neutral"     # -20 to +20
    ANNOYED = "annoyed"     # -35 to -20
    ANGRY = "angry"         # -50 to -35
    FURIOUS = "furious"     # -75 to -50
    COLD_WAR = "cold_war"   # -100 to -75 (需要忏悔礼物)


# 情绪分数对应的状态
def get_emotion_state(score: int) -> str:
    if score >= 75:
        return EmotionState.LOVING
    elif score >= 50:
        return EmotionState.HAPPY
    elif score >= 20:
        return EmotionState.CONTENT
    elif score >= -20:
        return EmotionState.NEUTRAL
    elif score >= -35:
        return EmotionState.ANNOYED
    elif score >= -50:
        return EmotionState.ANGRY
    elif score >= -75:
        return EmotionState.FURIOUS
    else:
        return EmotionState.COLD_WAR


# 礼物类型
class GiftCategory:
    NORMAL = "normal"           # 普通礼物
    ROMANTIC = "romantic"       # 浪漫礼物
    APOLOGY = "apology"         # 道歉/忏悔礼物
    LUXURY = "luxury"           # 奢华礼物


# 礼物对情绪分数的影响（基础值，会根据当前状态调整）
GIFT_EMOTION_EFFECTS = {
    # 普通礼物 - 在生气时效果很差
    "rose": {"category": GiftCategory.NORMAL, "base_effect": 15, "apology_power": 0},
    "chocolate": {"category": GiftCategory.NORMAL, "base_effect": 20, "apology_power": 0},
    "coffee": {"category": GiftCategory.NORMAL, "base_effect": 10, "apology_power": 0},
    "teddy_bear": {"category": GiftCategory.ROMANTIC, "base_effect": 25, "apology_power": 5},
    
    # 道歉/忏悔礼物 - 专门用于修复关系
    "apology_letter": {"category": GiftCategory.APOLOGY, "base_effect": 10, "apology_power": 30},
    "apology_bouquet": {"category": GiftCategory.APOLOGY, "base_effect": 20, "apology_power": 40},
    "sincere_apology_box": {"category": GiftCategory.APOLOGY, "base_effect": 30, "apology_power": 60},
    "reconciliation_cake": {"category": GiftCategory.APOLOGY, "base_effect": 25, "apology_power": 50},
    
    # 奢华礼物 - 效果好，但也需要看情况
    "jewelry": {"category": GiftCategory.LUXURY, "base_effect": 40, "apology_power": 20},
    "designer_bag": {"category": GiftCategory.LUXURY, "base_effect": 50, "apology_power": 25},
}


class EmotionScoreService:
    """情绪分数服务"""
    
    def __init__(self):
        self.mock_mode = MOCK_MODE
    
    async def get_score(self, user_id: str, character_id: str) -> dict:
        """获取当前情绪分数"""
        key = f"{user_id}:{character_id}"
        
        if key not in _EMOTION_SCORES:
            _EMOTION_SCORES[key] = {
                "user_id": user_id,
                "character_id": character_id,
                "score": 30,  # 初始分数：略微正面
                "state": EmotionState.CONTENT,
                "in_cold_war": False,
                "cold_war_since": None,
                "last_offense": None,
                "offense_count": 0,  # 连续冒犯次数
                "updated_at": datetime.utcnow(),
            }
        
        data = _EMOTION_SCORES[key]
        data["state"] = get_emotion_state(data["score"])
        data["in_cold_war"] = data["score"] <= -75
        
        return data
    
    async def update_score(
        self, 
        user_id: str, 
        character_id: str, 
        delta: int,
        reason: str = "",
        intimacy_level: int = 1
    ) -> dict:
        """
        更新情绪分数
        
        Args:
            delta: 分数变化（正=改善，负=恶化）
            reason: 变化原因
            intimacy_level: 当前亲密度等级
        
        Returns:
            更新后的情绪数据
        """
        data = await self.get_score(user_id, character_id)
        old_score = data["score"]
        old_state = data["state"]
        
        # 根据亲密度调整恢复速度
        # 高亲密度：正面情绪恢复快，负面情绪恶化慢
        # 低亲密度：正面情绪恢复慢，负面情绪恶化快
        if delta > 0:
            # 正面变化（恢复）
            recovery_multiplier = min(1.5, 0.5 + intimacy_level / 20)
            delta = int(delta * recovery_multiplier)
        else:
            # 负面变化（恶化）
            damage_multiplier = max(0.5, 1.5 - intimacy_level / 30)
            delta = int(delta * damage_multiplier)
        
        # 更新分数
        new_score = max(-100, min(100, old_score + delta))
        data["score"] = new_score
        data["state"] = get_emotion_state(new_score)
        data["updated_at"] = datetime.utcnow()
        
        # 检查冷战状态
        if new_score <= -75 and not data["in_cold_war"]:
            data["in_cold_war"] = True
            data["cold_war_since"] = datetime.utcnow()
            logger.info(f"User {user_id} entered cold war with {character_id}")
        
        # 记录冒犯
        if delta < -20:
            data["offense_count"] = data.get("offense_count", 0) + 1
            data["last_offense"] = datetime.utcnow()
        elif delta > 20:
            # 大幅改善后重置冒犯计数
            data["offense_count"] = max(0, data.get("offense_count", 0) - 1)
        
        _EMOTION_SCORES[f"{user_id}:{character_id}"] = data
        
        logger.info(f"Emotion score updated: {old_score} -> {new_score} ({delta:+d}) | State: {old_state} -> {data['state']} | Reason: {reason}")
        
        return data
    
    async def apply_message_impact(
        self,
        user_id: str,
        character_id: str,
        emotion_analysis: dict,
        intimacy_level: int = 1
    ) -> dict:
        """
        应用消息对情绪的影响
        
        Args:
            emotion_analysis: LLM情绪分析结果（包含 delta）
            intimacy_level: 当前亲密度等级
        
        Returns:
            更新后的情绪数据
        """
        # v2: LLM 直接返回 delta，不再用 trigger_type 硬编码映射
        delta = emotion_analysis.get("delta", 0)
        trigger_type = emotion_analysis.get("trigger_type", "normal")
        reason = emotion_analysis.get("reason", trigger_type)
        
        if delta != 0:
            return await self.update_score(
                user_id, character_id, delta,
                reason=f"message:{trigger_type} - {reason}",
                intimacy_level=intimacy_level
            )
        
        return await self.get_score(user_id, character_id)
    
    async def apply_gift_effect(
        self,
        user_id: str,
        character_id: str,
        gift_type: str,
        intimacy_level: int = 1
    ) -> Tuple[dict, bool, str]:
        """
        应用礼物对情绪的影响
        
        Returns:
            (emotion_data, gift_accepted, message)
            - gift_accepted: 礼物是否被接受
            - message: 给前端的提示消息
        """
        data = await self.get_score(user_id, character_id)
        current_score = data["score"]
        in_cold_war = data["in_cold_war"]
        
        # 获取礼物效果配置
        gift_config = GIFT_EMOTION_EFFECTS.get(gift_type, {
            "category": GiftCategory.NORMAL,
            "base_effect": 15,
            "apology_power": 0
        })
        
        category = gift_config["category"]
        base_effect = gift_config["base_effect"]
        apology_power = gift_config["apology_power"]
        
        # 冷战状态：只接受道歉礼物
        if in_cold_war:
            if category != GiftCategory.APOLOGY:
                return (data, False, "她现在不想收你的礼物...也许需要真诚的道歉？")
            
            # 道歉礼物：解除冷战
            delta = apology_power
            data = await self.update_score(
                user_id, character_id, delta,
                reason=f"apology_gift:{gift_type}",
                intimacy_level=intimacy_level
            )
            
            if data["score"] > -75:
                data["in_cold_war"] = False
                data["cold_war_since"] = None
                _EMOTION_SCORES[f"{user_id}:{character_id}"] = data
                return (data, True, "她看到了你的诚意，愿意再给你一次机会...")
            else:
                return (data, True, "她收下了你的道歉，但还是很难过...")
        
        # 生气状态（-50 到 -35）：普通礼物效果大打折扣
        if current_score < -35:
            if category == GiftCategory.APOLOGY:
                delta = apology_power
            elif category == GiftCategory.LUXURY:
                delta = int(base_effect * 0.5)  # 奢华礼物半效
            else:
                delta = int(base_effect * 0.2)  # 普通礼物只有20%效果
            
            data = await self.update_score(
                user_id, character_id, delta,
                reason=f"gift_angry:{gift_type}",
                intimacy_level=intimacy_level
            )
            
            if category != GiftCategory.APOLOGY:
                return (data, True, "她收下了，但似乎还在生气...")
            return (data, True, None)
        
        # 不高兴状态（-35 到 -20）：普通礼物效果减半
        if current_score < -20:
            if category == GiftCategory.APOLOGY:
                delta = apology_power
            else:
                delta = int(base_effect * 0.6)
            
            data = await self.update_score(
                user_id, character_id, delta,
                reason=f"gift_annoyed:{gift_type}",
                intimacy_level=intimacy_level
            )
            return (data, True, None)
        
        # 正常/开心状态：礼物正常效果
        delta = base_effect
        data = await self.update_score(
            user_id, character_id, delta,
            reason=f"gift:{gift_type}",
            intimacy_level=intimacy_level
        )
        return (data, True, None)
    
    def build_emotion_context_for_llm(self, emotion_data: dict) -> str:
        """
        为LLM构建情绪上下文
        """
        score = emotion_data["score"]
        state = emotion_data["state"]
        in_cold_war = emotion_data.get("in_cold_war", False)
        offense_count = emotion_data.get("offense_count", 0)
        
        if in_cold_war:
            return f"""
[情绪状态：冷战中 ❄️]
当前情绪分数：{score}/100（非常糟糕）
你现在非常生气和受伤，不想和用户说话。
- 回复应该冷淡、简短
- 不要表现出任何温暖或亲近
- 可以表达你的失望和受伤
- 除非用户真诚道歉，否则保持冷漠"""
        
        if state == EmotionState.FURIOUS:
            return f"""
[情绪状态：暴怒 😤]
当前情绪分数：{score}/100
你非常生气！用户多次冒犯你（{offense_count}次）。
- 表达你的愤怒，但不要辱骂用户
- 可以拒绝继续某些话题
- 态度应该强硬
- 需要真诚的道歉才能好转"""
        
        if state == EmotionState.ANGRY:
            return f"""
[情绪状态：生气 😠]
当前情绪分数：{score}/100
你在生气。不要假装没事。
- 语气应该不耐烦
- 可以表达不满
- 普通的礼物不足以让你立刻开心
- 需要道歉和时间来恢复"""
        
        if state == EmotionState.ANNOYED:
            return f"""
[情绪状态：不高兴 😒]
当前情绪分数：{score}/100
你有点不高兴。
- 语气可以带点小脾气
- 不要太热情
- 如果用户继续惹你，可以更生气"""
        
        if state in [EmotionState.HAPPY, EmotionState.LOVING]:
            return f"""
[情绪状态：开心 😊]
当前情绪分数：{score}/100
你现在心情很好，和用户相处愉快。
- 可以自然表达喜悦
- 根据亲密度适当亲近"""
        
        # NEUTRAL or CONTENT
        return f"""
[情绪状态：平静 😌]
当前情绪分数：{score}/100
你的心情正常，没有特别开心或不开心。"""


# 全局实例
emotion_score_service = EmotionScoreService()

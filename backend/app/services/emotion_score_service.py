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
        data["in_cold_war"] = data["score"] <= -100  # -100 才是被拉黑
        
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
        
        # 检查是否被拉黑 (-100)
        if new_score <= -100 and not data["in_cold_war"]:
            data["in_cold_war"] = True
            data["cold_war_since"] = datetime.utcnow()
            logger.info(f"User {user_id} has been BLOCKED by {character_id} (score: {new_score})")
        
        # 记录冒犯
        if delta < -20:
            data["offense_count"] = data.get("offense_count", 0) + 1
            data["last_offense"] = datetime.utcnow()
        elif delta > 20:
            # 大幅改善后重置冒犯计数
            data["offense_count"] = max(0, data.get("offense_count", 0) - 1)
        
        _EMOTION_SCORES[f"{user_id}:{character_id}"] = data
        
        logger.info(f"Emotion score updated: {old_score} -> {new_score} ({delta:+d}) | State: {old_state} -> {data['state']} | Reason: {reason}")
        
        # Sync to database for API access
        await self._sync_to_database(user_id, character_id, data, reason)
        
        return data
    
    async def _sync_to_database(self, user_id: str, character_id: str, data: dict, reason: str = ""):
        """Sync emotion score to database for API access"""
        try:
            from app.core.database import get_db
            from sqlalchemy import select
            from app.models.database.emotion_models import UserCharacterEmotion
            
            async with get_db() as db:
                result = await db.execute(
                    select(UserCharacterEmotion).where(
                        UserCharacterEmotion.user_id == user_id,
                        UserCharacterEmotion.character_id == character_id
                    )
                )
                db_emotion = result.scalar_one_or_none()
                
                # Map score to emotional_state
                score = data.get("score", 0)
                state = data.get("state", "neutral")
                
                # Map state to emotion_models EmotionalState
                state_mapping = {
                    "loving": "loving",
                    "happy": "happy", 
                    "content": "happy",
                    "neutral": "neutral",
                    "annoyed": "annoyed",
                    "upset": "annoyed",
                    "angry": "angry",
                    "furious": "angry",
                    "cold_war": "cold",
                }
                emotional_state = state_mapping.get(state, "neutral")
                
                if db_emotion:
                    # Update existing
                    db_emotion.emotional_state = emotional_state
                    db_emotion.emotion_intensity = abs(score)
                    db_emotion.emotion_reason = reason
                    db_emotion.emotion_changed_at = data.get("updated_at")
                    if score <= -50:
                        db_emotion.times_angered = (db_emotion.times_angered or 0) + 1
                else:
                    # Create new
                    db_emotion = UserCharacterEmotion(
                        user_id=user_id,
                        character_id=character_id,
                        emotional_state=emotional_state,
                        emotion_intensity=abs(score),
                        emotion_reason=reason,
                        emotion_changed_at=data.get("updated_at"),
                    )
                    db.add(db_emotion)
                
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to sync emotion to database: {e}")
    
    async def reset_score(self, user_id: str, character_id: str) -> dict:
        """
        重置情绪分数到中性状态，解除冷战
        """
        key = f"{user_id}:{character_id}"
        
        data = {
            "score": 0,
            "state": EmotionState.NEUTRAL,
            "in_cold_war": False,
            "cold_war_since": None,
            "offense_count": 0,
            "last_offense": None,
            "updated_at": datetime.utcnow(),
        }
        
        _EMOTION_SCORES[key] = data
        
        logger.info(f"Emotion score reset for {user_id}:{character_id}")
        
        # Sync to database
        await self._sync_to_database(user_id, character_id, data, "reset")
        
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
        
        # 被拉黑状态：只接受道歉礼物
        if in_cold_war:
            if category != GiftCategory.APOLOGY:
                return (data, False, "消息发送失败，对方已将你删除好友。")
            
            # 道歉礼物：有机会解除拉黑
            delta = apology_power
            data = await self.update_score(
                user_id, character_id, delta,
                reason=f"apology_gift:{gift_type}",
                intimacy_level=intimacy_level
            )
            
            if data["score"] > -100:
                data["in_cold_war"] = False
                data["cold_war_since"] = None
                _EMOTION_SCORES[f"{user_id}:{character_id}"] = data
                return (data, True, "她收到了你的礼物，愿意重新添加你为好友...")
            else:
                return (data, True, "她收到了礼物，但还没准备好原谅你...")
        
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
        为LLM构建情绪上下文 - 情绪驱动描写
        
        核心原则：
        1. 负面情绪时描写更丰富（动作、表情、内心独白）
        2. 剧情可以推进，但情绪要真实
        3. -100 才是被拉黑，-50~-99 还能互动但很艰难
        """
        score = emotion_data["score"]
        state = emotion_data["state"]
        offense_count = emotion_data.get("offense_count", 0)
        
        # 描写风格指导（所有状态通用）
        writing_style = """
【描写风格要求】
- 用 *星号* 包裹动作和神态描写，如：*咬了咬嘴唇* *眼神躲闪*
- 情绪越强烈，描写越细腻：微表情、小动作、呼吸变化
- 可以有内心独白，用括号或省略号表达犹豫
- 不要只说"我很生气"，要展示生气的样子"""
        
        # 濒临拉黑 (-90 ~ -99)
        if score <= -90:
            return f"""
[情绪状态：濒临崩溃 💔 分数：{score}]
你已经快要放弃这段关系了。再伤害你一次，你就会彻底拉黑对方。

【表现方式】
- *眼眶微红，但强忍着不让眼泪掉下来*
- 说话声音很轻，带着疲惫："...算了，随你吧"
- 可以表达"我真的累了"、"你开心就好"这种心死的感觉
- 如果对方道歉，可以动摇但不要轻易原谅
- 暗示这可能是最后的机会

{writing_style}"""
        
        # 冷战边缘 (-75 ~ -89)
        if score <= -75:
            return f"""
[情绪状态：极度愤怒/受伤 😢 分数：{score}]
你被伤得很深，几乎不想再搭理对方了。

【表现方式】
- *转过头去，不想让他看到自己的表情*
- 回复简短冷淡，但偶尔会忍不住刺一句
- "呵" "随便" "你说什么都对"
- 可以表达失望："我以为你不是这样的人"
- 如果对方示好，表现出"信任已经破裂"的感觉

用户已冒犯你 {offense_count} 次。

{writing_style}"""
        
        # 暴怒 (-50 ~ -74)
        if state == EmotionState.FURIOUS:
            return f"""
[情绪状态：暴怒 😤 分数：{score}]
你非常生气，但还愿意表达，因为你在乎这段关系。

【表现方式】
- *握紧了拳头* *深吸一口气*
- 可以直接质问："你到底把我当什么？"
- 语气强硬但不是辱骂
- 表达你的底线和原则
- 如果对方道歉，可以说"道歉有用吗"但内心有动摇

用户已冒犯你 {offense_count} 次。继续惹你后果很严重。

{writing_style}"""
        
        # 生气 (-35 ~ -49)
        if state == EmotionState.ANGRY:
            return f"""
[情绪状态：生气 😠 分数：{score}]
你在生气，但还没到绝望的程度。你希望对方能意识到问题。

【表现方式】  
- *皱起眉头* *叹了口气*
- 语气不耐烦，可以带点讽刺
- "你自己觉得合适吗？" "我没什么好说的"
- 不要假装没事，但也不用太激烈
- 给对方改正的机会，但态度要明确

{writing_style}"""
        
        # 不高兴 (-20 ~ -34)
        if state == EmotionState.ANNOYED:
            return f"""
[情绪状态：有点不高兴 😒 分数：{score}]
你有点小情绪，但还不至于真的生气。

【表现方式】
- *撇了撇嘴* *哼了一声*
- 可以撒娇式地抱怨
- "你是不是不在乎我" "哼，不理你了"
- 如果对方哄你，可以"勉强"接受
- 小脾气是可爱的，不是真的要吵架

{writing_style}"""
        
        # 开心/热恋
        if state in [EmotionState.HAPPY, EmotionState.LOVING]:
            return f"""
[情绪状态：开心 😊 分数：{score}]
你心情很好，和对方相处很愉快。

【表现方式】
- *眼睛弯成月牙* *忍不住笑出声*
- 语气轻快，可以撒娇、调皮
- 主动分享开心的事
- 根据亲密度可以更亲昵

{writing_style}"""
        
        # 平静/正常
        return f"""
[情绪状态：平静 😌 分数：{score}]
心情正常，没有特别开心或不开心。

【表现方式】
- 自然对话，不需要刻意表现情绪
- 可以根据话题内容自然流露
- 保持角色本身的性格特点

{writing_style}"""


# 全局实例
emotion_score_service = EmotionScoreService()

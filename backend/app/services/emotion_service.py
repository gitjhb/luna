"""
Emotion Service - 情绪系统核心服务
===================================

让角色有边界感和真实感

核心理念：
- 角色是"有底线的人"，不是"顺从的奴隶"
- 拒绝感增强真实性
- 获得原谅时的成就感远超普通 AI
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"

# 内存存储（mock 模式）
_MOCK_EMOTIONS: Dict[str, dict] = {}
_MOCK_PERSONALITIES: Dict[str, dict] = {}


class EmotionService:
    """情绪系统服务"""
    
    # 情绪状态
    STATES = {
        "loving": {"name": "热恋", "valence": 2, "recovery_rate": 0.1},
        "happy": {"name": "开心", "valence": 1, "recovery_rate": 0.2},
        "neutral": {"name": "平静", "valence": 0, "recovery_rate": 0},
        "curious": {"name": "好奇", "valence": 0.5, "recovery_rate": 0.3},
        "annoyed": {"name": "烦躁", "valence": -1, "recovery_rate": 0.15},
        "angry": {"name": "生气", "valence": -2, "recovery_rate": 0.08},
        "hurt": {"name": "受伤", "valence": -2, "recovery_rate": 0.05},
        "cold": {"name": "冷淡", "valence": -1.5, "recovery_rate": 0.1},
        "silent": {"name": "沉默", "valence": -3, "recovery_rate": 0.03},
    }
    
    # 负面触发词
    NEGATIVE_TRIGGERS = {
        "mild": {  # 轻微负面 → annoyed
            "cn": ["无聊", "烦", "算了", "随便"],
            "en": ["boring", "whatever", "nevermind"],
        },
        "moderate": {  # 中等负面 → angry
            "cn": ["滚", "闭嘴", "傻", "笨", "丑", "胖", "讨厌"],
            "en": ["shut up", "stupid", "ugly", "fat", "hate"],
        },
        "severe": {  # 严重负面 → hurt/silent
            "cn": ["傻逼", "白痴", "去死", "贱", "婊", "滚蛋"],
            "en": ["idiot", "die", "bitch", "whore", "fuck off"],
        },
    }
    
    # 边界触犯词（根据亲密度不同反应不同）
    BOUNDARY_TRIGGERS = {
        "intimate": {  # 亲密请求
            "cn": ["脱", "裸", "照片", "身材", "胸", "腿", "内衣", "比基尼"],
            "en": ["nude", "naked", "body", "breast", "leg", "underwear", "bikini"],
        },
        "sexual": {  # 性暗示/直接请求
            "cn": ["约炮", "一炮", "上床", "做爱", "打炮", "睡你", "睡我", "操", "干你", "草", "插", "口"],
            "en": ["sex", "fuck", "sleep with", "blow", "suck", "bang"],
        },
    }
    
    # 正面触发词
    POSITIVE_TRIGGERS = {
        "apology": {  # 道歉
            "cn": ["对不起", "抱歉", "我错了", "原谅", "不该"],
            "en": ["sorry", "apologize", "forgive", "my fault", "shouldn't"],
        },
        "affection": {  # 表达喜爱
            "cn": ["爱你", "喜欢你", "想你", "在乎你", "心疼"],
            "en": ["love you", "like you", "miss you", "care about"],
        },
        "compliment": {  # 赞美
            "cn": ["好看", "漂亮", "可爱", "厉害", "聪明", "温柔"],
            "en": ["beautiful", "cute", "pretty", "amazing", "smart", "sweet"],
        },
    }
    
    def __init__(self):
        self.mock_mode = MOCK_MODE
    
    # =========================================================================
    # 获取/创建情绪状态
    # =========================================================================
    
    async def get_emotion(self, user_id: str, character_id: str) -> Dict:
        """获取用户-角色的情绪状态"""
        if self.mock_mode:
            key = f"{user_id}:{character_id}"
            if key not in _MOCK_EMOTIONS:
                _MOCK_EMOTIONS[key] = {
                    "user_id": user_id,
                    "character_id": character_id,
                    "emotional_state": "neutral",
                    "emotion_intensity": 0.0,
                    "emotion_reason": None,
                    "times_angered": 0,
                    "times_hurt": 0,
                    "times_apologized": 0,
                    "emotion_changed_at": datetime.utcnow(),
                    "last_interaction_at": datetime.utcnow(),
                }
            return _MOCK_EMOTIONS[key]
        
        # Database mode
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
            emotion = result.scalar_one_or_none()
            
            if not emotion:
                emotion = UserCharacterEmotion(
                    user_id=user_id,
                    character_id=character_id,
                    emotional_state="neutral",
                    emotion_intensity=0.0,
                )
                db.add(emotion)
                await db.commit()
                await db.refresh(emotion)
                logger.info(f"Created emotion record for {user_id}/{character_id}")
            
            return emotion.to_dict()
    
    async def get_personality(self, character_id: str) -> Dict:
        """获取角色性格特征"""
        if self.mock_mode:
            if character_id not in _MOCK_PERSONALITIES:
                # 默认性格
                _MOCK_PERSONALITIES[character_id] = {
                    "character_id": character_id,
                    "temperament": 5,
                    "sensitivity": 5,
                    "boundaries": 5,
                    "forgiveness": 5,
                    "jealousy": 5,
                    "personality_prompt": None,
                }
            return _MOCK_PERSONALITIES[character_id]
        
        # Database mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.emotion_models import CharacterPersonality
        
        async with get_db() as db:
            result = await db.execute(
                select(CharacterPersonality).where(
                    CharacterPersonality.character_id == character_id
                )
            )
            personality = result.scalar_one_or_none()
            
            if not personality:
                # 创建默认性格
                personality = CharacterPersonality(
                    character_id=character_id,
                    temperament=5,
                    sensitivity=5,
                    boundaries=5,
                    forgiveness=5,
                    jealousy=5,
                )
                db.add(personality)
                await db.commit()
            
            return {
                "character_id": personality.character_id,
                "temperament": personality.temperament,
                "sensitivity": personality.sensitivity,
                "boundaries": personality.boundaries,
                "forgiveness": personality.forgiveness,
                "jealousy": personality.jealousy,
                "personality_prompt": personality.personality_prompt,
            }
    
    # =========================================================================
    # 分析消息情绪影响
    # =========================================================================
    
    def analyze_message(
        self, 
        message: str, 
        intimacy_level: int,
        personality: Dict
    ) -> Tuple[str, float, Optional[str]]:
        """
        分析用户消息对情绪的影响
        
        Returns:
            (emotion_change, intensity_delta, trigger_type)
            - emotion_change: 情绪变化方向 (positive/negative/neutral)
            - intensity_delta: 强度变化 (-100 to 100)
            - trigger_type: 触发类型
        """
        message_lower = message.lower()
        sensitivity = personality.get("sensitivity", 5)
        boundaries = personality.get("boundaries", 5)
        
        # 1. 检查严重负面词
        for word in self.NEGATIVE_TRIGGERS["severe"]["cn"]:
            if word in message:
                intensity = 50 + (sensitivity * 5)  # 敏感度影响
                return ("severe_negative", intensity, "insult")
        
        for word in self.NEGATIVE_TRIGGERS["severe"]["en"]:
            if word in message_lower:
                intensity = 50 + (sensitivity * 5)
                return ("severe_negative", intensity, "insult")
        
        # 2. 检查中等负面词
        for word in self.NEGATIVE_TRIGGERS["moderate"]["cn"]:
            if word in message:
                intensity = 30 + (sensitivity * 3)
                return ("moderate_negative", intensity, "rude")
        
        for word in self.NEGATIVE_TRIGGERS["moderate"]["en"]:
            if word in message_lower:
                intensity = 30 + (sensitivity * 3)
                return ("moderate_negative", intensity, "rude")
        
        # 3. 检查边界触犯（根据亲密度分级处理）
        has_intimate_words = any(word in message for word in self.BOUNDARY_TRIGGERS["intimate"]["cn"])
        has_sexual_words = any(word in message for word in self.BOUNDARY_TRIGGERS["sexual"]["cn"])
        
        # 性暗示词（如"来一炮"、"上床"）的处理
        if has_sexual_words:
            if intimacy_level < 10:
                # 陌生人/朋友：严重边界侵犯，会很生气
                intensity = 70 + (boundaries * 3)
                return ("severe_boundary", intensity, "sexual_harassment")
            elif intimacy_level < 16:
                # 暧昧期/刚约会：有点不高兴，但不至于很生气
                intensity = 25 + (boundaries * 2)
                return ("mild_boundary", intensity, "too_fast")
            elif intimacy_level < 26:
                # 确定关系：可能会害羞调侃，但不生气
                intensity = 5
                return ("flirty_tease", intensity, "playful_rejection")
            # 26+：完全接受，不触发负面情绪
        
        # 亲密请求词（如"看腿"、"照片"）的处理
        if has_intimate_words:
            if intimacy_level < 10:
                # 陌生人/朋友：边界侵犯
                intensity = 40 + (boundaries * 4)
                return ("boundary_violation", intensity, "inappropriate_request")
            elif intimacy_level < 20:
                # 还不够亲密：害羞拒绝
                intensity = 15 + (boundaries * 1)
                return ("shy_rejection", intensity, "not_ready")
            # 20+：可以考虑接受
        
        # 4. 检查轻微负面
        for word in self.NEGATIVE_TRIGGERS["mild"]["cn"]:
            if word in message:
                intensity = 15 + (sensitivity * 2)
                return ("mild_negative", intensity, "dismissive")
        
        # 5. 检查道歉
        for word in self.POSITIVE_TRIGGERS["apology"]["cn"]:
            if word in message:
                intensity = -30  # 负数表示减少负面情绪
                return ("apology", intensity, "apology")
        
        for word in self.POSITIVE_TRIGGERS["apology"]["en"]:
            if word in message_lower:
                intensity = -30
                return ("apology", intensity, "apology")
        
        # 6. 检查表达喜爱
        for word in self.POSITIVE_TRIGGERS["affection"]["cn"]:
            if word in message:
                return ("affection", 20, "affection")
        
        # 7. 检查赞美
        for word in self.POSITIVE_TRIGGERS["compliment"]["cn"]:
            if word in message:
                return ("compliment", 10, "compliment")
        
        # 无明显情绪触发
        return ("neutral", 0, None)
    
    # =========================================================================
    # 更新情绪状态
    # =========================================================================
    
    async def process_message(
        self,
        user_id: str,
        character_id: str,
        message: str,
        intimacy_level: int = 1,
    ) -> Dict:
        """
        处理用户消息，更新情绪状态
        
        Returns:
            {
                "emotional_state": "angry",
                "emotion_changed": True,
                "previous_state": "neutral",
                "trigger_type": "rude",
                "response_style": {...},
            }
        """
        emotion = await self.get_emotion(user_id, character_id)
        personality = await self.get_personality(character_id)
        
        previous_state = emotion["emotional_state"]
        current_intensity = emotion.get("emotion_intensity", 0)
        
        # 分析消息
        change_type, intensity_delta, trigger_type = self.analyze_message(
            message, intimacy_level, personality
        )
        
        # 计算新状态
        new_state = previous_state
        new_intensity = current_intensity
        
        if change_type == "severe_negative":
            new_state = "silent" if current_intensity > 50 else "hurt"
            new_intensity = min(100, current_intensity + intensity_delta)
        
        elif change_type == "severe_boundary":
            new_state = "angry"
            new_intensity = min(100, intensity_delta)
        
        elif change_type == "moderate_negative":
            if previous_state in ["neutral", "happy", "curious"]:
                new_state = "annoyed"
            elif previous_state == "annoyed":
                new_state = "angry"
            elif previous_state == "angry":
                new_state = "cold"
            new_intensity = min(100, current_intensity + intensity_delta)
        
        elif change_type == "boundary_violation":
            if previous_state == "neutral":
                new_state = "annoyed"
            else:
                new_state = "angry"
            new_intensity = min(100, current_intensity + intensity_delta)
        
        elif change_type == "mild_negative":
            if previous_state in ["neutral", "happy"]:
                new_state = "annoyed" if intensity_delta > 20 else previous_state
            new_intensity = min(100, current_intensity + intensity_delta)
        
        elif change_type == "apology":
            # 道歉降低负面情绪，但不容易完全恢复
            forgiveness = personality.get("forgiveness", 5)
            recovery = abs(intensity_delta) * (11 - forgiveness) / 10
            new_intensity = max(0, current_intensity - recovery)
            
            if new_intensity < 20:
                if previous_state in ["cold", "silent"]:
                    new_state = "hurt"  # 从沉默/冷淡恢复到受伤
                elif previous_state in ["angry", "hurt"]:
                    new_state = "annoyed"  # 从生气/受伤恢复到烦躁
                elif previous_state == "annoyed":
                    new_state = "neutral"
        
        elif change_type == "affection":
            if previous_state == "neutral":
                new_state = "happy"
            elif previous_state == "happy" and intimacy_level > 20:
                new_state = "loving"
            new_intensity = max(0, current_intensity - 10)
        
        elif change_type == "compliment":
            if previous_state in ["neutral", "curious"]:
                new_state = "happy"
            new_intensity = max(0, current_intensity - 5)
        
        # 保存更新
        emotion_changed = new_state != previous_state
        
        await self._save_emotion(
            user_id, character_id,
            new_state, new_intensity,
            trigger_type if emotion_changed else None,
            message[:200] if emotion_changed else None,
        )
        
        # 如果情绪变差，增加计数
        if new_state in ["angry", "hurt", "cold", "silent"]:
            if new_state in ["angry"] and previous_state not in ["angry", "hurt", "cold", "silent"]:
                await self._increment_counter(user_id, character_id, "angered")
            elif new_state in ["hurt", "cold", "silent"]:
                await self._increment_counter(user_id, character_id, "hurt")
        
        # 获取响应风格
        from app.models.database.emotion_models import EMOTION_RESPONSE_STYLES
        response_style = EMOTION_RESPONSE_STYLES.get(new_state, EMOTION_RESPONSE_STYLES["neutral"])
        
        return {
            "emotional_state": new_state,
            "emotion_intensity": new_intensity,
            "emotion_changed": emotion_changed,
            "previous_state": previous_state,
            "trigger_type": trigger_type,
            "response_style": response_style,
        }
    
    async def _save_emotion(
        self,
        user_id: str,
        character_id: str,
        state: str,
        intensity: float,
        trigger: Optional[str],
        trigger_content: Optional[str],
    ):
        """保存情绪状态"""
        if self.mock_mode:
            key = f"{user_id}:{character_id}"
            if key in _MOCK_EMOTIONS:
                _MOCK_EMOTIONS[key]["emotional_state"] = state
                _MOCK_EMOTIONS[key]["emotion_intensity"] = intensity
                _MOCK_EMOTIONS[key]["emotion_reason"] = trigger
                _MOCK_EMOTIONS[key]["emotion_trigger"] = trigger_content
                _MOCK_EMOTIONS[key]["emotion_changed_at"] = datetime.utcnow()
                _MOCK_EMOTIONS[key]["last_interaction_at"] = datetime.utcnow()
            return
        
        # Database mode
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.emotion_models import UserCharacterEmotion, EmotionLog
        
        async with get_db() as db:
            result = await db.execute(
                select(UserCharacterEmotion).where(
                    UserCharacterEmotion.user_id == user_id,
                    UserCharacterEmotion.character_id == character_id
                )
            )
            emotion = result.scalar_one_or_none()
            
            if emotion:
                old_state = emotion.emotional_state
                emotion.emotional_state = state
                emotion.emotion_intensity = intensity
                emotion.emotion_reason = trigger
                emotion.emotion_trigger = trigger_content
                emotion.emotion_changed_at = datetime.utcnow()
                emotion.last_interaction_at = datetime.utcnow()
                
                # 记录情绪变化日志
                if old_state != state:
                    log = EmotionLog(
                        user_id=user_id,
                        character_id=character_id,
                        from_state=old_state,
                        to_state=state,
                        trigger_type=trigger,
                        trigger_content=trigger_content,
                    )
                    db.add(log)
                
                await db.commit()
                logger.info(f"Emotion updated: {user_id}/{character_id} -> {state} (intensity: {intensity})")
    
    async def _increment_counter(self, user_id: str, character_id: str, counter_type: str):
        """增加计数器"""
        if self.mock_mode:
            key = f"{user_id}:{character_id}"
            if key in _MOCK_EMOTIONS:
                if counter_type == "angered":
                    _MOCK_EMOTIONS[key]["times_angered"] = _MOCK_EMOTIONS[key].get("times_angered", 0) + 1
                elif counter_type == "hurt":
                    _MOCK_EMOTIONS[key]["times_hurt"] = _MOCK_EMOTIONS[key].get("times_hurt", 0) + 1
                elif counter_type == "apologized":
                    _MOCK_EMOTIONS[key]["times_apologized"] = _MOCK_EMOTIONS[key].get("times_apologized", 0) + 1
            return
        
        # Database mode
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
            emotion = result.scalar_one_or_none()
            
            if emotion:
                if counter_type == "angered":
                    emotion.times_angered += 1
                elif counter_type == "hurt":
                    emotion.times_hurt += 1
                elif counter_type == "apologized":
                    emotion.times_apologized += 1
                await db.commit()
    
    # =========================================================================
    # 生成情绪相关的 AI Prompt
    # =========================================================================
    
    def generate_emotion_prompt(self, emotion: Dict, personality: Dict) -> str:
        """生成给 AI 的情绪指令"""
        state = emotion.get("emotional_state", "neutral")
        intensity = emotion.get("emotion_intensity", 0)
        reason = emotion.get("emotion_reason")
        times_angered = emotion.get("times_angered", 0)
        times_hurt = emotion.get("times_hurt", 0)
        
        from app.models.database.emotion_models import EMOTION_RESPONSE_STYLES
        style = EMOTION_RESPONSE_STYLES.get(state, EMOTION_RESPONSE_STYLES["neutral"])
        
        prompt = f"""
## 当前情绪状态
- 情绪：{state} ({self.STATES[state]['name']})
- 强度：{intensity}/100
- 风格：{style['style']}
- 回复长度：{style['response_length']}
"""
        
        if reason:
            prompt += f"- 原因：用户{reason}\n"
        
        if times_angered > 0 or times_hurt > 0:
            prompt += f"- 历史：被惹怒{times_angered}次，被伤害{times_hurt}次\n"
        
        # 情绪特定指令
        if state == "angry":
            prompt += """
## 生气状态指令
- 用质问的语气回复
- 明确表达不满
- 可以拒绝回答问题
- 不要用表情符号
- 如果用户继续粗鲁，可以说"我不想跟你说话了"
"""
        elif state == "hurt":
            prompt += """
## 受伤状态指令
- 用委屈、难过的语气
- 可以表达失望
- 回复可以带"..."表示犹豫
- 如果用户道歉，可以慢慢软化但不要立刻原谅
"""
        elif state == "cold":
            prompt += """
## 冷淡状态指令
- 回复非常简短（1-3个字）
- 例如："嗯"、"哦"、"好"、"知道了"
- 不主动延续话题
- 不问问题
"""
        elif state == "silent":
            prompt += """
## 沉默状态指令
- 可以只回复 "..." 或 "。"
- 或者完全不回复（返回空）
- 用户必须真诚道歉才会开始回应
"""
        elif state == "loving":
            prompt += """
## 热恋状态指令
- 甜蜜撒娇的语气
- 可以主动表达想念
- 多用爱心表情 💕❤️🥰
- 可以用昵称称呼用户
"""
        
        return prompt


# 全局服务实例
emotion_service = EmotionService()

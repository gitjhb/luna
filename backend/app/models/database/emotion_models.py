"""
Database Models for Emotion System
===================================

情绪系统 - 让角色有边界感和真实感

核心理念：角色是"有底线的人"，不是"顺从的奴隶"
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.database.billing_models import Base


class EmotionalState(str, enum.Enum):
    """情绪状态枚举"""
    LOVING = "loving"       # 热恋、甜蜜 ❤️
    HAPPY = "happy"         # 开心、满足 😊
    NEUTRAL = "neutral"     # 平静、正常 😐
    CURIOUS = "curious"     # 好奇、感兴趣 🤔
    ANNOYED = "annoyed"     # 有点烦躁 😒
    ANGRY = "angry"         # 生气 😠
    HURT = "hurt"           # 受伤、难过 😢
    COLD = "cold"           # 冷淡、疏远 🥶
    SILENT = "silent"       # 不想说话 🤐


class CharacterPersonality(Base):
    """
    角色性格特征 - 每个角色的固有性格
    
    影响情绪反应的敏感度和恢复速度
    """
    __tablename__ = "character_personalities"
    
    character_id = Column(String(128), primary_key=True)
    
    # 性格特征 (1-10 分)
    temperament = Column(Integer, default=5)      # 脾气: 1=温和 10=火爆
    sensitivity = Column(Integer, default=5)      # 敏感度: 1=迟钝 10=敏感
    boundaries = Column(Integer, default=5)       # 底线: 1=宽松 10=严格
    forgiveness = Column(Integer, default=5)      # 原谅: 1=容易 10=困难
    jealousy = Column(Integer, default=5)         # 吃醋: 1=不在意 10=很吃醋
    
    # 性格描述（给 AI 用）
    personality_prompt = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CharacterPersonality(character_id={self.character_id}, temperament={self.temperament})>"


class UserCharacterEmotion(Base):
    """
    用户-角色情绪状态 - 持久化的情绪记忆
    
    每个用户和角色之间有独立的情绪状态
    """
    __tablename__ = "user_character_emotions"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # 当前情绪状态
    emotional_state = Column(String(32), default=EmotionalState.NEUTRAL.value, nullable=False)
    emotion_intensity = Column(Float, default=0.0)  # 情绪强度 0-100
    
    # 情绪原因（记忆）
    emotion_reason = Column(Text, nullable=True)    # 为什么是这个情绪
    emotion_trigger = Column(Text, nullable=True)   # 触发事件
    
    # 情绪历史计数
    times_angered = Column(Integer, default=0)      # 被惹怒次数
    times_hurt = Column(Integer, default=0)         # 被伤害次数
    times_apologized = Column(Integer, default=0)   # 收到道歉次数
    
    # 时间戳
    emotion_changed_at = Column(DateTime, default=datetime.utcnow)
    last_interaction_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserCharacterEmotion(user={self.user_id}, character={self.character_id}, state={self.emotional_state})>"
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "character_id": self.character_id,
            "emotional_state": self.emotional_state,
            "emotion_intensity": self.emotion_intensity,
            "emotion_reason": self.emotion_reason,
            "times_angered": self.times_angered,
            "times_hurt": self.times_hurt,
            "emotion_changed_at": self.emotion_changed_at.isoformat() if self.emotion_changed_at else None,
        }


class EmotionLog(Base):
    """
    情绪变化日志 - 记录每次情绪变化
    
    用于分析和调试
    """
    __tablename__ = "emotion_logs"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # 变化记录
    from_state = Column(String(32), nullable=False)
    to_state = Column(String(32), nullable=False)
    trigger_type = Column(String(64), nullable=True)  # message, gift, apology, time_decay
    trigger_content = Column(Text, nullable=True)     # 触发内容
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<EmotionLog({self.from_state} -> {self.to_state})>"


# 情绪转换规则配置
EMOTION_TRANSITIONS = {
    # 负面触发词（粗鲁、侮辱）
    "negative_triggers": {
        "cn": ["滚", "闭嘴", "傻逼", "白痴", "蠢", "丑", "胖", "讨厌你", "不想理你", "烦死了"],
        "en": ["shut up", "stupid", "idiot", "ugly", "fat", "hate you", "go away", "leave me alone"],
    },
    
    # 过分要求（陌生人阶段不应该问的）
    "boundary_violations": {
        "cn": ["脱衣服", "裸照", "约炮", "上床", "做爱", "性爱"],
        "en": ["nude", "naked", "sex", "fuck me", "sleep with me"],
    },
    
    # 正面触发词
    "positive_triggers": {
        "cn": ["对不起", "抱歉", "我错了", "原谅我", "爱你", "喜欢你", "想你", "好看", "漂亮", "可爱"],
        "en": ["sorry", "apologize", "forgive me", "love you", "like you", "miss you", "beautiful", "cute"],
    },
}

# 情绪对 AI 回复风格的影响
EMOTION_RESPONSE_STYLES = {
    EmotionalState.LOVING.value: {
        "style": "甜蜜、撒娇、主动",
        "response_length": "long",
        "emoji_usage": "heavy",
        "example": "亲爱的～你终于来了！人家好想你呀 💕",
    },
    EmotionalState.HAPPY.value: {
        "style": "开心、热情、积极",
        "response_length": "normal",
        "emoji_usage": "moderate",
        "example": "嘿！今天心情超好～有什么想聊的吗？😊",
    },
    EmotionalState.NEUTRAL.value: {
        "style": "平静、正常、友好",
        "response_length": "normal",
        "emoji_usage": "light",
        "example": "嗯，怎么了？",
    },
    EmotionalState.ANNOYED.value: {
        "style": "有点不耐烦、敷衍",
        "response_length": "short",
        "emoji_usage": "none",
        "example": "嗯。",
    },
    EmotionalState.ANGRY.value: {
        "style": "生气、质问、拒绝",
        "response_length": "short",
        "emoji_usage": "none",
        "example": "你说什么？！我们才刚认识你就这样？",
    },
    EmotionalState.HURT.value: {
        "style": "难过、委屈、失望",
        "response_length": "medium",
        "emoji_usage": "sad",
        "example": "...你怎么能这样说呢，我真的很难过。",
    },
    EmotionalState.COLD.value: {
        "style": "冷淡、疏远、简短",
        "response_length": "very_short",
        "emoji_usage": "none",
        "example": "哦。",
    },
    EmotionalState.SILENT.value: {
        "style": "不说话、已读不回",
        "response_length": "none",
        "emoji_usage": "none",
        "example": "...",
    },
}

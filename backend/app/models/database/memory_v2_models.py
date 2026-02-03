"""
Memory System v2 - Database Models (using ChatBase)
===================================================

These models integrate with the existing ChatBase for consistent table creation.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, Index
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
import uuid

# Import the existing ChatBase
from app.models.database.chat_models import Base


def generate_uuid():
    return str(uuid.uuid4())


class SemanticMemory(Base):
    """
    语义记忆表 - 用户特征和偏好
    Stores user profile information learned through conversations
    """
    __tablename__ = "semantic_memories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)
    
    # 基本信息
    user_name = Column(String(64))
    user_nickname = Column(String(64))  # 用户希望被叫的昵称
    birthday = Column(String(32))
    occupation = Column(String(128))
    location = Column(String(128))
    
    # 偏好 (JSON 数组)
    likes = Column(JSON, default=[])
    dislikes = Column(JSON, default=[])
    interests = Column(JSON, default=[])
    
    # 性格特征
    personality_traits = Column(JSON, default=[])
    communication_style = Column(String(64))
    
    # 关系相关
    relationship_status = Column(String(32))
    pet_names = Column(JSON, default=[])  # 互相的昵称
    important_dates = Column(JSON, default={})  # 纪念日等
    shared_jokes = Column(JSON, default=[])  # 共同的梗
    
    # 敏感话题
    sensitive_topics = Column(JSON, default=[])  # 避免提及的话题
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 唯一约束
    __table_args__ = (
        Index('idx_semantic_user_char', 'user_id', 'character_id', unique=True),
    )
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "character_id": self.character_id,
            "user_name": self.user_name,
            "user_nickname": self.user_nickname,
            "birthday": self.birthday,
            "occupation": self.occupation,
            "location": self.location,
            "likes": self.likes or [],
            "dislikes": self.dislikes or [],
            "interests": self.interests or [],
            "personality_traits": self.personality_traits or [],
            "communication_style": self.communication_style,
            "relationship_status": self.relationship_status,
            "pet_names": self.pet_names or [],
            "important_dates": self.important_dates or {},
            "shared_jokes": self.shared_jokes or [],
            "sensitive_topics": self.sensitive_topics or [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EpisodicMemory(Base):
    """
    情节记忆表 - 重要事件和对话
    Stores significant events like confessions, fights, milestones
    """
    __tablename__ = "episodic_memories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    memory_id = Column(String(32), unique=True, nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)
    
    # 事件内容
    event_type = Column(String(32), nullable=False)  # confession/fight/gift/milestone/...
    summary = Column(Text, nullable=False)           # 事件摘要
    key_dialogue = Column(JSON, default=[])          # 关键对话
    emotion_state = Column(String(32))               # 当时的情绪
    
    # 元数据
    importance = Column(Integer, default=2)          # 1-4
    strength = Column(Float, default=1.0)            # 记忆强度 0.0-1.0
    
    # 回忆统计
    recall_count = Column(Integer, default=0)
    last_recalled = Column(DateTime)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 索引
    __table_args__ = (
        Index('idx_episodic_user_char', 'user_id', 'character_id'),
        Index('idx_episodic_importance', 'importance'),
    )
    
    def to_dict(self):
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "event_type": self.event_type,
            "summary": self.summary,
            "key_dialogue": self.key_dialogue or [],
            "emotion_state": self.emotion_state,
            "importance": self.importance,
            "strength": self.strength,
            "recall_count": self.recall_count,
            "last_recalled": self.last_recalled.isoformat() if self.last_recalled else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MemoryExtractionLog(Base):
    """
    记忆提取日志 - 调试用
    Logs extraction events for debugging
    """
    __tablename__ = "memory_extraction_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False)
    character_id = Column(String(64), nullable=False)
    
    # 提取内容
    source_message = Column(Text)
    extracted_semantic = Column(JSON)
    extracted_episodic = Column(JSON)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

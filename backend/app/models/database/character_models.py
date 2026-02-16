"""
Character Models - 角色数据库模型

存储所有角色的配置信息，支持动态管理
"""

import os
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON

# Use JSONB for PostgreSQL, JSON for SQLite
# Check DATABASE_URL to determine which to use
_db_url = os.getenv("DATABASE_URL", "")
if "postgresql" in _db_url:
    from sqlalchemy.dialects.postgresql import JSONB as JSONType
else:
    # For SQLite and other databases, use generic JSON
    JSONType = JSON

from app.models.database.billing_models import Base


class Character(Base):
    """
    角色模型
    
    存储角色的所有配置信息，包括基本信息、性格、prompt等
    """
    __tablename__ = "characters"
    
    # 基础信息
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=True)  # 英文名
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)  # 英文描述
    
    # 媒体资源
    avatar_url = Column(String(512), nullable=True)
    background_url = Column(String(512), nullable=True)
    intro_video_url = Column(String(512), nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)  # 是否启用
    is_spicy = Column(Boolean, default=False, nullable=False)  # 是否是 Spicy 角色
    sort_order = Column(Integer, default=0, nullable=False)  # 排序权重
    
    # 人设信息
    age = Column(Integer, nullable=True)
    zodiac = Column(String(32), nullable=True)  # 星座
    occupation = Column(String(64), nullable=True)  # 职业
    mbti = Column(String(8), nullable=True)
    birthday = Column(String(32), nullable=True)
    height = Column(String(16), nullable=True)
    location = Column(String(64), nullable=True)
    
    # 性格标签和爱好 (JSON 数组)
    personality_traits = Column(JSONType, default=list, nullable=False)  # ["温柔", "善解人意"]
    personality_traits_en = Column(JSONType, default=list, nullable=True)
    hobbies = Column(JSONType, default=list, nullable=False)  # ["烘焙", "看电影"]
    hobbies_en = Column(JSONType, default=list, nullable=True)
    
    # 性格参数 (JSON 对象)
    personality = Column(JSONType, default=dict, nullable=False)
    # {
    #   "temperament": 3,   # 脾气 1-10
    #   "sensitivity": 5,   # 敏感度 1-10
    #   "boundaries": 5,    # 边界感 1-10
    #   "forgiveness": 7,   # 原谅度 1-10
    #   "jealousy": 4       # 醋意 1-10
    # }
    
    # Greeting 和 Prompt
    greeting = Column(Text, nullable=True)
    greeting_en = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    system_prompt_en = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self, lang: str = "zh") -> dict:
        """转换为字典，支持多语言"""
        is_en = lang == "en"
        return {
            "character_id": self.id,
            "name": self.name_en if is_en and self.name_en else self.name,
            "description": self.description_en if is_en and self.description_en else self.description,
            "avatar_url": self.avatar_url,
            "background_url": self.background_url,
            "intro_video_url": self.intro_video_url,
            "is_active": self.is_active,
            "is_spicy": self.is_spicy,
            "sort_order": self.sort_order,
            "age": self.age,
            "zodiac": self.zodiac,
            "occupation": self.occupation,
            "mbti": self.mbti,
            "birthday": self.birthday,
            "height": self.height,
            "location": self.location,
            "personality_traits": self.personality_traits_en if is_en and self.personality_traits_en else self.personality_traits,
            "hobbies": self.hobbies_en if is_en and self.hobbies_en else self.hobbies,
            "personality": self.personality,
            "greeting": self.greeting_en if is_en and self.greeting_en else self.greeting,
            "system_prompt": self.system_prompt_en if is_en and self.system_prompt_en else self.system_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_public_dict(self, lang: str = "zh") -> dict:
        """公开信息（不含 system_prompt）"""
        data = self.to_dict(lang)
        del data["system_prompt"]
        return data


# SQL for creating indexes
"""
CREATE INDEX idx_characters_is_active ON characters(is_active);
CREATE INDEX idx_characters_sort_order ON characters(sort_order);
"""

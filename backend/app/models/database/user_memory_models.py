"""
User Memory Model
=================

简单直观的记忆存储表，与前端 MemoryItem 接口一一对应。
后端 LLM 自动提取，前端 CRUD 管理。
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from datetime import datetime
import uuid

from app.models.database.chat_models import Base


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class UserMemory(Base):
    """
    用户记忆表

    与前端 MemoryItem 接口完全对应：
    - category: preference | opinion | date | profile
    - title:    简短标签，如 "喜欢黑咖啡"
    - content:  完整记忆内容
    - source:   auto (LLM 提取) | manual (用户手动添加)
    - importance: 1=低 | 2=中 | 3=高
    """

    __tablename__ = "user_memories"

    id           = Column(String(36), primary_key=True, default=_gen_uuid)
    user_id      = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)

    category   = Column(String(16), nullable=False)   # preference | opinion | date | profile
    title      = Column(String(128), nullable=False)  # 短标签
    content    = Column(Text, nullable=False)          # 完整内容
    source     = Column(String(8),  nullable=False, default="auto")   # auto | manual
    importance = Column(Integer, nullable=False, default=2)            # 1 | 2 | 3

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_memory_user_char", "user_id", "character_id"),
        Index("idx_user_memory_category",  "user_id", "character_id", "category"),
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "character_id": self.character_id,
            "category":     self.category,
            "title":        self.title,
            "content":      self.content,
            "source":       self.source,
            "importance":   self.importance,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }

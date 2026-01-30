"""
SQLAlchemy Models for Chat - Sessions and Messages
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class ChatSession(Base):
    """Chat session between a user and a character"""
    __tablename__ = "chat_sessions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    character_id = Column(String(36), nullable=False, index=True)
    character_name = Column(String(100), nullable=False)
    character_avatar = Column(String(500), nullable=True)
    character_background = Column(String(500), nullable=True)
    total_messages = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to messages
    messages = relationship("ChatMessageDB", back_populates="session", cascade="all, delete-orphan")
    
    # Composite index for user+character lookup
    __table_args__ = (
        Index('idx_user_character', 'user_id', 'character_id'),
    )
    
    def to_dict(self):
        return {
            "session_id": self.id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "character_avatar": self.character_avatar,
            "character_background": self.character_background,
            "total_messages": self.total_messages,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ChatMessageDB(Base):
    """Individual chat message"""
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Extra data (optional)
    extra_data = Column(JSON, nullable=True)  # For storing additional info
    
    # Relationship back to session
    session = relationship("ChatSession", back_populates="messages")
    
    def to_dict(self):
        return {
            "message_id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at,
        }

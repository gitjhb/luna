"""
Event Memory Database Models
============================

Stores generated story content for milestone events like:
- first_date: 第一次约会
- first_confession: 第一次表白
- first_kiss: 第一次亲吻
- first_nsfw: 第一次亲密时刻

Each event generates a unique, immersive story (1000-2000 characters)
that becomes a permanent memory in the user-character relationship.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid

from app.models.database.billing_models import Base


class EventMemory(Base):
    """
    Event Memory Model
    
    Stores generated story content for milestone events.
    Each user-character pair can have multiple event memories,
    but only one of each event_type.
    """
    __tablename__ = "event_memories"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # Event type: first_date, first_confession, first_kiss, first_nsfw, etc.
    event_type = Column(String(64), nullable=False, index=True)
    
    # Generated story content (1000-2000 characters)
    # Contains immersive narrative with dialogue, scene descriptions, emotional development
    story_content = Column(Text, nullable=False)
    
    # Context summary at the time of event trigger
    # Captures relationship state, recent conversation themes, etc.
    context_summary = Column(Text, nullable=True)
    
    # Relationship stats at the time of event
    intimacy_level = Column(String(32), nullable=True)  # e.g., "friends", "lovers"
    emotion_state = Column(String(32), nullable=True)   # e.g., "happy", "loving"
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Composite index for efficient lookups
    __table_args__ = (
        Index('idx_event_memory_user_character', 'user_id', 'character_id'),
        Index('idx_event_memory_unique_event', 'user_id', 'character_id', 'event_type', unique=True),
    )
    
    def __repr__(self):
        return f"<EventMemory(user_id={self.user_id}, character_id={self.character_id}, event_type={self.event_type})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "event_type": self.event_type,
            "story_content": self.story_content,
            "context_summary": self.context_summary,
            "intimacy_level": self.intimacy_level,
            "emotion_state": self.emotion_state,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


# =============================================================================
# Event Types Definition
# =============================================================================

class EventType:
    """Supported milestone event types"""
    FIRST_CHAT = "first_chat"           # 第一次聊天 (通常不生成长剧情)
    FIRST_DATE = "first_date"           # 第一次约会
    FIRST_CONFESSION = "first_confession"  # 第一次表白
    FIRST_KISS = "first_kiss"           # 第一次亲吻
    FIRST_NSFW = "first_nsfw"           # 第一次亲密时刻
    ANNIVERSARY = "anniversary"         # 纪念日
    BREAKUP = "breakup"                 # 分手 (如果实现)
    RECONCILIATION = "reconciliation"   # 和好
    
    # Events that generate stories
    STORY_EVENTS = [
        FIRST_DATE,
        FIRST_CONFESSION,
        FIRST_KISS,
        FIRST_NSFW,
        ANNIVERSARY,
        RECONCILIATION,
    ]
    
    @classmethod
    def is_story_event(cls, event_type: str) -> bool:
        """Check if this event type generates a story"""
        return event_type in cls.STORY_EVENTS

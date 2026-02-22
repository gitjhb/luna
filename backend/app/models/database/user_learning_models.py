"""
User Learning Models
====================

Models for learning and tracking user communication preferences.
Migrated from Mio's user-learning.js to Luna.

Features:
- UserCommunicationStyle: learned speaking style preferences
- UserTopicInterest: topic interest graph with scores
- UserActivityPattern: when user is most active
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum

from .billing_models import Base  # Use existing Base


class CommunicationTone(str, enum.Enum):
    """Communication tone enumeration"""
    FORMAL = "formal"
    CASUAL = "casual"
    PLAYFUL = "playful"
    ROMANTIC = "romantic"


class MessageLength(str, enum.Enum):
    """Preferred message length"""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class EmojiUsage(str, enum.Enum):
    """Emoji usage frequency"""
    NONE = "none"
    RARE = "rare"
    MODERATE = "moderate"
    FREQUENT = "frequent"


class UserCommunicationStyle(Base):
    """
    Learned communication style for a user.
    
    Tracks how the user prefers to communicate:
    - Message length preferences
    - Emoji usage patterns
    - Communication tone (formal/casual/playful/romantic)
    - Common phrases they use
    """
    __tablename__ = "user_communication_styles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    
    # Core style attributes
    message_length = Column(String(20), default="medium")  # short/medium/long
    emoji_usage = Column(String(20), default="moderate")   # none/rare/moderate/frequent
    tone = Column(String(20), default="casual")           # formal/casual/playful/romantic
    punctuation_style = Column(String(20), default="normal")  # minimal/normal/expressive
    
    # Communication patterns
    communication_style = Column(String(20), default="direct")  # direct/indirect/expressive
    emotional_expression = Column(String(20), default="moderate")  # reserved/moderate/expressive
    
    # Common phrases (JSON list)
    common_phrases = Column(JSON, default=list)
    
    # Analysis metadata
    analysis_count = Column(Integer, default=0)
    total_messages_analyzed = Column(Integer, default=0)
    last_analysis_at = Column(DateTime, nullable=True)
    confidence_score = Column(Float, default=0.0)  # 0-1, increases with more data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<UserCommunicationStyle(user_id={self.user_id}, tone={self.tone})>"
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "message_length": self.message_length,
            "emoji_usage": self.emoji_usage,
            "tone": self.tone,
            "punctuation_style": self.punctuation_style,
            "communication_style": self.communication_style,
            "emotional_expression": self.emotional_expression,
            "common_phrases": self.common_phrases or [],
            "analysis_count": self.analysis_count,
            "confidence_score": self.confidence_score,
            "last_analysis_at": self.last_analysis_at.isoformat() if self.last_analysis_at else None,
        }


class UserTopicInterest(Base):
    """
    Topic interest graph for a user.
    
    Tracks what topics the user likes to discuss,
    with weighted scores based on frequency and engagement.
    """
    __tablename__ = "user_topic_interests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    
    # Topic info
    topic = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=True)  # entertainment/sports/tech/etc.
    
    # Scoring
    interest_score = Column(Float, default=1.0)  # Accumulated weight
    mention_count = Column(Integer, default=1)
    engagement_score = Column(Float, default=0.0)  # How deeply they engage with topic
    
    # Last interaction
    last_mentioned_at = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<UserTopicInterest(user_id={self.user_id}, topic={self.topic}, score={self.interest_score})>"
    
    def to_dict(self):
        return {
            "topic": self.topic,
            "category": self.category,
            "interest_score": self.interest_score,
            "mention_count": self.mention_count,
            "engagement_score": self.engagement_score,
            "last_mentioned_at": self.last_mentioned_at.isoformat() if self.last_mentioned_at else None,
        }


class UserActivityPattern(Base):
    """
    Activity pattern tracking for a user.
    
    Learns when the user is typically active to:
    - Time proactive messages appropriately
    - Understand their schedule
    - Adapt response timing
    """
    __tablename__ = "user_activity_patterns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), unique=True, index=True, nullable=False)
    
    # Hourly activity distribution (24 slots)
    # JSON: [count_for_hour_0, count_for_hour_1, ..., count_for_hour_23]
    hourly_activity = Column(JSON, default=lambda: [0] * 24)
    
    # Weekly activity distribution (7 slots, 0=Sunday)
    # JSON: [count_for_sunday, count_for_monday, ..., count_for_saturday]
    weekday_activity = Column(JSON, default=lambda: [0] * 7)
    
    # Total message count for statistical significance
    total_messages = Column(Integer, default=0)
    
    # Derived insights (computed periodically)
    peak_hours = Column(JSON, default=list)  # Top 3 active hours
    preferred_time_slots = Column(JSON, default=list)  # morning/afternoon/evening/night
    
    # Response patterns
    avg_response_time_seconds = Column(Float, nullable=True)  # How quickly they respond
    
    # Timestamps
    last_active_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<UserActivityPattern(user_id={self.user_id}, total_messages={self.total_messages})>"
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "hourly_activity": self.hourly_activity or [0] * 24,
            "weekday_activity": self.weekday_activity or [0] * 7,
            "total_messages": self.total_messages,
            "peak_hours": self.peak_hours or [],
            "preferred_time_slots": self.preferred_time_slots or [],
            "avg_response_time_seconds": self.avg_response_time_seconds,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }


class UserLearningSnapshot(Base):
    """
    Periodic snapshot of all learning data for a user.
    
    Used for:
    - Historical tracking
    - Backup/recovery
    - Analysis of learning evolution
    """
    __tablename__ = "user_learning_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    
    # Full snapshot data (JSON blob)
    style_data = Column(JSON, nullable=True)
    activity_data = Column(JSON, nullable=True)
    top_interests = Column(JSON, nullable=True)  # Top 10 interests
    
    # Snapshot metadata
    snapshot_reason = Column(String(50), default="periodic")  # periodic/manual/milestone
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<UserLearningSnapshot(user_id={self.user_id}, created_at={self.created_at})>"

"""
Stats & Events Database Models
==============================

Models for tracking user-character relationship statistics and events.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.models.database.billing_models import Base
import enum


class EventType(str, enum.Enum):
    FIRST_MEET = "first_meet"
    LEVEL_UP = "level_up"
    GIFT = "gift"
    STREAK_MILESTONE = "streak_milestone"
    MESSAGE_MILESTONE = "message_milestone"
    SPECIAL_DIALOGUE = "special_dialogue"
    CONFESSION = "confession"
    DATE = "date"
    COLD_WAR = "cold_war"
    MAKEUP = "makeup"


class UserCharacterStats(Base):
    """Track relationship statistics between user and character."""
    __tablename__ = "user_character_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)
    
    # Stats
    streak_days = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_gifts = Column(Integer, default=0)
    special_events = Column(Integer, default=0)
    
    # Tracking
    last_interaction_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        # Unique constraint on user_id + character_id
        {"sqlite_autoincrement": True},
    )


class UserCharacterEvent(Base):
    """Track significant events in user-character relationship."""
    __tablename__ = "user_character_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)
    
    event_type = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for extra data
    
    created_at = Column(DateTime, server_default=func.now())


class UserCharacterMemory(Base):
    """AI memories about user for personalization."""
    __tablename__ = "user_character_memories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    importance = Column(String(16), default="medium")  # low, medium, high
    source = Column(String(32), nullable=True)  # chat, gift, event, etc.
    
    created_at = Column(DateTime, server_default=func.now())


class UserCharacterGallery(Base):
    """Generated images with character."""
    __tablename__ = "user_character_gallery"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    character_id = Column(String(64), nullable=False, index=True)
    
    image_url = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

"""
Database Models for Proactive Messaging System
===============================================

Tracks proactive message history and cooldowns for user-character relationships.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, JSON, Boolean
import uuid

from app.models.database.billing_models import Base


class ProactiveHistory(Base):
    """
    Proactive Message History

    Tracks when proactive messages were sent to users.
    Used for cooldown management and analytics.
    """
    __tablename__ = "proactive_history"

    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # Message type: good_morning, good_night, miss_you, check_in, anniversary, random_share
    message_type = Column(String(32), nullable=False, index=True)
    
    # The actual message sent (for debugging/analytics)
    message_content = Column(String(2000), nullable=True)
    
    # Whether message was delivered successfully
    delivered = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<ProactiveHistory(user_id={self.user_id}, type={self.message_type})>"


class UserProactiveSettings(Base):
    """
    User Proactive Settings

    Per-user settings for proactive messaging preferences.
    """
    __tablename__ = "user_proactive_settings"

    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Whether proactive messages are enabled for this user
    enabled = Column(Boolean, default=True, nullable=False)
    
    # User timezone for determining greeting windows (e.g., "America/Los_Angeles")
    timezone = Column(String(64), default="America/Los_Angeles", nullable=False)
    
    # Preferred morning greeting window (hour, 24h format)
    morning_start = Column(Integer, default=7, nullable=False)
    morning_end = Column(Integer, default=9, nullable=False)
    
    # Preferred evening greeting window
    evening_start = Column(Integer, default=21, nullable=False)
    evening_end = Column(Integer, default=23, nullable=False)
    
    # Special dates (JSON: {"birthday": "1995-03-15", "anniversary": "2024-01-20"})
    special_dates = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Ensure one record per user
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_proactive_settings'),
    )

    def __repr__(self):
        return f"<UserProactiveSettings(user_id={self.user_id}, enabled={self.enabled})>"


# Database initialization script for indexes
"""
-- SQL to create additional indexes for proactive system

CREATE INDEX idx_proactive_history_user_id ON proactive_history(user_id);
CREATE INDEX idx_proactive_history_message_type ON proactive_history(message_type);
CREATE INDEX idx_proactive_history_created_at ON proactive_history(created_at);
CREATE INDEX idx_user_proactive_settings_user_id ON user_proactive_settings(user_id);
"""

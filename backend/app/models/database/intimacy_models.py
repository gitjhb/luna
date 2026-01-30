"""
Database Models for Intimacy System
====================================

SQLAlchemy models for UserIntimacy and IntimacyActionLog.
Tracks user-character relationship progression and XP history.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Integer, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid

from app.models.database.billing_models import Base


class UserIntimacy(Base):
    """
    User-Character Intimacy Model

    Tracks the relationship level between a user and a specific AI character.
    Each user can have different intimacy levels with different characters.
    """
    __tablename__ = "user_intimacy"

    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)

    # XP & Level
    total_xp = Column(Float, default=0.0, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)
    intimacy_stage = Column(String(32), default="strangers", nullable=False)

    # Daily XP tracking (resets every 24 hours)
    daily_xp_earned = Column(Float, default=0.0, nullable=False)
    last_daily_reset = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Streak tracking
    streak_days = Column(Integer, default=0, nullable=False)
    last_interaction_date = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Ensure one record per user-character pair
    __table_args__ = (
        UniqueConstraint('user_id', 'character_id', name='uq_user_character_intimacy'),
    )

    def __repr__(self):
        return f"<UserIntimacy(user_id={self.user_id}, character_id={self.character_id}, level={self.current_level})>"

    def needs_daily_reset(self) -> bool:
        """Check if daily XP counter should be reset"""
        if not self.last_daily_reset:
            return True

        now = datetime.utcnow()
        time_since_reset = now - self.last_daily_reset
        return time_since_reset.total_seconds() >= 86400  # 24 hours

    def apply_daily_reset(self) -> None:
        """Reset daily XP counter"""
        if self.needs_daily_reset():
            self.daily_xp_earned = 0.0
            self.last_daily_reset = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    def update_streak(self) -> None:
        """Update interaction streak"""
        today = date.today()

        if self.last_interaction_date is None:
            self.streak_days = 1
        elif self.last_interaction_date == today:
            # Already interacted today, no change
            pass
        elif (today - self.last_interaction_date).days == 1:
            # Consecutive day, increment streak
            self.streak_days += 1
        else:
            # Streak broken, reset to 1
            self.streak_days = 1

        self.last_interaction_date = today
        self.updated_at = datetime.utcnow()


class IntimacyActionLog(Base):
    """
    Intimacy Action Log Model

    Tracks individual XP-earning actions for cooldown management
    and history/analytics purposes.
    """
    __tablename__ = "intimacy_action_logs"

    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)

    # Action details
    action_type = Column(String(32), nullable=False, index=True)
    # Action types: message, continuous_chat, checkin, emotional, voice, share

    xp_awarded = Column(Float, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<IntimacyActionLog(user_id={self.user_id}, action={self.action_type}, xp={self.xp_awarded})>"


# Database initialization script for indexes
"""
-- SQL to create additional indexes for intimacy system

CREATE INDEX idx_user_intimacy_user_id ON user_intimacy(user_id);
CREATE INDEX idx_user_intimacy_character_id ON user_intimacy(character_id);
CREATE INDEX idx_user_intimacy_level ON user_intimacy(current_level);
CREATE INDEX idx_intimacy_action_logs_user_id ON intimacy_action_logs(user_id);
CREATE INDEX idx_intimacy_action_logs_character_id ON intimacy_action_logs(character_id);
CREATE INDEX idx_intimacy_action_logs_action_type ON intimacy_action_logs(action_type);
CREATE INDEX idx_intimacy_action_logs_created_at ON intimacy_action_logs(created_at);
"""

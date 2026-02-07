"""
User Database Models
====================

SQLAlchemy models for user data persistence.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from app.models.database.base import Base


class User(Base):
    """User account model - persists user info across sessions"""
    __tablename__ = "users"
    
    user_id = Column(String(128), primary_key=True)
    firebase_uid = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    
    # Subscription info
    is_subscribed = Column(Boolean, default=False, nullable=False)
    subscription_tier = Column(String(7), default="free", nullable=False)  # free, monthly, yearly
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "firebase_uid": self.firebase_uid,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "is_subscribed": self.is_subscribed,
            "subscription_tier": self.subscription_tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

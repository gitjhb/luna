"""
User Database Models
====================

Core user model and related enums.
This is the single source of truth for User entity.

Author: Luna Team
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum

# Base class for all models - defined here as the root
Base = declarative_base()


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration"""
    FREE = "free"
    PREMIUM = "premium"
    VIP = "vip"


class User(Base):
    """
    Core User model - single source of truth for user identity.
    
    Relationships:
    - 1:1 with UserWallet (credits/moonstone)
    - 1:N with ChatSession (chat history)
    - 1:N with TransactionHistory (payment records)
    - 1:N with UserIntimacy (per-character intimacy)
    """
    __tablename__ = "users"
    
    # Primary identification
    user_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    firebase_uid = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Cross-platform identity
    telegram_id = Column(String(64), unique=True, nullable=True, index=True)  # Telegram user ID
    apple_id = Column(String(128), unique=True, nullable=True, index=True)    # Apple Sign In ID
    
    # Profile
    display_name = Column(String(255))
    avatar_url = Column(String(512))
    preferred_language = Column(String(10), default='en')  # i18n: en, zh, ja, etc.
    
    # Subscription info
    is_subscribed = Column(Boolean, default=False, nullable=False)
    subscription_tier = Column(
        SQLEnum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships (defined here, actual models in their own files)
    wallet = relationship("UserWallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("TransactionHistory", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, email={self.email}, tier={self.subscription_tier})>"
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "firebase_uid": self.firebase_uid,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "is_subscribed": self.is_subscribed,
            "subscription_tier": self.subscription_tier.value if self.subscription_tier else "free",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

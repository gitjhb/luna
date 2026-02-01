"""
Database Models for Billing System
==================================

SQLAlchemy models for User, UserWallet, and TransactionHistory.

Author: Manus AI
Date: January 28, 2026
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum

Base = declarative_base()


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration"""
    FREE = "free"
    PREMIUM = "premium"
    VIP = "vip"


class TransactionType(str, enum.Enum):
    """Transaction type enumeration"""
    PURCHASE = "purchase"
    DEDUCTION = "deduction"
    REFUND = "refund"
    BONUS = "bonus"
    DAILY_REFRESH = "daily_refresh"
    GIFT = "gift"  # 送礼物消费
    REFERRAL = "referral"  # 邀请好友奖励


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    user_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    firebase_uid = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    avatar_url = Column(String(512))
    
    # Subscription info
    is_subscribed = Column(Boolean, default=False, nullable=False)
    subscription_tier = Column(
        SQLEnum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    wallet = relationship("UserWallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("TransactionHistory", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, email={self.email}, tier={self.subscription_tier})>"


class UserWallet(Base):
    """User wallet model for credit management"""
    __tablename__ = "user_wallets"
    
    wallet_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Credit balances
    free_credits = Column(Float, default=10.0, nullable=False)  # Daily refresh credits
    purchased_credits = Column(Float, default=0.0, nullable=False)  # Purchased credits
    total_credits = Column(Float, default=10.0, nullable=False)  # Sum of free + purchased
    
    # Daily refresh tracking
    last_daily_refresh = Column(DateTime, default=datetime.utcnow, nullable=False)
    daily_refresh_amount = Column(Float, default=10.0, nullable=False)  # Amount to refresh daily
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    
    def __repr__(self):
        return f"<UserWallet(user_id={self.user_id}, total_credits={self.total_credits})>"
    
    def needs_daily_refresh(self) -> bool:
        """Check if wallet needs daily refresh"""
        if not self.last_daily_refresh:
            return True
        
        now = datetime.utcnow()
        time_since_refresh = now - self.last_daily_refresh
        return time_since_refresh.total_seconds() >= 86400  # 24 hours
    
    def apply_daily_refresh(self) -> float:
        """Apply daily refresh and return the amount added"""
        if not self.needs_daily_refresh():
            return 0.0
        
        # Add daily refresh amount to free credits
        self.free_credits += self.daily_refresh_amount
        self.total_credits = self.free_credits + self.purchased_credits
        self.last_daily_refresh = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        return self.daily_refresh_amount


class TransactionHistory(Base):
    """Transaction history model for audit trail"""
    __tablename__ = "transaction_history"
    
    transaction_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(
        SQLEnum(TransactionType),
        nullable=False
    )
    amount = Column(Float, nullable=False)  # Positive for additions, negative for deductions
    balance_after = Column(Float, nullable=False)  # Balance after transaction
    
    # Description and extra data
    description = Column(String(512), nullable=True)
    extra_data = Column(JSON, nullable=True)  # Additional data (tokens used, mode, etc.)
    
    # Payment info (for purchases)
    payment_provider = Column(String(64), nullable=True)  # "stripe", "apple", "google"
    payment_id = Column(String(255), nullable=True)  # External payment ID
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<TransactionHistory(transaction_id={self.transaction_id}, type={self.transaction_type}, amount={self.amount})>"


class ChatSession(Base):
    """Chat session model"""
    __tablename__ = "chat_sessions"
    
    session_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # Session metadata
    title = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    total_tokens_used = Column(Integer, default=0, nullable=False)
    total_credits_spent = Column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id}, user_id={self.user_id}, character_id={self.character_id})>"


class ChatMessage(Base):
    """Chat message model"""
    __tablename__ = "chat_messages"
    
    message_id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(128), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message content
    role = Column(String(32), nullable=False)  # "user", "assistant", "system"
    content = Column(String(4096), nullable=False)
    
    # Metadata
    tokens_used = Column(Integer, default=0, nullable=False)
    credits_cost = Column(Float, default=0.0, nullable=False)
    is_spicy_mode = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(message_id={self.message_id}, role={self.role}, session_id={self.session_id})>"


# Database initialization script
"""
-- SQL to create indexes for performance

CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX idx_users_is_subscribed ON users(is_subscribed);
CREATE INDEX idx_user_wallets_user_id ON user_wallets(user_id);
CREATE INDEX idx_transaction_history_user_id ON transaction_history(user_id);
CREATE INDEX idx_transaction_history_created_at ON transaction_history(created_at);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_character_id ON chat_sessions(character_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
"""

"""
Database Models for Referral System
====================================

SQLAlchemy models for user referral tracking.

Author: Clawdbot
Date: January 31, 2025
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid
import secrets

from app.models.database.billing_models import Base


def generate_referral_code() -> str:
    """Generate a unique 8-character referral code"""
    # Use a mix of uppercase letters and digits, excluding ambiguous characters
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class UserReferral(Base):
    """User referral model - tracks referral codes and relationships"""
    __tablename__ = "user_referrals"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # User's own referral code (unique per user)
    referral_code = Column(String(16), unique=True, nullable=False, index=True, default=generate_referral_code)
    
    # Who referred this user (null if not referred)
    referred_by_user_id = Column(String(128), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Tracking
    total_referrals = Column(Integer, default=0, nullable=False)  # How many people this user referred
    total_rewards_earned = Column(Float, default=0.0, nullable=False)  # Total coins earned from referrals
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    referred_at = Column(DateTime, nullable=True)  # When this user was referred (if applicable)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="referral_info")
    referrer = relationship("User", foreign_keys=[referred_by_user_id])
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_referral_referred_by', 'referred_by_user_id'),
        Index('idx_referral_code_lookup', 'referral_code'),
    )
    
    def __repr__(self):
        return f"<UserReferral(user_id={self.user_id}, code={self.referral_code}, referrals={self.total_referrals})>"


class ReferralReward(Base):
    """Tracks individual referral reward events"""
    __tablename__ = "referral_rewards"
    
    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # The referrer who earned this reward
    referrer_user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # The new user who was referred
    referred_user_id = Column(String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Reward details
    reward_amount = Column(Float, nullable=False)  # Coins rewarded
    reward_type = Column(String(32), default="signup", nullable=False)  # signup, first_purchase, etc.
    
    # Status
    is_paid = Column(Boolean, default=True, nullable=False)  # Whether reward has been paid out
    transaction_id = Column(String(128), nullable=True)  # Link to TransactionHistory
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_user_id])
    referred_user = relationship("User", foreign_keys=[referred_user_id])
    
    __table_args__ = (
        Index('idx_reward_referrer', 'referrer_user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ReferralReward(referrer={self.referrer_user_id}, amount={self.reward_amount})>"

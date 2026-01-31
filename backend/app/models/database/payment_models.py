"""
SQLAlchemy Models for Payment - Subscriptions and Purchases
"""

from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PREMIUM = "premium"
    VIP = "vip"


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"        # 购买金币
    SUBSCRIPTION = "subscription"  # 订阅套餐
    GIFT = "gift"                # 送礼物消费
    REFUND = "refund"            # 退款


class UserSubscription(Base):
    """用户订阅信息"""
    __tablename__ = "user_subscriptions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, unique=True, index=True)
    
    # 订阅信息
    tier = Column(String(20), default="free", nullable=False)  # free, premium, vip
    started_at = Column(DateTime, nullable=True)  # 订阅开始时间
    expires_at = Column(DateTime, nullable=True)  # 订阅过期时间
    auto_renew = Column(Boolean, default=False)
    
    # 支付信息
    payment_provider = Column(String(20), nullable=True)  # apple, google, stripe, mock
    provider_subscription_id = Column(String(100), nullable=True)  # 第三方订阅ID
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tier": self.tier,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "auto_renew": self.auto_renew,
            "payment_provider": self.payment_provider,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def is_active(self) -> bool:
        """检查订阅是否有效"""
        if self.tier == "free":
            return True
        if not self.expires_at:
            return False
        return datetime.utcnow() < self.expires_at


class UserWallet(Base):
    """用户钱包"""
    __tablename__ = "user_wallets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, unique=True, index=True)
    
    # 余额
    total_credits = Column(Integer, default=100)  # 总金币
    purchased_credits = Column(Integer, default=0)  # 购买的金币
    bonus_credits = Column(Integer, default=0)  # 赠送的金币
    
    # 每日免费额度
    daily_free_credits = Column(Integer, default=10)
    daily_credits_used = Column(Integer, default=0)
    daily_reset_at = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "total_credits": self.total_credits,
            "purchased_credits": self.purchased_credits,
            "bonus_credits": self.bonus_credits,
            "daily_free_credits": self.daily_free_credits,
            "daily_credits_used": self.daily_credits_used,
        }


class Transaction(Base):
    """交易记录"""
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    
    # 交易信息
    transaction_type = Column(String(20), nullable=False)  # purchase, subscription, gift, refund
    amount = Column(Float, nullable=False)  # 金额（美元）
    credits = Column(Integer, default=0)  # 涉及的金币数
    description = Column(String(200), nullable=True)
    
    # 支付信息
    payment_provider = Column(String(20), nullable=True)  # apple, google, stripe, mock
    provider_transaction_id = Column(String(100), nullable=True)
    status = Column(String(20), default="completed")  # pending, completed, failed, refunded
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "credits": self.credits,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

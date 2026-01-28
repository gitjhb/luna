"""
Pydantic schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Login request with Firebase token."""
    firebase_token: str = Field(..., description="Firebase ID token")
    provider: str = Field(..., description="Auth provider: google or apple")


class UserContext(BaseModel):
    """User context from authentication."""
    user_id: UUID
    email: Optional[str] = None
    display_name: Optional[str] = None
    subscription_tier: str = "free"
    is_subscribed: bool = False
    subscription_expires_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """User profile response."""
    user_id: UUID
    email: Optional[str]
    display_name: Optional[str]
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with user data and wallet."""
    user_id: UUID
    email: Optional[str]
    display_name: Optional[str]
    subscription_tier: str
    wallet: dict
    access_token: str


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatCompletionRequest(BaseModel):
    """Chat completion request."""
    session_id: UUID = Field(..., description="Chat session ID")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    message_id: UUID
    content: str
    tokens_used: int
    credits_deducted: Optional[Decimal] = None
    character_name: str
    created_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    """Single chat message."""
    message_id: UUID
    role: str  # 'user' or 'assistant'
    content: str
    tokens_used: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CreateSessionRequest(BaseModel):
    """Create new chat session request."""
    character_id: UUID


class CreateSessionResponse(BaseModel):
    """Create session response."""
    session_id: UUID
    character_id: UUID
    character_name: str
    character_avatar: Optional[str]
    created_at: datetime


class SessionResponse(BaseModel):
    """Chat session details."""
    session_id: UUID
    title: str
    character_id: UUID
    character_name: str
    character_avatar: Optional[str]
    total_messages: int
    total_credits_spent: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """List of chat sessions."""
    sessions: List[SessionResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class MessageListResponse(BaseModel):
    """List of chat messages."""
    messages: List[ChatMessage]
    total: int
    limit: int
    offset: int
    has_more: bool


# ============================================================================
# Character Schemas
# ============================================================================

class CharacterResponse(BaseModel):
    """Character configuration."""
    character_id: UUID
    name: str
    avatar_url: Optional[str]
    description: str
    personality_traits: List[str]
    tier_required: str
    is_spicy: bool
    tags: List[str]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CharacterListResponse(BaseModel):
    """List of characters."""
    characters: List[CharacterResponse]


class CreateCharacterRequest(BaseModel):
    """Create character request (admin)."""
    name: str = Field(..., min_length=1, max_length=100)
    avatar_url: Optional[str] = None
    description: str = Field(..., min_length=1, max_length=1000)
    personality_traits: List[str] = Field(default_factory=list)
    tier_required: str = Field(default="free")
    is_spicy: bool = Field(default=False)
    system_prompt: str = Field(..., min_length=1)
    spicy_system_prompt: Optional[str] = None
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, ge=50, le=2000)
    tags: List[str] = Field(default_factory=list)


# ============================================================================
# Wallet Schemas
# ============================================================================

class WalletBalance(BaseModel):
    """User wallet balance."""
    total_credits: Decimal
    daily_free_credits: Decimal
    purchased_credits: Decimal
    bonus_credits: Decimal
    daily_credits_limit: Decimal
    daily_credits_refreshed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class Transaction(BaseModel):
    """Transaction record."""
    transaction_id: UUID
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """List of transactions."""
    transactions: List[Transaction]
    total: int
    limit: int
    offset: int
    has_more: bool


# ============================================================================
# Market Schemas
# ============================================================================

class CreditPackage(BaseModel):
    """Credit purchase package."""
    sku: str
    name: str
    credits: Decimal
    price_usd: Decimal
    discount_percentage: int


class SubscriptionPlan(BaseModel):
    """Subscription plan."""
    sku: str
    name: str
    tier: str
    price_usd: Decimal
    billing_period: str
    bonus_credits: Decimal
    features: List[str]


class ProductListResponse(BaseModel):
    """List of available products."""
    credit_packages: List[CreditPackage]
    subscriptions: List[SubscriptionPlan]


class PurchaseCreditsRequest(BaseModel):
    """Purchase credits request."""
    product_sku: str
    payment_provider: str  # 'stripe', 'apple_iap', 'google_play'
    provider_transaction_id: str


class PurchaseCreditsResponse(BaseModel):
    """Purchase credits response."""
    transaction_id: UUID
    credits_granted: Decimal
    new_balance: Decimal
    status: str


class SubscribeRequest(BaseModel):
    """Subscribe to plan request."""
    subscription_sku: str
    payment_provider: str
    provider_transaction_id: str


class SubscribeResponse(BaseModel):
    """Subscribe response."""
    subscription_tier: str
    subscription_expires_at: datetime
    bonus_credits_granted: Decimal
    new_balance: Decimal


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[dict] = None


class InsufficientCreditsError(BaseModel):
    """Insufficient credits error."""
    error: str = "insufficient_credits"
    message: str
    current_balance: Decimal
    required: Decimal


class RateLimitError(BaseModel):
    """Rate limit exceeded error."""
    error: str = "rate_limit_exceeded"
    message: str
    retry_after: int

"""
Pydantic Schemas for API Request/Response
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# Auth
# ============================================================================

class UserContext(BaseModel):
    """Authenticated user context (attached to request.state)"""
    user_id: str  # String ID for flexibility (can be UUID or simple ID)
    email: Optional[str] = None
    subscription_tier: str = "free"  # free, premium, vip
    is_subscribed: bool = False


class WalletInfo(BaseModel):
    total_credits: float = 10
    daily_free_credits: float = 10
    purchased_credits: float = 0
    bonus_credits: float = 0
    daily_credits_limit: float = 50


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    subscription_tier: str
    wallet: Optional[WalletInfo] = None


class FirebaseAuthRequest(BaseModel):
    id_token: str


# ============================================================================
# Chat
# ============================================================================

class ChatMessage(BaseModel):
    message_id: UUID
    role: str  # user, assistant
    content: str
    tokens_used: int = 0
    created_at: datetime


class ChatCompletionRequest(BaseModel):
    session_id: UUID
    message: str = Field(..., min_length=1, max_length=4000)
    spicy_mode: bool = False  # Enable adult content (Premium only)
    intimacy_level: int = 1   # Current relationship level (1-100)
    scenario_id: Optional[str] = None  # Scene context injection (e.g., "cafe_paris")
    client_message_id: Optional[str] = None  # Client-generated UUID for user message dedup


class ChatCompletionResponse(BaseModel):
    message_id: UUID
    content: str
    tokens_used: int
    character_name: str
    is_locked: bool = False  # True if content is hidden behind paywall
    content_rating: str = "safe"  # safe, flirty, spicy, explicit
    unlock_prompt: Optional[str] = None  # Message to show if locked
    extra_data: Optional[dict] = None  # Debug info: L1 perception, game engine state


class CreateSessionRequest(BaseModel):
    character_id: UUID


class CreateSessionResponse(BaseModel):
    session_id: UUID
    character_name: str
    character_avatar: Optional[str] = None
    character_background: Optional[str] = None
    intro_shown: bool = False  # 是否已播放过intro动画


class SessionInfo(BaseModel):
    session_id: UUID
    character_id: UUID
    character_name: str
    character_avatar: Optional[str] = None
    character_background: Optional[str] = None
    total_messages: int = 0
    last_message: Optional[str] = None  # 最后一条消息内容
    last_message_at: Optional[datetime] = None  # 最后消息时间
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Characters
# ============================================================================

class CharacterBase(BaseModel):
    name: str
    description: str
    avatar_url: Optional[str] = None
    is_spicy: bool = False
    personality_traits: List[str] = []


class CharacterResponse(CharacterBase):
    character_id: UUID
    is_active: bool = True
    created_at: datetime


class CharacterListResponse(BaseModel):
    characters: List[CharacterResponse]
    total: int


# ============================================================================
# Wallet / Billing
# ============================================================================

class WalletBalance(BaseModel):
    total_credits: float
    daily_free_credits: float
    purchased_credits: float
    bonus_credits: float
    subscription_tier: str
    daily_limit: float


class TransactionRecord(BaseModel):
    transaction_id: UUID
    transaction_type: str
    amount: float
    balance_after: float
    description: str
    created_at: datetime


class PurchaseRequest(BaseModel):
    package_id: str  # e.g., "pack_100", "pack_500"
    payment_method: str = "stripe"  # stripe, apple_iap, google_play


class PurchaseResponse(BaseModel):
    success: bool
    new_balance: float
    transaction_id: UUID


class SubscriptionInfo(BaseModel):
    tier: str
    expires_at: Optional[datetime] = None
    auto_renew: bool = False


# ============================================================================
# Voice
# ============================================================================

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice: Optional[str] = "灿灿"
    speed: float = Field(default=1.0, ge=0.2, le=3.0)
    emotion: Optional[str] = None


class VoiceListResponse(BaseModel):
    voices: dict


# ============================================================================
# Image
# ============================================================================

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    size: str = "1024x1024"
    quality: str = "standard"
    style: str = "vivid"


class ImageGenerationResponse(BaseModel):
    url: str
    revised_prompt: str


# ============================================================================
# Market
# ============================================================================

class CreditPackage(BaseModel):
    package_id: str
    credits: int
    price_usd: float
    label: str
    discount_percent: int = 0


class SubscriptionPlan(BaseModel):
    plan_id: str
    name: str
    tier: str
    price_monthly_usd: float
    daily_credits: int
    features: List[str]


# ============================================================================
# Intimacy (Re-export from intimacy_schemas)
# ============================================================================

from app.models.schemas.intimacy_schemas import (
    IntimacyStatus,
    ActionAvailability,
    XPAwardResponse,
    LevelUpEvent,
    DailyCheckinResponse,
    IntimacyHistoryEntry,
    IntimacyHistoryResponse,
    StageInfo,
    AllStagesResponse,
    FeatureUnlock,
    AllFeaturesResponse,
)

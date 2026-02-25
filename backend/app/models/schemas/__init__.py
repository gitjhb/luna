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
    user_id: str = Field(
        ...,
        description="Unique user identifier (can be UUID or alphanumeric)",
        example="demo-user-123"
    )
    email: Optional[str] = Field(
        default=None,
        description="User's email address from authentication provider",
        example="user@example.com"
    )
    subscription_tier: str = Field(
        default="free",
        description="Current subscription level",
        example="premium",
        enum=["free", "premium", "vip"]
    )
    is_subscribed: bool = Field(
        default=False,
        description="Whether user has active paid subscription",
        example=True
    )


class WalletInfo(BaseModel):
    """Basic wallet information for authentication response."""
    
    total_credits: float = Field(
        default=10,
        description="Total spendable credits",
        example=35.5
    )
    daily_free_credits: float = Field(
        default=10,
        description="Daily free credits available",
        example=25.0
    )
    purchased_credits: float = Field(
        default=0,
        description="Purchased credits (never expire)",
        example=10.5
    )
    bonus_credits: float = Field(
        default=0,
        description="Promotional bonus credits",
        example=0
    )
    daily_credits_limit: float = Field(
        default=50,
        description="Maximum daily credits for subscription tier",
        example=50
    )


class TokenResponse(BaseModel):
    """Authentication response with access token and user info."""
    
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        example="bearer"
    )
    user_id: str = Field(
        ...,
        description="Unique user identifier",
        example="demo-user-123"
    )
    subscription_tier: str = Field(
        ...,
        description="User's subscription level",
        example="premium",
        enum=["free", "premium", "vip"]
    )
    wallet: Optional[WalletInfo] = Field(
        default=None,
        description="Initial wallet balance information"
    )


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
    """Request to send a chat message to an AI companion."""
    
    session_id: UUID = Field(
        ..., 
        description="Unique identifier for the chat session",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=4000,
        description="User's message to send to the AI companion",
        example="Hi there! How are you feeling today?"
    )
    spicy_mode: bool = Field(
        default=False,
        description="Enable adult content mode (requires Premium subscription)",
        example=False
    )
    intimacy_level: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Current relationship intimacy level (1=stranger, 100=romantic partner)",
        example=25
    )
    scenario_id: Optional[str] = Field(
        default=None,
        description="Optional scenario context for roleplay (e.g., 'cafe_paris', 'beach_sunset')",
        example="cafe_paris"
    )
    client_message_id: Optional[str] = Field(
        default=None,
        description="Client-generated UUID for deduplication",
        example="msg_abc123"
    )
    timezone: str = Field(
        default="America/Los_Angeles",
        description="User's timezone for accurate time references",
        example="America/New_York"
    )


class ChatCompletionResponse(BaseModel):
    """AI companion's response to a chat message."""
    
    message_id: UUID = Field(
        ...,
        description="Unique identifier for this AI response message",
        example="660e8400-e29b-41d4-a716-446655440001"
    )
    content: str = Field(
        ...,
        description="The AI companion's response text",
        example="Hello! I'm doing wonderful, thank you for asking! Your message just brightened my day. 😊"
    )
    tokens_used: int = Field(
        ...,
        description="Number of tokens consumed for this interaction",
        example=45
    )
    character_name: str = Field(
        ...,
        description="Name of the AI character responding",
        example="小美"
    )
    is_locked: bool = Field(
        default=False,
        description="True if content is hidden behind premium paywall",
        example=False
    )
    content_rating: str = Field(
        default="safe",
        description="Content appropriateness rating",
        example="flirty",
        enum=["safe", "flirty", "spicy", "explicit"]
    )
    unlock_prompt: Optional[str] = Field(
        default=None,
        description="Message to display if content is locked",
        example="Upgrade to Premium to unlock spicy conversations! 🔥"
    )
    extra_data: Optional[dict] = Field(
        default=None,
        description="Additional debug information and game state",
        example={
            "intimacy_gained": 2,
            "emotion_detected": "happy",
            "scenario_active": "cafe_paris"
        }
    )


class CreateSessionRequest(BaseModel):
    """Request to create a new chat session with an AI character."""
    
    character_id: UUID = Field(
        ...,
        description="Unique identifier of the AI character to chat with",
        example="550e8400-e29b-41d4-a716-446655440000"
    )


class CreateSessionResponse(BaseModel):
    """Response after creating or retrieving a chat session."""
    
    session_id: UUID = Field(
        ...,
        description="Unique identifier for the chat session",
        example="660e8400-e29b-41d4-a716-446655440001"
    )
    character_name: str = Field(
        ...,
        description="Display name of the AI character",
        example="小美"
    )
    character_avatar: Optional[str] = Field(
        default=None,
        description="URL to character's profile picture",
        example="https://cdn.luna.app/characters/xiaomei/avatar.jpg"
    )
    character_background: Optional[str] = Field(
        default=None,
        description="URL to character's background image for chat interface",
        example="https://cdn.luna.app/characters/xiaomei/bg.jpg"
    )
    intro_shown: bool = Field(
        default=False,
        description="Whether introduction animation has been played for this session",
        example=False
    )


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
    """Base character information."""
    
    name: str = Field(
        ...,
        description="Character's display name",
        example="小美"
    )
    description: str = Field(
        ..., 
        description="Brief character description and personality summary",
        example="温柔体贴的邻家女孩，喜欢读书和烘焙"
    )
    avatar_url: Optional[str] = Field(
        default=None,
        description="URL to character's profile picture",
        example="https://cdn.luna.app/characters/xiaomei/avatar.jpg"
    )
    is_spicy: bool = Field(
        default=False,
        description="Whether character supports adult content (Premium required)",
        example=False
    )
    personality_traits: List[str] = Field(
        default=[],
        description="List of personality characteristics",
        example=["温柔", "体贴", "文艺", "爱笑"]
    )


class CharacterResponse(CharacterBase):
    """Detailed character information with metadata."""
    
    character_id: UUID = Field(
        ...,
        description="Unique identifier for the character",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    is_active: bool = Field(
        default=True,
        description="Whether character is currently available for chat",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="When the character was created",
        example="2024-01-15T10:30:00Z"
    )


class CharacterListResponse(BaseModel):
    """Response containing multiple characters."""
    
    characters: List[CharacterResponse] = Field(
        ...,
        description="List of available AI characters"
    )
    total: int = Field(
        ...,
        description="Total number of characters returned",
        example=5
    )


# ============================================================================
# Wallet / Billing
# ============================================================================

class WalletBalance(BaseModel):
    """User's wallet balance and credit breakdown."""
    
    total_credits: float = Field(
        ...,
        description="Total spendable credits (sum of all credit types)",
        example=125.5
    )
    daily_free_credits: float = Field(
        ...,
        description="Daily free credits available (resets every 24h)",
        example=35.0
    )
    purchased_credits: float = Field(
        ...,
        description="Credits bought through in-app purchases (never expire)",
        example=80.0
    )
    bonus_credits: float = Field(
        ...,
        description="Promotional or referral bonus credits",
        example=10.5
    )
    subscription_tier: str = Field(
        ...,
        description="User's current subscription level",
        example="premium",
        enum=["free", "premium", "vip"]
    )
    daily_limit: float = Field(
        ...,
        description="Maximum daily credits for this subscription tier",
        example=50.0
    )


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
    """Request to convert text to speech."""
    
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Text to convert to speech",
        example="你好！很高兴见到你！"
    )
    voice: Optional[str] = Field(
        default="灿灿",
        description="Voice character to use for speech synthesis",
        example="灿灿"
    )
    speed: float = Field(
        default=1.0, 
        ge=0.2, 
        le=3.0,
        description="Speech speed multiplier (0.2 = slow, 3.0 = fast)",
        example=1.2
    )
    emotion: Optional[str] = Field(
        default=None,
        description="Emotional tone for the voice",
        example="happy",
        enum=["happy", "sad", "excited", "neutral", "romantic"]
    )


class VoiceListResponse(BaseModel):
    """Response containing available voice options."""
    
    voices: dict = Field(
        ...,
        description="Dictionary of available voices with metadata",
        example={
            "灿灿": {"name": "灿灿", "gender": "female", "language": "zh-CN", "style": "sweet"},
            "晓梦": {"name": "晓梦", "gender": "female", "language": "zh-CN", "style": "energetic"},
            "云希": {"name": "云希", "gender": "female", "language": "zh-CN", "style": "mature"}
        }
    )


# ============================================================================
# Image
# ============================================================================

class ImageGenerationRequest(BaseModel):
    """Request to generate an AI image from text prompt."""
    
    prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Detailed text description of the image to generate",
        example="A cute anime girl with long pink hair reading a book in a cozy library"
    )
    size: str = Field(
        default="1024x1024",
        description="Output image dimensions",
        example="1024x1024",
        enum=["1024x1024", "1792x1024", "1024x1792"]
    )
    quality: str = Field(
        default="standard",
        description="Image generation quality level",
        example="standard",
        enum=["standard", "hd"]
    )
    style: str = Field(
        default="vivid",
        description="Artistic style for image generation",
        example="vivid",
        enum=["vivid", "natural"]
    )


class ImageGenerationResponse(BaseModel):
    """Response containing generated image details."""
    
    url: str = Field(
        ...,
        description="Direct download URL for the generated image (expires in 1 hour)",
        example="https://oaidalleapiprodscus.blob.core.windows.net/private/org-.../generated_image.png"
    )
    revised_prompt: str = Field(
        ...,
        description="Enhanced version of the original prompt used for generation",
        example="A cute anime-style girl with long flowing pink hair, sitting in a cozy library with warm lighting, reading an open book, surrounded by wooden bookshelves, soft atmospheric lighting, detailed digital art style"
    )


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

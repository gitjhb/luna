"""
Authentication API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from uuid import uuid4
import os

from app.models.schemas import (
    TokenResponse, FirebaseAuthRequest, UserContext, WalletInfo
)

router = APIRouter(prefix="/auth")

# Mock mode for development
MOCK_MODE = os.getenv("MOCK_AUTH", "true").lower() == "true"


@router.post("/firebase", response_model=TokenResponse)
async def authenticate_firebase(request: FirebaseAuthRequest):
    """
    Authenticate with Firebase ID token.
    In production: verify token with Firebase Admin SDK.
    In dev: mock authentication.
    """
    if MOCK_MODE:
        # Mock: accept any token
        user_id = str(uuid4())
        return TokenResponse(
            access_token=f"mock_token_{user_id}",
            user_id=user_id,
            subscription_tier="free",
        )

    # Production: verify with Firebase
    # from firebase_admin import auth as firebase_auth
    # decoded = firebase_auth.verify_id_token(request.id_token)
    # user_id = decoded["uid"]
    # ...
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Firebase auth not configured",
    )


@router.post("/google", response_model=TokenResponse)
async def authenticate_google(token: str):
    """Google OAuth mock endpoint"""
    if MOCK_MODE:
        user_id = str(uuid4())
        return TokenResponse(
            access_token=f"mock_google_{user_id}",
            user_id=user_id,
            subscription_tier="free",
        )
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/apple", response_model=TokenResponse)
async def authenticate_apple(token: str):
    """Apple OAuth mock endpoint"""
    if MOCK_MODE:
        user_id = str(uuid4())
        return TokenResponse(
            access_token=f"mock_apple_{user_id}",
            user_id=user_id,
            subscription_tier="free",
        )
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/guest", response_model=TokenResponse)
async def guest_login():
    """
    Guest login - creates a temporary user for testing.
    """
    user_id = f"guest-{str(uuid4())[:8]}"
    return TokenResponse(
        access_token=f"guest_token_{user_id}",
        user_id=user_id,
        subscription_tier="free",
        wallet=WalletInfo(
            total_credits=100,
            daily_free_credits=10,
            purchased_credits=0,
            bonus_credits=0,
            daily_credits_limit=50,
        )
    )


@router.get("/me")
async def get_current_user():
    """Get current user info (uses unified subscription service)"""
    user_id = "demo-user-123"
    
    # Use unified subscription service for accurate tier info
    from app.services.subscription_service import subscription_service
    subscription_info = await subscription_service.get_subscription_info(user_id)
    
    return {
        "user_id": user_id,
        "email": "demo@example.com",
        "subscription_tier": subscription_info.get("effective_tier", "free"),
        "is_subscribed": subscription_info.get("is_subscribed", False),
        "subscription_expires_at": subscription_info.get("expires_at"),
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str = None):
    """Refresh access token (mock)"""
    if MOCK_MODE:
        return TokenResponse(
            access_token=f"mock_refreshed_token",
            user_id="demo-user-123",
            subscription_tier="free",
        )
    raise HTTPException(status_code=501, detail="Not implemented")

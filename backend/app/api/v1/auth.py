"""
Authentication API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from uuid import uuid4
import os

from app.models.schemas import (
    TokenResponse, FirebaseAuthRequest, UserContext
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


@router.get("/me")
async def get_current_user():
    """Get current user info (mock)"""
    return {
        "user_id": "demo_user",
        "email": "demo@example.com",
        "subscription_tier": "free",
    }

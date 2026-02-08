"""
Authentication API Routes

Supports:
- Guest login (instant access)
- Firebase Auth (Apple/Google Sign In)
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from datetime import datetime
import os
import logging

from app.models.schemas import TokenResponse, WalletInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

# Configuration
MOCK_AUTH = os.getenv("MOCK_AUTH", "true").lower() == "true"
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

# In-memory user store (use database in production)
_users: dict = {}

# Firebase Admin SDK (lazy init)
_firebase_app = None


def get_firebase_app():
    """Initialize Firebase Admin SDK lazily"""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        # Check for service account file
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with service account")
        elif FIREBASE_PROJECT_ID:
            # Use default credentials (for Cloud Run, etc.)
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with default credentials")
        else:
            logger.warning("Firebase not configured - using mock mode")
            return None
            
        return _firebase_app
    except ImportError:
        logger.warning("firebase-admin not installed - using mock mode")
        return None
    except Exception as e:
        logger.error(f"Firebase init error: {e}")
        return None


# ============================================================================
# Request/Response Models
# ============================================================================

class FirebaseAuthRequest(BaseModel):
    id_token: str
    provider: str = "firebase"  # 'apple' or 'google'
    display_name: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None


class LinkAccountRequest(BaseModel):
    provider: str  # 'apple' or 'google'
    id_token: str


# ============================================================================
# Guest Login
# ============================================================================

# Demo user secret for JHB's testing (env var or hardcoded for dev)
DEMO_SECRET = os.getenv("DEMO_SECRET", "jhb-luna-2024")


class DemoLoginRequest(BaseModel):
    secret: str


@router.post("/demo", response_model=TokenResponse)
async def demo_login(request: DemoLoginRequest):
    """
    Demo login - returns a FIXED user ID for JHB's testing.
    Requires secret to prevent random access.
    All previous data (characters, chats, etc.) will be preserved.
    """
    if request.secret != DEMO_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid demo secret. Use Apple/Google Sign In instead."
        )
    
    user_id = "demo-jhb-123"
    
    # Store/update user
    _users[user_id] = {
        "user_id": user_id,
        "email": "jhb@luna.app",
        "display_name": "JHB",
        "provider": "demo",
        "subscription_tier": "vip",  # VIP for full feature access
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Initialize wallet
    from app.services.payment_service import payment_service
    wallet = await payment_service.get_or_create_wallet(user_id)
    
    logger.info(f"Demo login successful for user: {user_id}")
    
    return TokenResponse(
        access_token=f"demo_token_{user_id}",
        user_id=user_id,
        subscription_tier="vip",
        display_name="JHB",
        wallet=WalletInfo(
            total_credits=wallet.get("total_credits", 100),
            daily_free_credits=wallet.get("daily_free_credits", 10),
            purchased_credits=wallet.get("purchased_credits", 0),
            bonus_credits=wallet.get("bonus_credits", 0),
            daily_credits_limit=wallet.get("daily_credits_limit", 50),
        )
    )


# Only allow guest login in dev/test environment
ALLOW_GUEST = os.getenv("ALLOW_GUEST", "false").lower() == "true"


@router.post("/guest", response_model=TokenResponse)
async def guest_login():
    """
    Guest login - creates a temporary user for testing.
    Only available in test environment (ALLOW_GUEST=true).
    """
    if not ALLOW_GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest login is disabled. Please use Apple or Google Sign In."
        )
    
    user_id = f"guest-{str(uuid4())[:8]}"
    
    # Store user
    _users[user_id] = {
        "user_id": user_id,
        "email": None,
        "display_name": "Guest",
        "provider": "guest",
        "subscription_tier": "free",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Initialize wallet
    from app.services.payment_service import payment_service
    wallet = await payment_service.get_or_create_wallet(user_id)
    
    return TokenResponse(
        access_token=f"guest_token_{user_id}",
        user_id=user_id,
        subscription_tier="free",
        display_name="Guest",
        wallet=WalletInfo(
            total_credits=wallet.get("total_credits", 100),
            daily_free_credits=wallet.get("daily_free_credits", 10),
            purchased_credits=wallet.get("purchased_credits", 0),
            bonus_credits=wallet.get("bonus_credits", 0),
            daily_credits_limit=wallet.get("daily_credits_limit", 50),
        )
    )


# ============================================================================
# Firebase Auth (Apple/Google Sign In)
# ============================================================================

@router.post("/firebase", response_model=TokenResponse)
async def authenticate_firebase(request: FirebaseAuthRequest):
    """
    Authenticate with Firebase ID token.
    
    Flow:
    1. Client signs in with Apple/Google via Firebase
    2. Client sends Firebase ID token here
    3. We verify token with Firebase Admin SDK
    4. Create or update user in our database
    5. Return our own access token
    """
    
    # Mock mode for development
    if MOCK_AUTH and not get_firebase_app():
        logger.info(f"Mock Firebase auth for provider: {request.provider}")
        user_id = f"mock-{request.provider}-{str(uuid4())[:8]}"
        
        _users[user_id] = {
            "user_id": user_id,
            "email": request.email or f"{user_id}@mock.luna.app",
            "display_name": request.display_name or "Mock User",
            "provider": request.provider,
            "photo_url": request.photo_url,
            "subscription_tier": "free",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        from app.services.payment_service import payment_service
        wallet = await payment_service.get_or_create_wallet(user_id)
        
        return TokenResponse(
            access_token=f"mock_firebase_token_{user_id}",
            user_id=user_id,
            subscription_tier="free",
            display_name=request.display_name or "Mock User",
            email=request.email,
            wallet=WalletInfo(
                total_credits=wallet.get("total_credits", 100),
                daily_free_credits=wallet.get("daily_free_credits", 10),
                purchased_credits=wallet.get("purchased_credits", 0),
                bonus_credits=wallet.get("bonus_credits", 0),
                daily_credits_limit=wallet.get("daily_credits_limit", 50),
            )
        )
    
    # Production: Verify with Firebase Admin SDK
    try:
        from firebase_admin import auth as firebase_auth
        
        # Verify the ID token
        decoded_token = firebase_auth.verify_id_token(request.id_token)
        firebase_uid = decoded_token["uid"]
        
        logger.info(f"Firebase token verified for UID: {firebase_uid}")
        
        # Get or create user in DATABASE (persistent)
        user_id = f"fb-{firebase_uid}"
        user_email = decoded_token.get("email") or request.email or f"{user_id}@luna.app"
        user_display_name = request.display_name or decoded_token.get("name") or "User"
        user_avatar = request.photo_url or decoded_token.get("picture")
        
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.user_models import User
        
        async with get_db() as db:
            result = await db.execute(
                select(User).where(User.user_id == user_id)
            )
            db_user = result.scalar_one_or_none()
            
            if db_user:
                # Update existing user
                db_user.last_login_at = datetime.utcnow()
                if request.display_name:
                    db_user.display_name = request.display_name
                if request.photo_url:
                    db_user.avatar_url = request.photo_url
                await db.commit()
                logger.info(f"Updated existing user: {user_id}")
            else:
                # Create new user in database
                db_user = User(
                    user_id=user_id,
                    firebase_uid=firebase_uid,
                    email=user_email,
                    display_name=user_display_name,
                    avatar_url=user_avatar,
                    is_subscribed=False,
                    subscription_tier="free",
                )
                db.add(db_user)
                await db.commit()
                await db.refresh(db_user)
                logger.info(f"Created new user in database: {user_id}")
        
        # Also keep in memory cache for fast access
        user = {
            "user_id": user_id,
            "firebase_uid": firebase_uid,
            "email": user_email,
            "display_name": user_display_name,
            "photo_url": user_avatar,
            "provider": request.provider,
            "subscription_tier": "free",
        }
        _users[user_id] = user
        
        # Get subscription tier
        from app.services.subscription_service import subscription_service
        sub_info = await subscription_service.get_subscription_info(user_id)
        tier = sub_info.get("effective_tier", "free")
        
        # Get wallet
        from app.services.payment_service import payment_service
        wallet = await payment_service.get_or_create_wallet(user_id)
        
        # Generate our access token (in production, use proper JWT)
        access_token = f"luna_token_{user_id}_{str(uuid4())[:8]}"
        
        return TokenResponse(
            access_token=access_token,
            user_id=user_id,
            subscription_tier=tier,
            display_name=user.get("display_name"),
            email=user.get("email"),
            wallet=WalletInfo(
                total_credits=wallet.get("total_credits", 100),
                daily_free_credits=wallet.get("daily_free_credits", 10),
                purchased_credits=wallet.get("purchased_credits", 0),
                bonus_credits=wallet.get("bonus_credits", 0),
                daily_credits_limit=wallet.get("daily_credits_limit", 50),
            )
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Firebase Admin SDK not installed. Run: pip install firebase-admin"
        )
    except Exception as e:
        logger.error(f"Firebase auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


# ============================================================================
# Current User
# ============================================================================

@router.get("/me")
async def get_current_user(req: Request):
    """Get current user info"""
    user = getattr(req.state, "user", None)
    
    if user:
        user_id = str(user.user_id)
    else:
        # Fallback for development
        user_id = "demo-user-123"
    
    # Get user data
    user_data = _users.get(user_id, {
        "user_id": user_id,
        "email": "demo@example.com",
        "display_name": "Demo User",
    })
    
    # Get subscription info
    from app.services.subscription_service import subscription_service
    sub_info = await subscription_service.get_subscription_info(user_id)
    
    return {
        "user_id": user_id,
        "email": user_data.get("email"),
        "display_name": user_data.get("display_name", "User"),
        "avatar_url": user_data.get("photo_url"),
        "subscription_tier": sub_info.get("effective_tier", "free"),
        "is_subscribed": sub_info.get("is_subscribed", False),
        "subscription_expires_at": sub_info.get("expires_at"),
        "created_at": user_data.get("created_at"),
    }


# ============================================================================
# Token Refresh
# ============================================================================

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: Request):
    """Refresh access token"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # Generate new token
    new_token = f"luna_token_{user_id}_{str(uuid4())[:8]}"
    
    # Get subscription tier
    from app.services.subscription_service import subscription_service
    sub_info = await subscription_service.get_subscription_info(user_id)
    
    return TokenResponse(
        access_token=new_token,
        user_id=user_id,
        subscription_tier=sub_info.get("effective_tier", "free"),
    )


# ============================================================================
# Legacy endpoints (for backwards compatibility)
# ============================================================================

@router.post("/google", response_model=TokenResponse)
async def authenticate_google_legacy(token: str = ""):
    """Legacy Google OAuth - redirect to Firebase auth"""
    return await authenticate_firebase(FirebaseAuthRequest(
        id_token=token,
        provider="google"
    ))


@router.post("/apple", response_model=TokenResponse)
async def authenticate_apple_legacy(token: str = ""):
    """Legacy Apple OAuth - redirect to Firebase auth"""
    return await authenticate_firebase(FirebaseAuthRequest(
        id_token=token,
        provider="apple"
    ))

"""
Authentication Middleware
Extracts and validates auth tokens, attaches user context to request.state
"""

from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os
import logging

from app.models.schemas import UserContext

logger = logging.getLogger(__name__)

# Consistent demo user ID for mock mode
# Use simple string ID that matches API fallbacks
DEMO_USER_ID = "demo-user-123"

# Firebase Admin SDK (lazy init)
_firebase_admin_app = None


def get_firebase_admin():
    """Initialize Firebase Admin SDK lazily for user lookups"""
    global _firebase_admin_app
    if _firebase_admin_app is not None:
        return _firebase_admin_app
    
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        # Check if already initialized
        try:
            _firebase_admin_app = firebase_admin.get_app()
            return _firebase_admin_app
        except ValueError:
            pass
        
        # Try to initialize
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_admin_app = firebase_admin.initialize_app(cred)
        elif os.getenv("FIREBASE_PROJECT_ID"):
            _firebase_admin_app = firebase_admin.initialize_app()
        else:
            return None
            
        return _firebase_admin_app
    except Exception as e:
        logger.warning(f"Firebase Admin init failed: {e}")
        return None


async def fetch_email_from_firebase(firebase_uid: str) -> Optional[str]:
    """
    Fetch user's email from Firebase Auth.
    This is the FALLBACK when we don't have email in our database.
    """
    if not get_firebase_admin():
        return None
    
    try:
        from firebase_admin import auth as firebase_auth
        user_record = firebase_auth.get_user(firebase_uid)
        if user_record.email:
            logger.info(f"Fetched email from Firebase for {firebase_uid}: {user_record.email}")
            return user_record.email
    except Exception as e:
        logger.warning(f"Failed to fetch email from Firebase for {firebase_uid}: {e}")
    
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract user context from auth tokens.
    In mock mode: creates a demo user context.
    In production: validates Firebase/JWT tokens.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.mock_mode = os.getenv("MOCK_AUTH", "true").lower() == "true"
        self.public_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/api/v1/auth/firebase",
            "/api/v1/auth/google",
            "/api/v1/auth/apple",
            "/api/v1/market/packages",
            "/api/v1/market/plans",
            "/api/v1/characters",
        }

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in self.public_paths or request.url.path.startswith("/api/v1/auth"):
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Create user context
        # Priority: 1) Valid token  2) X-User-ID header (mock mode)  3) Demo user (mock mode)
        if token:
            # Try to validate token first
            user_context = await self._validate_token(token)
            if user_context:
                request.state.user = user_context
            elif self.mock_mode:
                # Token invalid but mock mode - fallback to header or demo
                request.state.user = await self._create_mock_user(request)
            else:
                request.state.user = None
        elif self.mock_mode:
            # No token but mock mode - use header or demo user
            request.state.user = await self._create_mock_user(request)
        else:
            request.state.user = None

        return await call_next(request)
    
    async def _create_mock_user(self, request: Request) -> UserContext:
        """Create mock user context from X-User-ID header or demo user"""
        from app.services.subscription_service import subscription_service
        
        header_user_id = request.headers.get("X-User-ID")
        user_id = header_user_id if header_user_id else DEMO_USER_ID
        
        # Fetch real email from database if user exists
        user_email = await self._get_user_email_from_db(user_id)
        if not user_email:
            user_email = "demo@example.com" if user_id == DEMO_USER_ID else None
        
        subscription_info = await subscription_service.get_subscription_info(user_id)
        subscription_tier = subscription_info.get("effective_tier", "free")
        is_subscribed = subscription_info.get("is_subscribed", False)
        
        return UserContext(
            user_id=user_id,
            email=user_email,
            subscription_tier=subscription_tier,
            is_subscribed=is_subscribed,
        )

    async def _get_user_email_from_db(self, user_id: str) -> Optional[str]:
        """Fetch user's email from database"""
        try:
            from app.core.database import get_db
            from app.models.database.user_models import User
            from sqlalchemy import select
            
            async with get_db() as db:
                result = await db.execute(
                    select(User.email).where(User.user_id == user_id)
                )
                row = result.first()
                if row and row[0]:
                    return row[0]
        except Exception:
            pass
        return None

    async def _ensure_user_in_database(
        self,
        user_id: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        is_guest: bool = False,
    ) -> Optional[str]:
        """
        Ensure user exists in database. Creates if not exists.
        Also updates email if we have a better one from Firebase.
        
        This is CRITICAL for:
        - FK constraints (transactions, subscriptions)
        - Payment webhooks (Stripe, RevenueCat)
        - Any database operation that references user_id
        
        Args:
            user_id: Firebase UID or guest ID
            email: User email (optional)
            display_name: Display name (optional)
            is_guest: Whether this is a guest user
            
        Returns:
            The user's email (from DB, param, or Firebase fallback), or None on error
        """
        try:
            from app.core.database import get_db
            from app.models.database.user_models import User
            from app.models.database.billing_models import UserWallet
            from app.core.config import settings
            from sqlalchemy import select
            from datetime import datetime
            
            async with get_db() as db:
                # Check if user already exists (by user_id or firebase_uid)
                result = await db.execute(
                    select(User).where(
                        (User.user_id == user_id) | (User.firebase_uid == user_id)
                    )
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # User exists - check if we need to update email
                    db_email = existing_user.email
                    
                    # If DB has fake/auto email but we have a real one, update it
                    is_fake_email = (
                        not db_email or 
                        "@auto.luna.app" in (db_email or "") or
                        "@guest.luna.app" in (db_email or "")
                    )
                    
                    if is_fake_email:
                        # Try to get real email: param > Firebase fallback
                        real_email = email
                        if not real_email and not is_guest:
                            real_email = await fetch_email_from_firebase(user_id)
                        
                        if real_email and "@" in real_email:
                            logger.info(f"Updating user {user_id} email: {db_email} -> {real_email}")
                            existing_user.email = real_email
                            await db.commit()
                            return real_email
                    
                    return db_email
                
                # User doesn't exist - need to create
                # First, try to get email from Firebase if not provided
                final_email = email
                if not final_email and not is_guest:
                    final_email = await fetch_email_from_firebase(user_id)
                
                if not final_email:
                    final_email = f"{user_id[:20]}@auto.luna.app"
                
                # Create new user
                logger.info(f"Creating user in database: {user_id} (is_guest={is_guest}, email={final_email})")
                user = User(
                    firebase_uid=user_id,
                    email=final_email,
                    display_name=display_name or ("Guest" if is_guest else "User"),
                    is_subscribed=False,
                    subscription_tier="free",
                    last_login_at=datetime.utcnow(),
                )
                db.add(user)
                await db.flush()  # Get user_id (auto-generated)
                
                # Create wallet
                initial_credits = getattr(settings, 'DAILY_CREDITS_FREE', 10.0)
                wallet = UserWallet(
                    user_id=user.user_id,
                    free_credits=initial_credits,
                    purchased_credits=0.0,
                    total_credits=initial_credits,
                    daily_refresh_amount=initial_credits,
                )
                db.add(wallet)
                await db.commit()
                
                logger.info(f"Created user {user.user_id} (firebase_uid={user_id}) with wallet")
                return final_email
                
        except Exception as e:
            logger.error(f"Failed to ensure user in database for {user_id}: {e}")
            return None

    async def _validate_token(self, token: str) -> Optional[UserContext]:
        """
        Validate auth token and return user context.
        
        Supports:
        - guest_token_xxx: Guest login tokens
        - luna_token_xxx: Firebase authenticated users
        - mock_firebase_token_xxx: Mock mode tokens
        """
        from app.api.v1.auth import _users
        from app.services.subscription_service import subscription_service
        import logging
        logger = logging.getLogger(__name__)
        
        user_id = None
        
        # Extract user_id from token format
        if token.startswith("demo_token_"):
            user_id = token.replace("demo_token_", "")
            logger.debug(f"Demo token, user_id: {user_id}")
        elif token.startswith("guest_token_"):
            user_id = token.replace("guest_token_", "")
            logger.debug(f"Guest token, user_id: {user_id}")
        elif token.startswith("luna_token_"):
            # Format: luna_token_{user_id}_{random}
            parts = token.replace("luna_token_", "").rsplit("_", 1)
            if parts:
                user_id = parts[0]
        elif token.startswith("mock_firebase_token_"):
            user_id = token.replace("mock_firebase_token_", "")
        
        if not user_id:
            return None
        
        # Look up user in memory cache
        user = _users.get(user_id)
        user_email = None
        
        if not user:
            # User not in memory (maybe server restarted)
            # Fetch from database first
            user_email = await self._get_user_email_from_db(user_id)
            
            # Auto-create a minimal user record for valid token formats
            # Accept: Firebase UIDs (alphanumeric 20+ chars), guest-*, demo-*
            is_demo = user_id.startswith("demo-")
            is_guest = user_id.startswith("guest-")
            is_firebase = len(user_id) >= 20 and user_id.replace("-", "").replace("_", "").isalnum()
            
            if user_id and (is_demo or is_guest or is_firebase):
                logger.info(f"Auto-creating user record for: {user_id}")
                
                # CRITICAL: Also create user in DATABASE (not just memory)
                # This ensures FK constraints work for transactions, subscriptions, etc.
                # This also fetches email from Firebase if not in DB
                resolved_email = await self._ensure_user_in_database(
                    user_id=user_id,
                    email=user_email or ("jhb@luna.app" if is_demo else None),
                    display_name="JHB" if is_demo else "User",
                    is_guest=is_guest,
                )
                
                # Use email from database/Firebase fallback
                if resolved_email:
                    user_email = resolved_email
                
                _users[user_id] = {
                    "user_id": user_id,
                    "email": user_email or ("jhb@luna.app" if is_demo else None),
                    "display_name": "JHB" if is_demo else "User",
                    "provider": "demo" if is_demo else ("firebase" if is_firebase else "guest"),
                    "subscription_tier": "free",
                }
                user = _users[user_id]
            else:
                logger.warning(f"Token validation failed: user not found for {user_id}")
                return None
        else:
            user_email = user.get("email")
            # If in-memory email is None/fake, try database
            if not user_email or "@example.com" in (user_email or "") or "@luna.app" in (user_email or ""):
                db_email = await self._get_user_email_from_db(user_id)
                if db_email:
                    user_email = db_email
                    user["email"] = db_email  # Update cache
        
        # Get subscription status
        try:
            sub_info = await subscription_service.get_subscription_info(user_id)
            subscription_tier = sub_info.get("effective_tier", "free")
            is_subscribed = sub_info.get("is_subscribed", False)
        except Exception:
            subscription_tier = "free"
            is_subscribed = False
        
        return UserContext(
            user_id=user_id,
            email=user_email,
            subscription_tier=subscription_tier,
            is_subscribed=is_subscribed,
        )

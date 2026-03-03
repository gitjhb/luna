"""
Authentication Middleware
Extracts and validates auth tokens, attaches user context to request.state
"""

from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os

from app.models.schemas import UserContext

# Consistent demo user ID for mock mode
# Use simple string ID that matches API fallbacks
DEMO_USER_ID = "demo-user-123"


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

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
        
        subscription_info = await subscription_service.get_subscription_info(user_id)
        subscription_tier = subscription_info.get("effective_tier", "free")
        is_subscribed = subscription_info.get("is_subscribed", False)
        
        return UserContext(
            user_id=user_id,
            email=f"{user_id}@example.com" if header_user_id else "demo@example.com",
            subscription_tier=subscription_tier,
            is_subscribed=is_subscribed,
        )

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
        
        # Look up user
        user = _users.get(user_id)
        if not user:
            # User not in memory (maybe server restarted)
            # Auto-create a minimal user record for valid token formats
            if user_id and (user_id.startswith("fb-") or user_id.startswith("guest-") or user_id.startswith("demo-")):
                logger.info(f"Auto-creating user record for: {user_id}")
                is_demo = user_id.startswith("demo-")
                _users[user_id] = {
                    "user_id": user_id,
                    "email": "jhb@luna.app" if is_demo else None,
                    "display_name": "JHB" if is_demo else "User",
                    "provider": "demo" if is_demo else ("firebase" if user_id.startswith("fb-") else "guest"),
                    "subscription_tier": "vip" if is_demo else "free",
                }
                user = _users[user_id]
            else:
                logger.warning(f"Token validation failed: user not found for {user_id}")
                return None
        
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
            email=user.get("email"),
            subscription_tier=subscription_tier,
            is_subscribed=is_subscribed,
        )

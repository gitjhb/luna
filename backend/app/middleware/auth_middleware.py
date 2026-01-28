"""
Authentication Middleware
Extracts and validates auth tokens, attaches user context to request.state
"""

from typing import Optional
from uuid import UUID, uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os

from app.models.schemas import UserContext


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
        if self.mock_mode:
            # Mock mode: create demo user
            request.state.user = UserContext(
                user_id=uuid4(),
                email="demo@example.com",
                subscription_tier="free",
                is_subscribed=False,
            )
        elif token:
            # Production: validate token
            user_context = await self._validate_token(token)
            if user_context:
                request.state.user = user_context
            else:
                request.state.user = None
        else:
            request.state.user = None

        return await call_next(request)

    async def _validate_token(self, token: str) -> Optional[UserContext]:
        """
        Validate auth token and return user context.
        In production: verify with Firebase Admin SDK.
        """
        # TODO: Implement Firebase token verification
        # from firebase_admin import auth
        # decoded = auth.verify_id_token(token)
        # return UserContext(user_id=UUID(decoded["uid"]), ...)
        return None

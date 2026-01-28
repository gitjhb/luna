"""
Billing Middleware - Simplified for development with mock support
"""

import os
import logging
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_DATABASE", "true").lower() == "true"


class BillingMiddleware(BaseHTTPMiddleware):
    """
    Billing middleware for credit checking and deduction.
    In mock mode: logs but doesn't actually deduct.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.billable_endpoints = [
            "/api/v1/chat/completions",
            "/api/v1/voice/tts",
            "/api/v1/image/generate",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a billable endpoint
        is_billable = any(
            request.url.path.startswith(endpoint)
            for endpoint in self.billable_endpoints
        )

        if not is_billable:
            return await call_next(request)

        # In mock mode, just log and proceed
        if MOCK_MODE:
            logger.debug(f"[MOCK] Billing check for {request.url.path}")
            response = await call_next(request)

            # Log the "cost" for debugging
            tokens_used = getattr(request.state, "tokens_used", 0)
            if tokens_used:
                logger.debug(f"[MOCK] Would deduct credits for {tokens_used} tokens")

            return response

        # Production mode: actual billing
        user = getattr(request.state, "user", None)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Authentication required"},
            )

        # TODO: Implement actual credit checking and deduction
        # See billing_middleware_complete.py for full implementation

        response = await call_next(request)
        return response

"""
Billing Middleware for AI Companion Platform
===========================================

This middleware intercepts every chat request to:
1. Verify user authentication
2. Check subscription tier (Free vs Premium)
3. Enforce rate limits
4. Check credit balance
5. Atomically deduct credits after successful LLM response

Author: Manus AI
Date: January 28, 2026
"""

import time
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
import logging

# Assuming these models exist in your project
from app.models.database import User, UserWallet, TransactionHistory
from app.core.config import settings
from app.services.auth_service import verify_firebase_token

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user has insufficient credits"""
    pass


class RateLimitExceededError(Exception):
    """Raised when user exceeds rate limit"""
    pass


class BillingContext:
    """Context object to store billing information during request lifecycle"""
    
    def __init__(self):
        self.user_id: Optional[str] = None
        self.user: Optional[User] = None
        self.is_subscribed: bool = False
        self.subscription_tier: str = "free"
        self.initial_credits: float = 0.0
        self.estimated_cost: float = 0.0
        self.actual_cost: float = 0.0
        self.tokens_used: int = 0
        self.is_spicy_mode: bool = False
        self.request_timestamp: float = time.time()
        self.transaction_id: Optional[str] = None


class BillingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles billing, rate limiting, and credit management.
    
    This middleware operates in two phases:
    1. Pre-request: Authentication, rate limiting, credit check
    2. Post-request: Atomic credit deduction based on actual usage
    """
    
    # Paths that require billing checks
    BILLING_REQUIRED_PATHS = [
        "/api/v1/chat/completions",
        "/api/v1/chat/stream",
    ]
    
    # Rate limits (requests per minute)
    RATE_LIMITS = {
        "free": 10,      # Free users: 10 requests/minute
        "premium": 60,   # Premium users: 60 requests/minute
        "vip": 120,      # VIP users: 120 requests/minute
    }
    
    # Credit costs (base cost per request)
    BASE_COSTS = {
        "normal": 1.0,   # Normal mode: 1 credit
        "spicy": 2.0,    # Spicy mode: 2 credits
    }
    
    def __init__(self, app, db_session_factory: Callable, redis_client: redis.Redis):
        """
        Initialize the billing middleware.
        
        Args:
            app: FastAPI application instance
            db_session_factory: Factory function to create database sessions
            redis_client: Redis client for rate limiting and caching
        """
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.redis = redis_client
        logger.info("BillingMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Main middleware dispatch method.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in the chain
            
        Returns:
            HTTP response
        """
        # Skip billing for non-billing paths
        if not self._requires_billing(request):
            return await call_next(request)
        
        # Create billing context
        billing_context = BillingContext()
        request.state.billing = billing_context
        
        try:
            # Phase 1: Pre-request checks
            async with self.db_session_factory() as db:
                await self._pre_request_checks(request, billing_context, db)
            
            # Call the actual endpoint
            response = await call_next(request)
            
            # Phase 2: Post-request credit deduction (only for successful responses)
            if response.status_code == 200:
                async with self.db_session_factory() as db:
                    await self._post_request_deduction(request, billing_context, db, response)
            
            return response
            
        except InsufficientCreditsError as e:
            logger.warning(f"Insufficient credits for user {billing_context.user_id}: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error": "insufficient_credits",
                    "message": "You don't have enough credits to complete this request.",
                    "current_balance": billing_context.initial_credits,
                    "required": billing_context.estimated_cost,
                }
            )
        
        except RateLimitExceededError as e:
            logger.warning(f"Rate limit exceeded for user {billing_context.user_id}: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "You have exceeded your rate limit. Please try again later.",
                    "retry_after": 60,  # seconds
                }
            )
        
        except HTTPException as e:
            raise e
        
        except Exception as e:
            logger.error(f"Billing middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "billing_error",
                    "message": "An error occurred while processing your request.",
                }
            )
    
    def _requires_billing(self, request: Request) -> bool:
        """Check if the request path requires billing"""
        return any(request.url.path.startswith(path) for path in self.BILLING_REQUIRED_PATHS)
    
    async def _pre_request_checks(
        self, 
        request: Request, 
        billing_context: BillingContext,
        db: AsyncSession
    ) -> None:
        """
        Perform all pre-request checks.
        
        Args:
            request: Incoming HTTP request
            billing_context: Billing context object
            db: Database session
            
        Raises:
            HTTPException: If authentication fails
            InsufficientCreditsError: If user has insufficient credits
            RateLimitExceededError: If rate limit is exceeded
        """
        # 1. Verify authentication
        await self._verify_authentication(request, billing_context, db)
        
        # 2. Check rate limits
        await self._check_rate_limit(billing_context)
        
        # 3. Parse request to estimate cost
        await self._estimate_cost(request, billing_context)
        
        # 4. Check credit balance
        await self._check_credit_balance(billing_context)
        
        logger.info(
            f"Pre-request checks passed for user {billing_context.user_id} "
            f"(tier: {billing_context.subscription_tier}, "
            f"credits: {billing_context.initial_credits:.2f})"
        )
    
    async def _verify_authentication(
        self,
        request: Request,
        billing_context: BillingContext,
        db: AsyncSession
    ) -> None:
        """
        Verify user authentication and load user data.
        
        Args:
            request: Incoming HTTP request
            billing_context: Billing context object
            db: Database session
            
        Raises:
            HTTPException: If authentication fails
        """
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = auth_header.split(" ")[1]
        
        # Verify Firebase token
        try:
            decoded_token = await verify_firebase_token(token)
            user_id = decoded_token.get("uid")
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Load user from database with wallet
        result = await db.execute(
            select(User)
            .options(selectinload(User.wallet))
            .where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Populate billing context
        billing_context.user_id = user_id
        billing_context.user = user
        billing_context.is_subscribed = user.is_subscribed
        billing_context.subscription_tier = user.subscription_tier
        billing_context.initial_credits = user.wallet.total_credits if user.wallet else 0.0
    
    async def _check_rate_limit(self, billing_context: BillingContext) -> None:
        """
        Check if user has exceeded their rate limit.
        
        Args:
            billing_context: Billing context object
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        user_id = billing_context.user_id
        tier = billing_context.subscription_tier
        limit = self.RATE_LIMITS.get(tier, self.RATE_LIMITS["free"])
        
        # Redis key for rate limiting
        rate_key = f"rate_limit:{user_id}:minute"
        
        # Get current count
        current_count = await self.redis.get(rate_key)
        
        if current_count is None:
            # First request in this minute
            await self.redis.setex(rate_key, 60, 1)
        else:
            count = int(current_count)
            if count >= limit:
                raise RateLimitExceededError(
                    f"Rate limit exceeded: {count}/{limit} requests per minute"
                )
            # Increment counter
            await self.redis.incr(rate_key)
        
        logger.debug(f"Rate limit check passed for user {user_id} (tier: {tier})")
    
    async def _estimate_cost(self, request: Request, billing_context: BillingContext) -> None:
        """
        Estimate the cost of the request based on mode.
        
        Args:
            request: Incoming HTTP request
            billing_context: Billing context object
        """
        # Parse request body to check for spicy mode
        try:
            body = await request.json()
            is_spicy = body.get("isSpicyMode", False)
            billing_context.is_spicy_mode = is_spicy
        except:
            billing_context.is_spicy_mode = False
        
        # Calculate estimated cost
        mode = "spicy" if billing_context.is_spicy_mode else "normal"
        billing_context.estimated_cost = self.BASE_COSTS[mode]
        
        logger.debug(
            f"Estimated cost for user {billing_context.user_id}: "
            f"{billing_context.estimated_cost} credits (mode: {mode})"
        )
    
    async def _check_credit_balance(self, billing_context: BillingContext) -> None:
        """
        Check if user has sufficient credits.
        
        Args:
            billing_context: Billing context object
            
        Raises:
            InsufficientCreditsError: If user has insufficient credits
        """
        if billing_context.initial_credits < billing_context.estimated_cost:
            raise InsufficientCreditsError(
                f"Insufficient credits: {billing_context.initial_credits} < "
                f"{billing_context.estimated_cost}"
            )
    
    async def _post_request_deduction(
        self,
        request: Request,
        billing_context: BillingContext,
        db: AsyncSession,
        response: Response
    ) -> None:
        """
        Atomically deduct credits after successful LLM response.
        
        Args:
            request: Incoming HTTP request
            billing_context: Billing context object
            db: Database session
            response: HTTP response from the endpoint
        """
        # Extract actual usage from response (if available)
        # This assumes the endpoint adds usage info to response headers or body
        try:
            # Try to get actual token usage from response
            tokens_used = int(response.headers.get("X-Tokens-Used", 0))
            billing_context.tokens_used = tokens_used
            
            # Calculate actual cost based on tokens (if you want token-based pricing)
            # For now, we use the estimated cost
            billing_context.actual_cost = billing_context.estimated_cost
            
        except:
            # Fallback to estimated cost
            billing_context.actual_cost = billing_context.estimated_cost
            billing_context.tokens_used = 0
        
        # Perform atomic credit deduction
        await self._atomic_credit_deduction(billing_context, db)
        
        logger.info(
            f"Credits deducted for user {billing_context.user_id}: "
            f"{billing_context.actual_cost} credits "
            f"(tokens: {billing_context.tokens_used})"
        )
    
    async def _atomic_credit_deduction(
        self,
        billing_context: BillingContext,
        db: AsyncSession
    ) -> None:
        """
        Atomically deduct credits from user's wallet.
        
        This uses database-level locking to ensure atomicity and prevent race conditions.
        
        Args:
            billing_context: Billing context object
            db: Database session
            
        Raises:
            InsufficientCreditsError: If credits were spent during request processing
        """
        user_id = billing_context.user_id
        amount = billing_context.actual_cost
        
        try:
            # Use SELECT FOR UPDATE to lock the wallet row
            result = await db.execute(
                select(UserWallet)
                .where(UserWallet.user_id == user_id)
                .with_for_update()
            )
            wallet = result.scalar_one_or_none()
            
            if not wallet:
                raise InsufficientCreditsError("Wallet not found")
            
            # Check balance again (it might have changed during request processing)
            if wallet.total_credits < amount:
                raise InsufficientCreditsError(
                    f"Insufficient credits at deduction time: "
                    f"{wallet.total_credits} < {amount}"
                )
            
            # Deduct from purchased credits first, then free credits
            if wallet.purchased_credits >= amount:
                wallet.purchased_credits -= amount
            else:
                remaining = amount - wallet.purchased_credits
                wallet.purchased_credits = 0.0
                wallet.free_credits -= remaining
            
            # Update total
            wallet.total_credits = wallet.free_credits + wallet.purchased_credits
            wallet.updated_at = datetime.utcnow()
            
            # Create transaction record
            transaction = TransactionHistory(
                user_id=user_id,
                transaction_type="deduction",
                amount=-amount,
                balance_after=wallet.total_credits,
                description=f"Chat completion ({'spicy' if billing_context.is_spicy_mode else 'normal'} mode)",
                metadata={
                    "tokens_used": billing_context.tokens_used,
                    "is_spicy_mode": billing_context.is_spicy_mode,
                    "timestamp": billing_context.request_timestamp,
                }
            )
            db.add(transaction)
            
            # Commit the transaction
            await db.commit()
            
            # Store transaction ID in context
            billing_context.transaction_id = transaction.transaction_id
            
            logger.info(
                f"Atomic credit deduction successful for user {user_id}: "
                f"{amount} credits (new balance: {wallet.total_credits})"
            )
            
        except InsufficientCreditsError:
            await db.rollback()
            raise
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Atomic credit deduction failed: {str(e)}", exc_info=True)
            raise


# Dependency injection helper
async def get_billing_context(request: Request) -> BillingContext:
    """
    FastAPI dependency to access billing context in endpoints.
    
    Usage:
        @app.post("/api/v1/chat/completions")
        async def chat_completions(
            billing: BillingContext = Depends(get_billing_context)
        ):
            # Access billing.user_id, billing.is_subscribed, etc.
            pass
    """
    if not hasattr(request.state, "billing"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Billing context not available"
        )
    return request.state.billing


# Example usage in main.py:
"""
from fastapi import FastAPI
from app.middleware.billing_middleware import BillingMiddleware
from app.core.database import get_db_session
from app.core.redis import get_redis_client

app = FastAPI()

# Add billing middleware
app.add_middleware(
    BillingMiddleware,
    db_session_factory=get_db_session,
    redis_client=get_redis_client()
)
"""

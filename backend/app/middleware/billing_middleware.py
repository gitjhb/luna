"""
Billing Middleware for AI Companion Platform
Handles credit checking, rate limiting, and atomic deduction
"""

from typing import Optional, Callable
from decimal import Decimal
from datetime import datetime, timedelta
import json
from uuid import UUID

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.exceptions import (
    InsufficientCreditsError,
    RateLimitExceededError,
    SubscriptionRequiredError
)
from app.models.schemas import UserContext
from app.utils.cost_calculator import calculate_chat_cost


class BillingMiddleware(BaseHTTPMiddleware):
    """
    Intercepts chat requests to enforce billing and rate limiting.
    
    Flow:
    1. Extract user context from request state (set by AuthMiddleware)
    2. Check subscription status and rate limits
    3. Pre-validate credit balance
    4. Allow request to proceed
    5. Post-process: Deduct credits atomically after successful LLM response
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.billable_endpoints = [
            "/api/v1/chat/completions",
            "/api/v1/chat/stream"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only intercept billable endpoints
        if not any(request.url.path.startswith(endpoint) for endpoint in self.billable_endpoints):
            return await call_next(request)
        
        # Extract user context (set by AuthMiddleware)
        user_context: Optional[UserContext] = getattr(request.state, "user", None)
        if not user_context:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Authentication required"}
            )
        
        try:
            # Step 1: Check and refresh daily credits if needed
            await self._check_and_refresh_daily_credits(user_context.user_id)
            
            # Step 2: Enforce rate limiting
            await self._check_rate_limit(user_context)
            
            # Step 3: Pre-validate credit balance
            await self._pre_validate_credits(user_context)
            
            # Step 4: Allow request to proceed
            response = await call_next(request)
            
            # Step 5: Post-process credit deduction (if response is successful)
            if response.status_code == 200:
                await self._post_deduct_credits(request, response, user_context)
            
            return response
            
        except InsufficientCreditsError as e:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error": "insufficient_credits",
                    "message": str(e),
                    "current_balance": float(e.current_balance),
                    "required": float(e.required_amount)
                }
            )
        except RateLimitExceededError as e:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": str(e),
                    "retry_after": e.retry_after
                },
                headers={"Retry-After": str(e.retry_after)}
            )
        except SubscriptionRequiredError as e:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "subscription_required",
                    "message": str(e),
                    "required_tier": e.required_tier
                }
            )
        except Exception as e:
            # Log error but don't expose internal details
            print(f"Billing middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "internal_error", "message": "An error occurred processing your request"}
            )
    
    async def _check_and_refresh_daily_credits(self, user_id: UUID) -> None:
        """
        Lazy refresh: Check if user's daily credits need refreshing.
        Uses Redis for fast lookup, PostgreSQL for atomic update.
        """
        redis = await get_redis()
        refresh_key = f"daily_refresh:{user_id}"
        
        # Check if already refreshed today
        last_refresh_date = await redis.get(refresh_key)
        today = datetime.utcnow().date().isoformat()
        
        if last_refresh_date and last_refresh_date.decode() == today:
            return  # Already refreshed today
        
        # Perform refresh
        async with get_db() as db:
            async with db.transaction():
                # Get user's subscription tier
                user = await db.fetchrow(
                    "SELECT subscription_tier FROM users WHERE user_id = $1",
                    user_id
                )
                
                if not user:
                    return
                
                # Determine daily credit limit based on tier
                tier_limits = {
                    "free": Decimal("10.00"),
                    "premium": Decimal("100.00"),
                    "vip": Decimal("500.00")
                }
                daily_limit = tier_limits.get(user["subscription_tier"], Decimal("10.00"))
                
                # Get current wallet state
                wallet = await db.fetchrow(
                    "SELECT * FROM user_wallet WHERE user_id = $1 FOR UPDATE",
                    user_id
                )
                
                if not wallet:
                    # Create wallet if doesn't exist
                    await db.execute(
                        """
                        INSERT INTO user_wallet (user_id, daily_free_credits, daily_credits_limit, daily_credits_refreshed_at)
                        VALUES ($1, $2, $3, NOW())
                        """,
                        user_id, daily_limit, daily_limit
                    )
                else:
                    # Check if refresh is needed
                    last_refresh = wallet["daily_credits_refreshed_at"]
                    if last_refresh.date() < datetime.utcnow().date():
                        # Refresh daily credits
                        old_balance = wallet["total_credits"]
                        new_daily_credits = daily_limit
                        new_total = wallet["purchased_credits"] + wallet["bonus_credits"] + new_daily_credits
                        
                        await db.execute(
                            """
                            UPDATE user_wallet
                            SET daily_free_credits = $1,
                                total_credits = $2,
                                daily_credits_refreshed_at = NOW(),
                                updated_at = NOW()
                            WHERE user_id = $3
                            """,
                            new_daily_credits, new_total, user_id
                        )
                        
                        # Record transaction
                        await db.execute(
                            """
                            INSERT INTO transaction_history 
                            (user_id, transaction_type, amount, balance_before, balance_after, description)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            """,
                            user_id, "daily_refresh", new_daily_credits, old_balance, new_total,
                            f"Daily credit refresh for {user['subscription_tier']} tier"
                        )
        
        # Cache refresh status in Redis
        await redis.setex(refresh_key, 86400, today)  # 24 hour TTL
    
    async def _check_rate_limit(self, user_context: UserContext) -> None:
        """
        Token bucket rate limiting with tier-based limits.
        
        Rate limits:
        - Free: 5 requests/minute
        - Premium: 30 requests/minute
        - VIP: 100 requests/minute
        """
        redis = await get_redis()
        rate_limit_key = f"rate_limit:{user_context.user_id}"
        
        # Tier-based limits
        tier_limits = {
            "free": {"tokens": 5, "refill_rate": 5, "window": 60},
            "premium": {"tokens": 30, "refill_rate": 30, "window": 60},
            "vip": {"tokens": 100, "refill_rate": 100, "window": 60}
        }
        
        limit_config = tier_limits.get(user_context.subscription_tier, tier_limits["free"])
        max_tokens = limit_config["tokens"]
        refill_rate = limit_config["refill_rate"]
        window = limit_config["window"]
        
        # Get current state
        current_data = await redis.hgetall(rate_limit_key)
        
        now = datetime.utcnow().timestamp()
        
        if current_data:
            tokens = float(current_data.get(b"tokens", max_tokens))
            last_refill = float(current_data.get(b"last_refill", now))
            
            # Refill tokens based on time elapsed
            time_elapsed = now - last_refill
            tokens_to_add = (time_elapsed / window) * refill_rate
            tokens = min(max_tokens, tokens + tokens_to_add)
            
            # Check if request can proceed
            if tokens < 1:
                retry_after = int((1 - tokens) / refill_rate * window)
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {user_context.subscription_tier} tier",
                    retry_after=retry_after
                )
            
            # Consume 1 token
            tokens -= 1
            
            # Update state
            await redis.hset(rate_limit_key, mapping={
                "tokens": str(tokens),
                "last_refill": str(now),
                "tier": user_context.subscription_tier
            })
        else:
            # Initialize rate limit state
            await redis.hset(rate_limit_key, mapping={
                "tokens": str(max_tokens - 1),
                "last_refill": str(now),
                "tier": user_context.subscription_tier
            })
        
        await redis.expire(rate_limit_key, window * 2)  # TTL: 2x window
    
    async def _pre_validate_credits(self, user_context: UserContext) -> None:
        """
        Check if user has sufficient credits before allowing request.
        Uses estimated cost based on max_tokens.
        """
        async with get_db() as db:
            wallet = await db.fetchrow(
                "SELECT total_credits FROM user_wallet WHERE user_id = $1",
                user_context.user_id
            )
            
            if not wallet:
                raise InsufficientCreditsError(
                    "Wallet not found",
                    current_balance=Decimal("0"),
                    required_amount=Decimal("0.1")
                )
            
            current_balance = Decimal(str(wallet["total_credits"]))
            
            # Estimate cost (assume max 1000 tokens for pre-check)
            estimated_cost = calculate_chat_cost(1000, user_context.subscription_tier)
            
            if current_balance < estimated_cost:
                raise InsufficientCreditsError(
                    f"Insufficient credits. Current balance: {current_balance}, estimated cost: {estimated_cost}",
                    current_balance=current_balance,
                    required_amount=estimated_cost
                )
    
    async def _post_deduct_credits(
        self, 
        request: Request, 
        response: Response, 
        user_context: UserContext
    ) -> None:
        """
        Atomically deduct credits after successful LLM response.
        Extracts actual token usage from response body.
        """
        # Extract token usage from response (stored in request.state by chat service)
        tokens_used = getattr(request.state, "tokens_used", None)
        session_id = getattr(request.state, "session_id", None)
        message_id = getattr(request.state, "message_id", None)
        
        if not tokens_used:
            # Fallback: estimate based on response length
            tokens_used = 500  # Conservative estimate
        
        # Calculate actual cost
        cost = calculate_chat_cost(tokens_used, user_context.subscription_tier)
        
        # Atomic deduction
        async with get_db() as db:
            async with db.transaction():
                # Lock wallet row
                wallet = await db.fetchrow(
                    "SELECT * FROM user_wallet WHERE user_id = $1 FOR UPDATE",
                    user_context.user_id
                )
                
                if not wallet:
                    raise InsufficientCreditsError(
                        "Wallet not found",
                        current_balance=Decimal("0"),
                        required_amount=cost
                    )
                
                current_balance = Decimal(str(wallet["total_credits"]))
                
                # Verify sufficient balance (double-check)
                if current_balance < cost:
                    raise InsufficientCreditsError(
                        f"Insufficient credits for deduction",
                        current_balance=current_balance,
                        required_amount=cost
                    )
                
                # Deduct credits (priority: daily_free > purchased > bonus)
                new_daily = max(Decimal("0"), Decimal(str(wallet["daily_free_credits"])) - cost)
                remaining_cost = max(Decimal("0"), cost - Decimal(str(wallet["daily_free_credits"])))
                
                new_purchased = max(Decimal("0"), Decimal(str(wallet["purchased_credits"])) - remaining_cost)
                remaining_cost = max(Decimal("0"), remaining_cost - Decimal(str(wallet["purchased_credits"])))
                
                new_bonus = max(Decimal("0"), Decimal(str(wallet["bonus_credits"])) - remaining_cost)
                
                new_total = new_daily + new_purchased + new_bonus
                
                # Update wallet
                await db.execute(
                    """
                    UPDATE user_wallet
                    SET total_credits = $1,
                        daily_free_credits = $2,
                        purchased_credits = $3,
                        bonus_credits = $4,
                        last_request_at = NOW(),
                        updated_at = NOW()
                    WHERE user_id = $5
                    """,
                    new_total, new_daily, new_purchased, new_bonus, user_context.user_id
                )
                
                # Record transaction
                await db.execute(
                    """
                    INSERT INTO transaction_history
                    (user_id, transaction_type, amount, balance_before, balance_after, reference_id, metadata, description)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    user_context.user_id,
                    "chat_deduction",
                    -cost,
                    current_balance,
                    new_total,
                    str(session_id) if session_id else None,
                    json.dumps({
                        "tokens_used": tokens_used,
                        "message_id": str(message_id) if message_id else None,
                        "tier": user_context.subscription_tier
                    }),
                    f"Chat completion ({tokens_used} tokens)"
                )
                
                # Update session total cost
                if session_id:
                    await db.execute(
                        """
                        UPDATE chat_sessions
                        SET total_credits_spent = total_credits_spent + $1,
                            updated_at = NOW()
                        WHERE session_id = $2
                        """,
                        cost, session_id
                    )


class CreditCheckDependency:
    """
    FastAPI dependency for manual credit checking in specific endpoints.
    Use this when you need fine-grained control over billing logic.
    """
    
    async def __call__(self, request: Request) -> UserContext:
        user_context: Optional[UserContext] = getattr(request.state, "user", None)
        if not user_context:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Check wallet balance
        async with get_db() as db:
            wallet = await db.fetchrow(
                "SELECT total_credits FROM user_wallet WHERE user_id = $1",
                user_context.user_id
            )
            
            if not wallet or Decimal(str(wallet["total_credits"])) <= 0:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits"
                )
        
        return user_context


async def deduct_credits_manual(
    user_id: UUID,
    amount: Decimal,
    transaction_type: str = "manual_deduction",
    reference_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    description: str = "Manual credit deduction"
) -> Decimal:
    """
    Manual credit deduction utility for non-middleware scenarios.
    Returns new balance.
    """
    async with get_db() as db:
        async with db.transaction():
            wallet = await db.fetchrow(
                "SELECT * FROM user_wallet WHERE user_id = $1 FOR UPDATE",
                user_id
            )
            
            if not wallet:
                raise InsufficientCreditsError(
                    "Wallet not found",
                    current_balance=Decimal("0"),
                    required_amount=amount
                )
            
            current_balance = Decimal(str(wallet["total_credits"]))
            
            if current_balance < amount:
                raise InsufficientCreditsError(
                    f"Insufficient credits",
                    current_balance=current_balance,
                    required_amount=amount
                )
            
            new_balance = current_balance - amount
            
            await db.execute(
                "UPDATE user_wallet SET total_credits = $1, updated_at = NOW() WHERE user_id = $2",
                new_balance, user_id
            )
            
            await db.execute(
                """
                INSERT INTO transaction_history
                (user_id, transaction_type, amount, balance_before, balance_after, reference_id, metadata, description)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                user_id, transaction_type, -amount, current_balance, new_balance,
                reference_id, json.dumps(metadata) if metadata else None, description
            )
            
            return new_balance


async def add_credits(
    user_id: UUID,
    amount: Decimal,
    credit_type: str = "purchased",  # 'purchased', 'bonus', 'daily_free'
    transaction_type: str = "purchase",
    reference_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    description: str = "Credit purchase"
) -> Decimal:
    """
    Add credits to user wallet.
    Returns new balance.
    """
    async with get_db() as db:
        async with db.transaction():
            wallet = await db.fetchrow(
                "SELECT * FROM user_wallet WHERE user_id = $1 FOR UPDATE",
                user_id
            )
            
            if not wallet:
                # Create wallet if doesn't exist
                await db.execute(
                    """
                    INSERT INTO user_wallet (user_id, total_credits, purchased_credits)
                    VALUES ($1, $2, $2)
                    """,
                    user_id, amount
                )
                new_balance = amount
                old_balance = Decimal("0")
            else:
                old_balance = Decimal(str(wallet["total_credits"]))
                
                # Update appropriate credit type
                if credit_type == "purchased":
                    new_purchased = Decimal(str(wallet["purchased_credits"])) + amount
                    await db.execute(
                        """
                        UPDATE user_wallet
                        SET purchased_credits = $1,
                            total_credits = total_credits + $2,
                            updated_at = NOW()
                        WHERE user_id = $3
                        """,
                        new_purchased, amount, user_id
                    )
                elif credit_type == "bonus":
                    new_bonus = Decimal(str(wallet["bonus_credits"])) + amount
                    await db.execute(
                        """
                        UPDATE user_wallet
                        SET bonus_credits = $1,
                            total_credits = total_credits + $2,
                            updated_at = NOW()
                        WHERE user_id = $3
                        """,
                        new_bonus, amount, user_id
                    )
                
                new_balance = old_balance + amount
            
            # Record transaction
            await db.execute(
                """
                INSERT INTO transaction_history
                (user_id, transaction_type, amount, balance_before, balance_after, reference_id, metadata, description)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                user_id, transaction_type, amount, old_balance, new_balance,
                reference_id, json.dumps(metadata) if metadata else None, description
            )
            
            return new_balance

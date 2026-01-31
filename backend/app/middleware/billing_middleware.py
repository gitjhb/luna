"""
Billing Middleware - Credit checking and deduction for chat
==========================================================

核心原则（JHB 要求）:
1. 金币 = 钱 - 所有金币相关操作都必须走 wallet 服务
2. 必须落账单 - 每笔金币变动都要写入 TransactionHistory
3. 一致性优先 - 保证数据一致性
4. **普通聊天免费，只有 spicy mode 才扣费**
5. **只有成功响应才记账单**
"""

import os
import logging
from typing import Callable
from datetime import datetime
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"
logger.info(f"BillingMiddleware MOCK_MODE: {MOCK_MODE}")

# Credit costs - 只有 spicy mode 才收费！
CREDIT_COSTS = {
    "chat_spicy": 2.0,    # Spicy mode: 2 credits per message  
    "voice_tts": 2.0,     # TTS: 2 credits
    "image_gen": 5.0,     # Image generation: 5 credits
}


class BillingContext:
    """Context object to store billing information during request lifecycle"""
    
    def __init__(self):
        self.user_id: str = None
        self.initial_credits: float = 0.0
        self.estimated_cost: float = 0.0
        self.actual_cost: float = 0.0
        self.tokens_used: int = 0
        self.is_spicy_mode: bool = False
        self.request_timestamp: float = None
        self.transaction_id: str = None
        self.deducted: bool = False


class BillingMiddleware(BaseHTTPMiddleware):
    """
    Billing middleware for credit checking and deduction.
    
    重要：普通聊天免费！只有 spicy mode 才扣费。
    
    Flow:
    1. Pre-request: Check if spicy mode, check credits if needed
    2. Process request
    3. Post-request: Deduct actual cost ONLY if request successful AND spicy mode
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Only these endpoints with spicy mode need billing
        self.billable_endpoints = {
            "/api/v1/chat/completions": "chat",
            "/api/v1/chat/stream": "chat",
            "/api/v1/voice/tts": "voice_tts",
            "/api/v1/image/generate": "image_gen",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Find matching billable endpoint
        endpoint_type = None
        for path, etype in self.billable_endpoints.items():
            if request.url.path.startswith(path):
                endpoint_type = etype
                break
        
        if not endpoint_type:
            return await call_next(request)

        # Get user from auth middleware
        user = getattr(request.state, "user", None)
        if not user:
            # Let the request proceed - auth middleware will handle it
            return await call_next(request)

        user_id = str(user.user_id) if hasattr(user, 'user_id') else str(user.get('user_id', 'unknown'))
        
        # Initialize billing context
        billing = BillingContext()
        billing.user_id = user_id
        billing.request_timestamp = datetime.utcnow().timestamp()
        request.state.billing = billing

        # In mock mode, just proceed
        if MOCK_MODE:
            logger.debug(f"[MOCK] Billing check for {request.url.path}, user: {user_id}")
            return await call_next(request)

        # =====================================================================
        # Production mode
        # Note: 普通聊天免费！Spicy mode 检测在 chat endpoint 里做，
        # 它会设置 request.state.billing.is_spicy_mode = True
        # =====================================================================
        
        # For non-chat endpoints (voice/image), pre-check credits
        if endpoint_type in ["voice_tts", "image_gen"]:
            estimated_cost = CREDIT_COSTS.get(endpoint_type, 0)
            billing.estimated_cost = estimated_cost
            
            if estimated_cost > 0:
                from app.core.database import get_db
                from sqlalchemy import select
                from app.models.database.billing_models import UserWallet
                
                try:
                    async with get_db() as db:
                        result = await db.execute(
                            select(UserWallet).where(UserWallet.user_id == user_id)
                        )
                        wallet = result.scalar_one_or_none()
                        
                        if wallet:
                            billing.initial_credits = wallet.total_credits
                            if wallet.total_credits < estimated_cost:
                                return JSONResponse(
                                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                                    content={
                                        "error": "insufficient_credits",
                                        "message": f"余额不足：当前 {wallet.total_credits:.1f} 金币，需要 {estimated_cost:.1f} 金币",
                                    },
                                )
                except Exception as e:
                    logger.error(f"Credit check failed: {e}")
        
        # Process request
        response = await call_next(request)
        
        # Post-request billing - ONLY if successful and has cost
        # For chat: only deduct if spicy mode (set by chat endpoint)
        if response.status_code < 400 and not billing.deducted:
            # Determine actual cost
            actual_cost = 0.0
            cost_type = None
            
            if endpoint_type == "chat" and billing.is_spicy_mode:
                actual_cost = CREDIT_COSTS.get("chat_spicy", 2.0)
                cost_type = "spicy"
            elif endpoint_type == "voice_tts":
                actual_cost = CREDIT_COSTS.get("voice_tts", 2.0)
                cost_type = "voice_tts"
            elif endpoint_type == "image_gen":
                actual_cost = CREDIT_COSTS.get("image_gen", 5.0)
                cost_type = "image_gen"
            
            # Only deduct if there's a cost
            if actual_cost > 0:
                billing.actual_cost = actual_cost
                await self._deduct_credits(user_id, actual_cost, cost_type, billing)
        
        return response
    
    async def _deduct_credits(self, user_id: str, amount: float, cost_type: str, billing: BillingContext):
        """Deduct credits and record transaction"""
        from app.core.database import get_db
        from sqlalchemy import select
        from app.models.database.billing_models import UserWallet, TransactionHistory, TransactionType
        
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(UserWallet).where(UserWallet.user_id == user_id).with_for_update()
                )
                wallet = result.scalar_one_or_none()
                
                if not wallet or wallet.total_credits < amount:
                    logger.warning(f"Insufficient credits at deduction time: user={user_id}")
                    return
                
                # Deduct from purchased credits first, then free credits
                if wallet.purchased_credits >= amount:
                    wallet.purchased_credits -= amount
                else:
                    remaining = amount - wallet.purchased_credits
                    wallet.purchased_credits = 0.0
                    wallet.free_credits = max(0, wallet.free_credits - remaining)
                
                wallet.total_credits = wallet.free_credits + wallet.purchased_credits
                wallet.updated_at = datetime.utcnow()
                
                # Create transaction record
                description_map = {
                    "spicy": "聊天消费 (spicy 模式)",
                    "voice_tts": "语音合成",
                    "image_gen": "图片生成",
                }
                
                transaction = TransactionHistory(
                    user_id=user_id,
                    transaction_type=TransactionType.DEDUCTION,
                    amount=-amount,
                    balance_after=wallet.total_credits,
                    description=description_map.get(cost_type, f"消费 ({cost_type})"),
                    extra_data={
                        "cost_type": cost_type,
                        "tokens_used": billing.tokens_used,
                    },
                )
                db.add(transaction)
                await db.commit()
                
                billing.transaction_id = transaction.transaction_id
                billing.deducted = True
                
                logger.info(f"Credit deduction: user={user_id}, cost={amount}, type={cost_type}, new_balance={wallet.total_credits}")
                
        except Exception as e:
            logger.error(f"Credit deduction failed: {e}", exc_info=True)


def get_billing_context(request: Request) -> BillingContext:
    """Get billing context from request"""
    return getattr(request.state, "billing", BillingContext())

"""
Payment API Routes - Subscriptions, Purchases, Gifts

Supports multiple payment providers:
- Stripe (Web)
- Apple App Store (iOS)
- Google Play (Android)
- Mock (Testing)
"""

from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.services.payment_service import (
    payment_service,
    SUBSCRIPTION_PLANS,
    CREDIT_PACKAGES,
    MOCK_PAYMENT,
)
from app.services.stripe_service import stripe_service, STRIPE_ENABLED
from app.services.iap_service import iap_service, IAPProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment")


# ============================================================================
# Request/Response Models
# ============================================================================

class PurchaseRequest(BaseModel):
    package_id: str
    payment_provider: str = "mock"
    provider_transaction_id: Optional[str] = None


class SubscribeRequest(BaseModel):
    plan_id: str
    billing_period: str = "monthly"  # monthly or yearly
    payment_provider: str = "mock"
    provider_transaction_id: Optional[str] = None


class SendGiftRequest(BaseModel):
    character_id: str
    gift_type: str
    gift_price: int
    xp_reward: int


class WalletResponse(BaseModel):
    user_id: str
    total_credits: int
    purchased_credits: int
    bonus_credits: int
    daily_free_credits: int


class SubscriptionResponse(BaseModel):
    user_id: str
    tier: str
    started_at: Optional[str]
    expires_at: Optional[str]
    auto_renew: bool
    is_active: bool


# Stripe-specific models
class StripeCheckoutRequest(BaseModel):
    package_id: str  # Credit package ID
    success_url: str
    cancel_url: str


class StripeSubscriptionCheckoutRequest(BaseModel):
    plan_id: str  # e.g., "premium_monthly", "vip_yearly"
    success_url: str
    cancel_url: str


# IAP-specific models
class IAPVerifyRequest(BaseModel):
    provider: str  # "apple" or "google"
    receipt_data: str  # Base64 receipt (Apple) or purchase token (Google)
    product_id: Optional[str] = None  # Required for Google
    purchase_token: Optional[str] = None  # Google-specific


# ============================================================================
# Info Endpoints
# ============================================================================

@router.get("/config")
async def get_payment_config():
    """Get payment configuration (mock mode status, available packages/plans)"""
    return {
        "mock_mode": MOCK_PAYMENT,
        "credit_packages": list(CREDIT_PACKAGES.values()),
        "subscription_plans": list(SUBSCRIPTION_PLANS.values()),
    }


@router.get("/plans")
async def get_available_plans(req: Request):
    """Get subscription plans available for the current user"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    plans = await payment_service.get_available_plans(user_id)
    return {"plans": plans}


# ============================================================================
# Wallet Endpoints
# ============================================================================

@router.get("/wallet")
async def get_wallet(req: Request):
    """Get current user's wallet"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    wallet = await payment_service.get_wallet(user_id)
    return wallet


@router.post("/wallet/add-credits")
async def add_credits(amount: int, req: Request):
    """Add credits to wallet (for testing/admin)"""
    if not MOCK_PAYMENT:
        raise HTTPException(status_code=403, detail="Only available in mock mode")
    
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    wallet = await payment_service.add_credits(user_id, amount, is_purchased=False)
    return {"success": True, "wallet": wallet}


# ============================================================================
# Purchase Endpoints
# ============================================================================

@router.post("/purchase")
async def purchase_credits(request: PurchaseRequest, req: Request):
    """Purchase a credit package"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    try:
        result = await payment_service.purchase_credits(
            user_id=user_id,
            package_id=request.package_id,
            payment_provider=request.payment_provider,
            provider_transaction_id=request.provider_transaction_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


# ============================================================================
# Subscription Endpoints
# ============================================================================

@router.get("/subscription")
async def get_subscription(req: Request):
    """Get current subscription status"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    subscription = await payment_service.get_subscription(user_id)
    return subscription


@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, req: Request):
    """Subscribe to a plan"""
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    try:
        result = await payment_service.subscribe(
            user_id=user_id,
            plan_id=request.plan_id,
            billing_period=request.billing_period,
            payment_provider=request.payment_provider,
            provider_transaction_id=request.provider_transaction_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


class CancelSubscriptionRequest(BaseModel):
    immediate: bool = True  # True = cancel now, False = stop auto-renew only


@router.post("/subscription/cancel")
async def cancel_subscription(request: CancelSubscriptionRequest = None, req: Request = None):
    """Cancel subscription
    
    - immediate=True: Cancel now, downgrade to free (no refund, credits preserved)
    - immediate=False: Stop auto-renew, keep benefits until expiry
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    immediate = request.immediate if request else True
    result = await payment_service.cancel_subscription(user_id, immediate=immediate)
    return result


# ============================================================================
# Transaction History
# ============================================================================

@router.get("/transactions")
async def get_transactions(limit: int = 20, offset: int = 0, req: Request = None):
    """Get transaction history"""
    user = getattr(req.state, "user", None) if req else None
    user_id = str(user.user_id) if user else "demo-user-123"
    
    transactions = await payment_service.get_transactions(user_id, limit, offset)
    return {"transactions": transactions, "total": len(transactions)}


# ============================================================================
# Stripe Endpoints (Web payments)
# ============================================================================

@router.get("/stripe/config")
async def get_stripe_config():
    """Get Stripe configuration for frontend"""
    return {
        "enabled": STRIPE_ENABLED,
        "publishable_key": stripe_service.get_publishable_key() if STRIPE_ENABLED else None,
    }


@router.post("/stripe/checkout")
async def create_stripe_checkout(request: StripeCheckoutRequest, req: Request):
    """
    Create a Stripe checkout session for credit purchase.
    
    Returns checkout URL to redirect user to Stripe's hosted payment page.
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    user_email = getattr(user, "email", None) if user else None
    
    try:
        result = await stripe_service.create_checkout_session(
            user_id=user_id,
            package_id=request.package_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=user_email,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail="Payment service error")


@router.post("/stripe/subscribe")
async def create_stripe_subscription_checkout(request: StripeSubscriptionCheckoutRequest, req: Request):
    """
    Create a Stripe checkout session for subscription.
    
    Returns checkout URL to redirect user to Stripe's hosted subscription page.
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    user_email = getattr(user, "email", None) if user else None
    
    try:
        result = await stripe_service.create_subscription_checkout(
            user_id=user_id,
            plan_id=request.plan_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=user_email,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe subscription error: {e}")
        raise HTTPException(status_code=500, detail="Payment service error")


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Handle Stripe webhook events.
    
    Configure webhook endpoint in Stripe Dashboard:
    https://dashboard.stripe.com/webhooks
    
    Events to enable:
    - checkout.session.completed
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - invoice.payment_failed
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    # Get raw body for signature verification
    payload = await request.body()
    
    try:
        # Verify webhook signature
        event = stripe_service.verify_webhook_signature(payload, stripe_signature)
        
        # Handle the event
        result = await stripe_service.handle_webhook_event(event)
        
        logger.info(f"Webhook processed: {event.type} -> {result}")
        return JSONResponse(content=result, status_code=200)
        
    except ValueError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


@router.post("/stripe/portal")
async def create_stripe_portal(return_url: str, req: Request):
    """
    Create a Stripe Customer Portal session for subscription management.
    
    Allows users to manage their subscriptions, update payment methods, etc.
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    
    user = getattr(req.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = str(user.user_id)
    user_email = getattr(user, "email", None)
    
    try:
        # Get or create customer
        customer_id = await stripe_service.get_or_create_customer(
            user_id=user_id,
            email=user_email or f"{user_id}@luna.app",
            name=getattr(user, "display_name", None),
        )
        
        # Create portal session
        portal_url = await stripe_service.create_customer_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )
        
        return {"portal_url": portal_url}
        
    except Exception as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=500, detail="Portal service error")


# ============================================================================
# In-App Purchase Endpoints (iOS/Android)
# ============================================================================

@router.get("/iap/products")
async def get_iap_products(provider: str):
    """
    Get available IAP products for a platform.
    
    Args:
        provider: 'apple' or 'google'
    """
    try:
        iap_provider = IAPProvider(provider.lower())
        products = iap_service.get_available_products(iap_provider)
        return products
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")


@router.post("/iap/verify")
async def verify_iap_purchase(request: IAPVerifyRequest, req: Request):
    """
    Verify and fulfill an in-app purchase.
    
    For Apple:
        - provider: "apple"
        - receipt_data: Base64 encoded receipt
    
    For Google:
        - provider: "google"
        - receipt_data: Purchase token
        - product_id: Product ID (required)
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    try:
        iap_provider = IAPProvider(request.provider.lower())
        
        result = await iap_service.verify_and_fulfill(
            user_id=user_id,
            provider=iap_provider,
            receipt_data=request.receipt_data,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"IAP verification error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"IAP error: {e}")
        raise HTTPException(status_code=500, detail="IAP verification error")


@router.post("/iap/restore")
async def restore_iap_purchases(request: IAPVerifyRequest, req: Request):
    """
    Restore previous purchases (for "Restore Purchases" button).
    
    Same as verify endpoint but specifically for restoration flow.
    Apple requires apps to have a "Restore Purchases" option.
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    try:
        iap_provider = IAPProvider(request.provider.lower())
        
        result = await iap_service.verify_and_fulfill(
            user_id=user_id,
            provider=iap_provider,
            receipt_data=request.receipt_data,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
        )
        
        return {
            "restored": True,
            **result,
        }
        
    except ValueError as e:
        logger.error(f"IAP restore error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"IAP restore error: {e}")
        raise HTTPException(status_code=500, detail="IAP restore error")

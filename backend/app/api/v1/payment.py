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
# Apple App Store Server Notifications (Webhooks)
# ============================================================================

class AppleNotificationPayload(BaseModel):
    """Apple Server Notification V2 payload"""
    signedPayload: str


@router.post("/apple/webhook")
async def apple_server_notification(request: Request):
    """
    Handle Apple App Store Server Notifications V2.
    
    Configure in App Store Connect:
    App Store Connect → Your App → App Information → App Store Server Notifications
    
    Set URL to: https://your-domain.com/api/v1/payment/apple/webhook
    
    Events handled:
    - SUBSCRIBED: New subscription
    - DID_RENEW: Renewal success
    - DID_CHANGE_RENEWAL_STATUS: User cancelled/reactivated auto-renew
    - DID_FAIL_TO_RENEW: Billing issue
    - EXPIRED: Subscription expired
    - GRACE_PERIOD_EXPIRED: Grace period ended
    - REFUND: User got refund
    - REVOKE: Family sharing revoked
    """
    try:
        # Parse request body
        body = await request.json()
        signed_payload = body.get("signedPayload")
        
        if not signed_payload:
            logger.warning("Apple webhook: missing signedPayload")
            raise HTTPException(status_code=400, detail="Missing signedPayload")
        
        # Process notification
        result = await iap_service.handle_apple_notification(signed_payload)
        
        logger.info(f"Apple webhook processed: {result.get('notification_type')}")
        return JSONResponse(content=result, status_code=200)
        
    except ValueError as e:
        logger.error(f"Apple webhook validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Apple webhook error: {e}", exc_info=True)
        # Return 200 to prevent Apple from retrying (we log the error)
        # Apple will retry on 4xx/5xx which could cause duplicate processing
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=200
        )


@router.post("/apple/webhook/test")
async def test_apple_webhook(request: Request):
    """
    Test endpoint for Apple webhook (development only).
    Simulates various notification types.
    """
    if not MOCK_PAYMENT:
        raise HTTPException(status_code=403, detail="Only available in mock mode")
    
    body = await request.json()
    notification_type = body.get("notification_type", "DID_RENEW")
    user_id = body.get("user_id", "test-user")
    product_id = body.get("product_id", "luna_premium_monthly")
    
    logger.info(f"Test Apple webhook: {notification_type} for {user_id}")
    
    # Simulate notification processing
    from app.services.payment_service import payment_service
    
    if notification_type == "DID_CHANGE_RENEWAL_STATUS":
        subtype = body.get("subtype", "AUTO_RENEW_DISABLED")
        auto_renew = subtype != "AUTO_RENEW_DISABLED"
        result = await payment_service.update_subscription_auto_renew(user_id, auto_renew)
    elif notification_type in ("EXPIRED", "GRACE_PERIOD_EXPIRED"):
        result = await payment_service.expire_subscription(user_id)
    elif notification_type == "DID_FAIL_TO_RENEW":
        result = await payment_service.mark_billing_issue(user_id)
    elif notification_type == "REFUND":
        result = await payment_service.handle_refund(user_id, "test-txn-123")
    else:
        result = {"message": f"Unhandled type: {notification_type}"}
    
    return {"test": True, "notification_type": notification_type, "result": result}


# ============================================================================
# Google Play Real-time Developer Notifications (Webhooks)
# ============================================================================

class GooglePubSubMessage(BaseModel):
    """Google Cloud Pub/Sub push message"""
    message: dict
    subscription: Optional[str] = None


@router.post("/google/webhook")
async def google_play_notification(request: Request):
    """
    Handle Google Play Real-time Developer Notifications.
    
    Configure in Google Play Console:
    1. Go to Monetization Setup → Real-time developer notifications
    2. Set Topic name (create a Pub/Sub topic)
    3. Create a push subscription to: https://your-domain.com/api/v1/payment/google/webhook
    
    Events handled:
    - SUBSCRIPTION_PURCHASED (4): New subscription
    - SUBSCRIPTION_RENEWED (2): Renewal success
    - SUBSCRIPTION_CANCELED (3): User cancelled
    - SUBSCRIPTION_ON_HOLD (5): Payment on hold
    - SUBSCRIPTION_IN_GRACE_PERIOD (6): Grace period
    - SUBSCRIPTION_RECOVERED (1): Recovered from hold
    - SUBSCRIPTION_RESTARTED (7): User resubscribed
    - SUBSCRIPTION_REVOKED (12): Subscription revoked
    - SUBSCRIPTION_EXPIRED (13): Subscription expired
    """
    try:
        # Google Pub/Sub sends a specific format
        body = await request.json()
        
        # Extract the base64-encoded message data
        message = body.get("message", {})
        message_data = message.get("data")
        
        if not message_data:
            logger.warning("Google webhook: missing message data")
            # Return 200 to acknowledge receipt (prevent retries)
            return JSONResponse(content={"status": "no_data"}, status_code=200)
        
        # Process notification
        result = await iap_service.handle_google_notification(message_data)
        
        logger.info(f"Google webhook processed: {result.get('type')}")
        return JSONResponse(content=result, status_code=200)
        
    except ValueError as e:
        logger.error(f"Google webhook validation error: {e}")
        # Return 200 to prevent infinite retries
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=200)
    except Exception as e:
        logger.error(f"Google webhook error: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=200)


@router.post("/google/webhook/test")
async def test_google_webhook(request: Request):
    """
    Test endpoint for Google webhook (development only).
    """
    if not MOCK_PAYMENT:
        raise HTTPException(status_code=403, detail="Only available in mock mode")
    
    body = await request.json()
    notification_type = body.get("notification_type", 2)  # Default: RENEWED
    user_id = body.get("user_id", "test-user")
    
    NOTIFICATION_NAMES = {
        1: "SUBSCRIPTION_RECOVERED",
        2: "SUBSCRIPTION_RENEWED",
        3: "SUBSCRIPTION_CANCELED",
        4: "SUBSCRIPTION_PURCHASED",
        5: "SUBSCRIPTION_ON_HOLD",
        6: "SUBSCRIPTION_IN_GRACE_PERIOD",
        7: "SUBSCRIPTION_RESTARTED",
        12: "SUBSCRIPTION_REVOKED",
        13: "SUBSCRIPTION_EXPIRED",
    }
    
    type_name = NOTIFICATION_NAMES.get(notification_type, f"UNKNOWN_{notification_type}")
    logger.info(f"Test Google webhook: {type_name} for {user_id}")
    
    from app.services.payment_service import payment_service
    
    if notification_type == 3:  # CANCELED
        result = await payment_service.update_subscription_auto_renew(user_id, False)
    elif notification_type in (5, 6):  # ON_HOLD or GRACE_PERIOD
        result = await payment_service.mark_billing_issue(user_id)
    elif notification_type == 7:  # RESTARTED
        result = await payment_service.update_subscription_auto_renew(user_id, True)
    elif notification_type in (12, 13):  # REVOKED or EXPIRED
        result = await payment_service.expire_subscription(user_id)
    else:
        result = {"message": f"Type {type_name} - no action in test mode"}
    
    return {"test": True, "notification_type": type_name, "result": result}


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

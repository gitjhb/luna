"""
Stripe Payment Service
======================

Handles Stripe checkout sessions, subscriptions, and webhooks.

Environment variables required:
- STRIPE_SECRET_KEY: Your Stripe secret key (sk_test_... or sk_live_...)
- STRIPE_WEBHOOK_SECRET: Webhook endpoint secret (whsec_...)
- STRIPE_PUBLISHABLE_KEY: For frontend (pk_test_... or pk_live_...)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe initialized successfully")
else:
    logger.warning("STRIPE_SECRET_KEY not set - Stripe payments disabled")


# ============================================================================
# Product Configuration
# ============================================================================

# Map our credit packages to Stripe Price IDs
# These should be created in your Stripe Dashboard
STRIPE_CREDIT_PACKAGES = {
    "pack_60": {
        "price_id": os.getenv("STRIPE_PRICE_PACK_60", "price_pack_60"),
        "coins": 60,
        "bonus": 0,
        "price_cents": 99,
    },
    "pack_300": {
        "price_id": os.getenv("STRIPE_PRICE_PACK_300", "price_pack_300"),
        "coins": 300,
        "bonus": 30,
        "price_cents": 499,
    },
    "pack_980": {
        "price_id": os.getenv("STRIPE_PRICE_PACK_980", "price_pack_980"),
        "coins": 980,
        "bonus": 110,
        "price_cents": 1499,
    },
    "pack_1980": {
        "price_id": os.getenv("STRIPE_PRICE_PACK_1980", "price_pack_1980"),
        "coins": 1980,
        "bonus": 260,
        "price_cents": 2999,
    },
    "pack_3280": {
        "price_id": os.getenv("STRIPE_PRICE_PACK_3280", "price_pack_3280"),
        "coins": 3280,
        "bonus": 600,
        "price_cents": 4999,
    },
    "pack_6480": {
        "price_id": os.getenv("STRIPE_PRICE_PACK_6480", "price_pack_6480"),
        "coins": 6480,
        "bonus": 1600,
        "price_cents": 9999,
    },
}

# Map subscription plans to Stripe Price IDs
# Luna 订阅分两档：basic / premium
# Stripe 产品：
#   - Basic Plan (prod_TyaqYmJJSZjbV9, price_1T3Zy1BGtpEcBypWJlKScOSD) → basic
#   - Premium (prod_TyaZ8zAFF70OqP, price_1T3ZzKBGtpEcBypWCQBVv5Ek) → premium
STRIPE_SUBSCRIPTION_PLANS = {
    "basic_monthly": {
        "price_id": os.getenv("STRIPE_PRICE_BASIC_MONTHLY", "price_1T3Zy1BGtpEcBypWJlKScOSD"),
        "tier": "basic",
        "billing_period": "monthly",
        "daily_credits": 50,
    },
    "basic_yearly": {
        "price_id": os.getenv("STRIPE_PRICE_BASIC_YEARLY", "price_basic_yearly"),
        "tier": "basic",
        "billing_period": "yearly",
        "daily_credits": 50,
    },
    "premium_monthly": {
        "price_id": os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", "price_1T3ZzKBGtpEcBypWCQBVv5Ek"),
        "tier": "premium",
        "billing_period": "monthly",
        "daily_credits": 200,
    },
    "premium_yearly": {
        "price_id": os.getenv("STRIPE_PRICE_PREMIUM_YEARLY", "price_premium_yearly"),
        "tier": "premium",
        "billing_period": "yearly",
        "daily_credits": 200,
    },
}

# Reverse lookup: price_id → tier (for webhook processing)
STRIPE_PRICE_TO_TIER = {
    "price_1T3Zy1BGtpEcBypWJlKScOSD": "basic",   # Basic Plan monthly
    "price_1T3ZzKBGtpEcBypWCQBVv5Ek": "premium", # Premium monthly
}


class StripeService:
    """
    Stripe payment integration service.
    
    Flow for one-time purchases (credits):
    1. Frontend calls create_checkout_session()
    2. User completes payment on Stripe's hosted page
    3. Stripe sends webhook to our server
    4. We verify and fulfill the order
    
    Flow for subscriptions:
    1. Frontend calls create_subscription_checkout()
    2. User subscribes on Stripe's hosted page
    3. Stripe sends webhook for subscription events
    4. We update user's subscription status
    """
    
    def __init__(self):
        self.enabled = STRIPE_ENABLED
    
    # ========================================================================
    # Checkout Sessions (One-time purchases)
    # ========================================================================
    
    async def create_checkout_session(
        self,
        user_id: str,
        package_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session for credit package purchase.
        
        Args:
            user_id: Internal user ID
            package_id: Credit package ID (e.g., "pack_300")
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            customer_email: Optional email for the customer
            
        Returns:
            dict with checkout_url and session_id
        """
        if not self.enabled:
            raise NotImplementedError("Stripe is not configured")
        
        if package_id not in STRIPE_CREDIT_PACKAGES:
            raise ValueError(f"Invalid package: {package_id}")
        
        package = STRIPE_CREDIT_PACKAGES[package_id]
        
        try:
            # Create checkout session
            session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[{
                    "price": package["price_id"],
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    "firebase_uid": user_id,  # Primary key - must have!
                    "package_id": package_id,
                    "type": "credit_purchase",
                    "coins": str(package["coins"]),
                    "bonus": str(package["bonus"]),
                },
                # Allow promo codes
                allow_promotion_codes=True,
                # Collect billing address
                billing_address_collection="auto",
            )
            
            logger.info(f"Created checkout session {session.id} for user {user_id}, package {package_id}")
            
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "package_id": package_id,
                "coins": package["coins"],
                "bonus": package["bonus"],
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout: {e}")
            raise RuntimeError(f"Payment error: {str(e)}")
    
    # ========================================================================
    # Subscription Checkout
    # ========================================================================
    
    async def create_subscription_checkout(
        self,
        user_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session for subscription.
        
        Args:
            user_id: Internal user ID
            plan_id: Subscription plan ID (e.g., "premium_monthly")
            success_url: URL to redirect after successful subscription
            cancel_url: URL to redirect if user cancels
            customer_email: Optional email for the customer
            
        Returns:
            dict with checkout_url and session_id
        """
        if not self.enabled:
            raise NotImplementedError("Stripe is not configured")
        
        if plan_id not in STRIPE_SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid subscription plan: {plan_id}")
        
        plan = STRIPE_SUBSCRIPTION_PLANS[plan_id]
        
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{
                    "price": plan["price_id"],
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                # IMPORTANT: client_reference_id is used by RevenueCat to identify the user
                client_reference_id=user_id,
                metadata={
                    "firebase_uid": user_id,  # Primary key - must have!
                    "tier": plan["tier"],
                    "plan_id": plan_id,
                    "type": "subscription",
                },
                # Subscription-specific settings
                subscription_data={
                    "metadata": {
                        "firebase_uid": user_id,  # Primary key - must have!
                        "tier": plan["tier"],
                        "plan_id": plan_id,
                    },
                },
                allow_promotion_codes=True,
            )
            
            logger.info(f"Created subscription checkout {session.id} for user {user_id}, plan {plan_id}")
            
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "plan_id": plan_id,
                "tier": plan["tier"],
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription checkout: {e}")
            raise RuntimeError(f"Subscription error: {str(e)}")
    
    # ========================================================================
    # Subscription Management
    # ========================================================================
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """
        Cancel a Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period (default)
            
        Returns:
            Updated subscription info
        """
        if not self.enabled:
            raise NotImplementedError("Stripe is not configured")
        
        try:
            if at_period_end:
                # Cancel at end of period (user keeps access until then)
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                # Immediate cancellation
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Cancelled subscription {subscription_id}, at_period_end={at_period_end}")
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {e}")
            raise RuntimeError(f"Cancellation error: {str(e)}")
    
    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription details from Stripe."""
        if not self.enabled:
            return None
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "metadata": subscription.metadata,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving subscription: {e}")
            return None
    
    # ========================================================================
    # Customer Management
    # ========================================================================
    
    async def get_or_create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
    ) -> str:
        """
        Get existing Stripe customer or create new one.
        
        Returns:
            Stripe customer ID
        """
        if not self.enabled:
            raise NotImplementedError("Stripe is not configured")
        
        try:
            # Search for existing customer
            customers = stripe.Customer.search(
                query=f"metadata['user_id']:'{user_id}'",
                limit=1,
            )
            
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id},
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Error managing customer: {e}")
            raise RuntimeError(f"Customer error: {str(e)}")
    
    async def get_stored_customer_id(self, user_id: str) -> Optional[str]:
        """
        Get Stripe customer ID from our database.
        This is the preferred method - avoids Stripe API calls and ensures correct customer.
        
        Returns:
            Stripe customer ID if stored, None otherwise
        """
        try:
            from app.core.database import get_db
            from app.models.database.user_models import User
            from sqlalchemy import select
            
            async with get_db() as db:
                result = await db.execute(
                    select(User.stripe_customer_id).where(User.user_id == user_id)
                )
                row = result.first()
                if row and row[0]:
                    return row[0]
            return None
        except Exception as e:
            logger.warning(f"Failed to get stored customer ID for {user_id}: {e}")
            return None
    
    async def _link_stripe_customer(self, user_id: str, stripe_customer_id: str) -> bool:
        """
        Link a Stripe customer ID to our user record.
        Called when checkout completes to ensure customer<->user mapping.
        
        Args:
            user_id: Our internal user ID
            stripe_customer_id: Stripe customer ID (cus_xxx)
            
        Returns:
            True if linked successfully
        """
        try:
            from app.core.database import get_db
            from app.models.database.user_models import User
            from sqlalchemy import update
            
            async with get_db() as db:
                await db.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(stripe_customer_id=stripe_customer_id)
                )
                await db.commit()
            
            logger.info(f"Linked Stripe customer {stripe_customer_id} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to link Stripe customer {stripe_customer_id} to user {user_id}: {e}")
            return False
    
    async def _ensure_user_exists(
        self,
        user_id: str,
        email: str = None,
        stripe_customer_id: str = None,
    ) -> bool:
        """
        Ensure a user exists in the database. Creates if not exists.
        Called before processing Payment Link webhooks.
        
        Args:
            user_id: Firebase UID or internal user ID
            email: User email from Stripe checkout
            stripe_customer_id: Stripe customer ID to link
            
        Returns:
            True if user exists or was created
        """
        try:
            from app.core.database import get_db
            from app.models.database.user_models import User
            from app.models.database.billing_models import UserWallet
            from app.core.config import settings
            from sqlalchemy import select
            from datetime import datetime
            
            async with get_db() as db:
                # Check if user exists
                result = await db.execute(
                    select(User).where(User.firebase_uid == user_id)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # User exists, update stripe_customer_id if provided
                    if stripe_customer_id and not existing_user.stripe_customer_id:
                        existing_user.stripe_customer_id = stripe_customer_id
                        await db.commit()
                    return True
                
                # Create new user
                logger.info(f"Creating new user for Payment Link: {user_id}")
                user = User(
                    firebase_uid=user_id,
                    email=email or f"{user_id}@payment-link.local",
                    display_name=email.split("@")[0] if email else "User",
                    stripe_customer_id=stripe_customer_id,
                    is_subscribed=False,
                    subscription_tier="free",
                    last_login_at=datetime.utcnow(),
                )
                db.add(user)
                await db.flush()
                
                # Create wallet
                wallet = UserWallet(
                    user_id=user.user_id,
                    free_credits=settings.DAILY_REFRESH_AMOUNT,
                    purchased_credits=0.0,
                    total_credits=settings.DAILY_REFRESH_AMOUNT,
                    daily_refresh_amount=settings.DAILY_REFRESH_AMOUNT,
                )
                db.add(wallet)
                await db.commit()
                
                logger.info(f"Created user {user.user_id} (firebase_uid={user_id}) for Payment Link")
                return True
                
        except Exception as e:
            logger.error(f"Failed to ensure user exists for {user_id}: {e}")
            return False
    
    async def get_customer_for_user(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
    ) -> str:
        """
        Get Stripe customer ID for a user. Checks stored ID first, then Stripe API.
        
        Priority:
        1. Stored stripe_customer_id in our database (most reliable)
        2. Search Stripe by user_id metadata
        3. Create new customer
        
        Returns:
            Stripe customer ID
        """
        # 1. Check stored customer ID first (fastest, most reliable)
        stored_id = await self.get_stored_customer_id(user_id)
        if stored_id:
            logger.debug(f"Using stored Stripe customer {stored_id} for user {user_id}")
            return stored_id
        
        # 2. Fall back to search/create
        customer_id = await self.get_or_create_customer(user_id, email, name)
        
        # 3. Store for future use
        await self._link_stripe_customer(user_id, customer_id)
        
        return customer_id
    
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """
        Create a customer portal session for subscription management.
        
        Returns:
            Portal URL
        """
        if not self.enabled:
            raise NotImplementedError("Stripe is not configured")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Error creating portal session: {e}")
            raise RuntimeError(f"Portal error: {str(e)}")
    
    # ========================================================================
    # Webhook Handling
    # ========================================================================
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Verify Stripe webhook signature and return event.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            Verified Stripe Event
            
        Raises:
            ValueError: If signature is invalid
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("Webhook secret not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                STRIPE_WEBHOOK_SECRET,
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise ValueError("Invalid signature")
    
    async def handle_webhook_event(self, event: stripe.Event) -> Dict[str, Any]:
        """
        Handle a verified Stripe webhook event.
        
        Args:
            event: Verified Stripe Event
            
        Returns:
            Processing result
        """
        event_type = event.type
        data = event.data.object
        
        logger.info(f"Processing webhook: {event_type}")
        
        # One-time payment completed
        if event_type == "checkout.session.completed":
            return await self._handle_checkout_completed(data)
        
        # Subscription events
        elif event_type == "customer.subscription.created":
            return await self._handle_subscription_created(data)
        
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data)
        
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data)
        
        # Invoice events (for subscription renewals)
        elif event_type == "invoice.paid":
            return await self._handle_invoice_paid(data)
        
        elif event_type == "invoice.payment_failed":
            return await self._handle_invoice_payment_failed(data)
        
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
            return {"handled": False, "event_type": event_type}
    
    async def _handle_checkout_completed(self, session: Dict) -> Dict[str, Any]:
        """Handle checkout.session.completed event."""
        metadata = session.get("metadata", {})
        purchase_type = metadata.get("type")
        
        # Get firebase_uid from metadata (primary), fallback to user_id (legacy)
        user_id = metadata.get("firebase_uid") or metadata.get("user_id")
        
        # Fallback to client_reference_id (used by Payment Links)
        if not user_id:
            user_id = session.get("client_reference_id")
            if user_id:
                logger.info(f"Using client_reference_id as firebase_uid: {user_id}")
        
        if not user_id:
            logger.error("No user_id in checkout metadata or client_reference_id")
            return {"error": "Missing user_id"}
        
        # CRITICAL: Ensure user exists in database before processing
        # This handles Payment Link users who may not have logged in yet
        stripe_customer_id = session.get("customer")
        customer_email = session.get("customer_details", {}).get("email")
        
        await self._ensure_user_exists(
            user_id=user_id,
            email=customer_email,
            stripe_customer_id=stripe_customer_id,
        )
        logger.info(f"Ensured user {user_id} exists, linked to Stripe customer {stripe_customer_id}")
        
        # For Payment Links: infer purchase type from line_items or amount
        if not purchase_type:
            # Check if this is a Payment Link purchase (credits)
            amount_total = session.get("amount_total", 0)  # in cents
            if amount_total > 0:
                purchase_type = "payment_link_credit"
                logger.info(f"Payment Link purchase detected: {amount_total} cents")
        
        if purchase_type == "credit_purchase":
            # Credit package purchase
            package_id = metadata.get("package_id")
            coins = int(metadata.get("coins", 0))
            bonus = int(metadata.get("bonus", 0))
            total_credits = coins + bonus
            
            # Add credits to user's wallet
            from app.services.payment_service import payment_service
            wallet = await payment_service.add_credits(
                user_id=user_id,
                amount=total_credits,
                is_purchased=True,
                description=f"Stripe purchase: {package_id} ({coins}+{bonus} credits)",
            )
            
            logger.info(f"Added {total_credits} credits for user {user_id} (Stripe session {session['id']})")
            
            return {
                "handled": True,
                "type": "credit_purchase",
                "user_id": user_id,
                "credits_added": total_credits,
                "session_id": session["id"],
            }
        
        elif purchase_type == "payment_link_credit":
            # Payment Link purchase (Telegram users)
            # Map amount to credits (customize based on your pricing)
            amount_cents = session.get("amount_total", 0)
            
            # Credit mapping: $0.99 = 100 credits, $4.99 = 550, $9.99 = 1200, etc.
            PAYMENT_LINK_CREDITS = {
                99: 100,      # $0.99 test
                499: 550,     # $4.99
                999: 1200,    # $9.99
                1999: 2600,   # $19.99
                4999: 7000,   # $49.99
            }
            
            credits = PAYMENT_LINK_CREDITS.get(amount_cents, amount_cents)  # fallback: 1 cent = 1 credit
            
            from app.services.payment_service import payment_service
            
            # For Telegram users, user_id is telegram_id - need to find or create Luna user
            # Check if this is a telegram_id (numeric string)
            actual_user_id = user_id
            if user_id.isdigit():
                # This is a Telegram ID, look up the Luna user
                from app.core.database import get_db
                from app.models.database.user_models import User
                from sqlalchemy import select
                
                async with get_db() as db:
                    result = await db.execute(
                        select(User).where(User.telegram_id == user_id)
                    )
                    luna_user = result.scalar_one_or_none()
                    if luna_user:
                        actual_user_id = str(luna_user.user_id)
                        logger.info(f"Found Luna user {actual_user_id} for Telegram ID {user_id}")
                    else:
                        logger.warning(f"No Luna user found for Telegram ID {user_id}, using telegram_id as user_id")
            
            wallet = await payment_service.add_credits(
                user_id=actual_user_id,
                amount=credits,
                is_purchased=True,
                description=f"Payment Link purchase: ${amount_cents/100:.2f} -> {credits} credits",
            )
            
            logger.info(f"Payment Link: Added {credits} credits for user {actual_user_id} (telegram: {user_id})")
            
            return {
                "handled": True,
                "type": "payment_link_credit",
                "user_id": actual_user_id,
                "telegram_id": user_id,
                "credits_added": credits,
                "amount_cents": amount_cents,
                "session_id": session["id"],
            }
        
        elif purchase_type == "subscription":
            # Subscription via our endpoint (has metadata)
            # Actual subscription handling happens in subscription.created
            logger.info(f"Subscription checkout completed for user {user_id}")
            return {
                "handled": True,
                "type": "subscription_checkout",
                "user_id": user_id,
            }
        
        # Handle Payment Link subscriptions (mode=subscription but no metadata.type)
        # This is the fallback for subscriptions created via Payment Links
        session_mode = session.get("mode")
        subscription_id = session.get("subscription")
        
        if session_mode == "subscription" and subscription_id and user_id:
            logger.info(f"Payment Link subscription detected for user {user_id}, sub: {subscription_id}")
            
            # Get subscription details to determine tier
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                price_id = sub.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
                
                # Infer tier from price_id using reverse lookup
                tier = STRIPE_PRICE_TO_TIER.get(price_id)
                if not tier:
                    # Fallback: search in plans
                    for plan_id, plan_config in STRIPE_SUBSCRIPTION_PLANS.items():
                        if plan_config.get("price_id") == price_id:
                            tier = plan_config.get("tier")
                            break
                if not tier:
                    tier = "basic"  # default to basic if unknown
                    logger.warning(f"Unknown price_id {price_id}, defaulting to basic")
                
                # Calculate duration from Stripe period
                period_end = sub.get("current_period_end", 0)
                period_start = sub.get("current_period_start", 0)
                duration_days = max(30, (period_end - period_start) // 86400)  # at least 30 days
                
                # Activate subscription
                from app.services.subscription_service import subscription_service
                await subscription_service.activate_subscription(
                    user_id=user_id,
                    tier=tier,
                    duration_days=duration_days,
                    payment_provider="stripe",
                    provider_transaction_id=subscription_id,
                )
                
                # Update subscription metadata for future webhook events
                stripe.Subscription.modify(
                    subscription_id,
                    metadata={
                        "firebase_uid": user_id,  # Primary key
                        "tier": tier,
                    }
                )
                
                logger.info(f"Payment Link subscription activated: user={user_id}, tier={tier}, days={duration_days}")
                
                return {
                    "handled": True,
                    "type": "payment_link_subscription",
                    "user_id": user_id,
                    "tier": tier,
                    "subscription_id": subscription_id,
                }
                
            except Exception as e:
                logger.error(f"Failed to process Payment Link subscription: {e}")
                return {"error": f"Payment Link subscription processing failed: {str(e)}"}
        
        return {"handled": False, "reason": "Unknown purchase type"}
    
    async def _handle_subscription_created(self, subscription: Dict) -> Dict[str, Any]:
        """Handle customer.subscription.created event."""
        metadata = subscription.get("metadata", {})
        # Get firebase_uid from metadata (primary), fallback to legacy keys
        user_id = metadata.get("firebase_uid") or metadata.get("user_id") or metadata.get("app_user_id")
        tier = metadata.get("tier", "basic")  # default to basic if not specified
        
        # Fallback: if no user_id in metadata, try to find from checkout session
        # This handles Payment Link subscriptions where checkout.session.completed
        # already processed the subscription (skip duplicate activation)
        if not user_id:
            # Check if this subscription was already handled by checkout.session.completed
            # by looking at whether metadata was populated (we set it there)
            if metadata.get("firebase_uid"):
                # Already processed, skip
                logger.info(f"Subscription {subscription['id']} already has firebase_uid in metadata, skipping")
                return {"handled": True, "type": "subscription_created", "skipped": True}
            
            # Try to find user_id from customer's stored link
            stripe_customer_id = subscription.get("customer")
            if stripe_customer_id:
                try:
                    from app.core.database import get_db
                    from app.models.database.user_models import User
                    from sqlalchemy import select
                    
                    async with get_db() as db:
                        result = await db.execute(
                            select(User.user_id).where(User.stripe_customer_id == stripe_customer_id)
                        )
                        row = result.first()
                        if row and row[0]:
                            user_id = str(row[0])
                            logger.info(f"Found user_id {user_id} from stripe_customer_id {stripe_customer_id}")
                except Exception as e:
                    logger.warning(f"Failed to lookup user by stripe_customer_id: {e}")
        
        if not user_id:
            logger.error(f"No user_id for subscription {subscription['id']}, metadata: {metadata}")
            return {"error": "Missing user_id"}
        
        # Link Stripe customer to our user (backup in case checkout webhook missed it)
        stripe_customer_id = subscription.get("customer")
        if stripe_customer_id:
            await self._link_stripe_customer(user_id, stripe_customer_id)
        
        # Use subscription_service for consistency
        from app.services.subscription_service import subscription_service
        
        # Calculate duration from Stripe period
        period_end = subscription.get("current_period_end", 0)
        period_start = subscription.get("current_period_start", 0)
        duration_days = max(1, (period_end - period_start) // 86400)
        
        await subscription_service.activate_subscription(
            user_id=user_id,
            tier=tier,
            duration_days=duration_days,
            payment_provider="stripe",
            provider_transaction_id=subscription["id"],
        )
        
        logger.info(f"Created subscription for user {user_id}: tier={tier}")
        
        return {
            "handled": True,
            "type": "subscription_created",
            "user_id": user_id,
            "tier": tier,
            "subscription_id": subscription["id"],
        }
    
    async def _handle_subscription_updated(self, subscription: Dict) -> Dict[str, Any]:
        """Handle customer.subscription.updated event."""
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("firebase_uid") or metadata.get("user_id")
        
        if not user_id:
            return {"handled": False, "reason": "Missing firebase_uid"}
        
        from app.services.subscription_service import subscription_service
        
        # Check if auto-renew status changed
        cancel_at_period_end = subscription.get("cancel_at_period_end", False)
        auto_renew = not cancel_at_period_end
        
        await subscription_service.update_auto_renew(user_id, auto_renew)
        
        # Check subscription status
        status = subscription.get("status")
        if status == "past_due":
            # Payment failed, in grace period
            await subscription_service.mark_billing_issue(user_id)
        elif status == "unpaid":
            # Grace period ended, still unpaid
            await subscription_service.expire_subscription(user_id, reason="unpaid")
        
        logger.info(f"Updated subscription for user {user_id}: status={status}, auto_renew={auto_renew}")
        
        return {
            "handled": True,
            "type": "subscription_updated",
            "user_id": user_id,
            "status": status,
            "auto_renew": auto_renew,
        }
    
    async def _handle_subscription_deleted(self, subscription: Dict) -> Dict[str, Any]:
        """Handle customer.subscription.deleted event."""
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("firebase_uid") or metadata.get("user_id")
        
        if not user_id:
            return {"handled": False, "reason": "Missing firebase_uid"}
        
        from app.services.subscription_service import subscription_service
        
        # Determine reason
        cancellation_details = subscription.get("cancellation_details", {})
        reason = cancellation_details.get("reason", "cancelled")
        
        # Downgrade to free
        await subscription_service.expire_subscription(user_id, reason=reason)
        
        logger.info(f"Subscription deleted for user {user_id}, reason={reason}")
        
        return {
            "handled": True,
            "type": "subscription_deleted",
            "user_id": user_id,
            "reason": reason,
        }
    
    async def _handle_invoice_paid(self, invoice: Dict) -> Dict[str, Any]:
        """Handle invoice.paid event (subscription renewal)."""
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return {"handled": False, "reason": "Not a subscription invoice"}
        
        # Subscription renewal successful - subscription.updated will handle the rest
        logger.info(f"Invoice paid for subscription {subscription_id}")
        
        return {
            "handled": True,
            "type": "invoice_paid",
            "subscription_id": subscription_id,
        }
    
    async def _handle_invoice_payment_failed(self, invoice: Dict) -> Dict[str, Any]:
        """Handle invoice.payment_failed event."""
        subscription_id = invoice.get("subscription")
        customer_email = invoice.get("customer_email")
        
        logger.warning(f"Invoice payment failed for subscription {subscription_id}, email: {customer_email}")
        
        # Get user_id from subscription metadata
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            user_id = sub.metadata.get("user_id")
            
            if user_id:
                from app.services.subscription_service import subscription_service
                await subscription_service.mark_billing_issue(user_id)
                
                # TODO: Send push notification to user about failed payment
                logger.info(f"Marked billing issue for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to mark billing issue: {e}")
        
        return {
            "handled": True,
            "type": "invoice_payment_failed",
            "subscription_id": subscription_id,
            "customer_email": customer_email,
        }
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_publishable_key(self) -> Optional[str]:
        """Get Stripe publishable key for frontend."""
        return os.getenv("STRIPE_PUBLISHABLE_KEY")
    
    def is_enabled(self) -> bool:
        """Check if Stripe is enabled."""
        return self.enabled


# Singleton instance
stripe_service = StripeService()

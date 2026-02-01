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
STRIPE_SUBSCRIPTION_PLANS = {
    "premium_monthly": {
        "price_id": os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", "price_premium_monthly"),
        "tier": "premium",
        "billing_period": "monthly",
        "daily_credits": 100,
    },
    "premium_yearly": {
        "price_id": os.getenv("STRIPE_PRICE_PREMIUM_YEARLY", "price_premium_yearly"),
        "tier": "premium",
        "billing_period": "yearly",
        "daily_credits": 100,
    },
    "vip_monthly": {
        "price_id": os.getenv("STRIPE_PRICE_VIP_MONTHLY", "price_vip_monthly"),
        "tier": "vip",
        "billing_period": "monthly",
        "daily_credits": 300,
    },
    "vip_yearly": {
        "price_id": os.getenv("STRIPE_PRICE_VIP_YEARLY", "price_vip_yearly"),
        "tier": "vip",
        "billing_period": "yearly",
        "daily_credits": 300,
    },
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
                    "user_id": user_id,
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
                metadata={
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "type": "subscription",
                    "tier": plan["tier"],
                },
                # Subscription-specific settings
                subscription_data={
                    "metadata": {
                        "user_id": user_id,
                        "plan_id": plan_id,
                        "tier": plan["tier"],
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
        user_id = metadata.get("user_id")
        
        if not user_id:
            logger.error("No user_id in checkout metadata")
            return {"error": "Missing user_id"}
        
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
        
        elif purchase_type == "subscription":
            # Subscription checkout - actual subscription handling happens in subscription.created
            logger.info(f"Subscription checkout completed for user {user_id}")
            return {
                "handled": True,
                "type": "subscription_checkout",
                "user_id": user_id,
            }
        
        return {"handled": False, "reason": "Unknown purchase type"}
    
    async def _handle_subscription_created(self, subscription: Dict) -> Dict[str, Any]:
        """Handle customer.subscription.created event."""
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("user_id")
        tier = metadata.get("tier", "premium")
        
        if not user_id:
            logger.error("No user_id in subscription metadata")
            return {"error": "Missing user_id"}
        
        # Update user's subscription in database
        from app.services.payment_service import payment_service, SUBSCRIPTION_PLANS
        
        # Get plan details
        plan = SUBSCRIPTION_PLANS.get(tier, SUBSCRIPTION_PLANS["premium"])
        
        # Store subscription info
        from app.services.payment_service import _subscriptions
        _subscriptions[user_id] = {
            "user_id": user_id,
            "tier": tier,
            "started_at": datetime.utcnow(),
            "expires_at": datetime.fromtimestamp(subscription["current_period_end"]),
            "auto_renew": not subscription.get("cancel_at_period_end", False),
            "payment_provider": "stripe",
            "provider_subscription_id": subscription["id"],
            "is_active": True,
            "created_at": datetime.utcnow(),
        }
        
        # Update daily credits
        wallet = await payment_service.get_or_create_wallet(user_id)
        wallet["daily_free_credits"] = plan["daily_credits"]
        
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
        user_id = metadata.get("user_id")
        
        if not user_id:
            return {"handled": False, "reason": "Missing user_id"}
        
        from app.services.payment_service import _subscriptions
        
        if user_id in _subscriptions:
            _subscriptions[user_id].update({
                "expires_at": datetime.fromtimestamp(subscription["current_period_end"]),
                "auto_renew": not subscription.get("cancel_at_period_end", False),
                "is_active": subscription["status"] == "active",
                "updated_at": datetime.utcnow(),
            })
        
        logger.info(f"Updated subscription for user {user_id}")
        
        return {
            "handled": True,
            "type": "subscription_updated",
            "user_id": user_id,
        }
    
    async def _handle_subscription_deleted(self, subscription: Dict) -> Dict[str, Any]:
        """Handle customer.subscription.deleted event."""
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("user_id")
        
        if not user_id:
            return {"handled": False, "reason": "Missing user_id"}
        
        from app.services.payment_service import _subscriptions, SUBSCRIPTION_PLANS
        
        # Downgrade to free
        if user_id in _subscriptions:
            _subscriptions[user_id].update({
                "tier": "free",
                "auto_renew": False,
                "is_active": True,  # Free is always active
                "updated_at": datetime.utcnow(),
            })
        
        # Reset daily credits to free tier
        from app.services.payment_service import payment_service
        wallet = await payment_service.get_or_create_wallet(user_id)
        wallet["daily_free_credits"] = SUBSCRIPTION_PLANS["free"]["daily_credits"]
        
        logger.info(f"Subscription deleted for user {user_id}, downgraded to free")
        
        return {
            "handled": True,
            "type": "subscription_deleted",
            "user_id": user_id,
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
        
        # TODO: Send notification to user about failed payment
        # TODO: Implement grace period logic
        
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

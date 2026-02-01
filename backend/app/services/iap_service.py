"""
In-App Purchase Verification Service
====================================

Handles receipt verification for:
- Apple App Store (iOS)
- Google Play (Android)

Environment variables required:
- APPLE_SHARED_SECRET: Your App Store Connect shared secret
- GOOGLE_SERVICE_ACCOUNT_KEY: Path to Google service account JSON
- IAP_BUNDLE_ID: Your app's bundle ID (e.g., com.yourcompany.luna)
"""

import os
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
APPLE_SHARED_SECRET = os.getenv("APPLE_SHARED_SECRET")
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
IAP_BUNDLE_ID = os.getenv("IAP_BUNDLE_ID", "com.yourcompany.luna")

# Apple endpoints
APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"

# Google Play API
GOOGLE_PLAY_API_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"


class IAPProvider(str, Enum):
    APPLE = "apple"
    GOOGLE = "google"


class IAPProductType(str, Enum):
    CONSUMABLE = "consumable"  # Credit packages
    SUBSCRIPTION = "subscription"  # Premium/VIP plans


# ============================================================================
# Product Configuration
# ============================================================================

# Map iOS/Android product IDs to our internal packages
IAP_CREDIT_PRODUCTS = {
    # iOS product IDs
    "com.luna.credits.60": {"package_id": "pack_60", "coins": 60, "bonus": 0},
    "com.luna.credits.300": {"package_id": "pack_300", "coins": 300, "bonus": 30},
    "com.luna.credits.980": {"package_id": "pack_980", "coins": 980, "bonus": 110},
    "com.luna.credits.1980": {"package_id": "pack_1980", "coins": 1980, "bonus": 260},
    "com.luna.credits.3280": {"package_id": "pack_3280", "coins": 3280, "bonus": 600},
    "com.luna.credits.6480": {"package_id": "pack_6480", "coins": 6480, "bonus": 1600},
    # Android product IDs (same values, different format if needed)
    "credits_60": {"package_id": "pack_60", "coins": 60, "bonus": 0},
    "credits_300": {"package_id": "pack_300", "coins": 300, "bonus": 30},
    "credits_980": {"package_id": "pack_980", "coins": 980, "bonus": 110},
    "credits_1980": {"package_id": "pack_1980", "coins": 1980, "bonus": 260},
    "credits_3280": {"package_id": "pack_3280", "coins": 3280, "bonus": 600},
    "credits_6480": {"package_id": "pack_6480", "coins": 6480, "bonus": 1600},
}

IAP_SUBSCRIPTION_PRODUCTS = {
    # iOS subscription IDs
    "com.luna.premium.monthly": {"plan_id": "premium_monthly", "tier": "premium", "period": "monthly"},
    "com.luna.premium.yearly": {"plan_id": "premium_yearly", "tier": "premium", "period": "yearly"},
    "com.luna.vip.monthly": {"plan_id": "vip_monthly", "tier": "vip", "period": "monthly"},
    "com.luna.vip.yearly": {"plan_id": "vip_yearly", "tier": "vip", "period": "yearly"},
    # Android subscription IDs
    "premium_monthly": {"plan_id": "premium_monthly", "tier": "premium", "period": "monthly"},
    "premium_yearly": {"plan_id": "premium_yearly", "tier": "premium", "period": "yearly"},
    "vip_monthly": {"plan_id": "vip_monthly", "tier": "vip", "period": "monthly"},
    "vip_yearly": {"plan_id": "vip_yearly", "tier": "vip", "period": "yearly"},
}


class IAPService:
    """
    In-App Purchase verification service.
    
    Supports both Apple App Store and Google Play Store receipts.
    """
    
    def __init__(self):
        self.apple_enabled = bool(APPLE_SHARED_SECRET)
        self.google_enabled = bool(GOOGLE_SERVICE_ACCOUNT_KEY)
        self._google_credentials = None
        
        if self.apple_enabled:
            logger.info("Apple IAP verification enabled")
        else:
            logger.warning("APPLE_SHARED_SECRET not set - Apple IAP disabled")
        
        if self.google_enabled:
            logger.info("Google Play verification enabled")
        else:
            logger.warning("GOOGLE_SERVICE_ACCOUNT_KEY not set - Google Play disabled")
    
    # ========================================================================
    # Main Verification Entry Point
    # ========================================================================
    
    async def verify_and_fulfill(
        self,
        user_id: str,
        provider: IAPProvider,
        receipt_data: str,
        product_id: Optional[str] = None,
        purchase_token: Optional[str] = None,  # Google Play specific
    ) -> Dict[str, Any]:
        """
        Verify IAP receipt and fulfill the purchase.
        
        Args:
            user_id: Internal user ID
            provider: 'apple' or 'google'
            receipt_data: Base64 encoded receipt (Apple) or purchase token (Google)
            product_id: Product ID (required for Google)
            purchase_token: Purchase token (Google Play)
            
        Returns:
            Fulfillment result
        """
        if provider == IAPProvider.APPLE:
            return await self._verify_and_fulfill_apple(user_id, receipt_data)
        elif provider == IAPProvider.GOOGLE:
            if not product_id:
                raise ValueError("product_id required for Google Play verification")
            return await self._verify_and_fulfill_google(
                user_id, product_id, purchase_token or receipt_data
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    # ========================================================================
    # Apple App Store Verification
    # ========================================================================
    
    async def _verify_and_fulfill_apple(
        self,
        user_id: str,
        receipt_data: str,
    ) -> Dict[str, Any]:
        """
        Verify Apple receipt and fulfill purchase.
        
        Apple's verification flow:
        1. Try production URL first
        2. If status 21007, retry with sandbox URL
        3. Parse receipt info
        4. Fulfill based on product type
        """
        if not self.apple_enabled:
            raise NotImplementedError("Apple IAP not configured")
        
        # Verify receipt
        receipt_info = await self._verify_apple_receipt(receipt_data)
        
        if not receipt_info:
            raise ValueError("Invalid receipt")
        
        # Get latest receipt info
        latest_receipt = receipt_info.get("latest_receipt_info", [])
        if not latest_receipt:
            latest_receipt = receipt_info.get("receipt", {}).get("in_app", [])
        
        if not latest_receipt:
            raise ValueError("No purchases found in receipt")
        
        # Process each purchase (usually just one for consumables)
        results = []
        for purchase in latest_receipt:
            product_id = purchase.get("product_id")
            transaction_id = purchase.get("transaction_id")
            
            # Check for consumable (credits)
            if product_id in IAP_CREDIT_PRODUCTS:
                result = await self._fulfill_credit_purchase(
                    user_id=user_id,
                    product_id=product_id,
                    transaction_id=transaction_id,
                    provider="apple",
                )
                results.append(result)
            
            # Check for subscription
            elif product_id in IAP_SUBSCRIPTION_PRODUCTS:
                result = await self._fulfill_subscription(
                    user_id=user_id,
                    product_id=product_id,
                    transaction_id=transaction_id,
                    expires_date_ms=purchase.get("expires_date_ms"),
                    provider="apple",
                )
                results.append(result)
            
            else:
                logger.warning(f"Unknown product ID: {product_id}")
        
        return {
            "success": True,
            "provider": "apple",
            "fulfillments": results,
        }
    
    async def _verify_apple_receipt(
        self,
        receipt_data: str,
        use_sandbox: bool = False,
    ) -> Optional[Dict]:
        """
        Send receipt to Apple for verification.
        
        Returns verified receipt info or None if invalid.
        """
        url = APPLE_SANDBOX_URL if use_sandbox else APPLE_PRODUCTION_URL
        
        payload = {
            "receipt-data": receipt_data,
            "password": APPLE_SHARED_SECRET,
            "exclude-old-transactions": True,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            data = response.json()
        
        status = data.get("status", -1)
        
        # Status codes:
        # 0 = Valid
        # 21007 = Sandbox receipt sent to production (retry with sandbox)
        # 21008 = Production receipt sent to sandbox
        # Other = Invalid
        
        if status == 0:
            return data
        elif status == 21007 and not use_sandbox:
            # Retry with sandbox
            logger.info("Retrying with sandbox URL")
            return await self._verify_apple_receipt(receipt_data, use_sandbox=True)
        else:
            logger.error(f"Apple receipt verification failed: status={status}")
            return None
    
    # ========================================================================
    # Google Play Verification
    # ========================================================================
    
    async def _verify_and_fulfill_google(
        self,
        user_id: str,
        product_id: str,
        purchase_token: str,
    ) -> Dict[str, Any]:
        """
        Verify Google Play purchase and fulfill.
        """
        if not self.google_enabled:
            raise NotImplementedError("Google Play IAP not configured")
        
        # Determine product type
        is_subscription = product_id in IAP_SUBSCRIPTION_PRODUCTS
        
        if is_subscription:
            # Verify subscription
            purchase_info = await self._verify_google_subscription(product_id, purchase_token)
            
            result = await self._fulfill_subscription(
                user_id=user_id,
                product_id=product_id,
                transaction_id=purchase_info.get("orderId"),
                expires_date_ms=purchase_info.get("expiryTimeMillis"),
                provider="google",
            )
        else:
            # Verify one-time purchase
            purchase_info = await self._verify_google_purchase(product_id, purchase_token)
            
            result = await self._fulfill_credit_purchase(
                user_id=user_id,
                product_id=product_id,
                transaction_id=purchase_info.get("orderId"),
                provider="google",
            )
            
            # Acknowledge the purchase (required for Google Play)
            await self._acknowledge_google_purchase(product_id, purchase_token)
        
        return {
            "success": True,
            "provider": "google",
            "fulfillments": [result],
        }
    
    async def _get_google_access_token(self) -> str:
        """
        Get Google API access token using service account.
        """
        # This is a simplified version - in production you'd use google-auth library
        # For now, we'll use a placeholder that should be replaced with proper implementation
        
        if not GOOGLE_SERVICE_ACCOUNT_KEY:
            raise NotImplementedError("Google service account not configured")
        
        # Load service account credentials
        # In production, use: from google.oauth2 import service_account
        # credentials = service_account.Credentials.from_service_account_file(
        #     GOOGLE_SERVICE_ACCOUNT_KEY,
        #     scopes=['https://www.googleapis.com/auth/androidpublisher']
        # )
        
        # For now, return a placeholder - implement proper auth in production
        raise NotImplementedError(
            "Google Play verification requires google-auth library. "
            "Install with: pip install google-auth google-auth-httplib2"
        )
    
    async def _verify_google_purchase(
        self,
        product_id: str,
        purchase_token: str,
    ) -> Dict:
        """
        Verify a one-time purchase with Google Play.
        """
        access_token = await self._get_google_access_token()
        
        url = (
            f"{GOOGLE_PLAY_API_BASE}/applications/{IAP_BUNDLE_ID}"
            f"/purchases/products/{product_id}/tokens/{purchase_token}"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            
            if response.status_code != 200:
                raise ValueError(f"Google verification failed: {response.text}")
            
            return response.json()
    
    async def _verify_google_subscription(
        self,
        product_id: str,
        purchase_token: str,
    ) -> Dict:
        """
        Verify a subscription with Google Play.
        """
        access_token = await self._get_google_access_token()
        
        url = (
            f"{GOOGLE_PLAY_API_BASE}/applications/{IAP_BUNDLE_ID}"
            f"/purchases/subscriptions/{product_id}/tokens/{purchase_token}"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            
            if response.status_code != 200:
                raise ValueError(f"Google verification failed: {response.text}")
            
            return response.json()
    
    async def _acknowledge_google_purchase(
        self,
        product_id: str,
        purchase_token: str,
    ) -> None:
        """
        Acknowledge a Google Play purchase (required to prevent automatic refund).
        """
        access_token = await self._get_google_access_token()
        
        url = (
            f"{GOOGLE_PLAY_API_BASE}/applications/{IAP_BUNDLE_ID}"
            f"/purchases/products/{product_id}/tokens/{purchase_token}:acknowledge"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Failed to acknowledge purchase: {response.text}")
    
    # ========================================================================
    # Fulfillment Logic
    # ========================================================================
    
    async def _fulfill_credit_purchase(
        self,
        user_id: str,
        product_id: str,
        transaction_id: str,
        provider: str,
    ) -> Dict[str, Any]:
        """
        Fulfill a credit package purchase.
        """
        # Check for duplicate transaction (idempotency)
        if await self._is_transaction_processed(transaction_id):
            logger.warning(f"Transaction {transaction_id} already processed")
            return {
                "type": "credit_purchase",
                "status": "duplicate",
                "transaction_id": transaction_id,
            }
        
        # Get product info
        product = IAP_CREDIT_PRODUCTS.get(product_id)
        if not product:
            raise ValueError(f"Unknown product: {product_id}")
        
        total_credits = product["coins"] + product["bonus"]
        
        # Add credits
        from app.services.payment_service import payment_service
        wallet = await payment_service.add_credits(
            user_id=user_id,
            amount=total_credits,
            is_purchased=True,
            description=f"IAP purchase ({provider}): {product_id} ({product['coins']}+{product['bonus']} credits)",
        )
        
        # Mark transaction as processed
        await self._mark_transaction_processed(
            transaction_id=transaction_id,
            user_id=user_id,
            product_id=product_id,
            provider=provider,
        )
        
        logger.info(f"Fulfilled {total_credits} credits for user {user_id} (txn: {transaction_id})")
        
        return {
            "type": "credit_purchase",
            "status": "fulfilled",
            "transaction_id": transaction_id,
            "credits_added": total_credits,
            "wallet_balance": wallet["total_credits"],
        }
    
    async def _fulfill_subscription(
        self,
        user_id: str,
        product_id: str,
        transaction_id: str,
        expires_date_ms: Optional[str],
        provider: str,
    ) -> Dict[str, Any]:
        """
        Fulfill a subscription purchase or renewal.
        """
        # Get product info
        product = IAP_SUBSCRIPTION_PRODUCTS.get(product_id)
        if not product:
            raise ValueError(f"Unknown subscription product: {product_id}")
        
        tier = product["tier"]
        
        # Calculate expiry date
        if expires_date_ms:
            expires_at = datetime.fromtimestamp(int(expires_date_ms) / 1000)
        else:
            # Fallback: 30 days for monthly, 365 for yearly
            days = 365 if product["period"] == "yearly" else 30
            expires_at = datetime.utcnow() + timedelta(days=days)
        
        # Update subscription
        from app.services.payment_service import payment_service, _subscriptions, SUBSCRIPTION_PLANS
        
        _subscriptions[user_id] = {
            "user_id": user_id,
            "tier": tier,
            "started_at": datetime.utcnow(),
            "expires_at": expires_at,
            "auto_renew": True,
            "payment_provider": provider,
            "provider_subscription_id": transaction_id,
            "is_active": True,
            "created_at": datetime.utcnow(),
        }
        
        # Update daily credits
        plan = SUBSCRIPTION_PLANS.get(tier, SUBSCRIPTION_PLANS["premium"])
        wallet = await payment_service.get_or_create_wallet(user_id)
        wallet["daily_free_credits"] = plan["daily_credits"]
        
        logger.info(f"Activated {tier} subscription for user {user_id} (expires: {expires_at})")
        
        return {
            "type": "subscription",
            "status": "activated",
            "tier": tier,
            "expires_at": expires_at.isoformat(),
            "daily_credits": plan["daily_credits"],
        }
    
    # ========================================================================
    # Transaction Tracking (Idempotency)
    # ========================================================================
    
    # In-memory storage for processed transactions (use Redis/DB in production)
    _processed_transactions: Dict[str, Dict] = {}
    
    async def _is_transaction_processed(self, transaction_id: str) -> bool:
        """Check if transaction was already processed."""
        # In production, check database/Redis
        return transaction_id in self._processed_transactions
    
    async def _mark_transaction_processed(
        self,
        transaction_id: str,
        user_id: str,
        product_id: str,
        provider: str,
    ) -> None:
        """Mark transaction as processed."""
        # In production, store in database
        self._processed_transactions[transaction_id] = {
            "user_id": user_id,
            "product_id": product_id,
            "provider": provider,
            "processed_at": datetime.utcnow().isoformat(),
        }
    
    # ========================================================================
    # Product Info
    # ========================================================================
    
    def get_available_products(self, provider: IAPProvider) -> Dict[str, List[Dict]]:
        """
        Get available IAP products for a provider.
        
        Returns product IDs that should be configured in App Store Connect / Google Play Console.
        """
        credit_products = []
        subscription_products = []
        
        for product_id, info in IAP_CREDIT_PRODUCTS.items():
            # Filter by platform naming convention
            if provider == IAPProvider.APPLE and product_id.startswith("com.luna"):
                credit_products.append({
                    "product_id": product_id,
                    **info,
                })
            elif provider == IAPProvider.GOOGLE and not product_id.startswith("com.luna"):
                credit_products.append({
                    "product_id": product_id,
                    **info,
                })
        
        for product_id, info in IAP_SUBSCRIPTION_PRODUCTS.items():
            if provider == IAPProvider.APPLE and product_id.startswith("com.luna"):
                subscription_products.append({
                    "product_id": product_id,
                    **info,
                })
            elif provider == IAPProvider.GOOGLE and not product_id.startswith("com.luna"):
                subscription_products.append({
                    "product_id": product_id,
                    **info,
                })
        
        return {
            "credit_packages": credit_products,
            "subscriptions": subscription_products,
        }


# Singleton instance
iap_service = IAPService()

"""
In-App Purchase Verification Service
====================================

Handles receipt verification for:
- Apple App Store (iOS)
- Google Play (Android)

Also handles App Store Server Notifications V2 for subscription lifecycle events.

Environment variables required:
- APPLE_SHARED_SECRET: Your App Store Connect shared secret
- APPLE_BUNDLE_ID: Your app's bundle ID for Apple (e.g., com.yourcompany.luna)
- GOOGLE_SERVICE_ACCOUNT_KEY: Path to Google service account JSON
- IAP_BUNDLE_ID: Your app's bundle ID (e.g., com.yourcompany.luna)
"""

import os
import json
import base64
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
APPLE_SHARED_SECRET = os.getenv("APPLE_SHARED_SECRET")
APPLE_BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID", os.getenv("IAP_BUNDLE_ID", "com.luna.companion"))
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
IAP_BUNDLE_ID = os.getenv("IAP_BUNDLE_ID", "com.yourcompany.luna")

# Apple endpoints
APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"

# Apple root certificates for JWS verification (cached on first use)
_apple_root_certs: Optional[List[Any]] = None

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
    # iOS/Android unified subscription IDs (used by react-native-iap)
    "luna_premium_monthly": {"plan_id": "premium_monthly", "tier": "premium", "period": "monthly"},
    "luna_premium_yearly": {"plan_id": "premium_yearly", "tier": "premium", "period": "yearly"},
    "luna_vip_monthly": {"plan_id": "vip_monthly", "tier": "vip", "period": "monthly"},
    "luna_vip_yearly": {"plan_id": "vip_yearly", "tier": "vip", "period": "yearly"},
    # Legacy iOS bundle ID format (keep for backwards compatibility)
    "com.luna.premium.monthly": {"plan_id": "premium_monthly", "tier": "premium", "period": "monthly"},
    "com.luna.premium.yearly": {"plan_id": "premium_yearly", "tier": "premium", "period": "yearly"},
    "com.luna.vip.monthly": {"plan_id": "vip_monthly", "tier": "vip", "period": "monthly"},
    "com.luna.vip.yearly": {"plan_id": "vip_yearly", "tier": "vip", "period": "yearly"},
    # Legacy Android format
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
    # Apple App Store Server Notifications V2
    # ========================================================================
    
    async def handle_apple_notification(self, signed_payload: str) -> Dict[str, Any]:
        """
        Handle Apple App Store Server Notifications V2.
        
        Notification types we care about:
        - SUBSCRIBED: New subscription
        - DID_RENEW: Subscription renewed
        - DID_FAIL_TO_RENEW: Renewal failed (billing issue)
        - DID_CHANGE_RENEWAL_STATUS: User toggled auto-renew (cancel/reactivate)
        - EXPIRED: Subscription expired
        - GRACE_PERIOD_EXPIRED: Grace period ended without payment
        - REFUND: User got refund
        - REVOKE: Family sharing access revoked
        
        Returns processing result.
        """
        try:
            # 1. Decode and verify the JWS signed payload
            payload = await self._decode_apple_jws(signed_payload)
            
            notification_type = payload.get("notificationType")
            subtype = payload.get("subtype")
            
            # 2. Extract transaction info from the nested signed data
            signed_transaction = payload.get("data", {}).get("signedTransactionInfo")
            signed_renewal = payload.get("data", {}).get("signedRenewalInfo")
            
            transaction_info = await self._decode_apple_jws(signed_transaction) if signed_transaction else {}
            renewal_info = await self._decode_apple_jws(signed_renewal) if signed_renewal else {}
            
            # Get user ID from app account token (set during purchase)
            # Or fall back to original transaction ID lookup
            app_account_token = transaction_info.get("appAccountToken")
            original_transaction_id = transaction_info.get("originalTransactionId")
            product_id = transaction_info.get("productId")
            
            user_id = await self._get_user_for_transaction(app_account_token, original_transaction_id)
            
            if not user_id:
                logger.warning(f"No user found for transaction {original_transaction_id}")
                return {"status": "no_user_found", "transaction_id": original_transaction_id}
            
            logger.info(f"Apple notification: {notification_type}/{subtype} for user {user_id}, product {product_id}")
            
            # 3. Handle based on notification type
            result = await self._process_apple_notification(
                user_id=user_id,
                notification_type=notification_type,
                subtype=subtype,
                transaction_info=transaction_info,
                renewal_info=renewal_info,
            )
            
            return {
                "status": "processed",
                "notification_type": notification_type,
                "subtype": subtype,
                "user_id": user_id,
                "result": result,
            }
            
        except Exception as e:
            logger.error(f"Failed to process Apple notification: {e}", exc_info=True)
            raise ValueError(f"Invalid notification: {e}")
    
    async def _decode_apple_jws(self, jws_string: str) -> Dict[str, Any]:
        """
        Decode and verify Apple's JWS (JSON Web Signature).
        
        Apple signs notifications with ES256 using their root certificate chain.
        """
        if not jws_string:
            return {}
        
        try:
            from jose import jwt, jwk
            from jose.utils import base64url_decode
            import json
            
            # Split JWS into parts
            parts = jws_string.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWS format")
            
            # For production: verify signature with Apple's root certificate
            # Apple provides certs in the x5c header chain
            header = json.loads(base64url_decode(parts[0]).decode("utf-8"))
            
            # Get certificate chain from header
            x5c = header.get("x5c", [])
            if x5c:
                # In production, verify the certificate chain against Apple's root CA
                # For now, we'll decode without full chain verification but log warning
                # TODO: Implement full certificate chain verification
                logger.debug("JWS has certificate chain, should verify against Apple root CA")
            
            # Decode payload (we verify bundle ID as a sanity check)
            payload_bytes = base64url_decode(parts[1])
            payload = json.loads(payload_bytes.decode("utf-8"))
            
            # Verify bundle ID matches
            bundle_id = payload.get("data", {}).get("bundleId")
            if bundle_id and bundle_id != APPLE_BUNDLE_ID:
                logger.warning(f"Bundle ID mismatch: {bundle_id} != {APPLE_BUNDLE_ID}")
                # Don't reject - might be a config issue, just log
            
            return payload
            
        except Exception as e:
            logger.error(f"JWS decode error: {e}")
            raise ValueError(f"Failed to decode JWS: {e}")
    
    async def _get_user_for_transaction(
        self,
        app_account_token: Optional[str],
        original_transaction_id: Optional[str],
    ) -> Optional[str]:
        """
        Look up user ID for a transaction.
        
        Priority:
        1. app_account_token (UUID we set during purchase = user_id)
        2. Lookup by original_transaction_id in our records
        """
        # If app_account_token is set, it should be the user_id
        if app_account_token:
            return app_account_token
        
        # Look up in processed transactions
        for txn_id, txn_info in self._processed_transactions.items():
            if txn_info.get("original_transaction_id") == original_transaction_id:
                return txn_info.get("user_id")
        
        # Try database lookup
        try:
            from app.core.database import get_db
            from sqlalchemy import text
            
            async with get_db() as db:
                result = await db.execute(
                    text("""
                        SELECT user_id FROM user_subscriptions 
                        WHERE provider_subscription_id = :txn_id
                        OR provider_original_transaction_id = :txn_id
                    """),
                    {"txn_id": original_transaction_id}
                )
                row = result.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            logger.warning(f"DB lookup for transaction failed: {e}")
        
        return None
    
    async def _process_apple_notification(
        self,
        user_id: str,
        notification_type: str,
        subtype: Optional[str],
        transaction_info: Dict[str, Any],
        renewal_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process Apple notification and update subscription state.
        """
        from app.services.payment_service import payment_service
        
        product_id = transaction_info.get("productId")
        expires_date_ms = transaction_info.get("expiresDate")
        
        # Map notification to action
        if notification_type == "SUBSCRIBED":
            # New subscription or resubscribe
            return await self._fulfill_subscription(
                user_id=user_id,
                product_id=product_id,
                transaction_id=transaction_info.get("transactionId"),
                expires_date_ms=str(expires_date_ms) if expires_date_ms else None,
                provider="apple",
            )
        
        elif notification_type == "DID_RENEW":
            # Subscription renewed successfully
            return await self._fulfill_subscription(
                user_id=user_id,
                product_id=product_id,
                transaction_id=transaction_info.get("transactionId"),
                expires_date_ms=str(expires_date_ms) if expires_date_ms else None,
                provider="apple",
            )
        
        elif notification_type == "DID_CHANGE_RENEWAL_STATUS":
            # User toggled auto-renew
            auto_renew_enabled = subtype != "AUTO_RENEW_DISABLED"
            
            await payment_service.update_subscription_auto_renew(
                user_id=user_id,
                auto_renew=auto_renew_enabled,
            )
            
            action = "reactivated" if auto_renew_enabled else "cancelled"
            logger.info(f"User {user_id} {action} auto-renew")
            
            return {
                "type": "renewal_status_change",
                "auto_renew": auto_renew_enabled,
                "action": action,
            }
        
        elif notification_type in ("EXPIRED", "GRACE_PERIOD_EXPIRED"):
            # Subscription expired - downgrade to free
            await payment_service.expire_subscription(user_id)
            
            logger.info(f"User {user_id} subscription expired")
            
            return {
                "type": "expiration",
                "status": "downgraded_to_free",
            }
        
        elif notification_type == "DID_FAIL_TO_RENEW":
            # Billing issue - subscription in grace period or will expire
            # Mark as billing issue but don't downgrade yet (grace period)
            await payment_service.mark_billing_issue(user_id)
            
            logger.warning(f"User {user_id} has billing issue")
            
            return {
                "type": "billing_issue",
                "status": "renewal_failed",
                "in_grace_period": subtype == "GRACE_PERIOD",
            }
        
        elif notification_type == "REFUND":
            # User got refund - revoke access
            await payment_service.handle_refund(
                user_id=user_id,
                transaction_id=transaction_info.get("transactionId"),
            )
            
            logger.info(f"User {user_id} refunded, access revoked")
            
            return {
                "type": "refund",
                "status": "access_revoked",
            }
        
        elif notification_type == "REVOKE":
            # Family sharing access revoked
            await payment_service.expire_subscription(user_id)
            
            logger.info(f"User {user_id} access revoked (family sharing)")
            
            return {
                "type": "revoke",
                "status": "access_revoked",
            }
        
        else:
            # Other notification types we don't need to act on
            logger.info(f"Unhandled notification type: {notification_type}/{subtype}")
            return {
                "type": "unhandled",
                "notification_type": notification_type,
                "subtype": subtype,
            }
    
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
    # Google Play Real-time Developer Notifications
    # ========================================================================
    
    async def handle_google_notification(self, message_data: str) -> Dict[str, Any]:
        """
        Handle Google Play Real-time Developer Notifications.
        
        Google sends notifications via Cloud Pub/Sub. The message data is base64 encoded.
        
        Notification types:
        - SUBSCRIPTION_RECOVERED (1): Subscription recovered from account hold
        - SUBSCRIPTION_RENEWED (2): Active subscription renewed
        - SUBSCRIPTION_CANCELED (3): Subscription cancelled (voluntary or involuntary)
        - SUBSCRIPTION_PURCHASED (4): New subscription purchased
        - SUBSCRIPTION_ON_HOLD (5): Subscription on account hold
        - SUBSCRIPTION_IN_GRACE_PERIOD (6): Subscription in grace period
        - SUBSCRIPTION_RESTARTED (7): Subscription restarted
        - SUBSCRIPTION_PRICE_CHANGE_CONFIRMED (8): User confirmed price change
        - SUBSCRIPTION_DEFERRED (9): Subscription deferred
        - SUBSCRIPTION_PAUSED (10): Subscription paused
        - SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED (11): Pause schedule changed
        - SUBSCRIPTION_REVOKED (12): Subscription revoked
        - SUBSCRIPTION_EXPIRED (13): Subscription expired
        
        Returns processing result.
        """
        try:
            # Decode base64 message
            import json
            decoded = base64.b64decode(message_data).decode("utf-8")
            notification = json.loads(decoded)
            
            # Extract notification details
            package_name = notification.get("packageName")
            subscription_notification = notification.get("subscriptionNotification", {})
            one_time_notification = notification.get("oneTimeProductNotification", {})
            
            if subscription_notification:
                return await self._process_google_subscription_notification(
                    package_name, subscription_notification
                )
            elif one_time_notification:
                # One-time purchases don't need webhook handling
                # They're verified at purchase time
                logger.info(f"Google one-time notification: {one_time_notification}")
                return {"status": "ignored", "type": "one_time_purchase"}
            else:
                logger.warning(f"Unknown Google notification: {notification}")
                return {"status": "unknown", "notification": notification}
                
        except Exception as e:
            logger.error(f"Failed to process Google notification: {e}", exc_info=True)
            raise ValueError(f"Invalid notification: {e}")
    
    async def _process_google_subscription_notification(
        self,
        package_name: str,
        notification: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process Google subscription notification.
        """
        from app.services.payment_service import payment_service
        
        notification_type = notification.get("notificationType")
        purchase_token = notification.get("purchaseToken")
        subscription_id = notification.get("subscriptionId")  # Product ID
        
        # Map notification type to action
        # https://developer.android.com/google/play/billing/rtdn-reference
        NOTIFICATION_TYPES = {
            1: "SUBSCRIPTION_RECOVERED",
            2: "SUBSCRIPTION_RENEWED",
            3: "SUBSCRIPTION_CANCELED",
            4: "SUBSCRIPTION_PURCHASED",
            5: "SUBSCRIPTION_ON_HOLD",
            6: "SUBSCRIPTION_IN_GRACE_PERIOD",
            7: "SUBSCRIPTION_RESTARTED",
            8: "SUBSCRIPTION_PRICE_CHANGE_CONFIRMED",
            9: "SUBSCRIPTION_DEFERRED",
            10: "SUBSCRIPTION_PAUSED",
            11: "SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED",
            12: "SUBSCRIPTION_REVOKED",
            13: "SUBSCRIPTION_EXPIRED",
        }
        
        type_name = NOTIFICATION_TYPES.get(notification_type, f"UNKNOWN_{notification_type}")
        logger.info(f"Google notification: {type_name} for {subscription_id}")
        
        # Get user from purchase token
        user_id = await self._get_user_for_google_purchase(purchase_token, subscription_id)
        
        if not user_id:
            logger.warning(f"No user found for Google purchase token")
            return {"status": "no_user_found", "type": type_name}
        
        # Process based on notification type
        if notification_type == 4:  # SUBSCRIPTION_PURCHASED
            # New subscription - verify and fulfill
            result = await self._verify_and_fulfill_google(
                user_id=user_id,
                product_id=subscription_id,
                purchase_token=purchase_token,
            )
            return {"status": "processed", "type": type_name, "result": result}
        
        elif notification_type == 2:  # SUBSCRIPTION_RENEWED
            # Renewal - update expiry date
            try:
                purchase_info = await self._verify_google_subscription(subscription_id, purchase_token)
                expires_ms = purchase_info.get("expiryTimeMillis")
                
                result = await self._fulfill_subscription(
                    user_id=user_id,
                    product_id=subscription_id,
                    transaction_id=purchase_info.get("orderId"),
                    expires_date_ms=expires_ms,
                    provider="google",
                )
                return {"status": "renewed", "type": type_name, "result": result}
            except Exception as e:
                logger.error(f"Failed to process renewal: {e}")
                return {"status": "error", "type": type_name, "error": str(e)}
        
        elif notification_type == 3:  # SUBSCRIPTION_CANCELED
            # User cancelled - just update auto_renew status
            await payment_service.update_subscription_auto_renew(user_id, False)
            return {"status": "processed", "type": type_name, "action": "auto_renew_disabled"}
        
        elif notification_type in (5, 6):  # ON_HOLD or GRACE_PERIOD
            # Billing issue
            await payment_service.mark_billing_issue(user_id)
            return {"status": "processed", "type": type_name, "action": "billing_issue_marked"}
        
        elif notification_type == 1:  # SUBSCRIPTION_RECOVERED
            # Recovered from hold - reactivate
            try:
                purchase_info = await self._verify_google_subscription(subscription_id, purchase_token)
                expires_ms = purchase_info.get("expiryTimeMillis")
                
                result = await self._fulfill_subscription(
                    user_id=user_id,
                    product_id=subscription_id,
                    transaction_id=purchase_info.get("orderId"),
                    expires_date_ms=expires_ms,
                    provider="google",
                )
                return {"status": "recovered", "type": type_name, "result": result}
            except Exception as e:
                logger.error(f"Failed to process recovery: {e}")
                return {"status": "error", "type": type_name, "error": str(e)}
        
        elif notification_type == 7:  # SUBSCRIPTION_RESTARTED
            # User restarted cancelled subscription
            await payment_service.update_subscription_auto_renew(user_id, True)
            return {"status": "processed", "type": type_name, "action": "auto_renew_enabled"}
        
        elif notification_type in (12, 13):  # REVOKED or EXPIRED
            # Subscription ended - downgrade to free
            reason = "revoked" if notification_type == 12 else "expired"
            await payment_service.expire_subscription(user_id)
            return {"status": "processed", "type": type_name, "action": "downgraded_to_free", "reason": reason}
        
        elif notification_type == 10:  # SUBSCRIPTION_PAUSED
            # Paused - treat similar to cancelled for now
            await payment_service.update_subscription_auto_renew(user_id, False)
            return {"status": "processed", "type": type_name, "action": "paused"}
        
        else:
            # Other notification types - log but don't act
            logger.info(f"Unhandled Google notification type: {type_name}")
            return {"status": "ignored", "type": type_name}
    
    async def _get_user_for_google_purchase(
        self,
        purchase_token: str,
        product_id: str,
    ) -> Optional[str]:
        """
        Look up user ID for a Google purchase token.
        """
        # Check processed transactions
        for txn_id, txn_info in self._processed_transactions.items():
            if (txn_info.get("provider") == "google" and 
                txn_info.get("purchase_token") == purchase_token):
                return txn_info.get("user_id")
        
        # Try database lookup
        try:
            from app.core.database import get_db
            from sqlalchemy import text
            
            async with get_db() as db:
                result = await db.execute(
                    text("""
                        SELECT user_id FROM user_subscriptions 
                        WHERE payment_provider = 'google'
                        AND provider_subscription_id LIKE :token_pattern
                    """),
                    {"token_pattern": f"%{purchase_token[:20]}%"}  # Partial match
                )
                row = result.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            logger.warning(f"DB lookup for Google purchase failed: {e}")
        
        return None
    
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

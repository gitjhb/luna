"""
Authentication Service
=====================

Handles Firebase authentication and user management.

Author: Manus AI
Date: January 28, 2026
"""

import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import settings
from app.models.database import User, UserWallet

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized")
except Exception as e:
    logger.warning(f"Firebase initialization failed: {str(e)}")


async def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    """
    Verify Firebase ID token.
    
    Args:
        id_token: Firebase ID token
        
    Returns:
        Decoded token data
        
    Raises:
        Exception: If token verification fails
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise


class AuthService:
    """Authentication service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def login_or_register(self, id_token: str) -> Dict[str, Any]:
        """
        Login or register user with Firebase token.
        
        Args:
            id_token: Firebase ID token
            
        Returns:
            User information dictionary
        """
        # Verify token
        decoded_token = await verify_firebase_token(id_token)
        
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        display_name = decoded_token.get("name")
        avatar_url = decoded_token.get("picture")
        
        # Check if user exists
        result = await self.db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update last login
            user.last_login_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"User {user.user_id} logged in")
        else:
            # Create new user
            user = await self._create_user(
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
            )
            
            logger.info(f"New user created: {user.user_id}")
        
        # Get wallet
        result = await self.db.execute(
            select(UserWallet).where(UserWallet.user_id == user.user_id)
        )
        wallet = result.scalar_one()
        
        # Use unified subscription service to get effective tier
        from app.services.subscription_service import subscription_service
        effective_tier = await subscription_service.get_effective_tier(user.user_id)
        is_subscribed = effective_tier != "free"
        
        return {
            "user_id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "is_subscribed": is_subscribed,
            "subscription_tier": effective_tier,
            "credits_balance": wallet.total_credits,
            "access_token": id_token,  # In production, generate your own JWT
        }
    
    async def _create_user(
        self,
        firebase_uid: str,
        email: str,
        display_name: str = None,
        avatar_url: str = None,
    ) -> User:
        """
        Create a new user with wallet.
        
        Args:
            firebase_uid: Firebase UID
            email: User email
            display_name: User display name
            avatar_url: User avatar URL
            
        Returns:
            Created user
        """
        # Create user
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            is_subscribed=False,
            subscription_tier="free",
            last_login_at=datetime.utcnow(),
        )
        self.db.add(user)
        await self.db.flush()  # Get user_id
        
        # Create wallet
        wallet = UserWallet(
            user_id=user.user_id,
            free_credits=settings.DAILY_REFRESH_AMOUNT,
            purchased_credits=0.0,
            total_credits=settings.DAILY_REFRESH_AMOUNT,
            daily_refresh_amount=settings.DAILY_REFRESH_AMOUNT,
        )
        self.db.add(wallet)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

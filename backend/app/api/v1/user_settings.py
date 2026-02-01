"""
User Settings API Routes
========================

Manage user preferences including NSFW mode.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings")


class UserSettingsResponse(BaseModel):
    user_id: str
    nsfw_enabled: bool
    language: str
    notifications_enabled: bool


class UpdateSettingsRequest(BaseModel):
    nsfw_enabled: Optional[bool] = None
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None


@router.get("", response_model=UserSettingsResponse)
async def get_settings(request: Request):
    """Get current user settings."""
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    from app.core.database import get_db
    from sqlalchemy import select
    from app.models.database.user_settings_models import UserSettings
    
    try:
        async with get_db() as db:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            
            if settings:
                return UserSettingsResponse(
                    user_id=user_id,
                    nsfw_enabled=settings.nsfw_enabled,
                    language=settings.language or "zh",
                    notifications_enabled=settings.notifications_enabled,
                )
            else:
                # Return defaults
                return UserSettingsResponse(
                    user_id=user_id,
                    nsfw_enabled=False,
                    language="zh",
                    notifications_enabled=True,
                )
    except Exception as e:
        logger.warning(f"Failed to get settings: {e}")
        return UserSettingsResponse(
            user_id=user_id,
            nsfw_enabled=False,
            language="zh",
            notifications_enabled=True,
        )


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(request: Request, body: UpdateSettingsRequest):
    """
    Update user settings.
    
    NSFW mode requires active subscription (premium/vip).
    """
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # Check subscription for NSFW - use unified subscription service
    if body.nsfw_enabled:
        from app.services.subscription_service import subscription_service
        
        # Allow guest/demo users for testing
        if user_id.startswith("guest-") or user_id.startswith("demo-"):
            pass  # Allow for testing
        else:
            can_nsfw = await subscription_service.has_feature(user_id, "nsfw_enabled")
            if not can_nsfw:
                raise HTTPException(
                    status_code=403,
                    detail="成人内容需要订阅 Premium 或 VIP 会员才能开启"
                )
    
    from app.core.database import get_db
    from sqlalchemy import select
    from app.models.database.user_settings_models import UserSettings
    
    try:
        async with get_db() as db:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            
            if not settings:
                # Create new settings
                settings = UserSettings(user_id=user_id)
                db.add(settings)
            
            # Update fields
            if body.nsfw_enabled is not None:
                settings.nsfw_enabled = body.nsfw_enabled
                logger.info(f"User {user_id} set NSFW mode to {body.nsfw_enabled}")
            if body.language is not None:
                settings.language = body.language
            if body.notifications_enabled is not None:
                settings.notifications_enabled = body.notifications_enabled
            
            await db.commit()
            await db.refresh(settings)
            
            return UserSettingsResponse(
                user_id=user_id,
                nsfw_enabled=settings.nsfw_enabled,
                language=settings.language or "zh",
                notifications_enabled=settings.notifications_enabled,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

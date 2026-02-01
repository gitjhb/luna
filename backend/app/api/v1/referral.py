"""
Referral API Routes
===================

Endpoints for referral code management and friend invitations.

Author: Clawdbot
Date: January 31, 2025
"""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.services.referral_service import referral_service, REFERRAL_REWARD_AMOUNT, REFERRAL_NEW_USER_BONUS

router = APIRouter(prefix="/referral")


# ============================================================================
# Request/Response Models
# ============================================================================

class ReferralCodeResponse(BaseModel):
    """Response for getting referral code"""
    referral_code: str
    total_referrals: int
    total_rewards_earned: float
    reward_per_referral: int = REFERRAL_REWARD_AMOUNT
    new_user_bonus: int = REFERRAL_NEW_USER_BONUS
    share_text: str = ""  # Pre-formatted share text


class ApplyReferralRequest(BaseModel):
    """Request to apply a referral code"""
    referral_code: str = Field(..., min_length=6, max_length=16)


class ApplyReferralResponse(BaseModel):
    """Response after applying referral code"""
    success: bool
    message: str
    error: Optional[str] = None
    new_user_bonus: Optional[int] = None
    new_balance: Optional[float] = None


class ReferredFriend(BaseModel):
    """A referred friend"""
    user_id: str
    display_name: str
    avatar_url: Optional[str] = None
    referred_at: Optional[str] = None
    reward_earned: float


class ReferredFriendsResponse(BaseModel):
    """Response for listing referred friends"""
    friends: List[ReferredFriend]
    total_count: int
    total_rewards: float


class ReferralStatsResponse(BaseModel):
    """Response for referral statistics"""
    referral_code: str
    total_referrals: int
    total_rewards_earned: float
    reward_per_referral: int
    new_user_bonus: int


# ============================================================================
# Helper
# ============================================================================

def get_user_id(req: Request) -> str:
    """Extract user_id from request state"""
    user = getattr(req.state, "user", None)
    if user:
        return str(user.user_id)
    # Fallback for demo/dev mode
    return "demo-user-123"


# ============================================================================
# Routes
# ============================================================================

@router.get("/code", response_model=ReferralCodeResponse)
async def get_my_referral_code(req: Request):
    """
    Get current user's referral code.
    
    Creates a new code if user doesn't have one yet.
    Returns the code along with referral statistics.
    """
    user_id = get_user_id(req)
    
    result = await referral_service.get_or_create_referral_code(user_id)
    
    # Generate share text
    share_text = (
        f"我正在使用 Luna AI 陪伴，超有趣！\n"
        f"使用我的邀请码 {result['referral_code']} 注册，你我都能获得金币奖励！\n"
        f"下载链接: https://luna.app/download"
    )
    
    return ReferralCodeResponse(
        referral_code=result["referral_code"],
        total_referrals=result["total_referrals"],
        total_rewards_earned=result["total_rewards_earned"],
        share_text=share_text,
    )


@router.post("/apply", response_model=ApplyReferralResponse)
async def apply_referral_code(request: ApplyReferralRequest, req: Request):
    """
    Apply a referral code for the current user.
    
    This awards coins to both the referrer and the new user.
    Can only be used once per user.
    """
    user_id = get_user_id(req)
    
    result = await referral_service.apply_referral_code(
        new_user_id=user_id,
        referral_code=request.referral_code
    )
    
    if not result["success"]:
        # Return 200 with success=False for validation errors
        # This allows frontend to show user-friendly messages
        return ApplyReferralResponse(
            success=False,
            message=result["message"],
            error=result.get("error"),
        )
    
    return ApplyReferralResponse(
        success=True,
        message=result["message"],
        new_user_bonus=result.get("new_user_bonus", REFERRAL_NEW_USER_BONUS),
        new_balance=result.get("new_balance"),
    )


@router.get("/friends", response_model=ReferredFriendsResponse)
async def get_referred_friends(
    limit: int = 50,
    offset: int = 0,
    req: Request = None,
):
    """
    Get list of friends referred by current user.
    
    Returns friend info along with reward earned for each.
    """
    user_id = get_user_id(req)
    
    result = await referral_service.get_referred_friends(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    
    friends = [
        ReferredFriend(
            user_id=f["user_id"],
            display_name=f["display_name"],
            avatar_url=f.get("avatar_url"),
            referred_at=f.get("referred_at"),
            reward_earned=f.get("reward_earned", REFERRAL_REWARD_AMOUNT),
        )
        for f in result["friends"]
    ]
    
    return ReferredFriendsResponse(
        friends=friends,
        total_count=result["total_count"],
        total_rewards=result["total_rewards"],
    )


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(req: Request):
    """
    Get referral statistics for current user.
    
    Returns referral code, counts, and reward info.
    """
    user_id = get_user_id(req)
    
    result = await referral_service.get_referral_stats(user_id)
    
    return ReferralStatsResponse(
        referral_code=result["referral_code"],
        total_referrals=result["total_referrals"],
        total_rewards_earned=result["total_rewards_earned"],
        reward_per_referral=result["reward_per_referral"],
        new_user_bonus=result["new_user_bonus"],
    )

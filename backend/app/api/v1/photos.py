"""
Photo API - 场景照片系统 API
============================

功能：
- POST /photos/{character_id}/request - 请求场景照片
- GET /photos/{character_id}/unlocked - 获取已解锁照片
- GET /photos/{character_id}/quota - 查询今日额度

场景类型：
- work: 工作/职业照片（禁止卧室场景）
- gym: 健身房照片
- intimate: 私密/居家照片

Author: Luna AI
Date: February 2026
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Optional
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.photo_unlock_service import photo_unlock_service
from app.services.scene_photo_service import (
    get_scene_photo_service,
    PhotoScene,
    PHOTO_COST,
    DAILY_LIMITS,
)

router = APIRouter(prefix="/photos", tags=["photos"])


# ============================================================================
# Schemas
# ============================================================================

class UnlockedPhoto(BaseModel):
    id: str
    scene: str
    photo_type: str
    source: str
    unlocked_at: str


class UnlockedPhotosResponse(BaseModel):
    success: bool
    photos: List[UnlockedPhoto]


class PhotoRequestPayload(BaseModel):
    """请求照片的payload"""
    messages: List[dict] = Field(
        default=[],
        description="最近的对话消息，用于场景识别"
    )
    scene: Optional[str] = Field(
        default=None,
        description="强制指定场景 (work/gym/intimate)"
    )


class PhotoRequestResponse(BaseModel):
    """照片请求响应"""
    success: bool
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    scene: Optional[str] = None
    cost_credits: int = 0
    remaining_daily: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = None


class QuotaResponse(BaseModel):
    """额度查询响应"""
    daily_limit: int
    daily_used: int
    daily_remaining: int
    credits_required: int
    credits_balance: float
    can_request: bool
    tier: str


# ============================================================================
# Helper Functions
# ============================================================================

def _get_user_id(request: Request) -> str:
    """从请求中获取用户ID"""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "user_id"):
        return str(user.user_id)
    # Fallback
    return request.headers.get("X-User-ID", "demo-user-123")


def _get_user_tier(request: Request) -> str:
    """从请求中获取用户等级"""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "subscription_tier"):
        return str(user.subscription_tier).lower()
    # Fallback
    return "free"


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/{character_id}/request", response_model=PhotoRequestResponse)
async def request_scene_photo(
    character_id: str,
    payload: PhotoRequestPayload,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    请求场景照片
    
    流程：
    1. 检查今日额度
    2. 检查credits余额
    3. 根据对话自动识别场景（或使用指定场景）
    4. 生成照片
    5. 扣费
    
    场景类型：
    - work: 工作/职业（禁止卧室）
    - gym: 健身房
    - intimate: 私密/居家
    
    成本：10 credits/张
    日上限：free=3张, premium=10张, vip=20张
    """
    user_id = _get_user_id(request)
    tier = _get_user_tier(request)
    
    service = get_scene_photo_service()
    
    # 处理场景override
    scene_override = None
    if payload.scene:
        try:
            scene_override = PhotoScene(payload.scene.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scene: {payload.scene}. Must be one of: work, gym, intimate"
            )
    
    # 调用服务
    result = await service.generate_scene_photo(
        user_id=user_id,
        character_id=character_id,
        messages=payload.messages,
        tier=tier,
        db=db,
        scene_override=scene_override,
    )
    
    if not result.success:
        # 返回错误但不抛异常，让前端处理
        return PhotoRequestResponse(
            success=False,
            remaining_daily=result.remaining_daily,
            error=result.error,
            error_code=result.error_code,
        )
    
    return PhotoRequestResponse(
        success=True,
        image_id=result.image_id,
        image_url=result.image_url,
        scene=result.scene,
        cost_credits=result.cost_credits,
        remaining_daily=result.remaining_daily,
    )


@router.get("/{character_id}/quota", response_model=QuotaResponse)
async def get_photo_quota(
    character_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    查询今日照片额度
    
    返回：
    - daily_limit: 每日上限
    - daily_used: 今日已用
    - daily_remaining: 今日剩余
    - credits_required: 单张成本
    - credits_balance: 当前余额
    - can_request: 是否可以请求
    """
    user_id = _get_user_id(request)
    tier = _get_user_tier(request)
    
    service = get_scene_photo_service()
    
    # 检查日上限
    can_by_daily, remaining = await service.check_daily_limit(user_id, tier, db)
    daily_limit = DAILY_LIMITS.get(tier, DAILY_LIMITS["free"])
    daily_used = daily_limit - remaining
    
    # 检查credits
    has_credits, balance = await service.check_credits(user_id, db)
    
    return QuotaResponse(
        daily_limit=daily_limit,
        daily_used=daily_used,
        daily_remaining=remaining,
        credits_required=PHOTO_COST,
        credits_balance=balance,
        can_request=can_by_daily and has_credits,
        tier=tier,
    )


@router.get("/{character_id}/unlocked", response_model=UnlockedPhotosResponse)
async def get_unlocked_photos(character_id: str, request: Request):
    """获取用户解锁的所有照片"""
    user_id = _get_user_id(request)
    
    photos = await photo_unlock_service.get_unlocked_photos(user_id, character_id)
    
    return UnlockedPhotosResponse(
        success=True,
        photos=[UnlockedPhoto(**p) for p in photos],
    )


@router.get("/{character_id}/check/{scene}/{photo_type}")
async def check_photo_unlocked(
    character_id: str, 
    scene: str, 
    photo_type: str, 
    request: Request
):
    """检查指定照片是否已解锁"""
    user_id = _get_user_id(request)
    
    is_unlocked = await photo_unlock_service.is_photo_unlocked(
        user_id, character_id, scene, photo_type
    )
    
    return {"unlocked": is_unlocked}

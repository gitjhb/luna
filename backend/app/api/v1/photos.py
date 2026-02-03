"""
Photo API - 照片解锁系统 API
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel

from app.services.photo_unlock_service import photo_unlock_service

router = APIRouter(prefix="/photos", tags=["photos"])


class UnlockedPhoto(BaseModel):
    id: str
    scene: str
    photo_type: str
    source: str
    unlocked_at: str


class UnlockedPhotosResponse(BaseModel):
    success: bool
    photos: List[UnlockedPhoto]


def _get_user_id(request: Request) -> str:
    """从请求中获取用户ID"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        user_id = request.headers.get("X-User-ID", "demo-user")
    return user_id


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

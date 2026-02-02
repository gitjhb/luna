"""
Interactions API - 拍照、换装等消费功能
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging
import random

router = APIRouter(prefix="/interactions")
logger = logging.getLogger(__name__)

# 功能配置
INTERACTION_CONFIG = {
    "photo": {
        "name": "拍照",
        "cost": 20,
        "unlock_level": 3,
        "event_name": "first_photo",
    },
    "dressup": {
        "name": "换装",
        "cost": 50,
        "unlock_level": 6,
        "event_name": "first_dressup",
    },
}

# Mock 角色图片 (后续替换为 Grok 生成)
MOCK_PHOTOS = {
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": [  # Luna
        "https://placeholder.com/luna_photo_1.jpg",
        "https://placeholder.com/luna_photo_2.jpg",
    ],
    "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c": [  # 小美
        "https://placeholder.com/xiaomei_photo_1.jpg",
        "https://placeholder.com/xiaomei_photo_2.jpg",
    ],
}

# 换装素材
DRESSUP_OPTIONS = {
    "tops": [
        {"id": "top_casual", "name": "休闲T恤", "icon": "👕"},
        {"id": "top_elegant", "name": "优雅衬衫", "icon": "👔"},
        {"id": "top_sexy", "name": "性感吊带", "icon": "👙"},
        {"id": "top_maid", "name": "女仆装上衣", "icon": "🎀"},
    ],
    "bottoms": [
        {"id": "bottom_jeans", "name": "牛仔裤", "icon": "👖"},
        {"id": "bottom_skirt", "name": "短裙", "icon": "🩱"},
        {"id": "bottom_dress", "name": "连衣裙", "icon": "👗"},
        {"id": "bottom_maid", "name": "女仆裙", "icon": "🖤"},
    ],
}

# 内存存储用户相册 (后续改用数据库)
_USER_ALBUMS: dict = {}


class PhotoRequest(BaseModel):
    character_id: str
    context: Optional[str] = None  # 当前对话上下文，用于生成场景


class DressupRequest(BaseModel):
    character_id: str
    top_id: str
    bottom_id: str


class PhotoResponse(BaseModel):
    success: bool
    image_url: str
    cost: int
    is_first: bool
    message: str
    album_id: str


class DressupOptionsResponse(BaseModel):
    tops: List[dict]
    bottoms: List[dict]
    cost: int
    unlock_level: int


@router.get("/config")
async def get_interaction_config(request: Request):
    """获取互动功能配置"""
    return INTERACTION_CONFIG


@router.get("/dressup/options")
async def get_dressup_options(request: Request):
    """获取换装选项"""
    return DressupOptionsResponse(
        tops=DRESSUP_OPTIONS["tops"],
        bottoms=DRESSUP_OPTIONS["bottoms"],
        cost=INTERACTION_CONFIG["dressup"]["cost"],
        unlock_level=INTERACTION_CONFIG["dressup"]["unlock_level"],
    )


@router.post("/photo", response_model=PhotoResponse)
async def take_photo(body: PhotoRequest, request: Request):
    """
    拍照功能
    - 扣除月石
    - 生成图片 (目前 mock)
    - 保存到相册
    - 记录首次事件
    """
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    config = INTERACTION_CONFIG["photo"]
    
    # 1. 检查等级
    from app.services.intimacy_service import intimacy_service
    intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, body.character_id)
    current_level = intimacy_data.get("current_level", 1)
    
    if current_level < config["unlock_level"]:
        raise HTTPException(
            status_code=403,
            detail=f"需要 Lv.{config['unlock_level']} 解锁此功能，当前 Lv.{current_level}"
        )
    
    # 2. 扣除月石
    from app.services.wallet_service import wallet_service
    
    balance = await wallet_service.get_balance(user_id)
    if balance < config["cost"]:
        raise HTTPException(
            status_code=402,
            detail=f"月石不足，需要 {config['cost']}，当前 {balance}"
        )
    
    await wallet_service.deduct(user_id, config["cost"], f"photo:{body.character_id}")
    
    # 3. 检查是否首次
    events = intimacy_data.get("events", [])
    is_first = config["event_name"] not in events
    
    # 4. 记录首次事件
    if is_first:
        try:
            from app.core.database import get_db
            from sqlalchemy import text
            import json
            
            events.append(config["event_name"])
            async with get_db() as session:
                await session.execute(
                    text("""
                        UPDATE user_intimacy 
                        SET events = :events, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND character_id = :char_id
                    """),
                    {"events": json.dumps(events), "user_id": user_id, "char_id": body.character_id}
                )
                await session.commit()
            logger.info(f"First photo event recorded for {user_id}:{body.character_id}")
        except Exception as e:
            logger.warning(f"Failed to record first photo event: {e}")
    
    # 5. 生成图片 (目前 mock，后续接 Grok)
    mock_photos = MOCK_PHOTOS.get(body.character_id, ["https://placeholder.com/default.jpg"])
    image_url = random.choice(mock_photos)
    
    # TODO: 调用 Grok image API
    # image_url = await generate_photo_with_grok(body.character_id, body.context)
    
    # 6. 保存到相册
    album_key = f"{user_id}:{body.character_id}"
    if album_key not in _USER_ALBUMS:
        _USER_ALBUMS[album_key] = []
    
    album_entry = {
        "id": f"photo_{datetime.utcnow().timestamp()}",
        "type": "photo",
        "image_url": image_url,
        "created_at": datetime.utcnow().isoformat(),
        "context": body.context,
    }
    _USER_ALBUMS[album_key].append(album_entry)
    
    logger.info(f"Photo taken: {user_id} -> {body.character_id}, cost={config['cost']}, is_first={is_first}")
    
    return PhotoResponse(
        success=True,
        image_url=image_url,
        cost=config["cost"],
        is_first=is_first,
        message="拍照成功！已保存到相册" if not is_first else "🎉 首次拍照！已保存到相册",
        album_id=album_entry["id"],
    )


@router.post("/dressup", response_model=PhotoResponse)
async def dressup(body: DressupRequest, request: Request):
    """
    换装功能
    - 扣除月石
    - 根据选择的素材生成图片 (目前 mock)
    - 保存到相册
    - 记录首次事件
    """
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    config = INTERACTION_CONFIG["dressup"]
    
    # 1. 检查等级
    from app.services.intimacy_service import intimacy_service
    intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, body.character_id)
    current_level = intimacy_data.get("current_level", 1)
    
    if current_level < config["unlock_level"]:
        raise HTTPException(
            status_code=403,
            detail=f"需要 Lv.{config['unlock_level']} 解锁此功能，当前 Lv.{current_level}"
        )
    
    # 2. 验证素材选择
    valid_tops = [t["id"] for t in DRESSUP_OPTIONS["tops"]]
    valid_bottoms = [b["id"] for b in DRESSUP_OPTIONS["bottoms"]]
    
    if body.top_id not in valid_tops or body.bottom_id not in valid_bottoms:
        raise HTTPException(status_code=400, detail="无效的服装选择")
    
    # 3. 扣除月石
    from app.services.wallet_service import wallet_service
    
    balance = await wallet_service.get_balance(user_id)
    if balance < config["cost"]:
        raise HTTPException(
            status_code=402,
            detail=f"月石不足，需要 {config['cost']}，当前 {balance}"
        )
    
    await wallet_service.deduct(user_id, config["cost"], f"dressup:{body.character_id}")
    
    # 4. 检查是否首次
    events = intimacy_data.get("events", [])
    is_first = config["event_name"] not in events
    
    # 5. 记录首次事件
    if is_first:
        try:
            from app.core.database import get_db
            from sqlalchemy import text
            import json
            
            events.append(config["event_name"])
            async with get_db() as session:
                await session.execute(
                    text("""
                        UPDATE user_intimacy 
                        SET events = :events, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND character_id = :char_id
                    """),
                    {"events": json.dumps(events), "user_id": user_id, "char_id": body.character_id}
                )
                await session.commit()
            logger.info(f"First dressup event recorded for {user_id}:{body.character_id}")
        except Exception as e:
            logger.warning(f"Failed to record first dressup event: {e}")
    
    # 6. 生成图片 (目前 mock，后续接 Grok)
    # TODO: 调用 Grok image API with outfit parameters
    # image_url = await generate_dressup_with_grok(body.character_id, body.top_id, body.bottom_id)
    
    mock_photos = MOCK_PHOTOS.get(body.character_id, ["https://placeholder.com/default.jpg"])
    image_url = random.choice(mock_photos)
    
    # 7. 保存到相册
    album_key = f"{user_id}:{body.character_id}"
    if album_key not in _USER_ALBUMS:
        _USER_ALBUMS[album_key] = []
    
    album_entry = {
        "id": f"dressup_{datetime.utcnow().timestamp()}",
        "type": "dressup",
        "image_url": image_url,
        "created_at": datetime.utcnow().isoformat(),
        "outfit": {"top": body.top_id, "bottom": body.bottom_id},
    }
    _USER_ALBUMS[album_key].append(album_entry)
    
    logger.info(f"Dressup: {user_id} -> {body.character_id}, outfit={body.top_id}/{body.bottom_id}, cost={config['cost']}")
    
    return PhotoResponse(
        success=True,
        image_url=image_url,
        cost=config["cost"],
        is_first=is_first,
        message="换装成功！已保存到相册" if not is_first else "🎉 首次换装！已保存到相册",
        album_id=album_entry["id"],
    )


@router.get("/album/{character_id}")
async def get_album(character_id: str, request: Request):
    """获取用户与角色的相册"""
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    album_key = f"{user_id}:{character_id}"
    photos = _USER_ALBUMS.get(album_key, [])
    
    return {
        "character_id": character_id,
        "photos": photos,
        "total": len(photos),
    }

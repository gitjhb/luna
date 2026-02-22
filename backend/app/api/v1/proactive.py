"""
Proactive Messaging API Routes
==============================

主动消息系统 API - 让 AI 伴侣主动关心用户
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from app.services.proactive_service import proactive_service, ProactiveType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proactive")


# =============================================================================
# Request/Response Models
# =============================================================================

class CheckRequest(BaseModel):
    """请求检查主动消息"""
    character_id: str = Field(..., description="角色 ID")


class UpdateSettingsRequest(BaseModel):
    """更新主动消息设置"""
    enabled: Optional[bool] = Field(None, description="是否启用主动消息")
    timezone: Optional[str] = Field(None, description="用户时区")
    special_dates: Optional[Dict[str, str]] = Field(
        None, 
        description="特殊日期，如 {'birthday': '1995-03-15', 'anniversary': '2024-01-20'}"
    )


class RecordRequest(BaseModel):
    """记录主动消息发送"""
    character_id: str
    message_type: str
    message_content: str
    delivered: bool = True


# =============================================================================
# API Routes
# =============================================================================

@router.post("/check")
async def check_proactive(req: Request, body: CheckRequest) -> Dict[str, Any]:
    """
    检查用户是否需要收到主动消息
    
    触发检查逻辑:
    - 检查特殊日期（生日、纪念日）
    - 检查问候时间窗口（早安、晚安）
    - 检查是否长时间未聊天（想念消息）
    
    Returns:
        - success: bool
        - has_message: bool - 是否有消息需要发送
        - proactive: dict - 消息详情（如果有）
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        proactive = await proactive_service.check_and_get_proactive(
            user_id=user_id,
            character_id=body.character_id,
        )
        
        return {
            "success": True,
            "has_message": proactive is not None,
            "proactive": proactive,
        }
    except Exception as e:
        logger.error(f"[Proactive] Check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger")
async def trigger_proactive(req: Request, body: CheckRequest) -> Dict[str, Any]:
    """
    触发并记录主动消息
    
    与 /check 不同的是，这个端点会记录消息已发送，更新冷却时间。
    
    Returns:
        - success: bool
        - proactive: dict - 消息详情（如果有）
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        proactive = await proactive_service.process_and_record(
            user_id=user_id,
            character_id=body.character_id,
        )
        
        if proactive:
            logger.info(f"[Proactive] Triggered {proactive['type']} for user {user_id}")
        
        return {
            "success": True,
            "proactive": proactive,
        }
    except Exception as e:
        logger.error(f"[Proactive] Trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_proactive(
    req: Request,
    character_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    获取所有待发送的主动消息（管理员/cron用）
    
    Args:
        character_id: 可选，只检查特定角色
        limit: 最大返回数量
    
    Returns:
        - success: bool
        - messages: list - 待发送消息列表
        - count: int
    """
    try:
        messages = await proactive_service.get_users_to_reach(
            character_id=character_id,
            limit=limit,
        )
        
        return {
            "success": True,
            "messages": messages,
            "count": len(messages),
        }
    except Exception as e:
        logger.error(f"[Proactive] Pending error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_settings(req: Request) -> Dict[str, Any]:
    """
    获取用户的主动消息设置
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    settings = await proactive_service.get_user_settings(user_id)
    
    return {
        "success": True,
        "settings": settings,
    }


@router.put("/settings")
async def update_settings(req: Request, body: UpdateSettingsRequest) -> Dict[str, Any]:
    """
    更新用户的主动消息设置
    
    Args:
        enabled: 是否启用主动消息
        timezone: 用户时区
        special_dates: 特殊日期
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    updated = await proactive_service.update_user_settings(
        user_id=user_id,
        enabled=body.enabled,
        timezone=body.timezone,
        special_dates=body.special_dates,
    )
    
    return {
        "success": True,
        "settings": updated,
    }


@router.post("/record")
async def record_proactive(req: Request, body: RecordRequest) -> Dict[str, Any]:
    """
    手动记录主动消息发送（用于外部系统记录）
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        message_type = ProactiveType(body.message_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid message_type. Must be one of: {[t.value for t in ProactiveType]}"
        )
    
    await proactive_service.record_proactive(
        user_id=user_id,
        character_id=body.character_id,
        message_type=message_type,
        message_content=body.message_content,
        delivered=body.delivered,
    )
    
    return {
        "success": True,
        "recorded": True,
    }


@router.get("/preview/{character_id}")
async def preview_message(
    character_id: str,
    message_type: str = "good_morning",
) -> Dict[str, Any]:
    """
    预览主动消息（调试用）
    
    Args:
        character_id: 角色 ID
        message_type: 消息类型
    """
    try:
        msg_type = ProactiveType(message_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message_type. Must be one of: {[t.value for t in ProactiveType]}"
        )
    
    message = proactive_service.generate_proactive_message(
        character_id=character_id,
        trigger_type=msg_type,
    )
    
    return {
        "success": True,
        "character_id": character_id,
        "message_type": message_type,
        "message": message,
    }


@router.get("/types")
async def get_proactive_types() -> Dict[str, Any]:
    """
    获取所有主动消息类型
    """
    return {
        "success": True,
        "types": [
            {
                "value": t.value,
                "name": t.name,
                "description": {
                    "good_morning": "早安消息 (7-9点)",
                    "good_night": "晚安消息 (21-23点)",
                    "miss_you": "想念消息 (4小时未聊天)",
                    "check_in": "关心消息 (6小时冷却)",
                    "anniversary": "纪念日消息",
                    "birthday": "生日消息",
                    "random_share": "随机分享",
                }.get(t.value, t.value),
            }
            for t in ProactiveType
        ],
    }

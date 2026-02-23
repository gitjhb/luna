"""
Proactive Message API
=====================

主动消息系统的 API 端点。
由 cron job 定期调用，检查并发送主动消息。
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from app.services.proactive_message import (
    proactive_service,
    check_proactive_for_user,
    ProactiveType,
    PROACTIVE_TEMPLATES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proactive")


class ProactiveCheckRequest(BaseModel):
    user_id: str
    character_id: str = "luna"
    intimacy_level: int = 1
    last_chat_hours: Optional[float] = None  # 距离上次聊天的小时数
    timezone: str = "America/Los_Angeles"


class ProactiveCheckResponse(BaseModel):
    should_send: bool
    type: Optional[str] = None
    message: Optional[str] = None


class ProactiveBatchRequest(BaseModel):
    users: List[ProactiveCheckRequest]


@router.post("/check", response_model=ProactiveCheckResponse)
async def check_proactive(req: ProactiveCheckRequest):
    """
    检查单个用户是否应该收到主动消息
    
    用于调试和测试。
    """
    last_chat_time = None
    if req.last_chat_hours is not None:
        from datetime import timedelta
        last_chat_time = datetime.now() - timedelta(hours=req.last_chat_hours)
    
    result = await check_proactive_for_user(
        user_id=req.user_id,
        character_id=req.character_id,
        intimacy_level=req.intimacy_level,
        last_chat_time=last_chat_time,
        timezone=req.timezone,
    )
    
    if result:
        return ProactiveCheckResponse(
            should_send=True,
            type=result["type"],
            message=result["message"],
        )
    
    return ProactiveCheckResponse(should_send=False)


@router.post("/batch")
async def check_proactive_batch(req: ProactiveBatchRequest):
    """
    批量检查多个用户的主动消息
    
    由 cron job 调用。返回需要发送消息的用户列表。
    """
    from datetime import timedelta
    
    users = []
    for u in req.users:
        last_chat_time = None
        if u.last_chat_hours is not None:
            last_chat_time = datetime.now() - timedelta(hours=u.last_chat_hours)
        
        users.append({
            "user_id": u.user_id,
            "character_id": u.character_id,
            "intimacy_level": u.intimacy_level,
            "last_chat_time": last_chat_time,
            "timezone": u.timezone,
            "muted": False,
        })
    
    results = await proactive_service.process_all_users(users)
    
    return {
        "total_checked": len(req.users),
        "messages_to_send": len(results),
        "results": results,
    }


@router.get("/templates")
async def get_templates(character_id: Optional[str] = None):
    """
    获取主动消息模板
    
    用于调试和预览。
    """
    if character_id:
        templates = PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES.get("default", {}))
        return {character_id: templates}
    
    return PROACTIVE_TEMPLATES


@router.post("/test/{user_id}")
async def test_proactive(
    user_id: str,
    character_id: str = "luna",
    msg_type: str = "good_morning",
    force: bool = Query(False, description="强制发送，忽略冷却时间"),
):
    """
    测试主动消息生成
    
    用于开发测试，可以强制生成消息忽略冷却。
    """
    try:
        ptype = ProactiveType(msg_type)
    except ValueError:
        raise HTTPException(400, f"Invalid message type: {msg_type}")
    
    # 检查冷却
    can_send = await proactive_service.can_send_proactive(user_id, character_id, ptype)
    
    if not can_send and not force:
        return {
            "success": False,
            "reason": "cooldown",
            "message": f"Message type {msg_type} is still in cooldown period",
        }
    
    # 生成消息
    message = proactive_service.pick_template(character_id, ptype)
    
    if not message:
        return {
            "success": False,
            "reason": "no_template",
            "message": f"No template found for {character_id}/{msg_type}",
        }
    
    # 记录发送
    if not force:
        await proactive_service.record_proactive(user_id, character_id, ptype)
    
    return {
        "success": True,
        "type": msg_type,
        "character_id": character_id,
        "message": message,
        "forced": force,
    }

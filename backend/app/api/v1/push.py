"""
Push Notification API Routes
"""

from fastapi import APIRouter, Request
from typing import List, Dict, Any
import logging

from app.services.push_notification_service import push_notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/push")


@router.get("/pending")
async def get_pending_pushes(req: Request) -> Dict[str, Any]:
    """
    获取待接收的推送消息
    
    前端可以定期轮询此接口（建议 5-10 分钟一次）
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    pushes = await push_notification_service.get_pending_pushes(user_id)
    
    return {
        "success": True,
        "pushes": pushes,
        "count": len(pushes),
    }


@router.get("/config/{character_id}")
async def get_character_push_config(character_id: str) -> Dict[str, Any]:
    """获取角色的推送配置"""
    config = push_notification_service.get_character_push_config(character_id)
    
    if not config:
        return {
            "success": False,
            "error": "Character not found",
        }
    
    return {
        "success": True,
        "config": config,
    }


@router.get("/preview/{character_id}")
async def preview_push_message(
    character_id: str,
    intimacy_level: int = 25,
) -> Dict[str, Any]:
    """
    预览推送消息（调试用）
    
    Args:
        character_id: 角色 ID
        intimacy_level: 模拟的亲密度等级
    """
    message = push_notification_service.generate_push_message(
        character_id, intimacy_level
    )
    
    if not message:
        return {
            "success": False,
            "error": "Cannot generate message (level too low or no config)",
        }
    
    return {
        "success": True,
        "preview": message,
    }


@router.get("/test")
async def test_push_all(req: Request) -> Dict[str, Any]:
    """
    测试所有角色的推送（调试用）
    
    忽略时间和频率限制，直接生成所有角色的消息
    """
    user = getattr(req.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    results = []
    
    for char_id in push_notification_service.configs.keys():
        # 模拟 S3 阶段
        message = push_notification_service.generate_push_message(char_id, 35)
        if message:
            results.append(message)
    
    return {
        "success": True,
        "test_messages": results,
        "count": len(results),
    }

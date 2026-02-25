"""
Enhanced Proactive Message API
==============================

增强版主动消息API端点
- POST /proactive/check/{user_id} - 检查并生成单用户主动消息
- POST /proactive/process-all - 批量处理（cron调用）
- GET /proactive/templates - 获取消息模板
- POST /proactive/test/{user_id} - 测试消息生成
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Query, Body
from pydantic import BaseModel
from datetime import datetime

from app.services.proactive_service_updated import (
    enhanced_proactive_service,
    ProactiveType,
    CHARACTER_TEMPLATES
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proactive", tags=["proactive"])


# =============================================================================
# 请求/响应模型
# =============================================================================

class ProactiveCheckResponse(BaseModel):
    """检查主动消息响应"""
    success: bool
    should_send: bool = False
    type: Optional[str] = None
    message: Optional[str] = None
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    timestamp: Optional[str] = None


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    users: List[Dict[str, str]]  # [{"user_id": "xxx", "character_id": "yyy"}, ...]
    limit: int = 50


class BatchProcessResponse(BaseModel):
    """批量处理响应"""
    success: bool
    total_checked: int
    messages_generated: int
    results: List[Dict[str, Any]]


class TestMessageRequest(BaseModel):
    """测试消息请求"""
    character_id: str = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"  # 默认Luna
    message_type: str = "good_morning"
    force_send: bool = False  # 忽略冷却时间


# =============================================================================
# API 端点
# =============================================================================

@router.post("/check/{user_id}", response_model=ProactiveCheckResponse)
async def check_user_proactive(
    user_id: str = Path(..., description="用户ID"),
    character_id: str = Query(
        "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d", 
        description="角色ID，默认Luna"
    )
):
    """
    检查并生成单个用户的主动消息
    
    Args:
        user_id: 用户ID
        character_id: 角色ID（可选，默认Luna）
    
    Returns:
        ProactiveCheckResponse: 包含生成的消息信息
    """
    try:
        result = await enhanced_proactive_service.process_user_proactive(
            user_id=user_id,
            character_id=character_id
        )
        
        if result:
            return ProactiveCheckResponse(
                success=True,
                should_send=True,
                type=result["type"],
                message=result["message"],
                user_id=result["user_id"],
                character_id=result["character_id"],
                timestamp=result["timestamp"]
            )
        else:
            return ProactiveCheckResponse(
                success=True,
                should_send=False
            )
            
    except Exception as e:
        logger.error(f"Error checking proactive for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/process-all", response_model=BatchProcessResponse)
async def process_all_users(request: BatchProcessRequest):
    """
    批量处理多个用户的主动消息
    
    由cron job调用，用于定期检查所有活跃用户的主动消息需求。
    
    Args:
        request: BatchProcessRequest包含用户列表和限制数量
    
    Returns:
        BatchProcessResponse: 批量处理结果
    """
    try:
        results = await enhanced_proactive_service.batch_process_users(
            users=request.users,
            limit=request.limit
        )
        
        return BatchProcessResponse(
            success=True,
            total_checked=len(request.users),
            messages_generated=len(results),
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.get("/templates")
async def get_character_templates(
    character_id: Optional[str] = Query(None, description="角色ID，留空获取所有模板")
):
    """
    获取角色消息模板
    
    用于调试和预览模板内容。
    
    Args:
        character_id: 可选，指定角色ID
    
    Returns:
        Dict: 角色消息模板
    """
    if character_id:
        templates = CHARACTER_TEMPLATES.get(character_id)
        if not templates:
            raise HTTPException(
                status_code=404,
                detail=f"No templates found for character: {character_id}"
            )
        return {character_id: templates}
    
    # 返回所有模板（去除敏感信息）
    return {
        "available_characters": list(CHARACTER_TEMPLATES.keys()),
        "templates": CHARACTER_TEMPLATES
    }


@router.post("/test/{user_id}")
async def test_message_generation(
    user_id: str = Path(..., description="用户ID"),
    request: TestMessageRequest = Body(...)
):
    """
    测试消息生成功能
    
    用于开发测试，可以强制生成特定类型的消息。
    
    Args:
        user_id: 用户ID
        request: TestMessageRequest包含测试参数
    
    Returns:
        Dict: 测试结果
    """
    try:
        # 验证消息类型
        try:
            msg_type = ProactiveType(request.message_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid message type: {request.message_type}. "
                       f"Valid types: {[t.value for t in ProactiveType]}"
            )
        
        # 检查冷却时间（除非force_send）
        if not request.force_send:
            can_send = await enhanced_proactive_service.can_send_proactive(
                user_id=user_id,
                character_id=request.character_id,
                msg_type=msg_type
            )
            if not can_send:
                return {
                    "success": False,
                    "reason": "cooldown",
                    "message": f"Message type {request.message_type} is still in cooldown",
                    "force_send_available": True
                }
        
        # 生成消息
        message = enhanced_proactive_service.pick_message_template(
            character_id=request.character_id,
            msg_type=msg_type
        )
        
        if not message:
            return {
                "success": False,
                "reason": "no_template",
                "message": f"No template found for character {request.character_id} "
                          f"and message type {request.message_type}"
            }
        
        # 如果不是强制发送，记录到系统中
        if not request.force_send:
            await enhanced_proactive_service.record_proactive(
                user_id=user_id,
                character_id=request.character_id,
                msg_type=msg_type,
                message_content=message
            )
        
        return {
            "success": True,
            "type": request.message_type,
            "character_id": request.character_id,
            "message": message,
            "forced": request.force_send,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test message generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )


@router.get("/stats/{user_id}")
async def get_user_proactive_stats(
    user_id: str = Path(..., description="用户ID"),
    character_id: Optional[str] = Query(None, description="角色ID")
):
    """
    获取用户主动消息统计
    
    Args:
        user_id: 用户ID
        character_id: 可选，角色ID
    
    Returns:
        Dict: 统计信息
    """
    try:
        from app.core.database import get_db
        from sqlalchemy import select, func
        from app.models.database.proactive_models import ProactiveHistory
        
        async with get_db() as db:
            query = select(
                ProactiveHistory.message_type,
                func.count(ProactiveHistory.id).label('count'),
                func.max(ProactiveHistory.created_at).label('last_sent')
            ).where(
                ProactiveHistory.user_id == user_id
            ).group_by(ProactiveHistory.message_type)
            
            if character_id:
                query = query.where(ProactiveHistory.character_id == character_id)
            
            result = await db.execute(query)
            stats = result.fetchall()
            
            return {
                "user_id": user_id,
                "character_id": character_id,
                "stats": [
                    {
                        "message_type": row.message_type,
                        "count": row.count,
                        "last_sent": row.last_sent.isoformat() if row.last_sent else None
                    }
                    for row in stats
                ],
                "total_messages": sum(row.count for row in stats)
            }
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    健康检查端点
    
    检查系统各组件是否正常。
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # 检查Redis连接
    try:
        from app.core.redis_client import get_redis_client
        redis = await get_redis_client()
        await redis.ping()
        health["components"]["redis"] = "healthy"
    except Exception as e:
        health["components"]["redis"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # 检查数据库连接
    try:
        from app.core.database import get_db
        async with get_db() as db:
            await db.execute(select(1))
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    return health
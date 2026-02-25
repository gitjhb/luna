"""
Proactive Messaging API v2
==========================
支持 cron job 调用的主动消息接口
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.services.proactive_v2 import ProactiveServiceV2, get_engagement_strategy
from app.models.database.user_models import User
from app.models.database.intimacy_models import UserIntimacy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proactive/v2", tags=["proactive-v2"])


@router.post("/check/{user_id}")
async def check_user_proactive(
    user_id: str,
    character_id: str = Query(...),
    character_name: str = Query(default="Luna"),
    db: AsyncSession = Depends(get_db),
):
    """
    检查单个用户是否应该收到主动消息
    返回生成的消息内容（如果需要发送）
    """
    try:
        redis = get_redis_client()
        service = ProactiveServiceV2(redis_client=redis, db_session=db)
        
        # 获取用户亲密度
        intimacy_level = 1
        try:
            result = await db.execute(
                select(UserIntimacy).where(
                    and_(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.character_id == character_id
                    )
                )
            )
            intimacy = result.scalar_one_or_none()
            if intimacy:
                intimacy_level = intimacy.current_level
        except Exception as e:
            logger.warning(f"Could not get intimacy: {e}")
        
        # 亲密度低于 2 不发
        if intimacy_level < 2:
            return {"send": False, "reason": "intimacy_too_low", "level": intimacy_level}
        
        # 检查并生成消息
        result = await service.check_and_generate(
            user_id=user_id,
            character_id=character_id,
            character_name=character_name,
            intimacy_level=intimacy_level,
        )
        
        if result:
            return {
                "send": True,
                "user_id": user_id,
                "message": result["message"],
                "type": result["type"],
                "mode": result["mode"],
                "language": result["language"],
            }
        else:
            return {"send": False, "reason": "skipped_by_strategy"}
            
    except Exception as e:
        logger.error(f"Error checking proactive for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-batch")
async def process_batch(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    批量处理活跃用户的主动消息
    由 cron job 定期调用
    """
    try:
        redis = get_redis_client()
        service = ProactiveServiceV2(redis_client=redis, db_session=db)
        
        # 获取最近 7 天活跃的用户
        # TODO: 根据实际情况调整查询
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        result = await db.execute(
            select(User).where(User.updated_at >= seven_days_ago).limit(limit)
        )
        users = result.scalars().all()
        
        results = []
        sent_count = 0
        
        for user in users:
            try:
                # 获取用户的角色偏好（简化：默认 Luna）
                character_id = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
                character_name = "Luna"
                
                # 获取亲密度
                intimacy_result = await db.execute(
                    select(UserIntimacy).where(
                        and_(
                            UserIntimacy.user_id == user.user_id,
                            UserIntimacy.character_id == character_id
                        )
                    )
                )
                intimacy = intimacy_result.scalar_one_or_none()
                intimacy_level = intimacy.current_level if intimacy else 1
                
                if intimacy_level < 2:
                    results.append({
                        "user_id": user.user_id,
                        "sent": False,
                        "reason": "low_intimacy"
                    })
                    continue
                
                # 检查并生成
                msg_result = await service.check_and_generate(
                    user_id=user.user_id,
                    character_id=character_id,
                    character_name=character_name,
                    intimacy_level=intimacy_level,
                )
                
                if msg_result:
                    # TODO: 实际发送消息（通过 push notification 或 websocket）
                    # await send_push_notification(user.user_id, msg_result["message"])
                    
                    results.append({
                        "user_id": user.user_id,
                        "sent": True,
                        "type": msg_result["type"],
                        "mode": msg_result["mode"],
                        "language": msg_result["language"],
                    })
                    sent_count += 1
                else:
                    results.append({
                        "user_id": user.user_id,
                        "sent": False,
                        "reason": "skipped"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing user {user.user_id}: {e}")
                results.append({
                    "user_id": user.user_id,
                    "sent": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_users": len(users),
            "sent_count": sent_count,
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"Batch process error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy-preview/{user_id}")
async def preview_strategy(
    user_id: str,
    days_since_reply: float = Query(default=0),
    intimacy_level: int = Query(default=1),
):
    """
    预览发送策略（调试用）
    """
    strategy = get_engagement_strategy(days_since_reply, intimacy_level)
    return {
        "user_id": user_id,
        "days_since_reply": days_since_reply,
        "intimacy_level": intimacy_level,
        "strategy": {
            "should_send": strategy["should_send"],
            "probability": strategy["probability"],
            "mode": strategy["mode"].value,
        }
    }


@router.get("/templates")
async def get_templates(
    language: str = Query(default="en"),
    character: str = Query(default="luna"),
):
    """
    获取角色模板（调试用）
    """
    from app.services.proactive_v2 import CHARACTER_TEMPLATES
    
    char_templates = CHARACTER_TEMPLATES.get(character.lower(), {})
    lang_templates = char_templates.get(language, {})
    
    return {
        "character": character,
        "language": language,
        "templates": lang_templates,
    }

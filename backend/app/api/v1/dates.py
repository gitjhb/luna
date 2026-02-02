"""
Date API Routes - 约会系统
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from pydantic import BaseModel

from app.services.date_service import date_service

router = APIRouter(prefix="/dates")


class StartDateRequest(BaseModel):
    character_id: str
    scenario_id: Optional[str] = None


class CompleteDateRequest(BaseModel):
    character_id: str


@router.get("/unlock-status/{character_id}")
async def check_date_unlock_status(character_id: str, req: Request):
    """
    检查约会是否解锁
    
    Returns:
        is_unlocked: 是否解锁
        reason: 原因说明
    """
    user_id = getattr(req.state, "user_id", "test_user")
    
    is_unlocked, reason = await date_service.check_date_unlock(user_id, character_id)
    
    return {
        "is_unlocked": is_unlocked,
        "reason": reason,
        "unlock_level": 10,
    }


@router.get("/scenarios")
async def list_date_scenarios():
    """
    获取可用的约会场景列表
    """
    scenarios = date_service.get_date_scenarios()
    return {
        "scenarios": scenarios,
        "total": len(scenarios),
    }


@router.post("/start")
async def start_date(request: StartDateRequest, req: Request):
    """
    开始约会
    
    需要：
    - LV 10+
    - 已完成 first_gift 事件
    """
    user_id = getattr(req.state, "user_id", "test_user")
    
    result = await date_service.start_date(
        user_id=user_id,
        character_id=request.character_id,
        scenario_id=request.scenario_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "无法开始约会"))
    
    return result


@router.get("/active/{character_id}")
async def get_active_date(character_id: str, req: Request):
    """
    获取当前进行中的约会
    """
    user_id = getattr(req.state, "user_id", "test_user")
    
    date_info = await date_service.get_active_date(user_id, character_id)
    
    if not date_info:
        return {"has_active_date": False}
    
    return {
        "has_active_date": True,
        "date": date_info,
    }


@router.post("/complete")
async def complete_date(request: CompleteDateRequest, req: Request):
    """
    完成约会（手动触发，通常由前端在适当时机调用）
    """
    user_id = getattr(req.state, "user_id", "test_user")
    
    result = await date_service.complete_date(
        user_id=user_id,
        character_id=request.character_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "无法完成约会"))
    
    return result


@router.post("/cancel")
async def cancel_date(request: CompleteDateRequest, req: Request):
    """
    取消约会
    """
    user_id = getattr(req.state, "user_id", "test_user")
    
    result = await date_service.cancel_date(
        user_id=user_id,
        character_id=request.character_id,
    )
    
    return result

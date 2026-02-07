"""
Date API Routes - 约会系统

支持两种模式：
1. 简单模式：一键生成约会故事 (原有)
2. 互动模式：分阶段选择的交互式约会 (新)
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from pydantic import BaseModel

from app.services.date_service import date_service
from app.services.interactive_date_service import interactive_date_service

router = APIRouter(prefix="/dates")


def _is_buddy_character(character_id: str) -> bool:
    """Check if character is BUDDY archetype (no dating allowed)."""
    try:
        from app.services.character_config import get_character_config, CharacterArchetype
        config = get_character_config(character_id)
        return config and config.archetype == CharacterArchetype.BUDDY
    except Exception:
        return False


def _get_user_id(req: Request) -> str:
    """Extract user_id from request state (set by auth middleware)."""
    user = getattr(req.state, "user", None)
    return str(user.user_id) if user else "demo-user-123"


# =============================================================================
# Request Models
# =============================================================================

class StartDateRequest(BaseModel):
    character_id: str
    scenario_id: Optional[str] = None


class MakeChoiceRequest(BaseModel):
    session_id: str
    choice_id: int


class CompleteDateRequest(BaseModel):
    character_id: str


class AbandonDateRequest(BaseModel):
    session_id: str


class FreeInputRequest(BaseModel):
    session_id: str
    user_input: str


class ExtendDateRequest(BaseModel):
    session_id: str


class FinishDateRequest(BaseModel):
    session_id: str


class ResetCooldownRequest(BaseModel):
    character_id: str


# =============================================================================
# 基础 API (解锁检查、场景列表)
# =============================================================================

@router.get("/unlock-status/{character_id}")
async def check_date_unlock_status(character_id: str, req: Request):
    """
    检查约会是否解锁
    
    Returns:
        is_unlocked: 是否解锁
        reason: 原因说明
        current_level: 当前等级
        level_met: 等级是否达标
        gift_sent: 是否已送过礼物
        hidden: 是否隐藏约会功能 (BUDDY角色)
    """
    # BUDDY角色（煤球）不支持约会
    if _is_buddy_character(character_id):
        return {
            "is_unlocked": False,
            "hidden": True,
            "reason": "这个角色不支持约会功能",
        }
    
    user_id = _get_user_id(req)
    result = await date_service.get_unlock_details(user_id, character_id)
    result["hidden"] = False
    return result


@router.get("/scenarios")
async def list_date_scenarios(req: Request, character_id: Optional[str] = None):
    """
    获取可用的约会场景列表
    
    如果提供 character_id，返回该角色的专属场景（带锁定状态）
    BUDDY角色返回空列表
    """
    if character_id:
        # BUDDY角色不支持约会，返回空
        if _is_buddy_character(character_id):
            return {"scenarios": [], "total": 0, "hidden": True}
        
        user_id = _get_user_id(req)
        scenarios = await date_service.get_character_date_scenarios(user_id, character_id)
    else:
        scenarios = date_service.get_date_scenarios()
    return {
        "scenarios": scenarios,
        "total": len(scenarios),
    }


@router.get("/status/{character_id}")
async def get_date_status(character_id: str, req: Request):
    """
    检查约会状态（冷却、进行中的约会）
    """
    # BUDDY角色不支持约会
    if _is_buddy_character(character_id):
        return {
            "is_unlocked": False,
            "hidden": True,
            "reason": "这个角色不支持约会功能",
            "can_date": False,
        }
    
    user_id = _get_user_id(req)
    
    # 检查解锁
    unlock_info = await date_service.get_unlock_details(user_id, character_id)
    
    # 检查冷却和活跃会话
    date_status = await interactive_date_service.check_can_date(user_id, character_id)
    
    return {
        "hidden": False,
        **unlock_info,
        **date_status,
    }


# =============================================================================
# 互动式约会 API (新)
# =============================================================================

@router.post("/interactive/start")
async def start_interactive_date(request: StartDateRequest, req: Request):
    """
    开始互动式约会
    
    返回第一个阶段的剧情和选项
    """
    # BUDDY角色不能约会
    if _is_buddy_character(request.character_id):
        raise HTTPException(status_code=400, detail="这个角色不支持约会功能")
    
    user_id = _get_user_id(req)
    
    if not request.scenario_id:
        return {"success": False, "error": "请选择约会场景"}
    
    result = await interactive_date_service.start_date(
        user_id=user_id,
        character_id=request.character_id,
        scenario_id=request.scenario_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "无法开始约会"))
    
    return result


@router.post("/interactive/choose")
async def make_date_choice(request: MakeChoiceRequest, req: Request):
    """
    在约会中做出选择
    
    返回下一阶段的剧情和选项，或者结局
    """
    result = await interactive_date_service.make_choice(
        session_id=request.session_id,
        choice_id=request.choice_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "选择失败"))
    
    return result


@router.get("/interactive/session/{session_id}")
async def get_date_session(session_id: str, req: Request):
    """
    获取约会会话信息
    """
    session = await interactive_date_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return session


@router.post("/interactive/free-input")
async def process_free_input(request: FreeInputRequest, req: Request):
    """
    处理用户自由输入
    
    用户可以输入预设选项之外的话，LLM 作为"裁判"评判并延续剧情
    """
    if not request.user_input or len(request.user_input.strip()) < 2:
        raise HTTPException(status_code=400, detail="请输入有效的内容")
    
    if len(request.user_input) > 500:
        raise HTTPException(status_code=400, detail="输入内容过长，请控制在 500 字以内")
    
    result = await interactive_date_service.process_free_input(
        session_id=request.session_id,
        user_input=request.user_input.strip(),
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "处理失败"))
    
    return result


@router.post("/interactive/abandon")
async def abandon_interactive_date(request: AbandonDateRequest, req: Request):
    """
    放弃当前约会
    """
    result = await interactive_date_service.abandon_date(request.session_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "取消失败"))
    
    return result


@router.post("/interactive/finish")
async def finish_date(request: FinishDateRequest, req: Request):
    """
    结束约会（在检查点选择不延长时调用）
    
    生成结局并返回奖励
    """
    result = await interactive_date_service.finish_date(
        session_id=request.session_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "结束失败"))
    
    return result


@router.post("/interactive/extend")
async def extend_date(request: ExtendDateRequest, req: Request):
    """
    付费延长约会剧情（生成 bonus stage）
    
    费用：10 月石
    上限：最多延长 3 章（原5章 + 3章bonus = 8章）
    """
    user_id = _get_user_id(req)
    
    result = await interactive_date_service.extend_date(
        session_id=request.session_id,
        user_id=user_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "延长失败"))
    
    return result


@router.get("/interactive/extend-price")
async def get_extend_price():
    """
    获取延长剧情的价格
    """
    return {
        "price": 10,
        "currency": "月石",
        "description": "继续约会剧情",
        "max_extends": 3,
    }


@router.post("/interactive/reset-cooldown")
async def reset_date_cooldown(request: ResetCooldownRequest, req: Request):
    """
    使用月石重置约会冷却时间
    
    费用：50 月石
    """
    user_id = _get_user_id(req)
    
    result = await interactive_date_service.reset_cooldown(
        user_id=user_id,
        character_id=request.character_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "重置失败"))
    
    return result


@router.get("/interactive/cooldown-reset-price")
async def get_cooldown_reset_price():
    """
    获取重置冷却的价格
    """
    return {
        "price": 50,
        "currency": "月石",
        "description": "立即重置约会冷却时间",
    }


# =============================================================================
# 简单模式 API (保留原有功能)
# =============================================================================

@router.post("/start")
async def start_date(request: StartDateRequest, req: Request):
    """
    开始约会（简单模式 - 一键生成故事）
    
    需要：
    - LV 10+
    - 已完成 first_gift 事件
    """
    user_id = _get_user_id(req)
    
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
    user_id = _get_user_id(req)
    
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
    完成约会（简单模式）
    """
    user_id = _get_user_id(req)
    
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
    user_id = _get_user_id(req)
    
    result = await date_service.cancel_date(
        user_id=user_id,
        character_id=request.character_id,
    )
    
    return result

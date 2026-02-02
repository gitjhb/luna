"""
Debug API Routes
================

仅用于测试环境！
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging

router = APIRouter(prefix="/debug")
logger = logging.getLogger(__name__)


class SetLevelRequest(BaseModel):
    user_id: Optional[str] = None
    character_id: str
    level: int


class SetEmotionRequest(BaseModel):
    user_id: Optional[str] = None
    character_id: str
    emotion: int


class SetXPRequest(BaseModel):
    user_id: Optional[str] = None
    character_id: str
    xp: int


class AddEventRequest(BaseModel):
    user_id: Optional[str] = None
    character_id: str
    event: str


@router.post("/set_level")
async def set_level(body: SetLevelRequest, request: Request):
    """
    Debug: 直接设置用户等级
    
    会同时更新 XP 到对应等级所需的值
    """
    user = getattr(request.state, "user", None)
    user_id = body.user_id or (str(user.user_id) if user else "demo-user-123")
    
    from app.services.intimacy_system import LEVEL_XP_TABLE, generate_levelup_message
    from app.services.intimacy_service import intimacy_service
    
    # 获取等级对应的 XP
    target_xp = LEVEL_XP_TABLE.get(body.level, 0)
    if target_xp == 0 and body.level > 1:
        # 估算中间等级的 XP
        sorted_levels = sorted(LEVEL_XP_TABLE.keys())
        for i, lvl in enumerate(sorted_levels):
            if lvl >= body.level:
                if i > 0:
                    prev_lvl = sorted_levels[i-1]
                    prev_xp = LEVEL_XP_TABLE[prev_lvl]
                    next_xp = LEVEL_XP_TABLE.get(lvl, prev_xp + 500)
                    ratio = (body.level - prev_lvl) / (lvl - prev_lvl)
                    target_xp = int(prev_xp + (next_xp - prev_xp) * ratio)
                break
    
    # 获取当前数据
    current = await intimacy_service.get_or_create_intimacy(user_id, body.character_id)
    old_level = current.get("current_level", 1)
    
    # 更新 XP
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        
        async with get_db() as session:
            await session.execute(
                text("""
                    UPDATE user_intimacy 
                    SET total_xp = :xp, current_level = :level, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND character_id = :char_id
                """),
                {"xp": target_xp, "level": body.level, "user_id": user_id, "char_id": body.character_id}
            )
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to set level: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # 生成升级提示
    levelup_msg = generate_levelup_message(old_level, body.level)
    
    return {
        "success": True,
        "user_id": user_id,
        "character_id": body.character_id,
        "old_level": old_level,
        "new_level": body.level,
        "xp_set": target_xp,
        "levelup_message": levelup_msg,
    }


@router.post("/set_emotion")
async def set_emotion(body: SetEmotionRequest, request: Request):
    """
    Debug: 直接设置用户情绪
    """
    user = getattr(request.state, "user", None)
    user_id = body.user_id or (str(user.user_id) if user else "demo-user-123")
    
    from app.services.emotion_engine_v2 import emotion_engine
    
    # 获取当前情绪
    current = await emotion_engine.get_score(user_id, body.character_id)
    
    # 计算 delta
    delta = body.emotion - current
    
    # 更新
    new_score = await emotion_engine.update_score(
        user_id, body.character_id, delta, "debug_set"
    )
    
    return {
        "success": True,
        "user_id": user_id,
        "character_id": body.character_id,
        "old_emotion": current,
        "new_emotion": new_score,
    }


@router.post("/set_xp")
async def set_xp(body: SetXPRequest, request: Request):
    """
    Debug: 直接设置用户 XP
    """
    user = getattr(request.state, "user", None)
    user_id = body.user_id or (str(user.user_id) if user else "demo-user-123")
    
    from app.services.intimacy_system import xp_to_level, generate_levelup_message
    from app.services.intimacy_service import intimacy_service
    
    # 获取当前数据
    current = await intimacy_service.get_or_create_intimacy(user_id, body.character_id)
    old_level = current.get("current_level", 1)
    old_xp = current.get("total_xp", 0)
    
    # 计算新等级
    new_level = xp_to_level(body.xp)
    
    # 更新
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        
        async with get_db() as session:
            await session.execute(
                text("""
                    UPDATE user_intimacy 
                    SET total_xp = :xp, current_level = :level, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND character_id = :char_id
                """),
                {"xp": body.xp, "level": new_level, "user_id": user_id, "char_id": body.character_id}
            )
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to set XP: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # 生成升级提示
    levelup_msg = None
    if new_level > old_level:
        levelup_msg = generate_levelup_message(old_level, new_level)
    
    return {
        "success": True,
        "user_id": user_id,
        "character_id": body.character_id,
        "old_xp": old_xp,
        "new_xp": body.xp,
        "old_level": old_level,
        "new_level": new_level,
        "levelup_message": levelup_msg,
    }


@router.post("/add_event")
async def add_event(body: AddEventRequest, request: Request):
    """
    Debug: 添加事件
    """
    user = getattr(request.state, "user", None)
    user_id = body.user_id or (str(user.user_id) if user else "demo-user-123")
    
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        import json
        
        async with get_db() as session:
            # 获取当前事件
            result = await session.execute(
                text("SELECT events FROM user_intimacy WHERE user_id = :user_id AND character_id = :char_id"),
                {"user_id": user_id, "char_id": body.character_id}
            )
            row = result.fetchone()
            
            if row and row[0]:
                events = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            else:
                events = []
            
            # 添加新事件
            if body.event not in events:
                events.append(body.event)
            
            # 更新
            await session.execute(
                text("""
                    UPDATE user_intimacy 
                    SET events = :events, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND character_id = :char_id
                """),
                {"events": json.dumps(events), "user_id": user_id, "char_id": body.character_id}
            )
            await session.commit()
            
        return {
            "success": True,
            "user_id": user_id,
            "character_id": body.character_id,
            "event_added": body.event,
            "all_events": events,
        }
    except Exception as e:
        logger.error(f"Failed to add event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{character_id}")
async def get_debug_status(character_id: str, request: Request):
    """
    Debug: 获取完整的用户状态
    """
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    from app.services.intimacy_service import intimacy_service
    from app.services.emotion_engine_v2 import emotion_engine
    from app.services.intimacy_system import (
        get_stage, get_unlocked_features, get_next_unlocks,
        calculate_power, STAGE_NAMES
    )
    from app.services.character_config import get_character_config
    
    # 获取亲密度数据
    intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
    level = intimacy_data.get("current_level", 1)
    xp = intimacy_data.get("total_xp", 0)
    events = intimacy_data.get("events", [])
    
    # 获取情绪
    emotion = await emotion_engine.get_score(user_id, character_id)
    
    # 获取角色配置
    char_config = get_character_config(character_id)
    chaos = char_config.z_axis.chaos_val if char_config else 20
    pure = char_config.z_axis.pure_val if char_config else 30
    archetype = char_config.archetype if char_config else "normal"
    
    # 计算 intimacy_x (和 game_engine 一样的逻辑)
    if level <= 5:
        intimacy_x = round((level - 1) * 4.75, 1)
    elif level <= 10:
        intimacy_x = round(20 + (level - 6) * 4, 1)
    elif level <= 15:
        intimacy_x = round(40 + (level - 11) * 4, 1)
    elif level <= 25:
        intimacy_x = round(60 + (level - 16) * 2, 1)
    else:
        intimacy_x = round(min(100, 80 + (level - 26) * 1.4), 1)
    
    # 计算 Power
    power = calculate_power(intimacy_x, emotion, chaos, pure)
    
    # 获取阶段
    stage = get_stage(int(intimacy_x))
    
    # 获取解锁功能
    unlocked = get_unlocked_features(level)
    next_lvl, next_unlocks = get_next_unlocks(level)
    
    return {
        "user_id": user_id,
        "character_id": character_id,
        "character_name": char_config.name if char_config else "Unknown",
        "archetype": archetype,
        "level": level,
        "xp": xp,
        "intimacy_x": intimacy_x,
        "emotion": emotion,
        "stage": stage.value,
        "stage_name": STAGE_NAMES.get(stage, "Unknown"),
        "power": round(power, 1),
        "chaos": chaos,
        "pure": pure,
        "events": events,
        "unlocked_features": unlocked,
        "next_unlock_level": next_lvl,
        "next_unlocks": next_unlocks,
    }

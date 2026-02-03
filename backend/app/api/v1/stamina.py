"""
Stamina API - 体力系统端点
==========================

提供体力查询和购买功能。

Author: Claude
Date: February 2025
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.stamina_service import (
    stamina_service,
    DAILY_FREE_STAMINA,
    STAMINA_PURCHASE_PRICE,
    STAMINA_PURCHASE_AMOUNT,
)
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stamina", tags=["stamina"])


# ==================== Schemas ====================

class StaminaStatusResponse(BaseModel):
    """体力状态响应"""
    current_stamina: int = Field(..., description="当前体力")
    max_stamina: int = Field(..., description="每日最大免费体力")
    last_reset_at: str = Field(..., description="上次重置时间 (ISO format)")
    needs_purchase: bool = Field(..., description="是否需要购买体力")
    
    # 购买信息
    purchase_price: int = Field(default=STAMINA_PURCHASE_PRICE, description="购买价格（月石）")
    purchase_amount: int = Field(default=STAMINA_PURCHASE_AMOUNT, description="购买获得的体力")


class BuyStaminaRequest(BaseModel):
    """购买体力请求"""
    packs: int = Field(default=1, ge=1, le=10, description="购买包数（1-10）")


class BuyStaminaResponse(BaseModel):
    """购买体力响应"""
    success: bool
    stamina_added: Optional[int] = None
    moonstone_spent: Optional[int] = None
    current_stamina: Optional[int] = None
    moonstone_balance: Optional[float] = None
    error: Optional[str] = None


class StaminaConfigResponse(BaseModel):
    """体力系统配置"""
    daily_free_stamina: int = DAILY_FREE_STAMINA
    cost_per_message: int = 1
    purchase_price: int = STAMINA_PURCHASE_PRICE
    purchase_amount: int = STAMINA_PURCHASE_AMOUNT


# ==================== Endpoints ====================

@router.get("", response_model=StaminaStatusResponse)
async def get_stamina(user=Depends(get_current_user)):
    """
    获取当前体力状态
    
    自动检查并应用每日重置。
    """
    user_id = str(user.user_id) if hasattr(user, 'user_id') else str(user.get('user_id'))
    
    try:
        result = await stamina_service.get_stamina(user_id)
        return StaminaStatusResponse(
            current_stamina=result["current_stamina"],
            max_stamina=result["max_stamina"],
            last_reset_at=result["last_reset_at"],
            needs_purchase=result["needs_purchase"],
        )
    except Exception as e:
        logger.error(f"Error getting stamina: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取体力状态失败",
        )


@router.post("/buy", response_model=BuyStaminaResponse)
async def buy_stamina(
    request: BuyStaminaRequest,
    user=Depends(get_current_user),
):
    """
    用月石购买体力
    
    价格: 10 月石 = 10 体力
    """
    user_id = str(user.user_id) if hasattr(user, 'user_id') else str(user.get('user_id'))
    
    try:
        result = await stamina_service.buy_stamina(user_id, request.packs)
        
        if not result["success"]:
            # 返回错误但不抛异常（让前端处理）
            return BuyStaminaResponse(
                success=False,
                error=result.get("error", "购买失败"),
            )
        
        return BuyStaminaResponse(
            success=True,
            stamina_added=result["stamina_added"],
            moonstone_spent=result["moonstone_spent"],
            current_stamina=result["current_stamina"],
            moonstone_balance=result["moonstone_balance"],
        )
        
    except Exception as e:
        logger.error(f"Error buying stamina: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="购买体力失败",
        )


@router.get("/config", response_model=StaminaConfigResponse)
async def get_stamina_config():
    """
    获取体力系统配置（公开接口）
    """
    return StaminaConfigResponse()

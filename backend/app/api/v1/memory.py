"""
Memory API - /api/v1/memory/{character_id}
==========================================

前端 CRUD 接口，后端 LLM 自动提取写入。

GET    /memory/{character_id}              → 获取所有记忆
POST   /memory/{character_id}              → 手动新增记忆
PATCH  /memory/{character_id}/{memory_id} → 编辑记忆
DELETE /memory/{character_id}/{memory_id} → 删除记忆
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services import user_memory_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])


# ─── 请求/响应模型 ─────────────────────────────────────────────────────────────

class CreateMemoryRequest(BaseModel):
    category:   str = Field(..., description="preference | opinion | date | profile")
    title:      str = Field(..., max_length=128, description="简短标签，如 '喜欢黑咖啡'")
    content:    str = Field(..., description="完整记忆内容")
    importance: Optional[int] = Field(2, ge=1, le=3, description="1=低 2=中 3=高")


class UpdateMemoryRequest(BaseModel):
    category:   Optional[str] = None
    title:      Optional[str] = Field(None, max_length=128)
    content:    Optional[str] = None
    importance: Optional[int] = Field(None, ge=1, le=3)


# ─── 工具函数 ──────────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "user_id"):
        return str(user.user_id)
    return request.headers.get("X-User-ID", "demo-user-123")


# ─── 路由 ──────────────────────────────────────────────────────────────────────

@router.get("/{character_id}", summary="获取用户记忆列表")
async def get_memories(character_id: str, req: Request):
    """
    获取当前用户对指定角色的所有记忆，按 importance desc, created_at desc 排序。
    """
    user_id = _get_user_id(req)
    memories = await svc.get_memories(user_id, character_id)
    return {"memories": memories, "total": len(memories)}


@router.post("/{character_id}", summary="手动新增记忆", status_code=201)
async def create_memory(
    character_id: str,
    body: CreateMemoryRequest,
    req: Request,
):
    """
    手动新增一条记忆。source 固定为 "manual"。

    需要有效订阅（basic 及以上），且未超出配额。
    """
    user_id = _get_user_id(req)

    # 检查订阅配额
    tier = await _get_user_tier(user_id)
    limit = svc.get_memory_limit(tier)
    if limit == 0:
        raise HTTPException(status_code=403, detail="Subscription required to add memories")

    current = await svc.count_memories(user_id, character_id)
    if current >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Memory limit reached ({current}/{limit}). Upgrade to add more."
        )

    try:
        mem = await svc.create_memory(
            user_id=user_id,
            character_id=character_id,
            category=body.category,
            title=body.title,
            content=body.content,
            importance=body.importance or 2,
            source="manual",
        )
        return mem
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{character_id}/{memory_id}", summary="编辑记忆")
async def update_memory(
    character_id: str,
    memory_id: str,
    body: UpdateMemoryRequest,
    req: Request,
):
    """部分更新指定记忆（仅允许修改 category / title / content / importance）。"""
    user_id = _get_user_id(req)
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    mem = await svc.update_memory(user_id, character_id, memory_id, patch)
    if mem is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem


@router.delete("/{character_id}/{memory_id}", status_code=204, summary="删除记忆")
async def delete_memory(
    character_id: str,
    memory_id: str,
    req: Request,
):
    """删除指定记忆。"""
    user_id = _get_user_id(req)
    deleted = await svc.delete_memory(user_id, character_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    # 204 No Content


# ─── 辅助：获取用户订阅等级 ────────────────────────────────────────────────────

async def _get_user_tier(user_id: str) -> str:
    """获取用户有效订阅等级，失败时降级到 free。"""
    try:
        from app.services.subscription_service import subscription_service
        return await subscription_service.get_effective_tier(user_id)
    except Exception as e:
        logger.warning(f"Failed to get tier for {user_id}: {e}")
        return "free"

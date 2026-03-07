"""
User Memory Service
===================

管理用户记忆的 CRUD 操作，以及 LLM 自动提取。

记忆四分类：
  preference  喜好（食物、音乐、活动等）
  opinion     观点（对某事的看法、价值观）
  date        约会记忆（两人共同经历的事）
  profile     个人档案（姓名、职业、生日等基本信息）

订阅配额：
  free    → 0 条（不存储，仅供展示用）
  basic   → 20 条
  premium → 无限制
"""

import json
import logging
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.models.database.user_memory_models import UserMemory

logger = logging.getLogger(__name__)

# ─── 订阅配额 ─────────────────────────────────────────────────────────────────
MEMORY_LIMITS: Dict[str, int] = {
    "free":    0,
    "basic":   20,
    "premium": 999_999,  # 实际无限制
}

VALID_CATEGORIES = {"preference", "opinion", "date", "profile"}


def get_memory_limit(tier: str) -> int:
    return MEMORY_LIMITS.get(tier, 0)


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def get_memories(user_id: str, character_id: str) -> List[dict]:
    """获取用户对某个角色的所有记忆，按 importance desc, created_at desc 排序"""
    from sqlalchemy import select
    try:
        async with get_db() as db:
            result = await db.execute(
                select(UserMemory)
                .where(
                    UserMemory.user_id == user_id,
                    UserMemory.character_id == character_id,
                )
                .order_by(UserMemory.importance.desc(), UserMemory.created_at.desc())
            )
            rows = result.scalars().all()
            return [r.to_dict() for r in rows]
    except Exception as e:
        logger.error(f"get_memories failed: {e}")
        return []


async def create_memory(
    user_id: str,
    character_id: str,
    category: str,
    title: str,
    content: str,
    importance: int = 2,
    source: str = "manual",
) -> Optional[dict]:
    """新增一条记忆（手动 or LLM 自动）"""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")
    if importance not in (1, 2, 3):
        importance = 2

    try:
        async with get_db() as db:
            mem = UserMemory(
                user_id=user_id,
                character_id=character_id,
                category=category,
                title=title[:128],
                content=content,
                source=source,
                importance=importance,
            )
            db.add(mem)
            await db.flush()   # 获取 id（commit 在 get_db context manager 里）
            await db.refresh(mem)
            return mem.to_dict()
    except Exception as e:
        logger.error(f"create_memory failed: {e}")
        raise


async def update_memory(
    user_id: str,
    character_id: str,
    memory_id: str,
    patch: Dict[str, Any],
) -> Optional[dict]:
    """更新记忆（部分字段）"""
    from sqlalchemy import select
    allowed = {"category", "title", "content", "importance"}
    try:
        async with get_db() as db:
            result = await db.execute(
                select(UserMemory).where(
                    UserMemory.id == memory_id,
                    UserMemory.user_id == user_id,
                    UserMemory.character_id == character_id,
                )
            )
            mem = result.scalar_one_or_none()
            if not mem:
                return None

            for field, val in patch.items():
                if field not in allowed:
                    continue
                if field == "category" and val not in VALID_CATEGORIES:
                    continue
                if field == "importance" and val not in (1, 2, 3):
                    continue
                setattr(mem, field, val)

            await db.flush()
            await db.refresh(mem)
            return mem.to_dict()
    except Exception as e:
        logger.error(f"update_memory failed: {e}")
        raise


async def delete_memory(user_id: str, character_id: str, memory_id: str) -> bool:
    """删除记忆，返回 True 表示删除成功"""
    from sqlalchemy import select
    try:
        async with get_db() as db:
            result = await db.execute(
                select(UserMemory).where(
                    UserMemory.id == memory_id,
                    UserMemory.user_id == user_id,
                    UserMemory.character_id == character_id,
                )
            )
            mem = result.scalar_one_or_none()
            if not mem:
                return False
            await db.delete(mem)
            return True
    except Exception as e:
        logger.error(f"delete_memory failed: {e}")
        raise


async def count_memories(user_id: str, character_id: str) -> int:
    """计算已有记忆数量"""
    from sqlalchemy import select, func
    try:
        async with get_db() as db:
            result = await db.execute(
                select(func.count()).select_from(UserMemory).where(
                    UserMemory.user_id == user_id,
                    UserMemory.character_id == character_id,
                )
            )
            return result.scalar() or 0
    except Exception:
        return 0


# ─── LLM 自动提取 ──────────────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """你是一个记忆提取助手。请分析用户消息和对话上下文，判断其中是否包含值得长期记住的用户信息。

记忆分为四类：
- preference（喜好）：用户喜欢或不喜欢的事物（食物、音乐、活动、颜色等）
- opinion（观点）：用户对某事的看法、价值观、信念
- date（约会记忆）：两人共同经历的特别时刻、约定、里程碑
- profile（个人档案）：用户的姓名、年龄、职业、居住地、家庭等基本信息

提取规则：
1. 只提取明确表达的信息，不要猜测或推断
2. 每条记忆要简洁有意义，title 不超过 20 字，content 不超过 100 字
3. importance：1=一般信息，2=值得记住，3=非常重要/核心信息
4. 如果没有值得提取的信息，返回空数组

输出格式（JSON数组，不要markdown代码块）：
[
  {
    "category": "preference",
    "title": "喜欢黑咖啡",
    "content": "用户喜欢喝不加糖的黑咖啡，尤其是早晨",
    "importance": 2
  }
]

如果没有可提取的信息，输出：[]
"""


async def extract_memories_from_chat(
    user_id: str,
    character_id: str,
    user_message: str,
    assistant_reply: str,
    tier: str = "free",
) -> List[dict]:
    """
    使用 LLM 从对话中提取记忆，并存入数据库。

    只有 basic 及以上用户才会执行提取。
    """
    limit = get_memory_limit(tier)
    if limit == 0:
        logger.debug(f"Memory extraction skipped: tier={tier} has no quota")
        return []

    # 检查配额
    current_count = await count_memories(user_id, character_id)
    if current_count >= limit:
        logger.debug(f"Memory extraction skipped: quota reached ({current_count}/{limit})")
        return []

    try:
        from app.services.llm_service import GrokService
        grok = GrokService()

        user_content = (
            f"用户消息：{user_message}\n"
            f"AI回复：{assistant_reply}\n\n"
            "请提取其中值得记住的用户信息（JSON数组）。"
        )

        response = await grok.chat_completion(
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        raw = response["choices"][0]["message"]["content"].strip()

        # 解析 JSON
        extracted: List[dict] = _parse_extraction(raw)
        if not extracted:
            logger.debug("Memory extraction: nothing extracted")
            return []

        saved = []
        remaining_quota = limit - current_count

        for item in extracted[:remaining_quota]:
            cat   = item.get("category", "")
            title = item.get("title", "").strip()
            content = item.get("content", "").strip()
            imp   = int(item.get("importance", 2))

            if not title or not content or cat not in VALID_CATEGORIES:
                continue

            # 检查是否已有相同 title（避免重复）
            if await _memory_title_exists(user_id, character_id, title):
                logger.debug(f"Memory skip duplicate title: {title}")
                continue

            try:
                mem = await create_memory(
                    user_id=user_id,
                    character_id=character_id,
                    category=cat,
                    title=title,
                    content=content,
                    importance=imp,
                    source="auto",
                )
                saved.append(mem)
            except Exception as e:
                logger.warning(f"Failed to save extracted memory '{title}': {e}")

        if saved:
            logger.info(
                f"🧠 Auto-extracted {len(saved)} memories for user={user_id} "
                f"char={character_id}: {[m['title'] for m in saved]}"
            )

        return saved

    except Exception as e:
        logger.warning(f"Memory LLM extraction failed: {e}")
        return []


def _parse_extraction(raw: str) -> List[dict]:
    """安全地解析 LLM 输出的 JSON 数组"""
    # 去掉可能的 markdown 代码块
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "memories" in data:
            return data["memories"]
        return []
    except json.JSONDecodeError:
        logger.debug(f"Memory extraction: failed to parse JSON: {raw[:200]}")
        return []


async def _memory_title_exists(user_id: str, character_id: str, title: str) -> bool:
    """检查相同 title 的记忆是否已存在（简单去重）"""
    from sqlalchemy import select
    try:
        async with get_db() as db:
            result = await db.execute(
                select(UserMemory).where(
                    UserMemory.user_id == user_id,
                    UserMemory.character_id == character_id,
                    UserMemory.title == title,
                ).limit(1)
            )
            return result.scalar_one_or_none() is not None
    except Exception:
        return False

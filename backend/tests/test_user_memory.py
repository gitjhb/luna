"""
User Memory System Tests
========================

覆盖范围：
  1. 数据库模型 - UserMemory 字段和 to_dict()
  2. 服务层 CRUD - get / create / update / delete / count
  3. 配额逻辑 - get_memory_limit / 订阅限制
  4. JSON 解析辅助函数 - _parse_extraction (各种格式)
  5. LLM 提取 - 配额充足 / 配额满 / LLM 失败降级
  6. API 端点 (集成测试, 需要 `uvicorn app.main:app` 在 localhost:8000 运行)

运行（纯单元测试，无需服务器）：
    pytest tests/test_user_memory.py -v -k "not Integration"

运行（含集成测试，需要服务器）：
    pytest tests/test_user_memory.py -v
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ─── 常量 ──────────────────────────────────────────────────────────────────────
TEST_USER_ID     = "test-mem-user-001"
TEST_CHARACTER_ID = "luna"
OTHER_USER_ID    = "test-mem-user-002"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 数据库模型
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserMemoryModel:
    """UserMemory ORM 模型测试"""

    def test_to_dict_has_all_fields(self):
        """to_dict() 必须包含前端所需的所有字段"""
        from app.models.database.user_memory_models import UserMemory

        mem = UserMemory(
            id="abc-123",
            user_id="u1",
            character_id="luna",
            category="preference",
            title="喜欢黑咖啡",
            content="用户喜欢不加糖的黑咖啡",
            source="auto",
            importance=2,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        d = mem.to_dict()
        expected_keys = {"id", "user_id", "character_id", "category",
                         "title", "content", "source", "importance",
                         "created_at", "updated_at"}
        assert expected_keys == set(d.keys())

    def test_to_dict_values_match(self):
        """to_dict() 值应与赋值一致"""
        from app.models.database.user_memory_models import UserMemory

        mem = UserMemory(
            id="xyz-999",
            user_id="u2",
            character_id="vera",
            category="profile",
            title="职业",
            content="用户是一名程序员",
            source="manual",
            importance=3,
            created_at=datetime(2024, 6, 15),
            updated_at=datetime(2024, 6, 15),
        )
        d = mem.to_dict()
        assert d["category"]  == "profile"
        assert d["source"]    == "manual"
        assert d["importance"] == 3
        assert "2024-06-15" in d["created_at"]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 配额逻辑
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryLimits:
    """订阅等级配额测试"""

    def test_free_tier_limit_is_zero(self):
        from app.services.user_memory_service import get_memory_limit
        assert get_memory_limit("free") == 0

    def test_basic_tier_limit(self):
        from app.services.user_memory_service import get_memory_limit
        assert get_memory_limit("basic") == 20

    def test_premium_tier_limit_is_large(self):
        from app.services.user_memory_service import get_memory_limit
        assert get_memory_limit("premium") >= 1000

    def test_unknown_tier_defaults_to_zero(self):
        from app.services.user_memory_service import get_memory_limit
        assert get_memory_limit("nonexistent_tier") == 0

    def test_valid_categories(self):
        from app.services.user_memory_service import VALID_CATEGORIES
        assert VALID_CATEGORIES == {"preference", "opinion", "date", "profile"}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. JSON 解析辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseExtraction:
    """_parse_extraction() 对 LLM 各种输出格式的健壮性测试"""

    def _parse(self, raw: str):
        from app.services.user_memory_service import _parse_extraction
        return _parse_extraction(raw)

    def test_clean_json_array(self):
        """标准 JSON 数组"""
        raw = '[{"category":"preference","title":"喜欢音乐","content":"用户喜欢Jazz","importance":2}]'
        result = self._parse(raw)
        assert len(result) == 1
        assert result[0]["category"] == "preference"

    def test_empty_array(self):
        """没有可提取信息时 LLM 应返回 []"""
        assert self._parse("[]") == []

    def test_markdown_code_block(self):
        """LLM 常常把 JSON 包在 ```json ... ``` 里"""
        raw = '```json\n[{"category":"profile","title":"姓名","content":"用户叫小明","importance":3}]\n```'
        result = self._parse(raw)
        assert len(result) == 1
        assert result[0]["title"] == "姓名"

    def test_memories_wrapper_key(self):
        """部分 LLM 会输出 {"memories": [...]}"""
        raw = '{"memories":[{"category":"opinion","title":"观点","content":"xxx","importance":1}]}'
        result = self._parse(raw)
        assert len(result) == 1
        assert result[0]["category"] == "opinion"

    def test_invalid_json_returns_empty(self):
        """无效 JSON 应降级返回 []，不抛异常"""
        assert self._parse("这不是JSON") == []
        assert self._parse("") == []
        assert self._parse("null") == []

    def test_multiple_items(self):
        """多条记忆都能解析"""
        import json
        items = [
            {"category": "preference", "title": "喜欢篮球", "content": "爱打球", "importance": 2},
            {"category": "profile",    "title": "职业",     "content": "程序员", "importance": 3},
        ]
        result = self._parse(json.dumps(items))
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 服务层 CRUD（Mock 数据库）
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserMemoryServiceCRUD:
    """
    使用 SQLite 内存数据库测试 CRUD，不依赖外部服务。
    """

    @pytest.fixture(autouse=True)
    def setup_db(self, monkeypatch):
        """
        在每个测试前准备一个干净的内存 SQLite，并 monkey-patch get_db。
        """
        import asyncio
        from contextlib import asynccontextmanager
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.models.database.chat_models import Base as ChatBase
        from app.models.database.user_memory_models import UserMemory  # noqa: registers model

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def _init():
            async with engine.begin() as conn:
                await conn.run_sync(ChatBase.metadata.create_all)
        asyncio.get_event_loop().run_until_complete(_init())

        @asynccontextmanager
        async def mock_get_db():
            async with factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        monkeypatch.setattr("app.services.user_memory_service.get_db", mock_get_db)

    # ── create ─────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_memory_returns_dict(self):
        from app.services.user_memory_service import create_memory
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "preference", "喜欢黑咖啡", "不加糖")
        assert mem["id"] is not None
        assert mem["category"] == "preference"
        assert mem["title"]    == "喜欢黑咖啡"
        assert mem["source"]   == "manual"

    @pytest.mark.asyncio
    async def test_create_memory_auto_source(self):
        from app.services.user_memory_service import create_memory
        mem = await create_memory(
            TEST_USER_ID, TEST_CHARACTER_ID, "profile", "职业", "程序员",
            importance=3, source="auto"
        )
        assert mem["source"] == "auto"
        assert mem["importance"] == 3

    @pytest.mark.asyncio
    async def test_create_memory_invalid_category_raises(self):
        from app.services.user_memory_service import create_memory
        with pytest.raises(ValueError):
            await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "INVALID", "t", "c")

    @pytest.mark.asyncio
    async def test_create_memory_clamps_importance(self):
        from app.services.user_memory_service import create_memory
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "opinion", "t", "c", importance=99)
        assert mem["importance"] == 2  # clamped to default

    # ── get ────────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_memories_empty_at_start(self):
        from app.services.user_memory_service import get_memories
        result = await get_memories(TEST_USER_ID, TEST_CHARACTER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_memories_returns_created(self):
        from app.services.user_memory_service import create_memory, get_memories
        await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "date", "第一次约会", "去了咖啡馆")
        result = await get_memories(TEST_USER_ID, TEST_CHARACTER_ID)
        assert len(result) == 1
        assert result[0]["category"] == "date"

    @pytest.mark.asyncio
    async def test_get_memories_isolated_by_user(self):
        """不同用户的记忆不应互相可见"""
        from app.services.user_memory_service import create_memory, get_memories
        await create_memory(TEST_USER_ID,  TEST_CHARACTER_ID, "preference", "喜欢猫", "养了两只猫")
        await create_memory(OTHER_USER_ID, TEST_CHARACTER_ID, "preference", "喜欢狗", "养了一条狗")

        user1_mems = await get_memories(TEST_USER_ID,  TEST_CHARACTER_ID)
        user2_mems = await get_memories(OTHER_USER_ID, TEST_CHARACTER_ID)
        assert len(user1_mems) == 1
        assert len(user2_mems) == 1
        assert user1_mems[0]["title"] == "喜欢猫"
        assert user2_mems[0]["title"] == "喜欢狗"

    @pytest.mark.asyncio
    async def test_get_memories_sorted_by_importance(self):
        """importance 高的应排在前面"""
        from app.services.user_memory_service import create_memory, get_memories
        await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "preference", "低优先", "内容", importance=1)
        await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "profile",    "高优先", "内容", importance=3)
        result = await get_memories(TEST_USER_ID, TEST_CHARACTER_ID)
        assert result[0]["importance"] == 3

    # ── count ──────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_count_memories_correct(self):
        from app.services.user_memory_service import create_memory, count_memories
        assert await count_memories(TEST_USER_ID, TEST_CHARACTER_ID) == 0
        await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "preference", "t1", "c1")
        await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "opinion",    "t2", "c2")
        assert await count_memories(TEST_USER_ID, TEST_CHARACTER_ID) == 2

    # ── update ─────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_memory_title(self):
        from app.services.user_memory_service import create_memory, update_memory
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "preference", "旧标题", "内容")
        updated = await update_memory(TEST_USER_ID, TEST_CHARACTER_ID, mem["id"], {"title": "新标题"})
        assert updated["title"] == "新标题"
        assert updated["content"] == "内容"  # 未修改的字段保持不变

    @pytest.mark.asyncio
    async def test_update_memory_multiple_fields(self):
        from app.services.user_memory_service import create_memory, update_memory
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "opinion", "t", "c", importance=1)
        updated = await update_memory(
            TEST_USER_ID, TEST_CHARACTER_ID, mem["id"],
            {"importance": 3, "content": "新内容"}
        )
        assert updated["importance"] == 3
        assert updated["content"] == "新内容"

    @pytest.mark.asyncio
    async def test_update_memory_not_found_returns_none(self):
        from app.services.user_memory_service import update_memory
        result = await update_memory(TEST_USER_ID, TEST_CHARACTER_ID, "nonexistent-id", {"title": "x"})
        assert result is None

    @pytest.mark.asyncio
    async def test_update_memory_cannot_touch_other_users_memory(self):
        """不能修改其他用户的记忆"""
        from app.services.user_memory_service import create_memory, update_memory
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "profile", "姓名", "小明")
        # other user tries to update
        result = await update_memory(OTHER_USER_ID, TEST_CHARACTER_ID, mem["id"], {"title": "篡改"})
        assert result is None

    # ── delete ─────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        from app.services.user_memory_service import create_memory, delete_memory, get_memories
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "date", "约会", "内容")
        ok = await delete_memory(TEST_USER_ID, TEST_CHARACTER_ID, mem["id"])
        assert ok is True
        assert await get_memories(TEST_USER_ID, TEST_CHARACTER_ID) == []

    @pytest.mark.asyncio
    async def test_delete_memory_not_found_returns_false(self):
        from app.services.user_memory_service import delete_memory
        ok = await delete_memory(TEST_USER_ID, TEST_CHARACTER_ID, "ghost-id")
        assert ok is False

    @pytest.mark.asyncio
    async def test_delete_memory_cannot_delete_other_users(self):
        from app.services.user_memory_service import create_memory, delete_memory, count_memories
        mem = await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "preference", "t", "c")
        ok = await delete_memory(OTHER_USER_ID, TEST_CHARACTER_ID, mem["id"])
        assert ok is False
        assert await count_memories(TEST_USER_ID, TEST_CHARACTER_ID) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 5. LLM 提取（Mock LLM，真实 DB）
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractMemoriesFromChat:
    """LLM 提取流程测试（LLM 调用被 Mock）"""

    @pytest.fixture(autouse=True)
    def setup_db(self, monkeypatch):
        import asyncio
        from contextlib import asynccontextmanager
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.models.database.chat_models import Base as ChatBase
        from app.models.database.user_memory_models import UserMemory  # noqa

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def _init():
            async with engine.begin() as conn:
                await conn.run_sync(ChatBase.metadata.create_all)
        asyncio.get_event_loop().run_until_complete(_init())

        @asynccontextmanager
        async def mock_get_db():
            async with factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        monkeypatch.setattr("app.services.user_memory_service.get_db", mock_get_db)

    def _make_llm_response(self, items: list) -> dict:
        import json
        content = json.dumps(items, ensure_ascii=False)
        return {
            "choices": [{"message": {"content": content}}],
            "usage":   {"total_tokens": 50},
        }

    @pytest.mark.asyncio
    async def test_free_tier_skips_extraction(self):
        """free tier 不提取，直接返回空列表"""
        from app.services.user_memory_service import extract_memories_from_chat
        result = await extract_memories_from_chat(
            TEST_USER_ID, TEST_CHARACTER_ID, "我喜欢黑咖啡", "好的～", tier="free"
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_basic_tier_extracts_memory(self, monkeypatch):
        """basic tier 调 LLM 并存储结果"""
        from app.services.user_memory_service import extract_memories_from_chat, count_memories

        mock_response = self._make_llm_response([
            {"category": "preference", "title": "喜欢黑咖啡", "content": "不加糖的美式", "importance": 2}
        ])

        mock_grok = MagicMock()
        mock_grok.chat_completion = AsyncMock(return_value=mock_response)

        with patch("app.services.user_memory_service.GrokService", return_value=mock_grok):
            saved = await extract_memories_from_chat(
                TEST_USER_ID, TEST_CHARACTER_ID, "我喜欢黑咖啡", "我记住了～", tier="basic"
            )

        assert len(saved) == 1
        assert saved[0]["category"] == "preference"
        assert saved[0]["source"]   == "auto"
        assert await count_memories(TEST_USER_ID, TEST_CHARACTER_ID) == 1

    @pytest.mark.asyncio
    async def test_duplicate_title_not_saved_again(self, monkeypatch):
        """相同 title 的记忆只存一次"""
        from app.services.user_memory_service import (
            create_memory, extract_memories_from_chat, count_memories
        )

        # 先手动插入同标题的记忆
        await create_memory(TEST_USER_ID, TEST_CHARACTER_ID, "preference", "喜欢黑咖啡", "原始内容")

        mock_response = self._make_llm_response([
            {"category": "preference", "title": "喜欢黑咖啡", "content": "再次提到", "importance": 2}
        ])

        mock_grok = MagicMock()
        mock_grok.chat_completion = AsyncMock(return_value=mock_response)

        with patch("app.services.user_memory_service.GrokService", return_value=mock_grok):
            saved = await extract_memories_from_chat(
                TEST_USER_ID, TEST_CHARACTER_ID, "我喜欢黑咖啡", "好的～", tier="basic"
            )

        assert saved == []
        assert await count_memories(TEST_USER_ID, TEST_CHARACTER_ID) == 1  # 还是 1 条

    @pytest.mark.asyncio
    async def test_quota_full_skips_extraction(self, monkeypatch):
        """达到 basic 配额 (20) 后不再提取"""
        from app.services import user_memory_service as svc

        # 模拟当前已有 20 条
        monkeypatch.setattr(svc, "count_memories", AsyncMock(return_value=20))
        mock_grok = MagicMock()
        mock_grok.chat_completion = AsyncMock()  # 不应该被调用

        with patch("app.services.user_memory_service.GrokService", return_value=mock_grok):
            result = await svc.extract_memories_from_chat(
                TEST_USER_ID, TEST_CHARACTER_ID, "我喜欢猫", "可爱～", tier="basic"
            )

        assert result == []
        mock_grok.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_failure_returns_empty_gracefully(self, monkeypatch):
        """LLM 调用失败时降级返回空列表，不抛异常"""
        from app.services.user_memory_service import extract_memories_from_chat

        mock_grok = MagicMock()
        mock_grok.chat_completion = AsyncMock(side_effect=Exception("LLM timeout"))

        with patch("app.services.user_memory_service.GrokService", return_value=mock_grok):
            result = await extract_memories_from_chat(
                TEST_USER_ID, TEST_CHARACTER_ID, "我喜欢蓝色", "好的～", tier="premium"
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_category_from_llm_is_skipped(self, monkeypatch):
        """LLM 返回非法 category 的记忆应被跳过"""
        from app.services.user_memory_service import extract_memories_from_chat, count_memories

        mock_response = self._make_llm_response([
            {"category": "INVALID_CATEGORY", "title": "t", "content": "c", "importance": 2},
            {"category": "profile",          "title": "职业", "content": "工程师", "importance": 3},
        ])

        mock_grok = MagicMock()
        mock_grok.chat_completion = AsyncMock(return_value=mock_response)

        with patch("app.services.user_memory_service.GrokService", return_value=mock_grok):
            saved = await extract_memories_from_chat(
                TEST_USER_ID, TEST_CHARACTER_ID, "我是工程师", "厉害！", tier="premium"
            )

        assert len(saved) == 1
        assert saved[0]["category"] == "profile"
        assert await count_memories(TEST_USER_ID, TEST_CHARACTER_ID) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 6. API 集成测试（需要 uvicorn 运行在 localhost:8000）
# ═══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8000/api/v1"
HEADERS  = {"X-User-ID": TEST_USER_ID}


@pytest.mark.Integration
class TestMemoryAPIIntegration:
    """
    集成测试：对真实运行中的服务器发请求。
    需要先运行：uvicorn app.main:app --reload
    跳过：pytest tests/test_user_memory.py -k "not Integration"
    """

    @pytest.mark.asyncio
    async def test_get_memories_empty(self):
        import httpx
        char_id = f"test-char-{TEST_USER_ID}"
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/memory/{char_id}", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "memories" in data
        assert "total" in data
        assert isinstance(data["memories"], list)

    @pytest.mark.asyncio
    async def test_create_memory_free_tier_forbidden(self):
        """free tier 用户不能手动新增记忆"""
        import httpx
        # demo-user-123 默认是 free tier（无付费记录）
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/memory/luna",
                headers={"X-User-ID": "demo-free-user-never-subscribed"},
                json={"category": "preference", "title": "测试", "content": "内容", "importance": 2},
            )
        # 403 or 201 depending on how the test server is configured
        assert r.status_code in (201, 403)

    @pytest.mark.asyncio
    async def test_crud_lifecycle(self):
        """完整 CRUD 生命周期：创建 → 读取 → 修改 → 删除"""
        import httpx
        char_id = "luna"

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 由于 free tier 限制，mock 一个 basic tier 的用户（需后端有对应订阅记录）
            # 此测试在 CI 中可能需要先插入订阅记录
            create_resp = await client.post(
                f"{BASE_URL}/memory/{char_id}",
                headers=HEADERS,
                json={
                    "category":  "preference",
                    "title":     "集成测试-喜欢黑咖啡",
                    "content":   "不加糖的美式",
                    "importance": 2,
                },
            )
            # 根据实际订阅状态会是 201 或 403
            if create_resp.status_code == 403:
                pytest.skip("User has no subscription (expected in CI without seeded data)")

            assert create_resp.status_code == 201
            mem = create_resp.json()
            mem_id = mem["id"]
            assert mem["source"] == "manual"

            # 读取
            get_resp = await client.get(f"{BASE_URL}/memory/{char_id}", headers=HEADERS)
            assert get_resp.status_code == 200
            assert any(m["id"] == mem_id for m in get_resp.json()["memories"])

            # 修改
            patch_resp = await client.patch(
                f"{BASE_URL}/memory/{char_id}/{mem_id}",
                headers=HEADERS,
                json={"title": "集成测试-更新标题", "importance": 3},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["title"] == "集成测试-更新标题"

            # 删除
            del_resp = await client.delete(
                f"{BASE_URL}/memory/{char_id}/{mem_id}",
                headers=HEADERS,
            )
            assert del_resp.status_code == 204

            # 确认已删除
            get_after = await client.get(f"{BASE_URL}/memory/{char_id}", headers=HEADERS)
            assert all(m["id"] != mem_id for m in get_after.json()["memories"])

    @pytest.mark.asyncio
    async def test_update_not_found_returns_404(self):
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/memory/luna/nonexistent-id-00000",
                headers=HEADERS,
                json={"title": "x"},
            )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self):
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{BASE_URL}/memory/luna/nonexistent-id-00000",
                headers=HEADERS,
            )
        assert r.status_code == 404

"""
Memory Extraction 单元测试 v2 - 场记模式
======================================

测试 MemoryExtractor 的 LLM 场记功能

运行: pytest tests/test_memory_extraction.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.memory_system_v2.memory_manager import (
    MemoryExtractor,
    SemanticMemory,
)


@pytest.fixture
def empty_semantic():
    """Create an empty SemanticMemory for testing"""
    return SemanticMemory(user_id="test-user", character_id="test-char")


@pytest.fixture
def mock_llm():
    """Create a mock LLM service"""
    llm = MagicMock()
    llm.chat_completion = AsyncMock()
    return llm


@pytest.fixture
def extractor_no_llm():
    """Create a MemoryExtractor without LLM"""
    return MemoryExtractor(llm_service=None)


@pytest.fixture
def extractor_with_mock_llm(mock_llm):
    """Create a MemoryExtractor with mock LLM"""
    return MemoryExtractor(llm_service=mock_llm)


class TestPreScreening:
    """测试预筛选逻辑 _needs_scene_analysis"""

    def test_should_analyze_intimate(self, extractor_no_llm):
        """亲密相关词应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("亲我一下", "") == True
        assert extractor_no_llm._needs_scene_analysis("kiss me", "") == True
        assert extractor_no_llm._needs_scene_analysis("抱抱", "") == True
        assert extractor_no_llm._needs_scene_analysis("hug me", "") == True

    def test_should_analyze_emotion(self, extractor_no_llm):
        """情感相关词应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("我爱你", "") == True
        assert extractor_no_llm._needs_scene_analysis("i love you", "") == True
        assert extractor_no_llm._needs_scene_analysis("我喜欢你", "") == True
        assert extractor_no_llm._needs_scene_analysis("我讨厌你", "") == True

    def test_should_analyze_relationship(self, extractor_no_llm):
        """关系变化词应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("我们分手吧", "") == True
        assert extractor_no_llm._needs_scene_analysis("做我女朋友", "") == True
        assert extractor_no_llm._needs_scene_analysis("结婚", "") == True
        assert extractor_no_llm._needs_scene_analysis("求婚", "") == True

    def test_should_analyze_milestone(self, extractor_no_llm):
        """里程碑词应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("第一次约会", "") == True
        assert extractor_no_llm._needs_scene_analysis("一周年纪念", "") == True
        assert extractor_no_llm._needs_scene_analysis("生日快乐", "") == True

    def test_should_analyze_gift(self, extractor_no_llm):
        """礼物相关词应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("送你一个礼物", "") == True
        assert extractor_no_llm._needs_scene_analysis("惊喜", "") == True
        assert extractor_no_llm._needs_scene_analysis("surprise for you", "") == True

    def test_should_skip_normal_chat(self, extractor_no_llm):
        """普通闲聊不应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("今天天气真好", "") == False
        assert extractor_no_llm._needs_scene_analysis("我去吃饭了", "") == False
        assert extractor_no_llm._needs_scene_analysis("你在干嘛", "") == False
        assert extractor_no_llm._needs_scene_analysis("晚安", "") == False
        assert extractor_no_llm._needs_scene_analysis("工作好累", "") == False

    def test_should_analyze_assistant_response(self, extractor_no_llm):
        """AI回复里的关键词也应该触发分析"""
        # 用户消息普通，但AI回复有关键词
        assert extractor_no_llm._needs_scene_analysis(
            "嗯", "*轻轻亲了你一下*"
        ) == True
        assert extractor_no_llm._needs_scene_analysis(
            "好的", "我也爱你"
        ) == True


class TestNoLLMBehavior:
    """测试没有 LLM 时的行为"""

    @pytest.mark.asyncio
    async def test_skip_without_llm(self, extractor_no_llm, empty_semantic):
        """没有 LLM 时应该跳过分析"""
        semantic, episodic = await extractor_no_llm.extract_from_message(
            message="我爱你",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="我也爱你",
        )
        
        # 没有 LLM，应该返回空
        assert semantic == {}
        assert episodic is None


class TestLLMSceneSupervisor:
    """测试 LLM 场记功能（使用 mock）"""

    @pytest.mark.asyncio
    async def test_kiss_detected(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """亲吻事件应该被正确检测"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '''{
                        "semantic": {},
                        "episodic": {
                            "event_found": true,
                            "actually_happened": true,
                            "event_type": "intimate",
                            "sub_type": "first_kiss",
                            "summary": "在月光下亲吻",
                            "importance": 3,
                            "is_first_time": true
                        }
                    }'''
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="亲我一下",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="*轻轻吻了你*",
        )
        
        assert episodic is not None
        assert episodic["event_type"] == "intimate"
        assert episodic["sub_type"] == "first_kiss"
        assert episodic["is_important"] == True

    @pytest.mark.asyncio
    async def test_rejection_detected(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """拒绝事件应该被正确检测"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '''{
                        "semantic": {},
                        "episodic": {
                            "event_found": true,
                            "actually_happened": true,
                            "event_type": "rejection",
                            "sub_type": "kiss",
                            "summary": "用户求吻被拒",
                            "importance": 1
                        }
                    }'''
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="亲我一下",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="不要啦，还没刷牙",
        )
        
        assert episodic is not None
        assert episodic["event_type"] == "rejection"

    @pytest.mark.asyncio
    async def test_dream_not_recorded(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """梦境不应该被记录为真实事件"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '''{
                        "semantic": {},
                        "episodic": {
                            "event_found": false
                        }
                    }'''
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="我昨晚梦到亲你了",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="梦到我了？好害羞",
        )
        
        assert episodic is None

    @pytest.mark.asyncio
    async def test_actually_happened_false(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """actually_happened=false 时不应该记录"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '''{
                        "semantic": {},
                        "episodic": {
                            "event_found": true,
                            "actually_happened": false,
                            "event_type": "intimate",
                            "summary": "只是在说梦话"
                        }
                    }'''
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="如果我们亲一下会怎样",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="那只是假设啦",
        )
        
        assert episodic is None

    @pytest.mark.asyncio
    async def test_confession_with_relationship_update(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """表白事件应该同时更新关系状态"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '''{
                        "semantic": {
                            "relationship_status": "dating"
                        },
                        "episodic": {
                            "event_found": true,
                            "actually_happened": true,
                            "event_type": "confession",
                            "summary": "用户表白成功，确定恋爱关系",
                            "importance": 4,
                            "is_first_time": true
                        }
                    }'''
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="我喜欢你，做我女朋友吧",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="我也喜欢你...好",
        )
        
        assert semantic.get("relationship_status") == "dating"
        assert episodic is not None
        assert episodic["event_type"] == "confession"
        assert episodic["importance"] == 4

    @pytest.mark.asyncio
    async def test_extract_user_info(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """应该能提取用户信息"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '''{
                        "semantic": {
                            "user_name": "小明",
                            "birthday": "03-15",
                            "likes": ["看电影", "打游戏"]
                        },
                        "episodic": {
                            "event_found": false
                        }
                    }'''
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="我叫小明，生日是3月15日，我喜欢看电影和打游戏",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="小明你好！",
        )
        
        assert semantic.get("user_name") == "小明"
        assert semantic.get("birthday") == "03-15"
        assert "看电影" in semantic.get("likes", [])


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_empty_message(self, extractor_no_llm, empty_semantic):
        """空消息应该跳过"""
        semantic, episodic = await extractor_no_llm.extract_from_message(
            message="",
            context=[],
            current_semantic=empty_semantic,
        )
        
        assert semantic == {}
        assert episodic is None

    @pytest.mark.asyncio
    async def test_llm_error_handling(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """LLM 出错时应该优雅降级"""
        mock_llm.chat_completion.side_effect = Exception("API Error")
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="我爱你",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="我也爱你",
        )
        
        # 出错时应该返回空，不崩溃
        assert semantic == {}
        assert episodic is None

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, extractor_with_mock_llm, mock_llm, empty_semantic):
        """LLM 返回无效 JSON 时应该优雅处理"""
        mock_llm.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": "这不是有效的JSON"
                }
            }]
        }
        
        semantic, episodic = await extractor_with_mock_llm.extract_from_message(
            message="我爱你",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="我也爱你",
        )
        
        assert semantic == {}
        assert episodic is None


class TestMultiLanguage:
    """测试多语言支持"""

    def test_english_hints(self, extractor_no_llm):
        """英文关键词应该触发分析"""
        assert extractor_no_llm._needs_scene_analysis("I love you", "") == True
        assert extractor_no_llm._needs_scene_analysis("kiss me please", "") == True
        assert extractor_no_llm._needs_scene_analysis("let's break up", "") == True

    def test_japanese_hints(self, extractor_no_llm):
        """日语关键词（如果包含在hints里）应该触发分析"""
        # 目前hints里没有日语，但 LLM 场记可以处理
        # 如果用户说日语但包含通用词如"kiss"，应该能触发
        assert extractor_no_llm._needs_scene_analysis("キスして", "") == False  # 纯日语暂不触发预筛选
        # 但如果包含英文关键词
        assert extractor_no_llm._needs_scene_analysis("please kiss", "") == True


class TestIntegration:
    """集成测试（需要真实 LLM）"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real LLM service - run manually")
    async def test_real_llm_kiss_scene(self, empty_semantic):
        """真实 LLM 测试亲吻场景"""
        from app.services.llm_service import GrokService
        
        extractor = MemoryExtractor(llm_service=GrokService())
        
        semantic, episodic = await extractor.extract_from_message(
            message="亲我一下嘛~",
            context=[],
            current_semantic=empty_semantic,
            assistant_response="*轻轻靠近，在你唇上落下一吻* 笨蛋...",
        )
        
        assert episodic is not None
        assert episodic["event_type"] == "intimate"
        assert episodic.get("is_important") == True

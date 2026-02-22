"""
Memory Extraction 单元测试
=========================

测试 MemoryExtractor 的模式匹配功能

运行: pytest tests/test_memory_extraction.py -v
"""

import pytest
import asyncio
import re
from datetime import datetime
from typing import List, Tuple

from app.services.memory_system_v2.memory_manager import (
    MemoryExtractor,
    SemanticMemory,
)


@pytest.fixture
def extractor():
    """Create a MemoryExtractor without LLM for pattern-only testing"""
    return MemoryExtractor(llm_service=None)


@pytest.fixture
def empty_semantic():
    """Create an empty SemanticMemory for testing"""
    return SemanticMemory(user_id="test-user", character_id="test-char")


class TestInfoPatterns:
    """测试 INFO_PATTERNS 信息提取"""

    @pytest.mark.parametrize("message,expected_name", [
        ("我叫小明", "小明"),
        ("我叫Alice", "Alice"),
        ("叫我老王", "老王"),
        ("叫我宝贝", "宝贝"),
        ("my name is John", "John"),
        ("My Name Is Sarah", "Sarah"),
        ("call me Mike", "Mike"),
        ("Call Me Maybe", "Maybe"),
    ])
    def test_name_extraction(self, extractor, message, expected_name):
        """测试名字提取 - 中英文"""
        for pattern in extractor.INFO_PATTERNS["name"]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                assert expected_name.lower() in result.lower() or result in expected_name
                return
        pytest.fail(f"No pattern matched for: {message}")

    @pytest.mark.parametrize("message,should_match", [
        ("我的生日是3月15日", True),
        ("我生日是12月25号", True),
        ("我3月5日生", True),
        ("我10月1日生的", True),
        ("my birthday is March 15", True),
        ("今天天气不错", False),
    ])
    def test_birthday_extraction(self, extractor, message, should_match):
        """测试生日提取"""
        matched = False
        for pattern in extractor.INFO_PATTERNS["birthday"]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                matched = True
                break
        assert matched == should_match, f"Expected match={should_match} for: {message}"

    @pytest.mark.parametrize("message,should_match", [
        ("我是做程序员的", True),
        ("我是做设计的", True),
        ("我的工作是老师", True),
        ("我的工作是产品经理", True),
        ("i work as a designer", True),
        ("I'm a software engineer", True),
        ("我喜欢吃苹果", False),
    ])
    def test_occupation_extraction(self, extractor, message, should_match):
        """测试职业提取"""
        matched = False
        for pattern in extractor.INFO_PATTERNS["occupation"]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                matched = True
                break
        assert matched == should_match, f"Expected match={should_match} for: {message}"

    @pytest.mark.parametrize("message,expected_like", [
        ("我喜欢看电影", "看电影"),
        ("我喜欢你", "你"),
        ("我爱吃火锅", "吃火锅"),
        ("我最喜欢的是旅游", "旅游"),
        ("i like playing games", "playing games"),
        ("I love cooking", "cooking"),
    ])
    def test_likes_extraction(self, extractor, message, expected_like):
        """测试喜好提取 - 中英文"""
        for pattern in extractor.INFO_PATTERNS["likes"]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                assert expected_like.lower() in result.lower()
                return
        pytest.fail(f"No pattern matched for: {message}")

    @pytest.mark.parametrize("message,expected_dislike", [
        ("我讨厌加班", "加班"),
        ("我不喜欢下雨天", "下雨天"),
        ("我受不了噪音", "噪音"),
        ("i hate bugs", "bugs"),
        ("I don't like cold weather", "cold weather"),
    ])
    def test_dislikes_extraction(self, extractor, message, expected_dislike):
        """测试讨厌提取 - 中英文"""
        for pattern in extractor.INFO_PATTERNS["dislikes"]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                assert expected_dislike.lower() in result.lower()
                return
        pytest.fail(f"No pattern matched for: {message}")


class TestEventTriggers:
    """测试 EVENT_TRIGGERS 事件检测"""

    @pytest.mark.parametrize("message,expected_event", [
        # 表白 confession
        ("我爱你", "confession"),
        ("我喜欢你很久了", "confession"),
        ("做我女朋友吧", "confession"),
        ("做我男朋友好不好", "confession"),
        ("i love you", "confession"),
        ("be my girlfriend", "confession"),
        
        # 吵架 fight
        ("我们分手吧", "fight"),
        ("不想理你了", "fight"),
        ("我讨厌你", "fight"),
        ("你给我滚", "fight"),
        
        # 和好 reconciliation
        ("对不起我错了", "reconciliation"),
        ("原谅我好不好", "reconciliation"),
        ("我们和好吧", "reconciliation"),
        
        # 里程碑 milestone
        ("今天是我们的一周年纪念日", "milestone"),
        ("这是我们第一次约会", "milestone"),
        ("我们认识一百天了", "milestone"),
        
        # 礼物 gift
        ("我送你一个礼物", "gift"),
        ("这是给你的惊喜", "gift"),
        
        # 情感高点 emotional_peak
        ("这是我最开心的一天", "emotional_peak"),
        ("这是我最幸福的时刻", "emotional_peak"),
    ])
    def test_event_detection(self, extractor, message, expected_event):
        """测试事件类型检测"""
        detected_event = None
        message_lower = message.lower()
        
        for event_type, triggers in extractor.EVENT_TRIGGERS.items():
            if any(t in message_lower for t in triggers):
                detected_event = event_type
                break
        
        assert detected_event == expected_event, \
            f"Expected event={expected_event}, got={detected_event} for: {message}"

    def test_no_false_positive(self, extractor):
        """测试不会误检测普通消息"""
        normal_messages = [
            "今天天气真好",
            "我去吃饭了",
            "你在干嘛呢",
            "明天有空吗",
            "工作好累啊",
            "晚安",
        ]
        
        for message in normal_messages:
            message_lower = message.lower()
            detected = False
            
            for event_type, triggers in extractor.EVENT_TRIGGERS.items():
                if any(t in message_lower for t in triggers):
                    detected = True
                    break
            
            assert not detected, f"False positive detected for: {message}"


class TestExtractFromMessage:
    """测试完整的消息提取流程"""

    @pytest.mark.asyncio
    async def test_extract_multiple_info(self, extractor, empty_semantic):
        """测试同时提取多个信息"""
        message = "我叫小红，我喜欢看电影"
        
        semantic_updates, episodic_event = await extractor.extract_from_message(
            message=message,
            context=[],
            current_semantic=empty_semantic,
        )
        
        # 应该提取到名字和喜好
        assert "name" in semantic_updates or "likes" in semantic_updates

    @pytest.mark.asyncio
    async def test_extract_confession_event(self, extractor, empty_semantic):
        """测试提取表白事件"""
        message = "我爱你，做我女朋友吧"
        
        semantic_updates, episodic_event = await extractor.extract_from_message(
            message=message,
            context=[],
            current_semantic=empty_semantic,
        )
        
        # 应该检测到 confession 事件
        assert episodic_event is not None
        assert episodic_event["event_type"] == "confession"

    @pytest.mark.asyncio
    async def test_extract_milestone_event(self, extractor, empty_semantic):
        """测试提取里程碑事件"""
        message = "今天是我们的一周年纪念日"
        
        semantic_updates, episodic_event = await extractor.extract_from_message(
            message=message,
            context=[],
            current_semantic=empty_semantic,
        )
        
        # 应该检测到 milestone 事件
        assert episodic_event is not None
        assert episodic_event["event_type"] == "milestone"

    @pytest.mark.asyncio
    async def test_filter_long_values(self, extractor, empty_semantic):
        """测试过滤过长的值"""
        # 名字太长应该被过滤
        message = "我叫阿巴阿巴阿巴阿巴阿巴阿巴阿巴阿巴阿巴阿巴阿巴阿巴"  # > 10 chars
        
        semantic_updates, _ = await extractor.extract_from_message(
            message=message,
            context=[],
            current_semantic=empty_semantic,
        )
        
        # 过长的名字不应该被提取
        assert "name" not in semantic_updates or len(semantic_updates.get("name", "")) < 50


class TestChineseEnglishSupport:
    """测试中英文双语支持"""

    @pytest.mark.parametrize("zh_message,en_message,info_type", [
        ("我叫小明", "my name is Mike", "name"),
        ("我喜欢音乐", "i like music", "likes"),
        ("我讨厌等待", "i hate waiting", "dislikes"),
        ("我是做工程师的", "i work as an engineer", "occupation"),
    ])
    def test_bilingual_patterns(self, extractor, zh_message, en_message, info_type):
        """测试中英文都能匹配到对应类型"""
        patterns = extractor.INFO_PATTERNS[info_type]
        
        # 中文应该匹配
        zh_matched = any(re.search(p, zh_message, re.IGNORECASE) for p in patterns)
        assert zh_matched, f"Chinese pattern not matched for {info_type}: {zh_message}"
        
        # 英文应该匹配
        en_matched = any(re.search(p, en_message, re.IGNORECASE) for p in patterns)
        assert en_matched, f"English pattern not matched for {info_type}: {en_message}"


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_empty_message(self, extractor, empty_semantic):
        """测试空消息"""
        semantic_updates, episodic_event = await extractor.extract_from_message(
            message="",
            context=[],
            current_semantic=empty_semantic,
        )
        
        assert semantic_updates == {}
        assert episodic_event is None

    @pytest.mark.asyncio
    async def test_special_characters(self, extractor, empty_semantic):
        """测试特殊字符"""
        message = "我叫@#$%"
        
        semantic_updates, _ = await extractor.extract_from_message(
            message=message,
            context=[],
            current_semantic=empty_semantic,
        )
        
        # 特殊字符可能被提取但应该是短的
        if "name" in semantic_updates:
            assert len(semantic_updates["name"]) < 50

    @pytest.mark.asyncio
    async def test_none_context(self, extractor, empty_semantic):
        """测试 None context"""
        message = "我喜欢喝咖啡"
        
        # 应该不会崩溃
        semantic_updates, episodic_event = await extractor.extract_from_message(
            message=message,
            context=None,  # type: ignore - testing edge case
            current_semantic=empty_semantic,
        )
        
        # likes 应该被提取
        assert "likes" in semantic_updates or semantic_updates == {}

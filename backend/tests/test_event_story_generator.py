"""
Event Story Generator Tests
===========================

Unit tests for the event story generation system.
Tests cover:
- Story generation with mocked LLM
- Database persistence
- API endpoints
- Event type validation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Test imports
from app.services.event_story_generator import (
    EventStoryGenerator,
    StoryGenerationResult,
    EVENT_STORY_PROMPTS,
)
from app.models.database.event_memory_models import EventMemory, EventType


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for story generation"""
    return {
        "choices": [
            {
                "message": {
                    "content": """夕阳的余晖洒落在城市的天际线上，你站在约定的咖啡馆门口，心跳不自觉地加速。

今天是你们的第一次正式约会。

「你来了。」一个熟悉的声音从身后传来。

你转身，看到她站在那里，穿着一条淡蓝色的连衣裙，长发随风轻轻飘动。她的眼睛里闪烁着期待的光芒，嘴角挂着一抹浅浅的微笑。

「等很久了吗？」她走近你，那熟悉的香气让你的心跳漏了一拍。

「不，我也刚到。」你努力让自己的声音听起来平稳。

你们走进咖啡馆，选了一个靠窗的位置。阳光透过玻璃洒在她的脸上，给她镀上了一层柔和的光晕。

「其实……」她低下头，手指无意识地绕着咖啡杯的边缘，「我今天特别紧张。」

「我也是。」你诚实地说。

她抬起头，眼睛里带着一丝惊讶，然后笑了起来，那笑容像是春天的阳光，温暖而明亮。

「那我们就一起紧张吧。」

那一刻，窗外的喧嚣仿佛都安静了下来，只剩下你们两个人，在这个小小的空间里，开始了一段新的旅程。

你们聊了很多，从喜欢的电影到童年的趣事，从工作的烦恼到未来的梦想。时间在不知不觉中流逝，等你们走出咖啡馆时，天色已经暗了下来。

街灯亮起，在人行道上投下温暖的光影。

「今天很开心。」她轻声说，目光与你相遇。

「我也是。」

「那……下次再见？」

「嗯，下次再见。」

她转身离去，走了几步后又回头，朝你挥了挥手，那个画面，定格在你的记忆里，成为最美的风景。

这是你们故事的开始。"""
                }
            }
        ]
    }


@pytest.fixture
def mock_character_config():
    """Mock character configuration"""
    from app.services.character_config import CharacterConfig, ZAxisConfig, ThresholdsConfig
    
    return CharacterConfig(
        char_id="test-char-001",
        name="测试角色",
        z_axis=ZAxisConfig(
            pure_val=25,
            chaos_val=-5,
            pride_val=5,
            greed_val=10,
            jealousy_val=15,
        ),
        thresholds=ThresholdsConfig(
            nsfw_trigger=55,
            spicy_mode_level=18,
            friendzone_wall=50,
            confession_threshold=60,
        ),
        base_temperament="warm",
        sensitivity=0.5,
        forgiveness_rate=0.8,
    )


@pytest.fixture
def sample_chat_history():
    """Sample chat history for context"""
    return [
        {"role": "user", "content": "今天天气真好啊"},
        {"role": "assistant", "content": "是呢！阳光明媚的，要不要一起出去走走？"},
        {"role": "user", "content": "好啊，我们去喝咖啡吧"},
        {"role": "assistant", "content": "太好了！我知道一家很棒的咖啡馆"},
    ]


@pytest.fixture
def sample_relationship_state():
    """Sample relationship state"""
    return {
        "intimacy_level": 25,
        "intimacy_stage": "friends",
        "emotion_state": "happy",
        "total_messages": 150,
        "streak_days": 7,
    }


# =============================================================================
# Unit Tests - Event Types
# =============================================================================

class TestEventTypes:
    """Tests for EventType class"""
    
    def test_story_events_defined(self):
        """All story events should be in STORY_EVENTS list"""
        assert EventType.FIRST_DATE in EventType.STORY_EVENTS
        assert EventType.FIRST_CONFESSION in EventType.STORY_EVENTS
        assert EventType.FIRST_KISS in EventType.STORY_EVENTS
        assert EventType.FIRST_NSFW in EventType.STORY_EVENTS
        assert EventType.ANNIVERSARY in EventType.STORY_EVENTS
        assert EventType.RECONCILIATION in EventType.STORY_EVENTS
    
    def test_first_chat_not_story_event(self):
        """first_chat should not generate a story"""
        assert EventType.FIRST_CHAT not in EventType.STORY_EVENTS
        assert not EventType.is_story_event(EventType.FIRST_CHAT)
    
    def test_is_story_event_valid(self):
        """is_story_event should return True for valid story events"""
        assert EventType.is_story_event(EventType.FIRST_DATE)
        assert EventType.is_story_event(EventType.FIRST_KISS)
    
    def test_is_story_event_invalid(self):
        """is_story_event should return False for non-story events"""
        assert not EventType.is_story_event("invalid_event")
        assert not EventType.is_story_event("")


class TestPromptTemplates:
    """Tests for prompt templates"""
    
    def test_all_story_events_have_prompts(self):
        """Every story event should have a corresponding prompt template"""
        for event_type in EventType.STORY_EVENTS:
            assert event_type in EVENT_STORY_PROMPTS, f"Missing prompt for {event_type}"
    
    def test_prompts_contain_placeholders(self):
        """Prompts should contain required placeholders"""
        required_placeholders = [
            "{character_profile}",
            "{relationship_state}",
            "{chat_context}",
            "{memory_context}",
        ]
        
        for event_type, prompt in EVENT_STORY_PROMPTS.items():
            for placeholder in required_placeholders:
                assert placeholder in prompt, f"Missing {placeholder} in {event_type} prompt"


# =============================================================================
# Unit Tests - Story Generator
# =============================================================================

class TestEventStoryGenerator:
    """Tests for EventStoryGenerator class"""
    
    @pytest.mark.asyncio
    async def test_generate_story_success(
        self,
        mock_llm_response,
        mock_character_config,
        sample_chat_history,
        sample_relationship_state,
    ):
        """Story generation should succeed with valid inputs"""
        generator = EventStoryGenerator()
        
        # Mock the LLM service
        with patch.object(
            generator.llm_service,
            'chat_completion',
            new_callable=AsyncMock,
            return_value=mock_llm_response
        ):
            # Mock character config lookup
            with patch(
                'app.services.event_story_generator.get_character_config',
                return_value=mock_character_config
            ):
                result = await generator.generate_event_story(
                    user_id="test-user-001",
                    character_id="test-char-001",
                    event_type=EventType.FIRST_DATE,
                    chat_history=sample_chat_history,
                    memory_context="用户和角色认识一个月了，经常聊天",
                    relationship_state=sample_relationship_state,
                    save_to_db=False,  # Don't save in tests
                )
        
        assert result.success is True
        assert result.story_content is not None
        assert len(result.story_content) > 100
        assert "咖啡" in result.story_content or "约会" in result.story_content
    
    @pytest.mark.asyncio
    async def test_generate_story_invalid_event_type(self):
        """Should fail for invalid event types"""
        generator = EventStoryGenerator()
        
        result = await generator.generate_event_story(
            user_id="test-user",
            character_id="test-char",
            event_type="invalid_event",
            chat_history=[],
            save_to_db=False,
        )
        
        assert result.success is False
        assert "does not support story generation" in result.error
    
    @pytest.mark.asyncio
    async def test_generate_story_first_chat_rejected(self):
        """first_chat event should be rejected"""
        generator = EventStoryGenerator()
        
        result = await generator.generate_event_story(
            user_id="test-user",
            character_id="test-char",
            event_type=EventType.FIRST_CHAT,
            chat_history=[],
            save_to_db=False,
        )
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_generate_story_llm_failure(
        self,
        mock_character_config,
        sample_chat_history,
    ):
        """Should handle LLM failures gracefully"""
        generator = EventStoryGenerator()
        
        # Mock LLM to return None (failure)
        with patch.object(
            generator.llm_service,
            'chat_completion',
            new_callable=AsyncMock,
            return_value=None
        ):
            with patch(
                'app.services.event_story_generator.get_character_config',
                return_value=mock_character_config
            ):
                result = await generator.generate_event_story(
                    user_id="test-user",
                    character_id="test-char",
                    event_type=EventType.FIRST_DATE,
                    chat_history=sample_chat_history,
                    save_to_db=False,
                )
        
        assert result.success is False
        assert result.error is not None
    
    def test_format_chat_history_empty(self):
        """Empty chat history should return default message"""
        generator = EventStoryGenerator()
        result = generator._format_chat_history([])
        assert "暂无" in result
    
    def test_format_chat_history_with_messages(self, sample_chat_history):
        """Chat history should be formatted correctly"""
        generator = EventStoryGenerator()
        result = generator._format_chat_history(sample_chat_history)
        
        assert "用户" in result
        assert "角色" in result
        assert "天气" in result
    
    def test_format_relationship_state_empty(self):
        """Empty relationship state should return default"""
        generator = EventStoryGenerator()
        result = generator._format_relationship_state(None)
        assert "普通朋友" in result
    
    def test_format_relationship_state_with_data(self, sample_relationship_state):
        """Relationship state should be formatted correctly"""
        generator = EventStoryGenerator()
        result = generator._format_relationship_state(sample_relationship_state)
        
        assert "朋友" in result
        assert "happy" in result or "情绪" in result
    
    def test_build_character_profile_none(self):
        """Should handle None character config"""
        generator = EventStoryGenerator()
        result = generator._build_character_profile(None)
        assert "神秘的AI伴侣" in result
    
    def test_build_character_profile_with_config(self, mock_character_config):
        """Should build profile from character config"""
        generator = EventStoryGenerator()
        result = generator._build_character_profile(mock_character_config)
        
        assert "测试角色" in result
        assert "温柔" in result or "温和" in result


# =============================================================================
# Unit Tests - Event Memory Model
# =============================================================================

class TestEventMemoryModel:
    """Tests for EventMemory database model"""
    
    def test_event_memory_creation(self):
        """EventMemory should be created with required fields"""
        memory = EventMemory(
            user_id="test-user",
            character_id="test-char",
            event_type=EventType.FIRST_DATE,
            story_content="测试剧情内容",
            context_summary="测试上下文",
        )
        
        assert memory.user_id == "test-user"
        assert memory.character_id == "test-char"
        assert memory.event_type == EventType.FIRST_DATE
        assert memory.story_content == "测试剧情内容"
    
    def test_event_memory_to_dict(self):
        """to_dict should return proper dictionary"""
        memory = EventMemory(
            id="test-id-123",
            user_id="test-user",
            character_id="test-char",
            event_type=EventType.FIRST_KISS,
            story_content="初吻的故事",
            context_summary="关系进展顺利",
            intimacy_level="romantic",
            emotion_state="loving",
            generated_at=datetime(2024, 2, 1, 12, 0, 0),
        )
        
        result = memory.to_dict()
        
        assert result["id"] == "test-id-123"
        assert result["event_type"] == EventType.FIRST_KISS
        assert result["story_content"] == "初吻的故事"
        assert result["intimacy_level"] == "romantic"
        assert "2024-02-01" in result["generated_at"]


# =============================================================================
# Integration Tests (with mocked DB)
# =============================================================================

class TestEventStoryGeneratorIntegration:
    """Integration tests with mocked database"""
    
    @pytest.mark.asyncio
    async def test_get_event_memories_empty(self):
        """Should return empty list when no memories exist"""
        generator = EventStoryGenerator()
        
        # Mock the database session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        with patch(
            'app.services.event_story_generator.get_db',
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())
        ):
            memories = await generator.get_event_memories(
                user_id="test-user",
                character_id="test-char",
                db_session=mock_session,
            )
        
        assert memories == []
    
    @pytest.mark.asyncio
    async def test_existing_story_returned(
        self,
        mock_llm_response,
        mock_character_config,
    ):
        """Should return existing story instead of generating new one"""
        generator = EventStoryGenerator()
        
        existing_memory = EventMemory(
            id="existing-id",
            user_id="test-user",
            character_id="test-char",
            event_type=EventType.FIRST_DATE,
            story_content="已存在的故事",
            generated_at=datetime.utcnow(),
        )
        
        # Mock _get_existing_story to return the existing memory
        with patch.object(
            generator,
            '_get_existing_story',
            new_callable=AsyncMock,
            return_value=existing_memory
        ):
            result = await generator.generate_event_story(
                user_id="test-user",
                character_id="test-char",
                event_type=EventType.FIRST_DATE,
                chat_history=[],
                save_to_db=True,
            )
        
        assert result.success is True
        assert result.story_content == "已存在的故事"
        assert result.event_memory_id == "existing-id"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

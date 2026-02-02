"""
Test Event Story Integration with Chat System
=============================================

Tests that events trigger correctly and insert placeholder messages
into the chat history.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.event_story_generator import EventType


class TestEventStoryPlaceholder:
    """Tests for event story placeholder messages in chat"""
    
    def test_placeholder_json_format(self):
        """Test that placeholder JSON has correct format"""
        placeholder = {
            "type": "event_story",
            "event_type": "first_date",
            "character_id": "char-123",
            "status": "pending",
            "story_id": None
        }
        
        json_str = json.dumps(placeholder, ensure_ascii=False)
        parsed = json.loads(json_str)
        
        assert parsed["type"] == "event_story"
        assert parsed["event_type"] == "first_date"
        assert parsed["status"] == "pending"
    
    def test_is_story_event(self):
        """Test EventType.is_story_event correctly identifies story events"""
        # Story events
        story_events = [
            "first_date",
            "first_kiss",
            "first_confession",
            "first_nsfw",
            "anniversary",
            "reconciliation",
        ]
        
        for event in story_events:
            assert EventType.is_story_event(event), f"{event} should be a story event"
        
        # Non-story events
        non_story_events = [
            "first_chat",
            "first_compliment",
            "first_gift",
        ]
        
        for event in non_story_events:
            assert not EventType.is_story_event(event), f"{event} should not be a story event"


class TestEventStoryGeneration:
    """Tests for event story generation"""
    
    @pytest.mark.asyncio
    async def test_generate_story_returns_content(self):
        """Test that story generation returns content"""
        from app.services.event_story_generator import event_story_generator
        
        # Mock the LLM call
        with patch.object(event_story_generator, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "这是一个美丽的初约会故事..."
            
            # Mock database operations
            with patch.object(event_story_generator, '_get_existing_story', new_callable=AsyncMock) as mock_existing:
                mock_existing.return_value = None
                
                with patch.object(event_story_generator, '_save_story', new_callable=AsyncMock) as mock_save:
                    mock_save.return_value = MagicMock(id="story-123")
                    
                    result = await event_story_generator.generate_event_story(
                        user_id="user-123",
                        character_id="char-123",
                        event_type="first_date",
                        chat_history=[
                            {"role": "user", "content": "我们去约会吧"},
                            {"role": "assistant", "content": "好啊，我也很期待！"},
                        ],
                        save_to_db=True,
                    )
                    
                    assert result.success
                    assert result.story_content is not None
                    assert len(result.story_content) > 0
    
    @pytest.mark.asyncio
    async def test_returns_existing_story_if_present(self):
        """Test that existing story is returned instead of generating new one"""
        from app.services.event_story_generator import event_story_generator
        from app.models.database.event_memory_models import EventMemory
        
        # Create mock existing story
        mock_memory = MagicMock()
        mock_memory.id = "existing-story-123"
        mock_memory.story_content = "这是已存在的故事内容..."
        
        with patch.object(event_story_generator, '_get_existing_story', new_callable=AsyncMock) as mock_existing:
            mock_existing.return_value = mock_memory
            
            result = await event_story_generator.generate_event_story(
                user_id="user-123",
                character_id="char-123",
                event_type="first_date",
                chat_history=[],
                save_to_db=True,
            )
            
            assert result.success
            assert result.story_content == "这是已存在的故事内容..."
            assert result.event_memory_id == "existing-story-123"


class TestEventAPIRoutes:
    """Tests for event API routes"""
    
    def test_me_routes_exist(self):
        """Test that /me/ routes are defined"""
        from app.api.v1.events import router
        
        route_paths = [r.path for r in router.routes]
        
        # Routes include the /events prefix from the router
        assert "/events/me/{character_id}" in route_paths
        assert "/events/me/{character_id}/{event_type}" in route_paths
        assert "/events/me/{character_id}/generate" in route_paths
    
    def test_get_user_id_helper(self):
        """Test _get_user_id helper function"""
        from app.api.v1.events import _get_user_id
        from unittest.mock import MagicMock
        
        # Test with authenticated user
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "auth-user-123"
        mock_request.state.user = mock_user
        
        assert _get_user_id(mock_request) == "auth-user-123"
        
        # Test without authenticated user
        mock_request.state.user = None
        assert _get_user_id(mock_request) == "demo-user-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

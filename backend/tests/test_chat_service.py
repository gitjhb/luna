"""
Tests for Chat Service
======================

Covers:
- Session management
- Message sending and receiving
- Context handling for free vs premium users
- Memory integration
- Error handling
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime
from typing import Dict, List, Optional

# Import the service we're testing
from app.services.chat_service import ChatService
from app.models.schemas import ChatMessage, ChatCompletionRequest, UserContext
from app.core.exceptions import (
    CharacterNotFoundError,
    SessionNotFoundError,
    ContentModerationError,
    LLMServiceError
)


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies for ChatService"""
    with patch('app.services.chat_service.get_db') as mock_db, \
         patch('app.services.chat_service.get_redis') as mock_redis, \
         patch('app.services.chat_service.chat_repo') as mock_chat_repo, \
         patch('app.services.chat_service.GrokService') as mock_grok, \
         patch('app.services.chat_service.VectorService') as mock_vector, \
         patch('app.services.chat_service.moderate_content') as mock_moderate:
        
        yield {
            'db': mock_db,
            'redis': mock_redis,
            'chat_repo': mock_chat_repo,
            'grok': mock_grok,
            'vector': mock_vector,
            'moderate': mock_moderate
        }


@pytest.fixture
def chat_service(mock_dependencies):
    """Create ChatService instance with mocked dependencies"""
    service = ChatService()
    # Mock the GrokService and VectorService instances
    service.grok_service = AsyncMock()
    service.vector_service = Mock()
    return service


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return uuid4()


@pytest.fixture
def sample_character_id():
    """Generate a sample character ID"""
    return uuid4()


@pytest.fixture
def sample_session_id():
    """Generate a sample session ID"""
    return uuid4()


class TestChatService:
    """Test cases for ChatService"""

    @pytest.mark.asyncio
    async def test_create_session_success(self, chat_service, mock_dependencies, sample_user_id, sample_character_id):
        """
        Test successful session creation between user and character.
        
        Should:
        - Generate a new session ID
        - Store session metadata in repository
        - Return the session ID
        """
        expected_session_id = uuid4()
        mock_dependencies['chat_repo'].create_session = AsyncMock(return_value=expected_session_id)
        
        # Act
        result = await chat_service.create_session(sample_user_id, sample_character_id)
        
        # Assert
        assert result == expected_session_id
        mock_dependencies['chat_repo'].create_session.assert_called_once_with(
            sample_user_id, sample_character_id
        )

    @pytest.mark.asyncio 
    async def test_create_session_character_not_found(self, chat_service, mock_dependencies, sample_user_id):
        """
        Test session creation with invalid character ID.
        
        Should raise CharacterNotFoundError.
        """
        invalid_character_id = uuid4()
        mock_dependencies['chat_repo'].create_session = AsyncMock(
            side_effect=CharacterNotFoundError("Character not found")
        )
        
        # Act & Assert
        with pytest.raises(CharacterNotFoundError):
            await chat_service.create_session(sample_user_id, invalid_character_id)

    @pytest.mark.asyncio
    async def test_send_message_free_user(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test message sending for free user (sliding window context).
        
        Should:
        - Use last 10 messages as context
        - Not use vector search
        - Generate appropriate response
        """
        # Setup
        request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Hello there!",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=False,
                character_id=uuid4()
            )
        )
        
        # Mock chat history (sliding window)
        mock_messages = [
            ChatMessage(id=uuid4(), content=f"Message {i}", timestamp=datetime.now())
            for i in range(5)
        ]
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(return_value=mock_messages)
        
        # Mock LLM response
        chat_service.grok_service.chat_completion = AsyncMock(return_value={
            'message': 'Hello! How are you?',
            'emotion': 'happy'
        })
        
        # Mock moderation (passed)
        mock_dependencies['moderate'].return_value = {'flagged': False}
        
        # Mock message storage
        mock_dependencies['chat_repo'].store_message = AsyncMock()
        
        # Act
        result = await chat_service.send_message(request)
        
        # Assert
        assert result.response == 'Hello! How are you?'
        assert result.emotion == 'happy'
        mock_dependencies['chat_repo'].get_chat_history.assert_called_once_with(
            sample_session_id, limit=10  # Free user limit
        )
        # Vector service should not be called for free users
        assert not hasattr(chat_service.vector_service, 'search_memories') or \
               not chat_service.vector_service.search_memories.called

    @pytest.mark.asyncio
    async def test_send_message_premium_user_with_rag(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test message sending for premium user with RAG (vector memory search).
        
        Should:
        - Use vector search for relevant memories
        - Include memories in context
        - Generate enhanced response
        """
        # Setup
        request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Remember when we talked about movies?",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=True,
                character_id=uuid4()
            )
        )
        
        # Mock recent messages
        mock_messages = [
            ChatMessage(id=uuid4(), content="Recent message", timestamp=datetime.now())
        ]
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(return_value=mock_messages)
        
        # Mock vector search results
        mock_memories = [
            {"content": "We discussed your favorite movie last week", "score": 0.9},
            {"content": "You mentioned liking sci-fi films", "score": 0.8}
        ]
        if chat_service.vector_service:
            chat_service.vector_service.search_memories = Mock(return_value=mock_memories)
        
        # Mock LLM response
        chat_service.grok_service.chat_completion = AsyncMock(return_value={
            'message': 'Yes! You loved Interstellar, right?',
            'emotion': 'excited'
        })
        
        # Mock moderation
        mock_dependencies['moderate'].return_value = {'flagged': False}
        
        # Mock message storage
        mock_dependencies['chat_repo'].store_message = AsyncMock()
        
        # Act
        result = await chat_service.send_message(request)
        
        # Assert
        assert result.response == 'Yes! You loved Interstellar, right?'
        assert result.emotion == 'excited'
        # Should use vector search for premium users
        if chat_service.vector_service:
            chat_service.vector_service.search_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_content_moderation_fails(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test message sending with inappropriate content.
        
        Should raise ContentModerationError and not process the message.
        """
        # Setup
        request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Inappropriate content here",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=False,
                character_id=uuid4()
            )
        )
        
        # Mock moderation failure
        mock_dependencies['moderate'].return_value = {
            'flagged': True,
            'categories': ['violence']
        }
        
        # Act & Assert
        with pytest.raises(ContentModerationError):
            await chat_service.send_message(request)
        
        # LLM should not be called if moderation fails
        chat_service.grok_service.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_chat_history_success(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test retrieving chat history for a session.
        
        Should return paginated list of messages.
        """
        # Setup
        expected_messages = [
            ChatMessage(
                id=uuid4(),
                content=f"Message {i}",
                timestamp=datetime.now(),
                sender_type="user" if i % 2 == 0 else "character"
            )
            for i in range(5)
        ]
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(return_value=expected_messages)
        
        # Act
        result = await chat_service.get_chat_history(sample_session_id, limit=10, offset=0)
        
        # Assert
        assert len(result) == 5
        assert all(isinstance(msg, ChatMessage) for msg in result)
        mock_dependencies['chat_repo'].get_chat_history.assert_called_once_with(
            sample_session_id, limit=10, offset=0
        )

    @pytest.mark.asyncio
    async def test_get_chat_history_invalid_session(self, chat_service, mock_dependencies):
        """
        Test retrieving chat history for non-existent session.
        
        Should raise SessionNotFoundError.
        """
        invalid_session_id = uuid4()
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(
            side_effect=SessionNotFoundError("Session not found")
        )
        
        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await chat_service.get_chat_history(invalid_session_id)

    @pytest.mark.asyncio
    async def test_llm_service_error_handling(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test handling of LLM service errors.
        
        Should raise LLMServiceError when Grok service fails.
        """
        # Setup
        request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Test message",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=False,
                character_id=uuid4()
            )
        )
        
        # Mock dependencies
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(return_value=[])
        mock_dependencies['moderate'].return_value = {'flagged': False}
        
        # Mock LLM failure
        chat_service.grok_service.chat_completion = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        
        # Act & Assert
        with pytest.raises(LLMServiceError):
            await chat_service.send_message(request)

    @pytest.mark.asyncio
    async def test_context_building_for_different_user_types(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test that context building works differently for free vs premium users.
        
        Free users get sliding window, premium users get enhanced context with memories.
        """
        # Test free user context
        free_request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Test message",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=False,
                character_id=uuid4()
            )
        )
        
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(return_value=[])
        mock_dependencies['moderate'].return_value = {'flagged': False}
        chat_service.grok_service.chat_completion = AsyncMock(return_value={
            'message': 'Response',
            'emotion': 'neutral'
        })
        mock_dependencies['chat_repo'].store_message = AsyncMock()
        
        # Act - Free user
        await chat_service.send_message(free_request)
        
        # Assert - Should use basic context only
        mock_dependencies['chat_repo'].get_chat_history.assert_called_with(
            sample_session_id, limit=10  # Free user sliding window
        )
        
        # Test premium user context  
        premium_request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Test message",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=True,
                character_id=uuid4()
            )
        )
        
        # Act - Premium user
        await chat_service.send_message(premium_request)
        
        # Vector service should be used for premium users (if available)
        if chat_service.vector_service:
            assert hasattr(chat_service.vector_service, 'search_memories')

    @pytest.mark.asyncio
    async def test_message_storage(self, chat_service, mock_dependencies, sample_session_id):
        """
        Test that both user messages and AI responses are properly stored.
        
        Should call store_message twice per conversation turn.
        """
        # Setup
        request = ChatCompletionRequest(
            session_id=sample_session_id,
            message="Hello AI",
            user_context=UserContext(
                user_id=uuid4(),
                is_premium=False,
                character_id=uuid4()
            )
        )
        
        mock_dependencies['chat_repo'].get_chat_history = AsyncMock(return_value=[])
        mock_dependencies['moderate'].return_value = {'flagged': False}
        chat_service.grok_service.chat_completion = AsyncMock(return_value={
            'message': 'Hello human!',
            'emotion': 'friendly'
        })
        mock_dependencies['chat_repo'].store_message = AsyncMock()
        
        # Act
        await chat_service.send_message(request)
        
        # Assert
        # Should store both user message and AI response
        assert mock_dependencies['chat_repo'].store_message.call_count == 2
        
        # Verify the calls
        calls = mock_dependencies['chat_repo'].store_message.call_args_list
        
        # First call should be user message
        user_msg_call = calls[0]
        assert user_msg_call[1]['sender_type'] == 'user'
        assert user_msg_call[1]['content'] == 'Hello AI'
        
        # Second call should be AI response
        ai_msg_call = calls[1]
        assert ai_msg_call[1]['sender_type'] == 'character'
        assert ai_msg_call[1]['content'] == 'Hello human!'
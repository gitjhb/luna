"""
Chat Service with RAG (Retrieval-Augmented Generation) and xAI Grok Integration
"""

from typing import List, Dict, Optional, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import json

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.exceptions import (
    CharacterNotFoundError,
    SessionNotFoundError,
    ContentModerationError,
    LLMServiceError
)
from app.services.llm_service import GrokService
from app.services.vector_service import VectorService
from app.utils.moderation import moderate_content
from app.models.schemas import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    UserContext
)


class ChatService:
    """
    Core chat service implementing RAG-powered conversations.
    
    Features:
    - Free users: Simple sliding window context (last 10 messages)
    - Premium users: Vector search for relevant memories + spicy mode
    - Automatic memory embedding and storage
    - Content moderation hooks
    """
    
    def __init__(self):
        self.grok_service = GrokService()
        # VectorService is optional - may fail due to dependency issues
        try:
            self.vector_service = VectorService()
        except Exception as e:
            print(f"Warning: VectorService unavailable: {e}")
            self.vector_service = None
        self.max_context_messages = 10  # For free users
        self.max_rag_memories = 5       # For premium users
    
    async def create_session(
        self,
        user_id: UUID,
        character_id: UUID
    ) -> UUID:
        """
        Create a new chat session.
        
        Args:
            user_id: User UUID
            character_id: Character UUID
        
        Returns:
            Session UUID
        """
        # Verify character exists and is accessible
        character = await self._get_character(character_id)
        
        async with get_db() as db:
            session_id = uuid4()
            await db.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, character_id, title)
                VALUES ($1, $2, $3, $4)
                """,
                session_id, user_id, character_id, f"Chat with {character['name']}"
            )
        
        return session_id
    
    async def get_session(self, session_id: UUID, user_id: UUID) -> Dict:
        """
        Get session details with validation.
        """
        async with get_db() as db:
            session = await db.fetchrow(
                """
                SELECT s.*, c.name as character_name, c.avatar_url
                FROM chat_sessions s
                JOIN character_config c ON s.character_id = c.character_id
                WHERE s.session_id = $1 AND s.user_id = $2
                """,
                session_id, user_id
            )
        
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        return dict(session)
    
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        user_context: UserContext
    ) -> ChatCompletionResponse:
        """
        Main chat completion endpoint.
        
        Flow:
        1. Validate session and character
        2. Moderate user input
        3. Build context (sliding window or RAG)
        4. Call Grok API
        5. Store messages and embeddings
        6. Return response
        
        Args:
            request: Chat completion request
            user_context: Authenticated user context
        
        Returns:
            Chat completion response
        """
        # Step 1: Validate session
        session = await self.get_session(request.session_id, user_context.user_id)
        character = await self._get_character(UUID(session["character_id"]))
        
        # Step 2: Moderate user input
        if not await moderate_content(request.message, mode="input"):
            raise ContentModerationError(
                "Your message contains prohibited content",
                flagged_content=request.message[:100]
            )
        
        # Step 3: Build conversation context
        if user_context.is_subscribed:
            # Premium: Use RAG for memory retrieval
            context_messages = await self._build_rag_context(
                user_id=user_context.user_id,
                session_id=request.session_id,
                current_message=request.message,
                character=character
            )
            system_prompt = self._build_system_prompt(
                character=character,
                mode="spicy" if character["is_spicy"] else "normal"
            )
        else:
            # Free: Use sliding window
            context_messages = await self._build_sliding_window_context(
                session_id=request.session_id
            )
            system_prompt = self._build_system_prompt(
                character=character,
                mode="normal"
            )
        
        # Step 4: Call Grok API
        try:
            grok_response = await self.grok_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    *context_messages,
                    {"role": "user", "content": request.message}
                ],
                temperature=float(character.get("temperature", 0.8)),
                max_tokens=int(character.get("max_tokens", 500))
            )
        except Exception as e:
            raise LLMServiceError(f"Grok API error: {str(e)}")
        
        assistant_message = grok_response["choices"][0]["message"]["content"]
        tokens_used = grok_response["usage"]["total_tokens"]
        
        # Step 5: Moderate assistant output (basic check)
        if not await moderate_content(assistant_message, mode="output"):
            # Log but don't block (Grok should handle this)
            print(f"Warning: Assistant message flagged by moderation: {assistant_message[:100]}")
        
        # Step 6: Store messages
        user_message_id = await self._store_message(
            session_id=request.session_id,
            user_id=user_context.user_id,
            role="user",
            content=request.message,
            tokens_used=0
        )
        
        assistant_message_id = await self._store_message(
            session_id=request.session_id,
            user_id=user_context.user_id,
            role="assistant",
            content=assistant_message,
            tokens_used=tokens_used
        )
        
        # Step 7: Embed and store in vector DB (async, for premium users)
        if user_context.is_subscribed:
            await self._embed_and_store_messages(
                user_id=user_context.user_id,
                session_id=request.session_id,
                messages=[
                    {"id": user_message_id, "role": "user", "content": request.message},
                    {"id": assistant_message_id, "role": "assistant", "content": assistant_message}
                ]
            )
        
        # Step 8: Update session stats
        await self._update_session_stats(request.session_id)
        
        return ChatCompletionResponse(
            message_id=assistant_message_id,
            content=assistant_message,
            tokens_used=tokens_used,
            character_name=character["name"]
        )
    
    async def stream_completion(
        self,
        request: ChatCompletionRequest,
        user_context: UserContext
    ) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion (for real-time responses).
        Similar to chat_completion but yields chunks.
        """
        # Similar implementation but with streaming
        # TODO: Implement streaming version
        raise NotImplementedError("Streaming not yet implemented")
    
    async def _get_character(self, character_id: UUID) -> Dict:
        """Get character configuration."""
        async with get_db() as db:
            character = await db.fetchrow(
                "SELECT * FROM character_config WHERE character_id = $1 AND is_active = TRUE",
                character_id
            )
        
        if not character:
            raise CharacterNotFoundError(f"Character {character_id} not found")
        
        return dict(character)
    
    async def _build_sliding_window_context(
        self,
        session_id: UUID
    ) -> List[Dict[str, str]]:
        """
        Build context from last N messages (for free users).
        """
        redis = await get_redis()
        cache_key = f"session:{session_id}:context"
        
        # Try cache first
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch from database
        async with get_db() as db:
            messages = await db.fetch(
                """
                SELECT role, content
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                session_id, self.max_context_messages
            )
        
        # Reverse to chronological order
        context = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in reversed(messages)
        ]
        
        # Cache for 1 hour
        await redis.setex(cache_key, 3600, json.dumps(context))
        
        return context
    
    async def _build_rag_context(
        self,
        user_id: UUID,
        session_id: UUID,
        current_message: str,
        character: Dict
    ) -> List[Dict[str, str]]:
        """
        Build context using RAG (for premium users).
        
        Flow:
        1. Embed current message
        2. Search vector DB for relevant past messages
        3. Combine with recent messages
        """
        # Get recent messages (last 5)
        async with get_db() as db:
            recent_messages = await db.fetch(
                """
                SELECT role, content
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT 5
                """,
                session_id
            )
        
        recent_context = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in reversed(recent_messages)
        ]
        
        # Search for relevant memories (if vector service available)
        try:
            if self.vector_service is None:
                return recent_context
            relevant_memories = await self.vector_service.search_memories(
                user_id=user_id,
                query_text=current_message,
                top_k=self.max_rag_memories
            )
            
            # Format memories as context
            if relevant_memories:
                memory_context = self._format_memories_as_context(relevant_memories)
                # Inject memories at the beginning
                return memory_context + recent_context
        except Exception as e:
            print(f"RAG search failed, falling back to recent context: {e}")
        
        return recent_context
    
    def _format_memories_as_context(self, memories: List[Dict]) -> List[Dict[str, str]]:
        """
        Format retrieved memories as conversation context.
        """
        context = []
        for memory in memories:
            context.append({
                "role": memory["role"],
                "content": memory["content"]
            })
        return context
    
    def _build_system_prompt(self, character: Dict, mode: str = "normal") -> str:
        """
        Build system prompt based on character and mode.
        
        Args:
            character: Character configuration
            mode: 'normal' or 'spicy'
        
        Returns:
            System prompt string
        """
        if mode == "spicy" and character.get("spicy_system_prompt"):
            base_prompt = character["spicy_system_prompt"]
        else:
            base_prompt = character["system_prompt"]
        
        # Add personality traits
        traits = character.get("personality_traits", [])
        if traits:
            traits_str = ", ".join(traits)
            base_prompt += f"\n\nPersonality traits: {traits_str}"
        
        # Add behavioral guidelines
        guidelines = """

IMPORTANT GUIDELINES:
- Stay in character at all times
- Be engaging, empathetic, and emotionally responsive
- Remember context from previous messages
- Use natural, conversational language
- Show personality through your responses
"""
        
        if mode == "spicy":
            guidelines += """- You can engage in flirtatious and suggestive conversation
- Be playful and bold, but always respect boundaries
- NSFW content is allowed within legal limits
"""
        else:
            guidelines += """- Keep responses appropriate and friendly
- Avoid explicit or overly suggestive content
"""
        
        return base_prompt + guidelines
    
    async def _store_message(
        self,
        session_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        tokens_used: int = 0
    ) -> UUID:
        """
        Store message in database.
        """
        message_id = uuid4()
        
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO chat_messages 
                (message_id, session_id, user_id, role, content, tokens_used)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                message_id, session_id, user_id, role, content, tokens_used
            )
        
        return message_id
    
    async def _embed_and_store_messages(
        self,
        user_id: UUID,
        session_id: UUID,
        messages: List[Dict]
    ) -> None:
        """
        Embed messages and store in vector database (async background task).
        """
        if self.vector_service is None:
            return  # Skip embedding if vector service unavailable
        try:
            for message in messages:
                # Embed message
                embedding = await self.vector_service.embed_text(message["content"])
                
                # Store in Pinecone
                await self.vector_service.upsert_memory(
                    user_id=user_id,
                    message_id=message["id"],
                    session_id=session_id,
                    role=message["role"],
                    content=message["content"],
                    embedding=embedding
                )
                
                # Update message with embedding_id
                async with get_db() as db:
                    await db.execute(
                        "UPDATE chat_messages SET embedding_id = $1 WHERE message_id = $2",
                        str(message["id"]), message["id"]
                    )
        except Exception as e:
            # Log but don't fail the request
            print(f"Failed to embed messages: {e}")
    
    async def _update_session_stats(self, session_id: UUID) -> None:
        """
        Update session statistics.
        """
        async with get_db() as db:
            await db.execute(
                """
                UPDATE chat_sessions
                SET total_messages = total_messages + 2,
                    updated_at = NOW()
                WHERE session_id = $1
                """,
                session_id
            )
    
    async def get_session_history(
        self,
        session_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """
        Get chat history for a session.
        """
        session = await self.get_session(session_id, user_id)
        
        async with get_db() as db:
            messages = await db.fetch(
                """
                SELECT message_id, role, content, tokens_used, created_at
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY created_at ASC
                LIMIT $2 OFFSET $3
                """,
                session_id, limit, offset
            )
        
        return [
            ChatMessage(
                message_id=msg["message_id"],
                role=msg["role"],
                content=msg["content"],
                tokens_used=msg["tokens_used"],
                created_at=msg["created_at"]
            )
            for msg in messages
        ]
    
    async def list_user_sessions(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        List all sessions for a user.
        """
        async with get_db() as db:
            sessions = await db.fetch(
                """
                SELECT 
                    s.session_id,
                    s.title,
                    s.total_messages,
                    s.total_credits_spent,
                    s.created_at,
                    s.updated_at,
                    c.name as character_name,
                    c.avatar_url
                FROM chat_sessions s
                JOIN character_config c ON s.character_id = c.character_id
                WHERE s.user_id = $1 AND s.is_active = TRUE
                ORDER BY s.updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )
        
        return [dict(session) for session in sessions]
    
    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        """
        Soft delete a session.
        """
        async with get_db() as db:
            result = await db.execute(
                """
                UPDATE chat_sessions
                SET is_active = FALSE
                WHERE session_id = $1 AND user_id = $2
                """,
                session_id, user_id
            )
        
        if result == "UPDATE 0":
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        # Clear cache
        redis = await get_redis()
        await redis.delete(f"session:{session_id}:context")

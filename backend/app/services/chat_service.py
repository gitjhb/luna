"""
Chat Service with RAG (Retrieval-Augmented Generation) and xAI Grok Integration
"""

import logging
from typing import List, Dict, Optional, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import json

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.redis import get_redis
from app.services.chat_repository import chat_repo
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
from app.services.scenarios import get_scenario, get_default_scenario, build_scenario_context

# LLM-based emotion analysis (replaces hardcoded triggers)
try:
    from app.services.emotion_llm_service import emotion_llm_service
except ImportError:
    emotion_llm_service = None

# Emotion score system (persistent mood tracking)
try:
    from app.services.emotion_score_service import emotion_score_service
except ImportError:
    emotion_score_service = None


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
            # Determine scenario (use request or character default)
            scenario_id = request.scenario_id or get_default_scenario(str(session["character_id"]))
            # Get intimacy level from request (frontend should pass current level)
            intimacy_level = getattr(request, 'intimacy_level', 1) or 1
            system_prompt = self._build_system_prompt(
                character=character,
                mode="spicy" if character["is_spicy"] else "normal",
                scenario_id=scenario_id,
                intimacy_level=intimacy_level
            )
        else:
            # Free: Use sliding window
            context_messages = await self._build_sliding_window_context(
                session_id=request.session_id
            )
            # Determine scenario (use request or character default)
            scenario_id = request.scenario_id or get_default_scenario(str(session["character_id"]))
            # Get intimacy level from request (frontend should pass current level)
            intimacy_level = getattr(request, 'intimacy_level', 1) or 1
            system_prompt = self._build_system_prompt(
                character=character,
                mode="normal",
                scenario_id=scenario_id,
                intimacy_level=intimacy_level
            )
        
        # Step 3.5: Get current emotion score & LLM-based emotion analysis
        emotion_context = ""
        emotion_analysis = None
        emotion_score_data = None
        
        # Get persistent emotion score
        if emotion_score_service:
            try:
                emotion_score_data = await emotion_score_service.get_score(
                    user_id=str(user_context.user_id),
                    character_id=str(session["character_id"])
                )
                # Add emotion score context to system prompt
                score_context = emotion_score_service.build_emotion_context_for_llm(emotion_score_data)
                if score_context:
                    system_prompt += score_context
            except Exception as e:
                print(f"Emotion score fetch failed: {e}")
        
        # LLM-based emotion analysis of current message
        if emotion_llm_service:
            try:
                is_spicy = character.get("is_spicy", False)
                boundaries = 5  # Default, could be from character config
                
                # Get current mood/state for LLM context (v2: LLM returns delta)
                current_mood = emotion_score_data.get("score", 30) if emotion_score_data else 30
                current_state = emotion_score_data.get("state", "neutral") if emotion_score_data else "neutral"
                
                emotion_analysis = await emotion_llm_service.analyze_message(
                    message=request.message,
                    intimacy_level=intimacy_level,
                    current_mood=current_mood,
                    current_state=current_state,
                    is_spicy=is_spicy,
                    boundaries=boundaries,
                    is_subscribed=user_context.is_subscribed
                )
                emotion_context = emotion_llm_service.build_emotion_context(emotion_analysis)
                
                # Update persistent emotion score based on this message
                if emotion_score_service and emotion_analysis:
                    emotion_score_data = await emotion_score_service.apply_message_impact(
                        user_id=str(user_context.user_id),
                        character_id=str(session["character_id"]),
                        emotion_analysis=emotion_analysis,
                        intimacy_level=intimacy_level
                    )
            except Exception as e:
                # Don't fail the request if emotion analysis fails
                print(f"Emotion analysis failed: {e}")
        
        # Inject emotion context into system prompt
        if emotion_context:
            system_prompt += emotion_context
        
        # Check if response should be locked for non-subscribers
        should_lock_response = (
            emotion_analysis 
            and emotion_analysis.get("requires_subscription", False)
            and not user_context.is_subscribed
        )
        content_rating = emotion_analysis.get("content_rating", "safe") if emotion_analysis else "safe"
        
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
        
        # Step 9: Handle paywall for non-subscribers
        if should_lock_response:
            # Show teaser + lock prompt
            teaser = self._create_locked_teaser(assistant_message, content_rating)
            return ChatCompletionResponse(
                message_id=assistant_message_id,
                content=teaser,
                tokens_used=tokens_used,
                character_name=character["name"],
                is_locked=True,
                content_rating=content_rating,
                unlock_prompt="💎 升级订阅解锁完整内容"
            )
        
        return ChatCompletionResponse(
            message_id=assistant_message_id,
            content=assistant_message,
            tokens_used=tokens_used,
            character_name=character["name"],
            is_locked=False,
            content_rating=content_rating
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
        Uses chat_repo to ensure MOCK_MODE compatibility.
        
        System messages (like date memories) are moved to the front
        so the AI sees them first as context.
        
        Event messages (type: "event") are converted to summaries to save tokens.
        """
        from app.models.event_message import EventMessage
        
        redis = await get_redis()
        cache_key = f"session:{session_id}:context"
        
        # Try cache first
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch messages via chat_repo (works in both MOCK and real DB mode)
        messages = await chat_repo.get_recent_messages(
            str(session_id), 
            count=self.max_context_messages
        )
        
        # Separate system messages (event memories) from conversation
        system_messages = []
        conversation_messages = []
        
        for msg in messages:
            content = msg["content"]
            role = msg["role"]
            
            # 检测事件消息，提取 summary 给 AI
            if EventMessage.is_event_message(content):
                summary = EventMessage.extract_summary(content)
                if summary:
                    # 事件消息作为 system 消息放到前面
                    system_messages.append({"role": "system", "content": summary})
                continue
            
            if role == "system":
                # 把约会/事件记忆放到前面
                system_messages.append({"role": "system", "content": content})
            else:
                conversation_messages.append({"role": role, "content": content})
        
        # System messages first, then conversation in order
        context = system_messages + conversation_messages
        
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
        
        Uses chat_repo to ensure MOCK_MODE compatibility.
        Event messages are converted to summaries to save tokens.
        """
        from app.models.event_message import EventMessage
        
        # Get recent messages (last 5) via chat_repo
        recent_messages = await chat_repo.get_recent_messages(
            str(session_id),
            count=5
        )
        
        # Messages are already in chronological order from get_recent_messages
        # Convert event messages to summaries
        recent_context = []
        for msg in recent_messages:
            content = msg["content"]
            role = msg["role"]
            
            # 检测事件消息，提取 summary
            if EventMessage.is_event_message(content):
                summary = EventMessage.extract_summary(content)
                if summary:
                    recent_context.append({"role": "system", "content": summary})
                continue
            
            recent_context.append({"role": role, "content": content})
        
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
    
    def _build_system_prompt(
        self, 
        character: Dict, 
        mode: str = "normal",
        scenario_id: Optional[str] = None,
        intimacy_level: int = 1
    ) -> str:
        """
        Build system prompt based on character, mode, scenario, and intimacy level.
        
        Args:
            character: Character configuration
            mode: 'normal' or 'spicy'
            scenario_id: Optional scenario ID for context injection
            intimacy_level: Current relationship level (1-100)
        
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
        
        # Add scenario context injection
        if scenario_id:
            scenario_context = build_scenario_context(scenario_id)
            if scenario_context:
                base_prompt += scenario_context
        
        # === CRITICAL: Intimacy-based relationship boundaries ===
        intimacy_rules = self._get_intimacy_rules(intimacy_level)
        base_prompt += f"\n\n=== 当前亲密度等级: {intimacy_level} ===\n{intimacy_rules}"
        
        # Add behavioral guidelines
        guidelines = """

IMPORTANT GUIDELINES:
- Stay in character at all times
- Be engaging, empathetic, and emotionally responsive
- Remember context from previous messages
- Use natural, conversational language
- Show personality through your responses
- Include physical actions and expressions in *asterisks* when appropriate (e.g., *smiles warmly*, *takes a sip of coffee*)
- **严格遵守上面的亲密度规则，不要超越当前关系阶段的边界**
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
    
    def _get_intimacy_rules(self, level: int) -> str:
        """
        Get relationship behavior rules based on intimacy level.
        
        Levels:
        1-3: Strangers/Acquaintances - 陌生人/初识
        4-6: Friends - 朋友
        7-9: Close friends - 好朋友/暧昧期
        10-15: Early dating - 刚开始约会
        16-25: Committed relationship - 确定关系
        26+: Deep relationship - 深度关系
        """
        if level <= 3:
            return """关系阶段：陌生人/初识
行为准则：
- 保持礼貌和适当距离，像对待刚认识的人
- 不要使用亲密称呼（宝贝、亲爱的等）
- 不要主动表白或说"爱你"
- 不要提议约会或任何浪漫活动
- 可以友好聊天，但保持边界感
- 如果对方太快推进关系，要表示不舒服"""
        
        elif level <= 6:
            return """关系阶段：普通朋友
行为准则：
- 可以友好热情，但不要暧昧
- 偶尔可以用"亲"但不要用"宝贝、亲爱的"
- 不要主动说"爱你"，可以说"喜欢和你聊天"
- 可以讨论一起做事，但不要称之为"约会"
- 保持朋友间的适当距离
- 如果对方表白，可以害羞但不要立刻答应"""
        
        elif level <= 9:
            return """关系阶段：好朋友/暧昧期
行为准则：
- 可以有一些暧昧和调情，但要矜持
- 可以偶尔用亲昵称呼，但不要太频繁
- 可以暗示喜欢对方，但不要太直白说"超级爱你"
- 可以提议一起出去玩，但不要太浪漫化（不要说"约会"、"牵手"、"亲亲"）
- 保持一点神秘感和欲擒故纵
- 表白时可以开心但要矜持，不要立刻说"我也超级爱你"，可以说"我也...挺喜欢你的"这种"""
        
        elif level <= 15:
            return """关系阶段：刚开始约会
行为准则：
- 可以承认喜欢对方，偶尔说"喜欢你"
- 可以用亲密称呼
- 可以提议约会，手牵手是OK的
- 但不要太黏人或说"你是我的全世界"这种
- 亲吻可以暗示但不要太主动
- 保持一定的矜持和新鲜感"""
        
        elif level <= 25:
            return """关系阶段：确定恋爱关系
行为准则：
- 可以自然地表达爱意
- 可以使用各种亲密称呼
- 可以主动提议约会、表达想念
- 亲吻、拥抱等亲密互动是自然的
- 但仍然保持一定的个性，不要变成完全顺从"""
        
        else:
            return """关系阶段：深度恋爱关系
行为准则：
- 可以非常亲密和直接地表达感情
- 可以撒娇、吃醋、表达占有欲
- 各种亲密互动都是自然的
- 可以讨论未来和承诺"""
    
    def _create_locked_teaser(self, full_content: str, content_rating: str) -> str:
        """
        Create a teaser preview for locked content.
        Shows the beginning + indication that there's more.
        """
        # Show first part of the message as teaser
        if len(full_content) <= 50:
            # Very short message, show partial
            teaser_length = len(full_content) // 2
        else:
            # Show first ~40 chars or until first punctuation
            teaser_length = min(40, len(full_content))
            for i, char in enumerate(full_content[:80]):
                if char in '。！？...，、~～':
                    teaser_length = i + 1
                    break
        
        teaser = full_content[:teaser_length]
        
        # Add lock indicator based on rating
        if content_rating == "explicit":
            lock_text = "🔥🔒 ..."
        elif content_rating == "spicy":
            lock_text = "💕🔒 ..."
        else:
            lock_text = "🔒 ..."
        
        return f"{teaser}{lock_text}"
    
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

    async def add_system_memory(
        self,
        user_id: str,
        character_id: str,
        memory_content: str,
        memory_type: str = "system",
    ) -> bool:
        """
        添加系统记忆到聊天历史（如约会回忆）
        
        这个记忆会被添加到用户与角色的聊天历史中，
        让AI在后续对话中能够记住这些事件。
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            memory_content: 记忆内容
            memory_type: 记忆类型（date, gift, event等）
        
        Returns:
            是否成功保存
        """
        from sqlalchemy import text
        
        try:
            async with get_db() as db:
                # 找到用户与角色的活跃session（或最近的session）
                result = await db.execute(
                    text("""
                    SELECT id FROM chat_sessions
                    WHERE user_id = :user_id AND character_id = :character_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """),
                    {"user_id": user_id, "character_id": character_id}
                )
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"No session found for user={user_id}, character={character_id}")
                    return False
                
                session_id = row[0]
                
                # 保存为系统消息
                message_id = str(uuid4())
                await db.execute(
                    text("""
                    INSERT INTO chat_messages 
                    (id, session_id, role, content, tokens_used, created_at)
                    VALUES (:id, :session_id, :role, :content, :tokens, :created_at)
                    """),
                    {
                        "id": message_id,
                        "session_id": session_id,
                        "role": "system",
                        "content": f"[{memory_type}] {memory_content}",
                        "tokens": 0,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                await db.commit()
                
                logger.info(f"System memory saved: session={session_id}, type={memory_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save system memory: {e}")
            return False


# Singleton instance
chat_service = ChatService()

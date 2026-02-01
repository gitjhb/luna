"""
LLM Service Layer
=================

Architecture:
- Chat: Grok grok-4-1-fast-non-reasoning ($0.2/M tokens) - Main conversation
- Image: Grok grok-imagine-image ($0.07/image) - Image generation
- Embedding: OpenAI text-embedding-3-small ($0.02/M tokens) - Memory/RAG only

IMPORTANT: OpenAI API is ONLY used for embeddings. Do not use it for chat/completion.
"""

from app.services.llm.grok_chat import GrokChatService, grok_chat
from app.services.llm.grok_image import GrokImageService, grok_image
from app.services.llm.openai_embedding import OpenAIEmbeddingService, openai_embedding

__all__ = [
    "GrokChatService",
    "GrokImageService", 
    "OpenAIEmbeddingService",
    "grok_chat",
    "grok_image",
    "openai_embedding",
]

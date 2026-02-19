"""
Configuration Management - with development defaults
"""

import os
from typing import List, Optional
from pydantic import Field

# Check if pydantic_settings is available
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with development defaults"""
    
    # ========== Application ==========
    APP_NAME: str = "AI Companion API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="dev_secret_key_change_in_production")
    
    # ========== Server ==========
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # ========== CORS ==========
    CORS_ORIGINS: List[str] = Field(default=["*"])
    
    # ========== Database ==========
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./data/app.db")
    DATABASE_POOL_SIZE: int = Field(default=5)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    
    # ========== Redis ==========
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=10)
    
    # ========== Vector Database ==========
    VECTOR_DB_PROVIDER: str = Field(default="chromadb")
    PINECONE_API_KEY: str = Field(default="")
    PINECONE_INDEX_NAME: str = Field(default="ai-companion-memories")
    CHROMADB_PERSIST_DIR: str = Field(default="./data/chromadb")
    
    # ========== LLM APIs ==========
    # Grok - Chat & Image (main provider)
    XAI_API_KEY: str = Field(default="")
    XAI_BASE_URL: str = Field(default="https://api.x.ai/v1")
    XAI_MODEL: str = Field(default="grok-4-1-fast-non-reasoning")  # $0.2/M tokens
    XAI_IMAGE_MODEL: str = Field(default="grok-2-image")  # $0.07/image
    
    # OpenAI - ONLY for embeddings! Do not use for chat.
    # See: app/services/llm/openai_embedding.py
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")  # $0.02/M tokens
    
    # ========== Database Backend ==========
    DB_BACKEND: str = Field(default="sqlite")  # sqlite | supabase
    
    # ========== Voice (豆包 TTS) ==========
    DOUBAO_APP_ID: str = Field(default="")
    DOUBAO_ACCESS_TOKEN: str = Field(default="")
    DOUBAO_CLUSTER: str = Field(default="volcano_tts")
    DOUBAO_VOICE_TYPE: str = Field(default="BV700_streaming")
    
    # ========== Firebase ==========
    FIREBASE_PROJECT_ID: str = Field(default="")
    FIREBASE_CREDENTIALS_PATH: str = Field(default="")
    
    # ========== Mock Modes ==========
    MOCK_AUTH: bool = Field(default=True)
    MOCK_DATABASE: bool = Field(default=True)
    MOCK_REDIS: bool = Field(default=True)
    MOCK_LLM: bool = Field(default=True)
    MOCK_TTS: bool = Field(default=True)
    MOCK_IMAGE: bool = Field(default=True)  # Mock mode for image generation
    
    # ========== Content Moderation ==========
    MODERATION_ENABLED: bool = Field(default=True)  # Set to False to skip moderation
    
    # ========== Rate Limiting ==========
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_FREE: int = Field(default=5)
    RATE_LIMIT_PREMIUM: int = Field(default=30)
    RATE_LIMIT_VIP: int = Field(default=100)
    
    # ========== Credits ==========
    DAILY_CREDITS_FREE: float = Field(default=10.0)
    DAILY_CREDITS_PREMIUM: float = Field(default=100.0)
    DAILY_CREDITS_VIP: float = Field(default=500.0)
    COST_PER_1K_TOKENS: float = Field(default=0.10)
    
    # ========== Logging ==========
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="text")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Instantiate settings
settings = Settings()


def is_production() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def is_development() -> bool:
    return settings.ENVIRONMENT.lower() == "development"

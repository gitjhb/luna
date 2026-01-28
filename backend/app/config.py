"""
Configuration Management
Loads environment variables and provides typed configuration objects
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # ========== Application ==========
    APP_NAME: str = "AI Companion API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    
    # ========== Server ==========
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    
    # ========== CORS ==========
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # ========== Database (PostgreSQL) ==========
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # ========== Redis ==========
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # ========== Vector Database ==========
    VECTOR_DB_PROVIDER: str = Field(default="chromadb", env="VECTOR_DB_PROVIDER")  # 'pinecone' or 'chromadb'
    
    # Pinecone
    PINECONE_API_KEY: str = Field(default="", env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field(default="us-east-1", env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = Field(default="ai-companion-memories", env="PINECONE_INDEX_NAME")
    
    # ChromaDB
    CHROMADB_PERSIST_DIR: str = Field(default="/var/lib/chromadb", env="CHROMADB_PERSIST_DIR")
    
    # ========== LLM APIs ==========
    # xAI Grok
    XAI_API_KEY: str = Field(..., env="XAI_API_KEY")
    XAI_BASE_URL: str = Field(default="https://api.x.ai/v1", env="XAI_BASE_URL")
    XAI_MODEL: str = Field(default="grok-beta", env="XAI_MODEL")
    XAI_TIMEOUT: int = Field(default=60, env="XAI_TIMEOUT")
    
    # OpenAI (for embeddings)
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    
    # ========== Firebase Authentication ==========
    FIREBASE_PROJECT_ID: str = Field(..., env="FIREBASE_PROJECT_ID")
    FIREBASE_CREDENTIALS_PATH: str = Field(..., env="FIREBASE_CREDENTIALS_PATH")
    
    # ========== Celery ==========
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # ========== Payment Providers ==========
    # Stripe
    STRIPE_SECRET_KEY: str = Field(default="", env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(default="", env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PUBLISHABLE_KEY: str = Field(default="", env="STRIPE_PUBLISHABLE_KEY")
    
    # Apple IAP
    APPLE_IAP_SHARED_SECRET: str = Field(default="", env="APPLE_IAP_SHARED_SECRET")
    
    # Google Play
    GOOGLE_PLAY_SERVICE_ACCOUNT_PATH: str = Field(default="", env="GOOGLE_PLAY_SERVICE_ACCOUNT_PATH")
    
    # ========== Logging ==========
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # 'json' or 'text'
    
    # ========== Rate Limiting ==========
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    
    # Tier limits (requests per minute)
    RATE_LIMIT_FREE: int = Field(default=5, env="RATE_LIMIT_FREE")
    RATE_LIMIT_PREMIUM: int = Field(default=30, env="RATE_LIMIT_PREMIUM")
    RATE_LIMIT_VIP: int = Field(default=100, env="RATE_LIMIT_VIP")
    
    # ========== Credits ==========
    # Daily credit limits
    DAILY_CREDITS_FREE: float = Field(default=10.0, env="DAILY_CREDITS_FREE")
    DAILY_CREDITS_PREMIUM: float = Field(default=100.0, env="DAILY_CREDITS_PREMIUM")
    DAILY_CREDITS_VIP: float = Field(default=500.0, env="DAILY_CREDITS_VIP")
    
    # Cost per 1000 tokens (in credits)
    COST_PER_1K_TOKENS: float = Field(default=0.10, env="COST_PER_1K_TOKENS")
    
    # Tier discounts
    DISCOUNT_PREMIUM: float = Field(default=0.7, env="DISCOUNT_PREMIUM")  # 30% off
    DISCOUNT_VIP: float = Field(default=0.5, env="DISCOUNT_VIP")  # 50% off
    
    # ========== Content Moderation ==========
    MODERATION_ENABLED: bool = Field(default=True, env="MODERATION_ENABLED")
    MODERATION_USE_OPENAI: bool = Field(default=False, env="MODERATION_USE_OPENAI")
    
    # ========== Monitoring ==========
    SENTRY_DSN: str = Field(default="", env="SENTRY_DSN")
    PROMETHEUS_ENABLED: bool = Field(default=False, env="PROMETHEUS_ENABLED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instantiate settings
settings = Settings()


# ============================================================================
# Helper Functions
# ============================================================================

def is_production() -> bool:
    """Check if running in production environment."""
    return settings.ENVIRONMENT.lower() == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return settings.ENVIRONMENT.lower() == "development"


def get_database_config() -> dict:
    """Get database configuration dict."""
    return {
        "dsn": settings.DATABASE_URL,
        "min_size": 5,
        "max_size": settings.DATABASE_POOL_SIZE,
        "timeout": settings.DATABASE_POOL_TIMEOUT,
    }


def get_redis_config() -> dict:
    """Get Redis configuration dict."""
    return {
        "url": settings.REDIS_URL,
        "max_connections": settings.REDIS_MAX_CONNECTIONS,
        "decode_responses": True,
    }


def get_tier_limits() -> dict:
    """Get rate limit configuration by tier."""
    return {
        "free": settings.RATE_LIMIT_FREE,
        "premium": settings.RATE_LIMIT_PREMIUM,
        "vip": settings.RATE_LIMIT_VIP,
    }


def get_daily_credit_limits() -> dict:
    """Get daily credit limits by tier."""
    return {
        "free": settings.DAILY_CREDITS_FREE,
        "premium": settings.DAILY_CREDITS_PREMIUM,
        "vip": settings.DAILY_CREDITS_VIP,
    }

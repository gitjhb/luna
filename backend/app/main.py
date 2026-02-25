"""
AI Companion Backend - FastAPI Application
Main entry point with middleware and router configuration
"""

# ============================================================
# CRITICAL: Load .env FIRST before any other imports
# This ensures all modules get correct environment variables
# ============================================================
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import init_db, close_db
from app.core.redis import init_redis, close_redis
from app.core.exceptions import AppException
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.billing_middleware import BillingMiddleware
from app.middleware.logging_middleware import LoggingMiddleware

# Import routers
from app.api.v1 import auth, chat, characters, wallet, market, voice, image, images, intimacy, pricing, payment, gifts, scenarios, emotion, user_settings, interests, referral, events, interactions, debug, dates, photos, stamina, push, daily_reward, admin, proactive, proactive_v2, user_insights, stories, telegram


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting AI Companion Backend...")
    
    # Initialize database connection pool
    await init_db()
    logger.info("Database connection pool initialized")
    
    # Initialize Redis connection
    await init_redis()
    logger.info("Redis connection initialized")
    
    # Initialize Firebase Admin SDK
    try:
        from app.api.v1.auth import get_firebase_app
        firebase_app = get_firebase_app()
        if firebase_app:
            logger.info("Firebase Admin SDK ready")
        else:
            logger.warning("Firebase Admin SDK not configured")
    except Exception as e:
        logger.error(f"Firebase initialization error: {e}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Companion Backend...")
    
    await close_db()
    logger.info("Database connections closed")
    
    await close_redis()
    logger.info("Redis connections closed")
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Luna AI Companion API",
    description="""
    🌙 Luna AI Companion Platform - Backend API

    A sophisticated emotional AI companion platform that provides:
    
    - **Chat System**: Real-time conversations with AI characters
    - **Character Management**: Multiple unique AI personalities
    - **Intimacy & Progress**: Relationship building mechanics
    - **Voice & Audio**: Text-to-speech and voice interactions
    - **Image Generation**: AI-powered image creation
    - **Gamification**: Points, gifts, scenarios, and achievements
    - **Subscription Management**: Tiered access and billing
    - **User Personalization**: Settings, interests, and preferences
    
    ## Authentication
    Supports both Firebase Auth (Google/Apple Sign-In) and guest access.
    
    ## Rate Limiting
    API usage is tracked by credits. Free users get daily limits, premium users get higher allowances.
    
    ## Content Ratings
    - **Safe**: General conversations
    - **Flirty**: Light romantic content 
    - **Spicy**: Adult content (Premium+ only)
    
    ## Development
    This API supports both production and development modes with extensive debugging endpoints.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc", 
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Luna AI Team",
        "email": "support@luna-ai.com",
        "url": "https://luna2077-ai.vercel.app"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://luna2077-ai.vercel.app/terms-of-service"
    },
    servers=[
        {
            "url": "https://luna-backend-1081215078404.us-west1.run.app", 
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
)

# Setup logging
setup_logging()


# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware (order matters: last added = first executed)
app.add_middleware(LoggingMiddleware)
app.add_middleware(BillingMiddleware)  # Must be after Auth
app.add_middleware(AuthMiddleware)     # Must be first (after logging)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Handle custom application exceptions.
    """
    logger.error(f"Application error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unexpected errors.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred"
        }
    )


# ============================================================================
# Router Configuration
# ============================================================================

# API v1 routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(characters.router, prefix="/api/v1", tags=["Characters"])
app.include_router(wallet.router, prefix="/api/v1", tags=["Wallet"])
app.include_router(market.router, prefix="/api/v1", tags=["Market"])
app.include_router(voice.router, prefix="/api/v1", tags=["Voice"])
app.include_router(image.router, prefix="/api/v1", tags=["Image"])
app.include_router(images.router, prefix="/api/v1", tags=["Images"])
app.include_router(intimacy.router, prefix="/api/v1", tags=["Intimacy"])
app.include_router(pricing.router, prefix="/api/v1", tags=["Pricing"])
app.include_router(payment.router, prefix="/api/v1", tags=["Payment"])
app.include_router(gifts.router, prefix="/api/v1", tags=["Gifts"])
app.include_router(scenarios.router, prefix="/api/v1", tags=["Scenarios"])
app.include_router(emotion.router, prefix="/api/v1", tags=["Emotion"])
app.include_router(user_settings.router, prefix="/api/v1", tags=["Settings"])
app.include_router(interests.router, prefix="/api/v1", tags=["Interests"])
app.include_router(referral.router, prefix="/api/v1", tags=["Referral"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(interactions.router, prefix="/api/v1", tags=["Interactions"])
app.include_router(debug.router, prefix="/api/v1", tags=["Debug"])
app.include_router(dates.router, prefix="/api/v1", tags=["Dates"])
app.include_router(photos.router, prefix="/api/v1", tags=["Photos"])
app.include_router(stamina.router, prefix="/api/v1", tags=["Stamina"])
app.include_router(push.router, prefix="/api/v1", tags=["Push"])
app.include_router(daily_reward.router, prefix="/api/v1", tags=["DailyReward"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
app.include_router(proactive.router, prefix="/api/v1", tags=["Proactive"])
app.include_router(proactive_v2.router, prefix="/api/v1", tags=["Proactive-v2"])
app.include_router(user_insights.router, prefix="/api/v1", tags=["User Insights"])
app.include_router(stories.router, prefix="/api/v1", tags=["Stories"])
app.include_router(telegram.router, prefix="/api/v1", tags=["Telegram"])

# Static files (privacy policy, terms, etc.)
import os
from fastapi.staticfiles import StaticFiles
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Admin dashboard static files
admin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "admin")
if os.path.isdir(admin_dir):
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": "AI Companion API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers.
    """
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check with dependency status.
    """
    from app.core.database import get_db
    from app.core.redis import get_redis
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check database
    try:
        async with get_db() as db:
            await db.fetchval("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


# ============================================================================
# Metrics Endpoint (for Prometheus)
# ============================================================================

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Prometheus metrics endpoint.
    TODO: Implement actual metrics collection.
    """
    return {
        "message": "Metrics endpoint - integrate with prometheus_client"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

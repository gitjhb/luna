"""
AI Companion Backend - FastAPI Application
Main entry point with middleware and router configuration
"""

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
from app.api.v1 import auth, chat, characters, wallet, market, voice, image


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
    
    # TODO: Initialize vector database connection
    # await init_vector_db()
    
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
    title="AI Companion API",
    description="Backend API for AI Emotional Companion Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
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

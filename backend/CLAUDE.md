# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Luna AI Companion backend - a FastAPI server powering an emotional AI companion mobile app. Users chat with AI characters (Luna, Vera, Karl, etc.), build relationships, earn rewards, and unlock content.

## Commands

```bash
# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run single test file / single test
pytest tests/test_chat_service.py -v
pytest tests/test_chat_service.py::test_name -v

# Format / lint
black app/
isort app/
flake8 app/
mypy app/

# Docker (alternative)
make up          # Start all services
make down        # Stop all services
make test        # Run tests in container
```

## Architecture

### Tech Stack
- **FastAPI** async Python, **SQLAlchemy 2.0** async ORM (SQLite dev / PostgreSQL prod)
- **Redis** for caching, **Celery** for background tasks
- **xAI Grok** for chat LLM, **OpenAI** for embeddings only (never for chat)
- **ChromaDB** (dev) / **Pinecone** (prod) for vector memory
- **Firebase Auth** + guest login, **Stripe** payments

### Three-Layer Chat Pipeline

The core system in `app/api/v1/chat.py` → `app/services/chat_service.py`:

1. **L1 Perception** (`perception_engine.py`) - Intent analysis, safety checks, sentiment
2. **Game Engine** (`game_engine.py`) - Emotion updates, intimacy checks, content filtering, event triggers
3. **L2 Execution** (`chat_service.py`) - Memory retrieval (RAG), prompt building, LLM call

**V4 pipeline** (`app/services/v4/chat_pipeline_v4.py`) combines all layers into one LLM call. Controlled by `USE_V4_PIPELINE` env var.

### Key Directories
- `app/api/v1/` - Route handlers (~30 routers, all under `/api/v1/`)
- `app/services/` - Business logic (chat, emotion, memory, intimacy, billing, etc.)
- `app/services/llm/` - LLM integrations (grok_chat.py, openai_embedding.py)
- `app/services/memory_system_v2/` - Three-tier memory: working + semantic + episodic
- `app/services/emotion_engine_v2/` - 8-dimension emotion tracking with decay
- `app/models/database/` - SQLAlchemy ORM models
- `app/models/schemas/` - Pydantic request/response schemas
- `app/prompts/` - Character personality definitions
- `app/core/` - DB, Redis, logging, auth JWT, exceptions
- `app/middleware/` - Auth → Billing → Logging (order matters in `main.py`)

### Database
- Factory pattern in `app/core/db/factory.py` - swaps SQLite/Supabase via `DB_BACKEND` env var
- Connection management in `app/core/database.py`
- Migrations in `migrations/`

### Mock Modes for Local Dev
Set in `.env` (see `.env.example`):
- `MOCK_AUTH=true` - Skip Firebase, use `X-User-ID` header
- `MOCK_LLM=true` - Return fake LLM responses
- `MOCK_DATABASE=true` - In-memory DB
- `MOCK_REDIS=true` - Skip Redis

### Config
`app/config.py` uses Pydantic Settings. All config via env vars, loaded from `.env`.

### Deployment
- **Production**: Google Cloud Run (`cloudbuild.yaml`)
- **Alternative**: Vercel serverless (`vercel.json`)
- **Docker**: `docker-compose.yml` (postgres, redis, chromadb, api, celery)

### Design Docs
`docs/` contains authoritative references: CHAT_FLOW.md, MEMORY_SYSTEM.md, EMOTION_SYSTEM.md, INTIMACY_SYSTEM.md, GIFT_SYSTEM.md, SUBSCRIPTION_DESIGN.md, PROACTIVE_SYSTEM.md.

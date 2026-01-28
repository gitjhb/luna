# AI Companion Backend - Project Structure

```
ai-companion-backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application entry point
│   ├── config.py                        # Configuration and environment variables
│   ├── dependencies.py                  # Dependency injection containers
│   │
│   ├── api/                             # API route handlers
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # /auth/* endpoints
│   │   │   ├── chat.py                  # /chat/* endpoints
│   │   │   ├── characters.py            # /config/characters/* endpoints
│   │   │   ├── wallet.py                # /wallet/* endpoints
│   │   │   ├── market.py                # /market/* endpoints
│   │   │   └── admin.py                 # /admin/* endpoints (optional)
│   │
│   ├── models/                          # Database models and schemas
│   │   ├── __init__.py
│   │   ├── database/                    # SQLAlchemy/asyncpg models
│   │   │   ├── __init__.py
│   │   │   ├── user.py                  # User model
│   │   │   ├── wallet.py                # UserWallet, TransactionHistory
│   │   │   ├── character.py             # CharacterConfig model
│   │   │   ├── chat.py                  # ChatSession, ChatMessage models
│   │   │   └── payment.py               # PaymentTransaction model
│   │   │
│   │   └── schemas/                     # Pydantic schemas (request/response)
│   │       ├── __init__.py
│   │       ├── auth.py                  # LoginRequest, UserResponse
│   │       ├── chat.py                  # ChatCompletionRequest, ChatMessage
│   │       ├── character.py             # CharacterResponse
│   │       ├── wallet.py                # WalletBalance, Transaction
│   │       └── market.py                # Product, PurchaseRequest
│   │
│   ├── services/                        # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py              # Firebase authentication
│   │   ├── chat_service.py              # Chat logic with RAG
│   │   ├── character_service.py         # Character management
│   │   ├── wallet_service.py            # Wallet and transaction logic
│   │   ├── market_service.py            # Payment and subscription logic
│   │   ├── llm_service.py               # Grok API wrapper
│   │   └── vector_service.py            # Pinecone/ChromaDB operations
│   │
│   ├── middleware/                      # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth_middleware.py           # Firebase token verification
│   │   ├── billing_middleware.py        # Credit check & deduction
│   │   ├── rate_limit_middleware.py     # Rate limiting
│   │   └── logging_middleware.py        # Request/response logging
│   │
│   ├── core/                            # Core utilities and infrastructure
│   │   ├── __init__.py
│   │   ├── database.py                  # PostgreSQL connection pool
│   │   ├── redis.py                     # Redis connection
│   │   ├── security.py                  # Hashing, encryption, tokens
│   │   ├── exceptions.py                # Custom exception classes
│   │   └── logging.py                   # Logging configuration
│   │
│   ├── tasks/                           # Background tasks (Celery)
│   │   ├── __init__.py
│   │   ├── celery_app.py                # Celery configuration
│   │   ├── credit_refresh.py            # Daily credit refresh task
│   │   └── analytics.py                 # Analytics aggregation tasks
│   │
│   └── utils/                           # Utility functions
│       ├── __init__.py
│       ├── moderation.py                # Content moderation
│       ├── cost_calculator.py           # Credit cost calculations
│       ├── validators.py                # Input validation helpers
│       └── formatters.py                # Response formatting
│
├── migrations/                          # Database migrations (Alembic)
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_character_config.py
│   │   └── ...
│   ├── env.py
│   └── alembic.ini
│
├── tests/                               # Test suite
│   ├── __init__.py
│   ├── conftest.py                      # Pytest fixtures
│   ├── unit/
│   │   ├── test_billing_middleware.py
│   │   ├── test_chat_service.py
│   │   ├── test_cost_calculator.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_auth_flow.py
│   │   ├── test_chat_flow.py
│   │   ├── test_payment_flow.py
│   │   └── ...
│   └── load/
│       └── locustfile.py                # Load testing with Locust
│
├── scripts/                             # Utility scripts
│   ├── seed_characters.py               # Seed initial character data
│   ├── seed_users.py                    # Create test users
│   ├── migrate_db.py                    # Database migration helper
│   └── cleanup_old_sessions.py          # Maintenance scripts
│
├── docker/                              # Docker configurations
│   ├── Dockerfile                       # Main application Dockerfile
│   ├── Dockerfile.celery                # Celery worker Dockerfile
│   └── nginx.conf                       # Nginx configuration (if needed)
│
├── .env.example                         # Example environment variables
├── .env                                 # Local environment variables (gitignored)
├── .gitignore
├── docker-compose.yml                   # Local development stack
├── docker-compose.prod.yml              # Production stack
├── requirements.txt                     # Python dependencies
├── requirements-dev.txt                 # Development dependencies
├── pyproject.toml                       # Python project configuration
├── pytest.ini                           # Pytest configuration
├── README.md                            # Project documentation
└── Makefile                             # Common commands (run, test, migrate)
```

## Key Files Description

### `app/main.py`
FastAPI application initialization, middleware registration, router inclusion.

### `app/config.py`
Environment variable loading, configuration classes (DatabaseConfig, RedisConfig, etc.).

### `app/dependencies.py`
Dependency injection for database sessions, Redis clients, services.

### `app/middleware/billing_middleware.py`
**Critical**: Intercepts chat requests, checks credits, enforces rate limits, deducts credits atomically.

### `app/services/chat_service.py`
**Critical**: Main chat logic with RAG, context building, Grok API calls, message storage.

### `app/services/llm_service.py`
Grok API wrapper with retry logic, error handling, token estimation.

### `app/services/vector_service.py`
Vector database abstraction (Pinecone/ChromaDB), embedding generation, similarity search.

### `app/core/database.py`
PostgreSQL connection pool using asyncpg, transaction management.

### `app/core/redis.py`
Redis connection pool, caching utilities.

### `app/utils/cost_calculator.py`
Credit cost calculation based on tokens and subscription tier.

### `app/utils/moderation.py`
Content moderation filters (keyword blocking, pattern matching).

### `migrations/`
Alembic database migrations for schema versioning.

### `docker-compose.yml`
Local development stack:
- PostgreSQL
- Redis
- Pinecone (or ChromaDB)
- FastAPI app
- Celery worker
- Celery beat

### `requirements.txt`
Core dependencies:
- fastapi
- uvicorn
- asyncpg
- redis
- pinecone-client / chromadb
- httpx
- tenacity
- firebase-admin
- celery
- alembic
- pydantic
- python-dotenv

---

## Module Import Structure

```python
# Example imports in a route handler (app/api/v1/chat.py)

from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.services.chat_service import ChatService
from app.middleware.billing_middleware import CreditCheckDependency
from app.dependencies import get_current_user, get_chat_service
from app.models.schemas.auth import UserContext

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completion(
    request: ChatCompletionRequest,
    user: UserContext = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return await chat_service.chat_completion(request, user)
```

---

## Configuration Management

### `.env.example`
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_companion
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379/0

# Vector DB
VECTOR_DB_PROVIDER=pinecone  # or chromadb
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=ai-companion-memories

# LLM
XAI_API_KEY=your_xai_key
OPENAI_API_KEY=your_openai_key  # For embeddings

# Firebase
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# App
SECRET_KEY=your_secret_key
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Payment (Optional)
STRIPE_SECRET_KEY=your_stripe_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret
```

---

## Development Workflow

### 1. Setup
```bash
# Clone repository
git clone <repo_url>
cd ai-companion-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Start infrastructure (Docker)
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_characters.py
```

### 2. Run Development Server
```bash
# Start FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

### 3. Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_billing_middleware.py -v

# Load testing
locust -f tests/load/locustfile.py
```

### 4. Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Production Deployment

### Docker Build
```bash
# Build image
docker build -t ai-companion-backend:latest .

# Run container
docker run -d \
  --name ai-companion-api \
  -p 8000:8000 \
  --env-file .env \
  ai-companion-backend:latest
```

### Docker Compose (Production)
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes (Optional)
- Helm charts in `k8s/` directory
- Separate deployments for API, Celery worker, Celery beat
- Horizontal Pod Autoscaling based on CPU/memory

---

## Monitoring & Observability

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Centralized logging with ELK stack or CloudWatch

### Metrics
- Prometheus metrics endpoint: `/metrics`
- Key metrics:
  - Request latency
  - Credit deduction rate
  - LLM API latency
  - Error rates
  - Active sessions

### Tracing
- OpenTelemetry integration
- Distributed tracing for request flows

### Alerting
- PagerDuty/Opsgenie integration
- Alerts for:
  - High error rates
  - Credit balance anomalies
  - LLM API failures
  - Database connection issues

---

## Security Considerations

1. **API Keys**: Never commit to git, use environment variables
2. **Firebase Credentials**: Store securely, rotate regularly
3. **Database**: Use connection pooling, prepared statements
4. **Rate Limiting**: Enforce strictly to prevent abuse
5. **Content Moderation**: Log all flagged content for review
6. **HTTPS**: Enforce TLS 1.3 in production
7. **CORS**: Whitelist only trusted origins
8. **Input Validation**: Validate all user inputs with Pydantic
9. **SQL Injection**: Use parameterized queries (asyncpg handles this)
10. **Secrets Management**: Use AWS Secrets Manager or HashiCorp Vault

---

## Next Steps

1. Implement all route handlers in `app/api/v1/`
2. Write comprehensive unit tests
3. Set up CI/CD pipeline (GitHub Actions)
4. Configure production database (AWS RDS, Google Cloud SQL)
5. Deploy to cloud (AWS ECS, Google Cloud Run, or Kubernetes)
6. Set up monitoring and alerting
7. Implement payment webhooks (Stripe, Apple IAP, Google Play)
8. Add admin dashboard for character management
9. Implement analytics and reporting
10. Scale horizontally with load balancer

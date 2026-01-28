# AI Emotional Companion Platform - Backend

A scalable, high-performance backend infrastructure for an AI Emotional Companion platform built with FastAPI, PostgreSQL, Redis, Vector DB, and xAI Grok integration.

## 🏗️ Architecture Overview

### Technology Stack
- **API Framework**: FastAPI (Async)
- **Database**: PostgreSQL (User data, credits, transactions)
- **Cache & Rate Limiting**: Redis
- **Vector Database**: Pinecone (production) / ChromaDB (development)
- **LLM Provider**: xAI Grok API
- **Authentication**: Firebase Admin SDK
- **Task Queue**: Celery + Redis
- **Embeddings**: OpenAI text-embedding-3-small

### Key Features
- ✅ **Credit-Based Billing System** with atomic transactions
- ✅ **RAG-Powered Chat** with vector memory for premium users
- ✅ **Tier-Based Rate Limiting** (Free, Premium, VIP)
- ✅ **Daily Credit Refresh** mechanism
- ✅ **Content Moderation** hooks
- ✅ **Decoupled Architecture** for multiple frontend skins
- ✅ **Horizontal Scalability** ready

## 📁 Project Structure

```
ai-companion-backend/
├── app/
│   ├── api/v1/              # API route handlers
│   ├── models/              # Database models & Pydantic schemas
│   ├── services/            # Business logic layer
│   ├── middleware/          # Custom middleware (auth, billing, rate limit)
│   ├── core/                # Core utilities (database, redis, exceptions)
│   ├── tasks/               # Celery background tasks
│   └── utils/               # Utility functions
├── migrations/              # Alembic database migrations
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
└── docker/                  # Docker configurations
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- xAI API Key
- OpenAI API Key (for embeddings)
- Firebase Project (for authentication)

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai-companion-backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 5. Start Infrastructure (Docker)
```bash
docker-compose up -d postgres redis
```

### 6. Run Database Migrations
```bash
alembic upgrade head
```

### 7. Seed Initial Data
```bash
python scripts/seed_characters.py
```

### 8. Start Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 9. Start Celery Worker (Optional)
```bash
# Terminal 2
celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 3
celery -A app.tasks.celery_app beat --loglevel=info
```

## 📚 API Documentation

Once the server is running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/login` - Login with Firebase token
- `GET /api/v1/auth/me` - Get current user profile

#### Chat
- `POST /api/v1/chat/sessions` - Create new chat session
- `GET /api/v1/chat/sessions` - List user's sessions
- `POST /api/v1/chat/completions` - Send message and get AI response
- `GET /api/v1/chat/sessions/{session_id}/messages` - Get chat history

#### Characters
- `GET /api/v1/config/characters` - List available characters
- `GET /api/v1/config/characters/{character_id}` - Get character details

#### Wallet
- `GET /api/v1/wallet/balance` - Get credit balance
- `GET /api/v1/wallet/transactions` - Get transaction history

#### Market
- `GET /api/v1/market/products` - List credit packages and subscriptions
- `POST /api/v1/market/buy_credits` - Purchase credits
- `POST /api/v1/market/subscribe` - Subscribe to plan

## 🔧 Configuration

### Environment Variables

Key configuration variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_companion

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM APIs
XAI_API_KEY=your-xai-api-key
OPENAI_API_KEY=your-openai-api-key

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=/path/to/credentials.json

# Vector DB
VECTOR_DB_PROVIDER=chromadb  # or 'pinecone'
PINECONE_API_KEY=your-pinecone-key
```

### Subscription Tiers

| Tier    | Daily Credits | Requests/Min | Cost per 1k Tokens | Features                |
|---------|---------------|--------------|-------------------|-------------------------|
| Free    | 10            | 5            | 0.1 credits       | Basic chat              |
| Premium | 100           | 30           | 0.07 credits      | RAG memory, 30% off     |
| VIP     | 500           | 100          | 0.05 credits      | Advanced RAG, 50% off   |

## 🧪 Testing

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test
```bash
pytest tests/unit/test_billing_middleware.py -v
```

### Load Testing
```bash
locust -f tests/load/locustfile.py
```

## 📊 Database Schema

### Core Tables
- `users` - User accounts and subscription info
- `user_wallet` - Credit balances and daily refresh tracking
- `transaction_history` - All credit transactions
- `character_config` - AI character configurations
- `chat_sessions` - Chat session metadata
- `chat_messages` - Individual messages
- `payment_transactions` - Payment records

### Vector Database
- **Namespace per user**: `user_{user_id}` (strict data isolation)
- **Metadata**: user_id, session_id, message_id, role, content, timestamp

## 🔒 Security

### Best Practices Implemented
- ✅ Firebase token verification for authentication
- ✅ Row-level security in PostgreSQL
- ✅ Atomic credit transactions with database locks
- ✅ Rate limiting per subscription tier
- ✅ Content moderation for illegal content
- ✅ CORS configuration
- ✅ Environment variable management
- ✅ SQL injection prevention (parameterized queries)

### Content Moderation Policy
- **BLOCKED**: Child exploitation, terrorism, violence, illegal activities
- **ALLOWED**: NSFW/adult content, flirting, suggestive themes (per Grok's policy)

## 🚢 Deployment

### Docker Deployment
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

### Environment-Specific Configurations
- **Development**: SQLite/ChromaDB, debug logging
- **Staging**: PostgreSQL/Pinecone, info logging
- **Production**: PostgreSQL/Pinecone, error logging, monitoring

## 📈 Monitoring

### Health Checks
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed service status

### Metrics (Prometheus)
- `GET /metrics` - Prometheus metrics endpoint

### Key Metrics to Monitor
- Request latency
- Credit deduction rate
- LLM API latency
- Error rates
- Active sessions
- Database connection pool usage

## 🔄 Background Tasks

### Celery Tasks
- **Daily Credit Refresh**: Runs at midnight UTC to refresh daily credits
- **Analytics Aggregation**: Periodic analytics data aggregation
- **Session Cleanup**: Remove inactive sessions

### Task Configuration
```python
# celerybeat-schedule.py
CELERY_BEAT_SCHEDULE = {
    'refresh-daily-credits': {
        'task': 'tasks.refresh_daily_credits',
        'schedule': crontab(hour=0, minute=0),
    },
}
```

## 🛠️ Development Workflow

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/

# Type checking
mypy app/
```

## 📦 Credit Packages

### Available Packages
```json
{
  "credits_10": {"credits": 10, "price": 0.99},
  "credits_50": {"credits": 50, "price": 4.99},
  "credits_100": {"credits": 100, "price": 8.99},  // 10% bonus
  "credits_500": {"credits": 550, "price": 39.99}, // 20% bonus
  "credits_1000": {"credits": 1200, "price": 69.99} // 30% bonus
}
```

### Subscription Plans
```json
{
  "premium_monthly": {"price": 9.99, "bonus_credits": 200},
  "premium_yearly": {"price": 99.99, "bonus_credits": 2500},
  "vip_monthly": {"price": 29.99, "bonus_credits": 1000},
  "vip_yearly": {"price": 299.99, "bonus_credits": 13000}
}
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

### Code Style
- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions small and focused

## 📝 License

[Your License Here]

## 🆘 Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Email: support@yourcompany.com
- Documentation: [docs-url]

## 🎯 Roadmap

### Phase 1 (MVP) ✅
- [x] Core API endpoints
- [x] Credit billing system
- [x] RAG-powered chat
- [x] Firebase authentication

### Phase 2 (Enhancements)
- [ ] Streaming chat responses
- [ ] Voice message support
- [ ] Image generation integration
- [ ] Admin dashboard

### Phase 3 (Scale)
- [ ] Kubernetes deployment
- [ ] Multi-region support
- [ ] Advanced analytics
- [ ] A/B testing framework

## 🙏 Acknowledgments

- FastAPI framework
- xAI Grok API
- Pinecone vector database
- Firebase authentication
- OpenAI embeddings

---

**Built with ❤️ for high-net-worth users seeking AI companionship**

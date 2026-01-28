# AI Emotional Companion Platform

A scalable, production-ready AI Emotional Companion platform with a FastAPI backend and React Native mobile frontend.

## Project Structure

```
.
├── backend/              # FastAPI Python Backend
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   │   └── v1/       # API version 1 endpoints
│   │   ├── models/       # Database models and schemas
│   │   │   ├── database/ # SQLAlchemy models
│   │   │   └── schemas/  # Pydantic schemas
│   │   ├── services/     # Business logic layer
│   │   ├── middleware/   # Custom middleware (auth, billing)
│   │   ├── core/         # Core utilities (database, redis, etc.)
│   │   ├── tasks/        # Background tasks (Celery)
│   │   └── utils/        # Utility functions
│   ├── docker/           # Docker configurations
│   ├── migrations/       # Database migrations (Alembic)
│   ├── tests/            # Test suite
│   ├── scripts/          # Utility scripts
│   ├── requirements.txt  # Python dependencies
│   ├── docker-compose.yml
│   ├── Makefile
│   └── .env              # Environment variables (gitignored)
│
├── frontend/             # React Native Mobile App (Expo)
│   ├── app/              # Expo Router file-based routing
│   │   ├── (tabs)/       # Tab navigation (index, chats, profile)
│   │   ├── auth/         # Login screen
│   │   └── chat/         # Chat screen
│   ├── components/       # React components
│   │   ├── atoms/        # Basic UI elements
│   │   ├── molecules/    # Composite components
│   │   └── organisms/    # Complex components
│   ├── services/         # API service layer
│   ├── store/            # Zustand state management
│   ├── theme/            # White-label theme config
│   ├── types/            # TypeScript definitions
│   ├── assets/           # Images, fonts, etc.
│   ├── package.json
│   ├── app.json
│   └── tsconfig.json
│
└── docs/                 # Documentation
    ├── AI Emotional Companion Platform - Backend Architecture Design.md
    ├── AI Companion Mobile App.md
    ├── API Endpoints Specification.md
    ├── project_structure.md
    └── ...
```

## Technology Stack

### Backend
- **Framework:** FastAPI (Async Python)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Vector DB:** Pinecone / ChromaDB
- **LLM:** xAI Grok API
- **Auth:** Firebase Admin SDK
- **Task Queue:** Celery
- **Deployment:** Docker + Docker Compose

### Frontend
- **Framework:** Expo (React Native)
- **Language:** TypeScript
- **Styling:** NativeWind (Tailwind CSS)
- **State:** Zustand + AsyncStorage
- **Networking:** Axios + TanStack Query
- **Auth:** Firebase

## Quick Start

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Start infrastructure with Docker
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env
# Edit .env with your API URL

# Start development server
npm start

# Run on iOS
npm run ios

# Run on Android
npm run android
```

## Key Features

### Backend
- Async FastAPI with automatic OpenAPI docs
- Credit-based billing system with atomic transactions
- RAG-powered chat with vector memory
- Real-time rate limiting with Redis
- Firebase authentication integration
- Docker containerization
- Celery background tasks for daily credit refresh
- PostgreSQL with connection pooling
- Content moderation pipeline

### Frontend
- White-label ready (single config file reskin)
- Dark luxury design theme
- Tinder-style character cards
- Real-time credit tracking
- Spicy mode with subscription gate
- Blur & unlock for NSFW content
- Optimized performance with FlatList
- Full TypeScript coverage
- Native iOS/Android support

## Documentation

All detailed documentation is available in the `docs/` directory:

- **Backend Architecture:** `docs/AI Emotional Companion Platform - Backend Architecture Design.md`
- **API Specification:** `docs/API Endpoints Specification.md`
- **Mobile App Guide:** `docs/AI Companion Mobile App.md`
- **Project Structure:** `docs/project_structure.md`
- **Deployment Guide:** `docs/DEPLOYMENT.md`

## Development Workflow

### Backend
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Create database migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Frontend
```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
eas build --platform ios
eas build --platform android
```

## Deployment

### Backend
- Docker images ready for AWS ECS, Google Cloud Run, or Kubernetes
- Production-ready with Gunicorn + Uvicorn workers
- Health check endpoints included

### Frontend
- Expo Application Services (EAS) for iOS/Android builds
- Over-the-air updates support
- App Store / Play Store ready

## Environment Variables

### Backend (.env)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `XAI_API_KEY` - xAI Grok API key
- `FIREBASE_CREDENTIALS_PATH` - Firebase service account JSON
- `PINECONE_API_KEY` - Pinecone API key

### Frontend (.env)
- `EXPO_PUBLIC_API_URL` - Backend API URL
- `EXPO_PUBLIC_FIREBASE_API_KEY` - Firebase config
- `EXPO_PUBLIC_MOCK_API` - Use mock API (true/false)

## License

[Your License Here]

## Support

For issues and questions, please refer to the documentation in the `docs/` directory.

---

**Built for scalable, premium AI companionship experiences**

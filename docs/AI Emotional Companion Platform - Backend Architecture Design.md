# AI Emotional Companion Platform - Backend Architecture Design

## 1. System Architecture Overview

### 1.1 Technology Stack
- **API Framework**: FastAPI (Async)
- **Primary Database**: PostgreSQL (User data, credits, transactions)
- **Cache & Rate Limiting**: Redis
- **Vector Database**: Pinecone (for production scalability) / ChromaDB (for development)
- **LLM Provider**: xAI Grok API
- **Authentication**: Firebase Admin SDK
- **Task Queue**: Celery + Redis (for daily credit refresh)
- **Monitoring**: Prometheus + Grafana (future)

### 1.2 High-Level Architecture

```
┌─────────────────┐
│  Mobile Apps    │
│ (iOS/Android)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌──────────────────────────────────┐  │
│  │   Auth Middleware (Firebase)     │  │
│  └──────────────┬───────────────────┘  │
│                 ▼                       │
│  ┌──────────────────────────────────┐  │
│  │  Billing Middleware              │  │
│  │  - Credit Check                  │  │
│  │  - Rate Limiting                 │  │
│  │  - Atomic Deduction              │  │
│  └──────────────┬───────────────────┘  │
│                 ▼                       │
│  ┌──────────────────────────────────┐  │
│  │  Business Logic Layer            │  │
│  │  - Chat Service (RAG)            │  │
│  │  - Character Service             │  │
│  │  - Wallet Service                │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │         │         │
         ▼         ▼         ▼
┌──────────┐ ┌─────────┐ ┌──────────┐
│PostgreSQL│ │  Redis  │ │ Pinecone │
└──────────┘ └─────────┘ └──────────┘
         │
         ▼
┌──────────────────┐
│  xAI Grok API    │
└──────────────────┘
```

## 2. Database Schema Design

### 2.1 PostgreSQL Schema

#### Table: `users`
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(255),
    display_name VARCHAR(100),
    subscription_tier VARCHAR(20) DEFAULT 'free', -- 'free', 'premium', 'vip'
    subscription_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    
    INDEX idx_firebase_uid (firebase_uid),
    INDEX idx_subscription_tier (subscription_tier)
);
```

#### Table: `user_wallet`
```sql
CREATE TABLE user_wallet (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Credit Balances
    total_credits DECIMAL(10, 2) DEFAULT 0.00,
    daily_free_credits DECIMAL(10, 2) DEFAULT 0.00,
    purchased_credits DECIMAL(10, 2) DEFAULT 0.00,
    bonus_credits DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Daily Refresh Tracking
    daily_credits_limit DECIMAL(10, 2) DEFAULT 10.00, -- Free: 10, Premium: 100, VIP: 500
    daily_credits_refreshed_at TIMESTAMP,
    
    -- Rate Limiting
    last_request_at TIMESTAMP,
    requests_today INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id)
);
```

#### Table: `transaction_history`
```sql
CREATE TABLE transaction_history (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Transaction Details
    transaction_type VARCHAR(50) NOT NULL, -- 'chat_deduction', 'purchase', 'daily_refresh', 'bonus', 'refund'
    amount DECIMAL(10, 2) NOT NULL, -- Positive for credit, negative for debit
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    
    -- Context
    reference_id VARCHAR(255), -- chat_session_id, payment_id, etc.
    metadata JSONB, -- {tokens_used: 150, model: "grok-beta", character_id: "xyz"}
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_transaction_type (transaction_type),
    INDEX idx_created_at (created_at)
);
```

#### Table: `character_config`
```sql
CREATE TABLE character_config (
    character_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Character Identity
    name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    description TEXT,
    personality_traits JSONB, -- ["flirty", "caring", "playful"]
    
    -- Access Control
    tier_required VARCHAR(20) DEFAULT 'free', -- 'free', 'premium', 'vip'
    is_active BOOLEAN DEFAULT TRUE,
    is_spicy BOOLEAN DEFAULT FALSE, -- Enables NSFW mode
    
    -- Prompt Configuration
    system_prompt TEXT NOT NULL,
    spicy_system_prompt TEXT, -- Override for premium users
    temperature DECIMAL(3, 2) DEFAULT 0.8,
    max_tokens INT DEFAULT 500,
    
    -- Metadata
    tags JSONB, -- ["anime", "girlfriend", "dominant"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_tier_required (tier_required),
    INDEX idx_is_active (is_active)
);
```

#### Table: `chat_sessions`
```sql
CREATE TABLE chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES character_config(character_id),
    
    -- Session Metadata
    title VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    total_messages INT DEFAULT 0,
    total_credits_spent DECIMAL(10, 2) DEFAULT 0.00,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_character_id (character_id),
    INDEX idx_created_at (created_at)
);
```

#### Table: `chat_messages`
```sql
CREATE TABLE chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Message Content
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    
    -- Cost Tracking
    tokens_used INT,
    credits_deducted DECIMAL(10, 2),
    
    -- Vector Embedding (stored separately in Pinecone)
    embedding_id VARCHAR(255), -- Reference to Pinecone vector ID
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```

#### Table: `payment_transactions`
```sql
CREATE TABLE payment_transactions (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Payment Details
    payment_provider VARCHAR(50), -- 'stripe', 'apple_iap', 'google_play'
    provider_transaction_id VARCHAR(255) UNIQUE,
    
    -- Product Info
    product_sku VARCHAR(100), -- 'credits_100', 'premium_monthly'
    product_type VARCHAR(50), -- 'credits', 'subscription'
    amount_usd DECIMAL(10, 2),
    credits_granted DECIMAL(10, 2),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'refunded'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_provider_transaction_id (provider_transaction_id)
);
```

### 2.2 Vector Database Structure (Pinecone)

#### Namespace Strategy
- **Namespace per user**: `user_{user_id}` (STRICT data isolation)

#### Vector Metadata Schema
```json
{
    "user_id": "uuid",
    "session_id": "uuid",
    "message_id": "uuid",
    "character_id": "uuid",
    "role": "user|assistant",
    "content": "original message text",
    "timestamp": "ISO8601",
    "embedding_model": "text-embedding-3-small"
}
```

#### Index Configuration
- **Dimension**: 1536 (OpenAI text-embedding-3-small)
- **Metric**: Cosine similarity
- **Pods**: Serverless (cost-effective for variable load)

### 2.3 Redis Data Structures

#### Rate Limiting (Token Bucket)
```
Key: rate_limit:{user_id}
Type: Hash
Fields:
  - tokens: <current_tokens>
  - last_refill: <timestamp>
  - tier: <free|premium|vip>
TTL: 86400 (24 hours)
```

#### Session Cache
```
Key: session:{session_id}
Type: Hash
Fields:
  - user_id
  - character_id
  - last_10_messages (JSON array)
TTL: 3600 (1 hour)
```

#### Daily Credit Refresh Tracking
```
Key: daily_refresh:{user_id}
Type: String
Value: <last_refresh_date YYYY-MM-DD>
TTL: 86400 (24 hours)
```

## 3. Daily Credit Refresh Mechanism

### 3.1 Approach: Celery Beat + PostgreSQL

#### Celery Task Configuration
```python
# celerybeat-schedule.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'refresh-daily-credits': {
        'task': 'tasks.refresh_daily_credits',
        'schedule': crontab(hour=0, minute=0),  # Midnight UTC
    },
}
```

#### Refresh Logic
1. **Trigger**: Celery Beat at midnight UTC
2. **Process**:
   - Query all active users
   - Reset `daily_free_credits` based on `subscription_tier`
   - Update `daily_credits_refreshed_at`
   - Create transaction record
3. **Fallback**: On-demand refresh check in billing middleware (if user hasn't been refreshed today)

### 3.2 Alternative: Lazy Refresh (On-Request)

Instead of batch processing, check and refresh on each request:

```python
async def check_and_refresh_daily_credits(user_id: UUID):
    wallet = await get_user_wallet(user_id)
    last_refresh = wallet.daily_credits_refreshed_at
    
    if last_refresh.date() < datetime.utcnow().date():
        # Refresh credits
        await refresh_user_daily_credits(user_id)
```

**Recommendation**: Use **Lazy Refresh** for MVP (simpler), migrate to Celery Beat for scale.

## 4. Credit Deduction Strategy

### 4.1 Atomic Transaction Flow

```python
async with db.transaction():
    # 1. Lock wallet row
    wallet = await db.execute(
        "SELECT * FROM user_wallet WHERE user_id = $1 FOR UPDATE",
        user_id
    )
    
    # 2. Verify sufficient balance
    if wallet.total_credits < cost:
        raise InsufficientCreditsError()
    
    # 3. Deduct credits (priority: daily_free > purchased > bonus)
    new_balance = wallet.total_credits - cost
    
    # 4. Update wallet
    await db.execute(
        "UPDATE user_wallet SET total_credits = $1, updated_at = NOW() WHERE user_id = $2",
        new_balance, user_id
    )
    
    # 5. Record transaction
    await db.execute(
        "INSERT INTO transaction_history (...) VALUES (...)"
    )
```

### 4.2 Cost Calculation

```python
def calculate_chat_cost(tokens_used: int, user_tier: str) -> Decimal:
    # Base cost: $0.01 per 1000 tokens (10 credits = $1)
    base_cost = Decimal(tokens_used) / 1000 * Decimal("0.10")  # 0.1 credits per 1k tokens
    
    # Tier discounts
    discounts = {
        "free": Decimal("1.0"),      # No discount
        "premium": Decimal("0.7"),   # 30% off
        "vip": Decimal("0.5")        # 50% off
    }
    
    return base_cost * discounts.get(user_tier, Decimal("1.0"))
```

## 5. Data Isolation & Security

### 5.1 Vector DB Isolation
- **Namespace per user**: Ensures queries never leak data across users
- **Metadata filtering**: Double-check `user_id` in query filters

### 5.2 PostgreSQL Row-Level Security (RLS)
```sql
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_messages_policy ON chat_messages
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);
```

### 5.3 API-Level Validation
- Every request validates `user_id` from JWT token
- No user can access another user's data via API manipulation

## 6. Scalability Considerations

### 6.1 Database Optimization
- **Connection Pooling**: asyncpg with pool size 20-50
- **Read Replicas**: Offload analytics queries
- **Partitioning**: Partition `chat_messages` by `created_at` (monthly)

### 6.2 Caching Strategy
- **Hot data**: Cache user wallet, character configs in Redis
- **Session context**: Cache last 10 messages per session
- **Invalidation**: TTL-based + manual invalidation on updates

### 6.3 Rate Limiting Tiers
| Tier    | Requests/Min | Daily Credits | Cost per 1k tokens |
|---------|--------------|---------------|--------------------|
| Free    | 5            | 10            | 0.1 credits        |
| Premium | 30           | 100           | 0.07 credits       |
| VIP     | 100          | 500           | 0.05 credits       |

## 7. Content Moderation Strategy

### 7.1 Moderation Pipeline
```
User Input → Pre-filter (Illegal keywords) → Grok API → Post-filter (Safety check) → Response
```

### 7.2 Blocked Content Categories
- **Illegal**: Child exploitation, terrorism, violence
- **Allowed (NSFW)**: Adult content, flirting, suggestive themes (Grok's policy)

### 7.3 Implementation Hooks
```python
async def moderate_content(text: str, mode: str = "input") -> bool:
    # TODO: Integrate OpenAI Moderation API or custom filter
    # For now: Basic keyword blacklist
    illegal_keywords = ["child", "minor", "underage", ...]
    
    if any(keyword in text.lower() for keyword in illegal_keywords):
        return False
    return True
```

## 8. Folder Structure Preview

```
ai-companion-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Environment variables
│   ├── dependencies.py         # DI containers
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py             # /auth/* endpoints
│   │   ├── chat.py             # /chat/* endpoints
│   │   ├── market.py           # /market/* endpoints
│   │   ├── config.py           # /config/* endpoints
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             # SQLAlchemy models
│   │   ├── wallet.py
│   │   ├── character.py
│   │   ├── chat.py
│   │   ├── schemas.py          # Pydantic schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── chat_service.py     # RAG + Grok integration
│   │   ├── wallet_service.py
│   │   ├── character_service.py
│   │   ├── vector_service.py   # Pinecone operations
│   │   ├── llm_service.py      # Grok API wrapper
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth_middleware.py  # Firebase token verification
│   │   ├── billing_middleware.py # Credit check & deduction
│   │   ├── rate_limit_middleware.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py         # PostgreSQL connection
│   │   ├── redis.py            # Redis connection
│   │   ├── security.py         # Hashing, tokens
│   │   ├── exceptions.py       # Custom exceptions
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── credit_refresh.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── moderation.py
│       ├── cost_calculator.py
│
├── migrations/                  # Alembic migrations
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Next Steps
1. Implement billing middleware with atomic credit deduction
2. Build RAG-powered chat service with Grok integration
3. Define REST API endpoints with OpenAPI specification
4. Write all core module implementations

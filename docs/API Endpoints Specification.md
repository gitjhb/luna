# API Endpoints Specification

## Base URL
```
Production: https://api.aicompanion.app/v1
Development: http://localhost:8000/api/v1
```

## Authentication
All endpoints (except `/auth/login`) require a Bearer token in the Authorization header:
```
Authorization: Bearer <firebase_id_token>
```

---

## 1. Authentication Endpoints

### POST `/auth/login`
Authenticate user with Firebase token and create/update user record.

**Request Body:**
```json
{
  "firebase_token": "string",
  "provider": "google" | "apple"
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "email": "string",
  "display_name": "string",
  "subscription_tier": "free" | "premium" | "vip",
  "wallet": {
    "total_credits": 10.00,
    "daily_free_credits": 10.00,
    "purchased_credits": 0.00
  },
  "access_token": "string"
}
```

**Errors:**
- `401 Unauthorized`: Invalid Firebase token
- `500 Internal Server Error`: Server error

---

### GET `/auth/me`
Get current user profile.

**Response (200):**
```json
{
  "user_id": "uuid",
  "email": "string",
  "display_name": "string",
  "subscription_tier": "free" | "premium" | "vip",
  "subscription_expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## 2. Chat Endpoints

### POST `/chat/sessions`
Create a new chat session.

**Request Body:**
```json
{
  "character_id": "uuid"
}
```

**Response (201):**
```json
{
  "session_id": "uuid",
  "character_id": "uuid",
  "character_name": "string",
  "character_avatar": "https://...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Character not found
- `403 Forbidden`: Character requires subscription

---

### GET `/chat/sessions`
List user's chat sessions.

**Query Parameters:**
- `limit` (optional, default: 20): Number of sessions to return
- `offset` (optional, default: 0): Pagination offset

**Response (200):**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "title": "Chat with Aria",
      "character_name": "Aria",
      "character_avatar": "https://...",
      "total_messages": 42,
      "total_credits_spent": 5.25,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-02T12:30:00Z"
    }
  ],
  "total": 10,
  "limit": 20,
  "offset": 0
}
```

---

### GET `/chat/sessions/{session_id}`
Get session details.

**Response (200):**
```json
{
  "session_id": "uuid",
  "title": "Chat with Aria",
  "character_id": "uuid",
  "character_name": "Aria",
  "character_avatar": "https://...",
  "total_messages": 42,
  "total_credits_spent": 5.25,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T12:30:00Z"
}
```

**Errors:**
- `404 Not Found`: Session not found

---

### GET `/chat/sessions/{session_id}/messages`
Get chat history for a session.

**Query Parameters:**
- `limit` (optional, default: 50): Number of messages to return
- `offset` (optional, default: 0): Pagination offset

**Response (200):**
```json
{
  "messages": [
    {
      "message_id": "uuid",
      "role": "user",
      "content": "Hello!",
      "tokens_used": 0,
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "message_id": "uuid",
      "role": "assistant",
      "content": "Hi there! How can I help you today?",
      "tokens_used": 150,
      "created_at": "2024-01-01T12:00:05Z"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

### POST `/chat/completions`
**Main chat endpoint** - Send message and get AI response.

**Request Body:**
```json
{
  "session_id": "uuid",
  "message": "string"
}
```

**Response (200):**
```json
{
  "message_id": "uuid",
  "content": "string",
  "tokens_used": 250,
  "credits_deducted": 0.025,
  "character_name": "Aria",
  "created_at": "2024-01-01T12:00:05Z"
}
```

**Errors:**
- `400 Bad Request`: Invalid request
- `402 Payment Required`: Insufficient credits
  ```json
  {
    "error": "insufficient_credits",
    "message": "You don't have enough credits",
    "current_balance": 0.50,
    "required": 1.00
  }
  ```
- `403 Forbidden`: Subscription required
- `429 Too Many Requests`: Rate limit exceeded
  ```json
  {
    "error": "rate_limit_exceeded",
    "message": "Too many requests",
    "retry_after": 30
  }
  ```
- `451 Unavailable For Legal Reasons`: Content moderation block
  ```json
  {
    "error": "content_moderation",
    "message": "Your message contains prohibited content"
  }
  ```

---

### POST `/chat/stream`
Streaming chat completion (SSE).

**Request Body:**
```json
{
  "session_id": "uuid",
  "message": "string"
}
```

**Response (200):** Server-Sent Events stream
```
data: {"type": "token", "content": "Hello"}
data: {"type": "token", "content": " there"}
data: {"type": "done", "message_id": "uuid", "tokens_used": 150, "credits_deducted": 0.015}
```

---

### DELETE `/chat/sessions/{session_id}`
Delete a chat session (soft delete).

**Response (204):** No content

**Errors:**
- `404 Not Found`: Session not found

---

## 3. Character Endpoints

### GET `/config/characters`
Get list of available characters.

**Query Parameters:**
- `tier` (optional): Filter by required tier ('free', 'premium', 'vip')
- `is_spicy` (optional): Filter by spicy mode (true/false)

**Response (200):**
```json
{
  "characters": [
    {
      "character_id": "uuid",
      "name": "Aria",
      "avatar_url": "https://...",
      "description": "A caring and empathetic companion",
      "personality_traits": ["caring", "empathetic", "playful"],
      "tier_required": "free",
      "is_spicy": false,
      "tags": ["girlfriend", "supportive"]
    },
    {
      "character_id": "uuid",
      "name": "Luna",
      "avatar_url": "https://...",
      "description": "A bold and flirtatious companion",
      "personality_traits": ["flirty", "confident", "playful"],
      "tier_required": "premium",
      "is_spicy": true,
      "tags": ["girlfriend", "flirty", "spicy"]
    }
  ]
}
```

---

### GET `/config/characters/{character_id}`
Get character details.

**Response (200):**
```json
{
  "character_id": "uuid",
  "name": "Aria",
  "avatar_url": "https://...",
  "description": "A caring and empathetic companion",
  "personality_traits": ["caring", "empathetic", "playful"],
  "tier_required": "free",
  "is_spicy": false,
  "tags": ["girlfriend", "supportive"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Character not found

---

## 4. Wallet & Billing Endpoints

### GET `/wallet/balance`
Get user's credit balance.

**Response (200):**
```json
{
  "total_credits": 25.50,
  "daily_free_credits": 10.00,
  "purchased_credits": 15.00,
  "bonus_credits": 0.50,
  "daily_credits_limit": 10.00,
  "daily_credits_refreshed_at": "2024-01-01T00:00:00Z"
}
```

---

### GET `/wallet/transactions`
Get transaction history.

**Query Parameters:**
- `limit` (optional, default: 50): Number of transactions to return
- `offset` (optional, default: 0): Pagination offset
- `type` (optional): Filter by transaction type

**Response (200):**
```json
{
  "transactions": [
    {
      "transaction_id": "uuid",
      "transaction_type": "chat_deduction",
      "amount": -0.025,
      "balance_before": 10.00,
      "balance_after": 9.975,
      "description": "Chat completion (250 tokens)",
      "created_at": "2024-01-01T12:00:05Z"
    },
    {
      "transaction_id": "uuid",
      "transaction_type": "purchase",
      "amount": 100.00,
      "balance_before": 9.975,
      "balance_after": 109.975,
      "description": "Credit purchase: 100 credits",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

## 5. Market & Payment Endpoints

### GET `/market/products`
Get available credit packages and subscriptions.

**Response (200):**
```json
{
  "credit_packages": [
    {
      "sku": "credits_10",
      "name": "10 Credits",
      "credits": 10.00,
      "price_usd": 0.99,
      "discount_percentage": 0
    },
    {
      "sku": "credits_100",
      "name": "100 Credits",
      "credits": 100.00,
      "price_usd": 8.99,
      "discount_percentage": 10
    },
    {
      "sku": "credits_500",
      "name": "500 Credits + 50 Bonus",
      "credits": 550.00,
      "price_usd": 39.99,
      "discount_percentage": 20
    }
  ],
  "subscriptions": [
    {
      "sku": "premium_monthly",
      "name": "Premium Monthly",
      "tier": "premium",
      "price_usd": 9.99,
      "billing_period": "monthly",
      "bonus_credits": 200.00,
      "features": [
        "100 daily free credits",
        "RAG memory system",
        "30% discount on credit purchases",
        "30 requests/minute"
      ]
    },
    {
      "sku": "vip_monthly",
      "name": "VIP Monthly",
      "tier": "vip",
      "price_usd": 29.99,
      "billing_period": "monthly",
      "bonus_credits": 1000.00,
      "features": [
        "500 daily free credits",
        "Advanced RAG memory",
        "50% discount on credit purchases",
        "100 requests/minute",
        "Priority support"
      ]
    }
  ]
}
```

---

### POST `/market/buy_credits`
Purchase credits (mock payment callback for development).

**Request Body:**
```json
{
  "product_sku": "credits_100",
  "payment_provider": "stripe" | "apple_iap" | "google_play",
  "provider_transaction_id": "string"
}
```

**Response (200):**
```json
{
  "transaction_id": "uuid",
  "credits_granted": 100.00,
  "new_balance": 125.50,
  "status": "completed"
}
```

**Errors:**
- `400 Bad Request`: Invalid product SKU
- `409 Conflict`: Duplicate transaction ID

---

### POST `/market/subscribe`
Subscribe to a plan (mock payment callback).

**Request Body:**
```json
{
  "subscription_sku": "premium_monthly",
  "payment_provider": "stripe" | "apple_iap" | "google_play",
  "provider_transaction_id": "string"
}
```

**Response (200):**
```json
{
  "subscription_tier": "premium",
  "subscription_expires_at": "2024-02-01T00:00:00Z",
  "bonus_credits_granted": 200.00,
  "new_balance": 325.50
}
```

---

### POST `/market/webhook/stripe`
Stripe webhook handler (for production payment processing).

**Headers:**
- `Stripe-Signature`: Webhook signature

**Request Body:** Stripe event payload

**Response (200):**
```json
{
  "received": true
}
```

---

## 6. Admin Endpoints (Optional)

### POST `/admin/characters`
Create a new character (admin only).

**Request Body:**
```json
{
  "name": "string",
  "avatar_url": "string",
  "description": "string",
  "personality_traits": ["string"],
  "tier_required": "free" | "premium" | "vip",
  "is_spicy": false,
  "system_prompt": "string",
  "spicy_system_prompt": "string",
  "temperature": 0.8,
  "max_tokens": 500,
  "tags": ["string"]
}
```

**Response (201):**
```json
{
  "character_id": "uuid",
  "name": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### PUT `/admin/characters/{character_id}`
Update character configuration.

**Request Body:** Same as POST `/admin/characters`

**Response (200):** Updated character object

---

### GET `/admin/stats`
Get platform statistics (admin only).

**Response (200):**
```json
{
  "total_users": 10000,
  "active_users_today": 2500,
  "total_sessions": 50000,
  "total_messages": 500000,
  "total_credits_spent": 25000.00,
  "total_revenue_usd": 15000.00
}
```

---

## Error Response Format

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    // Optional additional context
  }
}
```

### Common Error Codes
- `authentication_required`: Missing or invalid token
- `insufficient_credits`: Not enough credits
- `rate_limit_exceeded`: Too many requests
- `subscription_required`: Feature requires subscription
- `content_moderation`: Content violates policy
- `not_found`: Resource not found
- `validation_error`: Invalid request data
- `internal_error`: Server error

---

## Rate Limiting

Rate limits are enforced per user based on subscription tier:

| Tier    | Requests/Minute | Daily Credits |
|---------|-----------------|---------------|
| Free    | 5               | 10            |
| Premium | 30              | 100           |
| VIP     | 100             | 500           |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1704110400
```

---

## Pagination

List endpoints support pagination with `limit` and `offset` parameters:

**Request:**
```
GET /chat/sessions?limit=20&offset=40
```

**Response:**
```json
{
  "sessions": [...],
  "total": 100,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

---

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
```
GET /openapi.json
```

Interactive API documentation:
```
GET /docs (Swagger UI)
GET /redoc (ReDoc)
```

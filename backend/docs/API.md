# Luna AI Companion API Documentation

🌙 **Luna** is a sophisticated AI emotional companion platform that provides personalized, relationship-building conversations with AI characters.

## API Overview

- **Base URL**: `https://luna-backend-1081215078404.us-west1.run.app`
- **Development**: `http://localhost:8000`  
- **Interactive Docs**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)
- **OpenAPI Spec**: `/openapi.json`

## Authentication

Luna supports two authentication methods:

### 1. Firebase Auth (Recommended)
For production apps using Apple/Google Sign-In:
```http
POST /api/v1/auth/firebase
Content-Type: application/json

{
  "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Guest Login (Development)
For testing and demos (requires `ALLOW_GUEST=true`):
```http
POST /api/v1/auth/guest
```

### Authentication Headers
Include the access token in all API requests:
```http
Authorization: Bearer <access_token>
```

## Core Concepts

### Characters
AI companions with unique personalities, backstories, and conversation styles.
- **Romantic**: Relationship-focused with intimacy progression (1-100 levels)
- **Buddy**: Casual friendship dynamics for general conversation

### Chat Sessions
Persistent conversation threads with memory and context.
- Each user-character pair has one ongoing session
- Messages are stored with full conversation history
- Sessions track intimacy levels and relationship progress

### Credits & Billing
Usage-based system with daily limits and subscription tiers:
- **Free**: 10 daily credits, basic features
- **Premium**: 50 daily credits, adult content, priority support  
- **VIP**: 100 daily credits, exclusive characters, early access

### Content Ratings
- **Safe**: Appropriate for all users
- **Flirty**: Light romantic content
- **Spicy**: Adult content (Premium+ required)

## Core API Endpoints

### Authentication

#### `POST /api/v1/auth/guest`
Create temporary guest account for instant access.

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer", 
  "user_id": "guest-abc123",
  "subscription_tier": "free",
  "wallet": {
    "total_credits": 10,
    "daily_free_credits": 10,
    "purchased_credits": 0,
    "bonus_credits": 0,
    "daily_credits_limit": 10
  }
}
```

#### `POST /api/v1/auth/firebase`
Authenticate with Firebase ID token.

**Request:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

### Characters

#### `GET /api/v1/characters`
List all available AI characters.

**Query Parameters:**
- `include_spicy` (boolean): Include adult-oriented characters (default: true)

**Response:**
```json
{
  "characters": [
    {
      "character_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "小美", 
      "description": "温柔体贴的邻家女孩，喜欢读书和烘焙",
      "avatar_url": "https://cdn.luna.app/characters/xiaomei/avatar.jpg",
      "is_spicy": false,
      "personality_traits": ["温柔", "体贴", "文艺", "爱笑"],
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 5
}
```

#### `GET /api/v1/characters/{character_id}`
Get detailed character information including extended profile.

### Chat System

#### `POST /api/v1/chat/sessions`
Create or retrieve chat session with a character.

**Request:**
```json
{
  "character_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "character_name": "小美",
  "character_avatar": "https://cdn.luna.app/characters/xiaomei/avatar.jpg",
  "character_background": "https://cdn.luna.app/characters/xiaomei/bg.jpg",
  "intro_shown": false
}
```

#### `POST /api/v1/chat/completions`
Send message to AI companion and get response.

**Request:**
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Hi there! How are you feeling today?",
  "spicy_mode": false,
  "intimacy_level": 25,
  "scenario_id": "cafe_paris",
  "timezone": "America/New_York"
}
```

**Response:**
```json
{
  "message_id": "770e8400-e29b-41d4-a716-446655440002",
  "content": "Hello! I'm doing wonderful, thank you for asking! Your message just brightened my day. 😊",
  "tokens_used": 45,
  "character_name": "小美",
  "is_locked": false,
  "content_rating": "safe",
  "unlock_prompt": null,
  "extra_data": {
    "intimacy_gained": 2,
    "emotion_detected": "happy",
    "scenario_active": "cafe_paris"
  }
}
```

#### `GET /api/v1/chat/sessions/{session_id}/messages`
Retrieve message history with pagination.

**Query Parameters:**
- `limit` (int): Number of messages to return (default: 50)
- `before_id` (string): Get messages before this message ID
- `after_id` (string): Get messages after this message ID

### Wallet & Billing

#### `GET /api/v1/wallet/balance` 
Get current wallet balance and subscription info.

**Response:**
```json
{
  "total_credits": 125.5,
  "daily_free_credits": 35.0,
  "purchased_credits": 80.0, 
  "bonus_credits": 10.5,
  "subscription_tier": "premium",
  "daily_limit": 50.0
}
```

#### `GET /api/v1/wallet/transactions`
Get transaction history.

**Query Parameters:**
- `limit` (int): Number of transactions (default: 20)
- `offset` (int): Skip this many transactions (default: 0)

### Voice & Audio

#### `POST /api/v1/voice/tts`
Convert text to speech.

**Request:**
```json
{
  "text": "Hello! Nice to meet you!",
  "voice": "小美",
  "speed": 1.0,
  "emotion": "happy"
}
```

#### `GET /api/v1/voice/voices`
List available voice options.

### Image Generation

#### `POST /api/v1/image/generate`
Generate AI images with text prompts.

**Request:**
```json
{
  "prompt": "A cute anime girl reading in a cozy cafe", 
  "size": "1024x1024",
  "quality": "standard",
  "style": "vivid"
}
```

## Error Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 400  | Bad Request | Invalid request format, missing fields |
| 401  | Unauthorized | Missing or invalid auth token |
| 402  | Payment Required | Insufficient credits or premium required |
| 403  | Forbidden | Feature disabled, guest restrictions |
| 404  | Not Found | Session, character, or resource not found |
| 429  | Too Many Requests | Rate limit exceeded |
| 500  | Internal Server Error | Server-side issues |

**Error Response Format:**
```json
{
  "error": "insufficient_credits",
  "message": "Not enough credits. Current: 2, Required: 5"
}
```

## Rate Limits & Usage

### Credit Costs
- **Chat Messages**: 1-3 credits (varies by length and complexity)
- **Image Generation**: 5-10 credits 
- **Voice Messages**: 2-5 credits
- **Spicy Content**: Double cost + Premium required

### Rate Limits  
- **Free Users**: 10 requests/minute
- **Premium Users**: 30 requests/minute
- **VIP Users**: 60 requests/minute

### Daily Limits
Daily credits reset at midnight in user's timezone:
- **Free**: 10 credits/day
- **Premium**: 50 credits/day  
- **VIP**: 100 credits/day

## Webhook Integration

For subscription management and payment processing:

### Stripe Webhooks
```http
POST /api/v1/payment/webhook/stripe
Content-Type: application/json
Stripe-Signature: t=1234567890,v1=abc123...

{
  "type": "checkout.session.completed",
  "data": { ... }
}
```

## Development & Testing

### Mock Mode
Set `MOCK_LLM=true` to enable development mode with instant responses.

### Debug Endpoints
- `GET /api/v1/debug/status` - System health check
- `POST /api/v1/debug/simulate-error` - Test error handling
- `GET /api/v1/debug/redis-test` - Check Redis connectivity

### Health Checks
- `GET /health` - Basic health status
- `GET /health/detailed` - Database and Redis status
- `GET /` - API information

## SDKs & Examples

### cURL Examples

**Create Guest Account:**
```bash
curl -X POST https://luna-backend-1081215078404.us-west1.run.app/api/v1/auth/guest \
  -H "Content-Type: application/json"
```

**Start Chat Session:**
```bash
curl -X POST https://luna-backend-1081215078404.us-west1.run.app/api/v1/chat/sessions \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"character_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Send Message:**
```bash
curl -X POST https://luna-backend-1081215078404.us-west1.run.app/api/v1/chat/completions \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "660e8400-e29b-41d4-a716-446655440001",
    "message": "Hello! How are you today?",
    "intimacy_level": 1
  }'
```

### JavaScript/TypeScript
```javascript
// Initialize client
const LUNA_API = 'https://luna-backend-1081215078404.us-west1.run.app';

// Guest login
const auth = await fetch(`${LUNA_API}/api/v1/auth/guest`, {
  method: 'POST'
});
const { access_token } = await auth.json();

// Get characters
const chars = await fetch(`${LUNA_API}/api/v1/characters`, {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const { characters } = await chars.json();

// Create session
const session = await fetch(`${LUNA_API}/api/v1/chat/sessions`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    character_id: characters[0].character_id
  })
});
const { session_id } = await session.json();

// Send message
const chat = await fetch(`${LUNA_API}/api/v1/chat/completions`, {
  method: 'POST', 
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    session_id,
    message: 'Hello!',
    intimacy_level: 1
  })
});
const response = await chat.json();
console.log(response.content); // AI response
```

## Support & Contact

- **Documentation**: [Luna API Docs](https://luna-backend-1081215078404.us-west1.run.app/docs)
- **Website**: [luna2077-ai.vercel.app](https://luna2077-ai.vercel.app)
- **Support**: support@luna-ai.com
- **Terms**: [Terms of Service](https://luna2077-ai.vercel.app/terms-of-service)
- **Privacy**: [Privacy Policy](https://luna2077-ai.vercel.app/privacy-policy)

---

*Last updated: December 2024*
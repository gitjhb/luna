# Luna Telegram Bot

Lightweight Telegram bot backend for Luna AI Companion.

## Features

- 🔗 **Shared Database**: Uses same Neon PostgreSQL as Luna iOS backend
- 🧠 **Memory System**: pgvector semantic search for context-aware conversations
- 💬 **LLM Chat**: Grok (primary) / GPT-4 (fallback) for responses
- 👤 **User Linking**: Connect Telegram to Luna App account for Pro status

## Quick Start

### 1. Deploy to Vercel

```bash
npm install
vercel --prod
```

### 2. Set Environment Variables

In Vercel dashboard, add:

```
TELEGRAM_BOT_TOKEN=your_bot_token
POSTGRES_URL=your_neon_connection_string
OPENAI_API_KEY=sk-xxx
XAI_API_KEY=xai-xxx  # Optional
ADMIN_USER_ID=your_telegram_id
```

### 3. Set Webhook

```bash
curl https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-project.vercel.app/api/webhook
```

### 4. Initialize Database

Send `/init` to the bot (admin only).

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all commands |
| `/me` | View saved profile info |
| `/clear` | Clear chat history |
| `/link email` | Link Luna App account |
| `/info` | View account status |

## Architecture

```
api/
└── webhook.js      # Main webhook handler

lib/
├── telegram.js     # Telegram API helpers
├── db.js           # Neon PostgreSQL connection
├── memory.js       # pgvector semantic search
├── ai.js           # LLM chat (Grok/GPT-4)
└── user.js         # User identity management
```

## Database Schema

### telegram_users
Links Telegram users to Luna accounts.

### telegram_messages  
Conversation history for context.

### telegram_semantic_memories
User profile/preferences (name, likes, interests).

### telegram_episodic_memories
Important events with vector embeddings for semantic search.

## Memory System

1. **Semantic Memory**: User profile extracted from conversations
2. **Episodic Memory**: Important events stored with embeddings
3. **Context Building**: pgvector cosine similarity for relevant memories

### How it works:

```javascript
// On each message:
// 1. Build memory context from profile + relevant memories
const memoryContext = await buildMemoryContext(userId, userMessage);

// 2. Generate response with context
const reply = await chat(userMessage, { memoryContext });

// 3. Background: extract profile updates
const updates = await extractProfileInfo([{ role: 'user', content: userMessage }]);
await updateSemanticMemory(userId, updates);

// 4. Background: detect & store important events
const event = await detectImportantEvent(userMessage, reply);
if (event.is_important) {
  await storeEpisodicMemory(userId, event);
}
```

## Development

```bash
# Install dependencies
npm install

# Run locally with Vercel CLI
vercel dev

# Use ngrok for webhook testing
ngrok http 3000
```

## Rate Limiting

- 10 messages per minute per user
- Pro users: Unlimited messages, full memory
- Free users: 20 messages/day, limited context

## License

MIT

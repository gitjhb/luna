/**
 * Luna Telegram Bot - Thin Client Webhook
 * 
 * This is a minimal webhook that forwards messages to Luna backend.
 * All chat logic, memory, payments happen in the backend.
 */

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const LUNA_BACKEND_URL = process.env.LUNA_BACKEND_URL || 'https://luna-backend-1081215078404.us-west1.run.app';
const ADMIN_ID = process.env.ADMIN_USER_ID || '5056039560';

// Stripe Payment Link (Test Mode)
const STRIPE_PAYMENT_LINK = 'https://buy.stripe.com/test_aFa6oGcuLf0Z92gc9c2Fa02';

/**
 * Send message to Telegram
 */
async function sendMessage(chatId, text, options = {}) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
  
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: 'HTML',
    ...options,
  };
  
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  } catch (e) {
    console.error('sendMessage error:', e);
    return null;
  }
}

/**
 * Send typing indicator
 */
async function sendTyping(chatId) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendChatAction`;
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, action: 'typing' }),
    });
  } catch (e) {
    // Ignore
  }
}

/**
 * Call Luna backend for chat
 */
async function callLunaBackend(telegramId, username, firstName, message) {
  const url = `${LUNA_BACKEND_URL}/api/v1/telegram/chat`;
  
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: String(telegramId),
        username: username || null,
        first_name: firstName || null,
        message: message,
      }),
    });
    
    if (!res.ok) {
      console.error('Backend error:', res.status, await res.text());
      return null;
    }
    
    return res.json();
  } catch (e) {
    console.error('callLunaBackend error:', e);
    return null;
  }
}

/**
 * Handle /link command
 */
async function handleLinkCommand(chatId, telegramId, email) {
  const url = `${LUNA_BACKEND_URL}/api/v1/telegram/link`;
  
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: String(telegramId),
        email: email,
      }),
    });
    
    const data = await res.json();
    
    if (data.success) {
      await sendMessage(chatId, `✅ ${data.message}`);
    } else {
      await sendMessage(chatId, `❌ ${data.message}`);
    }
  } catch (e) {
    await sendMessage(chatId, '❌ Link failed. Try again later.');
  }
}

/**
 * Handle commands
 */
async function handleCommand(chatId, telegramId, command, args) {
  switch (command) {
    case '/start':
      await sendMessage(chatId, 
        `Hey~ 我是 Luna 💜\n\n` +
        `很高兴认识你！有什么想聊的吗？\n\n` +
        `<i>Tips: 直接发消息就能和我聊天哦</i>`,
      );
      break;
      
    case '/help':
      await sendMessage(chatId,
        `<b>Luna AI 指令</b>\n\n` +
        `/start - 开始聊天\n` +
        `/premium - 订阅 Premium 💎\n` +
        `/link <email> - 关联账号 (同步Pro状态)\n` +
        `/help - 显示帮助\n\n` +
        `直接发消息就能和我聊天 💬`,
      );
      break;
      
    case '/premium':
    case '/subscribe':
    case '/vip':
      await sendMessage(chatId,
        `💎 <b>Luna Premium</b>\n\n` +
        `解锁完整体验：\n` +
        `• 无限聊天次数\n` +
        `• 高级记忆功能\n` +
        `• 成人内容解锁\n` +
        `• 优先响应\n\n` +
        `点击下方链接订阅 👇`,
        {
          reply_markup: {
            inline_keyboard: [[
              { text: '💎 订阅 Premium', url: STRIPE_PAYMENT_LINK }
            ]]
          }
        }
      );
      break;
      
    case '/link':
      if (!args || !args.includes('@')) {
        await sendMessage(chatId, '用法: /link your@email.com');
        return;
      }
      await handleLinkCommand(chatId, telegramId, args.trim());
      break;
      
    default:
      // Unknown command, treat as message
      return false;
  }
  
  return true;
}

/**
 * Main webhook handler
 */
export default async function handler(req, res) {
  // Health check
  if (req.method === 'GET') {
    return res.status(200).json({ 
      status: 'ok', 
      bot: 'Luna',
      backend: LUNA_BACKEND_URL,
    });
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  const update = req.body;
  
  // Only handle messages
  if (!update.message?.text) {
    return res.status(200).json({ ok: true });
  }
  
  const msg = update.message;
  const chatId = msg.chat.id;
  const telegramId = msg.from.id;
  const username = msg.from.username;
  const firstName = msg.from.first_name;
  const text = msg.text.trim();
  
  console.log(`[Luna] ${telegramId} (${username || firstName}): ${text.slice(0, 50)}...`);
  
  // Handle commands
  if (text.startsWith('/')) {
    const [command, ...argParts] = text.split(' ');
    const args = argParts.join(' ');
    
    const handled = await handleCommand(chatId, telegramId, command.toLowerCase(), args);
    if (handled) {
      return res.status(200).json({ ok: true });
    }
  }
  
  // Send typing indicator
  await sendTyping(chatId);
  
  // Call Luna backend
  const response = await callLunaBackend(telegramId, username, firstName, text);
  
  if (response?.reply) {
    await sendMessage(chatId, response.reply);
    
    // Welcome new users
    if (response.is_new_user) {
      setTimeout(async () => {
        await sendMessage(chatId, 
          `\n💡 <i>想要解锁更多功能？下载 Luna iOS App!</i>`,
        );
      }, 2000);
    }
  } else {
    // Fallback
    await sendMessage(chatId, '嗯... 我刚才走神了，再说一遍？');
  }
  
  return res.status(200).json({ ok: true });
}

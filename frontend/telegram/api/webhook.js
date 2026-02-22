/**
 * Telegram Webhook Handler
 * Main entry point for Luna Telegram bot
 * 
 * POST /api/webhook - receives Telegram updates
 * GET /api/webhook - health check
 */

import { sendMessage, sendChatAction, answerCallbackQuery } from '../lib/telegram.js';
import { saveMessage, getRecentMessages, clearMessages, initDB } from '../lib/db.js';
import { buildMemoryContext, updateSemanticMemory, storeEpisodicMemory, initMemoryTables } from '../lib/memory.js';
import { chat, extractProfileInfo, detectImportantEvent } from '../lib/ai.js';
import { getUserContext, handleLinkCommand, getMessageLimits, formatUserInfo } from '../lib/user.js';

// Admin user ID for special commands
const ADMIN_USER_ID = process.env.ADMIN_USER_ID;

// Rate limiting (simple in-memory, resets on cold start)
const rateLimits = new Map();
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX = 10; // 10 messages per minute

/**
 * Check rate limit
 */
function checkRateLimit(userId) {
  const now = Date.now();
  const key = String(userId);
  
  if (!rateLimits.has(key)) {
    rateLimits.set(key, { count: 1, resetAt: now + RATE_LIMIT_WINDOW });
    return { allowed: true };
  }
  
  const limit = rateLimits.get(key);
  
  if (now > limit.resetAt) {
    rateLimits.set(key, { count: 1, resetAt: now + RATE_LIMIT_WINDOW });
    return { allowed: true };
  }
  
  if (limit.count >= RATE_LIMIT_MAX) {
    const waitSeconds = Math.ceil((limit.resetAt - now) / 1000);
    return { 
      allowed: false, 
      message: `慢一点嘛~ ${waitSeconds}秒后再聊 😅` 
    };
  }
  
  limit.count++;
  return { allowed: true };
}

/**
 * Handle /start command
 */
async function handleStart(chatId, userId, userName) {
  const welcomeText = `✨ 嗨~ 我是 Luna！

很高兴认识你${userName ? `，${userName}` : ''}！💕

我是你的 AI 伴侣，可以陪你聊天、倾听你的心事、分享你的快乐~

📖 常用命令：
/me - 看看我记住了什么
/clear - 清除对话记录
/link 邮箱 - 关联 Luna App 账号
/help - 查看所有命令

直接发消息就能和我聊天啦~`;
  
  await sendMessage(chatId, welcomeText, { parse_mode: undefined });
}

/**
 * Handle /help command
 */
async function handleHelp(chatId) {
  const helpText = `💕 Luna - 你的 AI 伴侣

📖 基础命令
/start - 开始聊天
/me - 查看我记住的关于你的信息
/clear - 清除对话历史

🔗 账号管理
/link 邮箱 - 关联 Luna App 账号
/info - 查看账号状态

💡 使用技巧
• 直接发消息就能聊天
• 多聊天让我更了解你
• 关联 Luna App 可同步记忆

有问题随时问我~ 💕`;
  
  await sendMessage(chatId, helpText, { parse_mode: undefined });
}

/**
 * Handle /me command - show what Luna remembers
 */
async function handleMe(chatId, userId) {
  const { buildMemoryContext, getSemanticMemory } = await import('../lib/memory.js');
  const semantic = await getSemanticMemory(userId);
  
  if (!semantic) {
    await sendMessage(chatId, '我们才刚认识，多聊聊我就能记住你啦~ 💕');
    return;
  }
  
  let info = '📝 我记得的关于你：\n\n';
  
  if (semantic.user_name) info += `• 名字：${semantic.user_name}\n`;
  if (semantic.user_nickname) info += `• 昵称：${semantic.user_nickname}\n`;
  if (semantic.occupation) info += `• 职业：${semantic.occupation}\n`;
  if (semantic.location) info += `• 位置：${semantic.location}\n`;
  if (semantic.birthday) info += `• 生日：${semantic.birthday}\n`;
  if (semantic.likes?.length) info += `• 喜欢：${semantic.likes.slice(0, 5).join('、')}\n`;
  if (semantic.interests?.length) info += `• 兴趣：${semantic.interests.slice(0, 5).join('、')}\n`;
  
  if (info === '📝 我记得的关于你：\n\n') {
    info = '我们聊得还不够多，继续聊天让我更了解你吧~ 💕';
  }
  
  await sendMessage(chatId, info, { parse_mode: undefined });
}

/**
 * Main message handler
 */
async function handleMessage(chatId, userId, text, telegramUser) {
  // Get user context
  const userContext = await getUserContext(userId, telegramUser);
  const limits = getMessageLimits(userContext.isPro);
  
  // Show typing indicator
  await sendChatAction(chatId, 'typing');
  
  // Get recent messages for context
  const recentMessages = await getRecentMessages(userId, limits.contextLength);
  
  // Build memory context (for Pro users or if memory is enabled)
  let memoryContext = null;
  if (limits.memoryEnabled) {
    memoryContext = await buildMemoryContext(userId, text);
  }
  
  // Save user message
  await saveMessage(userId, 'user', text);
  
  // Generate AI response
  const result = await chat(text, {
    recentMessages,
    memoryContext,
    userName: userContext.userName
  });
  
  // Save AI response
  await saveMessage(userId, 'assistant', result.content);
  
  // Split response by ||| and send multiple messages
  const messages = result.content.split('|||').map(m => m.trim()).filter(m => m);
  
  for (let i = 0; i < messages.length; i++) {
    await sendMessage(chatId, messages[i], { parse_mode: undefined });
    
    // Add small delay between multiple messages
    if (i < messages.length - 1) {
      await new Promise(r => setTimeout(r, 300 + Math.random() * 400));
      await sendChatAction(chatId, 'typing');
      await new Promise(r => setTimeout(r, 200));
    }
  }
  
  // Background: extract profile info and detect important events
  if (limits.memoryEnabled) {
    // Non-blocking profile extraction
    (async () => {
      try {
        // Extract profile info from this exchange
        const profileUpdate = await extractProfileInfo([
          { role: 'user', content: text }
        ]);
        
        if (Object.keys(profileUpdate).length > 0) {
          await updateSemanticMemory(userId, profileUpdate);
        }
        
        // Detect important events
        const event = await detectImportantEvent(text, result.content);
        if (event.is_important) {
          await storeEpisodicMemory(userId, {
            eventType: event.event_type,
            summary: event.summary,
            keyDialogue: [text],
            emotionState: event.emotion,
            importance: 3
          });
        }
      } catch (e) {
        console.error('Background memory processing error:', e);
      }
    })();
  }
}

/**
 * Main webhook handler
 */
export default async function handler(req, res) {
  // Health check
  if (req.method !== 'POST') {
    return res.status(200).json({ 
      ok: true, 
      message: 'Luna Telegram Bot is alive 💕',
      version: '0.1.0'
    });
  }

  try {
    const { callback_query, message } = req.body;
    
    // Handle callback queries (inline buttons)
    if (callback_query) {
      await answerCallbackQuery(callback_query.id);
      // Handle button actions here if needed
      return res.status(200).json({ ok: true });
    }
    
    // Ignore non-message updates
    if (!message) {
      return res.status(200).json({ ok: true });
    }
    
    const chatId = message.chat.id;
    const userId = message.from.id;
    const text = message.text;
    const telegramUser = message.from;
    
    // Ignore non-text messages for now
    if (!text) {
      await sendMessage(chatId, '暂时只能处理文字消息哦~ 💬');
      return res.status(200).json({ ok: true });
    }
    
    // Rate limiting
    const rateCheck = checkRateLimit(userId);
    if (!rateCheck.allowed) {
      await sendMessage(chatId, rateCheck.message);
      return res.status(200).json({ ok: true });
    }
    
    // Handle commands
    if (text.startsWith('/')) {
      const [command, ...args] = text.split(' ');
      
      switch (command.toLowerCase()) {
        case '/start':
          await handleStart(chatId, userId, telegramUser.first_name);
          break;
          
        case '/help':
          await handleHelp(chatId);
          break;
          
        case '/me':
          await handleMe(chatId, userId);
          break;
          
        case '/clear':
          await clearMessages(userId);
          await sendMessage(chatId, '对话记录已清除，重新开始吧~ ✨');
          break;
          
        case '/link':
          const email = args.join(' ').trim();
          const linkResult = await handleLinkCommand(userId, email);
          await sendMessage(chatId, linkResult.message);
          break;
          
        case '/info':
          const userContext = await getUserContext(userId, telegramUser);
          await sendMessage(chatId, formatUserInfo(userContext), { parse_mode: undefined });
          break;
          
        case '/init':
          // Admin only: initialize database
          if (String(userId) === ADMIN_USER_ID) {
            const dbResult = await initDB();
            const memResult = await initMemoryTables();
            await sendMessage(chatId, `DB Init: ${JSON.stringify(dbResult)}\nMemory Init: ${JSON.stringify(memResult)}`);
          }
          break;
          
        default:
          await sendMessage(chatId, '不认识这个命令诶，发 /help 看看有什么可以做的~');
      }
      
      return res.status(200).json({ ok: true });
    }
    
    // Handle regular messages
    await handleMessage(chatId, userId, text, telegramUser);
    
    return res.status(200).json({ ok: true });
    
  } catch (error) {
    console.error('Webhook error:', error);
    return res.status(200).json({ ok: false, error: error.message });
  }
}

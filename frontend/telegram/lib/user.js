/**
 * User Identity Management
 * Links Telegram users with Luna accounts
 */

import { getOrCreateUser, linkUserByEmail, checkProStatus } from './db.js';
import { getSemanticMemory } from './memory.js';

/**
 * Get full user context for chat
 */
export async function getUserContext(telegramId, telegramUser = {}) {
  // Get or create DB user
  const user = await getOrCreateUser(telegramId, {
    username: telegramUser.username,
    firstName: telegramUser.first_name
  });
  
  // Check Pro status
  const proStatus = await checkProStatus(telegramId);
  
  // Get semantic memory for name
  const semantic = await getSemanticMemory(telegramId);
  
  return {
    telegramId: String(telegramId),
    userName: semantic?.user_name || semantic?.user_nickname || telegramUser.first_name || null,
    isPro: proStatus.isPro,
    isLinked: !!user?.luna_user_id,
    email: user?.email || null
  };
}

/**
 * Handle /link command - link Telegram to Luna account
 */
export async function handleLinkCommand(telegramId, email) {
  if (!email || !email.includes('@')) {
    return {
      success: false,
      message: '请输入有效的邮箱地址\n格式：/link your@email.com'
    };
  }
  
  const result = await linkUserByEmail(telegramId, email.trim().toLowerCase());
  
  if (result.success) {
    return {
      success: true,
      message: result.isPro 
        ? '🎉 账号关联成功！你是 Pro 用户，享受无限对话~'
        : '✅ 账号关联成功！'
    };
  } else if (result.message === 'Email not found') {
    return {
      success: false,
      message: '找不到这个邮箱，确认是 Luna App 注册的邮箱吗？'
    };
  } else {
    return {
      success: false,
      message: '关联失败，请稍后再试'
    };
  }
}

/**
 * Get message limits based on user status
 */
export function getMessageLimits(isPro) {
  if (isPro) {
    return {
      dailyLimit: -1,  // Unlimited
      contextLength: 50,
      memoryEnabled: true
    };
  }
  
  return {
    dailyLimit: 20,
    contextLength: 10,
    memoryEnabled: false
  };
}

/**
 * Format user info for display
 */
export function formatUserInfo(userContext) {
  let info = '📋 你的账号信息\n\n';
  
  if (userContext.userName) {
    info += `👤 名字：${userContext.userName}\n`;
  }
  
  info += `🆔 Telegram ID：${userContext.telegramId}\n`;
  
  if (userContext.isLinked) {
    info += `📧 邮箱：${userContext.email}\n`;
    info += `💎 状态：${userContext.isPro ? 'Pro 用户 ✨' : '普通用户'}\n`;
  } else {
    info += `🔗 Luna App：未关联\n`;
    info += `\n使用 /link 邮箱 来关联你的 Luna App 账号`;
  }
  
  return info;
}

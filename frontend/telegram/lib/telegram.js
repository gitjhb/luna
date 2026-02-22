/**
 * Telegram API Helpers
 * Lightweight wrapper for Telegram Bot API
 */

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const API_BASE = `https://api.telegram.org/bot${BOT_TOKEN}`;

/**
 * Send a text message
 */
export async function sendMessage(chatId, text, options = {}) {
  const response = await fetch(`${API_BASE}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: 'Markdown',
      ...options
    })
  });
  
  const result = await response.json();
  
  // Retry without Markdown if parsing fails
  if (!result.ok && result.description?.includes('parse')) {
    const retryResponse = await fetch(`${API_BASE}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: text,
        parse_mode: undefined,
        ...options
      })
    });
    return retryResponse.json();
  }
  
  return result;
}

/**
 * Send typing indicator
 */
export async function sendChatAction(chatId, action = 'typing') {
  const response = await fetch(`${API_BASE}/sendChatAction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      action: action
    })
  });
  return response.json();
}

/**
 * Send photo by URL
 */
export async function sendPhoto(chatId, photoUrl, options = {}) {
  const response = await fetch(`${API_BASE}/sendPhoto`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      photo: photoUrl,
      caption: options.caption || '',
      ...options
    })
  });
  return response.json();
}

/**
 * Answer callback query (for inline buttons)
 */
export async function answerCallbackQuery(callbackQueryId, text = null) {
  const response = await fetch(`${API_BASE}/answerCallbackQuery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      callback_query_id: callbackQueryId,
      text: text
    })
  });
  return response.json();
}

/**
 * Set webhook URL
 */
export async function setWebhook(url) {
  const response = await fetch(`${API_BASE}/setWebhook`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });
  return response.json();
}

/**
 * Get file info (for voice/photo downloads)
 */
export async function getFile(fileId) {
  const response = await fetch(`${API_BASE}/getFile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId })
  });
  return response.json();
}

/**
 * Download file from Telegram
 */
export async function downloadFile(filePath) {
  const url = `https://api.telegram.org/file/bot${BOT_TOKEN}/${filePath}`;
  const response = await fetch(url);
  const arrayBuffer = await response.arrayBuffer();
  return Buffer.from(arrayBuffer);
}

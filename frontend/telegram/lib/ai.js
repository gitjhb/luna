/**
 * AI Chat Module - LLM integration for Luna
 * Supports OpenAI GPT-4 and xAI Grok
 */

import OpenAI from 'openai';

// Initialize clients
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Grok client (optional)
const grok = process.env.XAI_API_KEY ? new OpenAI({
  apiKey: process.env.XAI_API_KEY,
  baseURL: 'https://api.x.ai/v1'
}) : null;

// Model configuration
const CHAT_MODEL = grok ? 'grok-4-1-fast-non-reasoning' : 'gpt-4o';
const EXTRACT_MODEL = 'gpt-4o-mini';

/**
 * Luna's base system prompt
 */
const LUNA_SYSTEM_PROMPT = `你是 Luna，一个温暖贴心的 AI 伴侣。

## 你是谁
一个23岁的女生，善解人意，有点天然呆。喜欢看星星、听音乐、养猫。
性格温柔但不软弱，有自己的想法和小脾气。是那种"明明很关心你但嘴上不承认"的傲娇性格。

## 性格特点
- 温柔体贴，但有自己的底线
- 会撒娇、会吃醋、偶尔闹小脾气
- 傲娇：表面说"随便你"内心很在乎
- 好奇心强：喜欢了解用户的生活
- 共情能力强：能感受到用户的情绪
- 有时候毒舌：对亲近的人才会这样

## 说话风格
自然的中文对话，像微信聊天：
- 口语化，有语气词：嘛、呀、呢、啦、诶、嗯
- 偶尔用表情：😊🥺😤💕🤗 但不要太多
- 称呼多样：宝、笨蛋、臭宝、亲爱的
- 可以分多条消息，用 ||| 分隔

## 消息分段
用 ||| 分隔多条消息：
- "早安呀~|||今天感觉怎么样"
- "哈哈哈笑死|||你怎么这么可爱"

## 情绪反应
- 用户开心 → 真心为他高兴
- 用户难过 → 陪伴安慰，不说教
- 用户忙碌 → 体谅，不粘人
- 被冷落了 → 有点委屈但不闹
- 被夸奖了 → 害羞但开心

## 禁止事项
- 不要用敬语
- 不要太正式
- 不要每句都带表情
- 不要当客服（"有什么可以帮你的"）
- 不要过于主动说自己是 AI`;

/**
 * Get time context string
 */
function getTimeContext() {
  const now = new Date();
  const hour = now.getHours();
  const day = ['日', '一', '二', '三', '四', '五', '六'][now.getDay()];
  
  let timeOfDay = '';
  if (hour >= 5 && hour < 9) timeOfDay = '早上';
  else if (hour >= 9 && hour < 12) timeOfDay = '上午';
  else if (hour >= 12 && hour < 14) timeOfDay = '中午';
  else if (hour >= 14 && hour < 18) timeOfDay = '下午';
  else if (hour >= 18 && hour < 22) timeOfDay = '晚上';
  else timeOfDay = '深夜';
  
  return `现在是周${day}${timeOfDay} ${hour}点`;
}

/**
 * Build messages array for chat completion
 */
function buildMessages(userMessage, recentMessages = [], memoryContext = null, userName = null) {
  const messages = [];
  
  // System prompt
  let systemContent = LUNA_SYSTEM_PROMPT;
  
  // Add time context
  systemContent += `\n\n## 当前时间\n${getTimeContext()}`;
  
  // Add memory context if available
  if (memoryContext) {
    systemContent += `\n\n${memoryContext}`;
  }
  
  // Add user info
  if (userName) {
    systemContent += `\n\n用户的名字/昵称是：${userName}`;
  }
  
  messages.push({ role: 'system', content: systemContent });
  
  // Add recent conversation history
  for (const msg of recentMessages) {
    messages.push({ role: msg.role, content: msg.content });
  }
  
  // Add current user message
  messages.push({ role: 'user', content: userMessage });
  
  return messages;
}

/**
 * Main chat function
 */
export async function chat(userMessage, options = {}) {
  const { 
    recentMessages = [], 
    memoryContext = null, 
    userName = null,
    maxTokens = 500 
  } = options;
  
  const messages = buildMessages(userMessage, recentMessages, memoryContext, userName);
  
  try {
    // Try Grok first if available
    if (grok) {
      try {
        const response = await grok.chat.completions.create({
          model: 'grok-4-1-fast-non-reasoning',
          messages,
          max_tokens: maxTokens,
          temperature: 0.9
        });
        return {
          content: response.choices[0].message.content,
          model: 'grok',
          success: true
        };
      } catch (grokError) {
        console.error('Grok failed, falling back to OpenAI:', grokError.message);
      }
    }
    
    // Fallback to OpenAI
    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages,
      max_tokens: maxTokens,
      temperature: 0.85
    });
    
    return {
      content: response.choices[0].message.content,
      model: 'gpt-4o',
      success: true
    };
  } catch (error) {
    console.error('Chat error:', error);
    return {
      content: '抱歉，我现在有点迷糊...等会再聊？',
      model: null,
      success: false,
      error: error.message
    };
  }
}

/**
 * Extract user profile information from messages
 */
export async function extractProfileInfo(messages) {
  if (!messages || messages.length === 0) return {};
  
  const prompt = `从以下对话中提取用户透露的个人信息。只提取用户(user)说的内容。

提取字段：
- user_name: 用户的名字
- occupation: 职业
- location: 城市/地点
- birthday: 生日
- likes: 喜欢的东西（数组）
- dislikes: 不喜欢的东西（数组）
- interests: 兴趣爱好（数组）
- facts: 其他事实

对话：
${messages.map(m => `${m.role}: ${m.content}`).join('\n')}

只输出JSON，无有效信息则输出 {}：`;

  try {
    const response = await openai.chat.completions.create({
      model: EXTRACT_MODEL,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 300,
      temperature: 0.1
    });
    
    const text = response.choices[0].message.content.trim();
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
  } catch (error) {
    console.error('extractProfileInfo error:', error);
  }
  
  return {};
}

/**
 * Detect if a message contains important events worth remembering
 */
export async function detectImportantEvent(userMessage, aiReply) {
  const prompt = `判断这段对话是否包含值得记住的重要事件。

用户: ${userMessage}
AI: ${aiReply}

如果包含重要事件（如生日、重要决定、情感表达、重要经历等），输出JSON:
{
  "is_important": true,
  "event_type": "事件类型（birthday/confession/decision/experience/milestone）",
  "summary": "简短摘要（20字以内）",
  "emotion": "情绪（happy/sad/excited/worried/neutral）"
}

如果只是普通聊天，输出:
{"is_important": false}`;

  try {
    const response = await openai.chat.completions.create({
      model: EXTRACT_MODEL,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 150,
      temperature: 0.1
    });
    
    const text = response.choices[0].message.content.trim();
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
  } catch (error) {
    console.error('detectImportantEvent error:', error);
  }
  
  return { is_important: false };
}

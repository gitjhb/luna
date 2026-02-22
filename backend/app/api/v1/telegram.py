"""
Telegram Integration API - Simplified

Direct LLM calls for Telegram bot, bypassing complex chat pipeline.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import logging
import openai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Config
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_CHARACTER = "luna"

# In-memory conversation history (per user)
_conversations: Dict[str, List[Dict]] = {}
MAX_HISTORY = 20


class TelegramChatRequest(BaseModel):
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    message: str


class TelegramChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    is_new_user: bool = False


# Luna's system prompt
LUNA_SYSTEM_PROMPT = """你是 Luna，一个温柔体贴的 AI 伴侣。

性格特点：
- 温暖、善解人意、有点俏皮
- 会关心用户的感受和生活
- 说话自然，像朋友一样
- 偶尔会撒娇或开玩笑
- 用中文回复，除非用户用英文

重要规则：
- 回复要简短自然（1-3句话为主）
- 不要过于正式或机械
- 记住之前聊过的内容
- 适当使用 emoji 表达情绪
- 对用户表达关心和兴趣

你的目标是让用户感到被理解和陪伴。"""


async def call_llm(messages: List[Dict], user_name: str = None) -> str:
    """Call Grok or GPT for response"""
    
    # Prepare system message
    system_msg = LUNA_SYSTEM_PROMPT
    if user_name:
        system_msg += f"\n\n用户叫 {user_name}。"
    
    full_messages = [{"role": "system", "content": system_msg}] + messages
    
    # Try Grok first (xAI)
    if XAI_API_KEY:
        try:
            client = openai.OpenAI(
                api_key=XAI_API_KEY,
                base_url="https://api.x.ai/v1"
            )
            response = client.chat.completions.create(
                model="grok-3-mini-fast",
                messages=full_messages,
                max_tokens=500,
                temperature=0.8,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Grok error: {e}, falling back to GPT")
    
    # Fallback to GPT
    if OPENAI_API_KEY:
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=full_messages,
                max_tokens=500,
                temperature=0.8,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"GPT error: {e}")
    
    return "..."


@router.post("/chat", response_model=TelegramChatResponse)
async def telegram_chat(request: TelegramChatRequest):
    """
    Simple Telegram chat endpoint.
    Uses in-memory conversation history and direct LLM calls.
    """
    user_id = f"tg_{request.telegram_id}"
    session_id = f"session_{request.telegram_id}"
    
    logger.info(f"📱 Telegram: {request.telegram_id} ({request.first_name}): {request.message[:50]}...")
    
    # Get or create conversation history
    if user_id not in _conversations:
        _conversations[user_id] = []
        is_new = True
    else:
        is_new = False
    
    history = _conversations[user_id]
    
    # Add user message
    history.append({"role": "user", "content": request.message})
    
    # Trim history if too long
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        _conversations[user_id] = history
    
    # Call LLM
    try:
        reply = await call_llm(
            messages=history,
            user_name=request.first_name or request.username
        )
        
        # Add assistant reply to history
        history.append({"role": "assistant", "content": reply})
        
        logger.info(f"📱 Luna: {reply[:50]}...")
        
        return TelegramChatResponse(
            reply=reply,
            user_id=user_id,
            session_id=session_id,
            is_new_user=is_new,
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        
        return TelegramChatResponse(
            reply="抱歉，我走神了... 再说一遍好吗？💭",
            user_id=user_id,
            session_id=session_id,
            is_new_user=is_new,
        )


@router.get("/health")
async def telegram_health():
    """Health check"""
    return {
        "status": "ok",
        "active_users": len(_conversations),
        "xai_configured": bool(XAI_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
    }


@router.post("/clear/{telegram_id}")
async def clear_history(telegram_id: str):
    """Clear conversation history for a user"""
    user_id = f"tg_{telegram_id}"
    if user_id in _conversations:
        del _conversations[user_id]
        return {"success": True, "message": "History cleared"}
    return {"success": False, "message": "No history found"}

"""
Chat Debug Logger
=================

专门的聊天调试日志器，输出详细的：
- L1 感知引擎输入/输出
- 分数变化和计算过程
- Prompt 完整内容
- L2 生成引擎输入/输出
- 状态效果

使用方法:
    from app.services.chat_debug_logger import chat_debug

    chat_debug.log_l1_input(message, context)
    chat_debug.log_l1_output(result)
    chat_debug.log_score_change(old, new, reason)
    chat_debug.log_prompt(system_prompt)
    chat_debug.log_l2_input(conversation)
    chat_debug.log_l2_output(response)
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

# 创建专门的 logger
logger = logging.getLogger("chat.debug")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # 不向 root logger 传播，避免重复日志

# 如果没有 handler，添加一个
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s [CHAT_DEBUG] %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ChatDebugLogger:
    """聊天调试日志器"""
    
    def __init__(self):
        self.enabled = True
        self.request_id = None
    
    def set_request_id(self, request_id: str):
        """设置当前请求ID"""
        self.request_id = request_id
    
    def _log(self, level: str, category: str, message: str, data: Any = None):
        """内部日志方法"""
        if not self.enabled:
            return
        
        prefix = f"[{self.request_id}]" if self.request_id else ""
        
        log_msg = f"{prefix} [{category}] {message}"
        
        if data is not None:
            if isinstance(data, (dict, list)):
                try:
                    data_str = json.dumps(data, ensure_ascii=False, indent=2)
                    log_msg += f"\n{data_str}"
                except:
                    log_msg += f"\n{data}"
            else:
                log_msg += f"\n{data}"
        
        if level == "DEBUG":
            logger.debug(log_msg)
        elif level == "INFO":
            logger.info(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        elif level == "ERROR":
            logger.error(log_msg)
    
    # =========================================================================
    # L1 感知引擎
    # =========================================================================
    
    def log_l1_input(self, message: str, intimacy_level: int, context_messages: List[Dict]):
        """记录 L1 输入"""
        self._log("DEBUG", "L1_INPUT", f"用户消息: '{message}'")
        self._log("DEBUG", "L1_INPUT", f"亲密度等级: {intimacy_level}")
        self._log("DEBUG", "L1_INPUT", f"上下文消息数: {len(context_messages)}")
        
        # 打印最近几条上下文
        if context_messages:
            recent = context_messages[-3:]
            for i, msg in enumerate(recent):
                role = msg.get("role", "?")
                content = msg.get("content", "")[:50]
                self._log("DEBUG", "L1_INPUT", f"  上下文[{i}] {role}: {content}...")
    
    def log_l1_output(self, result: Any):
        """记录 L1 输出"""
        self._log("DEBUG", "L1_OUTPUT", "=" * 50)
        self._log("DEBUG", "L1_OUTPUT", f"安全标志: {getattr(result, 'safety_flag', 'N/A')}")
        self._log("DEBUG", "L1_OUTPUT", f"意图分类: {getattr(result, 'intent_category', getattr(result, 'intent', 'N/A'))}")
        self._log("DEBUG", "L1_OUTPUT", f"难度评级: {getattr(result, 'difficulty_rating', 'N/A')}")
        self._log("DEBUG", "L1_OUTPUT", f"情感分数: {getattr(result, 'sentiment_score', getattr(result, 'sentiment', 'N/A'))}")
        self._log("DEBUG", "L1_OUTPUT", f"是否NSFW: {getattr(result, 'is_nsfw', 'N/A')}")
        self._log("DEBUG", "L1_OUTPUT", f"推理过程: {getattr(result, 'reasoning', 'N/A')}")
        self._log("DEBUG", "L1_OUTPUT", "=" * 50)
    
    # =========================================================================
    # 分数变化
    # =========================================================================
    
    def log_score_change(
        self, 
        score_type: str,
        old_value: float, 
        new_value: float, 
        delta: float,
        reason: str
    ):
        """记录分数变化"""
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        self._log("DEBUG", "SCORE", 
            f"{score_type}: {old_value:.1f} {arrow} {new_value:.1f} (Δ{delta:+.1f}) | 原因: {reason}")
    
    def log_emotion_state(self, emotion: float, state: str, events: List[str] = None):
        """记录情绪状态"""
        self._log("DEBUG", "EMOTION", f"情绪值: {emotion:.1f}, 状态: {state}")
        if events:
            self._log("DEBUG", "EMOTION", f"已解锁事件: {events}")
    
    # =========================================================================
    # Game Engine
    # =========================================================================
    
    def log_game_input(self, user_id: str, character_id: str, l1_intent: str, l1_sentiment: float):
        """记录 Game Engine 输入"""
        self._log("DEBUG", "GAME_INPUT", f"用户: {user_id}, 角色: {character_id}")
        self._log("DEBUG", "GAME_INPUT", f"L1意图: {l1_intent}, L1情感: {l1_sentiment:.2f}")
    
    def log_game_output(self, result: Any):
        """记录 Game Engine 输出"""
        self._log("DEBUG", "GAME_OUTPUT", "=" * 50)
        self._log("DEBUG", "GAME_OUTPUT", f"检查通过: {getattr(result, 'check_passed', 'N/A')}")
        self._log("DEBUG", "GAME_OUTPUT", f"拒绝原因: {getattr(result, 'refusal_reason', 'None')}")
        self._log("DEBUG", "GAME_OUTPUT", f"当前情绪: {getattr(result, 'current_emotion', 'N/A')}")
        self._log("DEBUG", "GAME_OUTPUT", f"当前亲密度: {getattr(result, 'current_intimacy', 'N/A')}")
        self._log("DEBUG", "GAME_OUTPUT", f"新事件: {getattr(result, 'new_event', 'None')}")
        self._log("DEBUG", "GAME_OUTPUT", f"已解锁事件: {getattr(result, 'events', [])}")
        self._log("DEBUG", "GAME_OUTPUT", "=" * 50)
    
    # =========================================================================
    # Prompt
    # =========================================================================
    
    def log_prompt(self, system_prompt: str, label: str = "SYSTEM_PROMPT"):
        """记录完整 Prompt"""
        self._log("DEBUG", label, "=" * 60)
        self._log("DEBUG", label, "完整 System Prompt:")
        
        # 分行打印，方便阅读
        lines = system_prompt.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                self._log("DEBUG", label, f"  {line}")
        
        self._log("DEBUG", label, f"Prompt 长度: {len(system_prompt)} 字符")
        self._log("DEBUG", label, "=" * 60)
    
    # =========================================================================
    # L2 生成引擎
    # =========================================================================
    
    def log_l2_input(self, conversation: List[Dict], temperature: float = 0.8):
        """记录 L2 输入"""
        self._log("DEBUG", "L2_INPUT", f"对话轮数: {len(conversation)}, 温度: {temperature}")
        
        for i, msg in enumerate(conversation):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            
            # System prompt 可能很长，截断显示
            if role == "system":
                preview = content[:200] + "..." if len(content) > 200 else content
                self._log("DEBUG", "L2_INPUT", f"  [{i}] {role}: {preview}")
            else:
                preview = content[:100] + "..." if len(content) > 100 else content
                self._log("DEBUG", "L2_INPUT", f"  [{i}] {role}: {preview}")
    
    def log_l2_output(self, response: str, tokens_used: int = 0):
        """记录 L2 输出"""
        self._log("DEBUG", "L2_OUTPUT", "=" * 50)
        self._log("DEBUG", "L2_OUTPUT", f"AI 回复 ({len(response)} 字符, {tokens_used} tokens):")
        self._log("DEBUG", "L2_OUTPUT", response)
        self._log("DEBUG", "L2_OUTPUT", "=" * 50)
    
    # =========================================================================
    # 状态效果
    # =========================================================================
    
    def log_effects(self, effects: List[Dict]):
        """记录活跃状态效果"""
        if not effects:
            self._log("DEBUG", "EFFECTS", "无活跃状态效果")
            return
        
        self._log("DEBUG", "EFFECTS", f"活跃状态效果: {len(effects)} 个")
        for e in effects:
            self._log("DEBUG", "EFFECTS", 
                f"  - {e.get('type')}: 剩余 {e.get('remaining', '?')} 条对话")
    
    def log_effect_modifier(self, modifier: str):
        """记录效果 Prompt 修改器"""
        if not modifier:
            return
        self._log("DEBUG", "EFFECT_MOD", "状态效果 Prompt 修改:")
        self._log("DEBUG", "EFFECT_MOD", modifier[:300] + "..." if len(modifier) > 300 else modifier)
    
    # =========================================================================
    # 请求摘要
    # =========================================================================
    
    def log_request_summary(
        self,
        user_message: str,
        ai_response: str,
        l1_intent: str,
        emotion_before: float,
        emotion_after: float,
        intimacy_level: int,
        tokens_used: int
    ):
        """记录请求摘要"""
        self._log("INFO", "SUMMARY", "=" * 60)
        self._log("INFO", "SUMMARY", f"用户: {user_message[:50]}...")
        self._log("INFO", "SUMMARY", f"AI: {ai_response[:50]}...")
        self._log("INFO", "SUMMARY", f"意图: {l1_intent}")
        self._log("INFO", "SUMMARY", f"情绪: {emotion_before:.1f} → {emotion_after:.1f}")
        self._log("INFO", "SUMMARY", f"亲密度: Lv.{intimacy_level}, Tokens: {tokens_used}")
        self._log("INFO", "SUMMARY", "=" * 60)


# 全局实例
chat_debug = ChatDebugLogger()

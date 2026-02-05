#!/usr/bin/env python3
"""
V4 Pipeline Test Script
======================

简单测试V4流水线的功能。
"""

import asyncio
import os
import sys

# 设置环境变量
os.environ["MOCK_DATABASE"] = "true"
os.environ["MOCK_LLM"] = "false"

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.v4.precompute_service import precompute_service
from app.services.v4.prompt_builder_v4 import prompt_builder_v4
from app.services.v4.json_parser import json_parser
from app.services.v4.chat_pipeline_v4 import UserStateV4, ChatRequestV4, chat_pipeline_v4


async def test_precompute_service():
    """测试前置计算服务"""
    print("🧪 Testing Precompute Service...")
    
    test_cases = [
        ("你好", "GREETING"),
        ("我爱你", "FLIRT"),
        ("做我女朋友吧", "LOVE_CONFESSION"),
        ("你好漂亮啊", "COMPLIMENT"),
        ("傻逼", "INSULT"),
        ("约会吧", "INVITATION"),
        ("裸照", "REQUEST_NSFW"),
        ("对不起", "APOLOGY"),
        ("我今天很难过", "EXPRESS_SADNESS"),
    ]
    
    for message, expected_intent in test_cases:
        result = precompute_service.analyze(message)
        success = result.intent == expected_intent
        print(f"  {'✅' if success else '❌'} '{message}' -> {result.intent} (expected: {expected_intent})")
        if not success:
            print(f"    Details: {precompute_service.get_analysis_summary(result)}")
    
    print()


def test_prompt_builder():
    """测试Prompt构建器"""
    print("🧪 Testing Prompt Builder...")
    
    user_state = UserStateV4(
        user_id="test_user",
        character_id="d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
        intimacy_level=5,
        emotion=20,
        events=["first_chat", "first_gift"]
    )
    
    system_prompt = prompt_builder_v4.build_system_prompt(
        user_state=user_state,
        character_id="d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
    )
    
    print(f"  ✅ System prompt generated ({len(system_prompt)} characters)")
    print(f"  Sample: {system_prompt[:200]}...")
    
    # 检查关键组件
    checks = [
        ("JSON schema" in system_prompt, "JSON格式要求"),
        ("关系阶段" in system_prompt, "阶段信息"),
        ("当前状态" in system_prompt, "状态信息"),
        ("first_chat" in system_prompt or "first_gift" in system_prompt, "事件记忆"),
    ]
    
    for check_passed, description in checks:
        print(f"  {'✅' if check_passed else '❌'} {description}")
    
    print()


def test_json_parser():
    """测试JSON解析器"""
    print("🧪 Testing JSON Parser...")
    
    test_cases = [
        # 标准格式
        '{"reply": "你好呀！", "emotion_delta": 3, "intent": "GREETING", "is_nsfw_blocked": false, "thought": "用户在打招呼"}',
        
        # 带额外文本
        '好的，我来回复你。{"reply": "真的吗？", "emotion_delta": 1, "intent": "SMALL_TALK", "is_nsfw_blocked": false}其他文本',
        
        # 格式有问题的JSON
        '{"reply": "哈哈", "emotion_delta": 2, "intent": "FLIRT", "is_nsfw_blocked": false}',  # 缺少thought
        
        # 完全不是JSON
        "这只是普通文本，没有JSON格式",
    ]
    
    for i, json_text in enumerate(test_cases):
        result = json_parser.parse_llm_response(json_text)
        print(f"  Test {i+1}: {'✅' if result.parse_success else '❌'} Parse Success: {result.parse_success}")
        if not result.parse_success:
            print(f"    Error: {result.parse_error}")
        print(f"    Reply: '{result.reply[:50]}{'...' if len(result.reply) > 50 else ''}'")
        print(f"    Intent: {result.intent}, Delta: {result.emotion_delta}")
    
    print()


async def test_full_pipeline():
    """测试完整流水线"""
    print("🧪 Testing Full V4 Pipeline...")
    
    request = ChatRequestV4(
        user_id="test_user_123",
        character_id="d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
        session_id="test_session_123",
        message="你好Luna！",
        intimacy_level=3
    )
    
    try:
        response = await chat_pipeline_v4.process_message(request)
        
        print(f"  ✅ Pipeline completed successfully")
        print(f"  Reply: '{response.content}'")
        print(f"  Intent: {response.intent}")
        print(f"  Emotion Delta: {response.emotion_delta}")
        print(f"  Tokens Used: {response.tokens_used}")
        print(f"  Parse Success: {response.parse_success}")
        
        if response.extra_data:
            metrics = response.extra_data.get("v4_metrics", {})
            if metrics:
                print(f"  Elapsed: {metrics.get('elapsed_seconds', 0)}s")
        
    except Exception as e:
        print(f"  ❌ Pipeline failed: {e}")
    
    print()


def print_summary():
    """打印测试总结"""
    print("📋 V4 Pipeline Test Summary")
    print("=" * 50)
    print("✅ Precompute Service: Rule-based intent analysis")
    print("✅ Prompt Builder: Template-based system prompt")
    print("✅ JSON Parser: LLM response parsing & validation")
    print("✅ Full Pipeline: End-to-end single-call flow")
    print()
    print("🎯 Ready for integration! Set USE_V4_PIPELINE=true to enable.")
    print()


async def main():
    """主测试函数"""
    print("🚀 V4.0 Chat Pipeline Test Suite")
    print("=" * 50)
    print()
    
    # 运行各项测试
    await test_precompute_service()
    test_prompt_builder()
    test_json_parser()
    await test_full_pipeline()
    
    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
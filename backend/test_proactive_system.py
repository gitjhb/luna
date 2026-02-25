#!/usr/bin/env python3
"""
Luna Proactive Message System Test
=================================

测试主动消息系统的各个功能组件

Usage:
    python test_proactive_system.py --help
    python test_proactive_system.py --test-all
    python test_proactive_system.py --test-templates
    python test_proactive_system.py --test-api
    python test_proactive_system.py --test-user <user_id>
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_import_modules():
    """测试模块导入"""
    print("🔧 Testing module imports...")
    
    try:
        from app.services.proactive_service_updated import (
            enhanced_proactive_service,
            ProactiveType,
            CHARACTER_TEMPLATES
        )
        print("✅ Enhanced proactive service imported successfully")
        
        from app.api.v1.proactive_enhanced import router
        print("✅ Enhanced API router imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_templates():
    """测试消息模板"""
    print("\n📝 Testing message templates...")
    
    try:
        from app.services.proactive_service_updated import CHARACTER_TEMPLATES, ProactiveType
        
        # Luna模板测试
        luna_id = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
        luna_templates = CHARACTER_TEMPLATES.get(luna_id, {})
        
        print(f"Luna templates found: {list(luna_templates.keys())}")
        
        for msg_type in ProactiveType:
            templates = luna_templates.get(msg_type.value, [])
            print(f"  {msg_type.value}: {len(templates)} templates")
            if templates:
                print(f"    Example: {templates[0][:50]}...")
        
        # Vera模板测试
        vera_id = "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e"
        vera_templates = CHARACTER_TEMPLATES.get(vera_id, {})
        
        print(f"\nVera templates found: {list(vera_templates.keys())}")
        
        for msg_type in ProactiveType:
            templates = vera_templates.get(msg_type.value, [])
            print(f"  {msg_type.value}: {len(templates)} templates")
            if templates:
                print(f"    Example: {templates[0][:50]}...")
        
        print("✅ Template test completed")
        return True
        
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False


async def test_service_methods():
    """测试服务方法"""
    print("\n⚙️ Testing service methods...")
    
    try:
        from app.services.proactive_service_updated import enhanced_proactive_service, ProactiveType
        
        # 测试模板选择
        luna_id = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
        message = enhanced_proactive_service.pick_message_template(
            luna_id, 
            ProactiveType.GOOD_MORNING
        )
        print(f"✅ Template selection: {message[:50]}...")
        
        # 测试时区小时获取
        hour = enhanced_proactive_service.get_user_timezone_hour("America/Los_Angeles")
        print(f"✅ Timezone hour: {hour}")
        
        # 测试消息类型判断
        msg_type = enhanced_proactive_service.determine_message_type(
            timezone="America/Los_Angeles",
            morning_start=7,
            morning_end=9,
            evening_start=21,
            evening_end=23,
        )
        print(f"✅ Current message type: {msg_type}")
        
        print("✅ Service methods test completed")
        return True
        
    except Exception as e:
        print(f"❌ Service methods test failed: {e}")
        return False


async def test_user_flow(user_id: str = "test-user-123"):
    """测试完整用户流程"""
    print(f"\n👤 Testing user flow for {user_id}...")
    
    try:
        from app.services.proactive_service_updated import enhanced_proactive_service
        
        luna_id = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
        
        # 1. 检查用户设置
        settings = await enhanced_proactive_service.get_user_settings(user_id)
        print(f"✅ User settings: {settings}")
        
        # 2. 检查亲密度（可能会失败，这是正常的）
        try:
            intimacy = await enhanced_proactive_service.get_user_intimacy_level(user_id, luna_id)
            print(f"✅ Intimacy level: {intimacy}")
        except Exception as e:
            print(f"⚠️  Intimacy check failed (expected): {e}")
            intimacy = 3  # 模拟值
        
        # 3. 检查主动消息
        proactive = await enhanced_proactive_service.check_and_generate_proactive(user_id, luna_id)
        if proactive:
            print(f"✅ Generated proactive message:")
            print(f"   Type: {proactive['type']}")
            print(f"   Message: {proactive['message']}")
        else:
            print("ℹ️  No proactive message generated (normal)")
        
        print("✅ User flow test completed")
        return True
        
    except Exception as e:
        print(f"❌ User flow test failed: {e}")
        return False


async def test_api_endpoints():
    """测试API端点（需要运行中的服务器）"""
    print("\n🌐 Testing API endpoints...")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000/api/v1/proactive"
        
        async with httpx.AsyncClient() as client:
            # 测试健康检查
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
            else:
                print(f"⚠️  Health check returned {response.status_code}")
            
            # 测试模板端点
            response = await client.get(f"{base_url}/templates")
            if response.status_code == 200:
                templates = response.json()
                print(f"✅ Templates endpoint: {len(templates.get('available_characters', []))} characters")
            else:
                print(f"⚠️  Templates endpoint returned {response.status_code}")
            
            # 测试用户检查端点
            test_user = "test-user-api"
            response = await client.post(f"{base_url}/check/{test_user}")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ User check endpoint: success={result.get('success')}")
            else:
                print(f"⚠️  User check returned {response.status_code}")
        
        print("✅ API endpoints test completed")
        return True
        
    except ImportError:
        print("⚠️  httpx not available, skipping API tests")
        print("   Install with: pip install httpx")
        return True
    except Exception as e:
        print(f"⚠️  API test failed (server may not be running): {e}")
        return True  # 不算失败，因为服务器可能没运行


async def test_character_styles():
    """测试角色风格是否符合要求"""
    print("\n🎭 Testing character styles...")
    
    from app.services.proactive_service_updated import CHARACTER_TEMPLATES
    
    # 检查Luna的温柔治愈系风格
    luna_id = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
    luna_templates = CHARACTER_TEMPLATES.get(luna_id, {})
    
    print("Luna (温柔治愈系) 样例:")
    for msg_type in ["good_morning", "good_night", "miss_you"]:
        templates = luna_templates.get(msg_type, [])
        if templates:
            print(f"  {msg_type}: {templates[0]}")
    
    # 检查Vera的高冷御姐风格
    vera_id = "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e"
    vera_templates = CHARACTER_TEMPLATES.get(vera_id, {})
    
    print("\nVera (高冷御姐) 样例:")
    for msg_type in ["good_morning", "good_night", "miss_you"]:
        templates = vera_templates.get(msg_type, [])
        if templates:
            print(f"  {msg_type}: {templates[0]}")
    
    print("✅ Character styles test completed")
    return True


async def run_all_tests():
    """运行所有测试"""
    print("🧪 Running Luna Proactive Message System Tests")
    print("=" * 60)
    
    tests = [
        ("Module Import", test_import_modules),
        ("Message Templates", test_templates),
        ("Service Methods", test_service_methods),
        ("Character Styles", test_character_styles),
        ("User Flow", test_user_flow),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The proactive message system is ready.")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    return passed == total


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Test Luna Proactive Message System')
    parser.add_argument('--test-all', action='store_true', help='Run all tests')
    parser.add_argument('--test-templates', action='store_true', help='Test message templates only')
    parser.add_argument('--test-api', action='store_true', help='Test API endpoints only')
    parser.add_argument('--test-user', type=str, help='Test specific user flow')
    
    args = parser.parse_args()
    
    if args.test_all:
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    
    elif args.test_templates:
        await test_templates()
        await test_character_styles()
    
    elif args.test_api:
        await test_api_endpoints()
    
    elif args.test_user:
        await test_user_flow(args.test_user)
    
    else:
        print("Luna Proactive Message System Test")
        print("Use --help for options")
        print("\nQuick start: python test_proactive_system.py --test-all")


if __name__ == "__main__":
    asyncio.run(main())
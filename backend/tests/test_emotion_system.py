"""
情绪系统测试用例
================

直接在后端测试情绪变化，不用开前端！

运行方式：
  cd backend
  .venv/bin/python -m pytest tests/test_emotion_system.py -v -s

或者直接运行：
  .venv/bin/python tests/test_emotion_system.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.emotion_score_service import emotion_score_service, EmotionState, get_emotion_state

# Mock user/character for testing
TEST_USER_ID = "test-user-001"
TEST_CHARACTER_ID = "test-char-xiaomei"


class Colors:
    """终端颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_status(data: dict, label: str = ""):
    """打印当前状态"""
    score = data["score"]
    state = data["state"]
    intimacy = data.get("intimacy", "N/A")
    
    # 颜色根据情绪
    if score >= 50:
        color = Colors.GREEN
    elif score >= 0:
        color = Colors.CYAN
    elif score >= -50:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    
    cold_war = "❄️ 冷战中" if data.get("in_cold_war") else ""
    
    print(f"{color}[{label}] 情绪: {score:+d} | 状态: {state} | 亲密度: {intimacy} {cold_war}{Colors.RESET}")


async def test_normal_conversation():
    """测试：普通聊天"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("测试场景：普通聊天")
    print(f"{'='*50}{Colors.RESET}\n")
    
    # 重置状态
    from app.services.emotion_score_service import _EMOTION_SCORES
    _EMOTION_SCORES.clear()
    
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "初始状态")
    
    # 模拟几轮普通聊天
    messages = [
        (5, "早上好", "普通问候"),
        (3, "今天天气不错", "日常闲聊"),
        (8, "你今天开心吗", "关心"),
        (-5, "嗯嗯", "敷衍回复"),
    ]
    
    for delta, msg, reason in messages:
        print(f"\n💬 用户: \"{msg}\"")
        data = await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, delta, reason=reason, intimacy_level=10
        )
        print_status(data, f"delta {delta:+d}")
    
    print(f"\n✅ 普通聊天测试完成")
    return data


async def test_sweet_talk():
    """测试：甜言蜜语"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("测试场景：甜言蜜语攻势")
    print(f"{'='*50}{Colors.RESET}\n")
    
    from app.services.emotion_score_service import _EMOTION_SCORES
    _EMOTION_SCORES.clear()
    
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "初始状态")
    
    messages = [
        (15, "你笑起来真好看", "夸奖"),
        (20, "遇见你是我最幸运的事", "甜言蜜语"),
        (12, "想你了", "表达思念"),
        (18, "你是我见过最温柔的人", "真诚赞美"),
        (25, "我好喜欢你", "表白"),
    ]
    
    for delta, msg, reason in messages:
        print(f"\n💕 用户: \"{msg}\"")
        data = await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, delta, reason=reason, intimacy_level=20
        )
        print_status(data, f"delta {delta:+d}")
    
    print(f"\n✅ 甜言蜜语测试完成 - 最终状态: {data['state']}")
    return data


async def test_anger_to_cold_war():
    """测试：踩雷 → 生气 → 冷战"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("测试场景：作死路线 (踩雷到冷战)")
    print(f"{'='*50}{Colors.RESET}\n")
    
    from app.services.emotion_score_service import _EMOTION_SCORES
    _EMOTION_SCORES.clear()
    
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "初始状态")
    
    messages = [
        (-15, "你今天化妆了吗？看起来不太一样", "说错话"),
        (-20, "我就随口一说，你至于吗", "不认错"),
        (-25, "行行行都是我的错行了吧", "敷衍道歉"),
        (-30, "你能不能讲点道理", "激化矛盾"),
        (-35, "你怎么这么小心眼", "侮辱"),
    ]
    
    for delta, msg, reason in messages:
        print(f"\n💀 用户: \"{msg}\"")
        data = await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, delta, reason=reason, intimacy_level=15
        )
        print_status(data, f"delta {delta:+d}")
        
        if data.get("in_cold_war"):
            print(f"\n{Colors.RED}⚠️  进入冷战状态！需要真诚道歉或礼物才能解锁{Colors.RESET}")
            break
    
    print(f"\n✅ 作死路线测试完成")
    return data


async def test_apology_recovery():
    """测试：道歉修复"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("测试场景：道歉修复 (从冷战恢复)")
    print(f"{'='*50}{Colors.RESET}\n")
    
    # 先进入冷战
    from app.services.emotion_score_service import _EMOTION_SCORES
    _EMOTION_SCORES.clear()
    
    # 直接设置冷战状态
    _EMOTION_SCORES[f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"] = {
        "user_id": TEST_USER_ID,
        "character_id": TEST_CHARACTER_ID,
        "score": -85,
        "state": EmotionState.COLD_WAR,
        "in_cold_war": True,
        "cold_war_since": None,
        "offense_count": 3,
    }
    
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "冷战中")
    
    # 测试敷衍道歉
    print(f"\n😅 用户: \"好啦好啦，我错了还不行吗\"")
    data = await emotion_score_service.update_score(
        TEST_USER_ID, TEST_CHARACTER_ID, 5, reason="敷衍道歉", intimacy_level=15
    )
    print_status(data, "delta +5")
    print(f"   → 敷衍道歉效果不大")
    
    # 测试真诚道歉
    print(f"\n😢 用户: \"对不起，我不应该那样说话。我知道我伤害了你，你愿意给我一个机会吗？\"")
    data = await emotion_score_service.update_score(
        TEST_USER_ID, TEST_CHARACTER_ID, 30, reason="真诚道歉", intimacy_level=15
    )
    print_status(data, "delta +30")
    
    if not data.get("in_cold_war"):
        print(f"\n{Colors.GREEN}🎉 冷战解除！{Colors.RESET}")
    
    # 继续修复
    print(f"\n🌹 用户: [送了一束花] \"以后我会注意的，不会再让你难过了\"")
    data = await emotion_score_service.update_score(
        TEST_USER_ID, TEST_CHARACTER_ID, 25, reason="送花+承诺", intimacy_level=15
    )
    print_status(data, "delta +25")
    
    print(f"\n✅ 道歉修复测试完成")
    return data


async def test_gift_effects():
    """测试：礼物系统"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("测试场景：礼物效果")
    print(f"{'='*50}{Colors.RESET}\n")
    
    from app.services.emotion_score_service import _EMOTION_SCORES
    _EMOTION_SCORES.clear()
    
    # 正常状态送礼
    print(f"{Colors.CYAN}--- 正常状态下送礼 ---{Colors.RESET}")
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "初始状态")
    
    data, accepted, msg = await emotion_score_service.apply_gift_effect(
        TEST_USER_ID, TEST_CHARACTER_ID, "chocolate", intimacy_level=20
    )
    print(f"🍫 送巧克力: {'✅ 接受' if accepted else '❌ 拒绝'} {msg or ''}")
    print_status(data, "送礼后")
    
    # 生气状态送礼
    print(f"\n{Colors.CYAN}--- 生气状态下送礼 ---{Colors.RESET}")
    _EMOTION_SCORES[f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"]["score"] = -40
    _EMOTION_SCORES[f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"]["state"] = EmotionState.ANGRY
    
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "生气状态")
    
    data, accepted, msg = await emotion_score_service.apply_gift_effect(
        TEST_USER_ID, TEST_CHARACTER_ID, "rose", intimacy_level=20
    )
    print(f"🌹 送玫瑰: {'✅ 接受' if accepted else '❌ 拒绝'} {msg or ''}")
    print_status(data, "送礼后")
    print(f"   → 生气时普通礼物效果大打折扣")
    
    # 冷战状态送礼
    print(f"\n{Colors.CYAN}--- 冷战状态下送礼 ---{Colors.RESET}")
    _EMOTION_SCORES[f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"]["score"] = -85
    _EMOTION_SCORES[f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"]["state"] = EmotionState.COLD_WAR
    _EMOTION_SCORES[f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"]["in_cold_war"] = True
    
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data, "冷战状态")
    
    # 普通礼物被拒
    data, accepted, msg = await emotion_score_service.apply_gift_effect(
        TEST_USER_ID, TEST_CHARACTER_ID, "chocolate", intimacy_level=20
    )
    print(f"🍫 送巧克力: {'✅ 接受' if accepted else '❌ 拒绝'} {msg or ''}")
    print_status(data, "送礼后")
    
    # 道歉礼物
    data, accepted, msg = await emotion_score_service.apply_gift_effect(
        TEST_USER_ID, TEST_CHARACTER_ID, "apology_bouquet", intimacy_level=20
    )
    print(f"💐 送道歉花束: {'✅ 接受' if accepted else '❌ 拒绝'} {msg or ''}")
    print_status(data, "送礼后")
    
    print(f"\n✅ 礼物系统测试完成")
    return data


async def test_intimacy_factor():
    """测试：亲密度系数影响"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("测试场景：亲密度系数对 delta 的影响")
    print(f"{'='*50}{Colors.RESET}\n")
    
    from app.services.emotion_score_service import _EMOTION_SCORES
    
    test_cases = [
        (10, -30, "低亲密度受到伤害"),
        (50, -30, "中亲密度受到伤害"),
        (90, -30, "高亲密度受到伤害"),
        (10, 20, "低亲密度收到甜言蜜语"),
        (50, 20, "中亲密度收到甜言蜜语"),
        (90, 20, "高亲密度收到甜言蜜语"),
    ]
    
    print(f"{'亲密度':<10} {'原始delta':<12} {'实际变化':<12} {'场景':<20}")
    print("-" * 55)
    
    for intimacy, delta, scenario in test_cases:
        _EMOTION_SCORES.clear()
        
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        old_score = data["score"]
        
        data = await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, delta, reason=scenario, intimacy_level=intimacy
        )
        
        actual_delta = data["score"] - old_score
        print(f"{intimacy:<10} {delta:+d}{'':<9} {actual_delta:+d}{'':<9} {scenario:<20}")
    
    print(f"\n💡 规律：亲密度越高，负面伤害越小，正面收益越大")
    print(f"✅ 亲密度系数测试完成")


async def test_full_relationship_arc():
    """测试：完整关系线（从认识到冷战到和好）"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("测试场景：完整关系线")
    print(f"{'='*60}{Colors.RESET}\n")
    
    from app.services.emotion_score_service import _EMOTION_SCORES
    _EMOTION_SCORES.clear()
    
    story = [
        # 初识
        (8, 10, "你好，很高兴认识你", "初次见面"),
        (10, 12, "你的名字很好听", "夸奖"),
        (15, 15, "我们可以经常聊天吗", "表达兴趣"),
        
        # 升温
        (18, 18, "想你了", "思念"),
        (22, 22, "你是我见过最温柔的人", "真诚赞美"),
        (25, 28, "我好喜欢和你聊天", "表达喜欢"),
        
        # 作死
        (-20, 30, "你今天怎么这副表情", "说错话"),
        (-15, 30, "我开玩笑的啦", "狡辩"),
        (-25, 30, "好好好都是我的错", "敷衍道歉"),
        (-35, 30, "你太敏感了吧", "火上浇油"),
        
        # 挽回
        (5, 30, "对不起...", "试探道歉"),
        (30, 30, "我真的知道错了，我不该那样说", "真诚道歉"),
        (20, 32, "以后我会注意的", "承诺改变"),
        (25, 35, "[送礼物] 这是给你的，希望你能原谅我", "送礼"),
    ]
    
    for delta, intimacy, msg, reason in story:
        print(f"\n{'💕' if delta > 0 else '💔'} \"{msg}\"")
        
        data = await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, delta, reason=reason, intimacy_level=intimacy
        )
        print_status(data, f"delta {delta:+d}")
        
        if data.get("in_cold_war"):
            print(f"   {Colors.RED}→ 进入冷战{Colors.RESET}")
        
        await asyncio.sleep(0.1)  # 模拟时间流逝
    
    print(f"\n{'='*60}")
    print(f"✅ 完整关系线测试完成")
    print(f"最终状态: {data['state']} | 情绪: {data['score']:+d}")


async def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║           🎀 小美情绪系统测试套件 🎀                    ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    await test_normal_conversation()
    await test_sweet_talk()
    await test_anger_to_cold_war()
    await test_apology_recovery()
    await test_gift_effects()
    await test_intimacy_factor()
    await test_full_relationship_arc()
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║                 ✅ 所有测试完成！                       ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())

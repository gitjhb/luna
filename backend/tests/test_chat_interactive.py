"""
交互式聊天测试
==============

模拟真实聊天，测试 LLM 情绪分析 + 情绪系统

运行方式：
  cd backend
  .venv/bin/python tests/test_chat_interactive.py

支持命令：
  /status  - 查看当前状态
  /reset   - 重置状态
  /gift <礼物名>  - 送礼物
  /angry   - 设置为生气状态
  /cold    - 设置为冷战状态
  /happy   - 设置为开心状态
  /quit    - 退出
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["MOCK_DATABASE"] = "true"  # 使用内存存储

from app.services.emotion_score_service import (
    emotion_score_service, 
    EmotionState,
    _EMOTION_SCORES
)

# 尝试导入 LLM 服务
try:
    from app.services.emotion_llm_service import emotion_llm_service
    HAS_LLM = True
except ImportError as e:
    print(f"⚠️  LLM 服务不可用: {e}")
    print("   将使用模拟的情绪分析\n")
    HAS_LLM = False

TEST_USER_ID = "interactive-user"
TEST_CHARACTER_ID = "xiaomei"


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_status(data: dict):
    """打印当前状态"""
    score = data["score"]
    state = data["state"]
    
    if score >= 50:
        bar_color = Colors.GREEN
        emoji = "😊"
    elif score >= 0:
        bar_color = Colors.CYAN
        emoji = "🙂"
    elif score >= -50:
        bar_color = Colors.YELLOW
        emoji = "😐"
    else:
        bar_color = Colors.RED
        emoji = "😠"
    
    # 情绪条
    bar_length = 20
    filled = int((score + 100) / 200 * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    cold_war = " ❄️冷战中" if data.get("in_cold_war") else ""
    
    print(f"\n{bar_color}┌─────────────────────────────────────┐")
    print(f"│ {emoji} 情绪: {score:+4d}/100  [{bar}]{cold_war}")
    print(f"│ 📊 状态: {state:<10}")
    print(f"│ 💕 亲密度: {data.get('intimacy', 'N/A')}")
    print(f"└─────────────────────────────────────┘{Colors.RESET}\n")


def mock_emotion_analysis(message: str, current_mood: int) -> dict:
    """
    模拟情绪分析（当 LLM 不可用时）
    简单基于关键词的判断
    """
    message_lower = message.lower()
    
    # 正面关键词
    positive_words = ["喜欢", "爱", "想你", "好看", "漂亮", "温柔", "开心", "谢谢", "辛苦"]
    # 负面关键词
    negative_words = ["讨厌", "烦", "笨", "丑", "无聊", "算了", "随便", "敷衍"]
    # 道歉关键词
    apology_words = ["对不起", "抱歉", "我错了", "原谅"]
    
    delta = 0
    trigger_type = "normal"
    reason = "普通对话"
    
    for word in apology_words:
        if word in message:
            delta = 20
            trigger_type = "apology"
            reason = "道歉"
            break
    
    if delta == 0:
        for word in positive_words:
            if word in message:
                delta = 15
                trigger_type = "sweet"
                reason = f"包含正面词汇: {word}"
                break
    
    if delta == 0:
        for word in negative_words:
            if word in message:
                delta = -20
                trigger_type = "rude"
                reason = f"包含负面词汇: {word}"
                break
    
    if delta == 0:
        # 默认小幅正面
        delta = 3
        reason = "普通聊天"
    
    # 冷战时普通消息无效
    if current_mood <= -75 and trigger_type not in ["apology"]:
        delta = min(delta, 0)
        reason = "冷战中，普通消息无效"
    
    return {
        "delta": delta,
        "trigger_type": trigger_type,
        "should_reject": delta < -15,
        "suggested_mood": "neutral",
        "reason": reason
    }


async def analyze_and_update(message: str, intimacy_level: int = 20) -> dict:
    """分析消息并更新情绪"""
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    current_mood = data["score"]
    current_state = data["state"]
    
    if HAS_LLM:
        try:
            analysis = await emotion_llm_service.analyze_message(
                message=message,
                intimacy_level=intimacy_level,
                current_mood=current_mood,
                current_state=current_state,
                is_spicy=False,
                boundaries=5,
                is_subscribed=True
            )
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  LLM 调用失败: {e}{Colors.RESET}")
            print(f"   使用模拟分析...\n")
            analysis = mock_emotion_analysis(message, current_mood)
    else:
        analysis = mock_emotion_analysis(message, current_mood)
    
    delta = analysis.get("delta", 0)
    reason = analysis.get("reason", "")
    trigger_type = analysis.get("trigger_type", "normal")
    
    print(f"{Colors.CYAN}📝 分析结果:{Colors.RESET}")
    print(f"   delta: {delta:+d}")
    print(f"   类型: {trigger_type}")
    print(f"   原因: {reason}")
    
    if delta != 0:
        data = await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, delta,
            reason=f"{trigger_type}: {reason}",
            intimacy_level=intimacy_level
        )
    
    return data


async def handle_command(cmd: str) -> bool:
    """处理命令，返回是否继续"""
    parts = cmd.strip().split()
    command = parts[0].lower()
    
    if command == "/quit" or command == "/exit":
        return False
    
    elif command == "/status":
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        print_status(data)
    
    elif command == "/reset":
        _EMOTION_SCORES.clear()
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        print(f"{Colors.GREEN}✅ 状态已重置{Colors.RESET}")
        print_status(data)
    
    elif command == "/gift":
        gift_name = parts[1] if len(parts) > 1 else "chocolate"
        data, accepted, msg = await emotion_score_service.apply_gift_effect(
            TEST_USER_ID, TEST_CHARACTER_ID, gift_name, intimacy_level=20
        )
        status = "✅ 接受" if accepted else "❌ 拒绝"
        print(f"\n🎁 送出 {gift_name}: {status}")
        if msg:
            print(f"   {msg}")
        print_status(data)
    
    elif command == "/angry":
        key = f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"
        if key not in _EMOTION_SCORES:
            await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        _EMOTION_SCORES[key]["score"] = -45
        _EMOTION_SCORES[key]["state"] = EmotionState.ANGRY
        print(f"{Colors.YELLOW}😠 已设置为生气状态{Colors.RESET}")
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        print_status(data)
    
    elif command == "/cold":
        key = f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"
        if key not in _EMOTION_SCORES:
            await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        _EMOTION_SCORES[key]["score"] = -85
        _EMOTION_SCORES[key]["state"] = EmotionState.COLD_WAR
        _EMOTION_SCORES[key]["in_cold_war"] = True
        print(f"{Colors.RED}❄️  已设置为冷战状态{Colors.RESET}")
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        print_status(data)
    
    elif command == "/happy":
        key = f"{TEST_USER_ID}:{TEST_CHARACTER_ID}"
        if key not in _EMOTION_SCORES:
            await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        _EMOTION_SCORES[key]["score"] = 70
        _EMOTION_SCORES[key]["state"] = EmotionState.HAPPY
        _EMOTION_SCORES[key]["in_cold_war"] = False
        print(f"{Colors.GREEN}😊 已设置为开心状态{Colors.RESET}")
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        print_status(data)
    
    elif command == "/help":
        print(f"""
{Colors.CYAN}可用命令:{Colors.RESET}
  /status  - 查看当前状态
  /reset   - 重置状态
  /gift <礼物名>  - 送礼物 (chocolate, rose, apology_bouquet, jewelry...)
  /angry   - 设置为生气状态
  /cold    - 设置为冷战状态  
  /happy   - 设置为开心状态
  /quit    - 退出
  
直接输入文字则模拟发送消息。
""")
    
    else:
        print(f"{Colors.YELLOW}未知命令: {command}，输入 /help 查看帮助{Colors.RESET}")
    
    return True


async def main():
    print(f"""
{Colors.BOLD}{Colors.MAGENTA}
╔═══════════════════════════════════════════════════════╗
║          🎀 小美情绪系统 - 交互式测试 🎀              ║
╠═══════════════════════════════════════════════════════╣
║  输入消息模拟聊天，观察情绪变化                       ║
║  输入 /help 查看命令列表                              ║
║  输入 /quit 退出                                      ║
╚═══════════════════════════════════════════════════════╝
{Colors.RESET}""")
    
    # 显示初始状态
    data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
    print_status(data)
    
    while True:
        try:
            user_input = input(f"{Colors.BOLD}你: {Colors.RESET}").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                should_continue = await handle_command(user_input)
                if not should_continue:
                    print(f"\n{Colors.MAGENTA}👋 再见！{Colors.RESET}\n")
                    break
            else:
                # 普通消息
                data = await analyze_and_update(user_input)
                print_status(data)
                
                # 根据状态给出小美的反应提示
                if data.get("in_cold_war"):
                    print(f"{Colors.RED}[小美没有回复你的消息]{Colors.RESET}\n")
                elif data["score"] < -35:
                    print(f"{Colors.YELLOW}[小美看起来很生气]{Colors.RESET}\n")
                elif data["score"] > 70:
                    print(f"{Colors.GREEN}[小美看起来很开心]{Colors.RESET}\n")
        
        except KeyboardInterrupt:
            print(f"\n\n{Colors.MAGENTA}👋 再见！{Colors.RESET}\n")
            break
        except EOFError:
            break


if __name__ == "__main__":
    asyncio.run(main())

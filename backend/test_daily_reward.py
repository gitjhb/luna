#!/usr/bin/env python3
"""
每日签到奖励 API 测试脚本
测试连续签到逻辑和奖励计算
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.v1.daily_reward import _get_checkin_data, _save_checkin_data, _calculate_consecutive_days, _get_reward_amount, CONSECUTIVE_REWARDS, TIER_MULTIPLIERS
from datetime import date, timedelta

async def test_daily_reward_system():
    """测试每日奖励系统的各个功能"""
    
    print("🧪 测试每日签到奖励系统\n")
    
    # 测试用户ID
    test_user_id = "test_user_123"
    
    print("1. 测试奖励配置")
    print(f"   连续奖励配置: {CONSECUTIVE_REWARDS}")
    print(f"   订阅倍率配置: {TIER_MULTIPLIERS}\n")
    
    print("2. 测试连续签到天数计算")
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    
    # 首次签到
    consecutive_days = _calculate_consecutive_days(None)
    print(f"   首次签到: {consecutive_days} 天")
    
    # 昨天签到过，今天继续
    consecutive_days = _calculate_consecutive_days(yesterday.isoformat())
    print(f"   昨天签到过: {consecutive_days} 天")
    
    # 断签后重新开始
    consecutive_days = _calculate_consecutive_days(two_days_ago.isoformat())
    print(f"   两天前签到过(断签): {consecutive_days} 天")
    
    # 今天已签到
    consecutive_days = _calculate_consecutive_days(today.isoformat())
    print(f"   今天已签到: {consecutive_days} 天\n")
    
    print("3. 测试奖励金额计算")
    for tier in ['free', 'premium', 'vip']:
        print(f"   {tier} 用户:")
        for day in range(1, 8):
            reward = _get_reward_amount(day, tier)
            base = CONSECUTIVE_REWARDS.get(day, 5)
            multiplier = TIER_MULTIPLIERS.get(tier, 1.0)
            print(f"     第{day}天: {reward} 月石 (基础{base} × {multiplier})")
        print()
    
    print("4. 测试数据存储和读取")
    
    # 模拟首次签到
    initial_data = await _get_checkin_data(test_user_id)
    print(f"   初始数据: {initial_data}")
    
    # 保存签到数据
    test_date = today.isoformat()
    test_consecutive = 3
    
    await _save_checkin_data(test_user_id, test_date, test_consecutive)
    print(f"   保存数据: 日期={test_date}, 连续={test_consecutive}天")
    
    # 读取签到数据
    saved_data = await _get_checkin_data(test_user_id)
    print(f"   读取数据: {saved_data}")
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_daily_reward_system())
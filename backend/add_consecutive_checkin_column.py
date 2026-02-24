#!/usr/bin/env python3
"""
数据库迁移: 添加 consecutive_checkin_days 字段
为 user_subscriptions 表添加连续签到天数字段
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import get_db

async def migrate_db():
    """添加 consecutive_checkin_days 字段到 user_subscriptions 表"""
    
    print("🔧 开始数据库迁移: 添加连续签到天数字段")
    
    try:
        async with get_db() as db:
            # 检查字段是否已存在
            check_column_sql = """
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'user_subscriptions' 
                AND COLUMN_NAME = 'consecutive_checkin_days'
            """
            
            result = await db.execute(text(check_column_sql))
            column_exists = result.scalar() > 0
            
            if column_exists:
                print("✅ consecutive_checkin_days 字段已存在，无需迁移")
                return
            
            # 添加新字段
            add_column_sql = """
                ALTER TABLE user_subscriptions 
                ADD COLUMN consecutive_checkin_days INT DEFAULT 0
            """
            
            await db.execute(text(add_column_sql))
            await db.commit()
            
            print("✅ 成功添加 consecutive_checkin_days 字段")
            
            # 验证字段已添加
            verify_sql = """
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'user_subscriptions' 
                AND COLUMN_NAME = 'consecutive_checkin_days'
            """
            
            result = await db.execute(text(verify_sql))
            if result.scalar() > 0:
                print("✅ 字段验证成功")
            else:
                print("❌ 字段验证失败")
                
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_db())
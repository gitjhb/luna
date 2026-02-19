#!/usr/bin/env python3
"""
清理重复的"初次相遇"事件记录
============================

每个 user_id + character_id 组合只保留最早的一条 first_meet 记录。
"""

import sqlite3
import sys
from pathlib import Path


def cleanup_duplicate_first_meet(db_path: str, dry_run: bool = True):
    """清理重复的 first_meet 事件"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 找出所有重复的 first_meet 记录
    cursor.execute("""
        SELECT user_id, character_id, COUNT(*) as cnt 
        FROM user_character_events 
        WHERE event_type='first_meet' 
        GROUP BY user_id, character_id 
        HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("✅ 没有发现重复的初次相遇记录")
        conn.close()
        return
    
    print(f"发现 {len(duplicates)} 组重复记录:\n")
    
    total_deleted = 0
    
    for user_id, character_id, count in duplicates:
        print(f"  用户: {user_id}")
        print(f"  角色: {character_id}")
        print(f"  重复次数: {count}")
        
        # 找出该组合的所有 first_meet 记录，按时间排序
        cursor.execute("""
            SELECT id, created_at 
            FROM user_character_events 
            WHERE user_id = ? AND character_id = ? AND event_type = 'first_meet'
            ORDER BY created_at ASC
        """, (user_id, character_id))
        
        records = cursor.fetchall()
        keep_id = records[0][0]  # 保留最早的
        delete_ids = [r[0] for r in records[1:]]  # 删除其他的
        
        print(f"  保留 ID: {keep_id} ({records[0][1]})")
        print(f"  删除 IDs: {delete_ids}")
        
        if not dry_run:
            # 执行删除
            placeholders = ','.join('?' * len(delete_ids))
            cursor.execute(f"""
                DELETE FROM user_character_events 
                WHERE id IN ({placeholders})
            """, delete_ids)
            total_deleted += len(delete_ids)
        
        print()
    
    if dry_run:
        print("=" * 50)
        print("⚠️  DRY RUN 模式 - 没有实际删除数据")
        print(f"   如需执行删除，请运行: python {sys.argv[0]} --execute")
    else:
        conn.commit()
        print("=" * 50)
        print(f"✅ 已删除 {total_deleted} 条重复记录")
    
    conn.close()


if __name__ == "__main__":
    # 默认数据库路径
    db_path = Path(__file__).parent.parent / "data" / "app.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    dry_run = "--execute" not in sys.argv
    
    print(f"数据库: {db_path}")
    print(f"模式: {'DRY RUN (预览)' if dry_run else 'EXECUTE (执行删除)'}")
    print("=" * 50)
    print()
    
    cleanup_duplicate_first_meet(str(db_path), dry_run=dry_run)

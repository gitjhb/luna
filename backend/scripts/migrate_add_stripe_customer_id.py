#!/usr/bin/env python3
"""
Migration: Add stripe_customer_id column to users table

Run this once to add the new column for existing databases.

Usage:
    python scripts/migrate_add_stripe_customer_id.py

For SQLite (development):
    ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(128) UNIQUE;

For PostgreSQL (production):
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(128) UNIQUE;
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def migrate_sqlite():
    """Add column to SQLite database"""
    import aiosqlite
    
    db_path = os.getenv("SQLITE_DB_PATH", "data/luna.db")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("The column will be created automatically when the app starts.")
        return
    
    async with aiosqlite.connect(db_path) as db:
        # Check if users table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        table_exists = await cursor.fetchone()
        
        if not table_exists:
            print("Users table doesn't exist yet.")
            print("The column will be created automatically when the app starts.")
            return
        
        # Check if column exists
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "stripe_customer_id" in column_names:
            print("Column 'stripe_customer_id' already exists in users table.")
            return
        
        # Add column (SQLite doesn't support UNIQUE in ALTER TABLE, add index separately)
        print("Adding 'stripe_customer_id' column to users table...")
        await db.execute(
            "ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(128)"
        )
        
        # Try to add unique index (may fail if duplicates exist, which is fine)
        try:
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id)"
            )
        except Exception as e:
            print(f"Warning: Could not create unique index: {e}")
        
        await db.commit()
        print("✅ Migration complete!")


async def migrate_postgres():
    """Add column to PostgreSQL database"""
    import asyncpg
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set, skipping PostgreSQL migration")
        return
    
    conn = await asyncpg.connect(database_url)
    try:
        # Check if column exists
        result = await conn.fetchval("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='users' AND column_name='stripe_customer_id'
        """)
        
        if result:
            print("Column 'stripe_customer_id' already exists in users table.")
            return
        
        # Add column
        print("Adding 'stripe_customer_id' column to users table...")
        await conn.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(128) UNIQUE
        """)
        print("✅ Migration complete!")
    finally:
        await conn.close()


async def main():
    print("=" * 50)
    print("Migration: Add stripe_customer_id to users table")
    print("=" * 50)
    
    # Try SQLite first (development)
    sqlite_db = os.getenv("SQLITE_DB_PATH", "data/luna.db")
    if os.path.exists(sqlite_db):
        print(f"\nFound SQLite database: {sqlite_db}")
        await migrate_sqlite()
    
    # Try PostgreSQL (production)
    if os.getenv("DATABASE_URL"):
        print("\nFound DATABASE_URL, checking PostgreSQL...")
        await migrate_postgres()
    
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

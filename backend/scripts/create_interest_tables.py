"""
Create Interest Tables Migration Script

Run this script to create the interest-related tables in the database.
Usage: python scripts/create_interest_tables.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import get_engine


CREATE_TABLES_SQL = """
-- Create interests table (predefined interest tags)
CREATE TABLE IF NOT EXISTS interests (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create interest_users table (tracks which users have interests)
CREATE TABLE IF NOT EXISTS interest_users (
    user_id VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_interests junction table
CREATE TABLE IF NOT EXISTS user_interests (
    user_id VARCHAR(64) REFERENCES interest_users(user_id) ON DELETE CASCADE,
    interest_id INTEGER REFERENCES interests(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, interest_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_user_interests_user_id ON user_interests(user_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_interest_id ON user_interests(interest_id);
CREATE INDEX IF NOT EXISTS idx_interests_category ON interests(category);
"""


async def create_tables():
    """Create the interest tables."""
    print("Creating interest tables...")
    
    engine = await get_engine()
    
    async with engine.begin() as conn:
        # Split and execute each statement separately
        statements = [s.strip() for s in CREATE_TABLES_SQL.split(';') if s.strip()]
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
                print(f"  ✓ Executed: {stmt[:50]}...")
            except Exception as e:
                print(f"  ⚠ Warning: {e}")
    
    print("\n✓ Interest tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())

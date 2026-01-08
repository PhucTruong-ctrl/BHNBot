#!/usr/bin/env python3
"""
Migration: Add daily streak columns to users table.

Adds:
- daily_streak: INT - consecutive days claimed
- streak_protection: BOOLEAN - whether user has streak protection available

Run: python scripts/add_streak_columns.py
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def migrate():
    """Add daily_streak and streak_protection columns to users table."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        existing = await conn.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN ('daily_streak', 'streak_protection')
        """)
        existing_cols = [r['column_name'] for r in existing]
        
        if 'daily_streak' not in existing_cols:
            await conn.execute("""
                ALTER TABLE users ADD COLUMN daily_streak INT DEFAULT 0
            """)
            print("✅ Added daily_streak column")
        else:
            print("⏭️  daily_streak column already exists")
        
        if 'streak_protection' not in existing_cols:
            await conn.execute("""
                ALTER TABLE users ADD COLUMN streak_protection BOOLEAN DEFAULT FALSE
            """)
            print("✅ Added streak_protection column")
        else:
            print("⏭️  streak_protection column already exists")
        
        print("\n🎉 Migration complete!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())

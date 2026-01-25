#!/usr/bin/env python3
"""
Migration script for seasonal event tables schema fixes.

Fixes:
1. event_fish_collection: Add guild_id, event_id, caught_at columns
   - Old PK: (user_id, fish_key) 
   - New PK: (guild_id, user_id, event_id, fish_key)

2. event_shop_purchases: Add price_paid, purchased_at columns

Run with: python scripts/migrate_seasonal_schema.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager


async def migrate_event_fish_collection(db: DatabaseManager) -> int:
    check = await db.fetchrow(
        """
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'event_fish_collection' AND column_name = 'guild_id'
        """
    )
    if check:
        print("✓ event_fish_collection already has guild_id column")
        return 0
    
    print("Migrating event_fish_collection...")
    
    old_data = await db.fetchall("SELECT * FROM event_fish_collection")
    if not old_data:
        print("  No existing data to migrate")
        await db.execute("DROP TABLE IF EXISTS event_fish_collection")
        await db.execute("""
            CREATE TABLE event_fish_collection (
                guild_id BIGINT,
                user_id BIGINT,
                event_id TEXT,
                fish_key TEXT,
                quantity INTEGER DEFAULT 1,
                caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, event_id, fish_key)
            )
        """)
        print("✓ Created fresh event_fish_collection table")
        return 0
    
    await db.execute("""
        ALTER TABLE event_fish_collection 
        ADD COLUMN IF NOT EXISTS guild_id BIGINT,
        ADD COLUMN IF NOT EXISTS caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """)
    
    await db.execute("""
        UPDATE event_fish_collection 
        SET guild_id = 0, event_id = COALESCE(event_id, 'unknown')
        WHERE guild_id IS NULL
    """)
    
    print(f"✓ Migrated {len(old_data)} rows (set guild_id=0 for legacy data)")
    return len(old_data)


async def migrate_event_shop_purchases(db: DatabaseManager) -> int:
    check = await db.fetchrow(
        """
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'event_shop_purchases' AND column_name = 'price_paid'
        """
    )
    if check:
        print("✓ event_shop_purchases already has price_paid column")
        return 0
    
    print("Migrating event_shop_purchases...")
    
    await db.execute("""
        ALTER TABLE event_shop_purchases 
        ADD COLUMN IF NOT EXISTS price_paid INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """)
    
    result = await db.fetchrow("SELECT COUNT(*) as cnt FROM event_shop_purchases")
    count = result["cnt"] if result else 0
    
    print(f"✓ Added price_paid, purchased_at columns ({count} existing rows)")
    return count


async def main() -> None:
    print("=" * 50)
    print("Seasonal Events Schema Migration")
    print("=" * 50)
    
    db = DatabaseManager()
    try:
        await db.init()
        
        fish_count = await migrate_event_fish_collection(db)
        shop_count = await migrate_event_shop_purchases(db)
        
        print()
        print("=" * 50)
        print(f"Migration complete!")
        print(f"  - event_fish_collection: {fish_count} rows processed")
        print(f"  - event_shop_purchases: {shop_count} rows processed")
        print("=" * 50)
        
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())

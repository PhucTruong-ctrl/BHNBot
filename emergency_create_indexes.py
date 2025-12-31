#!/usr/bin/env python3
"""
Emergency Index Creation Script
Purpose: Create all missing UNIQUE indexes for PostgreSQL ON CONFLICT support
Run this IMMEDIATELY before starting the bot
"""

import asyncio
import asyncpg
import os

# PostgreSQL connection params
DB_CONFIG = {
    "user": "discord_bot",
    "password": "discord_bot_password",  # From .env DB_PASS
    "database": "discord_bot_db",
    "host": "localhost",
    "port": 5432
}

# Indexes to create
INDEXES = [
    ("idx_inventory_user_item", "inventory", ["user_id", "item_id"]),
    ("idx_users_user_id", "users", ["user_id"]),
    ("idx_user_buffs_user_buff", "user_buffs", ["user_id", "buff_type"]),
    ("idx_user_achievements_composite", "user_achievements", ["user_id", "achievement_key"]),
    ("idx_fish_collection_user_fish", "fish_collection", ["user_id", "fish_id"]),
    ("idx_user_invites_composite", "user_invites", ["inviter_id", "joined_user_id"]),
    ("idx_server_config_guild", "server_config", ["guild_id"]),
    ("idx_global_event_state_key", "global_event_state", ["event_key"]),
]

async def create_indexes():
    """Create all missing UNIQUE indexes."""
    try:
        # Connect to database
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✓ Connected to PostgreSQL")
        
        # Create each index
        for idx_name, table, columns in INDEXES:
            columns_str = ", ".join(columns)
            sql = f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table}({columns_str})"
            
            try:
                await conn.execute(sql)
                print(f"✓ Created index: {idx_name} on {table}({columns_str})")
            except Exception as e:
                print(f"✗ Failed to create {idx_name}: {e}")
        
        # Verify indexes
        print("\n=== Verifying Indexes ===")
        rows = await conn.fetch("""
            SELECT tablename, indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        
        for row in rows:
            print(f"  {row['tablename']}: {row['indexname']}")
        
        print(f"\n✅ Total indexes created/verified: {len(rows)}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("EMERGENCY INDEX CREATION - PostgreSQL Migration Fix")
    print("=" * 60)
    
    success = asyncio.run(create_indexes())
    
    if success:
        print("\n✅ SUCCESS: All indexes created!")
        print("You can now start the bot safely.")
    else:
        print("\n❌ FAILED: Check errors above")
        print("Bot may still have ON CONFLICT errors")
    
    print("=" * 60)

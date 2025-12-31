#!/usr/bin/env python3
"""
PostgreSQL Migration Verification Script
Purpose: Test database connection, schema, and type handling
Run this BEFORE starting the bot to ensure migration is stable
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime, timezone

# Database config
DB_CONFIG = {
    "user": "discord_bot",
    "password": "discord_bot_password",
    "database": "discord_bot_db",
    "host": "localhost",
    "port": 5432
}

async def verify_migration():
    """Run all verification checks."""
    print("="  * 70)
    print("PostgreSQL Migration Verification")
    print("=" * 70)
    
    try:
        # 1. Test Connection
        print("\n[1/5] Testing database connection...")
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✓ Connection successful")
        
        # 2. Verify Schema - Check UNIQUE constraints
        print("\n[2/5] Verifying UNIQUE indexes...")
        required_indexes = [
            "idx_inventory_user_item",
            "idx_users_user_id",
            "idx_user_buffs_user_buff",
            "idx_user_achievements_composite",
            "idx_fish_collection_user_fish",
            "idx_user_invites_composite",
            "idx_server_config_guild",
            "idx_global_event_state_key"
        ]
        
        rows = await conn.fetch("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' AND indexname = ANY($1::text[])
        """, required_indexes)
        
        found_indexes = [row['indexname'] for row in rows]
        missing = set(required_indexes) - set(found_indexes)
        
        if missing:
            print(f"✗ Missing indexes: {missing}")
            return False
        print(f"✓ All {len(required_indexes)} indexes present")
        
        # 3. Test Query Operations
        print("\n[3/5] Testing query operations...")
        
        # Test INSERT with ON CONFLICT
        test_user_id = 999999999
        await conn.execute("""
            INSERT INTO users (user_id, username, seeds) 
            VALUES ($1, $2, $3)
            ON CONFLICTuser_id) DO UPDATE SET username = EXCLUDED.username
        """, test_user_id, "test_verification", 0)
        
        # Test SELECT
        row = await conn.fetchone("SELECT username FROM users WHERE user_id = $1", test_user_id)
        if row and row['username'] == "test_verification":
            print("✓ INSERT/SELECT operations working")
        else:
            print("✗ INSERT/SELECT test failed")
            return False
        
        # Cleanup
        await conn.execute("DELETE FROM users WHERE user_id = $1", test_user_id)
        
        # 4. Test Type Compatibility
        print("\n[4/5] Testing datetime type handling...")
        
        # Create test entry with datetime
        test_datetime = datetime.now(timezone.utc)
        await conn.execute("""
            INSERT INTO server_config (guild_id, bump_start_time)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET bump_start_time = EXCLUDED.bump_start_time
        """, 888888888, test_datetime)
        
        # Retrieve and verify type
        row = await conn.fetchone(
            "SELECT bump_start_time FROM server_config WHERE guild_id = $1",
            888888888
        )
        
        if row and isinstance(row['bump_start_time'], datetime):
            print("✓ asyncpg returns native datetime objects (correct)")
        else:
            print(f"✗ Type mismatch: got {type(row['bump_start_time'])} expected datetime")
            return False
        
        # Cleanup
        await conn.execute("DELETE FROM server_config WHERE guild_id = $1", 888888888)
        
        # 5. Test Transaction Support
        print("\n[5/5] Testing transaction support...")
        
        async with conn.transaction():
            await conn.execute("""
                INSERT INTO users (user_id, username, seeds) 
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
            """, 777777777, "transaction_test", 100)
        
        row = await conn.fetchone("SELECT seeds FROM users WHERE user_id = $1", 777777777)
        if row and row['seeds'] == 100:
            print("✓ Transactions working correctly")
        else:
            print("✗ Transaction test failed")
            return False
        
        # Cleanup
        await conn.execute("DELETE FROM users WHERE user_id = $1", 777777777)
        
        await conn.close()
        
        print("\n" + "=" * 70)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("=" * 70)
        print("\n✓ Database is ready for bot startup")
        print("✓ All UNIQUE constraints in place")
        print("✓ Type conversions working correctly")
        print("✓ Transactions supported")
        print("\nYou can now safely start the Discord bot.")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_migration())
    sys.exit(0 if success else 1)

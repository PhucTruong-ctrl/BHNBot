"""
Database Migration Script: Add Missing Columns to server_config

Adds:
- fishing_channel_id (missing from production DB)
- bump_channel_id (new feature)
- bump_start_time (new feature)

Safe to run multiple times (uses IF NOT EXISTS pattern).

Author: BHNBot Team
Date: 2025-12-23
"""

import asyncio
import aiosqlite
from pathlib import Path

DB_PATH = "./data/database.db"


async def migrate_server_config():
    """Add missing columns to server_config table"""
    db_path = Path(DB_PATH)
    
    if not db_path.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    print("=" * 60)
    print("🔄 SERVER_CONFIG MIGRATION SCRIPT")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        
        # Get current columns
        cursor = await db.execute("PRAGMA table_info(server_config)")
        existing_columns = [row[1] for row in await cursor.fetchall()]
        
        print("📋 Current columns:")
        for col in existing_columns:
            print(f"  ✓ {col}")
        print()
        
        # Columns to add
        new_columns = [
            ("fishing_channel_id", "INTEGER"),
            ("bump_channel_id", "INTEGER"),
            ("bump_start_time", "DATETIME")
        ]
        
        added_count = 0
        print("🔧 Adding missing columns:")
        
        for col_name, col_type in new_columns:
            if col_name in existing_columns:
                print(f"  ⏭️  {col_name} - Already exists")
            else:
                try:
                    await db.execute(f"ALTER TABLE server_config ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ {col_name} - Added successfully")
                    added_count += 1
                except Exception as e:
                    print(f"  ❌ {col_name} - Error: {e}")
        
        await db.commit()
        
        print()
        print("=" * 60)
        if added_count > 0:
            print(f"✅ MIGRATION COMPLETE! Added {added_count} columns")
        else:
            print(f"✅ NO CHANGES NEEDED - All columns exist")
        print("=" * 60)
        print()
        
        # Verify
        print("🔍 VERIFICATION:")
        cursor = await db.execute("PRAGMA table_info(server_config)")
        final_columns = [row[1] for row in await cursor.fetchall()]
        
        for col in final_columns:
            print(f"  ✓ {col}")
        
        print()


async def main():
    """Main migration flow"""
    print()
    await migrate_server_config()
    print("✅ Migration script completed successfully!")
    print()


if __name__ == "__main__":
    asyncio.run(main())

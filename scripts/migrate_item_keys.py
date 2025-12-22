"""
Database Migration Script: English Item Keys → Vietnamese

Migrates all item keys in BOTH fishing_inventory and inventory tables.
Run this ONCE before deploying code changes.

Author: BHNBot Team
Date: 2025-12-23
"""

import asyncio
import aiosqlite
from pathlib import Path

# Item key mapping: old (English) → new (Vietnamese)
ITEM_KEY_MIGRATION = {
    # Special items
    "pearl": "ngoc_trai",
    "rod_material": "vat_lieu_nang_cap",
    
    # Chest loot items
    "fertilizer": "phan_bon",
    "puzzle_piece": "manh_ghep",
    "coin_pouch": "tui_tien",
    "gift_random": "qua_ngau_nhien",
    
    "puzzle_a": "manh_ghep_a",
    "puzzle_b": "manh_ghep_b",
    "puzzle_c": "manh_ghep_c",
    "puzzle_d": "manh_ghep_d",
    "puzzle_e": "manh_ghep_e",
    
    # Chest itself (if exists)
    "treasure_chest": "ruong_kho_bau",
}

# Database path
DB_PATH = "./data/database.db"


async def migrate_item_keys():
    """Migrate all item keys in fishing_inventory and inventory tables"""
    db_path = Path(DB_PATH)
    
    if not db_path.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    print("=" * 60)
    print("🔄 ITEM KEY MIGRATION SCRIPT")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Items to migrate: {len(ITEM_KEY_MIGRATION)}")
    print()
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for better concurrency
        await db.execute("PRAGMA journal_mode=WAL")
        
        total_updated = 0
        
        # TABLES TO MIGRATE: Only inventory table exists (fishing_inventory doesn't exist)
        tables = ["inventory"]
        
        for table in tables:
            print(f"\n📋 Migrating table: {table}")
            print("-" * 60)
            
            table_total = 0
            for old_key, new_key in ITEM_KEY_MIGRATION.items():
                # Get all user_ids with old key
                cursor = await db.execute(
                    f"SELECT user_id, SUM(quantity) as total_qty FROM {table} WHERE item_id = ? GROUP BY user_id",
                    (old_key,)
                )
                old_entries = await cursor.fetchall()
                
                if not old_entries:
                    continue
                
                migrated_count = 0
                for user_id, old_qty in old_entries:
                    # Check if user already has new key
                    cursor = await db.execute(
                        f"SELECT quantity FROM {table} WHERE user_id = ? AND item_id = ?",
                        (user_id, new_key)
                    )
                    existing = await cursor.fetchone()
                    
                    if existing:
                        # User has both old and new keys → MERGE (sum quantities)
                        new_total = existing[0] + old_qty
                        await db.execute(
                            f"UPDATE {table} SET quantity = ? WHERE user_id = ? AND item_id = ?",
                            (new_total, user_id, new_key)
                        )
                        # Delete old key entry
                        await db.execute(
                            f"DELETE FROM {table} WHERE user_id = ? AND item_id = ?",
                            (user_id, old_key)
                        )
                        print(f"  🔀 MERGE: user {user_id} | {old_key} ({old_qty}) + {new_key} ({existing[0]}) → {new_total}")
                    else:
                        # User only has old key → Simple rename
                        await db.execute(
                            f"UPDATE {table} SET item_id = ? WHERE user_id = ? AND item_id = ?",
                            (new_key, user_id, old_key)
                        )
                    
                    migrated_count += 1
                
                table_total += migrated_count
                total_updated += migrated_count
                if migrated_count > 0:
                    print(f"✅ {old_key:20} → {new_key:20} | Migrated {migrated_count:4} users")
            
            
            if table_total == 0:
                print("  ⏭️  No entries found in this table")
        
        # Commit changes
        await db.commit()
        
        print()
        print("=" * 60)
        print(f"✅ MIGRATION COMPLETE!")
        print(f"Total entries updated: {total_updated}")
        print("=" * 60)
        print()
        
        # Verify migration
        print("🔍 VERIFICATION:")
        for table in tables:
            print(f"\n{table}:")
            has_content = False
            for old_key, new_key in ITEM_KEY_MIGRATION.items():
                cursor = await db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE item_id = ?",
                    (old_key,)
                )
                old_count = (await cursor.fetchone())[0]
                
                cursor = await db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE item_id = ?",
                    (new_key,)
                )
                new_count = (await cursor.fetchone())[0]
                
                if old_count > 0:
                    print(f"  ⚠️  {old_key}: Still has {old_count} entries!")
                    has_content = True
                elif new_count > 0:
                    print(f"  ✅ {new_key}: {new_count} entries")
                    has_content = True
            
            if not has_content:
                print("  ⏭️  No relevant entries")
        
        print()


async def backup_database():
    """Create backup before migration"""
    import shutil
    from datetime import datetime
    
    backup_name = f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = f"./data/backups/{backup_name}"
    
    Path("./data/backups").mkdir(exist_ok=True)
    
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Backup created: {backup_path}")
    print()


async def main():
    """Main migration flow"""
    print()
    print("⚠️  WARNING: This will modify the database!")
    print("Creating backup first...")
    print()
    
    await backup_database()
    await migrate_item_keys()
    
    print("✅ Migration script completed successfully!")
    print()
    print("NEXT STEPS:")
    print("1. Deploy updated code with new item keys")
    print("2. Test fishing/inventory commands")
    print("3. Monitor for any issues")
    print()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Database Column Cleanup Migration

Removes unused columns from database:
- server_config: wolf_channel_id, giveaway_channel_id, bump_ping_roles
- inventory: obtained_at
- achievement_roles: achievement_key
- fishing_profiles: 5 quest columns

SAFETY:
- Backs up database before migration
- Uses transactions (auto-rollback on error)
- Verifies data integrity after migration
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = "./data/database.db"
BACKUP_DIR = "./data/backups"

def check_sqlite_version():
    """Check if SQLite supports DROP COLUMN."""
    version = sqlite3.sqlite_version_info
    print(f"SQLite version: {sqlite3.sqlite_version}")
    
    # DROP COLUMN supported from 3.35.0
    return version >= (3, 35, 0)

def backup_database():
    """Create timestamped backup."""
    Path(BACKUP_DIR).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}/database_before_cleanup_{timestamp}.db"
    
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def drop_column_modern(conn, table, column):
    """Drop column using ALTER TABLE DROP COLUMN (SQLite 3.35+)."""
    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    print(f"  ✅ Dropped {table}.{column}")

def recreate_table(conn, table, columns_to_keep):
    """Recreate table without certain columns (for old SQLite)."""
    cursor = conn.cursor()
    
    # Get current schema
    cursor.execute(f"PRAGMA table_info({table})")
    current_columns = cursor.fetchall()
    
    # Build new schema
    new_columns = []
    for col in current_columns:
        col_name = col[1]
        if col_name in columns_to_keep:
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else ""
            default = f"DEFAULT {col[4]}" if col[4] else ""
            pk = "PRIMARY KEY" if col[5] else ""
            new_columns.append(f"{col_name} {col_type} {not_null} {default} {pk}".strip())
    
    # Create temp table
    schema = ", ".join(new_columns)
    cursor.execute(f"CREATE TABLE {table}_new ({schema})")
    
    # Copy data
    cols = ", ".join(columns_to_keep)
    cursor.execute(f"INSERT INTO {table}_new ({cols}) SELECT {cols} FROM {table}")
    
    # Replace old table
    cursor.execute(f"DROP TABLE {table}")
    cursor.execute(f"ALTER TABLE {table}_new RENAME TO {table}")
    
    print(f"  ✅ Recreated {table} without removed columns")

def migrate_database():
    """Main migration logic."""
    print("=" * 80)
    print("DATABASE COLUMN CLEANUP MIGRATION")
    print("=" * 80)
    print()
    
    # Step 1: Backup
    print("[1/4] Creating backup...")
    backup_path = backup_database()
    print()
    
    # Step 2: Check SQLite version
    print("[2/4] Checking SQLite version...")
    supports_drop = check_sqlite_version()
    method = "ALTER TABLE DROP COLUMN" if supports_drop else "TABLE RECREATION"
    print(f"Migration method: {method}")
    print()
    
    # Step 3: Migrate
    print("[3/4] Removing unused columns...")
    conn = sqlite3.connect(DB_PATH)
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        if supports_drop:
            # Modern SQLite: Use DROP COLUMN
            print("\n📋 server_config:")
            drop_column_modern(conn, "server_config", "wolf_channel_id")
            drop_column_modern(conn, "server_config", "giveaway_channel_id")
            drop_column_modern(conn, "server_config", "bump_ping_roles")
            
            print("\n📋 inventory:")
            drop_column_modern(conn, "inventory", "obtained_at")
            
            print("\n📋 achievement_roles (recreate - PK column):")
            # Cannot drop PRIMARY KEY column, must recreate table
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE achievement_roles_new (guild_id INTEGER, role_id INTEGER, PRIMARY KEY (guild_id, role_id))")
            cursor.execute("INSERT INTO achievement_roles_new (guild_id, role_id) SELECT guild_id, role_id FROM achievement_roles")
            cursor.execute("DROP TABLE achievement_roles")
            cursor.execute("ALTER TABLE achievement_roles_new RENAME TO achievement_roles")
            print("  ✅ Recreated achievement_roles without achievement_key")
            
            print("\n📋 fishing_profiles:")
            drop_column_modern(conn, "fishing_profiles", "quest_thuong_luong")
            drop_column_modern(conn, "fishing_profiles", "quest_ca_ngan_ha")
            drop_column_modern(conn, "fishing_profiles", "quest_ca_phuong_hoang")
            drop_column_modern(conn, "fishing_profiles", "quest_cthulhu_con")
            drop_column_modern(conn, "fishing_profiles", "quest_ca_voi_52hz")
        else:
            # Old SQLite: Recreate tables
            print("\n📋 server_config:")
            recreate_table(conn, "server_config", [
                "guild_id", "logs_channel_id", "noitu_channel_id", "exclude_chat_channels",
                "harvest_buff_until", "werewolf_voice_channel_id", "fishing_channel_id",
                "bump_channel_id", "bump_start_time"
            ])
            
            print("\n📋 inventory:")
            recreate_table(conn, "inventory", [
                "user_id", "item_id", "quantity", "item_type"
            ])
            
            print("\n📋 achievement_roles:")
            recreate_table(conn, "achievement_roles", [
                "guild_id", "role_id"
            ])
            
            print("\n📋 fishing_profiles:")
            recreate_table(conn, "fishing_profiles", [
                "user_id", "rod_level", "rod_durability", "exp"
            ])
        
        conn.commit()
        print("\n✅ All columns removed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        print(f"Database rolled back. Restore from backup: {backup_path}")
        conn.close()
        return False
    
    conn.close()
    print()
    
    # Step 4: Verify
    print("[4/4] Verifying migration...")
    verify_migration()
    
    print()
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"Backup location: {backup_path}")
    print("If bot runs without errors, backup can be deleted.")
    return True

def verify_migration():
    """Verify database integrity after migration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check table schemas
    tables_to_check = ["server_config", "inventory", "achievement_roles", "fishing_profiles"]
    
    for table in tables_to_check:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"  {table}: {len(columns)} columns")
    
    # Run integrity check
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    
    if result == "ok":
        print(f"  ✅ Database integrity: OK")
    else:
        print(f"  ❌ Database integrity: {result}")
    
    conn.close()

if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)

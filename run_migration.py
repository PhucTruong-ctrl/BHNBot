#!/usr/bin/env python3
"""
Database Migration Runner - Apply Index Optimizations

Safely applies database indexes from optimize_indexes.sql
"""

import sqlite3
import os
import sys


def run_migration():
    """Apply database indexes from SQL file."""
    
    db_path = "data/database.db"
    sql_path = "optimize_indexes.sql"
    
    # Verify files exist
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database not found at {db_path}")
        return False
    
    if not os.path.exists(sql_path):
        print(f"❌ ERROR: SQL file not found at {sql_path}")
        return False
    
    print(f"📊 Reading SQL migration from {sql_path}...")
    
    try:
        # Read SQL file
        with open(sql_path, 'r') as f:
            sql_commands = f.read()
        
        # Connect to database
        print(f"🔌 Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute SQL (indexes are idempotent with IF NOT EXISTS)
        print(f"⚙️  Executing migration...")
        cursor.executescript(sql_commands)
        
        # Commit changes
        conn.commit()
        
        # Verify indexes were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = cursor.fetchall()
        
        print(f"✅ Migration successful!")
        print(f"   Created/Verified {len(indexes)} indexes:")
        for idx in indexes:
            print(f"   - {idx[0]}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ DATABASE ERROR: {e}")
        print(f"   Rolling back changes...")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: ADD INDEXES")
    print("=" * 60)
    print()
    
    success = run_migration()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ MIGRATION COMPLETED")
        sys.exit(0)
    else:
        print("❌ MIGRATION FAILED")
        sys.exit(1)

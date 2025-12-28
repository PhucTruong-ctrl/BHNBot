#!/usr/bin/env python3
"""
Database Backup Script - Pre-Migration Safety

Creates timestamped backup of database.db before running optimizations.
"""

import os
import shutil
from datetime import datetime
import sys


def backup_database():
    """Create timestamped backup of database."""
    
    # Paths
    db_path = "data/database.db"
    backup_dir = "data/backups"
    
    # Verify source exists
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database not found at {db_path}")
        return False
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"database_{timestamp}_pre_optimization.db"
    backup_path = os.path.join(backup_dir, backup_name)
    
    print(f"📦 Creating backup...")
    print(f"   Source: {db_path}")
    print(f"   Destination: {backup_path}")
    
    try:
        # Copy database
        shutil.copy2(db_path, backup_path)
        
        # Verify backup
        source_size = os.path.getsize(db_path)
        backup_size = os.path.getsize(backup_path)
        
        if backup_size == 0:
            print(f"❌ ERROR: Backup file is empty!")
            os.remove(backup_path)
            return False
        
        if backup_size != source_size:
            print(f"⚠️  WARNING: Size mismatch!")
            print(f"   Source: {source_size:,} bytes")
            print(f"   Backup: {backup_size:,} bytes")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                os.remove(backup_path)
                return False
        
        print(f"✅ Backup created successfully!")
        print(f"   Size: {backup_size:,} bytes")
        print(f"   Path: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Backup failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE BACKUP UTILITY")
    print("=" * 60)
    print()
    
    success = backup_database()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ PRE-FLIGHT CHECK PASSED")
        print("You may proceed with Phase 1 optimizations.")
        sys.exit(0)
    else:
        print("❌ PRE-FLIGHT CHECK FAILED")
        print("DO NOT proceed until backup is successful!")
        sys.exit(1)

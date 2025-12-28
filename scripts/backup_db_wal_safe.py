#!/usr/bin/env python3
"""
Enhanced Database Backup Script - WAL-Safe

Uses SQLite backup API to properly handle WAL files.
Safer than simple file copy for WAL mode databases.
"""

import sqlite3
import os
from datetime import datetime
import sys


def backup_database_wal_safe():
    """Create WAL-safe backup using SQLite backup API."""
    
    # Paths
    source_db = "data/database.db"
    backup_dir = "data/backups"
    
    # Verify source exists
    if not os.path.exists(source_db):
        print(f"❌ ERROR: Database not found at {source_db}")
        return False
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"database_{timestamp}_wal_safe.db"
    backup_path = os.path.join(backup_dir, backup_name)
    
    print(f"📦 Creating WAL-safe backup...")
    print(f"   Source: {source_db}")
    print(f"   Destination: {backup_path}")
    print(f"   Method: SQLite Backup API (handles WAL automatically)")
    
    try:
        # Connect to source database
        source = sqlite3.connect(source_db)
        
        # Connect to destination (creates new file)
        destination = sqlite3.connect(backup_path)
        
        # Perform backup using SQLite API
        # This handles WAL mode correctly and ensures consistency
        with destination:
            source.backup(destination, pages=100, progress=backup_progress)
        
        # Close connections
        destination.close()
        source.close()
        
        # Verify backup
        if not os.path.exists(backup_path):
            print(f"❌ ERROR: Backup file not created!")
            return False
        
        source_size = os.path.getsize(source_db)
        backup_size = os.path.getsize(backup_path)
        
        if backup_size == 0:
            print(f"❌ ERROR: Backup file is empty!")
            os.remove(backup_path)
            return False
        
        print(f"✅ Backup created successfully!")
        print(f"   Source size: {source_size:,} bytes")
        print(f"   Backup size: {backup_size:,} bytes")
        print(f"   Path: {backup_path}")
        
        # Checkpoint WAL after successful backup
        try:
            conn = sqlite3.connect(source_db)
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            conn.close()
            print(f"✅ WAL checkpoint completed")
        except Exception as e:
            print(f"⚠️  WAL checkpoint failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Backup failed: {e}")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return False


def backup_progress(status, remaining, total):
    """Callback for backup progress (optional)."""
    if total > 0:
        percent = ((total - remaining) / total) * 100
        if percent % 25 == 0:  # Print every 25%
            print(f"   Progress: {percent:.0f}%")


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE BACKUP UTILITY (WAL-SAFE)")
    print("=" * 60)
    print()
    
    success = backup_database_wal_safe()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ BACKUP COMPLETED")
        print("Safe to proceed with maintenance/migration.")
        sys.exit(0)
    else:
        print("❌ BACKUP FAILED")
        print("DO NOT proceed until backup is successful!")
        sys.exit(1)

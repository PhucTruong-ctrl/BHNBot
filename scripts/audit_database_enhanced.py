#!/usr/bin/env python3
"""Enhanced Database Schema Audit Script

Improved version with:
- Better column name matching (handles variations)
- SQL query parsing
- Schema definition checking
- Detailed usage reports
"""
import sqlite3
import os
import re
from pathlib import Path
from collections import defaultdict

DB_PATH = "./data/database.db"
CODEBASE_ROOT = "."

def get_all_tables_and_columns(db_path):
    """Extract all tables and their columns from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        schema[table] = columns
    
    conn.close()
    return schema

def search_column_usage(column_name, table_name, search_dirs):
    """Enhanced search for column usage.
    
    Searches for:
    - Direct column name in quotes
    - Column in SQL queries
    - Column in dictionary keys
    - Column in schema definitions
    """
    matches = defaultdict(list)
    
    # Search patterns
    patterns = [
        rf'["\']?{re.escape(column_name)}["\']?',  # Basic name
        rf'SELECT.*{re.escape(column_name)}',  # SELECT queries
        rf'INSERT.*{re.escape(column_name)}',  # INSERT queries
        rf'UPDATE.*{re.escape(column_name)}',  # UPDATE queries
        rf'{re.escape(column_name)}\s*=',  # Assignments
        rf'get\(["\']?{re.escape(column_name)}["\']?\)',  # Dict get
    ]
    
    for search_dir in search_dirs:
        for py_file in Path(search_dir).rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                matches[str(py_file)].append((line_num, line.strip()))
                                break
            except Exception:
                pass
    
    return dict(matches)

def manual_verify_column(table_name, column_name):
    """Manual verification for known cases."""
    # Known unused columns (from previous session/migrations)
    known_unused = {
        'server_config': ['wolf_channel_id', 'giveaway_channel_id'],
        'fishing_profiles': ['quest_thuong_luong', 'quest_ca_ngan_ha', 
                            'quest_ca_phuong_hoang', 'quest_cthulhu_con', 
                            'quest_ca_voi_52hz'],
    }
    
    # Columns we just removed
    recently_removed = {
        'server_config': ['bump_ping_roles'],  # Removed in recent refactor
    }
    
    # Check known lists
    if table_name in known_unused and column_name in known_unused[table_name]:
        return "CONFIRMED_UNUSED (migrated to new system)"
    
    if table_name in recently_removed and column_name in recently_removed[table_name]:
        return "CONFIRMED_UNUSED (feature removed)"
    
    return None

def analyze_schema_detailed():
    """Detailed schema analysis with enhanced detection."""
    print("=" * 80)
    print("ENHANCED DATABASE SCHEMA AUDIT")
    print("=" * 80)
    print()
    
    schema = get_all_tables_and_columns(DB_PATH)
    
    print(f"Analyzing {len(schema)} tables...")
    print()
    
    search_dirs = ["./cogs", "./database_manager.py", "./setup_data.py", "./scripts", "./main.py"]
    
    report = {}
    
    for table, columns in schema.items():
        print(f"\n{'=' * 80}")
        print(f"Table: {table}")
        print('=' * 80)
        
        table_report = {'used': [], 'unused': [], 'suspicious': []}
        
        for column in columns:
            # Skip primary/foreign keys
            if column in ["id", "user_id", "guild_id"]:
                table_report['used'].append((column, "PRIMARY/FOREIGN KEY"))
                continue
            
            # Manual verification first
            manual_check = manual_verify_column(table, column)
            if manual_check:
                table_report['unused'].append((column, manual_check))
                print(f"  ❌ {column}: {manual_check}")
                continue
            
            # Enhanced search
            matches = search_column_usage(column, table, search_dirs)
            
            if not matches:
                table_report['suspicious'].append((column, "NO MATCHES FOUND"))
                print(f"  ⚠️  {column}: NO MATCHES (needs manual review)")
            elif len(matches) == 1 and 'setup_data.py' in list(matches.keys())[0]:
                # Only found in schema definition
                table_report['suspicious'].append((column, "ONLY IN SCHEMA"))
                print(f"  ⚠️  {column}: Only in setup_data.py (may be unused)")
            else:
                usage_count = sum(len(v) for v in matches.values())
                files_count = len(matches)
                table_report['used'].append((column, f"{usage_count} usages in {files_count} files"))
                print(f"  ✅ {column}: {usage_count} usages in {files_count} files")
        
        report[table] = table_report
    
    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    print()
    
    confirmed_unused = []
    needs_review = []
    
    for table, data in report.items():
        if data['unused']:
            print(f"\n❌ {table} - CONFIRMED UNUSED:")
            for col, reason in data['unused']:
                print(f"   - {col}: {reason}")
                confirmed_unused.append((table, col))
        
        if data['suspicious']:
            print(f"\n⚠️  {table} - NEEDS MANUAL REVIEW:")
            for col, reason in data['suspicious']:
                print(f"   - {col}: {reason}")
                needs_review.append((table, col))
    
    print("\n" + "=" * 80)
    print(f"CONFIRMED UNUSED: {len(confirmed_unused)} columns")
    print(f"NEEDS REVIEW: {len(needs_review)} columns")
    print("=" * 80)
    
    # Generate migration SQL
    if confirmed_unused:
        print("\n" + "=" * 80)
        print("MIGRATION SQL (CONFIRMED UNUSED ONLY)")
        print("=" * 80)
        print()
        for table, column in confirmed_unused:
            print(f"-- ALTER TABLE {table} DROP COLUMN {column};")
        print()

if __name__ == "__main__":
    analyze_schema_detailed()

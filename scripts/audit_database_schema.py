#!/usr/bin/env python3
"""Database Schema Audit Script

Analyzes database.db to find unused columns by:
1. Extracting all tables and columns
2. Comparing with setup_data.py schema definitions
3. Searching codebase for column usage
4. Generating cleanup report
"""
import sqlite3
import os
import re
from pathlib import Path

DB_PATH = "./data/database.db"
CODEBASE_ROOT = "."

def get_all_tables_and_columns(db_path):
    """Extract all tables and their columns from database.
    
    Returns:
        dict: {table_name: [column_names]}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]  # row[1] is column name
        schema[table] = columns
    
    conn.close()
    return schema

def search_codebase_for_usage(column_name, search_dirs):
    """Search codebase for column name usage.
    
    Args:
        column_name (str): Column name to search
        search_dirs (list): Directories to search
        
    Returns:
        list: List of (file, line_number, line_content) tuples
    """
    matches = []
    
    for search_dir in search_dirs:
        for py_file in Path(search_dir).rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        # Search for column name in quotes or as identifier
                        if re.search(rf'["\']?{re.escape(column_name)}["\']?', line):
                            matches.append((str(py_file), line_num, line.strip()))
            except Exception as e:
                pass  # Skip files that can't be read
    
    return matches

def analyze_schema():
    """Main analysis function."""
    print("=" * 80)
    print("DATABASE SCHEMA AUDIT")
    print("=" * 80)
    print()
    
    # Get current schema
    print(f"[1/3] Extracting schema from {DB_PATH}...")
    schema = get_all_tables_and_columns(DB_PATH)
    
    print(f"Found {len(schema)} tables:")
    for table, columns in schema.items():
        print(f"  - {table}: {len(columns)} columns")
    print()
    
    # Analyze each table
    print("[2/3] Analyzing column usage in codebase...")
    search_dirs = ["./cogs", "./database_manager.py", "./setup_data.py", "./scripts"]
    
    unused_columns = {}
    
    for table, columns in schema.items():
        print(f"\nTable: {table}")
        print("-" * 40)
        
        table_unused = []
        
        for column in columns:
            # Skip primary keys and common columns
            if column in ["id", "user_id", "guild_id"]:
                continue
            
            # Search for usage
            matches = search_codebase_for_usage(column, search_dirs)
            
            if not matches:
                print(f"  ❌ {column}: NOT FOUND in codebase")
                table_unused.append(column)
            else:
                print(f"  ✅ {column}: {len(matches)} usage(s)")
        
        if table_unused:
            unused_columns[table] = table_unused
    
    # Generate report
    print()
    print("=" * 80)
    print("[3/3] CLEANUP REPORT")
    print("=" * 80)
    print()
    
    if not unused_columns:
        print("✅ No unused columns found! Database is clean.")
    else:
        print("⚠️  Found potentially unused columns:")
        print()
        
        for table, columns in unused_columns.items():
            print(f"Table: {table}")
            for column in columns:
                print(f"  - {column}")
            print()
        
        # Generate DROP statements
        print("=" * 80)
        print("SUGGESTED MIGRATION SQL")
        print("=" * 80)
        print()
        print("-- WARNING: Review carefully before executing!")
        print("-- SQLite doesn't support DROP COLUMN directly in old versions")
        print("-- You may need to recreate tables")
        print()
        
        for table, columns in unused_columns.items():
            for column in columns:
                print(f"-- ALTER TABLE {table} DROP COLUMN {column};")
        print()
    
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    analyze_schema()

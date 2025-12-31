#!/usr/bin/env python3
"""
Script to fix remaining SQLite syntax in codebase.
Replaces INSERT OR IGNORE and INSERT OR REPLACE with PostgreSQL equivalents.
"""

import re
import os
import glob

def fix_sql_syntax_in_file(filepath):
    """Fix SQL syntax in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modifications = []
        
        # Pattern 1: INSERT OR IGNORE INTO table_name (cols) VALUES (vals)
        # Convert to: INSERT INTO table_name (cols) VALUES (vals) ON CONFLICT DO NOTHING
        pattern1 = r'INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)\s+\(([^)]+)\)\s+VALUES\s+\(([^)]+)\)'
        matches = list(re.finditer(pattern1, content, re.IGNORECASE))
       
        for match in reversed(matches):  # Reverse to maintain positions
            table = match.group(1)
            cols = match.group(2)
            vals = match.group(3)
            
            # Try to infer conflict column (usually first column or user_id)
            column_list = [c.strip() for c in cols.split(',')]
            # Common conflict columns
            conflict_col = None
            if len(column_list) >= 2:
                # Assume the first two columns form the unique constraint
                conflict_col = f"({column_list[0]}, {column_list[1]})"
            elif len(column_list) == 1:
                conflict_col = f"({column_list[0]})"
            
            if conflict_col:
                replacement = f"INSERT INTO {table} ({cols}) VALUES ({vals}) ON CONFLICT {conflict_col} DO NOTHING"
            else:
                replacement = f"INSERT INTO {table} ({cols}) VALUES ({vals}) ON CONFLICT DO NOTHING"
            
            content = content[:match.start()] + replacement + content[match.end():]
            modifications.append(f"  - Line {content[:match.start()].count(chr(10))+1}: INSERT OR IGNORE -> ON CONFLICT DO NOTHING")
        
        # Only write if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return len(modifications), modifications
        
        return 0, []
    
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0, []

def main():
    # Scan all Python files in the project
    search_paths = [
        "/home/phuctruong/BHNBot/core/**/*.py",
        "/home/phuctruong/BHNBot/cogs/**/*.py",
    ]
    
    total_files_fixed = 0
    total_modifications = 0
    
    for pattern in search_paths:
        for filepath in glob.glob(pattern, recursive=True):
            modifications_count, modifications = fix_sql_syntax_in_file(filepath)
            if modifications_count > 0:
                total_files_fixed += 1
                total_modifications += modifications_count
                print(f"\nFixed {filepath}:")
                for mod in modifications:
                    print(mod)
    
    print(f"\n=== SUMMARY ===")
    print(f"Files fixed: {total_files_fixed}")
    print(f"Total modifications: {total_modifications}")

if __name__ == "__main__":
    main()

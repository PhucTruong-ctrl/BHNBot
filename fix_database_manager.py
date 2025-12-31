#!/usr/bin/env python3
"""
Script to fix database_manager.py caching issues for PostgreSQL migration.

Changes:
1. Remove use_cache, cache_key, cache_ttl parameters from db_manager calls
2. Remove db_manager.clear_cache_by_prefix() calls
3. Change db_manager.execute() to db_manager.fetchall() for SELECT queries
"""

import re

def fix_database_manager():
    filepath ="/home/phuctruong/BHNBot/database_manager.py"
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    skip_next = 0
    
    for i, line in enumerate(lines):
        # Skip lines that are part of caching parameters
        if skip_next > 0:
            skip_next -= 1
            continue
            
        # Skip clear_cache_by_prefix lines
        if 'db_manager.clear_cache_by_prefix' in line:
            continue
            
        # Check if this line has use_cache parameter
        if 'use_cache=True' in line:
            # Count how many lines to skip (cache_key and cache_ttl lines)
            j = i + 1
            while j < len(lines) and ('cache_key=' in lines[j] or 'cache_ttl=' in lines[j]):
                skip_next += 1
                j += 1
            continue
            
        # Fix execute() calls with SELECT to fetchall()
        if 'await db_manager.execute(' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            if '"SELECT' in next_line or "'SELECT" in next_line or 'SELECT' in line:
                line = line.replace('db_manager.execute(', 'db_manager.fetchall(')
        
        # Remove trailing commas before closing parenthesis (from removed cache params)
        line = re.sub(r',(\s*)\)', r'\1)', line)
        
        fixed_lines.append(line)
    
    with open(filepath, 'w') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed database_manager.py")
    print(f"Original lines: {len(lines)}")
    print(f"Fixed lines: {len(fixed_lines)}")
    print(f"Removed: {len(lines) - len(fixed_lines)} lines")

if __name__ == "__main__":
    fix_database_manager()

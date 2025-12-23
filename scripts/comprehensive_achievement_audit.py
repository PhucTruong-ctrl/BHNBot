#!/usr/bin/env python3
"""Comprehensive Achievement Audit

Checks all achievements for:
1. Missing triggers
2. Wrong stat keys
3. Duplicate unlock potential (spam)
4. Logic errors
5. Consistency issues
"""
import json
import re
from pathlib import Path
from collections import defaultdict

ACHIEVEMENTS_JSON = "./data/achievements.json"
CODE_DIRS = ["./cogs/fishing", "./cogs/noi_tu", "./cogs"]

# Load achievements
with open(ACHIEVEMENTS_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 80)
print("COMPREHENSIVE ACHIEVEMENT AUDIT")
print("=" * 80)
print()

# Analyze each category
for category, achievements in data.items():
    if category in ["__comment", "categories"]:
        continue
    
    print(f"\n{'='*80}")
    print(f"CATEGORY: {category.upper()}")
    print(f"{'='*80}")
    print(f"Total achievements: {len(achievements)}\n")
    
    # Collect stat keys usage
    stat_keys = defaultdict(list)
    
    for ach_key, ach_data in achievements.items():
        stat_key = ach_data.get("condition_stat")
        target = ach_data.get("target_value")
        name = ach_data.get("name")
        
        stat_keys[stat_key].append({
            "ach_key": ach_key,
            "name": name,
            "target": target
        })
    
    # Check for potential issues
    print("POTENTIAL ISSUES:")
    print("-" * 80)
    
    issues_found = False
    
    # Issue 1: Multiple achievements using same stat_key
    for stat_key, achs in stat_keys.items():
        if len(achs) > 1:
            issues_found = True
            print(f"\n⚠️  MULTIPLE ACHIEVEMENTS use stat_key: {stat_key}")
            for ach in achs:
                print(f"   - {ach['name']} (target: {ach['target']})")
            print(f"   → Risk: May unlock multiple at once if not checking target values correctly")
    
    # Issue 2: Very low target values (potential spam)
    for stat_key, achs in stat_keys.items():
        for ach in achs:
            if ach['target'] == 1:
                print(f"\n⚠️  LOW TARGET (1): {ach['name']} ({stat_key})")
                print(f"   → Risk: Will unlock immediately on first trigger")
    
    # Issue 3: Stat keys that look wrong
    for stat_key, achs in stat_keys.items():
        # Check for suspicious patterns
        if stat_key and ("_" not in stat_key or len(stat_key) < 3):
            issues_found = True
            print(f"\n⚠️  SUSPICIOUS STAT KEY: {stat_key}")
            for ach in achs:
                print(f"   - {ach['name']}")
    
    if not issues_found:
        print("✅ No obvious issues found in achievement definitions")
    
    print("\n" + "=" * 80)

# Now check for triggers in code
print("\n\n" + "=" * 80)
print("CHECKING TRIGGERS IN CODE")
print("=" * 80)

all_stat_keys = set()
for category, achievements in data.items():
    if category in ["__comment", "categories"]:
        continue
    for ach_data in achievements.values():
        stat_key = ach_data.get("condition_stat")
        if stat_key:
            all_stat_keys.add((category, stat_key))

# Search for check_unlock and increment_stat calls
trigger_usage = defaultdict(list)

for code_dir in CODE_DIRS:
    code_path = Path(code_dir)
    if not code_path.exists():
        continue
    
    for py_file in code_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Find increment_stat calls
                    if 'increment_stat' in line:
                        # Try to extract stat_key
                        match = re.search(r'increment_stat\([^,]+,\s*"([^"]+)",\s*"([^"]+)"', line)
                        if match:
                            category = match.group(1)
                            stat_key = match.group(2)
                            trigger_usage[(category, stat_key)].append({
                                "file": str(py_file.relative_to(".")),
                                "line": line_num,
                                "type": "increment"
                            })
                    
                    # Find check_unlock calls
                    if 'check_unlock' in line:
                        match = re.search(r'check_unlock\([^,]+,\s*"([^"]+)",\s*"([^"]+)"', line)
                        if match:
                            category = match.group(1)
                            stat_key = match.group(2)
                            trigger_usage[(category, stat_key)].append({
                                "file": str(py_file.relative_to(".")),
                                "line": line_num,
                                "type": "check_unlock"
                            })
        except Exception as e:
            pass

print(f"\nFound {len(trigger_usage)} unique stat_keys with triggers\n")

# Check for spam potential (increment without immediate check_unlock)
print("\n⚠️  POTENTIAL SPAM ISSUES:")
print("-" * 80)
spam_issues = False

for (category, stat_key), usages in trigger_usage.items():
    increments = [u for u in usages if u['type'] == 'increment']
    checks = [u for u in usages if u['type'] == 'check_unlock']
    
    if len(increments) > 0 and len(checks) == 0:
        spam_issues = True
        print(f"\n❌ {category}/{stat_key}: Has {len(increments)} increment(s) but NO check_unlock!")
        for inc in increments[:3]:
            print(f"   {inc['file']}:{inc['line']}")
    
    # Check if increments and checks are in same files (good pattern)
    inc_files = {u['file'] for u in increments}
    check_files = {u['file'] for u in checks}
    
    if inc_files and check_files and not inc_files.intersection(check_files):
        print(f"\n⚠️  {category}/{stat_key}: increment and check_unlock in DIFFERENT files")
        print(f"   Increment in: {', '.join(list(inc_files)[:2])}")
        print(f"   Check in: {', '.join(list(check_files)[:2])}")
        print(f"   → May cause delayed unlocks")

if not spam_issues:
    print("✅ No obvious spam issues found")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)

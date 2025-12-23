#!/usr/bin/env python3
"""Fishing Achievement Trigger Audit

Checks if all fishing achievements have proper triggers in code.
Compares achievements.json definitions with actual check_unlock calls.
"""
import json
import re
from pathlib import Path

ACHIEVEMENTS_JSON = "./data/achievements.json"
FISHING_CODE_DIR = "./cogs/fishing"

# Load achievements
with open(ACHIEVEMENTS_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

fishing_achievements = data.get("fishing", {})

print("=" * 80)
print("FISHING ACHIEVEMENT TRIGGER AUDIT")
print("=" * 80)
print()

print(f"Total Fishing Achievements: {len(fishing_achievements)}")
print()

# Collect all stat_keys from achievements
achievement_stats = {}
for ach_key, ach_data in fishing_achievements.items():
    stat_key = ach_data.get("condition_stat")
    name = ach_data.get("name")
    target = ach_data.get("target_value")
    achievement_stats[stat_key] = {
        "achievement_key": ach_key,
        "name": name,
        "target": target,
        "found_triggers": []
    }

print("Achievements by stat_key:")
for stat_key, info in achievement_stats.items():
    print(f"  - {stat_key}: {info['name']} (target: {info['target']})")
print()

# Search for check_unlock calls in fishing code
print("=" * 80)
print("Searching for triggers in code...")
print("=" * 80)
print()

for py_file in Path(FISHING_CODE_DIR).rglob("*.py"):
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if 'check_unlock' in line and 'fishing' in line:
                # Extract stat_key from check_unlock call
                # Pattern: check_unlock(user_id, "fishing", "stat_key", value, channel)
                match = re.search(r'check_unlock\([^,]+,\s*"fishing",\s*"([^"]+)"', line)
                if match:
                    stat_key = match.group(1)
                    if stat_key in achievement_stats:
                        achievement_stats[stat_key]["found_triggers"].append({
                            "file": str(py_file.relative_to(".")),
                            "line": line_num,
                            "code": line.strip()
                        })

# Analysis
print("=" * 80)
print("AUDIT RESULTS")
print("=" * 80)
print()

missing_triggers = []
found_triggers = []

for stat_key, info in achievement_stats.items():
    if not info["found_triggers"]:
        missing_triggers.append((stat_key, info))
    else:
        found_triggers.append((stat_key, info))

# Report found triggers
print(f"✅ Achievements WITH triggers: {len(found_triggers)}")
for stat_key, info in found_triggers:
    print(f"\n  {stat_key} ({info['name']})")
    for trigger in info["found_triggers"]:
        print(f"    → {trigger['file']}:{trigger['line']}")

# Report missing triggers
print()
print(f"❌ Achievements WITHOUT triggers: {len(missing_triggers)}")
if missing_triggers:
    for stat_key, info in missing_triggers:
        print(f"\n  {stat_key} ({info['name']})")
        print(f"    Achievement key: {info['achievement_key']}")
        print(f"    Target value: {info['target']}")
        print(f"    ⚠️  NO TRIGGER FOUND IN CODE!")

print()
print("=" * 80)
print(f"Summary: {len(found_triggers)}/{len(achievement_stats)} achievements have triggers")
print("=" * 80)

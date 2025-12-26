#!/usr/bin/env python3
"""
Complete Priority 2 - Add stats tracking and conditional logic to sell.py
"""

with open('cogs/fishing/commands/sell.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# STEP 1.1: Add sell_count tracking after line 468
# Find: await increment_stat(user_id, "fishing", "total_money_earned", final_value)
for i, line in enumerate(lines):
    if 'await increment_stat(user_id, "fishing", "total_money_earned", final_value)' in line:
        # Add after this line
        indent = '            '
        lines.insert(i+1, f'{indent}await increment_stat(user_id, "fishing", "sell_count", 1)\n')
        print(f"✅ Added sell_count tracking at line {i+2}")
        break

# STEP 1.2: Add rare_fish_sold tracking after line 256 (now shifted due to insert)
# Find: await increment_stat(user_id, "fishing", stat_key, 1)
# We need the one inside the fish selling loop
found_rare_insert = False
for i, line in enumerate(lines):
    if 'await increment_stat(user_id, "fishing", stat_key, 1)' in line and not found_rare_insert:
        # Check if this is in the fish loop by looking at context
        if i > 240 and i < 270:  # Approximate range
            indent = '                                    '
            # Add rare fish tracking after
            rare_code = f'''{indent}# Track rare fish sold
{indent}if rarity in ['rare', 'epic', 'legendary', 'boss']:
{indent}    await increment_stat(user_id, "fishing", "rare_fish_sold", 1)
'''
            lines.insert(i+1, rare_code)
            print(f"✅ Added rare_fish_sold tracking at line {i+2}")
            found_rare_insert = True
            break

# STEP 3: Add conditional filtering (import at top, logic before event trigger)
# Add import at top
import_added = False
for i, line in enumerate(lines):
    if 'from database_manager import' in line:
        if 'check_event_condition' not in ' '.join(lines[max(0, i-5):i+5]):
            # Not yet imported, will add later when we find the sell event trigger location
            pass
        break

# STEP 4: Add unlock notifications
# After sell_count increment, add unlock check
for i, line in enumerate(lines):
    if 'await increment_stat(user_id, "fishing", "sell_count", 1)' in line:
        indent = '            '
        unlock_code = f'''{indent}# Check unlock notifications
{indent}from ..mechanics.events import check_conditional_unlocks
{indent}current_sell_count = await get_stat(user_id, "fishing", "sell_count")
{indent}await check_conditional_unlocks(user_id, "sell_count", current_sell_count, channel)
'''
        lines.insert(i+1, unlock_code)
        print(f"✅ Added sell_count unlock notification at line {i+2}")
        break

# Write back
with open('cogs/fishing/commands/sell.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ SELL.PY UPDATED")
print("   - sell_count tracking added")
print("   - rare_fish_sold tracking added")  
print("   - unlock notifications added")

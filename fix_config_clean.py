#!/usr/bin/env python3
with open('cogs/config.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove line 512 (reset_timer in describe)
del lines[511]

# Fix function signature - now line 513
lines[513] = lines[513].replace(', reset_timer: bool = False', '')

# Delete reset_timer block (lines 526-540)
del lines[526:541]

# Insert corrected line at 526
lines[526] = '                if channel is None:\n'

with open('cogs/config.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Config cleaned!")

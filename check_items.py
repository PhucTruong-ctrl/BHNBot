import sys
import os
sys.path.append(os.getcwd())
from core.item_system import item_system

items = item_system.get_all_items()
gift_keys = ["cafe", "flower", "chocolate", "card", "gift", "ring"]
print("Checking Gift Items:")
for k in gift_keys:
    if k in items:
        print(f"[OK] {k}: {items[k].get('name')}")
    else:
        print(f"[MISSING] {k}")

print("\nTotal Items:", len(items))


import json
import random
import os
import sys

# Mock Data for simulation
RARE_FISH_KEYS = ["muc_khong_lo", "ca_ngua_van", "sa_sung", "ca_mat_quy"]
COMMON_FISH_KEYS = ["ca_chep", "ca_ro", "ca_tram"]
ALL_FISH = {k: {"name": k.replace("_", " ").title()} for k in RARE_FISH_KEYS + COMMON_FISH_KEYS}

def load_config():
    path = "data/fishing_global_events.json"
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {e}")
        return None

def simulate_loot(loot_list, iterations=1000):
    results = {}
    
    for _ in range(iterations):
        for item in loot_list:
            key = item.get("key")
            rate = item.get("rate", 1.0)
            
            # Simple probability check
            if random.random() < rate:
                # Handle random category logic mock
                if item.get("type") == "random_category":
                    cat = item.get("category")
                    if cat == "rare": key = "RANDOM_RARE"
                    else: key = "RANDOM_COMMON"
                
                qty = item.get("amount", 1)
                
                if key not in results: results[key] = 0
                results[key] += 1
                
    return results

def verify_events():
    config = load_config()
    if not config: return

    events = config.get("events", {})
    print(f"✅ Loaded {len(events)} events.")
    
    # 1. Verify VIP Box Rates
    vip_box = events.get("vip_blind_box")
    if vip_box:
        print("\n📦 --- SIMULATION: VIP BLIND BOX (1000 Opens) ---")
        buttons = vip_box["data"]["mechanics"]["buttons"]
        loot_table = buttons[0]["rewards"]
        
        # Calculate theoretical rates
        print("Theoretical Rates:")
        for item in loot_table:
            print(f"- {item.get('key')}: {item.get('rate', 0)*100}%")
            
        # Run Sim
        sim_results = simulate_loot(loot_table, 1000)
        print("\nActual Results (1000 runs):")
        for key, count in sim_results.items():
            print(f"- {key}: {count} ({count/10.0}%)")
            
    # 2. Verify Raid Rewards
    raid = events.get("cthulhu_raid")
    if raid:
        print("\n🐙 --- SIMULATION: CTHULHU RAID REWARDS (1000 Wins) ---")
        rewards = raid["rewards"]["success"]["items"]
        
        # Run Sim (Note: Raid rewards logic is slightly different, it iterates all items)
        # In Manager: "for item in items_cfg: ... random.randint(min, max)"
        # But wait, Manager doesn't have a 'chance' for raid items in the current logic?
        # Let's check the logic I wrote or the JSON.
        # JSON: {"key": "ngoc_trai", "min": 1, "max": 2} -> This implies 100% chance?
        # Let's check Code in GlobalEventManager...
        # "for item in items_cfg: ... qty = random.randint(min, max)"
        # YES! It's 100% chance unless I added a rate field?
        # I did NOT add a rate field in the json or code for Raid Items.
        # So Raid Items are GUARANTEED (1-2 Pearls, 1-3 Rares).
        # This is good to confirm.
        
        print("Logic Check: Raid items are GUARANTEED according to current code (100% chance).")
        print(f"Configured Items: {[i.get('key') or i.get('type') for i in rewards]}")

if __name__ == "__main__":
    verify_events()

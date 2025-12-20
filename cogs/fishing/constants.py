"""Game constants and data tables for fishing system"""

import json
import os
from configs.settings import (
    DB_PATH, DB_TIMEOUT, FISHING_DATA_PATH, LEGENDARY_FISH_PATH,
    FISHING_EVENTS_PATH, SELL_EVENTS_PATH, NPC_EVENTS_PATH,
    FISHING_ACHIEVEMENTS_PATH, FISHING_ITEMS_PATH, DISASTER_EVENTS_PATH,
    WORM_COST, FISH_BUCKET_LIMIT, NPC_ENCOUNTER_CHANCE, NPC_ENCOUNTER_DELAY,
    SNAKE_BITE_PENALTY_PERCENT, GLOBAL_DISASTER_COOLDOWN,
    LOOT_TABLE_NORMAL, LOOT_TABLE_BOOST, LOOT_TABLE_NO_WORM,
    CATCH_COUNT_WEIGHTS, TREE_NAMES, ROD_LEVELS
)

# NOTE: Database connections are now managed centrally through core.database
# This prevents connection leaks and provides proper connection pooling

# ==================== LOAD FISH DATA FROM JSON ====================
def load_fishing_data():
    """Load common + rare fish data from JSON file. Falls back to empty dict if not found."""
    if os.path.exists(FISHING_DATA_PATH):
        try:
            with open(FISHING_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("fishing_data", {})
        except Exception as e:
            print(f"[WARNING] Failed to load common/rare fish from JSON: {e}")
            return {}
    else:
        print(f"[WARNING] {FISHING_DATA_PATH} not found.")
        return {}

def load_legendary_fish_data():
    """Load legendary fish data from JSON file. Falls back to empty dict if not found."""
    if os.path.exists(LEGENDARY_FISH_PATH):
        try:
            with open(LEGENDARY_FISH_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("legendary_data", {})
        except Exception as e:
            print(f"[WARNING] Failed to load legendary fish from JSON: {e}")
            return {}
    else:
        print(f"[WARNING] {LEGENDARY_FISH_PATH} not found.")
        return {}

# Load data once at import time
_fishing_data = load_fishing_data()
_legendary_data = load_legendary_fish_data()

FISHING_DATA = _fishing_data.get("fish", [])
LEGENDARY_FISH_DATA = _legendary_data.get("fish", [])

# Build lookup dicts by category
ALL_FISH = {}
COMMON_FISH = []
RARE_FISH = []
LEGENDARY_FISH = []
COMMON_FISH_KEYS = []
RARE_FISH_KEYS = []
LEGENDARY_FISH_KEYS = []

# Load common and rare fish
if FISHING_DATA:
    for fish in FISHING_DATA:
        key = fish["key"]
        category = fish.get("category", "common")
        ALL_FISH[key] = fish
        
        # Categorize fish
        if category == "common":
            COMMON_FISH.append(fish)
            COMMON_FISH_KEYS.append(key)
        elif category == "rare":
            RARE_FISH.append(fish)
            RARE_FISH_KEYS.append(key)
else:
    print("[WARNING] No common/rare fish data loaded!")

# Load legendary fish
if LEGENDARY_FISH_DATA:
    for fish in LEGENDARY_FISH_DATA:
        key = fish["key"]
        ALL_FISH[key] = fish
        LEGENDARY_FISH.append(fish)
        LEGENDARY_FISH_KEYS.append(key)
else:
    print("[WARNING] No legendary fish data loaded!")

if not FISHING_DATA and not LEGENDARY_FISH_DATA:
    print("[ERROR] No fish data loaded! Game will not work properly.")

if not FISHING_DATA and not LEGENDARY_FISH_DATA:
    print("[ERROR] No fish data loaded! Game will not work properly.")

# ==================== SPECIAL ITEMS (Added to ALL_FISH after loading) ====================
# Add special items that aren't in JSON
ALL_FISH["pearl"] = {"key": "pearl", "name": "Ngọc Trai", "emoji": "🔮", "sell_price": 150}
ALL_FISH["rod_material"] = {"key": "rod_material", "name": "Vật Liệu Nâng Cấp Cần", "emoji": "⚙️", "sell_price": 0}

# Chest loot (will be populated after TRASH_ITEMS is defined)
CHEST_LOOT = {
    "nothing": 15,  # 15% chance to get nothing
    "fertilizer": 20,
    "puzzle_piece": 12,
    "coin_pouch": 15,
    "gift_random": 20,
    "manh_sao_bang": 8,  # Mảnh Sao Băng
    "manh_ban_do_a": 3,  # Mảnh Bản Đồ A
    "manh_ban_do_b": 3,  # Mảnh Bản Đồ B
    "manh_ban_do_c": 3,  # Mảnh Bản Đồ C
    "manh_ban_do_d": 3,
    # Trash items from fishing (2% each = 60 total, so ~1% each)
}

FISHING_EVENTS_PATH = "./data/fishing_events.json"
SELL_EVENTS_PATH = "./data/sell_events.json"
NPC_EVENTS_PATH = "./data/npc_events.json"
FISHING_ACHIEVEMENTS_PATH = "./data/fishing_achievements.json"
FISHING_ITEMS_PATH = "./data/fishing_items.json"
DISASTER_EVENTS_PATH = "./data/disaster_events.json"


def load_json_config(path: str, default):
    """Load JSON config from disk with graceful fallback."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load {path}: {e}")
    else:
        print(f"[WARNING] {path} not found.")
    return default


# ==================== LOAD ALL ITEMS FROM JSON ====================
_all_items_data = load_json_config(FISHING_ITEMS_PATH, {"items": {}})
ALL_ITEMS_DATA = _all_items_data.get("items", {})

# Filter items by type for backward compatibility
TRASH_ITEMS = [v for v in ALL_ITEMS_DATA.values() if v.get("type") == "trash"]
LEGENDARY_ITEMS = [v for v in ALL_ITEMS_DATA.values() if v.get("type") == "legendary_component"]
GIFT_ITEMS = [v.get("key") for v in ALL_ITEMS_DATA.values() if v.get("type") == "gift"]

# NOW populate CHEST_LOOT with trash items (after TRASH_ITEMS is defined)
for trash_item in TRASH_ITEMS:
    CHEST_LOOT[trash_item.get("key", f"trash_{trash_item}")] = 2


# Achievements (fishing-specific)
ACHIEVEMENTS = load_json_config(FISHING_ACHIEVEMENTS_PATH, {})


# Fishing random events
_fishing_events_data = load_json_config(FISHING_EVENTS_PATH, {"events": {}, "messages": {}})
RANDOM_EVENTS = _fishing_events_data.get("events", {})
RANDOM_EVENT_MESSAGES = _fishing_events_data.get("messages", {})


# Sell events
_sell_events_data = load_json_config(SELL_EVENTS_PATH, {"events": {}, "messages": {}})
SELL_EVENTS = _sell_events_data.get("events", {})
SELL_MESSAGES = _sell_events_data.get("messages", {})


# NPC encounters
NPC_ENCOUNTERS = load_json_config(NPC_EVENTS_PATH, {})


# Disaster events (Server-wide calamities)
_disaster_events_data = load_json_config(DISASTER_EVENTS_PATH, {"disasters": []})
DISASTER_EVENTS = _disaster_events_data.get("disasters", [])
GLOBAL_DISASTER_COOLDOWN = _disaster_events_data.get("global_cooldown", 3600)

# Achievement stat mappings for events
SELL_EVENT_STAT_MAPPING = {
    "maybach_crash": "luxury_car_crashes",
    "bugatti_crash": "luxury_car_crashes", 
    "ferrari_crash": "luxury_car_crashes",
    "vinfast_crash": "luxury_car_crashes",
    "crypto_loss": "crypto_fails",
    "scam": "crypto_fails",
    "market_crash": "crypto_fails",
    "shark_tank": "shark_tank_event",
    "land_fever": "land_fever_event",
    "drama": "drama_events",
    "tiktok_drama": "drama_events",
    "check_var": "drama_events",
    "phat": "drama_events",
    "fake_money": "scam_events",
    "broken_scale": "scam_events",
    "pickpocket": "scam_events",
    "gangster_fee": "scam_events",
    "scammer": "scam_events",
    "thief_run": "scam_events",
    "hole_in_bag": "scam_events",
    "cat_steal_sell": "scam_events",
    "stray_dog": "scam_events",
    "parking_fee": "scam_events",
    "plastic_bag_fee": "scam_events",
    "rent_increase": "scam_events",
    "sanitation_fine": "scam_events",
    "tax_collector": "scam_events",
    "market_management": "scam_events",
    "maybach_crash": "scam_events",
    "bugatti_crash": "scam_events",
    "ferrari_crash": "scam_events",
    "vinfast_crash": "scam_events",
}

FISHING_EVENT_STAT_MAPPING = {
    "truck_isekai": "isekai_event",
    "global_reset": "global_reset_triggered",
    "time_reset": "global_reset_triggered",
    "space_portal": "global_reset_triggered",
    "broken_hourglass": "global_reset_triggered",
}

NPC_EVENT_STAT_MAPPING = {
    "ninja_lead": "ninja_lead_encounter",
}

DISASTER_STAT_MAPPING = {
    "hacker_attack": "disaster_triggered",
    "earthquake": "disaster_triggered",
    "tsunami": "disaster_triggered",
    "volcano_eruption": "disaster_triggered",
    "meteor_shower": "disaster_triggered",
    "alien_invasion": "disaster_triggered",
}

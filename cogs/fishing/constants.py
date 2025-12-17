"""Game constants and data tables for fishing system"""

import json
import os

DB_PATH = "./data/database.db"
FISHING_DATA_PATH = "./data/fishing_data.json"
LEGENDARY_FISH_PATH = "./data/legendaryFish_data.json"

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

# Loot tables
LOOT_TABLE_NORMAL = {
    "trash": 30, "common_fish": 60, "rare_fish": 5, "chest": 5
}

LOOT_TABLE_BOOST = {
    "trash": 15, "common_fish": 75, "rare_fish": 5, "chest": 5
}

LOOT_TABLE_NO_WORM = {
    "trash": 50, "common_fish": 49, "rare_fish": 1, "chest": 0
}

CATCH_COUNT_WEIGHTS = [70, 20, 8, 1.5, 0.5]  # Tỉ lệ câu 1, 2, 3, 4, 5 con cá (tổng = 100)

# ==================== SPECIAL ITEMS (Added to ALL_FISH after loading) ====================
# Add special items that aren't in JSON
ALL_FISH["pearl"] = {"key": "pearl", "name": "Ngọc Trai", "emoji": "🔮", "sell_price": 150}
ALL_FISH["rod_material"] = {"key": "rod_material", "name": "Vật Liệu Nâng Cấp Cần", "emoji": "⚙️", "sell_price": 0}

# Chest loot
CHEST_LOOT = {
    "fertilizer": 25,
    "puzzle_piece": 15,
    "coin_pouch": 20,
    "gift_random": 30,
    "manh_sao_bang": 10,  # Mảnh Sao Băng (10% từ chest)
    "manh_ban_do_a": 5,  # Mảnh Bản Đồ A (5% từ chest)
    "manh_ban_do_b": 5,  # Mảnh Bản Đồ B (5% từ chest)
    "manh_ban_do_c": 5,  # Mảnh Bản Đồ C (5% từ chest)
    "manh_ban_do_d": 5,
}

# System values
WORM_COST = 5

# Tree names
TREE_NAMES = {
    1: "🌱 Hạt mầm",
    2: "🌿 Nảy mầm",
    3: "🎋 Cây non",
    4: "🌳 Trưởng thành",
    5: "🌸 Ra hoa",
    6: "🍎 Kết trái"
}

# Rod levels
ROD_LEVELS = {
    1: {"name": "Cần Tre", "cost": 0, "durability": 30, "repair": 50, "cd": 30, "luck": 0.0, "emoji": "🎋"},
    2: {"name": "Cần Thủy Tinh", "cost": 3000, "durability": 50, "repair": 100, "cd": 25, "luck": 0.0, "emoji": "🎣"},
    3: {"name": "Cần Carbon", "cost": 12000, "durability": 80, "repair": 200, "cd": 20, "luck": 0.02, "emoji": "✨🎣"},
    4: {"name": "Cần Hợp Kim", "cost": 30000, "durability": 120, "repair": 500, "cd": 15, "luck": 0.05, "emoji": "🔱"},
    5: {"name": "Cần Poseidon", "cost": 80000, "durability": 200, "repair": 1000, "cd": 10, "luck": 0.10, "emoji": "🔱✨"},
}

FISHING_EVENTS_PATH = "./data/fishing_events.json"
SELL_EVENTS_PATH = "./data/sell_events.json"
NPC_EVENTS_PATH = "./data/npc_events.json"
FISHING_ACHIEVEMENTS_PATH = "./data/fishing_achievements.json"
FISHING_ITEMS_PATH = "./data/fishing_items.json"


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

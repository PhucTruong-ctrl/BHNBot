"""Configuration settings for the bot."""

import os

# Base directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Database configuration
DB_PATH = os.path.join(DATA_DIR, "database.db")
DB_TIMEOUT = 30.0  # 30 seconds timeout for high concurrency
DB_MAX_RETRIES = 5  # Maximum retry attempts for locked database
DB_RETRY_DELAY = 0.1  # Initial delay between retries (seconds)

# Data file paths
FISHING_DATA_PATH = os.path.join(DATA_DIR, "fishing_data.json")
LEGENDARY_FISH_PATH = os.path.join(DATA_DIR, "legendaryFish_data.json")
FISHING_EVENTS_PATH = os.path.join(DATA_DIR, "fishing_events.json")
SELL_EVENTS_PATH = os.path.join(DATA_DIR, "sell_events.json")
NPC_EVENTS_PATH = os.path.join(DATA_DIR, "npc_events.json")
FISHING_ACHIEVEMENTS_PATH = os.path.join(DATA_DIR, "achievements.json")
FISHING_ITEMS_PATH = os.path.join(DATA_DIR, "fishing_items.json")
DISASTER_EVENTS_PATH = os.path.join(DATA_DIR, "disaster_events.json")

# Game constants (static values that don't change per server)
WORM_COST = 5
FISH_BUCKET_LIMIT = 15
NPC_ENCOUNTER_CHANCE = 0.05
NPC_ENCOUNTER_DELAY = 2
SNAKE_BITE_PENALTY_PERCENT = 0.05
GLOBAL_DISASTER_COOLDOWN = 3600

# Loot tables (game logic, same across servers)
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

# Tree names (static game data)
TREE_NAMES = {
    1: "🌱 Hạt mầm",
    2: "🌿 Nảy mầm",
    3: "🎋 Cây non",
    4: "🌳 Trưởng thành",
    5: "🌸 Ra hoa",
    6: "🍎 Kết trái"
}

# Rod levels (static game data)
ROD_LEVELS = {
    1: {"name": "Cần Tre", "cost": 0, "durability": 30, "repair": 50, "cd": 30, "luck": 0.0, "emoji": "🎋"},
    2: {"name": "Cần Thủy Tinh", "cost": 3000, "durability": 50, "repair": 100, "cd": 25, "luck": 0.0, "emoji": "🎣"},
    3: {"name": "Cần Carbon", "cost": 12000, "durability": 80, "repair": 200, "cd": 20, "luck": 0.02, "emoji": "✨🎣"},
    4: {"name": "Cần Hợp Kim", "cost": 30000, "durability": 120, "repair": 500, "cd": 15, "luck": 0.05, "emoji": "🔱"},
    5: {"name": "Cần Poseidon", "cost": 80000, "durability": 200, "repair": 1000, "cd": 10, "luck": 0.10, "emoji": "🔱✨"},
}
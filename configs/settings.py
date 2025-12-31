"""Configuration settings for the bot."""

import os
from dotenv import load_dotenv
load_dotenv()

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
FISHING_ITEMS_PATH = os.path.join(DATA_DIR, "items")
DISASTER_EVENTS_PATH = os.path.join(DATA_DIR, "disaster_events.json")

# Game constants (static values that don't change per server)
WORM_COST = 3
FISH_BUCKET_LIMIT = 15
NPC_ENCOUNTER_CHANCE = 0.06
NPC_ENCOUNTER_DELAY = 2
SNAKE_BITE_PENALTY_PERCENT = 0.05
GLOBAL_DISASTER_COOLDOWN = 3600
CRYPTO_LOSS_CAP = 5000
AUDIT_TAX_CAP = 10000
GAIN_PERCENT_CAP = 30000

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
    1: {"name": "Cần Tre", "cost": 0, "material": 0, "durability": 30, "repair": 50, "cd": 30, "luck": 0.0, "emoji": "🎋"},
    2: {"name": "Cần Thủy Tinh", "cost": 3000, "material": 5, "durability": 50, "repair": 100, "cd": 25, "luck": 0.0, "emoji": "🎣"},
    3: {"name": "Cần Carbon", "cost": 12000, "material": 10, "durability": 80, "repair": 200, "cd": 20, "luck": 0.02, "emoji": "✨🎣"},
    4: {"name": "Cần Hợp Kim", "cost": 30000, "material": 15, "durability": 120, "repair": 500, "cd": 15, "luck": 0.05, "emoji": "🔱"},
    5: {"name": "Cần Poseidon", "cost": 80000, "material": 20, "durability": 200, "repair": 1000, "cd": 10, "luck": 0.10, "emoji": "🔱✨"},
    6: {
        "name": "Cần Hư Không", 
        "cost": 200000, 
        "material": 25, 
        "special_materials": {"manh_sao_bang": 2},
        "durability": 300, 
        "repair": 2000, 
        "cd": 8, 
        "luck": 0.15, 
        "emoji": "🌌",
        "passive": "double_catch",
        "passive_chance": 0.05
    },
    7: {
        "name": "Cần Thời Gian", 
        "cost": 500000, 
        "material": 35,
        "special_requirement": "ca_ngan_ha",
        "durability": 500, 
        "repair": 5000, 
        "cd": 8, 
        "luck": 0.20, 
        "emoji": "⏳",
        "passive": "no_bait_loss",
        "passive_chance": 0.10,
        "lore": "Cá Ngân Hà ban phép thuật thời gian vào cần câu, cho phép bạn câu cá vượt thời gian..."
    }
}
# Discord Logging Configuration (read from .env)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str.strip().isdigit()]
if OWNER_ID and OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(OWNER_ID)

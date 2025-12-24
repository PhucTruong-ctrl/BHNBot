"""Tree system constants and configuration.

Contains tree images, level names, descriptions, and reward values.
"""

from configs.settings import DB_PATH, DATA_DIR
import json

# Load tree configuration from data file
with open(f"{DATA_DIR}/tree_config.json", 'r', encoding='utf-8') as f:
    TREE_CONFIG = json.load(f)

# ==================== TREE CONFIGURATION ====================

# Base level requirements for season 1
# {level: seeds_required}
BASE_LEVEL_REQS = TREE_CONFIG['base_level_reqs']

# Seasonal scaling factor (25% increase per season)
SEASON_SCALING = 1.25

# ==================== TREE VISUALS ====================

# Tree images by level (1-6)
TREE_IMAGES = {
    1: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(1).png",
    2: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(2).png",
    3: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(3).png",
    4: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(4).png",
    5: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(5).png",
    6: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(6).png"
}

# Tree level names with emoji
TREE_NAMES = {
    1: "🌱 Hạt mầm",
    2: "🌿 Nảy mầm",
    3: "🎋 Cây non",
    4: "🌳 Trưởng thành",
    5: "🌸 Ra hoa",
    6: "🍎 Kết trái"
}

# Tree descriptions by level
TREE_DESCRIPTIONS = {
    1: "Một mầm sống nhỏ bé đang ngủ yên...",
    2: "Mầm non đã vươn lên đón nắng!",
    3: "Cây bắt đầu ra những cành lá đầu tiên.",
    4: "Cây đã cao lớn, tỏa bóng mát cho Hiên Nhà.",
    5: "Những đóa hoa rực rỡ báo hiệu mùa quả ngọt.",
    6: "Cây trĩu quả! Dùng lệnh /thuhoach ngay!"
}

# ==================== TIMING CONSTANTS ====================

# Cache TTLs
USER_CACHE_TTL_SECONDS = 300  # 5 minutes
TREE_DATA_CACHE_TTL_SECONDS = 60  # 60 seconds

# Cleanup intervals
CLEANUP_INTERVAL_HOURS = 1  # Run cleanup every hour
CLEANUP_CUTOFF_HOURS = 24  # Remove data older than 24h
CACHE_EXPIRY_MULTIPLIER = 2  # Clean cache at 2x TTL

# Rate limiting
CONTRIBUTION_COOLDOWN_SECONDS = 2  # Minimum time between contributions

# Time conversion helpers
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400

# Seed rewards by rank when harvesting
HARVEST_REWARDS = {
    "top1": 10000,       # Top contributor
    "top2": 5000,        # Second place
    "top3": 3000,        # Third place
    "others": 1500,      # All other contributors
    "top1_bonus": 3000   # Extra bonus for top 1
}

# Harvest buff duration in hours
HARVEST_BUFF_HOURS = 24

# Security: Maximum total harvest rewards to prevent overflow
MAX_TOTAL_REWARDS = 100_000_000  # 100M seeds cap

# ==================== UPDATE SETTINGS ====================

# Minimum seconds between tree message updates (debounce)
TREE_UPDATE_DEBOUNCE_SECONDS = 5

# Progress bar length in characters
PROGRESS_BAR_LENGTH = 14

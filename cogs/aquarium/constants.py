
from core.item_system import item_system

# Leaf Coin Exchange Rate
LEAF_COIN_RATE = 1  # 1 Trash = 1 Leaf Coin

# Streak Bonus
STREAK_BONUS_DAYS = 5
STREAK_BONUS_PERCENT = 0.10

# Trash Items (Fallback logic)
try:
    _all_items = item_system.get_all_items()
    TRASH_ITEM_IDS = [k for k, v in _all_items.items() if v.get("type") == "trash"]
    if not TRASH_ITEM_IDS: raise ValueError("Empty trash list")
except:
    TRASH_ITEM_IDS = ["rac", "chai_nhua", "lon_nuoc", "giay_vun", "vo_oc", "xuong_ca", "chai_thuy_tinh"]

# Structure: key -> {name, price_seeds, price_leaf, icon, type, description}
DECOR_ITEMS = {
    "san_ho": {
        "name": "San Hô Đỏ", 
        "price_seeds": 5000, 
        "price_leaf": 50, 
        "icon": "🪸", 
        "type": "water", 
        "desc": "Tăng vẻ đẹp hoang sơ. (+2 Charm)",
        "set": "dai_duong"
    },
    "rong_bien": {
        "name": "Rong Biển Xanh", 
        "price_seeds": 2000, 
        "price_leaf": 20, 
        "icon": "🌿", 
        "type": "water", 
        "desc": "Thức ăn cho cá. (+1 Charm)",
        "set": "dai_duong"
    },
    "ruong_vang": {
        "name": "Rương Kho Báu", 
        "price_seeds": 50000, 
        "price_leaf": 200, 
        "price_magic_fruit": 1, 
        "icon": "⚱️", 
        "type": "floor", 
        "desc": "Chứa đầy bí mật. (+10 Charm)",
        "set": "hoang_gia"
    },
    "ca_map": {
        "name": "Cá Mập Con", 
        "price_seeds": 100000, 
        "price_leaf": 500, 
        "icon": "🦈", 
        "type": "fish", 
        "desc": "Hung dữ nhưng đáng yêu. (+20 Charm)",
        "set": "dai_duong"
    },
    "mo_neo": {
        "name": "Mỏ Neo Cổ", 
        "price_seeds": 15000, 
        "price_leaf": 100, 
        "icon": "⚓", 
        "type": "floor", 
        "desc": "Dấu tích tàu đắm. (+5 Charm)",
        "set": "hoang_gia"
    },
    "den_neon": {
        "name": "Đèn Neon Sứa", 
        "price_seeds": 30000, 
        "price_leaf": 150, 
        "icon": "💡", 
        "type": "float", 
        "desc": "Lung linh huyền ảo. (+8 Charm)",
        "set": "dai_duong"
    },
    "lau_dai_cat": {
        "name": "Lâu Đài Cát", 
        "price_seeds": 20000, 
        "price_leaf": 80, 
        "icon": "🏰", 
        "type": "floor", 
        "desc": "Công trình kiến trúc tí hon. (+6 Charm)",
        "set": "hoang_gia"
    },
    "ngoc_trai_khong_lo": {
        "name": "Ngọc Trai Khổng Lồ", 
        "price_seeds": 200000, 
        "price_leaf": 1000, 
        "icon": "🔮", 
        "type": "floor", 
        "desc": "Hào quang chói lóa. (+50 Charm)",
        "set": "hoang_gia"
    },
    # Phase 3: Future Tech (Tier 3)
    "hologram_shark": {
        "name": "Cá Mập Hologram",
        "price_seeds": 500000,
        "price_leaf": 2000,
        "icon": "🦈",
        "type": "fish",
        "desc": "Công nghệ 4.0. (+80 Charm)",
        "set": "tuong_lai"
    },
    "cyber_coral": {
        "name": "San Hô Cyber",
        "price_seeds": 150000,
        "price_leaf": 800,
        "icon": "👾",
        "type": "water",
        "desc": "Phát sáng RGB. (+40 Charm)",
        "set": "tuong_lai"
    }
}

# Feng Shui Sets (Bonuses)
FENG_SHUI_SETS = {
    "dai_duong": {
        "name": "🌊 Rạn San Hô (Tier 1)",
        "required": ["san_ho", "rong_bien", "ca_map", "den_neon"],
        "bonus_desc": "Tăng 5% Hạt nhận từ Cây Server (/thuhoach).",
        "icon": "🌊",
        "tier": 1
    },
    "hoang_gia": {
        "name": "👑 Kho Báu Cổ Đại (Tier 2)",
        "required": ["ruong_vang", "lau_dai_cat", "ngoc_trai_khong_lo", "mo_neo"],
        "bonus_desc": "Tăng 10% giá trị bán cá (/ban).",
        "icon": "👑",
        "tier": 2
    },
    "tuong_lai": {
        "name": "🚀 Công Nghệ Tương Lai (Tier 3)",
        "required": ["hologram_shark", "cyber_coral"],
        "bonus_desc": "Nhận 200 Hạt mỗi ngày (Passive).",
        "icon": "🚀",
        "tier": 3
    }
}

# VIP System Constants
VIP_PRICES = {
    1: 10000,   # Silver
    2: 50000,   # Gold
    3: 200000   # Diamond
}

VIP_NAMES = {
    1: "Thành Viên Bạc",
    2: "Thành Viên Vàng",
    3: "Thành Viên Kim Cương"
}

VIP_COLORS = {
    1: 0xbdc3c7, # Silver
    2: 0xf1c40f, # Gold
    3: 0x3498db  # Diamond (Cyan-ish)
}
AQUARIUM_FORUM_CHANNEL_ID = 0 # TODO: CREATE A FORUM CHANNEL AND SET ID HERE

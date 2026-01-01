from core.item_system import item_system

# Dynamically load Trash IDs from centralized Item System
_all_items = item_system.get_all_items()
TRASH_ITEM_IDS = [k for k, v in _all_items.items() if v.get("type") == "trash"]
if not TRASH_ITEM_IDS:
    # Fallback if item_system not loaded/empty (safe defaults)
    TRASH_ITEM_IDS = ["rac", "chai_nhua", "lon_nuoc", "giay_vun", "vo_oc", "xuong_ca"]

# Leaf Coin Exchange Rate
LEAF_COIN_RATE = 1  # 1 Trash = 1 Leaf Coin

# Streak Bonus
STREAK_BONUS_DAYS = 5
STREAK_BONUS_PERCENT = 0.10

# Decor Definition
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
    }
}

# Feng Shui Sets (Bonuses)
# Logic: If user has ALL required items in their slots (any order), apply bonus.
FENG_SHUI_SETS = {
    "dai_duong": {
        "name": "🌊 Hơi Thở Đại Dương",
        "required": ["san_ho", "rong_bien", "ca_map", "den_neon"],
        "bonus_desc": "Tăng 20% sản lượng Xu Lá khi tái chế.",
        "icon": "🌊"
    },
    "hoang_gia": {
        "name": "👑 Kho Báu Hoàng Gia",
        "required": ["ruong_vang", "lau_dai_cat", "ngoc_trai_khong_lo", "mo_neo"],
        "bonus_desc": "Giảm 10% giá mua nội thất.",
        "icon": "👑"
    }
}

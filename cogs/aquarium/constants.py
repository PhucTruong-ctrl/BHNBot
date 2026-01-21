
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
except Exception:
    TRASH_ITEM_IDS = ["rac", "chai_nhua", "lon_nuoc", "giay_vun", "vo_oc", "xuong_ca", "chai_thuy_tinh"]

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
AQUARIUM_FORUM_CHANNEL_ID = 0


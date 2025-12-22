"""Consumable items system for buffs and effects."""

import json
import os

# Load consumable items from unified fishing_items.json
_consumables_path = "./data/fishing_items.json"

def _load_consumable_items():
    """Load consumable items from JSON with graceful fallback."""
    if os.path.exists(_consumables_path):
        try:
            with open(_consumables_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("items", {})
                # Filter only consumable type items
                consumables = {k: v for k, v in items.items() if v.get("type") == "consumable"}
                return consumables
        except Exception as e:
            print(f"[WARNING] Failed to load consumable items from JSON: {e}")
    return {}

# Initialize consumable items from JSON
CONSUMABLE_ITEMS = _load_consumable_items()

# Fallback if JSON doesn't exist or is empty - provide default consumables
if not CONSUMABLE_ITEMS:
    print("[WARNING] No consumable items loaded from JSON. Using fallback defaults.")
    CONSUMABLE_ITEMS = {
        "nuoc_tang_luc": {
            "key": "nuoc_tang_luc",
            "type": "consumable",
            "name": "💪 Nước Tăng Lực",
            "emoji": "💪",
            "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 90% (1 lần sử dụng)",
            "sell_price": 0,
            "effect_type": "legendary_fish_boost",
            "effect_value": 0.90,
            "original_value": 0.65,
            "one_time_use": True,
        },
        "gang_tay_xin": {
            "key": "gang_tay_xin",
            "type": "consumable",
            "name": "🥊 Găng Tay Câu Cá",
            "emoji": "🥊",
            "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 90% (1 lần sử dụng)",
            "sell_price": 0,
            "effect_type": "legendary_fish_boost",
            "effect_value": 0.90,
            "original_value": 0.65,
            "one_time_use": True,
        },
        "thao_tac_tinh_vi": {
            "key": "thao_tac_tinh_vi",
            "type": "consumable",
            "name": "🎯 Thao Tác Tinh Vi",
            "emoji": "🎯",
            "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 92% (1 lần sử dụng)",
            "sell_price": 0,
            "effect_type": "legendary_fish_boost",
            "effect_value": 0.92,
            "original_value": 0.65,
            "one_time_use": True,
        },
        "tinh_yeu_ca": {
            "key": "tinh_yeu_ca",
            "type": "consumable",
            "name": "❤️ Tình Yêu Với Cá",
            "emoji": "❤️",
            "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 88% (1 lần sử dụng)",
            "sell_price": 0,
            "effect_type": "legendary_fish_boost",
            "effect_value": 0.88,
            "original_value": 0.65,
            "one_time_use": True,
        },
    }

# Tạo reverse lookup theo tên
CONSUMABLE_BY_NAME = {item_info["name"]: key for key, item_info in CONSUMABLE_ITEMS.items()}

def get_consumable_info(item_key: str) -> dict | None:
    """Lấy thông tin vật phẩm tiêu thụ"""
    return CONSUMABLE_ITEMS.get(item_key)

def is_consumable(item_key: str) -> bool:
    """Kiểm tra xem có phải vật phẩm tiêu thụ không"""
    return item_key in CONSUMABLE_ITEMS


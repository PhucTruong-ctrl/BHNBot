"""Consumable items system for buffs and effects."""

import json
import os

from configs.item_constants import ItemKeys

from core.item_system import item_system

def _load_consumable_items():
    """Load consumable items from ItemSystem."""
    all_items = item_system.get_all_items()
    consumables = {}
    
    # 1. Standard Consumables
    for k, v in all_items.items():
        if v.get("type") == "consumable":
            consumables[k] = v
            
    # 2. Special Legendary Quest Items (whitelist)
    # These might be type 'legendary_component' or 'tool', but acts as consumable
    special_keys = [
        "tinh_cau", 
        "long_vu_lua", 
        "ban_do_ham_am", 
        "may_do_song"
    ]
    
    for k in special_keys:
        if k in all_items and k not in consumables:
            consumables[k] = all_items[k]
            
    return consumables

# Initialize consumable items from JSON
CONSUMABLE_ITEMS = _load_consumable_items()

# Fallback if JSON doesn't exist or is empty - provide default consumables
if not CONSUMABLE_ITEMS:
    print("[WARNING] No consumable items loaded from JSON. Using fallback defaults.")
    CONSUMABLE_ITEMS = {
        ItemKeys.NUOC_TANG_LUC: {
            "key": ItemKeys.NUOC_TANG_LUC,
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
        ItemKeys.GANG_TAY_XIN: {
            "key": ItemKeys.GANG_TAY_XIN,
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
        ItemKeys.THAO_TAC_TINH_VI: {
            "key": ItemKeys.THAO_TAC_TINH_VI,
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
        ItemKeys.TINH_YEU_CA: {
            "key": ItemKeys.TINH_YEU_CA,
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


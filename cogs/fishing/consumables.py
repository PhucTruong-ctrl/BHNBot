"""Consumable items system for buffs and effects."""

# Định nghĩa các vật phẩm tiêu thụ
CONSUMABLE_ITEMS = {
    "nuoc_tang_luc": {
        "name": "💪 Nước Tăng Lực",
        "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 90% (1 lần sử dụng)",
        "mechanism": "Khi bấm nút 'Dìu Cá' trong trận câu cá huyền thoại, tỉ lệ thắng tăng lên 90%",
        "category": "buff",
        "effect_type": "legendary_fish_boost",  # Loại hiệu ứng
        "effect_value": 0.90,  # Giá trị boost (tỉ lệ thắng mới)
        "original_value": 0.65,  # Giá trị gốc
        "one_time_use": True,  # Dùng 1 lần thì mất
    },
    "gang_tay_xin": {
        "name": "🥊 Găng Tay Câu Cá",
        "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 90% (1 lần sử dụng)",
        "mechanism": "Khi bấm nút 'Dìu Cá' trong trận câu cá huyền thoại, tỉ lệ thắng tăng lên 90%",
        "category": "buff",
        "effect_type": "legendary_fish_boost",
        "effect_value": 0.90,
        "original_value": 0.65,
        "one_time_use": True,
    },
    "thao_tac_tinh_vi": {
        "name": "🎯 Thao Tác Tinh Vi",
        "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 92% (1 lần sử dụng)",
        "mechanism": "Kỹ năng câu cá cao cấp - cải thiện kỹ thuật dìu cá",
        "category": "buff",
        "effect_type": "legendary_fish_boost",
        "effect_value": 0.92,
        "original_value": 0.65,
        "one_time_use": True,
    },
    "tim_yeu_ca": {
        "name": "❤️ Tình Yêu Với Cá",
        "description": "Tăng tỉ lệ thắng 'Dìu Cá' từ 65% → 88% (1 lần sử dụng)",
        "mechanism": "Cảm thông với tâm trạng của cá - dễ dàng kiểm soát hơn",
        "category": "buff",
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

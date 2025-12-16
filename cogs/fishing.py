import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import asyncio
import time
from datetime import datetime, timedelta
from database_manager import (
    get_inventory,
    add_item,
    remove_item,
    add_seeds,
    get_user_balance,
    get_or_create_user
)

DB_PATH = "./data/database.db"

# ==================== LOOT TABLES ====================

LOOT_TABLE_NORMAL = {
    "trash": 30,         # Rác (ủng rách, lon nước)
    "common_fish": 60,   # Cá thường (cá chép, cá rô) - nguồn thu chính
    "rare_fish": 5,      # Cá hiếm (cá koi, cá hồi) - giảm để rare thực sự rare
    "chest": 5           # Rương báu
}

# Khi cây ở level max hoặc nở hoa (Boost)
# CHÚ Ý: Boost chỉ áp dụng x2 giá bán, KHÔNG tăng tỷ lệ Cá Hiếm (chống lạm phát)
LOOT_TABLE_BOOST = {
    "trash": 15,         # Giảm rác
    "common_fish": 75,   # Tăng cá thường (thay vì tăng cá hiếm)
    "rare_fish": 5,      # GIỮ NGUYÊN 5% - không tăng cá hiếm (chống lạm phát)
    "chest": 5           # Rương tương tự
}

# Không có mồi câu (No Worm) - Câu được cá nhỏ để kiếm vốn, nhưng cực khó ra đồ xịn
# Để giúp newbie dễ kiếm 10 Hạt đầu tiên và không cảm thấy nản
LOOT_TABLE_NO_WORM = {
    "trash": 50,         # Rác (vừa phải - giúp newbie kiếm cá để bán)
    "common_fish": 49,   # Cá thường (tăng cơ hội kiếm vốn)
    "rare_fish": 1,      # Cực hiếm - cho hy vọng bất ngờ (1%)
    "chest": 0           # Không có rương khi không có mồi
}

# Tỉ lệ roll số lượng cá (1-5) - tỉ lệ giảm dần (NERF từ [40,30,20,8,2] -> [70,20,8,2,0])
# 1 cá: 70%, 2 cá: 20%, 3 cá: 8%, 4 cá: 2%, 5 cá: 0%
# Trung bình: ~1.4 con/lần (giảm từ 2.0)
CATCH_COUNT_WEIGHTS = [70, 20, 8, 2, 0]  # Cho random.choices() với k=1

# ==================== FISH DATABASE ====================

# 1. CÁ THƯỜNG (COMMON) - Tỉ lệ gặp cao (~90-95%)
# Giá: 5 - 15 Hạt.
COMMON_FISH = [
    # --- Nhóm Giá Rẻ (5-7 Hạt) - Dễ dính ---
    {"key": "ca_chep", "name": "Cá Chép", "emoji": "🐠", "sell_price": 5},
    {"key": "ca_ro", "name": "Cá Rô", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_bong", "name": "Cá Bống", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_com", "name": "Cá Cơm", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_moi", "name": "Cá Mòi", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_me", "name": "Cá Mè", "emoji": "⚪", "sell_price": 6},
    {"key": "ca_sac", "name": "Cá Sặc", "emoji": "🐠", "sell_price": 6},
    {"key": "ca_nuc", "name": "Cá Nục", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_bac_ma", "name": "Cá Bạc Má", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_chim", "name": "Cá Chim", "emoji": "⬜", "sell_price": 7},

    # --- Nhóm Trung Bình (8-10 Hạt) ---
    {"key": "ca_tre", "name": "Cá Trê", "emoji": "🥖", "sell_price": 8},
    {"key": "ca_loc", "name": "Cá Lóc", "emoji": "🦈", "sell_price": 9},
    {"key": "ca_tram", "name": "Cá Trắm", "emoji": "🐟", "sell_price": 9},
    {"key": "ca_chach", "name": "Cá Chạch", "emoji": "🐍", "sell_price": 8},
    {"key": "ca_keo", "name": "Cá Kèo", "emoji": "🥢", "sell_price": 8},
    {"key": "ca_dieu_hong", "name": "Diêu Hồng", "emoji": "🌸", "sell_price": 9},
    {"key": "ca_vang", "name": "Cá Vàng", "emoji": "🐡", "sell_price": 10},
    {"key": "ca_bay_mau", "name": "Cá 7 Màu", "emoji": "🌈", "sell_price": 10},
    {"key": "ca_nheo", "name": "Cá Nheo", "emoji": "🐟", "sell_price": 10},
    {"key": "ca_ho", "name": "Cá Hố", "emoji": "🎗️", "sell_price": 10},

    # --- Nhóm Ngon (11-15 Hạt) ---
    {"key": "ca_thu", "name": "Cá Thu", "emoji": "🐟", "sell_price": 12},
    {"key": "ca_ngu", "name": "Cá Ngừ", "emoji": "🦈", "sell_price": 12},
    {"key": "ca_mu", "name": "Cá Mú", "emoji": "🐡", "sell_price": 13},
    {"key": "ca_lang", "name": "Cá Lăng", "emoji": "🥖", "sell_price": 14},
    {"key": "ca_chinh", "name": "Cá Chình", "emoji": "🐍", "sell_price": 14},
    {"key": "ca_tai_tuong", "name": "Tai Tượng", "emoji": "👂", "sell_price": 13},
    {"key": "muc_ong", "name": "Mực Ống", "emoji": "🦑", "sell_price": 15},
    {"key": "bach_tuoc", "name": "Bạch Tuộc", "emoji": "🐙", "sell_price": 15},
    {"key": "tom_hum_dat", "name": "Tôm Đất", "emoji": "🦐", "sell_price": 15},
    {"key": "cua_dong", "name": "Cua Đồng", "emoji": "🦀", "sell_price": 12},
]

# 2. CÁ HIẾM (RARE) - Tỉ lệ gặp thấp (~5-10%)
# Giá: 35 - 150 Hạt.
RARE_FISH = [
    # --- Rare Thường (35-50 Hạt) ---
    {"key": "ca_koi", "name": "Cá Koi", "emoji": "✨🐠", "sell_price": 35},
    {"key": "ca_he", "name": "Cá Hề (Nemo)", "emoji": "🤡", "sell_price": 35},
    {"key": "ca_hoi", "name": "Cá Hồi", "emoji": "🍣", "sell_price": 40},
    {"key": "ca_thien_than", "name": "Thiên Thần", "emoji": "👼", "sell_price": 40},
    {"key": "ca_dia", "name": "Cá Đĩa", "emoji": "💿", "sell_price": 45},
    {"key": "ca_ngua", "name": "Cá Ngựa", "emoji": "🐎", "sell_price": 45},
    {"key": "ca_tam", "name": "Cá Tầm", "emoji": "🦈", "sell_price": 50},
    {"key": "ca_betta", "name": "Betta Rồng", "emoji": "🐉", "sell_price": 50},

    # --- Rare Xịn (60-90 Hạt) ---
    {"key": "ca_duoi_dien", "name": "Đuối Điện", "emoji": "⚡", "sell_price": 60},
    {"key": "ca_long_den", "name": "Cá Lồng Đèn", "emoji": "💡", "sell_price": 65},
    {"key": "ca_mat_trang", "name": "Mặt Trăng", "emoji": "🌙", "sell_price": 70},
    {"key": "ca_kiem", "name": "Cá Kiếm", "emoji": "⚔️", "sell_price": 75},
    {"key": "ca_rong", "name": "Cá Rồng", "emoji": "🐲", "sell_price": 80},
    {"key": "ca_map", "name": "Cá Mập", "emoji": "🦈", "sell_price": 90},

    # --- LEGENDARY (100+ Hạt) ---
    {"key": "ca_voi", "name": "Cá Voi Xanh", "emoji": "🐋", "sell_price": 120},
    {"key": "ca_hai_tuong", "name": "Hải Tượng", "emoji": "🦕", "sell_price": 130},
    {"key": "ca_nha_tang", "name": "Cá Nhà Táng", "emoji": "🐳", "sell_price": 150},
]

# (Đừng quên giữ dòng này để code hoạt động)
# PEARL_INFO = {"key": "pearl", "name": "Ngọc Trai", "emoji": "🔮", "sell_price": 150}

# Ngọc Trai - Item hiếm từ Tiên Cá (bán giá cao)
PEARL_INFO = {"key": "pearl", "name": "Ngọc Trai", "emoji": "🔮", "sell_price": 150}

# Create lookup dictionaries
ALL_FISH = {fish["key"]: fish for fish in COMMON_FISH + RARE_FISH}
ALL_FISH["pearl"] = PEARL_INFO  # Thêm ngọc trai vào danh sách để có thể bán
COMMON_FISH_KEYS = [f["key"] for f in COMMON_FISH]
RARE_FISH_KEYS = [f["key"] for f in RARE_FISH]

# Rác tái chế
TRASH_ITEMS = [
    {"name": "Ủng Rách", "emoji": "🥾"},
    {"name": "Lon Nước", "emoji": "🥫"},
    {"name": "Xà Phòng Cũ", "emoji": "🧼"},
    {"name": "Mảnh Kính", "emoji": "🔨"},
]

# Rương báu - các loại vật phẩm có thể ra
CHEST_LOOT = {
    "fertilizer": 30,       # Phân bón
    "puzzle_piece": 20,     # Mảnh ghép
    "coin_pouch": 20,       # Túi hạt
    "gift_random": 30       # Quà tặng ngẫu nhiên
}

# Các loại quà tặng
GIFT_ITEMS = ["cafe", "flower", "ring", "gift", "chocolate", "card"]

# Mồi câu (Money Sink)
WORM_COST = 5  # Giá mua mồi - chống lạm phát bằng cách tiêu tiền trước khi câu

# ==================== ACHIEVEMENTS SYSTEM ====================
# Hệ thống thành tựu - mục tiêu dài hạn cho người chơi
# Format: {"key": {"name": "Tên", "description": "Mô tả", "condition_type": "type", "target": value, "reward_coins": x, "role_id": ROLE_ID}}

ACHIEVEMENTS = {
    "first_catch": {
        "name": "Tân Thủ Tập Sự",
        "description": "Câu được con cá đầu tiên",
        "condition_type": "first_catch",
        "target": 1,
        "reward_coins": 50,
        "emoji": "🎣",
        "role_id": None  # Để trống - không cấp role cho thành tựu này
    },
    "worm_destroyer": {
        "name": "Kẻ Hủy Diệt Giun",
        "description": "Tiêu thụ tổng cộng 500 Giun",
        "condition_type": "worms_used",
        "target": 500,
        "reward_coins": 1000,
        "emoji": "🪱",
        "role_id": None  # Để trống hoặc thay bằng role_id của server
    },
    "trash_master": {
        "name": "Hiệp Sĩ Môi Trường",
        "description": "Câu được 100 loại Rác",
        "condition_type": "trash_caught",
        "target": 100,
        "reward_coins": 500,
        "emoji": "🗑️",
        "role_id": None
    },
    "millionaire": {
        "name": "Tỷ Phú",
        "description": "Kiếm được 100,000 Hạt từ bán cá",
        "condition_type": "coins_earned",
        "target": 100000,
        "reward_coins": 5000,
        "emoji": "💰",
        "role_id": None
    },
    "dragon_slayer": {
        "name": "Long Vương",
        "description": "Câu được Cá Rồng (Cá hiếm nhất)",
        "condition_type": "caught_fish",
        "target": "ca_rong",
        "reward_coins": 1000,
        "emoji": "🐲",
        "role_id": None
    },
    "unlucky": {
        "name": "Thánh Nhọ",
        "description": "Gặp sự kiện xấu 50 lần",
        "condition_type": "bad_events",
        "target": 50,
        "reward_coins": 500,
        "emoji": "😭",
        "role_id": None
    },
    "lucky": {
        "name": "Bạn Của Thần Tài",
        "description": "Gặp sự kiện tốt 50 lần",
        "condition_type": "good_events",
        "target": 50,
        "reward_coins": 2000,
        "emoji": "✨",
        "role_id": None
    },
    "collection_master": {
        "name": "Vua Câu Cá",
        "description": "Hoàn thành bộ sưu tập (câu được tất cả loại cá)",
        "condition_type": "collection_complete",
        "target": 1,
        "reward_coins": 10000,
        "emoji": "👑",
        "role_id": 1450409414111658024  # Dùng role "Vua Câu Cá" hiện tại
    }
}

# ==================== RANDOM EVENTS EXPANDED ====================
# Tỉ lệ tổng nên giữ ở mức 14-16% để game không bị loạn
# 20 sự kiện: 10 xấu + 10 tốt

RANDOM_EVENTS = {
    # --- BAD EVENTS (Kiếp Nạn - 10 sự kiện) ---
    "snapped_line": {"chance": 0.008, "name": "Đứt Dây!"},
    "police_fine": {"chance": 0.005, "name": "Công An Phạt!"},
    "predator": {"chance": 0.008, "name": "Cá Sư Tử!"},
    "dropped_slipper": {"chance": 0.01, "name": "Rớt Dép!"},
    "mom_called": {"chance": 0.005, "name": "Mẹ Gọi!"},
    "cat_steal": {"chance": 0.008, "name": "Mèo Mun!"},
    "broken_phone": {"chance": 0.001, "name": "Rớt iPhone!"},
    "sea_sickness": {"chance": 0.003, "name": "Say Sóng!"},
    "snake_bite": {"chance": 0.003, "name": "Rắn Nước!"},
    "plastic_trap": {"chance": 0.005, "name": "Vướng Rác!"},

    # --- GOOD EVENTS (Nhân Phẩm - 10 sự kiện) ---
    "found_wallet": {"chance": 0.008, "name": "Vớt Ví!"},
    "fairy_gift": {"chance": 0.005, "name": "Ông Bụt!"},
    "double_rainbow": {"chance": 0.003, "name": "Cầu Vồng!"},
    "tourist_tip": {"chance": 0.008, "name": "Khách Tip!"},
    "golden_turtle": {"chance": 0.005, "name": "Rùa Vàng!"},
    "school_of_fish": {"chance": 0.005, "name": "Bão Cá!"},
    "engagement_ring": {"chance": 0.002, "name": "Nhẫn Cầu!"},
    "ancient_vase": {"chance": 0.001, "name": "Bình Cổ!"},
    "sixth_sense": {"chance": 0.004, "name": "Giác Thứ 6!"},
    "treasure_shipwreck": {"chance": 0.002, "name": "Tàu Nạn!"},
}

RANDOM_EVENT_MESSAGES = {
    # --- BAD EVENTS ---
    "snapped_line": "Dây đứt phựt! Mất toi cái mồi. 😭",
    "police_fine": "O e o e! 🚔 Công an phạt 50 Hạt vì câu trộm!",
    "predator": "Cá Sư Tử lao tới đớp sạch mẻ cá của bạn! 😱",
    "dropped_slipper": "Mải giật cần làm rớt dép lào. Phải bơi đi nhặt mất 2 phút! 🩴",
    "mom_called": "Mẹ gọi về ăn cơm! Bạn vội chạy về, bỏ lỡ mẻ cá này. 🍚",
    "cat_steal": "Meow! 🐈 Một con mèo đen nhảy ra cướp mất con cá to nhất của bạn!",
    "broken_phone": "Tõm! Chiếc điện thoại rơi xuống nước. Tốn 200 Hạt sửa chữa. 📱💦",
    "sea_sickness": "Sóng đánh tụt quần! Bạn nôn thốc nôn tháo... nôn hết cả túi mồi ra biển. 🤢",
    "snake_bite": "Kéo lên không phải cá mà là con Rắn Nước! Bị cắn chảy máu 😱 (-5% tài sản)",
    "plastic_trap": "Lưỡi câu mắc vào bao tải rác khổng lồ. Cần câu gãy, chờ thêm 3 phút. 🗑️",
    
    # --- GOOD EVENTS ---
    "found_wallet": "Vớt được cái ví da cá sấu! Bên trong có 150 Hạt. 👛✨",
    "fairy_gift": "Ông Bụt hiện lên: 'Ta tặng con 5 con Giun vì sự kiên trì'. 🎅",
    "double_rainbow": "Cầu vồng đôi xuất hiện! 🌈 May mắn tràn trề (Lần sau chắc chắn ra Cá Hiếm)!",
    "tourist_tip": "Khách du lịch thấy bạn câu đỉnh quá nên tip nóng 100 Hạt. 💵",
    "golden_turtle": "Cụ Rùa Vàng nổi lên! 🐢✨ Bạn cảm thấy khỏe khoắn (Xóa cooldown lượt này).",
    "school_of_fish": "Trúng ổ cá rồi! 🐟🐟🐟 Số lượng cá nhân 3!",
    "engagement_ring": "Vớt được chiếc nhẫn kim cương! Bán được 300 Hạt. 💍",
    "ancient_vase": "Vớt được bình gốm thời Lý! Bán cho bảo tàng được 500 Hạt! 🏺💰",
    "sixth_sense": "Tự nhiên linh tính mách bảo... ✨ Bạn tránh được xui xẻo lần sau!",
    "treasure_shipwreck": "Một xác tàu chìm hiện lên! 🏴‍☠️ Bạn vớt được 2 Rương Kho Báu!",
}


# ==================== SELL EVENTS (Sự kiện khi bán cá) ====================
# Tỉ lệ xảy ra khi bán: khoảng 15-20%

SELL_EVENTS = {
    # --- BAD EVENTS (Xui xẻo - Giảm tiền) ---
    "market_crash":   {"chance": 0.01, "type": "bad", "mul": 0.7, "flat": 0, "name": "Chợ Ế!"},
    "rotten_fish":    {"chance": 0.01, "type": "bad", "mul": 0.8, "flat": 0, "name": "Cá Ươn!"},
    "tax_collector":  {"chance": 0.01, "type": "bad", "mul": 0.85, "flat": 0, "name": "Thuế Chợ!"},
    "broken_scale":   {"chance": 0.01, "type": "bad", "mul": 0.9, "flat": 0, "name": "Cân Điêu!"},
    "dropped_money":  {"chance": 0.01, "type": "bad", "mul": 1.0, "flat": -50, "name": "Rớt Tiền!"},
    "gangster_fee":   {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -100, "name": "Phí Bảo Kê!"},
    "hole_in_bag":    {"chance": 0.01, "type": "bad", "mul": 0.95, "flat": 0, "name": "Túi Thủng!"},
    "rainy_day":      {"chance": 0.01, "type": "bad", "mul": 0.75, "flat": 0, "name": "Mưa Giông!"},
    "pickpocket":     {"chance": 0.005, "type": "bad", "mul": 0.6, "flat": 0, "name": "Móc Túi!"},
    "fake_money":     {"chance": 0.01, "type": "bad", "mul": 1.0, "flat": -20, "name": "Tiền Giả!"},

    # --- GOOD EVENTS (May mắn - Tăng tiền) ---
    "market_boom":    {"chance": 0.01, "type": "good", "mul": 1.3, "flat": 0, "name": "Được Giá!"},
    "sushi_chef":     {"chance": 0.005, "type": "good", "mul": 1.5, "flat": 0, "name": "Đầu Bếp VIP!"},
    "rich_customer":  {"chance": 0.01, "type": "good", "mul": 1.2, "flat": 0, "name": "Khách Sộp!"},
    "tip_money":      {"chance": 0.01, "type": "good", "mul": 1.0, "flat": 50, "name": "Tiền Tip!"},
    "golden_scale":   {"chance": 0.01, "type": "good", "mul": 1.1, "flat": 0, "name": "Cân Thừa!"},
    "bidding_war":    {"chance": 0.005, "type": "good", "mul": 1.4, "flat": 0, "name": "Tranh Mua!"},
    "festival":       {"chance": 0.01, "type": "good", "mul": 1.25, "flat": 0, "name": "Lễ Hội!"},
    "charity":        {"chance": 0.01, "type": "good", "mul": 1.0, "flat": 100, "name": "Lì Xì!"},
    "fresh_bonus":    {"chance": 0.01, "type": "good", "mul": 1.15, "flat": 0, "name": "Tươi Roi Rói!"},
    "god_of_wealth":  {"chance": 0.002, "type": "good", "mul": 2.0, "flat": 0, "name": "Thần Tài!"},
}

SELL_MESSAGES = {
    # Bad
    "market_crash": "Hôm nay chợ vắng hoe, tiểu thương ép giá thê thảm. 📉 (Giá giảm 30%)",
    "rotten_fish": "Bảo quản không kỹ, một số cá bị ươn nên phải bán rẻ. 🤢 (Giá giảm 20%)",
    "tax_collector": "Ban quản lý chợ đi thu thuế chỗ ngồi. 💸 (Mất 15% doanh thu)",
    "broken_scale": "Cân của bà chủ bị 'lỗi', cân điêu cho bạn. ⚖️ (Mất 10% doanh thu)",
    "dropped_money": "Bán xong hí hửng đi về, bạn làm rớt mất 50 Hạt. 😭",
    "gangster_fee": "Giang hồ chợ cá chặn đường thu 'phí bảo kê'. 🕶️ (Mất 100 Hạt)",
    "hole_in_bag": "Túi đựng tiền bị thủng lỗ nhỏ, rơi rớt dọc đường. 🧵 (Mất 5%)",
    "rainy_day": "Trời mưa to quá, phải bán tháo để chạy mưa. 🌧️ (Giá giảm 25%)",
    "pickpocket": "Ơ! Ví đâu rồi? Kẻ gian đã móc túi bạn lúc đông người! 🕵️ (Mất 40% doanh thu)",
    "fake_money": "Về nhà đếm lại mới phát hiện có tờ tiền giả. 💸 (Mất 20 Hạt)",

    # Good
    "market_boom": "Thị trường đang khan hiếm, thương lái tranh nhau mua! 📈 (Giá tăng 30%)",
    "sushi_chef": "Một đầu bếp nhà hàng 5 sao đi chợ và mua hết cá của bạn! 🍣 (Giá tăng 50%)",
    "rich_customer": "Gặp đại gia mua cá về làm hồ thủy sinh, không cần nhìn giá. 🎩 (Giá tăng 20%)",
    "tip_money": "Khách thấy bạn bán hàng duyên dáng nên bo thêm tiền. 💵 (+50 Hạt)",
    "golden_scale": "Cân nhà này bị hỏng, cân thừa cho bạn! ⚖️ (Lời thêm 10%)",
    "bidding_war": "Hai bà bán cá tranh nhau mua mẻ cá ngon của bạn. 🗣️ (Giá tăng 40%)",
    "festival": "Lễ hội ẩm thực đang diễn ra, nhu cầu cá tăng cao! 🏮 (Giá tăng 25%)",
    "charity": "Hôm nay bà chủ trúng số nên lì xì cho bạn. 🧧 (+100 Hạt)",
    "fresh_bonus": "Cá bạn tươi quá, được đánh giá 5 sao! ⭐ (Giá tăng 15%)",
    "god_of_wealth": "🧧 **THẦN TÀI GÕ CỬA!** Hôm nay là ngày may mắn nhất đời bạn! (X2 DOANH THU)",
}

# ==================== UI COMPONENTS ====================

class FishSellView(discord.ui.View):
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
    
    @discord.ui.button(label="💰 Bán Cá Vừa Câu", style=discord.ButtonStyle.green)
    async def sell_caught_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sell only the fish just caught"""
        # Only allow the user who caught the fish to sell
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            print(f"[FISHING] User {interaction.user.name} selling caught fish: {self.caught_items}")
            
            # Calculate money (NO boost multiplier anymore)
            total_money = 0
            
            for fish_key, quantity in self.caught_items.items():
                fish_info = ALL_FISH.get(fish_key)
                if fish_info:
                    base_price = fish_info['sell_price']
                    total_money += base_price * quantity
            
            print(f"[FISHING] Total money: {total_money}")
            
            # Remove items from inventory
            for fish_key, quantity in self.caught_items.items():
                await remove_item(self.user_id, fish_key, quantity)
                print(f"[FISHING] Removed {quantity}x {fish_key} from inventory")
            
            # Add money
            await add_seeds(self.user_id, total_money)
            print(f"[FISHING] Added {total_money} seeds to user {self.user_id}")
            
            # Clean up
            if self.user_id in self.cog.caught_items:
                del self.cog.caught_items[self.user_id]
            
            # Send result
            fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
            embed = discord.Embed(
                title=f"**{interaction.user.name}** đã bán {sum(self.caught_items.values())} con cá",
                description=f"\n{fish_summary}\n**Nhận: {total_money} Hạt**",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
            # Disable button after sell
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            print(f"[FISHING] ✅ Sell completed successfully")
            
        except Exception as e:
            print(f"[FISHING] ❌ ERROR selling fish: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)
            except:
                pass

class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fishing_cooldown = {}  # {user_id: timestamp}
        self.caught_items = {}  # {user_id: {item_key: quantity}} - temporarily store caught items
        self.user_titles = {}  # {user_id: title} - cache danh hiệu người dùng
        
        # Achievement tracking
        self.user_stats = {}  # {user_id: {stat_key: value}} - track user statistics
        self.user_achievements = {}  # {user_id: [achievement_keys]} - unlocked achievements
        self.lucky_buff_users = {}  # {user_id: True} - sixth_sense buff cache
        self.avoid_event_users = {}  # {user_id: True} - lucky buff cache
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def track_caught_fish(self, user_id: int, fish_key: str):
        """Track that user caught this fish type for collection book"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if already caught
                async with db.execute(
                    "SELECT id FROM fish_collection WHERE user_id = ? AND fish_key = ?",
                    (user_id, fish_key)
                ) as cursor:
                    exists = await cursor.fetchone()
                
                if not exists:
                    # Add to collection
                    await db.execute(
                        "INSERT INTO fish_collection (user_id, fish_key, caught_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        (user_id, fish_key)
                    )
                    await db.commit()
                    print(f"[COLLECTION] {user_id} added {fish_key} to collection")
                    return True  # Lần đầu bắt loại này
        except Exception as e:
            print(f"[COLLECTION] Error tracking fish: {e}")
            # Create table nếu không tồn tại
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS fish_collection (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            fish_key TEXT NOT NULL,
                            caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, fish_key)
                        )
                    """)
                    await db.commit()
                    # Thử lại
                    return await self.track_caught_fish(user_id, fish_key)
            except Exception as e2:
                print(f"[COLLECTION] Failed to create table: {e2}")
        
        return False
    
    async def get_collection(self, user_id: int) -> dict:
        """Get user's fish collection"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    """SELECT fish_key, caught_at FROM fish_collection 
                       WHERE user_id = ? ORDER BY caught_at""",
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return {row[0]: row[1] for row in rows}
        except:
            return {}
    
    async def check_collection_complete(self, user_id: int) -> bool:
        """Check if user caught all fish types"""
        collection = await self.get_collection(user_id)
        all_fish_keys = set(COMMON_FISH_KEYS + RARE_FISH_KEYS)
        caught_keys = set(collection.keys())
        return all_fish_keys.issubset(caught_keys)
    
    async def add_title(self, user_id: int, guild_id: int, title: str):
        """Add title to user by assigning Discord role"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                print(f"[TITLE] Guild {guild_id} not found")
                return
            
            user = guild.get_member(user_id)
            if not user:
                print(f"[TITLE] User {user_id} not found in guild {guild_id}")
                return
            
            # Get the role (1450409414111658024)
            role_id = 1450409414111658024
            role = guild.get_role(role_id)
            if not role:
                print(f"[TITLE] Role {role_id} not found in guild {guild_id}")
                return
            
            # Add role to user
            await user.add_roles(role)
            self.user_titles[user_id] = title
            print(f"[TITLE] Added role '{role.name}' to user {user_id}")
        except Exception as e:
            print(f"[TITLE] Error adding title: {e}")
    
    async def get_title(self, user_id: int, guild_id: int) -> str:
        """Get user's title by checking if they have the role"""
        if user_id in self.user_titles:
            return self.user_titles[user_id]
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return ""
            
            user = guild.get_member(user_id)
            if not user:
                return ""
            
            # Check if user has the role (1450409414111658024)
            role_id = 1450409414111658024
            role = guild.get_role(role_id)
            if role and role in user.roles:
                title = "👑 Vua Câu Cá 👑"
                self.user_titles[user_id] = title
                return title
        except Exception as e:
            print(f"[TITLE] Error getting title: {e}")
        
        return ""
    
    async def trigger_random_event(self, user_id: int, guild_id: int) -> dict:
        """Trigger random event during fishing - returns event_type and result"""
        # Default result dict
        result = {
            "triggered": False, "type": None, "message": "",
            "lose_worm": False, "lose_catch": False, "lose_money": 0, "gain_money": 0,
            "cooldown_increase": 0,
            "catch_multiplier": 1,  # Mặc định x1
            "convert_to_trash": False,  # Mặc định False
            "gain_items": {},  # Item nhận được thêm
            "custom_effect": None  # Cho các effect đặc biệt
        }
        
        # Roll for random event
        rand = random.random()
        current_chance = 0
        
        for event_type, event_data in RANDOM_EVENTS.items():
            current_chance += event_data["chance"]
            if rand < current_chance:
                # Event triggered!
                print(f"[EVENT] {event_type} triggered for user {user_id}")
                
                # Build result dict with event data
                result["triggered"] = True
                result["type"] = event_type
                result["message"] = f"{event_data['name']} {RANDOM_EVENT_MESSAGES[event_type]}"
                
                # --- BAD EVENTS (10) ---
                if event_type == "snapped_line":
                    result["lose_worm"] = True
                    result["lose_catch"] = True
                    
                elif event_type == "police_fine":
                    result["lose_money"] = 50
                    
                elif event_type == "predator":
                    result["lose_worm"] = True
                    result["lose_catch"] = True
                    
                elif event_type == "dropped_slipper":
                    result["cooldown_increase"] = 120  # Phạt thêm 2 phút
                    
                elif event_type == "mom_called":
                    result["lose_catch"] = True  # Mất cá nhưng ko mất mồi thêm
                    
                elif event_type == "cat_steal":
                    result["custom_effect"] = "cat_steal"  # Xử lý riêng: mất cá to nhất
                    
                elif event_type == "broken_phone":
                    result["lose_money"] = 200
                    
                elif event_type == "sea_sickness":
                    result["custom_effect"] = "lose_all_bait"  # Xóa sạch mồi
                    
                elif event_type == "snake_bite":
                    # Trừ 5% tài sản
                    result["custom_effect"] = "snake_bite"
                    
                elif event_type == "plastic_trap":
                    result["lose_catch"] = True
                    result["cooldown_increase"] = 180  # Thêm 3 phút
                
                # --- GOOD EVENTS (10) ---
                elif event_type == "found_wallet":
                    result["gain_money"] = random.randint(50, 150)
                    
                elif event_type == "fairy_gift":
                    result["gain_items"] = {"worm": 5}
                    
                elif event_type == "double_rainbow":
                    result["custom_effect"] = "lucky_buff"  # Buff may mắn lần sau
                    
                elif event_type == "tourist_tip":
                    result["gain_money"] = 100
                    
                elif event_type == "golden_turtle":
                    result["cooldown_increase"] = -30  # Xóa cooldown (về 0)
                    
                elif event_type == "school_of_fish":
                    result["catch_multiplier"] = 3
                    
                elif event_type == "engagement_ring":
                    result["gain_money"] = 300
                    
                elif event_type == "ancient_vase":
                    result["gain_money"] = 500
                    
                elif event_type == "sixth_sense":
                    result["custom_effect"] = "sixth_sense"  # Tránh được xui lần sau
                    
                elif event_type == "treasure_shipwreck":
                    result["gain_items"] = {"treasure_chest": 2}
                
                return result
        
        # No event
        return {"triggered": False}
    
    async def check_achievement(self, user_id: int, achievement_key: str, channel: discord.TextChannel = None, guild_id: int = None):
        """Check and award achievement if conditions are met"""
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = []
        
        # Skip if already earned
        if achievement_key in self.user_achievements[user_id]:
            return False
        
        achievement = ACHIEVEMENTS.get(achievement_key)
        if not achievement:
            return False
        
        # Check if conditions are met (simplified version)
        # Full implementation would check self.user_stats[user_id]
        if achievement_key == "collection_master":
            # This is checked separately in _fish_action
            self.user_achievements[user_id].append(achievement_key)
            
            # Award role if specified
            if achievement.get("role_id") and guild_id:
                try:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        user = guild.get_member(user_id)
                        role = guild.get_role(achievement["role_id"])
                        if user and role:
                            await user.add_roles(role)
                            print(f"[ACHIEVEMENT] {user_id} awarded role '{role.name}' for achievement '{achievement_key}'")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error awarding role for {achievement_key}: {e}")
            
            # Send announcement
            if channel:
                embed = discord.Embed(
                    title=f"🏆 THÀNH TỰU: {achievement['emoji']} {achievement['name']}",
                    description=achievement['description'],
                    color=discord.Color.gold()
                )
                embed.add_field(name="Phần Thưởng", value=f"+{achievement['reward_coins']} Hạt", inline=False)
                if achievement.get("role_id"):
                    embed.add_field(name="🎖️ Role Cấp", value=f"Bạn đã nhận được role thành tựu!", inline=False)
                await channel.send(embed=embed)
            return True
        
        return False
    
    async def update_user_stat(self, user_id: int, stat_key: str, value: int, operation: str = "add"):
        """Update user statistics for achievements"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {}
        
        current_value = self.user_stats[user_id].get(stat_key, 0)
        
        if operation == "add":
            self.user_stats[user_id][stat_key] = current_value + value
        elif operation == "set":
            self.user_stats[user_id][stat_key] = value
        
        return self.user_stats[user_id][stat_key]
    
    async def get_tree_boost_status(self, guild_id: int) -> bool:
        """Check if server tree is at max level (nở hoa/kết trái)"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT level FROM server_tree WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] >= 5:  # Level 5+ = boost
                        return True
        except:
            pass
        return False
    
    async def get_loot_table(self, guild_id: int) -> dict:
        """Get loot table based on tree status"""
        is_boosted = await self.get_tree_boost_status(guild_id)
        return LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
    
    async def roll_loot(self, guild_id: int) -> str:
        """Roll kết quả câu cá"""
        table = await self.get_loot_table(guild_id)
        items = list(table.keys())
        weights = list(table.values())
        return random.choices(items, weights=weights, k=1)[0]
    
    async def add_inventory_item(self, user_id: int, item_name: str, item_type: str):
        """Add item to inventory with type tracking"""
        await add_item(user_id, item_name, 1)
        
        # Also update item_type in DB (extension)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE inventory SET type = ? WHERE user_id = ? AND item_name = ?",
                    (item_type, user_id, item_name)
                )
                await db.commit()
        except:
            pass  # Fallback: type column might not exist yet
    
    async def get_fishing_cooldown_remaining(self, user_id: int) -> int:
        """Get remaining cooldown in seconds"""
        if user_id not in self.fishing_cooldown:
            return 0
        
        cooldown_until = self.fishing_cooldown[user_id]
        remaining = max(0, cooldown_until - time.time())
        return int(remaining)
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="cauca", description="Câu cá - cooldown 30s")
    async def fish_slash(self, interaction: discord.Interaction):
        """Fish via slash command"""
        await self._fish_action(interaction)
    
    @commands.command(name="cauca", description="Câu cá - cooldown 30s")
    async def fish_prefix(self, ctx):
        """Fish via prefix command"""
        await self._fish_action(ctx)
    
    async def _fish_action(self, ctx_or_interaction):
        """Main fishing logic - roll loot 1-5 times per cast"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            channel = ctx_or_interaction.channel
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            channel = ctx_or_interaction.channel
            ctx = ctx_or_interaction
        
        # Check cooldown
        remaining = await self.get_fishing_cooldown_remaining(user_id)
        if remaining > 0:
            msg = f"⏱️ Cần chờ {remaining}s nữa mới được câu lại!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Ensure user exists
        username = ctx.author.name if not is_slash else ctx_or_interaction.user.name
        await get_or_create_user(user_id, username)
        
        # --- LOGIC MỚI: AUTO-BUY MỒI NẾU CÓ ĐỦ TIỀN ---
        inventory = await get_inventory(user_id)
        has_worm = inventory.get("worm", 0) > 0
        auto_bought = False  # Biến check xem có tự mua không

        # Nếu không có mồi, kiểm tra xem có đủ tiền mua không
        if not has_worm:
            balance = await get_user_balance(user_id)
            if balance >= WORM_COST:
                # Tự động trừ tiền coi như mua mồi dùng ngay
                await add_seeds(user_id, -WORM_COST)
                has_worm = True
                auto_bought = True
                print(f"[FISHING] {username} auto-bought worm (-{WORM_COST} seeds)")
            else:
                # Không có mồi, cũng không đủ tiền -> Chấp nhận câu rác
                has_worm = False
        else:
            # Có mồi trong túi -> Trừ mồi
            await remove_item(user_id, "worm", 1)
            print(f"[FISHING] {username} consumed 1 worm from inventory")
        
        # --- KẾT THÚC LOGIC MỚI ---
        
        print(f"[FISHING] {username} started fishing (user_id={user_id}) [has_worm={has_worm}] [auto_bought={auto_bought}]")
        
        # Set cooldown
        self.fishing_cooldown[user_id] = time.time() + 30
        
        # Casting animation
        wait_time = random.randint(1, 5)
        
        # Thêm thông báo nhỏ nếu tự mua mồi hoặc không có mồi
        status_text = ""
        if auto_bought:
            status_text = f"\n💸 *(-{WORM_COST} Hạt mua mồi)*"
        elif not has_worm:
            status_text = "\n⚠️ *Không có mồi (Tỉ lệ rác cao)*"

        casting_msg = await channel.send(
            f"🎣 **{username}** quăng cần... Chờ cá cắn câu... ({wait_time}s){status_text}"
        )
        await asyncio.sleep(wait_time)
        
        # ==================== TRIGGER RANDOM EVENTS ====================
        event_result = await self.trigger_random_event(user_id, channel.guild.id)
        
        if event_result.get("triggered", False):
            # Random event occurred!
            event_message = event_result["message"]
            event_type = event_result.get("type")
            
            # Process event effects
            if event_result.get("lose_worm", False) and has_worm:
                await remove_item(user_id, "worm", 1)
                event_message += " (Mất 1 Giun)"
            
            if event_result.get("lose_money", 0) > 0:
                await add_seeds(user_id, -event_result["lose_money"])
                event_message += f" (-{event_result['lose_money']} Hạt)"
            
            if event_result.get("gain_money", 0) > 0:
                await add_seeds(user_id, event_result["gain_money"])
                event_message += f" (+{event_result['gain_money']} Hạt)"
            
            # Process gain_items (pearls, worms, chests, etc.)
            if event_result.get("gain_items", {}):
                for item_key, item_count in event_result["gain_items"].items():
                    await add_item(user_id, item_key, item_count)
                    item_name = ALL_FISH.get(item_key, {}).get("name", item_key)
                    event_message += f" (+{item_count} {item_name})"
            
            # Handle special effects
            if event_result.get("custom_effect") == "lose_all_bait":
                # sea_sickness: Mất hết mồi
                inventory = await get_inventory(user_id)
                worm_count = inventory.get("worm", 0)
                if worm_count > 0:
                    await remove_item(user_id, "worm", worm_count)
                    event_message += f" (Nôn hết {worm_count} Giun)"
                    print(f"[EVENT] {username} lost all {worm_count} worms from sea_sickness")
            
            elif event_result.get("custom_effect") == "cat_steal":
                # Mèo Mun: Cướp con cá to nhất (giá cao nhất)
                # Điều này sẽ xử lý ở phần sau trong catch result
                pass
            
            elif event_result.get("custom_effect") == "snake_bite":
                # Rắn Nước: Trừ 5% tài sản
                balance = await get_user_balance(user_id)
                penalty = max(10, int(balance * 0.05))  # Min 10 Hạt
                await add_seeds(user_id, -penalty)
                event_message += f" (Trừ 5% tài sản: {penalty} Hạt)"
                print(f"[EVENT] {username} lost 5% assets ({penalty} Hạt) from snake_bite")
            
            elif event_result.get("custom_effect") == "lucky_buff":
                # Cầu Vồng Đôi: Buff may mắn cho lần sau (cá hiếm chắc chắn)
                # Lưu vào cache (tạm thời cho lần tiếp theo)
                if not hasattr(self, "lucky_buff_users"):
                    self.lucky_buff_users = {}
                self.lucky_buff_users[user_id] = True
                event_message += " (Lần câu sau chắc ra Cá Hiếm!)"
                print(f"[EVENT] {username} received lucky buff for next cast")
            
            elif event_result.get("custom_effect") == "sixth_sense":
                # Giác Thứ 6: Tránh xui lần sau (bỏ qua event tiếp theo)
                if not hasattr(self, "avoid_event_users"):
                    self.avoid_event_users = {}
                self.avoid_event_users[user_id] = True
                event_message += " (Lần sau tránh xui!)"
                print(f"[EVENT] {username} will avoid bad event on next cast")
            
            # Adjust cooldown (golden_turtle có thể là -30 để reset)
            if event_result.get("cooldown_increase", 0) != 0:
                if event_result["cooldown_increase"] < 0:
                    # Reset cooldown (golden_turtle)
                    self.fishing_cooldown[user_id] = time.time()
                    event_message += " (Cooldown xóa sạch!)"
                    print(f"[EVENT] {username} cooldown reset")
                else:
                    self.fishing_cooldown[user_id] = time.time() + 30 + event_result["cooldown_increase"]
            else:
                self.fishing_cooldown[user_id] = time.time() + 30
            
            # If lose_catch, don't process fishing
            if event_result.get("lose_catch", False):
                embed = discord.Embed(
                    title=f"⚠️ THẢM HỌA - {username}!",
                    description=event_message,
                    color=discord.Color.red()
                )
                await casting_msg.edit(content="", embed=embed)
                print(f"[EVENT] {username} triggered {event_type} - fishing cancelled")
                return
            
            # Otherwise, display event message and continue fishing
            color = discord.Color.green() if "gain" in event_type or event_type in ["double_rainbow", "sixth_sense", "golden_turtle", "school_of_fish"] else discord.Color.orange()
            embed = discord.Embed(
                title=f"⚠️ SỰ KIỆN - {username}!",
                description=event_message,
                color=color
            )
            await casting_msg.edit(content="", embed=embed)
            
            # Wait a bit before showing catch
            await asyncio.sleep(1)
            casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
        # ==================== NORMAL FISHING PROCESSING ====================
        
        # Roll số lượng cá (1-5) với tỉ lệ giảm dần
        num_fish = random.choices([1, 2, 3, 4, 5], weights=CATCH_COUNT_WEIGHTS, k=1)[0]
        
        # Apply catch multiplier from events (e.g., Golden Hook)
        multiplier = event_result.get("catch_multiplier", 1)
        original_num_fish = num_fish
        num_fish = num_fish * multiplier
        if multiplier > 1:
            print(f"[EVENT] {username} activated catch_multiplier x{multiplier}: {original_num_fish} → {num_fish} fish")
        
        # Roll trash (độc lập)
        trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
        
        # Roll chest (độc lập, tỉ lệ thấp)
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        chest_weights = [95, 5] if not is_boosted else [90, 10]
        chest_count = random.choices([0, 1], weights=chest_weights, k=1)[0]
        
        results = {"fish": num_fish}
        if trash_count > 0:
            results["trash"] = trash_count
        if chest_count > 0:
            results["chest"] = chest_count
        
        print(f"[FISHING] {username} rolled: {num_fish} fish, {trash_count} trash, {chest_count} chest")
        
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        boost_text = " ✨**(CÂY BUFF!)**✨" if is_boosted else ""
        
        # Track caught items for sell button
        self.caught_items[user_id] = {}
        
        # Build summary display and process all results
        fish_display = []
        fish_only_items = {}
        
        # FIX: Track if rare fish already caught this turn (Max 1 rare per cast)
        caught_rare_this_turn = False
        
        # Chọn loot table dựa trên có worm hay không
        if has_worm:
            # Có mồi = dùng loot table bình thường (có cả cá hiếm)
            loot_table = LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
        else:
            # Không có mồi = dùng loot table giảm cực (chỉ rác và cá thường)
            loot_table = LOOT_TABLE_NO_WORM
        
        # Process fish - roll loại cá cho mỗi con
        # CHÚ Ý: Boost KHÔNG tăng tỷ lệ Cá Hiếm, chỉ tăng tỷ lệ Rương để balance
        for _ in range(num_fish):
            # Roll từ LOOT_TABLE để xác định loại (Rare vs Common)
            # Normalize weights để lấy tỉ lệ common vs rare
            fish_weights_sum = loot_table["common_fish"] + loot_table["rare_fish"]
            
            # Nếu không có mồi, fish_weights_sum = 30 + 0 = 30
            # Lúc này common_ratio = 100%, rare_ratio = 0% (không bao giờ rare)
            if fish_weights_sum == 0:
                # Nếu không có cá nào trong loot table (chỉ có rác/rương)
                common_ratio = 1.0
                rare_ratio = 0.0
            else:
                common_ratio = loot_table["common_fish"] / fish_weights_sum
                rare_ratio = loot_table["rare_fish"] / fish_weights_sum
            
            is_rare = random.choices([False, True], weights=[common_ratio, rare_ratio], k=1)[0]
            
            # Check if convert_to_trash event is active (e.g., Pollution)
            if event_result.get("convert_to_trash", False):
                # Convert fish to trash
                trash = random.choice(TRASH_ITEMS)
                item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                await self.add_inventory_item(user_id, item_key, "trash")
                print(f"[EVENT-POLLUTION] {username} fish converted to trash: {item_key}")
                continue
            
            # FIX: Nếu đã bắt rare rồi hoặc roll ra rare lần này nhưng đã bắt rare trước -> bắt buộc common
            if is_rare and not caught_rare_this_turn:
                fish = random.choice(RARE_FISH)
                caught_rare_this_turn = True  # Đánh dấu đã bắt rare
                print(f"[FISHING] {username} caught RARE fish: {fish['key']} ✨ (Max 1 rare per cast)")
                await self.add_inventory_item(user_id, fish['key'], "fish")
                # Track in collection
                is_new_collection = await self.track_caught_fish(user_id, fish['key'])
                if is_new_collection:
                    print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                if fish['key'] not in fish_only_items:
                    fish_only_items[fish['key']] = 0
                fish_only_items[fish['key']] += 1
            else:
                # Bắt cá thường (hoặc roll rare lần 2+ thì buộc common)
                fish = random.choice(COMMON_FISH)
                print(f"[FISHING] {username} caught common fish: {fish['key']}")
                await self.add_inventory_item(user_id, fish['key'], "fish")
                # Track in collection
                is_new_collection = await self.track_caught_fish(user_id, fish['key'])
                if is_new_collection:
                    print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                if fish['key'] not in fish_only_items:
                    fish_only_items[fish['key']] = 0
                fish_only_items[fish['key']] += 1
        
        # Display fish grouped
        for key, qty in fish_only_items.items():
            fish = ALL_FISH[key]
            emoji = fish['emoji']
            total_price = fish['sell_price'] * qty  # Multiply price by quantity
            fish_display.append(f"{emoji} {fish['name']} x{qty} ({total_price} Hạt)")
        
        # Process trash (độc lập)
        if trash_count > 0:
            trash_items_caught = {}
            for _ in range(trash_count):
                trash = random.choice(TRASH_ITEMS)
                item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                await self.add_inventory_item(user_id, item_key, "trash")
                if item_key not in trash_items_caught:
                    trash_items_caught[item_key] = 0
                trash_items_caught[item_key] += 1
            
            for key, qty in trash_items_caught.items():
                trash_name = key.replace("trash_", "").replace("_", " ").title()
                fish_display.append(f"🥾 {trash_name} x{qty}")
            print(f"[FISHING] {username} caught trash: {trash_items_caught}")
        
        # Process chest (độc lập)
        if chest_count > 0:
            for _ in range(chest_count):
                await self.add_inventory_item(user_id, "treasure_chest", "tool")
            fish_display.append(f"🎁 Rương Kho Báu x{chest_count}")
            print(f"[FISHING] {username} caught {chest_count}x TREASURE CHEST! 🎁")
        
        # Store only fish for the sell button
        self.caught_items[user_id] = fish_only_items
        print(f"[FISHING] {username} final caught items: {fish_only_items}")
        
        # Handle cat_steal event: Remove most valuable fish
        if event_result.get("custom_effect") == "cat_steal" and fish_only_items:
            # Find the fish with highest price
            most_valuable_fish = None
            highest_price = -1
            for fish_key, qty in fish_only_items.items():
                fish_info = ALL_FISH.get(fish_key, {})
                price = fish_info.get('sell_price', 0)
                if price > highest_price and qty > 0:
                    highest_price = price
                    most_valuable_fish = fish_key
            
            if most_valuable_fish:
                # Remove 1 of the most valuable fish
                await remove_item(user_id, most_valuable_fish, 1)
                fish_info = ALL_FISH[most_valuable_fish]
                fish_display = [line for line in fish_display if fish_info['name'] not in line]
                fish_only_items[most_valuable_fish] -= 1
                if fish_only_items[most_valuable_fish] == 0:
                    del fish_only_items[most_valuable_fish]
                
                # Update display
                if fish_only_items:
                    for key, qty in fish_only_items.items():
                        if qty > 0:
                            fish = ALL_FISH[key]
                            total_price = fish['sell_price'] * qty
                            fish_display.append(f"{fish['emoji']} {fish['name']} x{qty} ({total_price} Hạt)")
                
                print(f"[EVENT] {username} lost {fish_info['name']} to cat_steal")
                # Add cat message to display
                if fish_display:
                    fish_display[0] = fish_display[0] + f"\n(🐈 Mèo cướp mất {fish_info['name']} giá {highest_price} Hạt!)"
        
        # Update caught items for sell button
        self.caught_items[user_id] = fish_only_items
        
        # Check if collection is complete and award title if needed
        is_complete = await self.check_collection_complete(user_id)
        title_earned = False
        if is_complete:
            current_title = await self.get_title(user_id, channel.guild.id)
            if not current_title or "Vua" not in current_title:
                await self.add_title(user_id, channel.guild.id, "👑 Vua Câu Cá 👑")
                title_earned = True
                print(f"[TITLE] {username} earned 'Vua Câu Cá' title!")
        
        # Build embed with item summary
        total_catches = num_fish + trash_count + chest_count
        
        # Create summary text for title
        summary_parts = []
        for key, qty in fish_only_items.items():
            fish = ALL_FISH[key]
            summary_parts.append(f"{qty} {fish['name']}")
        if chest_count > 0:
            summary_parts.append(f"{chest_count} Rương")
        
        summary_text = " và ".join(summary_parts) if summary_parts else "Rác"
        title = f"🎣 {username} Câu Được {summary_text}"
        
        if num_fish > 2:
            title = f"🎣 BIG HAUL! {username} Bắt {num_fish} Con Cá! 🎉"
        
        # Add title-earned message if applicable
        if title_earned:
            title = f"🎣 {title}\n👑 **DANH HIỆU: VUA CÂU CÁ ĐƯỢC MỞ KHÓA!** 👑"
        
        embed = discord.Embed(
            title=title,
            description="\n".join(fish_display) if fish_display else "Không có gì",
            color=discord.Color.gold() if title_earned else (discord.Color.blue() if total_catches == 1 else discord.Color.gold())
        )
        
        if title_earned:
            embed.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã bắt được **tất cả các loại cá**!\nChúc mừng bạn trở thành **Vua Câu Cá**! 🎉\nXem `/suutapca` để xác nhận!",
                inline=False
            )
        
        embed.set_footer(text=f"Tổng câu được: {total_catches} vật{boost_text}")
        
        # Create view with sell button if there are fish to sell
        view = None
        if fish_only_items:
            view = FishSellView(self, user_id, fish_only_items, channel.guild.id)
            print(f"[FISHING] Created sell button for {username} with {len(fish_only_items)} fish types")
        else:
            print(f"[FISHING] No fish to sell, button not shown")
        
        await casting_msg.edit(content="", embed=embed, view=view)
        print(f"[FISHING] ✅ Fishing result posted for {username}")
    
    
    @app_commands.command(name="banca", description="Bán cá - dùng /banca cá_rô hoặc /banca cá_rô, cá_chép")
    @app_commands.describe(fish_types="Loại cá (cá_rô, cá_chép, cá_koi) - phân cách bằng dấu phẩy để bán nhiều loại")
    async def sell_fish_slash(self, interaction: discord.Interaction, fish_types: str = None):
        """Sell selected fish via slash command"""
        await self._sell_fish_action(interaction, fish_types)
    
    @commands.command(name="banca", description="Bán cá - dùng !banca cá_rô hoặc !banca cá_rô, cá_chép")
    async def sell_fish_prefix(self, ctx, *, fish_types: str = None):
        """Sell selected fish via prefix command"""
        await self._sell_fish_action(ctx, fish_types)
    
    async def _sell_fish_action(self, ctx_or_interaction, fish_types: str = None):
        """Sell all fish or specific types logic with RANDOM EVENTS"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Filter fish items by type
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH}
        
        if not fish_items:
            msg = "❌ Bạn không có cá nào để bán!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Parse fish_types if specified
        selected_fish = None
        if fish_types:
            requested = [f.strip().lower().replace(" ", "_") for f in fish_types.split(",")]
            selected_fish = {k: v for k, v in fish_items.items() if k in requested}
            
            if not selected_fish:
                available = ", ".join(fish_items.keys())
                msg = f"❌ Không tìm thấy cá!\nCá bạn có: {available}"
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
        else:
            selected_fish = fish_items
        
        # 1. Tính tổng tiền gốc
        base_total = 0
        for fish_key, quantity in selected_fish.items():
            fish_info = ALL_FISH.get(fish_key)
            if fish_info:
                base_price = fish_info['sell_price']
                base_total += base_price * quantity
        
        # 2. Xử lý sự kiện bán hàng (Sell Event)
        final_total = base_total
        event_msg = ""
        event_name = ""
        event_color = discord.Color.green()  # Mặc định màu xanh lá
        
        # Roll event
        rand = random.random()
        current_chance = 0
        triggered_event = None
        
        for ev_key, ev_data in SELL_EVENTS.items():
            current_chance += ev_data["chance"]
            if rand < current_chance:
                triggered_event = ev_key
                break
        
        # Apply event logic
        if triggered_event:
            ev_data = SELL_EVENTS[triggered_event]
            event_name = ev_data["name"]
            
            # Tính toán tiền sau sự kiện
            # Công thức: (Gốc * Multiplier) + Flat Bonus
            final_total = int(base_total * ev_data["mul"]) + ev_data["flat"]
            
            # Đảm bảo không bị âm tiền
            if final_total < 0: 
                final_total = 0
            
            diff = final_total - base_total
            sign = "+" if diff >= 0 else ""
            
            # Formatting message
            if ev_data["type"] == "good":
                event_color = discord.Color.gold()
                event_msg = f"\n🌟 **SỰ KIỆN: {event_name}**\n_{SELL_MESSAGES[triggered_event]}_\n👉 **Biến động:** {sign}{diff} Hạt"
            else:
                event_color = discord.Color.orange()
                event_msg = f"\n⚠️ **SỰ CỐ: {event_name}**\n_{SELL_MESSAGES[triggered_event]}_\n👉 **Thiệt hại:** {diff} Hạt"
                
            print(f"[SELL EVENT] {ctx.user.name if is_slash else ctx.author.name} triggered {triggered_event}: {base_total} -> {final_total}")

        # 3. Remove items & Add money
        for fish_key in selected_fish.keys():
            await remove_item(user_id, fish_key, selected_fish[fish_key])
        
        await add_seeds(user_id, final_total)
        
        # 4. Gửi kết quả
        fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in selected_fish.items()])
        username = ctx.user.name if is_slash else ctx.author.name
        
        embed = discord.Embed(
            title=f"💰 **{username}** bán {sum(selected_fish.values())} con cá",
            description=f"{fish_summary}\n\n💵 **Tổng gốc:** {base_total} Hạt{event_msg}",
            color=event_color
        )
        
        # Hiển thị số thực nhận to rõ
        embed.add_field(name="THỰC NHẬN", value=f"**{final_total} Hạt**", inline=False)
        
        # Check achievement "millionaire" (Tích lũy tiền)
        if hasattr(self, "update_user_stat"):
            total_earned = await self.update_user_stat(user_id, "coins_earned", final_total)
            if total_earned >= 100000:
                await self.check_achievement(user_id, "millionaire", ctx.channel, ctx.guild.id if hasattr(ctx, 'guild') else ctx_or_interaction.guild.id)

        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    
    @app_commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_slash(self, interaction: discord.Interaction):
        """Open chest via slash command"""
        await self._open_chest_action(interaction)
    
    @commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_prefix(self, ctx):
        """Open chest via prefix command"""
        await self._open_chest_action(ctx)
    
    async def _open_chest_action(self, ctx_or_interaction):
        """Open treasure chest logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Check if user has chest
        inventory = await get_inventory(user_id)
        if inventory.get("treasure_chest", 0) <= 0:
            msg = "❌ Bạn không có Rương Kho Báu!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove chest from inventory
        await remove_item(user_id, "treasure_chest", 1)
        
        # Roll loot
        items = list(CHEST_LOOT.keys())
        weights = list(CHEST_LOOT.values())
        loot_type = random.choices(items, weights=weights, k=1)[0]
        
        # Process loot
        if loot_type == "fertilizer":
            await self.add_inventory_item(user_id, "fertilizer", "tool")
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description="**🌾 Phân Bón** (Dùng `/bonphan` để nuôi cây)",
                color=discord.Color.gold()
            )
        
        elif loot_type == "puzzle_piece":
            pieces = ["puzzle_a", "puzzle_b", "puzzle_c", "puzzle_d"]
            piece = random.choice(pieces)
            await self.add_inventory_item(user_id, piece, "tool")
            piece_display = piece.split("_")[1].upper()
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**🧩 Mảnh Ghép {piece_display}** (Gom đủ 4 mảnh A-B-C-D để đổi quà siêu to!)",
                color=discord.Color.blue()
            )
        
        elif loot_type == "coin_pouch":
            coins = random.randint(100, 200)
            await add_seeds(user_id, coins)
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**💰 Túi Hạt** - Bạn nhận được **{coins} Hạt**!",
                color=discord.Color.green()
            )
        
        else:  # gift_random
            gift = random.choice(GIFT_ITEMS)
            await self.add_inventory_item(user_id, gift, "gift")
            gift_names = {"cafe": "☕ Cà Phê", "flower": "🌹 Hoa", "ring": "💍 Nhẫn", 
                         "gift": "🎁 Quà", "chocolate": "🍫 Sô Cô La", "card": "💌 Thiệp"}
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**{gift_names[gift]}** (Dùng `/tangqua` để tặng cho ai đó)",
                color=discord.Color.magenta()
            )
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    # ==================== CRAFT/RECYCLE ====================
    
    @app_commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    @app_commands.describe(
        action="Để trống để xem thông tin, hoặc 'phan' để tạo phân bón"
    )
    async def recycle_trash_slash(self, interaction: discord.Interaction, action: str = None):
        """Recycle trash via slash command"""
        await self._recycle_trash_action(interaction, action)
    
    @commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    async def recycle_trash_prefix(self, ctx, action: str = None):
        """Recycle trash via prefix command"""
        await self._recycle_trash_action(ctx, action)
    
    async def _recycle_trash_action(self, ctx_or_interaction, action: str = None):
        """Recycle trash logic - auto converts 10 trash → 1 fertilizer"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=True)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Count all trash items
        trash_count = sum(qty for key, qty in inventory.items() if key.startswith("trash_"))
        
        if trash_count == 0:
            msg = "❌ Bạn không có rác nào để tái chế!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Check if user has enough trash
        if trash_count < 10:
            msg = f"❌ Bạn cần 10 rác để tạo phân bón, hiện có {trash_count}"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove 10 trash items
        trash_removed = 0
        for key in list(inventory.keys()):
            if key.startswith("trash_") and trash_removed < 10:
                qty_to_remove = min(inventory[key], 10 - trash_removed)
                await remove_item(user_id, key, qty_to_remove)
                trash_removed += qty_to_remove
        
        # Add 1 fertilizer
        await self.add_inventory_item(user_id, "fertilizer", "tool")
        
        embed = discord.Embed(
            title="✅ Tái Chế Thành Công",
            description="10 Rác → 1 🌱 Phân Bón",
            color=discord.Color.green()
        )
        print(f"[RECYCLE] {ctx.author.name if not is_slash else ctx.user.name} recycled 10 trash → 1 fertilizer")
        
        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    
    @app_commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây (tăng 50-100 điểm)")
    async def use_fertilizer_slash(self, interaction: discord.Interaction):
        """Use fertilizer via slash command"""
        await self._use_fertilizer_action(interaction)
    
    @commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây")
    async def use_fertilizer_prefix(self, ctx):
        """Use fertilizer via prefix command"""
        await self._use_fertilizer_action(ctx)
    
    async def _use_fertilizer_action(self, ctx_or_interaction):
        """Use fertilizer logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        guild_id = ctx_or_interaction.guild.id
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            guild_id = ctx_or_interaction.guild.id
            ctx = ctx_or_interaction
        
        # Check if user has fertilizer
        inventory = await get_inventory(user_id)
        if inventory.get("fertilizer", 0) <= 0:
            msg = "❌ Bạn không có Phân Bón!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove fertilizer
        await remove_item(user_id, "fertilizer", 1)
        
        # Add to tree
        boost_amount = random.randint(50, 100)
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE server_tree SET current_progress = current_progress + ? WHERE guild_id = ?",
                    (boost_amount, guild_id)
                )
                await db.commit()
            
            embed = discord.Embed(
                title="🌾 Phân Bón Hiệu Quả!",
                description=f"**+{boost_amount}** điểm cho Cây Server! (Tổng progress tăng)",
                color=discord.Color.green()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi",
                description=f"Không thể cộng điểm: {str(e)}",
                color=discord.Color.red()
            )
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    # ==================== COLLECTION BOOK ====================
    
    @app_commands.command(name="suutapca", description="Xem Bộ Sưu Tập Cá - Câu Đủ Tất Cả Để Thành Vua Câu Cá!")
    async def view_collection_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """View fish collection via slash command"""
        target_user = user or interaction.user
        await self._view_collection_action(interaction, target_user.id, target_user.name)
    
    @commands.command(name="suutapca", description="Xem Bộ Sưu Tập Cá")
    async def view_collection_prefix(self, ctx, user: discord.User = None):
        """View fish collection via prefix command"""
        target_user = user or ctx.author
        await self._view_collection_action(ctx, target_user.id, target_user.name)
    
    async def _view_collection_action(self, ctx_or_interaction, user_id: int, username: str):
        """View collection logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            ctx = ctx_or_interaction
            guild_id = ctx_or_interaction.guild_id
        else:
            ctx = ctx_or_interaction
            guild_id = ctx_or_interaction.guild.id
        
        # Get collection
        collection = await self.get_collection(user_id)
        
        # Separate common and rare
        common_caught = set()
        rare_caught = set()
        
        for fish_key in collection.keys():
            if fish_key in RARE_FISH_KEYS:
                rare_caught.add(fish_key)
            elif fish_key in COMMON_FISH_KEYS:
                common_caught.add(fish_key)
        
        # Get total count
        total_all_fish = len(COMMON_FISH_KEYS + RARE_FISH_KEYS)
        total_caught = len(common_caught) + len(rare_caught)
        completion_percent = int((total_caught / total_all_fish) * 100)
        
        # Check if completed
        is_complete = await self.check_collection_complete(user_id)
        
        # Get current title
        current_title = await self.get_title(user_id, guild_id)
        
        # Build embed
        embed = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_fish}** ({completion_percent}%) ",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        # Add title if has
        if current_title:
            embed.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add common fish section
        common_display = []
        for fish in COMMON_FISH:
            emoji = "✅" if fish['key'] in common_caught else "❌"
            common_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        embed.add_field(
            name=f"🐠 Cá Thường ({len(common_caught)}/{len(COMMON_FISH)})",
            value="\n".join(common_display) if common_display else "Không có",
            inline=False
        )
        
        # Add rare fish section
        rare_display = []
        for fish in RARE_FISH:
            emoji = "✅" if fish['key'] in rare_caught else "❌"
            rare_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        embed.add_field(
            name=f"✨ Cá Hiếm ({len(rare_caught)}/{len(RARE_FISH)})",
            value="\n".join(rare_display) if rare_display else "Không có",
            inline=False
        )
        
        # Add completion message
        if is_complete:
            embed.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã trở thành **👑 VUA CÂU CÁ 👑**!\nCảm ơn sự kiên trì của bạn! 🎉",
                inline=False
            )
        else:
            missing_count = total_all_fish - total_caught
            embed.add_field(
                name="📝 Còn Lại",
                value=f"Bạn còn cần bắt **{missing_count}** loại cá nữa để trở thành Vua Câu Cá! 💪",
                inline=False
            )
        
        embed.set_footer(text="Mỗi lần bắt một loại cá mới, nó sẽ được thêm vào sưu tập của bạn!")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

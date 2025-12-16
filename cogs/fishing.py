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
    # --- Nhóm Giá Rẻ & Cá Đồng (5-7 Hạt) ---
    {"key": "ca_chep", "name": "Cá Chép", "emoji": "🐠", "sell_price": 5},
    {"key": "ca_ro", "name": "Cá Rô Đồng", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_bong", "name": "Cá Bống", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_com", "name": "Cá Cơm", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_moi", "name": "Cá Mòi", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_me", "name": "Cá Mè", "emoji": "⚪", "sell_price": 6},
    {"key": "ca_sac", "name": "Cá Sặc", "emoji": "🐠", "sell_price": 6},
    {"key": "ca_nuc", "name": "Cá Nục", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_bac_ma", "name": "Cá Bạc Má", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_chim", "name": "Cá Chim Trắng", "emoji": "⬜", "sell_price": 7},
    {"key": "ca_lau_kinh", "name": "Cá Lau Kính", "emoji": "🧹", "sell_price": 5}, # Đặc sản sông VN
    {"key": "ca_long_tong", "name": "Cá Lòng Tong", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_bay_trau", "name": "Cá Bảy Trầu", "emoji": "🌈", "sell_price": 6},
    {"key": "ca_ro_phi", "name": "Cá Rô Phi", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_trang", "name": "Cá Trắng", "emoji": "⚪", "sell_price": 5},
    {"key": "ca_linh", "name": "Cá Linh", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_chot", "name": "Cá Chốt", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_diu", "name": "Cá Đù", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_liet", "name": "Cá Liệt", "emoji": "🐟", "sell_price": 5},
    {"key": "ca_phen", "name": "Cá Phèn", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_dong", "name": "Cá Đổng", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_khoai", "name": "Cá Khoai", "emoji": "🥖", "sell_price": 7},
    {"key": "ca_bep", "name": "Cá Bớp", "emoji": "🦈", "sell_price": 7},
    {"key": "ca_son", "name": "Cá Sơn", "emoji": "🔴", "sell_price": 6},
    {"key": "ca_dia", "name": "Cá Dìa", "emoji": "🍃", "sell_price": 7},
    {"key": "ca_kinh", "name": "Cá Kình", "emoji": "🐟", "sell_price": 7},
    {"key": "ca_doi", "name": "Cá Đối", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_nham", "name": "Cá Nhám", "emoji": "🦈", "sell_price": 7},
    {"key": "ca_thoi_loi", "name": "Cá Thòi Lòi", "emoji": "👀", "sell_price": 7},
    {"key": "nong_noc", "name": "Nòng Nọc", "emoji": "⚫", "sell_price": 5},

    # --- Nhóm Tôm/Cua/Ốc Bình Dân (5-8 Hạt) ---
    {"key": "tep_dong", "name": "Tép Đồng", "emoji": "🦐", "sell_price": 5},
    {"key": "oc_buou", "name": "Ốc Bươu", "emoji": "🐚", "sell_price": 6},
    {"key": "oc_lac", "name": "Ốc Lác", "emoji": "🐚", "sell_price": 6},
    {"key": "oc_gao", "name": "Ốc Gạo", "emoji": "🐚", "sell_price": 5},
    {"key": "oc_dang", "name": "Ốc Đắng", "emoji": "🐚", "sell_price": 5},
    {"key": "hen", "name": "Con Hến", "emoji": "🦪", "sell_price": 5},
    {"key": "ngheu", "name": "Con Nghêu", "emoji": "🦪", "sell_price": 6},
    {"key": "chem_chep", "name": "Chem Chép", "emoji": "🦪", "sell_price": 6},
    {"key": "so_long", "name": "Sò Lông", "emoji": "🦪", "sell_price": 7},
    {"key": "so_huyet", "name": "Sò Huyết", "emoji": "🩸", "sell_price": 8},
    {"key": "cua_dong", "name": "Cua Đồng", "emoji": "🦀", "sell_price": 6},
    {"key": "con_ram", "name": "Con Rạm", "emoji": "🦀", "sell_price": 6},
    {"key": "con_cay", "name": "Con Cáy", "emoji": "🦀", "sell_price": 5},
    {"key": "ba_khia", "name": "Ba Khía", "emoji": "🦀", "sell_price": 7},
    {"key": "trung_ca", "name": "Trứng Cá", "emoji": "🫧", "sell_price": 5},

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
    {"key": "ca_tra", "name": "Cá Tra", "emoji": "🐋", "sell_price": 8},
    {"key": "ca_basa", "name": "Cá Basa", "emoji": "🐋", "sell_price": 8},
    {"key": "ca_chim_den", "name": "Cá Chim Đen", "emoji": "⬛", "sell_price": 9},
    {"key": "ca_that_lat", "name": "Cá Thát Lát", "emoji": "🔪", "sell_price": 9},
    {"key": "ca_nganh", "name": "Cá Ngạnh", "emoji": "🐟", "sell_price": 8},
    {"key": "ca_muong", "name": "Cá Mương", "emoji": "🐟", "sell_price": 8},
    {"key": "ca_diec", "name": "Cá Diếc", "emoji": "🐟", "sell_price": 8},
    {"key": "ca_he_vang", "name": "Cá He Vàng", "emoji": "🟡", "sell_price": 9},
    {"key": "ca_me_vinh", "name": "Cá Mè Vinh", "emoji": "🐟", "sell_price": 9},
    {"key": "ca_bup", "name": "Cá Búp", "emoji": "🐟", "sell_price": 8},
    {"key": "ca_neon", "name": "Cá Neon", "emoji": "🚥", "sell_price": 10},
    {"key": "ca_ty_ba", "name": "Cá Tỳ Bà", "emoji": "🎸", "sell_price": 10},
    {"key": "ca_mun", "name": "Cá Mún", "emoji": "🐟", "sell_price": 8},
    {"key": "ca_duoi_nho", "name": "Cá Đuối Nhỏ", "emoji": "🪁", "sell_price": 10},
    {"key": "luon", "name": "Con Lươn", "emoji": "🐍", "sell_price": 10},

    # --- Nhóm Ngon & Đặc Sản (11-15 Hạt) ---
    {"key": "ca_thu", "name": "Cá Thu", "emoji": "🐟", "sell_price": 12},
    {"key": "ca_ngu", "name": "Cá Ngừ", "emoji": "🦈", "sell_price": 12},
    {"key": "ca_mu", "name": "Cá Mú", "emoji": "🐡", "sell_price": 13},
    {"key": "ca_lang", "name": "Cá Lăng", "emoji": "🥖", "sell_price": 14},
    {"key": "ca_chinh", "name": "Cá Chình", "emoji": "🐍", "sell_price": 14},
    {"key": "ca_tai_tuong", "name": "Tai Tượng", "emoji": "👂", "sell_price": 13},
    {"key": "muc_ong", "name": "Mực Ống", "emoji": "🦑", "sell_price": 15},
    {"key": "bach_tuoc", "name": "Bạch Tuộc", "emoji": "🐙", "sell_price": 15},
    {"key": "tom_hum_dat", "name": "Tôm Đất", "emoji": "🦐", "sell_price": 15},
    {"key": "tom_cang_xanh", "name": "Tôm Càng", "emoji": "🦞", "sell_price": 14},
    {"key": "tom_su", "name": "Tôm Sú", "emoji": "🦐", "sell_price": 13},
    {"key": "tom_tit", "name": "Tôm Tít", "emoji": "🦐", "sell_price": 12},
    {"key": "ghe_xanh", "name": "Ghẹ Xanh", "emoji": "🦀", "sell_price": 13},
    {"key": "oc_huong", "name": "Ốc Hương", "emoji": "🐚", "sell_price": 14},
    {"key": "oc_mong_tay", "name": "Ốc Móng Tay", "emoji": "💅", "sell_price": 12},
    {"key": "oc_len", "name": "Ốc Len", "emoji": "🐚", "sell_price": 12},
    {"key": "ech", "name": "Con Ếch", "emoji": "🐸", "sell_price": 11},
    {"key": "ca_bop_bien", "name": "Cá Bớp Biển", "emoji": "🦈", "sell_price": 14},
    {"key": "ca_chach_lau", "name": "Cá Chạch Lấu", "emoji": "🐍", "sell_price": 15},
    {"key": "ca_bong_tuong", "name": "Cá Bống Tượng", "emoji": "🗿", "sell_price": 15},
    {"key": "ca_leo", "name": "Cá Leo", "emoji": "🦈", "sell_price": 13},
    {"key": "ca_chem", "name": "Cá Chẽm", "emoji": "🐟", "sell_price": 13},
    {"key": "ca_bong_mu", "name": "Cá Bống Mú", "emoji": "🐡", "sell_price": 14},
    {"key": "ca_khoai", "name": "Cá Khoai", "emoji": "🐟", "sell_price": 11},
    {"key": "ca_tuyet", "name": "Cá Tuyết", "emoji": "❄️", "sell_price": 15},
    {"key": "muc_la", "name": "Mực Lá", "emoji": "🦑", "sell_price": 15},
    {"key": "muc_sim", "name": "Mực Sim", "emoji": "🦑", "sell_price": 14},
    {"key": "sua", "name": "Con Sứa", "emoji": "🎐", "sell_price": 11},
    {"key": "sam_bien", "name": "Con Sam", "emoji": "🛸", "sell_price": 15},
    {"key": "ca_chich", "name": "Cá Trích", "emoji": "🐟", "sell_price": 11},
]

# 2. CÁ HIẾM (RARE) - Tỉ lệ gặp thấp (~5-10%)
# Giá: 35 - 150 Hạt.
RARE_FISH = [
    # --- Rare Thường: Cá cảnh & Hải sản cao cấp (35-55 Hạt) ---
    {"key": "ca_koi", "name": "Cá Koi", "emoji": "✨🐠", "sell_price": 35},
    {"key": "ca_he", "name": "Cá Hề (Nemo)", "emoji": "🤡", "sell_price": 35},
    {"key": "ca_hoi", "name": "Cá Hồi", "emoji": "🍣", "sell_price": 40},
    {"key": "ca_thien_than", "name": "Thiên Thần", "emoji": "👼", "sell_price": 40},
    {"key": "ca_dia_canh", "name": "Cá Đĩa", "emoji": "💿", "sell_price": 45},
    {"key": "ca_ngua", "name": "Cá Ngựa", "emoji": "🐎", "sell_price": 45},
    {"key": "ca_tam", "name": "Cá Tầm", "emoji": "🦈", "sell_price": 50},
    {"key": "ca_betta", "name": "Betta Rồng", "emoji": "🐉", "sell_price": 50},
    {"key": "ca_la_han", "name": "La Hán", "emoji": "🤯", "sell_price": 55},
    {"key": "ca_hong_ket", "name": "Hồng Két", "emoji": "🦜", "sell_price": 45},
    {"key": "ca_phuong_hoang", "name": "Phượng Hoàng", "emoji": "🐦", "sell_price": 40},
    {"key": "ca_than_tien", "name": "Thần Tiên", "emoji": "🧚", "sell_price": 40},
    {"key": "tom_hum_bong", "name": "Tôm Hùm Bông", "emoji": "🦞", "sell_price": 55},
    {"key": "tom_hum_alaska", "name": "Tôm Alaska", "emoji": "🦞", "sell_price": 55},
    {"key": "cua_hoang_de", "name": "Cua Hoàng Đế", "emoji": "👑", "sell_price": 55},
    {"key": "cua_tuyet", "name": "Cua Tuyết", "emoji": "❄️", "sell_price": 50},
    {"key": "bao_ngu", "name": "Bào Ngư", "emoji": "👂", "sell_price": 50},
    {"key": "hai_sam", "name": "Hải Sâm", "emoji": "🥒", "sell_price": 45},
    {"key": "cau_gai", "name": "Cầu Gai (Nhum)", "emoji": "⚫", "sell_price": 40},
    {"key": "oc_voi_voi", "name": "Ốc Vòi Voi", "emoji": "🐘", "sell_price": 55},
    {"key": "ca_noc", "name": "Cá Nóc", "emoji": "🐡", "sell_price": 50},
    {"key": "ca_bo_giap", "name": "Cá Bò Giáp", "emoji": "🛡️", "sell_price": 45},
    {"key": "ca_su_mi", "name": "Cá Napoleon", "emoji": "🎩", "sell_price": 55},
    {"key": "ca_mo", "name": "Cá Mó (Vẹt)", "emoji": "🦜", "sell_price": 40},
    {"key": "ca_duoi_gai", "name": "Đuối Gai Độc", "emoji": "💉", "sell_price": 50},
    {"key": "ca_hong_vy", "name": "Hồng Vỹ Mỏ Vịt", "emoji": "🦆", "sell_price": 55},
    {"key": "ca_sau_hoa_tien", "name": "Sấu Hỏa Tiễn", "emoji": "🚀", "sell_price": 50},
    {"key": "axolotl", "name": "Kỳ Giông Axolotl", "emoji": "🦎", "sell_price": 55},
    {"key": "rua_xanh", "name": "Rùa Xanh", "emoji": "🐢", "sell_price": 45},
    {"key": "ba_ba", "name": "Con Ba Ba", "emoji": "🐢", "sell_price": 40},

    # --- Rare Xịn: Đại dương & Săn mồi (60-95 Hạt) ---
    {"key": "ca_duoi_dien", "name": "Đuối Điện", "emoji": "⚡", "sell_price": 60},
    {"key": "ca_long_den", "name": "Cá Lồng Đèn", "emoji": "💡", "sell_price": 65},
    {"key": "ca_mat_trang", "name": "Mặt Trăng (Mola)", "emoji": "🌙", "sell_price": 70},
    {"key": "ca_kiem", "name": "Cá Kiếm", "emoji": "⚔️", "sell_price": 75},
    {"key": "ca_rong_ngan", "name": "Ngân Long", "emoji": "🐲", "sell_price": 70},
    {"key": "ca_rong_kim", "name": "Kim Long", "emoji": "🐲", "sell_price": 80},
    {"key": "ca_rong_huyet", "name": "Huyết Long", "emoji": "🐲", "sell_price": 85},
    {"key": "ca_map", "name": "Cá Mập", "emoji": "🦈", "sell_price": 90},
    {"key": "ca_map_bua", "name": "Cá Mập Búa", "emoji": "🔨", "sell_price": 85},
    {"key": "ca_map_ho", "name": "Cá Mập Hổ", "emoji": "🐅", "sell_price": 88},
    {"key": "ca_map_trang", "name": "Cá Mập Trắng", "emoji": "🦷", "sell_price": 95},
    {"key": "ca_duoi_manta", "name": "Đuối Manta", "emoji": "🛸", "sell_price": 85},
    {"key": "ca_ngu_dai_duong", "name": "Ngừ Đại Dương", "emoji": "🌊", "sell_price": 80},
    {"key": "ca_ngu_vay_xanh", "name": "Ngừ Vây Xanh", "emoji": "💎", "sell_price": 95},
    {"key": "ca_ho_khong_lo", "name": "Cá Hô Khổng Lồ", "emoji": "🤯", "sell_price": 90},
    {"key": "ca_anh_vu", "name": "Cá Anh Vũ", "emoji": "💋", "sell_price": 90},
    {"key": "ca_chien", "name": "Cá Chiên Sông Đà", "emoji": "😈", "sell_price": 85},
    {"key": "ca_tra_dau", "name": "Cá Tra Dầu", "emoji": "⛽", "sell_price": 88},
    {"key": "ca_lang_khong_lo", "name": "Lăng Khổng Lồ", "emoji": "🥖", "sell_price": 80},
    {"key": "ca_cop", "name": "Cá Cọp (Tiger)", "emoji": "🐯", "sell_price": 75},
    {"key": "piranha", "name": "Cá Piranha", "emoji": "😬", "sell_price": 60},
    {"key": "muc_khong_lo", "name": "Mực Khổng Lồ", "emoji": "🦑", "sell_price": 80},
    {"key": "bach_tuoc_dom", "name": "Bạch Tuộc Đốm Xanh", "emoji": "☠️", "sell_price": 75},
    {"key": "sua_hop", "name": "Sứa Hộp", "emoji": "📦", "sell_price": 65},
    {"key": "ca_mat_quy", "name": "Cá Mặt Quỷ", "emoji": "👺", "sell_price": 70},
    {"key": "ca_mao_tien", "name": "Cá Mao Tiên", "emoji": "🦁", "sell_price": 65},
    {"key": "ca_co", "name": "Cá Cờ", "emoji": "🚩", "sell_price": 75},
    {"key": "ca_buom", "name": "Cá Buồm", "emoji": "⛵", "sell_price": 78},
    {"key": "luon_dien", "name": "Lươn Điện", "emoji": "⚡", "sell_price": 70},
    {"key": "ran_bien", "name": "Rắn Biển", "emoji": "🐍", "sell_price": 65},
    {"key": "ca_hoang_hau", "name": "Cá Hoàng Hậu", "emoji": "👸", "sell_price": 80},
    {"key": "ca_vampire", "name": "Cá Vampire", "emoji": "🧛", "sell_price": 85},

    # --- LEGENDARY: Thú biển & Thần thoại (100-150+ Hạt) ---
    {"key": "ca_voi_xanh", "name": "Cá Voi Xanh", "emoji": "🐋", "sell_price": 120},
    {"key": "ca_hai_tuong", "name": "Hải Tượng", "emoji": "🦕", "sell_price": 130},
    {"key": "ca_nha_tang", "name": "Cá Nhà Táng", "emoji": "🐳", "sell_price": 150},
    {"key": "ca_heo", "name": "Cá Heo", "emoji": "🐬", "sell_price": 110},
    {"key": "ca_heo_hong", "name": "Cá Heo Hồng", "emoji": "🌸", "sell_price": 115},
    {"key": "ca_voi_sat_thu", "name": "Cá Voi Sát Thủ", "emoji": "🐼", "sell_price": 140},
    {"key": "ky_lan_bien", "name": "Kỳ Lân Biển", "emoji": "🦄", "sell_price": 145},
    {"key": "ca_voi_trang", "name": "Cá Voi Trắng", "emoji": "⚪", "sell_price": 125},
    {"key": "hai_cau", "name": "Hải Cẩu", "emoji": "🦭", "sell_price": 105},
    {"key": "su_tu_bien", "name": "Sư Tử Biển", "emoji": "🦁", "sell_price": 110},
    {"key": "voi_bien", "name": "Voi Biển", "emoji": "🐘", "sell_price": 115},
    {"key": "chim_canh_cut", "name": "Chim Cánh Cụt", "emoji": "🐧", "sell_price": 100},
    {"key": "ca_sau", "name": "Cá Sấu Chúa", "emoji": "🐊", "sell_price": 120},
    {"key": "ha_ma", "name": "Hà Mã", "emoji": "🦛", "sell_price": 130},
    {"key": "rua_da", "name": "Rùa Da", "emoji": "🐢", "sell_price": 120},
    {"key": "rua_hoan_kiem", "name": "Rùa Hoàn Kiếm", "emoji": "🗡️", "sell_price": 200}, # Cực hiếm
    {"key": "megalodon", "name": "Megalodon", "emoji": "🦖", "sell_price": 180},
    {"key": "thuy_quai_kraken", "name": "Kraken", "emoji": "🦑", "sell_price": 190},
    {"key": "thuy_quai_nessie", "name": "Quái Vật Nessie", "emoji": "🦕", "sell_price": 190},
    {"key": "ca_nham_voi", "name": "Cá Nhám Voi", "emoji": "🦈", "sell_price": 135},
    {"key": "ca_mai_cheo", "name": "Cá Mái Chèo", "emoji": "🚣", "sell_price": 125},
    {"key": "ca_blob", "name": "Cá Giọt Nước", "emoji": "💧", "sell_price": 110},
    {"key": "muc_ma", "name": "Mực Ma Cà Rồng", "emoji": "🧛", "sell_price": 130},
    {"key": "bo_bien", "name": "Bò Biển (Dugong)", "emoji": "🐄", "sell_price": 125},
    {"key": "ca_coelacanth", "name": "Cá Vây Tay", "emoji": "🦴", "sell_price": 150},
    {"key": "rong_bien", "name": "Rồng Biển", "emoji": "🐉", "sell_price": 160},
    {"key": "leviathan", "name": "Leviathan", "emoji": "🌊", "sell_price": 250}, # Boss cuối
    {"key": "my_nhan_ngu", "name": "Mỹ Nhân Ngư", "emoji": "🧜‍♀️", "sell_price": 300}, # Easter egg
    {"key": "poseidon", "name": "Đinh Ba Poseidon", "emoji": "🔱", "sell_price": 500}, # Item siêu hiếm
    {"key": "ngoc_trai_den", "name": "Ngọc Trai Đen", "emoji": "🔮", "sell_price": 150},
    {"key": "ruong_kho_bau", "name": "Rương Kho Báu", "emoji": "💰", "sell_price": 200},
    {"key": "ca_than", "name": "Cá Thần", "emoji": "✨", "sell_price": 168},
    {"key": "ca_chay", "name": "Cá Chuồn", "emoji": "✈️", "sell_price": 100},
    {"key": "ca_hot_mit", "name": "Cá Hót Mít", "emoji": "🍘", "sell_price": 105},
    {"key": "ca_vang_khong_lo", "name": "Cá Vàng Giant", "emoji": "🐡", "sell_price": 110},
    {"key": "ca_map_ma", "name": "Cá Mập Ma", "emoji": "👻", "sell_price": 140},
    {"key": "ca_rac", "name": "Cá Rác (Dọn Bể)", "emoji": "🗑️", "sell_price": 1}, # Troll: Hiếm nhưng rẻ
    {"key": "tom_hum_dat_vang", "name": "Tôm Hùm Vàng", "emoji": "🏆", "sell_price": 160},
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

# ==================== TREE NAMES (for level-up notification) ====================
TREE_NAMES = {
    1: "🌱 Hạt mầm",
    2: "🌿 Nảy mầm",
    3: "🎋 Cây non",
    4: "🌳 Trưởng thành",
    5: "🌸 Ra hoa",
    6: "🍎 Kết trái"
}

# ==================== CẦN CÂU (ROD SYSTEM) ====================
# Hệ thống nâng cấp cần câu với Cooldown, Durability, Luck
ROD_LEVELS = {
    1: {"name": "Cần Tre", "cost": 0, "durability": 30, "repair": 50, "cd": 30, "luck": 0.0, "emoji": "🎋"},
    2: {"name": "Cần Thủy Tinh", "cost": 5000, "durability": 50, "repair": 100, "cd": 25, "luck": 0.0, "emoji": "🎣"},
    3: {"name": "Cần Carbon", "cost": 20000, "durability": 80, "repair": 200, "cd": 20, "luck": 0.02, "emoji": "✨🎣"},
    4: {"name": "Cần Hợp Kim", "cost": 50000, "durability": 120, "repair": 500, "cd": 15, "luck": 0.05, "emoji": "🔱"},
    5: {"name": "Cần Poseidon", "cost": 150000, "durability": 200, "repair": 1000, "cd": 10, "luck": 0.10, "emoji": "🔱✨"},
}

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
    # ================= 30 BAD EVENTS (KIẾP NẠN) =================
    # effect: Loại hình phạt (lose_worm, lose_catch, lose_money_*, cooldown_*, durability_hit, lose_turn, lose_all_bait, thief)
    
    # --- Nhóm 1: Mất Mồi & Dây (Cơ bản) ---
    "snapped_line":    {"chance": 0.005, "type": "bad", "name": "Đứt Dây!", "effect": "lose_worm"},
    "hook_stuck":      {"chance": 0.005, "type": "bad", "name": "Mắc Cây!", "effect": "lose_worm"},
    "rat_bite":        {"chance": 0.004, "type": "bad", "name": "Chuột Cắn!", "effect": "lose_worm"},
    "poor_knot":       {"chance": 0.005, "type": "bad", "name": "Tuột Nút!", "effect": "lose_worm"},
    "fish_escape":     {"chance": 0.005, "type": "bad", "name": "Cá Sẩy!", "effect": "lose_worm"},

    # --- Nhóm 2: Mất Cá (Ức chế) ---
    "predator":        {"chance": 0.005, "type": "bad", "name": "Cá Dữ!", "effect": "lose_catch"},
    "cat_steal":       {"chance": 0.005, "type": "bad", "name": "Mèo Mun!", "effect": "thief"},  # Mất cá to nhất
    "bird_steal":      {"chance": 0.004, "type": "bad", "name": "Chim Cướp!", "effect": "lose_catch"},
    "bucket_leak":     {"chance": 0.003, "type": "bad", "name": "Thủng Xô!", "effect": "lose_catch"},
    "otter_troll":     {"chance": 0.003, "type": "bad", "name": "Rái Cá!", "effect": "thief"},

    # --- Nhóm 3: Mất Tiền (Tai nạn tài chính) ---
    "police_fine":     {"chance": 0.004, "type": "bad", "name": "Công An!", "effect": "lose_money_50"},
    "broken_phone":    {"chance": 0.001, "type": "bad", "name": "Rớt ĐT!", "effect": "lose_money_200"},  # Hiếm
    "wallet_fall":     {"chance": 0.002, "type": "bad", "name": "Rớt Ví!", "effect": "lose_money_100"},
    "snake_bite":      {"chance": 0.002, "type": "bad", "name": "Rắn Cắn!", "effect": "lose_money_percent"},  # -5%
    "hospital_fee":    {"chance": 0.001, "type": "bad", "name": "Nhập Viện!", "effect": "lose_money_percent"},
    "bet_lose":        {"chance": 0.005, "type": "bad", "name": "Thua Cược!", "effect": "bet_loss"},

    # --- Nhóm 4: Tăng Cooldown (Tốn thời gian) ---
    "dropped_slipper": {"chance": 0.005, "type": "bad", "name": "Rớt Dép!", "effect": "cooldown_short"},  # +2 phút
    "tangled_line":    {"chance": 0.005, "type": "bad", "name": "Rối Dây!", "effect": "cooldown_short"},
    "stomach_ache":    {"chance": 0.004, "type": "bad", "name": "Đau Bụng!", "effect": "cooldown_medium"},  # +5 phút
    "heavy_rain":      {"chance": 0.004, "type": "bad", "name": "Mưa To!", "effect": "cooldown_medium"},
    "equipment_break": {"chance": 0.002, "type": "bad", "name": "Gãy Cần!", "effect": "cooldown_long"},  # +10 phút

    # --- Nhóm 5: Mất Lượt (Vô tri/Hài hước) ---
    "mom_called":      {"chance": 0.005, "type": "bad", "name": "Mẹ Gọi!", "effect": "lose_turn"},
    "wife_gank":       {"chance": 0.003, "type": "bad", "name": "Vợ Gank!", "effect": "lose_turn"},
    "sleepy":          {"chance": 0.005, "type": "bad", "name": "Ngủ Gật!", "effect": "lose_turn"},
    "sneeze":          {"chance": 0.005, "type": "bad", "name": "Hắt Xì!", "effect": "lose_turn"},
    "kids_rock":       {"chance": 0.004, "type": "bad", "name": "Trẻ Trâu!", "effect": "lose_turn"},

    # --- Nhóm 6: Hại Độ Bền (Phá hoại) ---
    "plastic_trap":    {"chance": 0.005, "type": "bad", "name": "Vướng Rác!", "effect": "durability_hit"},
    "big_log":         {"chance": 0.004, "type": "bad", "name": "Mắc Gỗ!", "effect": "durability_hit"},
    "crab_cut":        {"chance": 0.004, "type": "bad", "name": "Cua Kẹp!", "effect": "durability_hit"},
    "electric_eel":    {"chance": 0.002, "type": "bad", "name": "Lươn Điện!", "effect": "durability_hit"},
    "sea_sickness":    {"chance": 0.002, "type": "bad", "name": "Say Sóng!", "effect": "lose_all_bait"},  # Đặc biệt

    # ================= 30 GOOD EVENTS (NHÂN PHẨM) =================
    # effect: gain_money_*, gain_worm_*, gain_chest_*, gain_pearl, gain_ring, multiply_catch_*, reset_cooldown, restore_durability, lucky_buff, avoid_bad_event
    
    # --- Nhóm 1: Nhặt Được Tiền (Lộc trời cho) ---
    "found_wallet":    {"chance": 0.005, "type": "good", "name": "Vớt Ví!", "effect": "gain_money_medium"},  # 100-200
    "tourist_tip":     {"chance": 0.005, "type": "good", "name": "Tiền Tip!", "effect": "gain_money_medium"},
    "floating_cash":   {"chance": 0.005, "type": "good", "name": "Tiền Trôi!", "effect": "gain_money_small"},  # 50-100
    "ancient_coin":    {"chance": 0.003, "type": "good", "name": "Xu Cổ!", "effect": "gain_money_large"},  # 300-500
    "lottery_win":     {"chance": 0.001, "type": "good", "name": "Trúng Số!", "effect": "gain_money_huge"},  # 1000
    "streamer_gift":   {"chance": 0.004, "type": "good", "name": "Donate!", "effect": "gain_money_medium"},
    "bet_win":         {"chance": 0.005, "type": "good", "name": "Thắng Cược!", "effect": "bet_win"},

    # --- Nhóm 2: Nhận Vật Phẩm (Mồi/Rương/Ngọc) ---
    "fairy_gift":      {"chance": 0.005, "type": "good", "name": "Ông Bụt!", "effect": "gain_worm_5"},
    "worm_nest":       {"chance": 0.004, "type": "good", "name": "Ổ Giun!", "effect": "gain_worm_10"},
    "treasure_chest":  {"chance": 0.003, "type": "good", "name": "Rương Báu!", "effect": "gain_chest_1"},
    "shipwreck":       {"chance": 0.001, "type": "good", "name": "Tàu Đắm!", "effect": "gain_chest_2"},
    "mermaid_gift":    {"chance": 0.002, "type": "good", "name": "Tiên Cá!", "effect": "gain_pearl"},  # Ngọc trai
    "message_bottle":  {"chance": 0.003, "type": "good", "name": "Thư Chai!", "effect": "gain_chest_1"},
    "engagement_ring": {"chance": 0.002, "type": "good", "name": "Nhẫn Cưới!", "effect": "gain_ring"},  # Bán giá cao

    # --- Nhóm 3: X2, X3 Cá (Trúng mánh) ---
    "school_of_fish":  {"chance": 0.005, "type": "good", "name": "Bão Cá!", "effect": "multiply_catch_3"},
    "golden_hook":     {"chance": 0.006, "type": "good", "name": "Lưỡi Vàng!", "effect": "multiply_catch_2"},
    "fish_feeding":    {"chance": 0.005, "type": "good", "name": "Cá Ăn Rộ!", "effect": "multiply_catch_2"},
    "friendly_otter":  {"chance": 0.004, "type": "good", "name": "Rái Cá Giúp!", "effect": "multiply_catch_2"},
    "net_fishing":     {"chance": 0.002, "type": "good", "name": "Vớt Lưới!", "effect": "multiply_catch_3"},

    # --- Nhóm 4: Hồi Phục & Cooldown (Tiện ích) ---
    "golden_turtle":   {"chance": 0.005, "type": "good", "name": "Rùa Vàng!", "effect": "reset_cooldown"},
    "favorable_wind":  {"chance": 0.005, "type": "good", "name": "Gió Thuận!", "effect": "reset_cooldown"},
    "blacksmith_ghost":{"chance": 0.003, "type": "good", "name": "Ma Thợ Rèn!", "effect": "restore_durability"},  # Hồi độ bền
    "maintenance_kit": {"chance": 0.003, "type": "good", "name": "Dầu Máy!", "effect": "restore_durability"},
    "energy_drink":    {"chance": 0.004, "type": "good", "name": "Tăng Lực!", "effect": "reset_cooldown"},

    # --- Nhóm 5: Buff May Mắn (Tâm linh) ---
    "double_rainbow":  {"chance": 0.003, "type": "good", "name": "Cầu Vồng!", "effect": "lucky_buff"},  # Lần sau chắc chắn Rare
    "shooting_star":   {"chance": 0.003, "type": "good", "name": "Sao Băng!", "effect": "lucky_buff"},
    "ancestor_bless":  {"chance": 0.004, "type": "good", "name": "Ông Bà Độ!", "effect": "lucky_buff"},
    "sixth_sense":     {"chance": 0.004, "type": "good", "name": "Giác Quan 6!", "effect": "avoid_bad_event"},  # Tránh xui lần sau
    "lucky_underwear": {"chance": 0.002, "type": "good", "name": "Quần Đỏ!", "effect": "lucky_buff"},  # Hài hước
    "temple_pray":     {"chance": 0.003, "type": "good", "name": "Đi Chùa!", "effect": "avoid_bad_event"},
}

RANDOM_EVENT_MESSAGES = {
    # --- BAD EVENTS MESSAGES ---
    "snapped_line":    "Dây câu căng quá... PẶT! Mất toi cái mồi rồi. 😭",
    "hook_stuck":      "Lưỡi câu mắc vào rễ cây dưới đáy hồ. Phải cắt dây bỏ mồi. ✂️",
    "rat_bite":        "Một con chuột cống chạy qua cắn đứt dây câu của bạn! 🐀",
    "poor_knot":       "Do buộc nút không chặt, lưỡi câu tuột mất tiêu. Gà quá! 🐔",
    "fish_escape":     "Cá đã cắn câu nhưng quẫy mạnh quá nên thoát được. Tiếc hùi hụi! 🐟💨",
    "bet_lose": "Một tay câu mới đến thách đấu. Bạn tự tin nhận kèo và... thua sấp mặt! 💸",

    "predator":        "Cá Sư Tử lao tới đớp trọn mẻ cá của bạn rồi bỏ chạy! 😱",
    "cat_steal":       "Meow! 🐈 Một con mèo đen nhanh tay cướp mất con cá to nhất của bạn!",
    "bird_steal":      "Một con Hải Âu sà xuống cắp mất con cá ngon nhất. Cay thế nhở! 🦅",
    "bucket_leak":     "Xô đựng cá bị thủng đáy! Mấy con cá bé chui ra ngoài hết rồi. 🕳️",
    "otter_troll":     "Một chú Rái Cá trêu ngươi bạn, thò tay bốc trộm cá rồi lặn mất. 🦦",

    "police_fine":     "O e o e! 🚔 Công an phường phạt 50 Hạt vì tội câu cá trái phép!",
    "broken_phone":    "Tõm! Chiếc iPhone 15 Promax rơi xuống nước. Tốn 200 Hạt sửa chữa. 📱💦",
    "wallet_fall":     "Cúi xuống gỡ cá, ví tiền rơi tõm xuống hồ. Mất 100 Hạt. 💸",
    "snake_bite":      "Kéo lên không phải cá mà là Rắn Nước! Bị cắn chảy máu (-5% tiền thuốc men) 🐍",
    "hospital_fee":    "Trượt chân ngã sấp mặt! Phải đi trạm xá khâu vết thương (-5% tiền). 🏥",

    "dropped_slipper": "Mải giật cần làm rớt dép lào. Phải bơi đi nhặt mất 2 phút! 🩴",
    "tangled_line":    "Dây câu rối như tơ vò. Ngồi gỡ mất cả thanh xuân (2 phút). 🧶",
    "stomach_ache":    "Tào Tháo đuổi! 🚽 Bạn phải chạy đi giải quyết nỗi buồn (Chờ 5 phút).",
    "heavy_rain":      "Mưa to gió lớn! Phải trú mưa chờ tạnh (Chờ 5 phút). ⛈️",
    "equipment_break": "Rắc! Cần câu bị gãy gập. Phải đem đi hàn lại (Chờ 10 phút). 🛠️",

    "mom_called":      "Alo? Mẹ gọi về ăn cơm! Bạn vội chạy về, bỏ lỡ mẻ cá này. 🍚",
    "wife_gank":       "Vợ/Người yêu xuất hiện gank! 'Suốt ngày câu với kéo!'. Bạn phải trốn ngay. 🏃",
    "sleepy":          "Gió mát quá... Zzz... Bạn ngủ gật và cá ăn hết mồi lúc nào không hay. 😴",
    "sneeze":          "Hắt xì!!! 🤧 Tiếng hắt hơi làm đàn cá giật mình bơi đi hết.",
    "kids_rock":       "Lũ trẻ trâu ném đá xuống hồ làm cá sợ chạy mất dép. 🗿",

    "plastic_trap":    "Lưỡi câu móc vào bao tải rác. Kéo nặng trịch làm hại độ bền cần. 🗑️",
    "big_log":         "Tưởng cá to, hóa ra là khúc gỗ mục. Cần câu bị cong vòng (-Độ bền). 🪵",
    "crab_cut":        "Con Cua kẹp vào dây câu làm xước dây và mòn cần. 🦀",
    "electric_eel":    "Câu trúng Lươn Điện! Nó phóng điện làm bạn tê tay, rơi cần xuống đất. ⚡",
    "sea_sickness":    "Sóng đánh tụt quần! Bạn nôn thốc nôn tháo... nôn hết cả túi mồi ra biển. 🤢",
    
    # --- GOOD EVENTS MESSAGES ---
    "found_wallet":    "Vớt được cái ví da cá sấu! Bên trong có kha khá tiền lẻ. 👛",
    "tourist_tip":     "Khách du lịch thấy bạn câu điệu nghệ quá nên tip nóng! 💵",
    "floating_cash":   "Ai đó đánh rơi tờ 50k trôi lềnh bềnh trên mặt nước! Vớt lẹ! 💸",
    "ancient_coin":    "Móc lên được đồng xu cổ thời vua Hùng. Bảo tàng mua lại giá cao! 🪙",
    "lottery_win":     "Vớt được tờ vé số trúng giải độc đắc (giải khuyến khích)! 🎫🎉",
    "streamer_gift":   "Độ Mixi đi ngang qua và donate cho bạn tiền mua mồi! 🎥",
    "bet_win":  "Một tay câu mới đến thách đấu. Bạn dạy cho hắn một bài học về kỹ năng! 😎",

    "fairy_gift":      "Ông Bụt hiện lên: 'Ta tặng con 5 con Giun vì con nghèo mà ham cày'. 🎅",
    "worm_nest":       "Đào trúng ổ giun chúa! Nhặt mỏi tay không hết mồi. 🪱",
    "treasure_chest":  "Kéo nặng trịch... Là một Rương Kho Báu của cướp biển để lại! 🏴‍☠️",
    "shipwreck":       "Phát hiện xác tàu đắm! Bạn tìm thấy 2 cái Rương còn nguyên vẹn. 📦📦",
    "mermaid_gift":    "Nàng Tiên Cá ngoi lên tặng bạn viên Ngọc Trai rồi ngại ngùng bơi đi. 🧜‍♀️",
    "message_bottle":  "Một cái chai trôi dạt, bên trong có bản đồ dẫn tới Kho Báu! 🗺️",
    "engagement_ring": "Ai đó thất tình ném nhẫn xuống hồ. Nhẫn kim cương xịn nha! 💍",

    "school_of_fish":  "Trúng luồng cá di cư! Giật mỏi tay, X3 sản lượng! 🐟🐟🐟",
    "golden_hook":     "Lưỡi câu của bạn phát sáng hoàng kim! Cá cắn câu gấp đôi! ✨",
    "fish_feeding":    "Đúng giờ cá ăn! Lũ cá tranh nhau đớp mồi. X2 sản lượng! 🍲",
    "friendly_otter":  "Một chú Rái Cá lùa cá vào lưới giúp bạn. X2 cá! 🦦",
    "net_fishing":     "Móc trúng cái lưới của ai bỏ quên, bên trong đầy cá! (X3) 🕸️",

    "golden_turtle":   "Cụ Rùa Vàng nổi lên thở. Bạn cảm thấy tràn trề sinh lực (Xóa Cooldown)! 🐢",
    "favorable_wind":  "Gió đông thổi tới! Câu nhanh hơn hẳn (Xóa Cooldown). 🌬️",
    "blacksmith_ghost":"Hồn ma thợ rèn hiện về: 'Để ta sửa cần cho con'. (+20 Độ bền) 🔨👻",
    "maintenance_kit": "Vớt được hộp dầu máy. Tra dầu vào cần câu chạy mượt hẳn! (+20 Độ bền) 🛢️",
    "energy_drink":    "Làm lon bò húc! Tỉnh cả người, quăng cần liên tục (Xóa Cooldown). 🐂",

    "double_rainbow":  "Cầu vồng đôi! 🌈 Nhân phẩm bùng nổ (Lần sau chắc chắn ra Cá Hiếm).",
    "shooting_star":   "Sao băng lướt qua! 🌠 Ước gì được nấy (Buff may mắn).",
    "ancestor_bless":  "Ông bà gánh còng lưng! Lần câu sau auto đỏ. 🙏",
    "sixth_sense":     "Mắt phải giật liên hồi... Linh tính mách bảo bạn sẽ tránh được kiếp nạn sắp tới. 👁️",
    "lucky_underwear": "Bạn mặc chiếc quần chip đỏ may mắn hôm nay. Cá to tự tìm đến! 🩲",
    "temple_pray":     "Hôm qua mới đi chùa thắp hương. Thần linh phù hộ tránh xui xẻo. 🏯",
}


# ==================== SELL EVENTS (Sự kiện khi bán cá) ====================
# Tỉ lệ xảy ra khi bán: khoảng 15-20%

SELL_EVENTS = {
    # ================= 30 BAD EVENTS (KIẾP NẠN THƯƠNG TRƯỜNG) =================
    # mul: Nhân doanh thu (< 1.0)
    # flat: Trừ thẳng tiền (< 0)

    # --- Nhóm 1: Thị Trường & Giá Cả (Ép giá) ---
    "market_crash":       {"chance": 0.01, "type": "bad", "mul": 0.7, "flat": 0, "name": "Sập Giá!"},
    "aggressive_haggler": {"chance": 0.008, "type": "bad", "mul": 0.85, "flat": 0, "name": "Trả Giá!"},
    "competitor_sale":    {"chance": 0.008, "type": "bad", "mul": 0.9, "flat": 0, "name": "Cạnh Tranh!"},
    "deflation":          {"chance": 0.005, "type": "bad", "mul": 0.8, "flat": 0, "name": "Mất Giá!"},
    "wrong_season":       {"chance": 0.005, "type": "bad", "mul": 0.75, "flat": 0, "name": "Nghịch Mùa!"},
    "oversupply":         {"chance": 0.008, "type": "bad", "mul": 0.85, "flat": 0, "name": "Dư Thừa!"},

    # --- Nhóm 2: Chất Lượng Kém (Hư hỏng) ---
    "rotten_fish":        {"chance": 0.008, "type": "bad", "mul": 0.6, "flat": 0, "name": "Cá Ươn!"},
    "bad_smell":          {"chance": 0.008, "type": "bad", "mul": 0.9, "flat": 0, "name": "Mùi Hôi!"},
    "flies_swarm":        {"chance": 0.005, "type": "bad", "mul": 0.95, "flat": -20, "name": "Ruồi Bu!"},
    "melting_ice":        {"chance": 0.008, "type": "bad", "mul": 0.9, "flat": -10, "name": "Tan Đá!"},
    "skinny_fish":        {"chance": 0.005, "type": "bad", "mul": 0.85, "flat": 0, "name": "Cá Còi!"},
    "parasite_found":     {"chance": 0.003, "type": "bad", "mul": 0.5, "flat": 0, "name": "Ký Sinh!"},

    # --- Nhóm 3: Chính Quyền & Thuế (Phạt tiền) ---
    "tax_collector":      {"chance": 0.008, "type": "bad", "mul": 0.85, "flat": 0, "name": "Thuế Chợ!"},
    "market_management":  {"chance": 0.004, "type": "bad", "mul": 1.0, "flat": -200, "name": "QLTT Phạt!"},
    "sanitation_fine":    {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -100, "name": "Vệ Sinh!"},
    "parking_fee":        {"chance": 0.01, "type": "bad", "mul": 1.0, "flat": -10, "name": "Gửi Xe!"},
    "rent_increase":      {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -50, "name": "Tăng Rent!"},

    # --- Nhóm 4: Tội Phạm & Lừa Đảo (Mất mát) ---
    "fake_money":         {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -100, "name": "Tiền Giả!"},
    "pickpocket":         {"chance": 0.004, "type": "bad", "mul": 0.7, "flat": 0, "name": "Móc Túi!"},
    "gangster_fee":       {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -150, "name": "Bảo Kê!"},
    "scammer":            {"chance": 0.005, "type": "bad", "mul": 0.8, "flat": 0, "name": "Lừa Đảo!"},
    "thief_run":          {"chance": 0.002, "type": "bad", "mul": 0.0, "flat": 0, "name": "Cướp!"},

    # --- Nhóm 5: Tai Nạn & Đen Đủi (Hài hước) ---
    "dropped_money":      {"chance": 0.008, "type": "bad", "mul": 1.0, "flat": -50, "name": "Rớt Tiền!"},
    "hole_in_bag":        {"chance": 0.008, "type": "bad", "mul": 0.9, "flat": 0, "name": "Túi Thủng!"},
    "broken_scale":       {"chance": 0.008, "type": "bad", "mul": 0.9, "flat": 0, "name": "Cân Điêu!"},
    "cat_steal_sell":     {"chance": 0.008, "type": "bad", "mul": 1.0, "flat": -30, "name": "Mèo Cướp!"},
    "stray_dog":          {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -40, "name": "Chó Dữ!"},
    "rainy_day":          {"chance": 0.008, "type": "bad", "mul": 0.8, "flat": 0, "name": "Mưa Giông!"},
    "slip_fall":          {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -80, "name": "Trượt Ngã!"},
    "plastic_bag_fee":    {"chance": 0.01, "type": "bad", "mul": 1.0, "flat": -5, "name": "Tiền Túi!"},
    "maybach_crash":      {"chance": 0.002, "type": "bad", "mul": 1.0, "flat": -500, "name": "Tông Maybach!"},
    "rollroyce_crash":    {"chance": 0.001, "type": "bad", "mul": 1.0, "flat": -1000, "name": "Tông Rolls-Royce!"},
    "ferrari_crash":      {"chance": 0.001, "type": "bad", "mul": 1.0, "flat": -1000, "name": "Tông Ferrari!"},
    "porsche_crash":      {"chance": 0.002, "type": "bad", "mul": 1.0, "flat": -800, "name": "Tông Porsche!"},
    "mercedes_g63":       {"chance": 0.003, "type": "bad", "mul": 1.0, "flat": -600, "name": "Tông G63!"},
    "lamborghini_crash":  {"chance": 0.001, "type": "bad", "mul": 1.0, "flat": -1200, "name": "Tông Bò Tót!"},
    "bentley_crash":      {"chance": 0.002, "type": "bad", "mul": 1.0, "flat": -900, "name": "Tông Bentley!"},
    "bugatti_crash":      {"chance": 0.0005, "type": "bad", "mul": 1.0, "flat": -2000, "name": "Tông Bugatti!"},
    "vinfast_crash":      {"chance": 0.004, "type": "bad", "mul": 1.0, "flat": -300, "name": "Tông VinFast!"},

    # --- GOOD EVENTS (May mắn - Tăng tiền - 30 events) ---
    # Nhóm 1: Tăng giá bán
    "market_boom":         {"chance": 0.01, "type": "good", "mul": 1.2, "flat": 0, "name": "Chợ Sôi!"},
    "sushi_chef":          {"chance": 0.005, "type": "good", "mul": 1.3, "flat": 0, "name": "Đầu Bếp!"},
    "tourist_group":       {"chance": 0.008, "type": "good", "mul": 1.15, "flat": 0, "name": "Khách Du!"},
    "festival":            {"chance": 0.01, "type": "good", "mul": 1.25, "flat": 0, "name": "Lễ Hội!"},
    "fresh_bonus":         {"chance": 0.01, "type": "good", "mul": 1.1, "flat": 0, "name": "Tươi Roi!"},
    "bidding_war":         {"chance": 0.005, "type": "good", "mul": 1.35, "flat": 0, "name": "Tranh Mua!"},
    "supportive_friend":   {"chance": 0.008, "type": "good", "mul": 1.1, "flat": 50, "name": "Bạn Ủng!"},
    "golden_scale":        {"chance": 0.01, "type": "good", "mul": 1.1, "flat": 0, "name": "Cân Thừa!"},
    "sold_out":            {"chance": 0.008, "type": "good", "mul": 1.15, "flat": 0, "name": "Cháy Hàng!"},
    "compliment":          {"chance": 0.008, "type": "good", "mul": 1.1, "flat": 20, "name": "Khen Ngợi!"},
    "loyal_customer":      {"chance": 0.008, "type": "good", "mul": 1.15, "flat": 0, "name": "Khách Quen!"},
    "good_weather":        {"chance": 0.01, "type": "good", "mul": 1.1, "flat": 0, "name": "Trời Đẹp!"},
    "unexpected_luck":     {"chance": 0.005, "type": "good", "mul": 1.2, "flat": 50, "name": "May Mắn!"},
    "big_fish_auction":    {"chance": 0.003, "type": "good", "mul": 2.0, "flat": 0, "name": "Đấu Giá!"},
    "newspaper_feature":   {"chance": 0.002, "type": "good", "mul": 1.5, "flat": 0, "name": "Lên Báo!"},
    
    # Nhóm 2: Nhận thêm tiền
    "tip_money":           {"chance": 0.01, "type": "good", "mul": 1.0, "flat": 50, "name": "Tiền Tip!"},
    "charity":             {"chance": 0.01, "type": "good", "mul": 1.0, "flat": 100, "name": "Lì Xì!"},
    "found_money":         {"chance": 0.005, "type": "good", "mul": 1.0, "flat": 200, "name": "Tiền Rơi!"},
    "lucky_money":         {"chance": 0.005, "type": "good", "mul": 1.0, "flat": 100, "name": "May Mắn!"},
    "golden_hour":         {"chance": 0.005, "type": "good", "mul": 1.4, "flat": 0, "name": "Giờ Vàng!"},
    "rich_customer":       {"chance": 0.01, "type": "good", "mul": 1.2, "flat": 0, "name": "Khách Sộp!"},
    "buy_one_get_one":     {"chance": 0.008, "type": "good", "mul": 1.2, "flat": 0, "name": "Khuyến Mãi!"},
    "double_joy":          {"chance": 0.003, "type": "good", "mul": 1.3, "flat": 100, "name": "Niềm Vui!"},
    
    # Nhóm 3: Nhận vật phẩm/special
    "gift_received":       {"chance": 0.003, "type": "good", "mul": 1.0, "flat": 0, "name": "Quà Tặng!", "special": "chest"},
    "found_bait":          {"chance": 0.005, "type": "good", "mul": 1.0, "flat": 0, "name": "Tìm Mồi!", "special": "worm"},
    "lottery_ticket":      {"chance": 0.003, "type": "good", "mul": 1.0, "flat": 0, "name": "Vé Số!", "special": "lottery"},
    "pearl_in_fish":       {"chance": 0.001, "type": "good", "mul": 1.0, "flat": 0, "name": "Ngọc Trai!", "special": "pearl"},
    "free_breakfast":      {"chance": 0.005, "type": "good", "mul": 1.0, "flat": 0, "name": "Ăn Sáng!", "special": "durability"},
    "old_rod_gift":        {"chance": 0.001, "type": "good", "mul": 1.0, "flat": 0, "name": "Tặng Cần!", "special": "rod"},
    "god_of_wealth":       {"chance": 0.002, "type": "good", "mul": 2.0, "flat": 0, "name": "Thần Tài!"},
}

SELL_MESSAGES = {
    # --- 30 BAD EVENTS MESSAGES ---
    # Nhóm 1: Thị Trường & Giá Cả
    "market_crash": "Cả chợ ai cũng bán cá này, giá rớt thê thảm! 📉 (Giá giảm 30%)",
    "aggressive_haggler": "Gặp bà thím mặc cả kinh hoàng: 'Bớt đi cháu, không cô đi hàng khác!'. 👵 (Giá giảm 15%)",
    "competitor_sale": "Sạp bên cạnh xả hàng tồn kho giá rẻ bèo, bạn buộc phải giảm giá theo. 🏷️ (Giá giảm 10%)",
    "deflation": "Kinh tế khó khăn, người dân thắt chặt chi tiêu, ép giá bạn. 💸 (Giá giảm 20%)",
    "wrong_season": "Mùa này không ai ăn cá này cả, phải năn nỉ mãi mới bán được. 🍂 (Giá giảm 25%)",
    "oversupply": "Thuyền về bến quá nhiều, cá ngập chợ, giá rẻ như cho. 🐟 (Giá giảm 15%)",

    # Nhóm 2: Chất Lượng Kém
    "rotten_fish": "Trời nóng quá làm cá bị ươn, bốc mùi. Phải bán đổ bán tháo. 🤢 (Giá giảm 40%)",
    "bad_smell": "Sạp cá của bạn bốc mùi lạ, khách hàng bịt mũi bỏ đi. 👃 (Giá giảm 10%)",
    "flies_swarm": "Ruồi bu kiến đậu, bạn phải tốn tiền mua nhang muỗi để đuổi. 🪰 (Mất 20 Hạt)",
    "melting_ice": "Đá ướp tan hết sạch, cá mất độ tươi ngon. 🧊 (Giá giảm 10% + Tốn 10 Hạt)",
    "skinny_fish": "Khách chê: 'Cá gì mà toàn xương với đầu', ép giá bạn. 🦴 (Giá giảm 15%)",
    "parasite_found": "Khách phát hiện có sán trong mang cá! Bạn phải đền bù danh dự. 😱 (Giá giảm 50%)",

    # Nhóm 3: Chính Quyền & Thuế
    "tax_collector": "Ban quản lý chợ đi thu thuế chỗ ngồi và phí vệ sinh. 🧾 (Mất 15% doanh thu)",
    "market_management": "Quản lý thị trường kiểm tra: 'Cân chưa kiểm định!'. Phạt nóng! 👮 (Phạt 200 Hạt)",
    "sanitation_fine": "Vứt rác bừa bãi bị tổ dân phố bắt quả tang. Phạt cảnh cáo. 🧹 (Phạt 100 Hạt)",
    "parking_fee": "Hôm nay bãi xe tăng giá, tốn thêm tiền gửi xe tải cá. 🛵 (Mất 10 Hạt)",
    "rent_increase": "Chủ sạp thông báo tăng tiền thuê mặt bằng đột xuất. 🏘️ (Mất 50 Hạt)",

    # Nhóm 4: Tội Phạm & Lừa Đảo
    "fake_money": "Về nhà đếm lại tiền mới phát hiện bị kẹp tờ tiền âm phủ. 💸 (Mất 100 Hạt)",
    "pickpocket": "Chen chúc đông người, kẻ gian đã rạch túi lấy mất ví tiền của bạn! 🕵️ (Mất 30% doanh thu)",
    "gangster_fee": "Giang hồ 'Hắc Long Bang' đi thu phí bảo kê khu vực này. 🕶️ (Mất 150 Hạt)",
    "scammer": "Bị khách dùng thủ thuật 'tráo tiền' lừa mất một khoản. 🃏 (Mất 20% doanh thu)",
    "thief_run": "CƯỚP! Một tên cướp giật phăng túi tiền của bạn và chạy mất! 🏃💨 (Mất TRẮNG doanh thu)",

    # Nhóm 5: Tai Nạn & Đen Đủi
    "dropped_money": "Đang đếm tiền thì gió thổi bay mất một tờ 50 Hạt xuống cống. 🌬️ (Mất 50 Hạt)",
    "hole_in_bag": "Túi đựng tiền bị thủng lỗ nhỏ, rơi rớt tiền lẻ dọc đường. 🧵 (Mất 10% doanh thu)",
    "broken_scale": "Cái cân lò xo bị giãn, cân 1kg mà chỉ hiện 9 lạng. ⚖️ (Mất 10% doanh thu)",
    "cat_steal_sell": "Đang bận bán hàng, con mèo hoang nhảy lên quầy cướp mất con cá ngon. 🐈 (Mất 30 Hạt)",
    "stray_dog": "Con chó hàng xóm chạy qua tè vào xô cá. Phải đền tiền cho khách. 🐕 (Mất 40 Hạt)",
    "rainy_day": "Mưa to quá, chợ vắng tanh, phải bán lỗ vốn để về sớm. 🌧️ (Giá giảm 20%)",
    "slip_fall": "Sàn chợ trơn trượt, bạn ngã sấp mặt làm đổ hết tiền ra sàn. 🤕 (Mất 80 Hạt)",
    "plastic_bag_fee": "Khách đòi nhiều túi ni lông quá, tốn tiền mua bao bì. 🛍️ (Mất 5 Hạt)",
    "maybach_crash": "Mải bấm điện thoại check giá cá, bạn tông phải đuôi xe Maybach của chủ tịch xã. Đền ốm đòn! 🚗💥 (-500 Hạt)",
    "maybach_crash": "Mải check giá cá trên điện thoại, bạn tông móp đuôi chiếc **Maybach S680** của chủ tịch huyện. Bán cả sạp cá cũng không đủ đền! 😭 (-500 Hạt)",
    "rollroyce_crash": "Đang phi xe ba gác thì tạt đầu trúng chiếc **Rolls-Royce Phantom**. Cái logo 'Spirit of Ecstasy' bay mất tiêu. Bạn xác định ra đê ở! 💸 (-1000 Hạt)",
    "ferrari_crash": "Thấy đèn vàng cố vượt, bạn quẹt xước sườn siêu xe **Ferrari 488** đang dừng. Tiếng 'két' nghe mà xót xa cõi lòng. 🏎️💔 (-1000 Hạt)",
    "porsche_crash": "Mắt nhắm mắt mở thế nào mà húc thẳng vào đuôi em **Porsche Panamera**. Chủ xe bước xuống nhìn bạn ngao ngán... Chuẩn bị tiền đi! 🚗💥 (-1000 Hạt)",
    "mercedes_g63": "Lùi xe không quan sát, bạn húc vỡ đèn hậu chiếc **Mercedes G63** mới cóng. Chủ xe nhìn bạn bằng nửa con mắt. 🚙 (-600 Hạt)",
    "lamborghini_crash": "Nghe tiếng nẹt pô giật mình, bạn tay lái lụa quẹt luôn vào cánh cửa chiếc **Lamborghini Aventador**. Bò tót húc thủng ví rồi! 🐂💸 (-1200 Hạt)",
    "bentley_crash": "Tránh ổ gà, bạn lạng tay lái va phải chiếc **Bentley** sang trọng. Tiền sơn xe bằng cả tháng đi câu! 🎩 (-900 Hạt)",
    "bugatti_crash": "😱 **THẢM HỌA!** Bạn vừa tông phải siêu phẩm **Bugatti Chiron** độc nhất vô nhị. Bán nhà, bán đất, bán cả server cũng không đủ đền! ☠️ (-2000 Hạt)",
    "vinfast_crash": "Ủng hộ hàng Việt nhưng hơi sai cách. Bạn vừa hôn vào đuôi chiếc **VinFast President**. Mãnh liệt tinh thần... đền tiền. 🇻🇳 (-300 Hạt)",

    # --- 30 GOOD EVENTS MESSAGES ---
    # Nhóm 1: Tăng giá bán
    "market_boom": "Thị trường sôi động, giá cá tăng vọt! 📈 (Tăng 20%)",
    "sushi_chef": "Đầu bếp nhà hàng 5 sao mua cá với giá cao! 🍣 (Tăng 30%)",
    "tourist_group": "Khách du lịch ghé chợ, mua cá với giá hời. 🎒 (Tăng 15%)",
    "festival": "Lễ hội ẩm thực đang diễn ra, nhu cầu tăng! 🏮 (Tăng 25%)",
    "fresh_bonus": "Cá của bạn tươi quá! Được đánh giá 5 sao. ⭐ (Tăng 10%)",
    "bidding_war": "Thương lái tranh nhau mua mẻ cá của bạn! 🗣️ (Tăng 35%)",
    "supportive_friend": "Gặp bạn quen, họ mua ủng hộ với giá cao. 💚 (Tăng 10% + 50 Hạt)",
    "golden_scale": "Cân của bà chủ bị hỏng, cân thừa cho bạn! ⚖️ (Tăng 10%)",
    "sold_out": "Bạn bán hết sạch cá trong tích tắc! 🔥 (Tăng 15%)",
    "compliment": "Mọi người khen cá bạn ngon nhất chợ! 👍 (Tăng 10% + 20 Hạt)",
    "loyal_customer": "Khách quen quay lại mua ủng hộ. 🤝 (Tăng 15%)",
    "good_weather": "Trời đẹp, chợ đông, bán đắt hàng! ☀️ (Tăng 10%)",
    "unexpected_luck": "Hôm nay bạn cảm thấy thật may mắn! 🍀 (Tăng 20% + 50 Hạt)",
    "big_fish_auction": "Con cá to nhất được đấu giá! 🏆 (Giá cực cao)",
    "newspaper_feature": "Báo đưa tin về mẻ cá tuyệt vời của bạn! 📰 (Tăng 50%)",
    
    # Nhóm 2: Nhận thêm tiền
    "tip_money": "Khách hàng thấy bạn vui vẻ nên tip thêm tiền. 💵 (+50 Hạt)",
    "charity": "Hôm nay bà chủ trúng số, lì xì cho bạn. 🧧 (+100 Hạt)",
    "found_money": "Bạn nhặt được tiền rơi ở chợ! 💸 (+200 Hạt)",
    "lucky_money": "Bà chủ cảm thấy vui nên lì xì thêm. 🎉 (+100 Hạt)",
    "golden_hour": "Bạn bán cá đúng giờ vàng, giá cao nhất! ⏰ (Tăng 40%)",
    "rich_customer": "Gặp đại gia, không cần nhìn giá. 🎩 (Tăng 20%)",
    "buy_one_get_one": "Khách hàng vui vẻ mua thêm vì khuyến mãi. 🎁 (Tăng 20%)",
    "double_joy": "Bán được giá cao lại còn được khen! 😊 (Tăng 30% + 100 Hạt)",
    
    # Nhóm 3: Nhận vật phẩm
    "gift_received": "Khách hàng tặng bạn một rương báu nhỏ. 📦 (+1 Rương)",
    "found_bait": "Bạn tìm thấy mồi câu bị bỏ quên! 🪱 (+5 Mồi)",
    "lottery_ticket": "Ai đó tặng bạn vé số! 🎫 (Cơ hội trúng thưởng)",
    "pearl_in_fish": "Phát hiện ngọc trai trong bụng cá! 🔮 (+1 Ngọc Trai)",
    "free_breakfast": "Bà chủ mời bạn ăn sáng miễn phí! 🍜 (+Độ bền)",
    "old_rod_gift": "Ngư dân già tặng cần câu cũ của ông! 🎣 (+Vật liệu)",
    "god_of_wealth": "🧧 **THẦN TÀI GÕ CỬA!** Hôm nay may mắn nhất! (X2 DOANH THU)",
    "buy_one_get_one": "Khách hàng vui vẻ mua thêm vì khuyến mãi. 🎁 (Tăng 20%)",
    "double_joy": "Bán được giá cao lại còn được khen! 😊 (Tăng 30% + 100 Hạt)",
    
    # Nhóm 3: Nhận vật phẩm
    "gift_received": "Khách hàng tặng bạn một rương báu nhỏ. 📦 (+1 Rương)",
    "found_bait": "Bạn tìm thấy mồi câu bị bỏ quên! 🪱 (+5 Mồi)",
    "lottery_ticket": "Ai đó tặng bạn vé số! 🎫 (Cơ hội trúng thưởng)",
    "pearl_in_fish": "Phát hiện ngọc trai trong bụng cá! 🔮 (+1 Ngọc Trai)",
    "free_breakfast": "Bà chủ mời bạn ăn sáng miễn phí! 🍜 (+Độ bền)",
    "old_rod_gift": "Ngư dân già tặng cần câu cũ của ông! 🎣 (+Vật liệu)",
    "god_of_wealth": "🧧 **THẦN TÀI GÕ CỬA!** Hôm nay may mắn nhất! (X2 DOANH THU)",
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
        # Check if user has avoid_bad_event protection
        if hasattr(self, "avoid_event_users") and self.avoid_event_users.get(user_id, False):
            # Clear the protection flag
            self.avoid_event_users[user_id] = False
            print(f"[EVENT PROTECTION] User {user_id} avoided bad event (protection active)")
            # Return no event
            return {
                "triggered": False, "type": None, "message": "",
                "lose_worm": False, "lose_catch": False, "lose_money": 0, "gain_money": 0,
                "cooldown_increase": 0,
                "catch_multiplier": 1,
                "convert_to_trash": False,
                "gain_items": {},
                "custom_effect": None,
                "durability_loss": 0
            }
        
        # Default result dict
        result = {
            "triggered": False, "type": None, "message": "",
            "lose_worm": False, "lose_catch": False, "lose_money": 0, "gain_money": 0,
            "cooldown_increase": 0,
            "catch_multiplier": 1,  # Mặc định x1
            "convert_to_trash": False,  # Mặc định False
            "gain_items": {},  # Item nhận được thêm
            "custom_effect": None,  # Cho các effect đặc biệt
            "durability_loss": 0  # Mất độ bền riêng
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
                result["message"] = f"**{event_data['name']}** {RANDOM_EVENT_MESSAGES[event_type]}"
                
                effect = event_data.get("effect")
                
                # === XỬ LÝ BAD EVENTS THEO NHÓM ===
                if effect == "lose_worm":
                    result["lose_worm"] = True
                    result["lose_catch"] = True  # Mất mồi thì thường mất luôn cá
                
                elif effect == "lose_catch":
                    result["lose_worm"] = True  # Vẫn mất mồi đã dùng
                    result["lose_catch"] = True
                
                elif effect == "thief":
                    result["custom_effect"] = "cat_steal"  # Xử lý riêng: mất cá to nhất
                    result["lose_worm"] = True  # Mất mồi
                
                elif effect == "lose_money_50":
                    result["lose_money"] = 50
                elif effect == "lose_money_100":
                    result["lose_money"] = 100
                elif effect == "lose_money_200":
                    result["lose_money"] = 200
                elif effect == "lose_money_percent":
                    result["custom_effect"] = "snake_bite"  # Trừ 5%
                    result["lose_money"] = -1  # Flag: tính % trong xử lý
                
                elif effect == "cooldown_short":
                    result["cooldown_increase"] = 120  # 2 phút
                elif effect == "cooldown_medium":
                    result["cooldown_increase"] = 300  # 5 phút
                elif effect == "cooldown_long":
                    result["cooldown_increase"] = 600  # 10 phút
                
                elif effect == "lose_turn":
                    result["lose_catch"] = True  # Mất cá
                    # Không phạt thêm gì khác
                
                elif effect == "durability_hit":
                    result["custom_effect"] = "durability_hit"  # Trừ độ bền nặng
                    result["durability_loss"] = -5  # Trừ 5 độ bền
                    result["lose_catch"] = True  # Thường vướng rác thì ko có cá
                
                elif effect == "lose_all_bait":
                    result["custom_effect"] = "lose_all_bait"
                
                # === XỬ LÝ GOOD EVENTS THEO NHÓM ===
                elif effect == "gain_money_small":
                    result["gain_money"] = random.randint(30, 80)
                elif effect == "gain_money_medium":
                    result["gain_money"] = random.randint(100, 200)
                elif effect == "gain_money_large":
                    result["gain_money"] = random.randint(300, 500)
                elif effect == "gain_money_huge":
                    result["gain_money"] = 1000  # Jackpot

                elif effect == "bet_loss":
                    # Random số tiền thua từ 100 đến 300
                    amount = random.randint(100, 300)
                    result["lose_money"] = amount

                elif effect == "bet_win":
                    # Random số tiền thắng từ 100 đến 300
                    amount = random.randint(100, 300)
                    result["gain_money"] = amount

                elif effect == "gain_worm_5":
                    result["gain_items"] = {"worm": 5}
                elif effect == "gain_worm_10":
                    result["gain_items"] = {"worm": 10}
                
                elif effect == "gain_chest_1":
                    result["gain_items"] = {"treasure_chest": 1}
                elif effect == "gain_chest_2":
                    result["gain_items"] = {"treasure_chest": 2}
                
                elif effect == "gain_pearl":
                    result["gain_items"] = {"pearl": 1}
                elif effect == "gain_ring":
                    result["gain_items"] = {"ring": 1}

                elif effect == "multiply_catch_2":
                    result["catch_multiplier"] = 2
                elif effect == "multiply_catch_3":
                    result["catch_multiplier"] = 3

                elif effect == "reset_cooldown":
                    result["cooldown_increase"] = -999  # Trừ số lớn để về 0

                elif effect == "restore_durability":
                    result["custom_effect"] = "restore_durability"  # Xử lý ngoài _fish_action

                elif effect == "lucky_buff":
                    result["custom_effect"] = "lucky_buff"

                elif effect == "avoid_bad_event":
                    result["custom_effect"] = "sixth_sense"
                
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
    
    # ==================== ROD SYSTEM HELPERS ====================
    
    async def get_rod_data(self, user_id: int) -> tuple:
        """Get rod level and durability for user (rod_level, rod_durability)"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT rod_level, rod_durability FROM economy_users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                # Default: level 1, full durability
                return 1, ROD_LEVELS[1]["durability"]
            return row[0] or 1, row[1] or ROD_LEVELS[1]["durability"]
        except Exception as e:
            print(f"[ROD] Error getting rod data: {e}")
            return 1, ROD_LEVELS[1]["durability"]
    
    async def update_rod_data(self, user_id: int, durability: int, level: int = None):
        """Update rod durability (and level if provided)"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                if level is not None:
                    await db.execute(
                        "UPDATE economy_users SET rod_durability = ?, rod_level = ? WHERE user_id = ?",
                        (durability, level, user_id)
                    )
                else:
                    await db.execute(
                        "UPDATE economy_users SET rod_durability = ? WHERE user_id = ?",
                        (durability, user_id)
                    )
                await db.commit()
            print(f"[ROD] Updated user {user_id}: durability={durability}, level={level}")
        except Exception as e:
            print(f"[ROD] Error updating rod data: {e}")
    
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
        
        # --- GET ROD DATA ---
        rod_lvl, rod_durability = await self.get_rod_data(user_id)
        rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
        
        # --- CHECK DURABILITY & AUTO REPAIR ---
        repair_msg = ""
        is_broken_rod = False  # Flag to treat as no-worm when durability is broken
        
        if rod_durability <= 0:
            repair_cost = rod_config["repair"]
            balance = await get_user_balance(user_id)
            
            if balance >= repair_cost:
                # Auto repair
                await add_seeds(user_id, -repair_cost)
                rod_durability = rod_config["durability"]
                await self.update_rod_data(user_id, rod_durability)
                repair_msg = f"\n🛠️ *Cần gãy! Đã tự động sửa (-{repair_cost} Hạt)*"
                print(f"[FISHING] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} auto-repaired rod (-{repair_cost})")
            else:
                # Not enough money to repair - allow fishing but with broken rod penalties
                is_broken_rod = True
                repair_msg = f"\n⚠️ **Cần câu đã gãy!** Phí sửa là {repair_cost} Hạt. Bạn đang câu với cần gãy (chỉ 1% cá hiếm, 1 item/lần, không rương)."
                print(f"[FISHING] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} fishing with broken rod (no funds to repair)")
        
        # --- CHECK COOLDOWN (using rod-based cooldown) ---
        remaining = await self.get_fishing_cooldown_remaining(user_id)
        if remaining > 0:
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            msg = f"⏱️ **{username_display}** chờ chút nhen! Cần chờ {remaining}s nữa mới được câu lại! (Cooldown: {rod_config['cd']}s)"
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
        
        print(f"[FISHING] {username} started fishing (user_id={user_id}) [rod_lvl={rod_lvl}] [durability={rod_durability}] [has_worm={has_worm}]")
        
        # Set cooldown using rod-based cooldown
        self.fishing_cooldown[user_id] = time.time() + rod_config["cd"]
        
        # Casting animation
        wait_time = random.randint(1, 5)
        
        # Thêm thông báo nhỏ nếu tự mua mồi hoặc không có mồi
        status_text = ""
        if auto_bought:
            status_text = f"\n💸 *(-{WORM_COST} Hạt mua mồi)*"
        elif not has_worm:
            status_text = "\n⚠️ *Không có mồi (Tỉ lệ rác cao)*"
        
        rod_status = f"\n🎣 *{rod_config['emoji']} {rod_config['name']} (Cooldown: {rod_config['cd']}s)*"

        casting_msg = await channel.send(
            f"🎣 **{username}** quăng cần... Chờ cá cắn câu... ({wait_time}s){status_text}{rod_status}"
        )
        await asyncio.sleep(wait_time)
        
        # ==================== CHECK FISH BUCKET LIMIT ====================
        # Get current fish count
        current_inventory = await get_inventory(user_id)
        fish_count = sum(v for k, v in current_inventory.items() if k in ALL_FISH)
        
        # If bucket is full (15+ fish), block fishing
        if fish_count >= 15:
            embed = discord.Embed(
                title=f"⚠️ XÔ ĐÃ ĐẦY - {username}!",
                description=f"🪣 Xô cá của bạn đã chứa {fish_count} con cá (tối đa 15).\n\nHãy bán cá để có chỗ trống, rồi quay lại câu tiếp!",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Hãy dùng lệnh bán cá để bán bớt nhé.")
            await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
            # Remove worm cost from refund check - it was already consumed
            print(f"[FISHING] {username} blocked: bucket full ({fish_count}/15 fish)")
            return
        
        # ==================== TRIGGER RANDOM EVENTS ====================
        
        # Check if user was protected from bad event
        was_protected = False
        if hasattr(self, "avoid_event_users") and self.avoid_event_users.get(user_id, False):
            was_protected = True
        
        event_result = await self.trigger_random_event(user_id, channel.guild.id)
        
        # If user was protected, show protection message
        if was_protected:
            embed = discord.Embed(
                title=f"🛡️ BẢO VỆ - {username}!",
                description="✨ **Giác Quan Thứ 6 hoặc Đi Chùa bảo vệ bạn!**\n\nBạn an toàn thoát khỏi một sự kiện xấu!",
                color=discord.Color.gold()
            )
            await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
            await asyncio.sleep(1)
            casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
        # Initialize durability loss (apply after event check)
        durability_loss = 1  # Default: 1 per cast
        
        if event_result.get("triggered", False):
            # Random event occurred!
            event_message = event_result["message"]
            event_type = event_result.get("type")
            
            # *** DURABILITY LOSS FROM EVENTS ***
            if event_type == "equipment_break":
                # Gãy cần: Trừ hết độ bền
                durability_loss = rod_durability  # Trừ sạch về 0
                event_message += " (**Cần bị gãy hoàn toàn!**)"
            elif event_type in ["snapped_line", "plastic_trap"]:
                # Đứt dây / Vướng rác: Trừ 5 độ bền
                durability_loss = 5
                event_message += " (-5 Độ bền cần)"
            elif event_type == "predator":
                # Cá dữ: Trừ 3 độ bền
                durability_loss = 3
                event_message += " (-3 Độ bền cần)"
            
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
            
            elif event_result.get("custom_effect") == "restore_durability":
                # Hồi độ bền: +20 độ bền (không vượt quá max)
                max_durability = rod_config["durability"]
                rod_durability = min(max_durability, rod_durability + 20)
                await self.update_rod_data(user_id, rod_durability)
                event_message += f" (Độ bền +20: {rod_durability}/{max_durability})"
                print(f"[EVENT] {username} restored rod durability to {rod_durability}")
            
            # Adjust cooldown (golden_turtle có thể là -30 để reset)
            if event_result.get("cooldown_increase", 0) != 0:
                if event_result["cooldown_increase"] < 0:
                    # Reset cooldown (golden_turtle)
                    self.fishing_cooldown[user_id] = time.time()
                    event_message += " (Cooldown xóa sạch!)"
                    print(f"[EVENT] {username} cooldown reset")
                else:
                    self.fishing_cooldown[user_id] = time.time() + rod_config["cd"] + event_result["cooldown_increase"]
            else:
                self.fishing_cooldown[user_id] = time.time() + rod_config["cd"]
            
            # If lose_catch, don't process fishing
            if event_result.get("lose_catch", False):
                embed = discord.Embed(
                    title=f"⚠️ KIẾP NẠN - {username}!",
                    description=event_message,
                    color=discord.Color.red()
                )
                # Apply durability loss before returning
                rod_durability = max(0, rod_durability - durability_loss)
                await self.update_rod_data(user_id, rod_durability)
                embed.set_footer(text=f"🛡️ Độ bền: {rod_durability}/{rod_config['durability']}")
                await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
                print(f"[EVENT] {username} triggered {event_type} - fishing cancelled, durability loss: {durability_loss}")
                return
            
            # Otherwise, display event message and continue fishing
            event_type_data = RANDOM_EVENTS.get(event_type, {})
            is_good_event = event_type_data.get("type") == "good"
            color = discord.Color.green() if is_good_event else discord.Color.orange()
            event_title = f"🌟 PHƯỚC LÀNH - {username}!" if is_good_event else f"⚠️ KIẾP NẠN - {username}!"
            embed = discord.Embed(
                title=event_title,
                description=event_message,
                color=color
            )
            await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
            
            # Wait a bit before showing catch
            await asyncio.sleep(1)
            casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
        # ==================== NORMAL FISHING PROCESSING ====================
        
        # Roll số lượng cá (1-5) với tỉ lệ giảm dần
        # NHƯNG: Nếu không có mồi HOẶC cần gãy -> chỉ được 1 cá hoặc 1 rác (không multiple)
        if has_worm and not is_broken_rod:
            num_fish = random.choices([1, 2, 3, 4, 5], weights=CATCH_COUNT_WEIGHTS, k=1)[0]
        else:
            num_fish = 1  # Không mồi hoặc cần gãy = 1 cá thôi
        
        # Apply catch multiplier from events (e.g., Golden Hook)
        multiplier = event_result.get("catch_multiplier", 1)
        original_num_fish = num_fish
        num_fish = num_fish * multiplier
        if multiplier > 1:
            print(f"[EVENT] {username} activated catch_multiplier x{multiplier}: {original_num_fish} → {num_fish} fish")
        
        # Roll trash (độc lập)
        # NHƯNG: Nếu không có mồi HOẶC cần gãy -> chỉ roll trash hoặc cá, không vừa cá vừa rác vừa rương
        if has_worm and not is_broken_rod:
            trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
        else:
            # Không mồi hoặc cần gãy: Xác suất cao là rác (50/50 rác hoặc cá)
            trash_count = random.choices([0, 1], weights=[50, 50], k=1)[0]
        
        # Roll chest (độc lập, tỉ lệ thấp)
        # NHƯNG: Nếu không có mồi HOẶC cần gãy -> không bao giờ ra rương
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        if has_worm and not is_broken_rod:
            chest_weights = [95, 5] if not is_boosted else [90, 10]
            chest_count = random.choices([0, 1], weights=chest_weights, k=1)[0]
        else:
            chest_count = 0  # Không mồi = không ra rương
        
        results = {"fish": num_fish}
        if trash_count > 0:
            results["trash"] = trash_count
        if chest_count > 0:
            results["chest"] = chest_count
        
        print(f"[FISHING] {username} rolled: {num_fish} fish, {trash_count} trash, {chest_count} chest [has_worm={has_worm}]")
        
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        boost_text = " ✨**(CÂY BUFF!)**✨" if is_boosted else ""
        
        # Track caught items for sell button
        self.caught_items[user_id] = {}
        
        # Build summary display and process all results
        fish_display = []
        fish_only_items = {}
        
        # FIX: Track if rare fish already caught this turn (Max 1 rare per cast)
        caught_rare_this_turn = False
        
        # Chọn loot table dựa trên có worm hay không, hoặc cần gãy
        if has_worm and not is_broken_rod:
            # Có mồi = dùng loot table bình thường (có cả cá hiếm)
            loot_table = LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
        else:
            # Không có mồi HOẶC cần gãy = dùng loot table giảm cực (chỉ rác và cá thường, 1% hiếm)
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
            
            # *** APPLY ROD LUCK BONUS ***
            rare_ratio = min(0.9, rare_ratio + rod_config["luck"])  # Cap at 90% max
            common_ratio = 1.0 - rare_ratio  # Adjust common to maintain 100% total
            
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
                print(f"[FISHING] {username} caught RARE fish: {fish['key']} ✨ (Max 1 rare per cast, Rod Luck: +{int(rod_config['luck']*100)}%)")
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
        
        # Build description with broken rod warning if needed
        desc_parts = ["\n".join(fish_display) if fish_display else "Không có gì"]
        if is_broken_rod:
            desc_parts.append("\n⚠️ **CẢNH BÁO: Cần câu gãy!** (Chỉ 1% cá hiếm, 1 item/lần, không rương)")
        
        embed = discord.Embed(
            title=title,
            description="".join(desc_parts),
            color=discord.Color.red() if is_broken_rod else (discord.Color.gold() if title_earned else (discord.Color.blue() if total_catches == 1 else discord.Color.gold()))
        )
        
        if title_earned:
            embed.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã bắt được **tất cả các loại cá**!\nChúc mừng bạn trở thành **Vua Câu Cá**! 🎉\nXem `/suutapca` để xác nhận!",
                inline=False
            )
        
        # *** UPDATE DURABILITY AFTER FISHING ***
        rod_durability = max(0, rod_durability - durability_loss)
        await self.update_rod_data(user_id, rod_durability)
        
        durability_status = f"🛡️ Độ bền: {rod_durability}/{rod_config['durability']}"
        embed.set_footer(text=f"Tổng câu được: {total_catches} vật{boost_text} | {durability_status}")
        
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
        
        # Get username
        username = ctx.user.name if is_slash else ctx.author.name
        
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
        triggered_event = None
        
        # Roll event
        rand = random.random()
        current_chance = 0
        
        # Debug log
        print(f"[SELL EVENT DEBUG] User: {username}, base_total: {base_total}, random value: {rand:.4f}")
        
        for ev_key, ev_data in SELL_EVENTS.items():
            current_chance += ev_data["chance"]
            print(f"[SELL EVENT DEBUG] Checking {ev_key}: chance {ev_data['chance']}, cumulative {current_chance:.4f}, trigger? {rand < current_chance}")
            if rand < current_chance:
                triggered_event = ev_key
                print(f"[SELL EVENT DEBUG] ✅ TRIGGERED: {triggered_event}")
                break
        
        if not triggered_event:
            print(f"[SELL EVENT DEBUG] ❌ No event triggered (final cumulative: {current_chance:.4f})")
        
        # Apply event logic
        special_rewards = []
        if triggered_event:
            ev_data = SELL_EVENTS[triggered_event]
            event_name = ev_data["name"]
            
            # Tính toán tiền sau sự kiện
            # Công thức: (Gốc * Multiplier) + Flat Bonus
            final_total = int(base_total * ev_data["mul"]) + ev_data["flat"]
            
            # Cho phép âm tiền nếu sự kiện xấu quá nghiêm trọng
            
            diff = final_total - base_total
            sign = "+" if diff >= 0 else ""
            
            # Xử lý special effects (vật phẩm thưởng)
            if "special" in ev_data:
                special_type = ev_data["special"]
                
                if special_type == "chest":
                    await self.add_inventory_item(user_id, "treasure_chest", "tool")
                    special_rewards.append("🎁 +1 Rương Kho Báu")
                
                elif special_type == "worm":
                    await self.add_inventory_item(user_id, "worm", "bait")
                    special_rewards.append("🪱 +5 Mồi Câu")
                
                elif special_type == "pearl":
                    await self.add_inventory_item(user_id, "pearl", "tool")
                    special_rewards.append("🔮 +1 Ngọc Trai")
                
                elif special_type == "durability":
                    # Thêm độ bền cho cần câu hiện tại
                    user_rod_level, user_rod_durability = await self.get_rod_data(user_id)
                    max_durability = ROD_LEVELS[user_rod_level]["durability"]
                    new_durability = min(max_durability, user_rod_durability + 10)
                    await self.update_rod_data(user_id, new_durability)
                    special_rewards.append("🛠️ +10 Độ Bền Cần Câu")
                
                elif special_type == "rod":
                    await self.add_inventory_item(user_id, "rod_material", "material")
                    special_rewards.append("🎣 +1 Vật Liệu Nâng Cấp Cần")
                
                elif special_type == "lottery":
                    if random.random() < 0.1:  # 10% win chance
                        lottery_reward = 500
                        await add_seeds(user_id, lottery_reward)
                        final_total += lottery_reward
                        special_rewards.append(f"🎉 **TRÚNG SỐ! +{lottery_reward} Hạt!**")
                    else:
                        special_rewards.append("❌ Vé số không trúng")
            
            # Formatting message
            if ev_data["type"] == "good":
                event_color = discord.Color.gold()
                event_msg = f"\n🌟 **SỰ KIỆN: {event_name}**\n_{SELL_MESSAGES[triggered_event]}_\n👉 **Biến động:** {sign}{diff} Hạt"
            else:
                event_color = discord.Color.orange()
                event_msg = f"\n⚠️ **SỰ CỐ: {event_name}**\n_{SELL_MESSAGES[triggered_event]}_\n👉 **Thiệt hại:** {diff} Hạt"
                
            print(f"[SELL EVENT] {ctx.user.name if is_slash else ctx.author.name} triggered {triggered_event}: {base_total} -> {final_total}")

        # Remove items & Add money
        for fish_key in selected_fish.keys():
            await remove_item(user_id, fish_key, selected_fish[fish_key])
        
        await add_seeds(user_id, final_total)
        
        # 4. Display sell event notification FIRST (if triggered)
        if triggered_event:
            if SELL_EVENTS[triggered_event]["type"] == "good":
                title = f"🌟 PHƯỚC LÀNH - {username}!"
                event_embed_color = discord.Color.gold()
            else:
                title = f"⚠️ KIẾP NẠN - {username}!"
                event_embed_color = discord.Color.orange()
            
            diff = final_total - base_total
            sign = "+" if diff >= 0 else ""
            event_detail = f"{SELL_MESSAGES[triggered_event]}\n\n💰 **{event_name}**"
            
            event_embed = discord.Embed(
                title=title,
                description=event_detail,
                color=event_embed_color
            )
            event_embed.add_field(
                name="📊 Ảnh hưởng giá bán",
                value=f"Gốc: {base_total} Hạt\n{sign}{diff} Hạt\n**= {final_total} Hạt**",
                inline=False
            )
            
            # Add special rewards if any
            if special_rewards:
                event_embed.add_field(
                    name="🎁 Phần Thưởng Đặc Biệt",
                    value="\n".join(special_rewards),
                    inline=False
                )
            
            if is_slash:
                await ctx.followup.send(content=f"<@{user_id}>", embed=event_embed, ephemeral=False)
            else:
                await ctx.send(content=f"<@{user_id}>", embed=event_embed)
        
        # 5. Display main sell result embed
        fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in selected_fish.items()])
        
        embed = discord.Embed(
            title=f"💰 **{username}** bán {sum(selected_fish.values())} con cá",
            description=f"{fish_summary}\n\n💵 **Tổng nhận:** {final_total} Hạt",
            color=discord.Color.green()
        )
        
        # Check achievement "millionaire" (Tích lũy tiền)
        if hasattr(self, "update_user_stat"):
            total_earned = await self.update_user_stat(user_id, "coins_earned", final_total)
            if total_earned >= 100000:
                await self.check_achievement(user_id, "millionaire", ctx.channel, ctx.guild.id if hasattr(ctx, 'guild') else ctx_or_interaction.guild.id)

        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=False)
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
        """Recycle trash logic - auto converts 10 trash → 1 fertilizer (recycle ALL trash)"""
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
        
        # Check if user has enough trash (at least 10)
        if trash_count < 10:
            msg = f"❌ Bạn cần 10 rác để tạo phân bón, hiện có {trash_count}"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Calculate how many fertilizers can be created
        fertilizer_count = trash_count // 10
        trash_used = fertilizer_count * 10
        trash_remaining = trash_count - trash_used
        
        # Remove all trash items (in groups of 10)
        trash_removed = 0
        for key in list(inventory.keys()):
            if key.startswith("trash_") and trash_removed < trash_used:
                qty_to_remove = min(inventory[key], trash_used - trash_removed)
                await remove_item(user_id, key, qty_to_remove)
                trash_removed += qty_to_remove
        
        # Add fertilizers (multiply the count)
        for _ in range(fertilizer_count):
            await self.add_inventory_item(user_id, "fertilizer", "tool")
        
        embed = discord.Embed(
            title="✅ Tái Chế Thành Công",
            description=f"🗑️ {trash_used} Rác → 🌱 {fertilizer_count} Phân Bón",
            color=discord.Color.green()
        )
        if trash_remaining > 0:
            embed.add_field(name="Rác còn lại", value=f"{trash_remaining} (cần 10 để tạo 1 phân)", inline=False)
        
        username = ctx.user.name if is_slash else ctx.author.name
        print(f"[RECYCLE] {username} recycled {trash_used} trash → {fertilizer_count} fertilizer")
        
        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    
    # ==================== ROD UPGRADE ====================
    
    @app_commands.command(name="nangcap", description="Nâng cấp cần câu (Giảm hồi chiêu, tăng bền, tăng may mắn)")
    async def upgrade_rod_slash(self, interaction: discord.Interaction):
        """Upgrade rod via slash command"""
        await self._upgrade_rod_action(interaction)
    
    @commands.command(name="nangcap", description="Nâng cấp cần câu")
    async def upgrade_rod_prefix(self, ctx):
        """Upgrade rod via prefix command"""
        await self._upgrade_rod_action(ctx)
    
    async def _upgrade_rod_action(self, ctx_or_interaction):
        """Upgrade rod logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get current rod
        cur_lvl, cur_durability = await self.get_rod_data(user_id)
        
        if cur_lvl >= 5:
            msg = "🌟 Cần câu của bạn đã đạt cấp tối đa **(Poseidon)**!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        next_lvl = cur_lvl + 1
        rod_info = ROD_LEVELS[next_lvl]
        cost = rod_info["cost"]
        
        # Check balance
        balance = await get_user_balance(user_id)
        if balance < cost:
            msg = f"❌ Bạn cần **{cost:,} Hạt** để nâng lên **{rod_info['name']}**!\nHiện có: **{balance:,} Hạt**"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Deduct seeds and upgrade
        await add_seeds(user_id, -cost)
        # When upgrading, restore full durability
        await self.update_rod_data(user_id, rod_info["durability"], next_lvl)
        
        # Build response embed
        embed = discord.Embed(
            title="✅ Nâng Cấp Cần Câu Thành Công!",
            description=f"**{rod_info['emoji']} {rod_info['name']}** (Cấp {next_lvl}/5)",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚡ Cooldown", value=f"**{rod_info['cd']}s** (giảm từ {ROD_LEVELS[cur_lvl]['cd']}s)", inline=True)
        embed.add_field(name="🛡️ Độ Bền", value=f"**{rod_info['durability']}** (tăng từ {ROD_LEVELS[cur_lvl]['durability']})", inline=True)
        embed.add_field(name="🍀 May Mắn", value=f"**+{int(rod_info['luck']*100)}%** Cá Hiếm" if rod_info['luck'] > 0 else "**Không thay đổi**", inline=True)
        embed.add_field(name="💰 Chi Phí", value=f"**{cost:,} Hạt**", inline=False)
        embed.set_footer(text="Độ bền đã được hồi phục hoàn toàn!")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
        
        print(f"[ROD] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} upgraded rod to level {next_lvl}")
    
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
            # Get current tree state
            tree_cog = self.bot.get_cog("CommunityCog")
            if not tree_cog:
                raise Exception("CommunityCog not found!")
            
            # Get current tree data
            lvl, prog, total, season, tree_channel_id, _ = await tree_cog.get_tree_data(guild_id)
            
            # Calculate new progress and potential level-up
            level_reqs = tree_cog.get_level_reqs(season)
            req = level_reqs.get(lvl + 1, level_reqs[6])
            new_progress = prog + boost_amount
            new_total = total + boost_amount
            new_level = lvl
            leveled_up = False
            
            # Handle level ups
            while new_progress >= req and new_level < 6:
                new_level += 1
                new_progress = new_progress - req
                leveled_up = True
                req = level_reqs.get(new_level + 1, level_reqs[6])
            
            # Update tree in database
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE server_tree SET current_level = ?, current_progress = ?, total_contributed = ? WHERE guild_id = ?",
                    (new_level, new_progress, new_total, guild_id)
                )
                await db.commit()
            
            # Build response embed
            embed = discord.Embed(
                title="🌾 Phân Bón Hiệu Quả!",
                description=f"**+{boost_amount}** điểm cho Cây Server!",
                color=discord.Color.green()
            )
            
            # Add level-up notification if applicable
            if leveled_up:
                embed.add_field(
                    name="🌳 CÂY ĐÃ LÊN CẤP!",
                    value=f"**{TREE_NAMES[new_level]}** (Cấp {new_level}/6)",
                    inline=False
                )
                embed.color = discord.Color.gold()
            else:
                embed.add_field(
                    name="Tiến độ",
                    value=f"**{int((new_progress / req) * 100) if req > 0 else 0}%** ({new_progress}/{req})",
                    inline=False
                )
            
            print(f"[FERTILIZER] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} used fertilizer: +{boost_amount} (Tree Level {new_level})")
            
            # Update tree embed in the designated channel
            if tree_channel_id:
                try:
                    print(f"[FERTILIZER] Updating tree message in channel {tree_channel_id}")
                    await tree_cog.update_or_create_pin_message(guild_id, tree_channel_id)
                    print(f"[FERTILIZER] ✅ Tree embed updated successfully")
                    
                    # Send notification embed to tree channel
                    tree_channel = self.bot.get_channel(tree_channel_id)
                    if tree_channel:
                        user_name = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                        notification_embed = discord.Embed(
                            title="🌾 Phân Bón Được Sử Dụng!",
                            description=f"**{user_name}** đã dùng Phân Bón",
                            color=discord.Color.green()
                        )
                        notification_embed.add_field(
                            name="📈 Mức tăng",
                            value=f"**+{boost_amount}** điểm",
                            inline=False
                        )
                        
                        if leveled_up:
                            notification_embed.add_field(
                                name="🎉 Cây đã lên cấp!",
                                value=f"**{TREE_NAMES[new_level]}** (Cấp {new_level}/6)",
                                inline=False
                            )
                            notification_embed.color = discord.Color.gold()
                        else:
                            notification_embed.add_field(
                                name="📊 Tiến độ",
                                value=f"**{int((new_progress / req) * 100) if req > 0 else 0}%** ({new_progress}/{req})",
                                inline=False
                            )
                        
                        await tree_channel.send(embed=notification_embed)
                except Exception as e:
                    print(f"[FERTILIZER] ❌ Failed to update tree embed: {type(e).__name__}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[FERTILIZER] ⚠️ No tree channel configured for guild {guild_id}")
        
        except Exception as e:
            print(f"[FERTILIZER] Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
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
        """View collection logic with pagination"""
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
        
        # Build common fish embed (Page 1)
        embed_common = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_fish}** ({completion_percent}%)\n📄 **Trang 1/2 - Cá Thường**",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        if current_title:
            embed_common.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add common fish section (split into multiple fields to avoid length limit)
        common_display = []
        for fish in COMMON_FISH:
            emoji = "✅" if fish['key'] in common_caught else "❌"
            common_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        # Split common fish into 2 columns if too many
        if len(common_display) > 30:
            mid = len(common_display) // 2
            col1 = "\n".join(common_display[:mid])
            col2 = "\n".join(common_display[mid:])
            
            embed_common.add_field(
                name=f"🐠 Cá Thường ({len(common_caught)}/{len(COMMON_FISH)}) - Phần 1",
                value=col1 if col1 else "Không có",
                inline=True
            )
            embed_common.add_field(
                name="Phần 2",
                value=col2 if col2 else "Không có",
                inline=True
            )
        else:
            embed_common.add_field(
                name=f"🐠 Cá Thường ({len(common_caught)}/{len(COMMON_FISH)})",
                value="\n".join(common_display) if common_display else "Không có",
                inline=False
            )
        
        embed_common.set_footer(text="Bấm nút → để xem cá hiếm")
        
        # Build rare fish embed (Page 2)
        embed_rare = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_fish}** ({completion_percent}%)\n📄 **Trang 2/2 - Cá Hiếm**",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        if current_title:
            embed_rare.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add rare fish section (split into multiple fields to avoid length limit)
        rare_display = []
        for fish in RARE_FISH:
            emoji = "✅" if fish['key'] in rare_caught else "❌"
            rare_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        # Split rare fish into 2 columns if too many
        if len(rare_display) > 20:
            mid = len(rare_display) // 2
            col1 = "\n".join(rare_display[:mid])
            col2 = "\n".join(rare_display[mid:])
            
            embed_rare.add_field(
                name=f"✨ Cá Hiếm ({len(rare_caught)}/{len(RARE_FISH)}) - Phần 1",
                value=col1 if col1 else "Không có",
                inline=True
            )
            embed_rare.add_field(
                name="Phần 2",
                value=col2 if col2 else "Không có",
                inline=True
            )
        else:
            embed_rare.add_field(
                name=f"✨ Cá Hiếm ({len(rare_caught)}/{len(RARE_FISH)})",
                value="\n".join(rare_display) if rare_display else "Không có",
                inline=False
            )
        
        # Add completion message
        if is_complete:
            embed_rare.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã trở thành **👑 VUA CÂU CÁ 👑**!\nCảm ơn sự kiên trì của bạn! 🎉",
                inline=False
            )
        else:
            missing_count = total_all_fish - total_caught
            embed_rare.add_field(
                name="📝 Còn Lại",
                value=f"Bạn còn cần bắt **{missing_count}** loại cá nữa để trở thành Vua Câu Cá! 💪",
                inline=False
            )
        
        embed_rare.set_footer(text="Bấm nút ← để xem cá thường • Mỗi lần bắt một loại cá mới, nó sẽ được thêm vào sưu tập!")
        
        # Create pagination view
        class CollectionPaginationView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
                self.current_page = 0  # 0 = common, 1 = rare
                self.message = None
            
            @discord.ui.button(label="← Cá Thường", style=discord.ButtonStyle.primary, custom_id="collection_prev")
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != user_id:
                    await interaction.response.send_message("❌ Bạn không có quyền sử dụng nút này!", ephemeral=True)
                    return
                
                self.current_page = 0
                await interaction.response.edit_message(embed=embed_common, view=self)
            
            @discord.ui.button(label="Cá Hiếm →", style=discord.ButtonStyle.primary, custom_id="collection_next")
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != user_id:
                    await interaction.response.send_message("❌ Bạn không có quyền sử dụng nút này!", ephemeral=True)
                    return
                
                self.current_page = 1
                await interaction.response.edit_message(embed=embed_rare, view=self)
        
        view = CollectionPaginationView()
        
        if is_slash:
            view.message = await ctx.followup.send(embed=embed_common, view=view)
        else:
            view.message = await ctx.send(embed=embed_common, view=view)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

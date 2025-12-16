"""Game constants and data tables for fishing system"""

DB_PATH = "./data/database.db"

# Loot tables
LOOT_TABLE_NORMAL = {
    "trash": 30, "common_fish": 60, "rare_fish": 5, "chest": 5
}

LOOT_TABLE_BOOST = {
    "trash": 15, "common_fish": 75, "rare_fish": 5, "chest": 5
}

LOOT_TABLE_NO_WORM = {
    "trash": 50, "common_fish": 49, "rare_fish": 1, "chest": 0
}

CATCH_COUNT_WEIGHTS = [70, 20, 8, 2, 0]

# Common fish (60+ entries)
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
    {"key": "ca_ma_ca_rong", "name": "Cá Ma Cà Rồng", "emoji": "🧛", "sell_price": 85},

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

# Legendary fish
LEGENDARY_FISH = [
    {
        "key": "thuong_luong",
        "name": "Thuồng Luồng",
        "emoji": "🐍🌊",
        "sell_price": 500,
        "description": "Quái vật sông nước trong truyền thuyết Việt Nam. Kẻ cai trị những dòng nước xoáy dữ dội nhất.",
        "condition": "river_storm",  # Chỉ xuất hiện ở Sông khi trời Mưa Bão
        "image_url": "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/fishing-game/legendary-fish/thuongluong.png",
        "level": 5,  # Cần cần câu level 5 trở lên để có cơ hội catch
        "spawn_chance": 0.01,  # 1% - Balanced by storm rarity
        "achievement": "river_lord",
        "time_restriction": None,  # No time limit
    },
    {
        "key": "ca_ngan_ha",
        "name": "Cá Ngân Hà",
        "emoji": "🌌✨",
        "sell_price": 600,
        "description": "Cơ thể nó chứa đựng cả một vũ trụ thu nhỏ. Chỉ bơi xuống trần gian vào những đêm đầy sao.",
        "condition": "clear_night",  # Chỉ xuất hiện vào Ban Đêm khi trời Quang Mây (00:00-04:00)
        "image_url": "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/fishing-game/legendary-fish/canganha.png",
        "level": 5,
        "spawn_chance": 0.008,  # 0.8% at night (reduced from 2%)
        "achievement": "star_walker",
        "time_restriction": (0, 4),  # 00:00-04:00
    },
    {
        "key": "ca_phuong_hoang",
        "name": "Cá Phượng Hoàng",
        "emoji": "🔥🦅",
        "sell_price": 550,
        "description": "Sinh vật kỳ bí rực cháy dưới nước. Truyền thuyết nói rằng nó mang lại sự hồi sinh.",
        "condition": "noon_sun",  # Chỉ xuất hiện vào 12h trưa (Giờ Ngọ) khi nắng gắt
        "image_url": "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/fishing-game/legendary-fish/caphuonghoang.png",
        "level": 5,
        "spawn_chance": 0.008,  # 0.8% at noon (reduced from 1.5%)
        "achievement": "sun_guardian",
        "time_restriction": (12, 14),  # 12:00-14:00
    },
    {
        "key": "cthulhu_con",
        "name": "Cthulhu Non",
        "emoji": "🐙👁️",
        "sell_price": 666,
        "description": "Một thực thể cổ xưa đang say ngủ. Đừng nhìn vào mắt nó quá lâu nếu không muốn mất trí.",
        "condition": "deep_sea",  # Cần dùng mồi đặc biệt hoặc câu ở biển sâu, rare event
        "image_url": "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/fishing-game/legendary-fish/cthulunon.png",
        "level": 5,
        "spawn_chance": 0.0015,  # 0.15% (reduced from 0.5%)
        "achievement": "void_gazer",
        "time_restriction": None,  # Always available
    },
    {
        "key": "ca_voi_52hz",
        "name": "Cá Voi 52Hz",
        "emoji": "🐋💔",
        "sell_price": 800,
        "description": "Chú cá voi cô đơn nhất thế giới. Tiếng hát của nó không đồng loại nào nghe thấy được.",
        "condition": "silence",  # Chỉ xuất hiện khi server vắng vẻ (random cực thấp) hoặc sau sự kiện buồn
        "image_url": "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/fishing-game/legendary-fish/cavoi52hz.png",
        "level": 5,
        "spawn_chance": 0.0005,  # 0.05% (1/2000 - rarest)
        "achievement": "lonely_frequency",
        "time_restriction": None,  # Always available
    }
]

ALL_FISH = {fish["key"]: fish for fish in COMMON_FISH + RARE_FISH + LEGENDARY_FISH}
ALL_FISH["pearl"] = {"key": "pearl", "name": "Ngọc Trai", "emoji": "🔮", "sell_price": 150}
ALL_FISH["rod_material"] = {"key": "rod_material", "name": "Vật Liệu Nâng Cấp Cần", "emoji": "⚙️", "sell_price": 0}

COMMON_FISH_KEYS = [f["key"] for f in COMMON_FISH]
RARE_FISH_KEYS = [f["key"] for f in RARE_FISH]
LEGENDARY_FISH_KEYS = [f["key"] for f in LEGENDARY_FISH]

# Trash items
TRASH_ITEMS = [
    # --- Rác Cơ Bản (10 món) ---
    {"name": "Ủng Rách", "emoji": "🥾"},
    {"name": "Lon Nước", "emoji": "🥫"},
    {"name": "Xà Phòng Cũ", "emoji": "🧼"},
    {"name": "Mảnh Kính", "emoji": "🔨"},
    {"name": "Túi Ni Lông", "emoji": "🛍️"},
    {"name": "Chai Nhựa", "emoji": "🥤"},
    {"name": "Lốp Xe Hư", "emoji": "🍩"},
    {"name": "Cành Củi Khô", "emoji": "🪵"},
    {"name": "Giấy Báo Cũ", "emoji": "📰"},
    {"name": "Hộp Xốp", "emoji": "🥡"},

    # --- Rác Hữu Cơ & Sinh Vật Chết (10 món) ---
    {"name": "Vỏ Chuối", "emoji": "🍌"},
    {"name": "Xương Cá", "emoji": "🦴"},
    {"name": "Rong Biển", "emoji": "🌿"},
    {"name": "Xác Gián", "emoji": "🪳"},
    {"name": "Cùi Bắp", "emoji": "🌽"},
    {"name": "Trứng Ung", "emoji": "🥚"},
    {"name": "Đầu Tôm", "emoji": "🦐"},
    {"name": "Táo Cắn Dở", "emoji": "🍎"},
    {"name": "Hoa Héo", "emoji": "🥀"},
    {"name": "Cơm Thiu", "emoji": "🍚"},

    # --- Rác "Bựa" & Tục Tiễu (10 món) ---
    {"name": "Quần Xì Rách", "emoji": "🩲"},   
    {"name": "Cục Cứt", "emoji": "💩"},      
    {"name": "Ba Con Sói", "emoji": "🎈"},    
    {"name": "Băng Vệ Sinh", "emoji": "🩸"},     
    {"name": "Áo Dú Cũ", "emoji": "👙"},      
    {"name": "Vớ Thối", "emoji": "🧦"},      
    {"name": "Răng Giả", "emoji": "🦷"},     
    {"name": "Giấy Chùi Đít", "emoji": "🧻"},  
    {"name": "Tả Em Bé", "emoji": "👶"},      
    {"name": "Dép Tổ Ong Rách", "emoji": "🩴"}, 
]

# Chest loot
CHEST_LOOT = {
    "fertilizer": 30,
    "puzzle_piece": 20,
    "coin_pouch": 20,
    "gift_random": 30
}

GIFT_ITEMS = ["cafe", "flower", "ring", "gift", "chocolate", "card"]

# System values
WORM_COST = 5

# Tree names
TREE_NAMES = {
    1: "🌱 Hạt mầm",
    2: "🌿 Nảy mầm",
    3: "🎋 Cây non",
    4: "🌳 Trưởng thành",
    5: "🌸 Ra hoa",
    6: "🍎 Kết trái"
}

# Rod levels
ROD_LEVELS = {
    1: {"name": "Cần Tre", "cost": 0, "durability": 30, "repair": 50, "cd": 30, "luck": 0.0, "emoji": "🎋"},
    2: {"name": "Cần Thủy Tinh", "cost": 5000, "durability": 50, "repair": 100, "cd": 25, "luck": 0.0, "emoji": "🎣"},
    3: {"name": "Cần Carbon", "cost": 20000, "durability": 80, "repair": 200, "cd": 20, "luck": 0.02, "emoji": "✨🎣"},
    4: {"name": "Cần Hợp Kim", "cost": 50000, "durability": 120, "repair": 500, "cd": 15, "luck": 0.05, "emoji": "🔱"},
    5: {"name": "Cần Poseidon", "cost": 150000, "durability": 200, "repair": 1000, "cd": 10, "luck": 0.10, "emoji": "🔱✨"},
}

# Achievements
ACHIEVEMENTS = {
    "first_catch": {
        "name": "Tân Thủ Tập Sự",
        "description": "Câu được con cá đầu tiên",
        "condition_type": "first_catch",
        "target": 1,
        "reward_coins": 50,
        "emoji": "🎣",
        "role_id": 1450496409341263912  # Để trống - không cấp role cho thành tựu này
    },
    "worm_destroyer": {
        "name": "Kẻ Hủy Diệt Giun",
        "description": "Tiêu thụ tổng cộng 500 Giun",
        "condition_type": "worms_used",
        "target": 500,
        "reward_coins": 1000,
        "emoji": "🪱",
        "role_id": 1450496472817729729  # Để trống hoặc thay bằng role_id của server
    },
    "trash_master": {
        "name": "Hiệp Sĩ Môi Trường",
        "description": "Câu được 100 loại Rác",
        "condition_type": "trash_caught",
        "target": 100,
        "reward_coins": 500,
        "emoji": "🗑️",
        "role_id": 1450496511329833103
    },
    "millionaire": {
        "name": "Tỷ Phú",
        "description": "Kiếm được 100,000 Hạt từ bán cá",
        "condition_type": "coins_earned",
        "target": 100000,
        "reward_coins": 5000,
        "emoji": "💰",
        "role_id": 1450496548138909780
    },
    "dragon_slayer": {
        "name": "Long Vương",
        "description": "Câu được Cá Rồng (Cá hiếm nhất)",
        "condition_type": "caught_fish",
        "target": "ca_rong",
        "reward_coins": 1000,
        "emoji": "🐲",
        "role_id": 1450496587691327540
    },
    "unlucky": {
        "name": "Thánh Nhọ",
        "description": "Gặp sự kiện xấu 50 lần",
        "condition_type": "bad_events",
        "target": 50,
        "reward_coins": 500,
        "emoji": "😭",
        "role_id": 1450496621413404863
    },
    "lucky": {
        "name": "Bạn Của Thần Tài",
        "description": "Gặp sự kiện tốt 50 lần",
        "condition_type": "good_events",
        "target": 50,
        "reward_coins": 2000,
        "emoji": "✨",
        "role_id": 1450496661477396491
    },
    "collection_master": {
        "name": "Vua Câu Cá",
        "description": "Hoàn thành bộ sưu tập (câu được tất cả loại cá)",
        "condition_type": "collection_complete",
        "target": 1,
        "reward_coins": 10000,
        "emoji": "👑",
        "role_id": 1450409414111658024  # Dùng role "Vua Câu Cá" hiện tại
    },
    "survivor": {
        "name": "Kẻ Sống Sót",
        "description": "Vượt qua 100 sự kiện xấu khi câu cá",
        "condition_type": "bad_events",
        "target": 100,
        "reward_coins": 2000,
        "emoji": "🛡️",
        "role_id": None
    },
    "child_of_sea": {
        "name": "Đứa Con Của Biển",
        "description": "Kích hoạt sự kiện Global Reset (Tiếng Hát Cá Voi hoặc Thủy Triều Đỏ)",
        "condition_type": "global_reset",
        "target": 1,
        "reward_coins": 5000,
        "emoji": "🌊",
        "role_id": 1450517603675017276
    },
    "treasure_hunter": {
        "name": "Thợ Săn Kho Báu",
        "description": "Câu được 50 Rương Kho Báu",
        "condition_type": "chests",
        "target": 50,
        "reward_coins": 3000,
        "emoji": "💎",
        "role_id": 1450499187727925349
    },
    "market_manipulator": {
        "name": "Gian Thương",
        "description": "Bán cá trúng sự kiện Thị Trường Sôi Động 20 lần",
        "condition_type": "market_boom",
        "target": 20,
        "reward_coins": 2500,
        "emoji": "📈",
        "role_id": 1450517773888389140
    },
    "market_unluckiest": {
        "name": "Thánh Nhọ Chợ Cá",
        "description": "Bị Cướp mất trắng tiền bán cá 3 lần",
        "condition_type": "robbed",
        "target": 3,
        "reward_coins": 1000,
        "emoji": "😭",
        "role_id": 1450517849645908018
    },
    "god_of_wealth": {
        "name": "Thần Tài Gõ Cửa",
        "description": "Gặp sự kiện Thần Tài khi bán cá",
        "condition_type": "god_of_wealth",
        "target": 1,
        "reward_coins": 5000,
        "emoji": "💰",
        "role_id": 1450517908076892193
    },
    "diligent_smith": {
        "name": "Thợ Rèn Cần Mẫn",
        "description": "Tự động sửa cần câu 100 lần",
        "condition_type": "rods_repaired",
        "target": 100,
        "reward_coins": 1500,
        "emoji": "🔨",
        "role_id": 1450517830100582411
    },
    "rod_tycoon": {
        "name": "Ông Trùm Cần Câu",
        "description": "Nâng cấp cần câu lên cấp tối đa (Poseidon - Level 5)",
        "condition_type": "rod_level",
        "target": 5,
        "reward_coins": 10000,
        "emoji": "🔱",
        "role_id": 1450518071319203993
    },
    "master_recycler": {
        "name": "Nhà Tái Chế Đại Tài",
        "description": "Tái chế thành công 1000 rác thành phân bón",
        "condition_type": "trash_recycled",
        "target": 1000,
        "reward_coins": 2000,
        "emoji": "♻️",
        "role_id": 1450518142299279551
    },
    "boss_hunter": {
        "name": "Chuyên Gia Săn Boss",
        "description": "Câu được đủ bộ 3 con Boss: Megalodon, Kraken, Leviathan",
        "condition_type": "boss_hunter",
        "target": 1,
        "reward_coins": 20000,
        "emoji": "🦑",
        "role_id": 1450518235526205440
    },
    
    # ==================== LEGENDARY FISH ACHIEVEMENTS ====================
    
    "river_lord": {
        "name": "Chúa Tể Vùng Nước Xoáy",
        "description": "Câu được Thuồng Luồng trong cơn bão dữ",
        "condition_type": "caught_legendary",
        "target": "thuong_luong",
        "reward_coins": 5000,
        "emoji": "⛈️",
        "role_id": 1450518323770167327
    },
    
    "star_walker": {
        "name": "Kẻ Hái Sao",
        "description": "Câu được Cá Ngân Hà vào lúc đêm khuya thanh vắng",
        "condition_type": "caught_legendary",
        "target": "ca_ngan_ha",
        "reward_coins": 6000,
        "emoji": "🌌",
        "role_id": 1450518368368066611
    },
    
    "sun_guardian": {
        "name": "Ngự Lâm Quân Mặt Trời",
        "description": "Câu được Cá Phượng Hoàng dưới ánh nắng chói chang",
        "condition_type": "caught_legendary",
        "target": "ca_phuong_hoang",
        "reward_coins": 5500,
        "emoji": "☀️",
        "role_id": 1450518432582992004
    },
    
    "void_gazer": {
        "name": "Kẻ Nhìn Thấu Vực Thẳm",
        "description": "Bắt được Cthulhu Non và giữ được sự tỉnh táo",
        "condition_type": "caught_legendary",
        "target": "cthulhu_con",
        "reward_coins": 6666,
        "emoji": "👁️",
        "role_id": 1450518489247776880
    },
    
    "lonely_frequency": {
        "name": "Tần Số Cô Đơn",
        "description": "Tìm thấy Cá Voi 52Hz giữa đại dương mênh mông",
        "condition_type": "caught_legendary",
        "target": "ca_voi_52hz",
        "reward_coins": 8000,
        "emoji": "🐋",
        "role_id": 1450518545627877466
    },
    
    "legendary_hunter": {
        "name": "Thợ Săn Huyền Thoại",
        "description": "Sở hữu đủ 5 loài cá Legendary mới trong Hồ Cá",
        "condition_type": "full_legendary_set",
        "target": 5,
        "reward_coins": 50000,
        "emoji": "🏆",
        "role_id": 1450518602041004162
    }
}

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
    # effect: gain_money_*, gain_worm_*, gain_chest_*, gain_pearl, gain_ring, bonus_catch_*, duplicate_catch_*, reset_cooldown, restore_durability, lucky_buff, avoid_bad_event
    
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

    # --- Nhóm 3A: Câu Thêm Cá Ngẫu Nhiên (Bonus Catch) ---
    "school_of_fish":  {"chance": 0.005, "type": "good", "name": "Bão Cá!", "effect": "bonus_catch_3"},
    "golden_hook":     {"chance": 0.006, "type": "good", "name": "Lưỡi Vàng!", "effect": "bonus_catch_2"},
    "fish_feeding":    {"chance": 0.005, "type": "good", "name": "Cá Ăn Rộ!", "effect": "bonus_catch_2"},
    "friendly_otter":  {"chance": 0.004, "type": "good", "name": "Rái Cá Giúp!", "effect": "bonus_catch_2"},
    "net_fishing":     {"chance": 0.002, "type": "good", "name": "Vớt Lưới!", "effect": "bonus_catch_3"},
    
    # --- Nhóm 3B: Nhân Cá Giống Nhau (Duplicate Catch) ---
    "magic_bait":      {"chance": 0.003, "type": "good", "name": "Mồi Thần Kỳ!", "effect": "duplicate_catch_2"},
    "twin_fish":       {"chance": 0.002, "type": "good", "name": "Cá Song Sinh!", "effect": "duplicate_catch_2"},
    "mirror_water":    {"chance": 0.001, "type": "good", "name": "Mặt Nước Gương!", "effect": "duplicate_catch_3"},

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

    # --- Nhóm 6: GLOBAL RESET (Siêu Hiếm: 0.1%) ---
    "broken_hourglass": {"chance": 0.001, "type": "good", "name": "⏳ Đồng Hồ Cát Vỡ!", "effect": "global_reset"},
    "whale_song":       {"chance": 0.001, "type": "good", "name": "🐋 Tiếng Hát Cá Voi!", "effect": "global_reset"},
    "red_tide":         {"chance": 0.001, "type": "good", "name": "🌊 Thủy Triều Đỏ!", "effect": "global_reset"},
    "lantern_festival": {"chance": 0.001, "type": "good", "name": "🏮 Lễ Hội Thả Đèn!", "effect": "global_reset"},
    "dragon_blessing":  {"chance": 0.001, "type": "good", "name": "🐉 Long Vương Ban Phước!", "effect": "global_reset"},
    "energy_storm":     {"chance": 0.001, "type": "good", "name": "⚡ Cơn Bão Năng Lượng!", "effect": "global_reset"},
    "mermaid_tea":      {"chance": 0.001, "type": "good", "name": "🧚‍♀️ Tiệc Trà Tiên Cá!", "effect": "global_reset"},
    "monsoon":          {"chance": 0.001, "type": "good", "name": "🌬️ Gió Mùa Đông Bắc!", "effect": "global_reset"},
    "temple_bell":      {"chance": 0.001, "type": "good", "name": "🔔 Tiếng Chuông Chùa!", "effect": "global_reset"},
    "warp_gate":        {"chance": 0.001, "type": "good", "name": "🌌 Cổng Không Gian!", "effect": "global_reset"},
}

RANDOM_EVENT_MESSAGES = {
    # --- BAD EVENTS MESSAGES ---
    "snapped_line":    "Dây câu căng quá... PẶT! Mất toi cái mồi rồi (-5 Độ bền). 😭",
    "hook_stuck":      "Lưỡi câu mắc vào rễ cây dưới đáy hồ. Phải cắt dây bỏ mồi. ✂️",
    "rat_bite":        "Một con chuột cống chạy qua cắn đứt dây câu của bạn! 🐀",
    "poor_knot":       "Do buộc nút không chặt, lưỡi câu tuột mất tiêu. Gà quá! 🐔",
    "fish_escape":     "Cá đã cắn câu nhưng quẫy mạnh quá nên thoát được. Tiếc hùi hụi! 🐟💨",
    "bet_lose": "Một tay câu mới đến thách đấu. Bạn tự tin nhận kèo và... thua sấp mặt! 💸",

    "predator":        "Cá Sư Tử lao tới đớp trọn mẻ cá của bạn rồi bỏ chạy (-3 Độ bền)! 😱",
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
    "equipment_break": "Rắc! Cần câu bị gãy gập. Phải đem đi hàn lại (Chờ 10 phút - Mất toàn bộ độ bền). 🛠️",

    "mom_called":      "Alo? Mẹ gọi về ăn cơm! Bạn vội chạy về, bỏ lỡ mẻ cá này. 🍚",
    "wife_gank":       "Vợ/Người yêu xuất hiện gank! 'Suốt ngày câu với kéo!'. Bạn phải trốn ngay. 🏃",
    "sleepy":          "Gió mát quá... Zzz... Bạn ngủ gật và cá ăn hết mồi lúc nào không hay. 😴",
    "sneeze":          "Hắt xì!!! 🤧 Tiếng hắt hơi làm đàn cá giật mình bơi đi hết.",
    "kids_rock":       "Lũ trẻ trâu ném đá xuống hồ làm cá sợ chạy mất dép. 🗿",

    "plastic_trap":    "Lưỡi câu móc vào bao tải rác. Kéo nặng trịch làm hại độ bền cần (-5 Độ bền). 🗑️",
    "big_log":         "Tưởng cá to, hóa ra là khúc gỗ mục. Cần câu bị cong vòng (-5 Độ bền). 🪵",
    "crab_cut":        "Con Cua kẹp vào dây câu làm xước dây và mòn cần (-5 Độ bền). 🦀",
    "electric_eel":    "Câu trúng Lươn Điện! Nó phóng điện làm bạn tê tay, rơi cần xuống đất (-5 Độ bền). ⚡",
    "sea_sickness":    "Sóng đánh tụt quần! Bạn nôn thốc nôn tháo... nôn hết cả túi mồi ra biển. 🤢",
    
    # --- GOOD EVENTS MESSAGES ---
    "found_wallet":    "Vớt được cái ví da cá sấu! Bên trong có kha khá tiền lẻ. 👛",
    "magic_bait":      "Mồi của bạn tỏa sáng kỳ lạ! Cá đến thành đàn! ✨🐟",
    "twin_fish":       "Bạn câu được cá song sinh! Mỗi con lại kéo thêm anh em! 👯",
    "mirror_water":    "Mặt nước như gương phản chiếu - cá bị ảo giác và cắn nhiều lần! 🪞",
    "tourist_tip":     "Khách du lịch thấy bạn câu điệu nghệ quá nên tip nóng! 💵",
    "floating_cash":   "Ai đó đánh rơi tờ tiền trôi lềnh bềnh trên mặt nước! Vớt lẹ! 💸",
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

    "golden_turtle":   "Cụ Rùa Vàng nổi lên thở. Bạn cảm thấy tràn trề sinh lực! 🐢",
    "favorable_wind":  "Gió đông thổi tới! Câu nhanh hơn hẳn. 🌬️",
    "blacksmith_ghost":"Hồn ma thợ rèn hiện về: 'Để ta sửa cần cho con'. (+20 Độ bền) 🔨👻",
    "maintenance_kit": "Vớt được hộp dầu máy. Tra dầu vào cần câu chạy mượt hẳn! (+20 Độ bền) 🛢️",
    "energy_drink":    "Làm lon bò húc! Tỉnh cả người, quăng cần liên tục. 🐂",

    "double_rainbow":  "Cầu vồng đôi! 🌈 Nhân phẩm bùng nổ.",
    "shooting_star":   "Sao băng lướt qua! 🌠 Ước gì được nấy (Buff may mắn).",
    "ancestor_bless":  "Ông bà gánh còng lưng! Lần câu sau auto đỏ. 🙏",
    "sixth_sense":     "Mắt phải giật liên hồi... Linh tính mách bảo bạn sẽ tránh được kiếp nạn sắp tới. 👁️",
    "lucky_underwear": "Bạn mặc chiếc quần chip đỏ may mắn hôm nay. Cá to tự tìm đến! 🩲",
    "temple_pray":     "Hôm qua mới đi chùa thắp hương. Thần linh phù hộ tránh xui xẻo. 🏯",
    
    # --- GLOBAL RESET EVENTS (Cực Hiếm: 0.1%) ---
    "broken_hourglass": "Bạn câu được một chiếc đồng hồ cát cổ đại... Nó vỡ tan và làm thời gian đảo ngược! ⏳✨",
    "whale_song": "Một chú Cá Voi Xanh khổng lồ nổi lên và cất tiếng hát vang vọng đại dương. Âm thanh chữa lành mọi mệt mỏi. 🐋🎵",
    "red_tide": "Một đợt thủy triều mang theo hàng triệu sinh vật phù du tràn về. Cá ăn điên cuồng, không cần chờ đợi! 🌊✨",
    "lantern_festival": "Hàng nghìn chiếc đèn lồng trôi trên mặt nước, soi sáng cả một vùng. Không khí lễ hội khiến ai cũng hăng say. 🏮🎊",
    "dragon_blessing": "Long Vương đi vi hành và thấy sự chăm chỉ của các bạn. Ngài phất tay xóa bỏ mọi giới hạn! 🐉👑",
    "energy_storm": "Một luồng điện tích tụ trong không khí kích thích thần kinh vận động. Mọi người thao tác nhanh như chớp! ⚡💨",
    "mermaid_tea": "Các nàng tiên cá mời cả server dùng 'Trà Rong Biển'. Uống vào tỉnh táo, quăng cần không biết mệt. 🧚‍♀️🫖",
    "monsoon": "Gió mùa về! Cá nổi lên hít thở rợp cả mặt hồ. Cơ hội ngàn năm có một! 🌬️🐟",
    "temple_bell": "Tiếng chuông chùa xa xa vọng lại... Tâm tịnh, tay nhanh, mọi phiền muộn (và cooldown) đều tan biến. 🔔✨",
    "warp_gate": "Lưỡi câu của bạn móc trúng nút 'Refresh' của Vũ Trụ. Hệ thống thời gian bị reset! 🌌🔄",
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
    "rent_increase":      {"chance": 0.005, "type": "bad", "mul": 1.0, "flat": -50, "name": "Tăng Giá Thuê!"},

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

# ==================== NPC ENCOUNTERS (Khách Vãng Lai) ====================
# Tỉ lệ xuất hiện: 5% sau khi câu cá thành công

NPC_ENCOUNTERS = {
    "stray_cat": {
        "name": "🐈 Mèo Hoang Đói Bụng",
        "description": "Một chú mèo hoang gầy gò nhìn chằm chằm vào con cá bạn vừa câu.\nNó kêu 'Meow~' vẻ đói bụng.",
        "question": "**Bạn có muốn cho nó con cá này không?**",
        "image_url": "https://i.imgur.com/QfzKZYH.png",
        "chance": 0.25,
        "rewards": {
            "accept": [
                {"type": "worm", "amount": 5, "chance": 0.3, "message": "Mèo ăn xong vui vẻ nhả lại **5 Mồi Câu** rồi bỏ đi! 🪱"},
                {"type": "lucky_buff", "chance": 0.4, "message": "Mèo dụi đầu vào chân bạn. Bạn cảm thấy **May Mắn** hơn! ✨"},
                {"type": "nothing", "chance": 0.3, "message": "Mèo ăn xong rồi bỏ đi một mạch. Đồ vô ơn! 😿"}
            ],
            "decline": "Bạn đuổi mèo đi. Nó liếc bạn một cái đầy oán hận rồi chạy mất."
        },
        "cost": "fish"  # Mất con cá vừa câu
    },
    
    "beggar": {
        "name": "👴 Ông Lão Ăn Xin",
        "description": "Một cụ già rách rưới đi qua:\n'Cậu ơi, cho già xin **50 Hạt** mua bánh mì...'",
        "question": "**Bạn có muốn làm việc thiện không?**",
        "image_url": "https://i.imgur.com/3mKxPLH.png",
        "chance": 0.2,
        "rewards": {
            "accept": [
                {"type": "chest", "amount": 1, "chance": 0.5, "message": "👴: 'Cảm ơn con! Ta thực ra là **Thổ Địa**. Tặng con **1 Rương Kho Báu**!' 🎁"},
                {"type": "rod_durability", "amount": 999, "chance": 0.3, "message": "👴: 'Ta là **Tiên Ông**! Cần câu của con được hồi phục **Hoàn Toàn**!' 🔨✨"},
                {"type": "money", "amount": 150, "chance": 0.2, "message": "👴: 'Lương thiện được trời thương! Của cho không bằng cách cho!' (+150 Hạt) 🙏"}
            ],
            "decline": "Ông lão thở dài bỏ đi. Bạn cảm thấy hơi áy náy..."
        },
        "cost": 50  # Mất 50 Hạt
    },
    
    "otter_trader": {
        "name": "🦦 Rái Cá Trao Đổi",
        "description": "Một con Rái Cá trồi lên, tay cầm một viên đá sáng lấp lánh.\nNó chỉ vào con cá của bạn, tỏ ý muốn trao đổi.",
        "question": "**Bạn có muốn đổi cá lấy vật phẩm bí ẩn không?**",
        "image_url": "https://i.imgur.com/9Ky7XzR.png",
        "chance": 0.25,
        "rewards": {
            "accept": [
                {"type": "pearl", "amount": 1, "chance": 0.25, "message": "Rái cá trao cho bạn **1 Ngọc Trai** lấp lánh! 🔮"},
                {"type": "rod_material", "amount": 2, "chance": 0.3, "message": "Rái cá tặng bạn **2 Vật Liệu Cần Câu**! 🛠️"},
                {"type": "worm", "amount": 10, "chance": 0.2, "message": "Rái cá cho bạn **10 Mồi Câu** từ kho của nó! 🪱"},
                {"type": "rock", "chance": 0.25, "message": "Rái cá đưa cho bạn... một cục đá cuội thôi. Bị lừa rồi! 🪨"}
            ],
            "decline": "Rái cá tức giận tát nước vào mặt bạn rồi lặn mất! 💦"
        },
        "cost": "fish"
    },
    
    "black_market": {
        "name": "🕵️ Thương Buôn Chợ Đen",
        "description": "Một gã mặc áo choàng đen thì thầm:\n'Con cá này nhìn được đấy, ta mua **GẤP 3 LẦN** giá thị trường, bán không?'",
        "question": "**Rủi ro:** Có 20% bị Công An bắt!",
        "image_url": "https://i.imgur.com/zQx3YmH.png",
        "chance": 0.15,
        "rewards": {
            "accept": [
                {"type": "triple_money", "chance": 0.8, "message": "Giao dịch trót lọt! Bạn nhận được tiền gấp 3! 💰"},
                {"type": "caught", "fine": 200, "chance": 0.2, "message": "🚔 **O e o e!** Công an ập tới bắt quả tang!\nBạn mất cá và bị phạt **200 Hạt**! 😱"}
            ],
            "decline": "Gã bí ẩn gật đầu rồi biến vào bóng tối."
        },
        "cost": "fish"
    },
    
    "drowned_ghost": {
        "name": "👻 Hồn Ma Chết Đuối",
        "description": "Không khí lạnh toát... Một bóng trắng lướt qua:\n'Ta lạnh quá... Cần câu của ngươi có vẻ ấm... Cho ta mượn chút...'",
        "question": "**Bạn có dám cho ma mượn cần câu không?**",
        "image_url": "https://i.imgur.com/kX9Tz4L.png",
        "chance": 0.15,
        "rewards": {
            "accept": [
                {"type": "legendary_buff", "duration": 10, "chance": 0.7, "message": "Ma trả lại cần câu đã được **TẨM PHÉP**!\n✨ 10 lần câu tới tăng **50% tỉ lệ Cá Hiếm**! ✨"},
                {"type": "cursed", "chance": 0.3, "message": "👻 Ma cười nham hiểm rồi biến mất!\nCần câu bị **NGUYỀN RỦA** - độ bền giảm 20 điểm! 💀"}
            ],
            "decline": "Bạn hoảng sợ bỏ chạy. Tiếng cười thảm thiết vang lên phía sau..."
        },
        "cost": "cooldown_5min"  # Mất lượt câu trong 5 phút
    }
}

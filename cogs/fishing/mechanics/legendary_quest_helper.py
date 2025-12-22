"""
Legendary Quest Helper Functions
Quản lý tiến độ quest cho các cá huyền thoại
"""

from database_manager import db_manager


# ==================== THUỒNG LUỒNG - Hiến Tế Cá ====================

async def get_sacrifice_count(user_id: int, fish_key: str = "thuong_luong") -> int:
    """Lấy số lần hiến tế cho Thuồng Luồng"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] if row else 0
    except Exception as e:
        print(f"[LEGENDARY] Error getting sacrifice count: {e}")
        return 0


async def increment_sacrifice_count(user_id: int, amount: int = 1, fish_key: str = "thuong_luong") -> int:
    """Tăng số lần hiến tế cho Thuồng Luồng"""
    try:
        current = await get_sacrifice_count(user_id, fish_key)
        new_count = current + amount
        
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, ?, ?)",
            (user_id, fish_key, new_count)
        )
        print(f"[LEGENDARY] {user_id} sacrifice count: {current} → {new_count}")
        return new_count
    except Exception as e:
        print(f"[LEGENDARY] Error incrementing sacrifice count: {e}")
        return await get_sacrifice_count(user_id, fish_key)


async def reset_sacrifice_count(user_id: int, fish_key: str = "thuong_luong") -> None:
    """Reset số lần hiến tế (sau khi hoàn thành quest)"""
    try:
        await db_manager.modify(
            "UPDATE legendary_quests SET quest_status = 0 WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        print(f"[LEGENDARY] Reset sacrifice count for {user_id}")
    except Exception as e:
        print(f"[LEGENDARY] Error resetting sacrifice count: {e}")


# ==================== CÁ NGÂN HÀ - Chế Tạo Mồi ====================

async def get_crafted_bait_status(user_id: int, fish_key: str = "ca_ngan_ha") -> bool:
    """Kiểm tra đã chế tạo Mảnh Sao Băng chưa (quest_status = 1)"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] == 1 if row else False
    except Exception as e:
        print(f"[LEGENDARY] Error checking crafted bait status: {e}")
        return False


async def set_crafted_bait_status(user_id: int, completed: bool = True, fish_key: str = "ca_ngan_ha") -> None:
    """Set trạng thái chế tạo mồi"""
    try:
        status = 1 if completed else 0
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, ?, ?)",
            (user_id, fish_key, status)
        )
        print(f"[LEGENDARY] Set {fish_key} crafted_bait_status: {completed}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting crafted bait status: {e}")


# ==================== CÁ PHƯỢNG HOÀNG - Chuẩn Bị Vật Phẩm ====================

async def get_phoenix_prep_status(user_id: int, fish_key: str = "ca_phuong_hoang") -> bool:
    """Kiểm tra đã chuẩn bị (có Lông Vũ Lửa hoặc buff cây) chưa (quest_status = 1)"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] == 1 if row else False
    except Exception as e:
        print(f"[LEGENDARY] Error checking phoenix prep status: {e}")
        return False


async def set_phoenix_prep_status(user_id: int, prepared: bool = True, fish_key: str = "ca_phuong_hoang") -> None:
    """Set trạng thái chuẩn bị"""
    try:
        status = 1 if prepared else 0
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, ?, ?)",
            (user_id, fish_key, status)
        )
        print(f"[LEGENDARY] Set {fish_key} prep_status: {prepared}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting phoenix prep status: {e}")


# ==================== CTHULHU - Ghép Bản Đồ ====================

async def get_map_pieces_count(user_id: int, fish_key: str = "cthulhu_con") -> int:
    """Lấy số mảnh bản đồ hiện có"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] if row else 0
    except Exception as e:
        print(f"[LEGENDARY] Error getting map pieces count: {e}")
        return 0


async def set_map_pieces_count(user_id: int, pieces: int, fish_key: str = "cthulhu_con") -> None:
    """Set số mảnh bản đồ (0-4)"""
    try:
        pieces = max(0, min(pieces, 4))  # Clamp 0-4
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, ?, ?)",
            (user_id, fish_key, pieces)
        )
        print(f"[LEGENDARY] Set {fish_key} map_pieces: {pieces}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting map pieces count: {e}")


async def is_quest_completed(user_id: int, fish_key: str) -> bool:
    """Kiểm tra quest đã hoàn thành chưa (quest_completed = true)"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_completed FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] if row else False
    except Exception as e:
        print(f"[LEGENDARY] Error checking quest completed: {e}")
        return False


async def set_quest_completed(user_id: int, fish_key: str, completed: bool = True) -> None:
    """Set quest đã hoàn thành (chuẩn bị kích hoạt gặp cá)"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_completed) VALUES (?, ?, ?) ON CONFLICT(user_id, fish_key) DO UPDATE SET quest_completed = ?",
            (user_id, fish_key, completed, completed)
        )
        print(f"[LEGENDARY] Set {fish_key} quest_completed: {completed}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting quest completed: {e}")


# ==================== CÁ VỎI 52HZ - Dò Sóng ====================

async def get_frequency_hunt_status(user_id: int, fish_key: str = "ca_voi_52hz") -> int:
    """
    Lấy trạng thái dò tần số:
    0 = chưa mua máy dò
    1 = đã mua, đang dò (chưa dò được 52Hz)
    2 = đã dò được 52Hz, lần câu tiếp theo chắc chắn ra cá
    """
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] if row else 0
    except Exception as e:
        print(f"[LEGENDARY] Error getting frequency hunt status: {e}")
        return 0


async def set_frequency_hunt_status(user_id: int, status: int, fish_key: str = "ca_voi_52hz") -> None:
    """
    Set trạng thái dò tần số:
    0 = chưa mua máy dò
    1 = đã mua, đang dò
    2 = đã dò được 52Hz
    """
    try:
        status = max(0, min(status, 2))  # Clamp 0-2
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, ?, ?)",
            (user_id, fish_key, status)
        )
        print(f"[LEGENDARY] Set {fish_key} frequency_hunt_status: {status}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting frequency hunt status: {e}")


# ==================== CÁ NGÂN HÀ - Mảnh Sao Băng & Tinh Cầu ====================

async def get_manh_sao_bang_count(user_id: int) -> int:
    """Lấy số lượng Mảnh Sao Băng người chơi đang sở hữu"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = 'ca_ngan_ha'",
            (user_id,)
        )
        return row[0] if row else 0
    except Exception as e:
        print(f"[LEGENDARY] Error getting manh sao bang count: {e}")
        return 0


async def set_manh_sao_bang_count(user_id: int, count: int) -> None:
    """Set số lượng Mảnh Sao Băng"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, 'ca_ngan_ha', ?)",
            (user_id, count)
        )
        print(f"[LEGENDARY] Set manh sao bang count for {user_id}: {count}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting manh sao bang count: {e}")


async def increment_manh_sao_bang(user_id: int, amount: int = 1) -> int:
    """Tăng số lượng Mảnh Sao Băng"""
    try:
        current = await get_manh_sao_bang_count(user_id)
        new_count = current + amount
        await set_manh_sao_bang_count(user_id, new_count)
        return new_count
    except Exception as e:
        print(f"[LEGENDARY] Error incrementing manh sao bang: {e}")
        return await get_manh_sao_bang_count(user_id)


async def has_tinh_cau(user_id: int) -> bool:
    """Kiểm tra người chơi có Tinh Cầu Không Gian không"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_completed FROM legendary_quests WHERE user_id = ? AND fish_key = 'ca_ngan_ha'",
            (user_id,)
        )
        return row[0] if row else False
    except Exception as e:
        print(f"[LEGENDARY] Error checking tinh cau: {e}")
        return False


async def set_has_tinh_cau(user_id: int, has: bool = True) -> None:
    """Set trạng thái có Tinh Cầu Không Gian"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_completed) VALUES (?, 'ca_ngan_ha', ?) ON CONFLICT(user_id, fish_key) DO UPDATE SET quest_completed = ?",
            (user_id, has, has)
        )
        print(f"[LEGENDARY] Set tinh cau for {user_id}: {has}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting tinh cau: {e}")


async def get_tinh_cau_cooldown(user_id: int) -> str or None:
    """Lấy thời gian cooldown của Tinh Cầu (last_progress_time)"""
    try:
        row = await db_manager.fetchone(
            "SELECT last_progress_time FROM legendary_quests WHERE user_id = ? AND fish_key = 'ca_ngan_ha'",
            (user_id,)
        )
        return row[0] if row else None
    except Exception as e:
        print(f"[LEGENDARY] Error getting tinh cau cooldown: {e}")
        return None


async def set_tinh_cau_cooldown(user_id: int) -> None:
    """Set thời gian cooldown cho Tinh Cầu (sau khi thất bại mini-game)"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, last_progress_time) VALUES (?, 'ca_ngan_ha', CURRENT_TIMESTAMP) ON CONFLICT(user_id, fish_key) DO UPDATE SET last_progress_time = CURRENT_TIMESTAMP",
            (user_id,)
        )
        print(f"[LEGENDARY] Set tinh cau cooldown for {user_id}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting tinh cau cooldown: {e}")


async def craft_tinh_cau(user_id: int) -> bool:
    """Chế tạo Tinh Cầu từ 5 Mảnh Sao Băng + 1 Ngọc Trai"""
    try:
        # Check if already caught
        if await is_legendary_caught(user_id, "ca_ngan_ha"):
            return False
        
        manh_count = await get_manh_sao_bang_count(user_id)
        if manh_count < 5:
            return False
        
        # Check có Ngọc Trai không
        from database_manager import get_inventory
        inventory = await get_inventory(user_id)
        if inventory.get('ngoc_trai', 0) < 1:
            return False
        
        # Trừ vật phẩm
        from database_manager import remove_item
        await remove_item(user_id, 'ngoc_trai', 1)
        await set_manh_sao_bang_count(user_id, manh_count - 5)
        await set_has_tinh_cau(user_id, True)
        
        print(f"[LEGENDARY] {user_id} crafted Tinh Cầu")
        return True
    except Exception as e:
        print(f"[LEGENDARY] Error crafting tinh cau: {e}")
        return False


# ==================== LEGENDARY CAUGHT ====================

async def is_legendary_caught(user_id: int, fish_key: str) -> bool:
    """Kiểm tra đã bắt được cá huyền thoại chưa"""
    try:
        row = await db_manager.fetchone(
            "SELECT legendary_caught FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        return row[0] if row else False
    except Exception as e:
        print(f"[LEGENDARY] Error checking legendary caught: {e}")
        return False


async def set_legendary_caught(user_id: int, fish_key: str, caught: bool = True) -> None:
    """Mark cá huyền thoại đã bắt được"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, legendary_caught) VALUES (?, ?, ?) ON CONFLICT(user_id, fish_key) DO UPDATE SET legendary_caught = ?",
            (user_id, fish_key, caught, caught)
        )
        print(f"[LEGENDARY] Set {fish_key} legendary_caught: {caught}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting legendary caught: {e}")


# ==================== RESET QUEST ====================

async def reset_legendary_quest(user_id: int, fish_key: str) -> None:
    """Reset toàn bộ quest trạng thái (quay lại ban đầu)"""
    try:
        await db_manager.modify(
            "UPDATE legendary_quests SET quest_status = 0, quest_completed = FALSE WHERE user_id = ? AND fish_key = ?",
            (user_id, fish_key)
        )
        print(f"[LEGENDARY] Reset quest for {fish_key}")
    except Exception as e:
        print(f"[LEGENDARY] Error resetting quest: {e}")


# ==================== CÁ PHƯỢNG HOÀNG - Lông Vũ Lửa & Buff ====================

async def get_long_vu_lua_count(user_id: int) -> int:
    """Lấy số lượng Lông Vũ Lửa cho Cá Phượng Hoàng"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_status FROM legendary_quests WHERE user_id = ? AND fish_key = 'ca_phuong_hoang'",
            (user_id,)
        )
        return row[0] if row else 0
    except Exception as e:
        print(f"[LEGENDARY] Error getting long vu lua count: {e}")
        return 0


async def set_long_vu_lua_count(user_id: int, count: int) -> None:
    """Set số lượng Lông Vũ Lửa"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_status) VALUES (?, 'ca_phuong_hoang', ?)",
            (user_id, count)
        )
        print(f"[LEGENDARY] Set long vu lua count for {user_id}: {count}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting long vu lua count: {e}")


async def increment_long_vu_lua(user_id: int, amount: int = 1) -> int:
    """Tăng số lượng Lông Vũ Lửa"""
    try:
        current = await get_long_vu_lua_count(user_id)
        new_count = current + amount
        await set_long_vu_lua_count(user_id, new_count)
        return new_count
    except Exception as e:
        print(f"[LEGENDARY] Error incrementing long vu lua: {e}")
        return await get_long_vu_lua_count(user_id)


async def has_phoenix_buff(user_id: int) -> bool:
    """Kiểm tra có buff Cá Phượng Hoàng không (quest_completed)"""
    try:
        row = await db_manager.fetchone(
            "SELECT quest_completed FROM legendary_quests WHERE user_id = ? AND fish_key = 'ca_phuong_hoang'",
            (user_id,)
        )
        return bool(row[0]) if row else False
    except Exception as e:
        print(f"[LEGENDARY] Error checking phoenix buff: {e}")
        return False


async def set_phoenix_buff(user_id: int, active: bool = True) -> None:
    """Set buff Cá Phượng Hoàng"""
    try:
        await db_manager.modify(
            "INSERT OR REPLACE INTO legendary_quests (user_id, fish_key, quest_completed) VALUES (?, 'ca_phuong_hoang', ?)",
            (user_id, int(active))
        )
        print(f"[LEGENDARY] Set phoenix buff for {user_id}: {active}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting phoenix buff: {e}")


async def get_phoenix_last_play(user_id: int) -> str:
    """Lấy thời gian chơi mini-game cuối cùng"""
    try:
        row = await db_manager.fetchone(
            "SELECT last_progress_time FROM legendary_quests WHERE user_id = ? AND fish_key = 'ca_phuong_hoang'",
            (user_id,)
        )
        return row[0] if row and row[0] else None
    except Exception as e:
        print(f"[LEGENDARY] Error getting phoenix last play: {e}")
        return None


async def set_phoenix_last_play(user_id: int) -> None:
    """Set thời gian chơi mini-game cuối cùng"""
    try:
        await db_manager.modify(
            "UPDATE legendary_quests SET last_progress_time = CURRENT_TIMESTAMP WHERE user_id = ? AND fish_key = 'ca_phuong_hoang'",
            (user_id,)
        )
        print(f"[LEGENDARY] Set phoenix last play for {user_id}")
    except Exception as e:
        print(f"[LEGENDARY] Error setting phoenix last play: {e}")

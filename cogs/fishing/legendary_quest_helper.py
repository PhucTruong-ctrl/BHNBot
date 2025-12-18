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
    """Kiểm tra đã chế tạo mồi Bụi Sao chưa (quest_status = 1)"""
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

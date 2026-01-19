"""Rod upgrade and durability system."""

from ..constants import DB_PATH, ROD_LEVELS
from database_manager import db_manager, increment_stat, get_stat, add_seeds, get_user_balance

from core.logging import get_logger
logger = get_logger("rod_system")

async def get_rod_data(user_id: int) -> tuple:
    """Retrieves the user's rod level and durability.

    Automatically creates a fishing profile if one does not exist.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        tuple: A tuple containing (rod_level, rod_durability).
    """
    try:
        # Use fetchrow for retrieving single record (PostgreSQL)
        row = await db_manager.fetchrow(
            "SELECT rod_level, rod_durability FROM fishing_profiles WHERE user_id = $1",
            (user_id,)
        )
        
        if not row:
            # Auto-create fishing profile for new user
            try:
                # Use execute with PostgreSQL $1,$2,$3 placeholders
                await db_manager.execute(
                    "INSERT INTO fishing_profiles (user_id, rod_level, rod_durability) VALUES ($1, $2, $3)",
                    (user_id, 1, ROD_LEVELS[1]["durability"])
                )
            except Exception as e:
                logger.debug("[rod]_error_creating_fishing_p", user_id=user_id)
            return 1, ROD_LEVELS[1]["durability"]
            
        # Ensure level fallback only when None/invalid, and do NOT override legitimate 0 durability
        # AsyncPG returns Record objects which are subscriptable by column name (and index-based if using sqlite/aiosqlite emulation)
        # Using index 0 and 1 to be backend-agnostic given we know order
        rod_level = row[0] if row[0] is not None and int(row[0]) >= 1 else 1
        rod_durability = row[1] if row[1] is not None else ROD_LEVELS[rod_level]["durability"]
        
        return rod_level, rod_durability
    except Exception as e:
        logger.debug("[rod]_error_getting_rod_data:_", e=e)
        return 1, ROD_LEVELS[1]["durability"]

async def update_rod_data(user_id: int, durability: int, level: int | None = None):
    """Updates the user's rod durability and optionally upgrade level.

    Args:
        user_id (int): The Discord user ID.
        durability (int): The new durability value.
        level (int, optional): The new rod level. Defaults to None (no change).
    """
    try:
        if level is not None:
            await db_manager.execute(
                "UPDATE fishing_profiles SET rod_durability = $1, rod_level = $2 WHERE user_id = $3",
                (durability, level, user_id)
            )
            logger.debug("[rod]_[update]_user_id=_durabi", user_id=user_id)
        else:
            await db_manager.execute(
                "UPDATE fishing_profiles SET rod_durability = $1 WHERE user_id = $2",
                (durability, user_id)
            )
            logger.debug("[rod]_[update]_user_id=_durabi", user_id=user_id)
    except Exception as e:
        logger.debug("[rod]_error_updating_rod_data_", user_id=user_id)


async def check_and_repair_rod(
    user_id: int, 
    rod_lvl: int, 
    rod_durability: int, 
    rod_config: dict, 
    username: str,
    achievement_callback=None
) -> tuple[int, str, bool]:
    """Check rod durability and auto-repair if possible.
    
    Args:
        user_id: User ID
        rod_lvl: Current rod level
        rod_durability: Current rod durability
        rod_config: Rod configuration dict with 'repair' and 'durability' keys
        username: Username for logging
        achievement_callback: Optional async callback(user_id, stat_key, current_value) for achievements
        
    Returns:
        tuple: (new_durability, repair_msg, is_broken_rod)
    """
    repair_msg = ""
    is_broken_rod = False
    
    if rod_durability <= 0:
        repair_cost = rod_config["repair"]
        balance = await get_user_balance(user_id)
        logger.info(f"[FISHING] [ROD_BROKEN] {username} (user_id={user_id}) rod_level={rod_lvl} durability={rod_durability} repair_cost={repair_cost} balance={balance}")
        
        if balance >= repair_cost:
            await add_seeds(user_id, -repair_cost, 'rod_repair', 'fishing')
            rod_durability = rod_config["durability"]
            await update_rod_data(user_id, rod_durability, rod_lvl)
            repair_msg = f"\n🛠️ **Cần câu đã gãy!** Tự động sửa chữa: **-{repair_cost} Hạt** (Độ bền phục hồi: {rod_durability}/{rod_config['durability']})"
            logger.info(f"[FISHING] [AUTO_REPAIR] {username} (user_id={user_id}) seed_change=-{repair_cost} action=rod_repaired new_durability={rod_durability}")
            
            try:
                await increment_stat(user_id, "fishing", "rods_repaired", 1)
                current_repairs = await get_stat(user_id, "fishing", "rods_repaired")
                if achievement_callback:
                    await achievement_callback(user_id, "rods_repaired", current_repairs)
            except Exception as e:
                logger.error(f"[ACHIEVEMENT] Error updating rods_repaired for {user_id}: {e}")
        else:
            is_broken_rod = True
            repair_msg = f"\n⚠️ **Cần câu đã gãy!** Phí sửa là {repair_cost} Hạt. Bạn đang câu với cần gãy (chỉ 1% cá hiếm, 1 item/lần, không rương)."
            logger.info(f"[FISHING] [BROKEN_ROD] {username} (user_id={user_id}) cannot_afford_repair cost={repair_cost}")
    
    return rod_durability, repair_msg, is_broken_rod

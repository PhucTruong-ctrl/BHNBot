import logging
import asyncio
from database_manager import db_manager, get_user_balance, add_seeds, get_stat, increment_stat
from .constants import ROD_LEVELS

logger = logging.getLogger("FishingModels")

async def get_rod_data(user_id: int):
    """Retrieves rod level and durability from database."""
    # Use fishing_profiles table which is standard in this project
    result = await db_manager.fetchone(
        "SELECT rod_level, rod_durability FROM fishing_profiles WHERE user_id = ?",
        (user_id,)
    )
    if result:
        return result[0], result[1]
    else:
        # Default values if no record exists
        return 1, 30

async def update_rod_data(user_id: int, durability: int, level: int = None):
    """Updates rod durability and optionally level."""
    if level is not None:
        # Upsert with level update
        await db_manager.modify(
            """INSERT INTO fishing_profiles (user_id, rod_level, rod_durability, exp) 
               VALUES (?, ?, ?, 0)
               ON CONFLICT(user_id) DO UPDATE SET rod_level = ?, rod_durability = ?""",
            (user_id, level, durability, level, durability)
        )
    else:
        # Upsert with durability only (preserve level if exists, else default 1)
        await db_manager.modify(
            """INSERT INTO fishing_profiles (user_id, rod_level, rod_durability, exp) 
               VALUES (?, 1, ?, 0)
               ON CONFLICT(user_id) DO UPDATE SET rod_durability = ?""",
            (user_id, durability, durability)
        )

async def check_bucket_limit(user_id: int, bucket_limit: int) -> tuple[int, bool]:
    """Returns current fish count and if full."""
    # Logic moved to Logic/Service layer using Inventory Service
    pass

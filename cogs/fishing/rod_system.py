"""Rod upgrade and durability system."""

import aiosqlite
from .constants import DB_PATH, ROD_LEVELS

async def get_rod_data(user_id: int) -> tuple:
    """Get rod level and durability (rod_level, rod_durability)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT rod_level, rod_durability FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return 1, ROD_LEVELS[1]["durability"]
        return row[0] or 1, row[1] or ROD_LEVELS[1]["durability"]
    except Exception as e:
        print(f"[ROD] Error getting rod data: {e}")
        return 1, ROD_LEVELS[1]["durability"]

async def update_rod_data(user_id: int, durability: int, level: int = None):
    """Update rod durability (and level if provided)."""
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
    except Exception as e:
        pass

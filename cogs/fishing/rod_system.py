"""Rod upgrade and durability system."""

import aiosqlite
from .constants import DB_PATH, ROD_LEVELS, get_db

async def get_rod_data(user_id: int) -> tuple:
    """Get rod level and durability (rod_level, rod_durability).
    Creates fishing_profile automatically if user doesn't have one."""
    try:
        from database_manager import db_manager
        
        db = await get_db()
        try:
            async with db.execute(
                "SELECT rod_level, rod_durability FROM fishing_profiles WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        
        if not row:
            # Auto-create fishing profile for new user
            try:
                await db_manager.modify(
                    "INSERT INTO fishing_profiles (user_id, rod_level, rod_durability) VALUES (?, ?, ?)",
                    (user_id, 1, ROD_LEVELS[1]["durability"])
                )
            except Exception as e:
                print(f"[ROD] Error creating fishing profile for {user_id}: {e}")
            return 1, ROD_LEVELS[1]["durability"]
        return row[0] or 1, row[1] or ROD_LEVELS[1]["durability"]
    except Exception as e:
        print(f"[ROD] Error getting rod data: {e}")
        return 1, ROD_LEVELS[1]["durability"]

async def update_rod_data(user_id: int, durability: int, level: int = None):
    """Update rod durability (and level if provided)."""
    try:
        db = await get_db()
        try:
            if level is not None:
                await db.execute(
                    "UPDATE fishing_profiles SET rod_durability = ?, rod_level = ? WHERE user_id = ?",
                    (durability, level, user_id)
                )
            else:
                await db.execute(
                    "UPDATE fishing_profiles SET rod_durability = ? WHERE user_id = ?",
                    (durability, user_id)
                )
            await db.commit()
        finally:
            await db.close()
    except Exception as e:
        pass

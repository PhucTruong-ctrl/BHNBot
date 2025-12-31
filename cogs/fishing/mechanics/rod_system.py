"""Rod upgrade and durability system."""

from ..constants import DB_PATH, ROD_LEVELS
from database_manager import db_manager

async def get_rod_data(user_id: int) -> tuple:
    """Retrieves the user's rod level and durability.

    Automatically creates a fishing profile if one does not exist.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        tuple: A tuple containing (rod_level, rod_durability).
    """
    try:
        # Use fetchrow for retrieving single record
        row = await db_manager.fetchrow(
            "SELECT rod_level, rod_durability FROM fishing_profiles WHERE user_id = $1",
            (user_id,)
        )
        
        if not row:
            # Auto-create fishing profile for new user
            try:
                # Use execute with $n placeholders
                await db_manager.execute(
                    "INSERT INTO fishing_profiles (user_id, rod_level, rod_durability) VALUES ($1, $2, $3)",
                    (user_id, 1, ROD_LEVELS[1]["durability"])
                )
            except Exception as e:
                print(f"[ROD] Error creating fishing profile for {user_id}: {e}")
            return 1, ROD_LEVELS[1]["durability"]
            
        # Ensure level fallback only when None/invalid, and do NOT override legitimate 0 durability
        # AsyncPG returns Record objects which are subscriptable by column name
        rod_level = row['rod_level'] if row['rod_level'] is not None and int(row['rod_level']) >= 1 else 1
        
        # If durability is None, fall back to max durability for current level
        rod_durability = row['rod_durability'] if row['rod_durability'] is not None else ROD_LEVELS[rod_level]["durability"]
        
        return rod_level, rod_durability
    except Exception as e:
        print(f"[ROD] Error getting rod data: {e}")
        return 1, ROD_LEVELS[1]["durability"]

async def update_rod_data(user_id: int, durability: int, level: int = None):
    """Updates the user's rod durability and optionally upgrade level.

    Args:
        user_id (int): The Discord user ID.
        durability (int): The new durability value.
        level (int, optional): The new rod level. Defaults to None (no change).
    """
    try:
        # Use db_manager.execute with $n placeholders
        if level is not None:
            await db_manager.execute(
                "UPDATE fishing_profiles SET rod_durability = $1, rod_level = $2 WHERE user_id = $3",
                (durability, level, user_id)
            )
            print(f"[ROD] [UPDATE] user_id={user_id} durability={durability} level={level}")
        else:
            await db_manager.execute(
                "UPDATE fishing_profiles SET rod_durability = $1 WHERE user_id = $2",
                (durability, user_id)
            )
            print(f"[ROD] [UPDATE] user_id={user_id} durability={durability}")
    except Exception as e:
        print(f"[ROD] Error updating rod data for {user_id}: {e}")

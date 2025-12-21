"""Helper functions for fishing system."""

import json
from .constants import DB_PATH, COMMON_FISH_KEYS, RARE_FISH_KEYS, LEGENDARY_FISH_KEYS, ALL_FISH
from database_manager import db_manager

async def track_caught_fish(user_id: int, fish_key: str) -> bool:
    """Tracks a caught fish in the user's collection.

    This function records the first time a fish is caught.

    Args:
        user_id (int): The Discord user ID.
        fish_key (str): The identifier of the fish.

    Returns:
        bool: True if this is the first time the user has caught this fish, False otherwise.
    """
    try:
        # Use database_manager for proper connection pooling
        exists = await db_manager.execute(
            "SELECT 1 FROM fish_collection WHERE user_id = ? AND fish_id = ?",
            (user_id, fish_key)
        )
        
        if not exists:
            await db_manager.modify(
                "INSERT INTO fish_collection (user_id, fish_id) VALUES (?, ?)",
                (user_id, fish_key)
            )
            return True
    except Exception as e:
        # Note: 'caught_at' will default to CURRENT_TIMESTAMP due to schema
        print(f"[COLLECTION] Error tracking fish {fish_key} for user {user_id}: {e}")
        # Try to use database_manager.add_fish instead/fallback logic if needed
        # But for now, we assume schema is correct from setup_data
        pass
    
    return False

async def get_collection(user_id: int) -> dict:
    """Retrieves the user's fish collection details.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        dict: A dictionary mapping fish_id to catch timestamp (or other metadata).
    """
    try:
        # Use database_manager for proper connection pooling
        rows = await db_manager.execute(
            "SELECT fish_id FROM fish_collection WHERE user_id = ?",
            (user_id,)
        )
        # Return dict with fish_id as key, None as value (no timestamp in current schema)
        return {row[0]: None for row in rows}
    except Exception as e:
        print(f"[COLLECTION] Error getting collection for user {user_id}: {e}")
        return {}

async def check_collection_complete(user_id: int) -> bool:
    """Checks if the user has completed the fishing collection (Common + Rare).

    Args:
        user_id (int): The Discord user ID.

    Returns:
        bool: True if all common and rare fish have been caught.
    """
    collection = await get_collection(user_id)
    all_fish_keys = set(COMMON_FISH_KEYS + RARE_FISH_KEYS)
    caught_keys = set(collection.keys())
    return all_fish_keys.issubset(caught_keys)


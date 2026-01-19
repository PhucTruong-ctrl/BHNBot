"""Helper functions for fishing system."""

import json
from .constants import DB_PATH, COMMON_FISH_KEYS, RARE_FISH_KEYS, LEGENDARY_FISH_KEYS, ALL_FISH
from database_manager import db_manager

from core.logging import get_logger
logger = get_logger("fishing_helpers")

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
        exists = await db_manager.fetchone(
            "SELECT 1 FROM fish_collection WHERE user_id = $1 AND fish_id = $2",
            (user_id, fish_key)
        )
        
        if not exists:
            await db_manager.modify(
                "INSERT INTO fish_collection (user_id, fish_id, quantity) VALUES ($1, $2, 1) ON CONFLICT (user_id, fish_id) DO NOTHING",
                (user_id, fish_key)
            )
            return True
    except Exception as e:
        logger.debug("[collection]_error_tracking_fi", fish_key=fish_key)
    
    return False

async def get_collection(user_id: int) -> dict:
    """Retrieves the user's fish collection details.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        dict: A dictionary mapping fish_id to quantity.
    """
    try:
        rows = await db_manager.fetchall(
            "SELECT fish_id, COALESCE(quantity, 1) FROM fish_collection WHERE user_id = $1 AND quantity > 0",
            (user_id,)
        )
        return {row[0]: row[1] for row in rows} if rows else {}
    except Exception as e:
        logger.debug("[collection]_error_getting_col", user_id=user_id)
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


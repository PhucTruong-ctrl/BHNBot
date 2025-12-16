"""Helper functions for fishing system."""

import aiosqlite
import json
from .constants import DB_PATH, COMMON_FISH_KEYS, RARE_FISH_KEYS, LEGENDARY_FISH_KEYS, ALL_FISH

async def track_caught_fish(user_id: int, fish_key: str) -> bool:
    """Track that user caught this fish type for collection book.
    Returns True if first time catching this fish."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id FROM fish_collection WHERE user_id = ? AND fish_key = ?",
                (user_id, fish_key)
            ) as cursor:
                exists = await cursor.fetchone()
            
            if not exists:
                await db.execute(
                    "INSERT INTO fish_collection (user_id, fish_key, caught_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (user_id, fish_key)
                )
                await db.commit()
                return True
    except Exception as e:
        pass
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS fish_collection (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        fish_key TEXT NOT NULL,
                        caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, fish_key)
                    )
                """)
                await db.commit()
                return await track_caught_fish(user_id, fish_key)
        except Exception as e2:
            pass
    
    return False

async def get_collection(user_id: int) -> dict:
    """Get user's fish collection."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT fish_key, caught_at FROM fish_collection WHERE user_id = ? ORDER BY caught_at",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}
    except:
        return {}

async def check_collection_complete(user_id: int) -> bool:
    """Check if user caught all fish types (common + rare only)."""
    collection = await get_collection(user_id)
    all_fish_keys = set(COMMON_FISH_KEYS + RARE_FISH_KEYS)
    caught_keys = set(collection.keys())
    return all_fish_keys.issubset(caught_keys)


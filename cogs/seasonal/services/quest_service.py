from __future__ import annotations

import json
from core.logging import get_logger
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .database import execute_query, execute_write
from .participation_service import add_currency

if TYPE_CHECKING:
    pass

logger = get_logger("seasonal_services_quest_servic")


async def get_user_quests(guild_id: int, user_id: int, event_id: str) -> list[dict]:
    return await execute_query(
        "SELECT * FROM event_quests WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (guild_id, user_id, event_id),
    )


async def get_quest_progress(
    guild_id: int, user_id: int, event_id: str, quest_id: str
) -> dict | None:
    rows = await execute_query(
        "SELECT * FROM event_quests WHERE guild_id = ? AND user_id = ? AND event_id = ? AND quest_id = ?",
        (guild_id, user_id, event_id, quest_id),
    )
    return rows[0] if rows else None


async def init_daily_quests(
    guild_id: int, user_id: int, event_id: str, event_config: dict
) -> list[dict]:
    """Initialize or refresh daily quests for a user.
    
    Daily quests reset at midnight. This function checks if quests need refresh
    and assigns new random quests from the event's daily_quests pool.
    """
    today = datetime.now().date().isoformat()

    existing = await execute_query(
        """SELECT * FROM event_quests 
           WHERE guild_id = ? AND user_id = ? AND event_id = ? 
           AND quest_type = 'daily' AND assigned_date = ?""",
        (guild_id, user_id, event_id, today),
    )

    if existing:
        return existing

    await execute_write(
        """DELETE FROM event_quests 
           WHERE guild_id = ? AND user_id = ? AND event_id = ? AND quest_type = 'daily'""",
        (guild_id, user_id, event_id),
    )

    daily_pool = event_config.get("daily_quests", [])
    quest_count = event_config.get("daily_quest_count", 3)

    if not daily_pool:
        return []

    selected = random.sample(daily_pool, min(quest_count, len(daily_pool)))
    result = []

    for quest in selected:
        quest_data = json.dumps(quest)
        await execute_write(
            """INSERT INTO event_quests 
               (guild_id, user_id, event_id, quest_id, quest_type, quest_data, progress, target, completed, assigned_date)
               VALUES (?, ?, ?, ?, 'daily', ?, 0, ?, FALSE, ?)""",
            (guild_id, user_id, event_id, quest["id"], quest_data, quest["target"], today),
        )
        result.append({
            "quest_id": quest["id"],
            "quest_type": "daily",
            "quest_data": quest,
            "progress": 0,
            "target": quest["target"],
            "completed": False,
        })

    return result


async def init_fixed_quests(
    guild_id: int, user_id: int, event_id: str, event_config: dict
) -> list[dict]:
    """Initialize fixed/achievement quests for a user.
    
    Fixed quests persist for the entire event duration and are not reset.
    """
    fixed_quests = event_config.get("fixed_quests", [])
    if not fixed_quests:
        return []

    result = []
    for quest in fixed_quests:
        existing = await get_quest_progress(guild_id, user_id, event_id, quest["id"])
        if existing:
            existing["quest_data"] = json.loads(existing.get("quest_data", "{}"))
            result.append(existing)
            continue

        quest_data = json.dumps(quest)
        await execute_write(
            """INSERT INTO event_quests 
               (guild_id, user_id, event_id, quest_id, quest_type, quest_data, progress, target, completed, assigned_date)
               VALUES (?, ?, ?, ?, 'fixed', ?, 0, ?, FALSE, ?)""",
            (guild_id, user_id, event_id, quest["id"], quest_data, quest["target"], datetime.now().date().isoformat()),
        )
        result.append({
            "quest_id": quest["id"],
            "quest_type": "fixed",
            "quest_data": quest,
            "progress": 0,
            "target": quest["target"],
            "completed": False,
        })

    return result


async def update_quest_progress(
    guild_id: int,
    user_id: int,
    event_id: str,
    quest_type_filter: str,
    increment: int = 1,
) -> list[dict]:
    """Update progress for all quests matching a type filter.
    
    Args:
        guild_id: The guild ID.
        user_id: The user ID.
        event_id: The event ID.
        quest_type_filter: The quest action type (e.g., 'fish_count', 'lixi_sent').
        increment: Amount to add to progress.
    
    Returns:
        List of quests that were just completed by this update.
    """
    quests = await execute_query(
        """SELECT * FROM event_quests 
           WHERE guild_id = ? AND user_id = ? AND event_id = ? AND completed = FALSE""",
        (guild_id, user_id, event_id),
    )

    completed_quests = []

    for quest in quests:
        quest_data = json.loads(quest.get("quest_data", "{}"))
        if quest_data.get("type") != quest_type_filter:
            continue

        new_progress = min(quest["progress"] + increment, quest["target"])
        just_completed = new_progress >= quest["target"] and quest["progress"] < quest["target"]

        await execute_write(
            """UPDATE event_quests SET progress = ?, completed = ? 
               WHERE guild_id = ? AND user_id = ? AND event_id = ? AND quest_id = ?""",
            (new_progress, new_progress >= quest["target"], guild_id, user_id, event_id, quest["quest_id"]),
        )

        if just_completed:
            quest["quest_data"] = quest_data
            quest["progress"] = new_progress
            completed_quests.append(quest)

    return completed_quests


async def claim_quest_reward(
    guild_id: int, user_id: int, event_id: str, quest_id: str
) -> dict[str, Any] | None:
    """Claim reward for a completed quest.
    
    Returns:
        Reward info dict if claimed, None if quest not found or not completed.
    """
    quest = await get_quest_progress(guild_id, user_id, event_id, quest_id)
    if not quest:
        return None

    if not quest["completed"]:
        return None

    rows = await execute_query(
        "SELECT claimed FROM event_quests WHERE guild_id = ? AND user_id = ? AND event_id = ? AND quest_id = ?",
        (guild_id, user_id, event_id, quest_id),
    )
    if rows and rows[0].get("claimed"):
        return None

    quest_data = json.loads(quest.get("quest_data", "{}"))

    reward_type = quest_data.get("reward_type", "currency")
    reward_value = quest_data.get("reward_value") or quest_data.get("reward", 0)

    if reward_type == "currency" and isinstance(reward_value, int):
        await add_currency(guild_id, user_id, event_id, reward_value)

    await execute_write(
        "UPDATE event_quests SET claimed = TRUE WHERE guild_id = ? AND user_id = ? AND event_id = ? AND quest_id = ?",
        (guild_id, user_id, event_id, quest_id),
    )

    return {
        "quest_id": quest_id,
        "reward_type": reward_type,
        "reward_value": reward_value,
        "quest_data": quest_data,
    }


async def get_all_user_quests(
    guild_id: int, user_id: int, event_id: str, event_config: dict
) -> dict[str, list[dict]]:
    """Get all quests for a user, initializing if needed.
    
    Returns:
        Dict with 'daily' and 'fixed' quest lists.
    """
    daily = await init_daily_quests(guild_id, user_id, event_id, event_config)
    fixed = await init_fixed_quests(guild_id, user_id, event_id, event_config)

    return {"daily": daily, "fixed": fixed}


async def get_quest_stats(guild_id: int, user_id: int, event_id: str) -> dict:
    """Get summary stats for user's quests."""
    rows = await execute_query(
        """SELECT 
             COUNT(*) as total,
             SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) as completed,
              SUM(CASE WHEN claimed = TRUE THEN 1 ELSE 0 END) as claimed
           FROM event_quests 
           WHERE guild_id = ? AND user_id = ? AND event_id = ?""",
        (guild_id, user_id, event_id),
    )

    if not rows:
        return {"total": 0, "completed": 0, "claimed": 0}

    return {
        "total": rows[0]["total"] or 0,
        "completed": rows[0]["completed"] or 0,
        "claimed": rows[0]["claimed"] or 0,
    }

from __future__ import annotations

from core.logging import get_logger
from datetime import datetime
from typing import TYPE_CHECKING

from .database import execute_query, execute_write

if TYPE_CHECKING:
    pass

logger = get_logger("seasonal_services_title_servic")


async def unlock_title(user_id: int, title_key: str, title_name: str, source: str) -> bool:
    existing = await execute_query(
        "SELECT 1 FROM user_titles WHERE user_id = ? AND title_key = ?",
        (user_id, title_key),
    )
    if existing:
        return False

    await execute_write(
        "INSERT INTO user_titles (user_id, title_key, title_name, source, unlocked_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, title_key, title_name, source, datetime.now().isoformat()),
    )
    logger.info(f"Unlocked title {title_key} for user {user_id}")
    return True


async def get_user_titles(user_id: int) -> list[dict]:
    return await execute_query(
        "SELECT * FROM user_titles WHERE user_id = ? ORDER BY unlocked_at DESC",
        (user_id,),
    )


async def has_title(user_id: int, title_key: str) -> bool:
    rows = await execute_query(
        "SELECT 1 FROM user_titles WHERE user_id = ? AND title_key = ?",
        (user_id, title_key),
    )
    return len(rows) > 0


async def get_active_title(user_id: int) -> str | None:
    rows = await execute_query(
        "SELECT active_title FROM user_profiles WHERE user_id = ?",
        (user_id,),
    )
    if rows and rows[0].get("active_title"):
        return rows[0]["active_title"]
    return None


async def set_active_title(user_id: int, title_key: str) -> bool:
    if not await has_title(user_id, title_key):
        return False

    await execute_write(
        "UPDATE user_profiles SET active_title = ? WHERE user_id = ?",
        (title_key, user_id),
    )
    return True


async def clear_active_title(user_id: int) -> None:
    await execute_write(
        "UPDATE user_profiles SET active_title = NULL WHERE user_id = ?",
        (user_id,),
    )


async def get_title_display(user_id: int) -> str | None:
    active = await get_active_title(user_id)
    if not active:
        return None

    rows = await execute_query(
        "SELECT title_name FROM user_titles WHERE user_id = ? AND title_key = ?",
        (user_id, active),
    )
    return rows[0]["title_name"] if rows else None

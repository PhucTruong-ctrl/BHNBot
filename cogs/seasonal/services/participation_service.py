from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .database import execute_query, execute_write

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def get_participation(guild_id: int, user_id: int, event_id: str) -> dict | None:
    rows = await execute_query(
        "SELECT * FROM event_participation WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (guild_id, user_id, event_id),
    )
    return rows[0] if rows else None


async def ensure_participation(guild_id: int, user_id: int, event_id: str) -> dict:
    participation = await get_participation(guild_id, user_id, event_id)
    if not participation:
        await execute_write(
            "INSERT INTO event_participation (guild_id, user_id, event_id, currency, contributions) VALUES (?, ?, ?, 0, 0)",
            (guild_id, user_id, event_id),
        )
        participation = {"guild_id": guild_id, "user_id": user_id, "event_id": event_id, "currency": 0, "contributions": 0}
    return participation


async def add_currency(guild_id: int, user_id: int, event_id: str, amount: int) -> int:
    await ensure_participation(guild_id, user_id, event_id)
    await execute_write(
        "UPDATE event_participation SET currency = currency + ? WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (amount, guild_id, user_id, event_id),
    )
    rows = await execute_query(
        "SELECT currency FROM event_participation WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (guild_id, user_id, event_id),
    )
    return rows[0]["currency"] if rows else 0


async def spend_currency(guild_id: int, user_id: int, event_id: str, amount: int) -> bool:
    participation = await get_participation(guild_id, user_id, event_id)
    if not participation or participation["currency"] < amount:
        return False

    await execute_write(
        "UPDATE event_participation SET currency = currency - ? WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (amount, guild_id, user_id, event_id),
    )
    return True


async def get_currency(guild_id: int, user_id: int, event_id: str) -> int:
    rows = await execute_query(
        "SELECT currency FROM event_participation WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (guild_id, user_id, event_id),
    )
    return rows[0]["currency"] if rows else 0


async def add_contribution(guild_id: int, user_id: int, event_id: str, amount: int = 1) -> int:
    await ensure_participation(guild_id, user_id, event_id)
    await execute_write(
        "UPDATE event_participation SET contributions = contributions + ? WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (amount, guild_id, user_id, event_id),
    )
    rows = await execute_query(
        "SELECT contributions FROM event_participation WHERE guild_id = ? AND user_id = ? AND event_id = ?",
        (guild_id, user_id, event_id),
    )
    return rows[0]["contributions"] if rows else 0


async def get_participants(guild_id: int, event_id: str) -> list[dict]:
    return await execute_query(
        "SELECT * FROM event_participation WHERE guild_id = ? AND event_id = ? ORDER BY currency DESC",
        (guild_id, event_id),
    )


async def get_leaderboard(guild_id: int, event_id: str, limit: int = 10) -> list[dict]:
    return await execute_query(
        "SELECT * FROM event_participation WHERE guild_id = ? AND event_id = ? ORDER BY currency DESC LIMIT ?",
        (guild_id, event_id, limit),
    )


async def get_participant_count(guild_id: int, event_id: str) -> int:
    rows = await execute_query(
        "SELECT COUNT(*) as count FROM event_participation WHERE guild_id = ? AND event_id = ?",
        (guild_id, event_id),
    )
    return rows[0]["count"] if rows else 0

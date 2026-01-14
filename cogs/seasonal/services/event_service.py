from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from .database import execute_query, execute_write

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def get_active_event(guild_id: int) -> dict | None:
    rows = await execute_query(
        "SELECT * FROM active_events WHERE guild_id = ?",
        (guild_id,),
    )
    if rows:
        row = rows[0]
        row["milestones_reached"] = json.loads(row.get("milestones_reached", "[]"))
        return row
    return None


async def start_event(
    guild_id: int,
    event_id: str,
    community_goal: int,
    ends_at: datetime,
    announcement_channel_id: int | None = None,
    announcement_message_id: int | None = None,
    is_test_event: bool = False,
) -> None:
    now = datetime.now()
    await execute_write(
        """
        INSERT INTO active_events 
        (guild_id, event_id, started_at, ends_at, community_progress, community_goal, milestones_reached, announcement_channel_id, announcement_message_id, last_progress_update, is_test_event)
        VALUES (?, ?, ?, ?, 0, ?, '[]', ?, ?, 0, ?)
        ON CONFLICT (guild_id) DO UPDATE SET
            event_id = EXCLUDED.event_id,
            started_at = EXCLUDED.started_at,
            ends_at = EXCLUDED.ends_at,
            community_progress = 0,
            community_goal = EXCLUDED.community_goal,
            milestones_reached = '[]',
            announcement_channel_id = EXCLUDED.announcement_channel_id,
            announcement_message_id = EXCLUDED.announcement_message_id,
            last_progress_update = 0,
            is_test_event = EXCLUDED.is_test_event
        """,
        (guild_id, event_id, now, ends_at, community_goal, announcement_channel_id, announcement_message_id, is_test_event),
    )
    logger.info(f"Started event {event_id} for guild {guild_id} (test={is_test_event})")


async def end_event(guild_id: int) -> dict | None:
    event = await get_active_event(guild_id)
    if event:
        await execute_write(
            "DELETE FROM active_events WHERE guild_id = ?",
            (guild_id,),
        )
        logger.info(f"Ended event for guild {guild_id}")
    return event


async def update_community_progress(guild_id: int, amount: int) -> int:
    await execute_write(
        "UPDATE active_events SET community_progress = community_progress + ? WHERE guild_id = ?",
        (amount, guild_id),
    )
    rows = await execute_query(
        "SELECT community_progress FROM active_events WHERE guild_id = ?",
        (guild_id,),
    )
    return rows[0]["community_progress"] if rows else 0


async def get_community_progress(guild_id: int) -> tuple[int, int]:
    rows = await execute_query(
        "SELECT community_progress, community_goal FROM active_events WHERE guild_id = ?",
        (guild_id,),
    )
    if rows:
        return rows[0]["community_progress"], rows[0]["community_goal"]
    return 0, 0


async def add_milestone_reached(guild_id: int, percent: int) -> None:
    event = await get_active_event(guild_id)
    if not event:
        return

    milestones = event.get("milestones_reached", [])
    if percent not in milestones:
        milestones.append(percent)
        await execute_write(
            "UPDATE active_events SET milestones_reached = ? WHERE guild_id = ?",
            (json.dumps(milestones), guild_id),
        )


async def get_milestones_reached(guild_id: int) -> list[int]:
    event = await get_active_event(guild_id)
    if event:
        return event.get("milestones_reached", [])
    return []


async def set_announcement_message(
    guild_id: int, channel_id: int, message_id: int
) -> None:
    await execute_write(
        "UPDATE active_events SET announcement_channel_id = ?, announcement_message_id = ? WHERE guild_id = ?",
        (channel_id, message_id, guild_id),
    )


async def get_announcement_message(guild_id: int) -> tuple[int | None, int | None]:
    rows = await execute_query(
        "SELECT announcement_channel_id, announcement_message_id FROM active_events WHERE guild_id = ?",
        (guild_id,),
    )
    if rows:
        return rows[0].get("announcement_channel_id"), rows[0].get("announcement_message_id")
    return None, None


async def update_last_progress(guild_id: int, progress: int) -> None:
    await execute_write(
        "UPDATE active_events SET last_progress_update = ? WHERE guild_id = ?",
        (progress, guild_id),
    )


async def get_last_progress(guild_id: int) -> int:
    rows = await execute_query(
        "SELECT last_progress_update FROM active_events WHERE guild_id = ?",
        (guild_id,),
    )
    return rows[0].get("last_progress_update", 0) if rows else 0

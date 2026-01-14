"""Community goal service for seasonal events.

Tracks community-wide progress toward event milestones and handles
milestone completion rewards.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .database import execute_query, execute_write
from .participation_service import (
    add_currency,
    add_milestone_reached,
    get_community_progress,
    get_milestones_reached,
    update_community_progress,
)

logger = logging.getLogger(__name__)


@dataclass
class Milestone:
    """A community milestone with threshold and rewards."""

    percentage: int
    title_key: str | None
    currency_bonus: int
    description: str


@dataclass
class CommunityGoalStatus:
    """Current status of community goal."""

    goal_type: str
    goal_target: int
    current_progress: int
    percentage: float
    milestones: list[Milestone]
    reached_milestones: list[int]
    next_milestone: Milestone | None


def _load_event_milestones(event_type: str) -> tuple[dict[str, Any], list[Milestone]]:
    """Load milestones from event JSON file."""
    base_type = event_type.split("_")[0]
    json_path = Path(__file__).parent.parent.parent.parent / "data" / "events" / f"{base_type}.json"

    if not json_path.exists():
        logger.warning(f"Event file not found: {json_path}")
        return {}, []

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        goal_data = data.get("community_goal", {})
        milestones_data = data.get("milestones", [])

        milestones = [
            Milestone(
                percentage=m["percentage"],
                title_key=m.get("title"),
                currency_bonus=m.get("currency_bonus", 0),
                description=m.get("description", ""),
            )
            for m in milestones_data
        ]

        return goal_data, milestones
    except Exception as e:
        logger.exception(f"Failed to load milestones: {e}")
        return {}, []


async def get_community_goal_status(
    guild_id: int, event_id: str
) -> CommunityGoalStatus | None:
    """Get the current community goal status for an event.

    Args:
        guild_id: The guild ID.
        event_id: The event ID.

    Returns:
        CommunityGoalStatus or None if no goal defined.
    """
    goal_data, milestones = _load_event_milestones(event_id)

    if not goal_data:
        return None

    current_progress = await get_community_progress(guild_id, event_id)
    reached = await get_milestones_reached(guild_id, event_id)

    goal_target = goal_data.get("target", 0)
    if goal_target <= 0:
        return None

    percentage = min(100.0, (current_progress / goal_target) * 100)

    next_milestone = None
    for m in milestones:
        if m.percentage not in reached and m.percentage > percentage:
            next_milestone = m
            break

    return CommunityGoalStatus(
        goal_type=goal_data.get("type", "unknown"),
        goal_target=goal_target,
        current_progress=current_progress,
        percentage=percentage,
        milestones=milestones,
        reached_milestones=list(reached),
        next_milestone=next_milestone,
    )


async def add_community_contribution(
    guild_id: int, event_id: str, amount: int = 1
) -> list[Milestone]:
    """Add a contribution to community goal and check for milestone completions.

    Args:
        guild_id: The guild ID.
        event_id: The event ID.
        amount: Amount to add to progress.

    Returns:
        List of newly reached milestones.
    """
    goal_data, milestones = _load_event_milestones(event_id)

    if not goal_data:
        return []

    goal_target = goal_data.get("target", 0)
    if goal_target <= 0:
        return []

    old_progress = await get_community_progress(guild_id, event_id)
    new_progress = old_progress + amount
    await update_community_progress(guild_id, event_id, amount)

    old_percentage = (old_progress / goal_target) * 100
    new_percentage = (new_progress / goal_target) * 100

    reached = await get_milestones_reached(guild_id, event_id)
    newly_reached = []

    for m in milestones:
        if m.percentage in reached:
            continue
        if old_percentage < m.percentage <= new_percentage:
            await add_milestone_reached(guild_id, event_id, m.percentage)
            newly_reached.append(m)
            logger.info(
                f"Guild {guild_id} reached {m.percentage}% milestone "
                f"for event {event_id}"
            )

    return newly_reached


async def distribute_milestone_rewards(
    guild_id: int, event_id: str, milestone: Milestone
) -> list[int]:
    """Distribute rewards to all participants for reaching a milestone.

    Args:
        guild_id: The guild ID.
        event_id: The event ID.
        milestone: The milestone that was reached.

    Returns:
        List of user IDs who received rewards.
    """
    from .participation_service import get_participants
    from .title_service import unlock_title

    participants = await get_participants(guild_id, event_id)
    rewarded_users = []

    for user_id in participants:
        if milestone.currency_bonus > 0:
            await add_currency(guild_id, user_id, event_id, milestone.currency_bonus)

        if milestone.title_key:
            await unlock_title(guild_id, user_id, milestone.title_key, event_id)

        rewarded_users.append(user_id)

    logger.info(
        f"Distributed {milestone.percentage}% milestone rewards to "
        f"{len(rewarded_users)} users in guild {guild_id}"
    )

    return rewarded_users


async def get_contribution_leaderboard(
    guild_id: int, event_id: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Get top contributors for the community goal.

    Args:
        guild_id: The guild ID.
        event_id: The event ID.
        limit: Maximum number of entries.

    Returns:
        List of dicts with user_id and contribution amount.
    """
    goal_data, _ = _load_event_milestones(event_id)
    goal_type = goal_data.get("type", "")

    table_mapping = {
        "treasure": ("treasure_hunt_daily", "treasures_found"),
        "ghost": ("ghost_hunt_daily", "catch_count"),
        "thank_letter": ("thank_letters", "COUNT(*)"),
        "snowman": ("snowman_contributions", "SUM(amount)"),
        "trash": ("beach_cleanup_daily", "trash_collected"),
        "lantern": ("lantern_parade", "lanterns"),
        "wish": ("birthday_wishes", "COUNT(*)"),
    }

    if goal_type not in table_mapping:
        return []

    table, column = table_mapping[goal_type]

    if column.startswith("COUNT") or column.startswith("SUM"):
        query = f"""
            SELECT user_id, {column} as contribution
            FROM {table}
            WHERE guild_id = $1 AND event_id = $2
            GROUP BY user_id
            ORDER BY contribution DESC
            LIMIT $3
        """
    else:
        query = f"""
            SELECT user_id, SUM({column}) as contribution
            FROM {table}
            WHERE guild_id = $1 AND event_id = $2
            GROUP BY user_id
            ORDER BY contribution DESC
            LIMIT $3
        """

    rows = await execute_query(query, (guild_id, event_id, limit))
    return [{"user_id": row["user_id"], "contribution": row["contribution"]} for row in rows]


async def reset_community_goal(guild_id: int, event_id: str) -> None:
    """Reset community goal progress (for testing).

    Args:
        guild_id: The guild ID.
        event_id: The event ID.
    """
    await execute_write(
        """
        UPDATE active_events
        SET community_progress = 0, milestones_reached = $1
        WHERE guild_id = $2 AND event_id = $3
        """,
        ("[]", guild_id, event_id),
    )
    logger.info(f"Reset community goal for guild {guild_id}, event {event_id}")

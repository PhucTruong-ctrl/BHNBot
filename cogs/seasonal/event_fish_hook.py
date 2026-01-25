"""Event fish integration service.

Provides a hook for the fishing system to add event fish to catches.
Call `try_catch_event_fish()` after a regular fishing catch.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .services import (
    add_currency,
    ensure_participation,
    get_active_event,
    update_quest_progress,
)
from .services.community_goal_service import add_community_contribution, distribute_milestone_rewards
from .services.database import execute_write, execute_query
from .core.event_manager import EventManager

if TYPE_CHECKING:
    from .core.event_types import EventFishConfig
    import discord


@dataclass
class EventFishCatch:
    fish: EventFishConfig
    currency_earned: int
    is_new_collection: bool
    remaining_uncaught: int = 0


async def try_catch_event_fish(
    bot,
    user_id: int,
    guild_id: int,
    event_manager: EventManager | None = None,
) -> EventFishCatch | None:
    """Attempt to catch an event fish during fishing.

    Should be called after a regular fishing catch. Has 15% chance
    to catch an event fish if an event is active.

    Args:
        bot: Bot instance for achievement tracking.
        user_id: The user ID.
        guild_id: The guild ID.
        event_manager: Optional EventManager instance.

    Returns:
        EventFishCatch if a fish was caught, None otherwise.
    """
    active = await get_active_event(guild_id)
    if not active:
        return None

    if event_manager is None:
        event_manager = EventManager()

    event = event_manager.get_event(active["event_id"])
    if not event or not event.fish:
        return None

    if random.random() > 0.15:
        return None

    await ensure_participation(guild_id, user_id, active["event_id"])

    # Use actual drop_rate from fish config (not index-based weights)
    weights = [f.drop_rate for f in event.fish]

    chosen = random.choices(event.fish, weights=weights, k=1)[0]
    currency_reward = chosen.currency_reward

    await add_currency(guild_id, user_id, active["event_id"], currency_reward)

    existing = await _check_collection(guild_id, user_id, active["event_id"], chosen.key)
    is_new = not existing
    
    remaining = 0
    if chosen.tier == "epic" and is_new:
        remaining = await _count_users_without_fish(guild_id, active["event_id"], chosen.key)

    await _add_to_collection(guild_id, user_id, active["event_id"], chosen.key)
    await update_quest_progress(guild_id, user_id, active["event_id"], "catch_event_fish", 1)
    
    newly_reached = await add_community_contribution(guild_id, active["event_id"], 1)
    for milestone in newly_reached:
        await distribute_milestone_rewards(guild_id, active["event_id"], milestone, bot)
    
    if bot and hasattr(bot, "achievement_manager") and bot.achievement_manager:
        await bot.achievement_manager.check_seasonal_unlock(
            user_id=user_id,
            event_id=active["event_id"],
            condition_type="catch_specific_fish",
            condition_key=chosen.key,
            current_value=1,
            channel=None,
        )

    return EventFishCatch(
        fish=chosen,
        currency_earned=currency_reward,
        is_new_collection=is_new,
        remaining_uncaught=remaining,
    )


async def _check_collection(
    guild_id: int, user_id: int, event_id: str, fish_key: str
) -> bool:
    from .services.database import execute_query

    rows = await execute_query(
        """
        SELECT 1 FROM event_fish_collection
        WHERE guild_id = $1 AND user_id = $2 AND event_id = $3 AND fish_key = $4
        LIMIT 1
        """,
        (guild_id, user_id, event_id, fish_key),
    )
    return len(rows) > 0


async def _add_to_collection(
    guild_id: int, user_id: int, event_id: str, fish_key: str
) -> None:
    await execute_write(
        """
        INSERT INTO event_fish_collection (guild_id, user_id, event_id, fish_key, caught_at)
        VALUES ($1, $2, $3, $4, NOW())
        ON CONFLICT (guild_id, user_id, event_id, fish_key) 
        DO UPDATE SET quantity = event_fish_collection.quantity + 1
        """,
        (guild_id, user_id, event_id, fish_key),
    )


async def _count_users_without_fish(guild_id: int, event_id: str, fish_key: str) -> int:
    rows = await execute_query(
        """
        SELECT COUNT(DISTINCT ep.user_id) as total
        FROM event_participation ep
        WHERE ep.guild_id = $1 AND ep.event_id = $2
        AND NOT EXISTS (
            SELECT 1 FROM event_fish_collection efc
            WHERE efc.guild_id = ep.guild_id 
            AND efc.user_id = ep.user_id 
            AND efc.event_id = ep.event_id
            AND efc.fish_key = $3
        )
        """,
        (guild_id, event_id, fish_key),
    )
    return rows[0]["total"] if rows else 0


async def announce_epic_catch(
    channel: discord.TextChannel,
    user: discord.Member,
    catch: EventFishCatch,
    event_name: str,
) -> None:
    if catch.fish.tier != "epic":
        return
    
    import discord as discord_lib
    
    embed = discord_lib.Embed(
        title="🎣✨ CÁ EPIC ĐÃ XUẤT HIỆN!",
        description=f"**{user.display_name}** vừa bắt được **{catch.fish.name}** {catch.fish.emoji}!",
        color=0xFFD700,
    )
    
    if catch.is_new_collection:
        embed.add_field(
            name="🆕 Lần đầu bắt được!",
            value=f"Còn **{catch.remaining_uncaught}** người chưa có con cá này!",
            inline=False,
        )
    
    embed.set_footer(text=f"Sự kiện {event_name}")
    
    await channel.send(embed=embed)


async def get_event_fish_for_display(
    guild_id: int,
) -> tuple[str, str, int] | None:
    """Get active event fish info for displaying in fishing results.

    Returns:
        Tuple of (event_name, currency_emoji, fish_count) or None.
    """
    active = await get_active_event(guild_id)
    if not active:
        return None

    event_manager = EventManager()
    event = event_manager.get_event(active["event_id"])
    if not event or not event.fish:
        return None

    return (event.name, event.currency_emoji, len(event.fish))

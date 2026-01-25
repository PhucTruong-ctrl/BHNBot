from __future__ import annotations

from core.logging import get_logger
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress
from ..services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = get_logger("seasonal_minigames_lantern_par")


@register_minigame("lantern_parade")
class LanternParadeMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)

    @property
    def name(self) -> str:
        return "Rước Đèn Trung Thu"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "voice_tracking",
            "minutes_per_reward": 5,
            "max_daily_minutes": 60,
        }

    def _get_config(self, event: Any) -> dict[str, Any]:
        """Get minigame config from event with fallbacks."""
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("lantern_parade", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def track_voice_time(self, guild_id: int, user_id: int, minutes: int) -> int:
        active = await get_active_event(guild_id)
        if not active:
            return 0

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return 0

        config = self._get_config(event)
        daily_cap = config.get("daily_cap_minutes", 60)
        reward_per_5 = config.get("currency_per_5min", 5)
        lantern_per_5 = config.get("lanterns_per_5min", 1)

        today_minutes = await self._get_today_minutes(guild_id, user_id, active["event_id"])
        remaining_cap = max(0, daily_cap - today_minutes)
        eligible_minutes = min(minutes, remaining_cap)

        if eligible_minutes <= 0:
            return 0

        intervals = eligible_minutes // 5
        if intervals <= 0:
            await self._record_minutes(guild_id, user_id, active["event_id"], eligible_minutes)
            return 0

        reward = intervals * reward_per_5
        lanterns = intervals * lantern_per_5

        await add_currency(guild_id, user_id, active["event_id"], reward)
        await add_contribution(guild_id, user_id, active["event_id"], reward)
        await update_community_progress(guild_id, active["event_id"], lanterns)
        await self._record_minutes(guild_id, user_id, active["event_id"], eligible_minutes)
        await self._add_lanterns(guild_id, user_id, active["event_id"], lanterns)

        return reward

    async def get_user_lanterns(self, guild_id: int, user_id: int, event_id: str) -> int:
        rows = await execute_query(
            "SELECT lanterns FROM lantern_parade WHERE guild_id = ? AND user_id = ? AND event_id = ?",
            (guild_id, user_id, event_id),
        )
        return rows[0]["lanterns"] if rows else 0

    async def show_parade(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        top_lanterns = await self._get_top_lanterns(guild_id, active["event_id"])

        parade_text = []
        for i, row in enumerate(top_lanterns[:10], 1):
            user = self.bot.get_user(row["user_id"])
            name = user.display_name if user else f"User {row['user_id']}"
            lanterns = "🏮" * min(row["lanterns"], 10)
            parade_text.append(f"{i}. {name}: {lanterns} ({row['lanterns']})")

        embed = discord.Embed(
            title="🏮 ĐOÀN RƯỚC ĐÈN TRUNG THU",
            description="Tham gia voice chat để nhận đèn lồng!",
            color=event.color if event else 0xFFD700,
        )
        if parade_text:
            embed.add_field(name="🏆 Top Rước Đèn", value="\n".join(parade_text), inline=False)
        embed.set_footer(text="Mỗi 5 phút voice chat = 1 đèn lồng + 5 🥮")

        await interaction.response.send_message(embed=embed)

    async def _get_today_minutes(self, guild_id: int, user_id: int, event_id: str) -> int:
        today = datetime.now().date().isoformat()
        rows = await execute_query(
            """
            SELECT SUM(minutes) as total FROM lantern_voice_time
            WHERE guild_id = ? AND user_id = ? AND event_id = ? AND DATE(tracked_at) = ?
            """,
            (guild_id, user_id, event_id, today),
        )
        return rows[0]["total"] or 0 if rows else 0

    async def _record_minutes(self, guild_id: int, user_id: int, event_id: str, minutes: int) -> None:
        await execute_write(
            """
            INSERT INTO lantern_voice_time (guild_id, user_id, event_id, minutes, tracked_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, event_id, minutes, datetime.now().isoformat()),
        )

    async def _add_lanterns(self, guild_id: int, user_id: int, event_id: str, count: int) -> None:
        await execute_write(
            """
            INSERT INTO lantern_parade (guild_id, user_id, event_id, lanterns)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (guild_id, user_id, event_id) DO UPDATE SET
                lanterns = lantern_parade.lanterns + ?
            """,
            (guild_id, user_id, event_id, count, count),
        )

    async def _get_top_lanterns(self, guild_id: int, event_id: str) -> list[dict]:
        return await execute_query(
            """
            SELECT user_id, lanterns FROM lantern_parade
            WHERE guild_id = ? AND event_id = ?
            ORDER BY lanterns DESC
            LIMIT 10
            """,
            (guild_id, event_id),
        )

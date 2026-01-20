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

logger = get_logger("seasonal_minigames_snowman")


DEFAULT_SNOWMAN_PARTS = [
    {"emoji": "⛄", "name": "Tuyết", "contribution": 1},
    {"emoji": "🥕", "name": "Cà Rốt", "contribution": 2},
    {"emoji": "🎩", "name": "Mũ", "contribution": 3},
    {"emoji": "🧣", "name": "Khăn", "contribution": 2},
    {"emoji": "🪵", "name": "Cành Cây", "contribution": 1},
]


@register_minigame("snowman")
class SnowmanMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)

    @property
    def name(self) -> str:
        return "Người Tuyết Cộng Đồng"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "manual",
            "daily_contributions": 10,
            "snow_per_contribution": [1, 3],
        }

    def _get_config(self, event: Any) -> dict[str, Any]:
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("snowman", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def contribute_snow(self, interaction: Interaction, amount: int = 1) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy sự kiện!", ephemeral=True)
            return

        config = self._get_config(event)
        daily_limit = config.get("daily_limit", 20)

        today_contributions = await self._get_today_contributions(guild_id, user_id, active["event_id"])
        if today_contributions >= daily_limit:
            await interaction.response.send_message(
                f"❌ Bạn đã góp đủ {daily_limit} tuyết hôm nay!", ephemeral=True
            )
            return

        actual_amount = min(amount, daily_limit - today_contributions)

        await self._record_contribution(guild_id, user_id, active["event_id"], actual_amount)
        await update_community_progress(guild_id, actual_amount)

        reward_per = config.get("reward_per_contribution", 5)
        total_reward = actual_amount * reward_per
        await add_currency(guild_id, user_id, active["event_id"], total_reward)
        await add_contribution(guild_id, user_id, active["event_id"], total_reward)

        emoji = event.currency_emoji if event else "❄️"
        progress = await self._get_snowman_progress(guild_id, active["event_id"])
        goal = config.get("goal_per_snowman", 100)
        snowmen_built = progress // goal
        current_progress = progress % goal

        await interaction.response.send_message(
            f"⛄ Bạn góp **{actual_amount}** tuyết! +**{total_reward}** {emoji}\n"
            f"Tiến độ: {current_progress}/{goal} (Đã xây: {snowmen_built} người tuyết)",
            ephemeral=True,
        )

    async def show_progress(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        config = self._get_config(event)
        goal = config.get("goal_per_snowman", 100)

        progress = await self._get_snowman_progress(guild_id, active["event_id"])
        snowmen_built = progress // goal
        current_progress = progress % goal
        progress_percent = (current_progress / goal) * 100

        bar_filled = int(progress_percent // 10)
        bar_empty = 10 - bar_filled
        progress_bar = "⬜" * bar_filled + "⬛" * bar_empty

        top_contributors = await self._get_top_contributors(guild_id, active["event_id"])
        contributors_text = []
        for i, c in enumerate(top_contributors[:5], 1):
            user = self.bot.get_user(c["user_id"])
            name = user.display_name if user else f"User {c['user_id']}"
            contributors_text.append(f"{i}. {name}: {c['total']} tuyết")

        embed = discord.Embed(
            title="⛄ NGƯỜI TUYẾT CỘNG ĐỒNG",
            description=f"Đã xây được **{snowmen_built}** người tuyết!",
            color=event.color if event else 0x87CEEB,
        )
        embed.add_field(
            name=f"Tiến độ ({current_progress}/{goal})",
            value=f"{progress_bar} {progress_percent:.1f}%",
            inline=False,
        )
        if contributors_text:
            embed.add_field(name="🏆 Top góp tuyết", value="\n".join(contributors_text), inline=False)

        snowman_art = "⛄" * min(snowmen_built, 10)
        if snowman_art:
            embed.add_field(name="❄️ Người tuyết", value=snowman_art, inline=False)

        await interaction.response.send_message(embed=embed)

    async def _get_today_contributions(self, guild_id: int, user_id: int, event_id: str) -> int:
        today = datetime.now().date().isoformat()
        rows = await execute_query(
            """
            SELECT SUM(amount) as total FROM snowman_contributions
            WHERE guild_id = ? AND user_id = ? AND event_id = ? AND DATE(contributed_at) = ?
            """,
            (guild_id, user_id, event_id, today),
        )
        return rows[0]["total"] or 0 if rows else 0

    async def _record_contribution(self, guild_id: int, user_id: int, event_id: str, amount: int) -> None:
        await execute_write(
            """
            INSERT INTO snowman_contributions (guild_id, user_id, event_id, amount, contributed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, event_id, amount, datetime.now().isoformat()),
        )

    async def _get_snowman_progress(self, guild_id: int, event_id: str) -> int:
        rows = await execute_query(
            "SELECT SUM(amount) as total FROM snowman_contributions WHERE guild_id = ? AND event_id = ?",
            (guild_id, event_id),
        )
        return rows[0]["total"] or 0 if rows else 0

    async def _get_top_contributors(self, guild_id: int, event_id: str) -> list[dict]:
        return await execute_query(
            """
            SELECT user_id, SUM(amount) as total FROM snowman_contributions
            WHERE guild_id = ? AND event_id = ?
            GROUP BY user_id
            ORDER BY total DESC
            LIMIT 5
            """,
            (guild_id, event_id),
        )

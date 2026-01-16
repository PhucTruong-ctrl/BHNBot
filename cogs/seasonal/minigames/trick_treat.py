from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_currency, get_active_event, get_currency
from ..services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("TrickTreat")


DEFAULT_TRICK_RESULTS = [
    {"type": "trick", "emoji": "🎃", "message": "Trick! Bạn bị ném trứng!", "amount": -10},
    {"type": "trick", "emoji": "🕷️", "message": "Trick! Nhện chui vào túi bạn!", "amount": -15},
    {"type": "trick", "emoji": "💀", "message": "Trick! Ma dọa bạn chạy mất dép!", "amount": -5},
]

DEFAULT_TREAT_RESULTS = [
    {"type": "treat", "emoji": "🍬", "message": "Treat! Nhận được kẹo ngọt!", "amount": 30},
    {"type": "treat", "emoji": "🍫", "message": "Treat! Socola thơm ngon!", "amount": 35},
    {"type": "treat", "emoji": "🧁", "message": "Treat! Cupcake Halloween!", "amount": 40},
    {"type": "treat", "emoji": "🍭", "message": "Treat! Kẹo mút ma quái!", "amount": 25},
]


@register_minigame("trick_treat")
class TrickTreatMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)

    @property
    def name(self) -> str:
        return "Trick or Treat"

    def _get_config(self, event: Any) -> dict[str, Any]:
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("trick_treat", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def trick_or_treat(
        self,
        interaction: Interaction,
        target_user: discord.User | discord.Member,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        if target_user.bot:
            await interaction.response.send_message("❌ Không thể trick or treat với bot!", ephemeral=True)
            return

        if target_user.id == interaction.user.id:
            await interaction.response.send_message("❌ Bạn không thể trick or treat chính mình!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện Halloween!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy thông tin sự kiện!", ephemeral=True)
            return

        config = self._get_config(event)
        daily_limit = config.get("daily_limit", 5)
        cooldown = config.get("cooldown_seconds", 300)

        uses_today = await self._get_daily_uses(guild_id, user_id, active["event_id"])
        if uses_today >= daily_limit:
            await interaction.response.send_message(
                f"❌ Bạn đã trick or treat đủ {daily_limit} lần hôm nay!", ephemeral=True
            )
            return

        last_use = await self._get_last_use_time(guild_id, user_id, active["event_id"])
        if last_use:
            elapsed = (datetime.now() - last_use).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                await interaction.response.send_message(
                    f"❌ Chờ **{remaining}** giây nữa mới trick or treat được!", ephemeral=True
                )
                return

        trick_chance = config.get("trick_chance", 0.3)
        trick_results = config.get("trick_results", DEFAULT_TRICK_RESULTS)
        treat_results = config.get("treat_results", DEFAULT_TREAT_RESULTS)
        is_trick = random.random() < trick_chance

        if is_trick:
            result = random.choice(trick_results)
        else:
            result = random.choice(treat_results)

        await add_currency(guild_id, user_id, active["event_id"], result["amount"])
        await self._record_use(guild_id, user_id, active["event_id"])

        emoji = event.currency_emoji if event else "🍬"

        if result["amount"] > 0:
            amount_text = f"+**{result['amount']}** {emoji}"
        else:
            amount_text = f"**{result['amount']}** {emoji}"

        embed = discord.Embed(
            title=f"🎃 TRICK OR TREAT!",
            description=(
                f"{interaction.user.mention} gõ cửa nhà {target_user.mention}...\n\n"
                f"{result['emoji']} **{result['message']}**\n\n"
                f"Kết quả: {amount_text}"
            ),
            color=event.color if is_trick else event.color,
        )
        embed.set_footer(text=f"Còn {daily_limit - uses_today - 1} lượt hôm nay")

        await interaction.response.send_message(embed=embed)

    async def _get_daily_uses(self, guild_id: int, user_id: int, event_id: str) -> int:
        today = datetime.now().date().isoformat()
        rows = await execute_query(
            """
            SELECT use_count FROM trick_treat_daily
            WHERE guild_id = ? AND user_id = ? AND event_id = ? AND date = ?
            """,
            (guild_id, user_id, event_id, today),
        )
        return rows[0]["use_count"] if rows else 0

    async def _get_last_use_time(self, guild_id: int, user_id: int, event_id: str) -> datetime | None:
        rows = await execute_query(
            """
            SELECT last_use FROM trick_treat_daily
            WHERE guild_id = ? AND user_id = ? AND event_id = ?
            ORDER BY last_use DESC LIMIT 1
            """,
            (guild_id, user_id, event_id),
        )
        if rows and rows[0]["last_use"]:
            return datetime.fromisoformat(rows[0]["last_use"])
        return None

    async def _record_use(self, guild_id: int, user_id: int, event_id: str) -> None:
        today = datetime.now().date().isoformat()
        now = datetime.now().isoformat()
        await execute_write(
            """
            INSERT INTO trick_treat_daily (guild_id, user_id, event_id, date, use_count, last_use)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT (guild_id, user_id, event_id, date) DO UPDATE SET
                use_count = trick_treat_daily.use_count + 1,
                last_use = ?
            """,
            (guild_id, user_id, event_id, today, now, now),
        )

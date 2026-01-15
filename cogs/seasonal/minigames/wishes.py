from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress
from ..services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("Wishes")


@register_minigame("wishes")
class WishesMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)

    @property
    def name(self) -> str:
        return "Gửi Lời Chúc"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "manual",
            "daily_limit": 3,
            "reward_per_wish": 20,
            "min_length": 10,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def send_wish(self, interaction: Interaction, message: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện sinh nhật đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy sự kiện!", ephemeral=True)
            return

        config = self.spawn_config
        daily_limit = config.get("daily_limit", 3)
        min_length = config.get("min_length", 10)

        if len(message.strip()) < min_length:
            await interaction.response.send_message(
                f"❌ Lời chúc phải có ít nhất {min_length} ký tự!", ephemeral=True
            )
            return

        wishes_today = await self._get_wishes_today(guild_id, user_id, active["event_id"])
        if wishes_today >= daily_limit:
            await interaction.response.send_message(
                f"❌ Bạn đã gửi đủ {daily_limit} lời chúc hôm nay!", ephemeral=True
            )
            return

        reward = config.get("reward_per_wish", 20)
        await add_currency(guild_id, user_id, active["event_id"], reward)
        await add_contribution(guild_id, user_id, active["event_id"], reward)
        await update_community_progress(guild_id, 1)
        await self._record_wish(guild_id, user_id, active["event_id"], message)

        emoji = event.currency_emoji if event else "🎈"

        embed = discord.Embed(
            title="🎂 LỜI CHÚC SINH NHẬT",
            description=f"**{interaction.user.display_name}** gửi lời chúc:",
            color=event.color if event else 0xFF69B4,
        )
        embed.add_field(name="💌 Nội dung", value=message[:500], inline=False)
        embed.add_field(name="🎁 Phần thưởng", value=f"+{reward} {emoji}", inline=True)
        embed.set_footer(text=f"Còn {daily_limit - wishes_today - 1} lời chúc hôm nay")

        await interaction.response.send_message(embed=embed)

    async def show_wishes(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        guild_id = interaction.guild.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Không có sự kiện đang diễn ra!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        recent_wishes = await self._get_recent_wishes(guild_id, active["event_id"])

        embed = discord.Embed(
            title="🎂 BẢNG LỜI CHÚC SINH NHẬT",
            description="Những lời chúc gần đây nhất:",
            color=event.color if event else 0xFF69B4,
        )

        if recent_wishes:
            for wish in recent_wishes[:10]:
                user = self.bot.get_user(wish["user_id"])
                name = user.display_name if user else f"User {wish['user_id']}"
                message = wish["message"][:100] + "..." if len(wish["message"]) > 100 else wish["message"]
                embed.add_field(name=f"💌 {name}", value=message, inline=False)
        else:
            embed.add_field(name="📭", value="Chưa có lời chúc nào!", inline=False)

        await interaction.response.send_message(embed=embed)

    async def _get_wishes_today(self, guild_id: int, user_id: int, event_id: str) -> int:
        today = datetime.now().date().isoformat()
        rows = await execute_query(
            """
            SELECT COUNT(*) as count FROM birthday_wishes
            WHERE guild_id = ? AND user_id = ? AND event_id = ? AND DATE(sent_at) = ?
            """,
            (guild_id, user_id, event_id, today),
        )
        return rows[0]["count"] if rows else 0

    async def _record_wish(self, guild_id: int, user_id: int, event_id: str, message: str) -> None:
        await execute_write(
            """
            INSERT INTO birthday_wishes (guild_id, user_id, event_id, message, sent_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, event_id, message, datetime.now().isoformat()),
        )

    async def _get_recent_wishes(self, guild_id: int, event_id: str) -> list[dict]:
        return await execute_query(
            """
            SELECT user_id, message, sent_at FROM birthday_wishes
            WHERE guild_id = ? AND event_id = ?
            ORDER BY sent_at DESC
            LIMIT 10
            """,
            (guild_id, event_id),
        )

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

logger = get_logger("seasonal_minigames_thank_lette")


@register_minigame("thank_letter")
class ThankLetterMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)

    @property
    def name(self) -> str:
        return "Thư Cảm Ơn"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "manual",
            "daily_limit": 3,
            "reward_sender": 20,
            "reward_receiver": 20,
            "min_length": 20,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def send_thank_letter(
        self,
        interaction: Interaction,
        target_user: discord.User | discord.Member,
        message: str,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("❌ Chỉ dùng được trong server!", ephemeral=True)
            return

        if target_user.bot:
            await interaction.response.send_message("❌ Không thể gửi thư cho bot!", ephemeral=True)
            return

        if target_user.id == interaction.user.id:
            await interaction.response.send_message("❌ Không thể gửi thư cho chính mình!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        active = await get_active_event(guild_id)
        if not active:
            await interaction.response.send_message("❌ Hiện không có sự kiện Thu!", ephemeral=True)
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            await interaction.response.send_message("❌ Không tìm thấy thông tin sự kiện!", ephemeral=True)
            return

        config = self.spawn_config
        daily_limit = config.get("daily_limit", 3)
        min_length = config.get("min_length", 20)

        if len(message.strip()) < min_length:
            await interaction.response.send_message(
                f"❌ Thư cảm ơn phải có ít nhất {min_length} ký tự!", ephemeral=True
            )
            return

        sent_today = await self._get_letters_sent_today(guild_id, user_id, active["event_id"])
        if sent_today >= daily_limit:
            await interaction.response.send_message(
                f"❌ Bạn đã gửi đủ {daily_limit} thư hôm nay!", ephemeral=True
            )
            return

        reward_sender = config.get("reward_sender", 20)
        reward_receiver = config.get("reward_receiver", 20)

        await add_currency(guild_id, user_id, active["event_id"], reward_sender)
        await add_currency(guild_id, target_user.id, active["event_id"], reward_receiver)
        await add_contribution(guild_id, user_id, active["event_id"], reward_sender)
        await update_community_progress(guild_id, active["event_id"], 1)
        await self._record_letter(guild_id, user_id, target_user.id, active["event_id"], message)

        emoji = event.currency_emoji if event else "🍂"

        embed = discord.Embed(
            title="💌 THƯ CẢM ƠN",
            description=f"**Từ:** {interaction.user.mention}\n**Gửi:** {target_user.mention}",
            color=event.color if event else 0xD2691E,
        )
        embed.add_field(name="📝 Nội dung", value=message[:500], inline=False)
        embed.add_field(
            name="🎁 Phần thưởng",
            value=f"Người gửi: +{reward_sender} {emoji}\nNgười nhận: +{reward_receiver} {emoji}",
            inline=False,
        )
        embed.set_footer(text=f"Còn {daily_limit - sent_today - 1} thư hôm nay")

        await interaction.response.send_message(embed=embed)

    async def _get_letters_sent_today(self, guild_id: int, user_id: int, event_id: str) -> int:
        today = datetime.now().date().isoformat()
        rows = await execute_query(
            """
            SELECT COUNT(*) as count FROM thank_letters
            WHERE guild_id = ? AND sender_id = ? AND event_id = ? AND DATE(sent_at) = ?
            """,
            (guild_id, user_id, event_id, today),
        )
        return rows[0]["count"] if rows else 0

    async def _record_letter(
        self, guild_id: int, sender_id: int, receiver_id: int, event_id: str, message: str
    ) -> None:
        await execute_write(
            """
            INSERT INTO thank_letters (guild_id, sender_id, receiver_id, event_id, message, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild_id, sender_id, receiver_id, event_id, message, datetime.now().isoformat()),
        )

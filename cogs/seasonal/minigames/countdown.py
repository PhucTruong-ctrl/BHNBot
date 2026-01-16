from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("Countdown")


@register_minigame("countdown")
class CountdownMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_countdowns: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Đếm Ngược Năm Mới"

    def _get_config(self, event: Any) -> dict[str, Any]:
        """Get minigame config from event with fallbacks."""
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("countdown", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def start_countdown(self, channel: TextChannel, guild_id: int, target_time: datetime | None = None) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        if target_time is None:
            now = datetime.now()
            target_time = datetime(now.year + 1, 1, 1, 0, 0, 0)

        embed = discord.Embed(
            title="🎆 ĐẾM NGƯỢC NĂM MỚI!",
            description=f"Năm mới sẽ đến vào: <t:{int(target_time.timestamp())}:F>",
            color=event.color if event else 0xFFD700,
        )
        embed.add_field(
            name="⏰ Còn",
            value=f"<t:{int(target_time.timestamp())}:R>",
            inline=False,
        )
        embed.add_field(
            name="📢 Hướng dẫn",
            value="Khi đồng hồ điểm 0, react 🎆 để nhận thưởng!\n10 người đầu tiên nhận bonus!",
            inline=False,
        )

        message = await channel.send(embed=embed)

        self._active_countdowns[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "target_time": target_time,
            "message": message,
            "channel": channel,
            "participants": [],
            "triggered": False,
        }

        delay = (target_time - datetime.now()).total_seconds()
        if delay > 0:
            asyncio.create_task(self._countdown_timer(message.id, delay))

    async def _countdown_timer(self, message_id: int, delay: float) -> None:
        if delay > 60:
            await asyncio.sleep(delay - 60)

            data = self._active_countdowns.get(message_id)
            if data and not data["triggered"]:
                embed = discord.Embed(
                    title="🎆 60 GIÂY NỮA LÀ NĂM MỚI!",
                    description="Chuẩn bị react 🎆 khi đồng hồ điểm 0!",
                    color=0xFF0000,
                )
                try:
                    await data["message"].edit(embed=embed)
                except discord.NotFound:
                    pass

            await asyncio.sleep(60)
        else:
            await asyncio.sleep(max(delay, 0))

        await self._trigger_countdown(message_id)

    async def _trigger_countdown(self, message_id: int) -> None:
        data = self._active_countdowns.get(message_id)
        if not data or data["triggered"]:
            return

        data["triggered"] = True
        event = self.event_manager.get_event(data["event_id"])
        config = self._get_config(event)
        window = config.get("react_timeout_seconds", 60)
        expire_time = datetime.now() + timedelta(seconds=window)

        embed = discord.Embed(
            title="🎆🎆🎆 CHÚC MỪNG NĂM MỚI! 🎆🎆🎆",
            description=(
                "**HAPPY NEW YEAR!**\n\n"
                f"React 🎆 trong vòng {window} giây để nhận thưởng!\n"
                "10 người đầu tiên nhận bonus!"
            ),
            color=0xFFD700,
        )
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        view = CountdownReactView(self, data["guild_id"], data["event_id"], message_id, expire_time)

        try:
            await data["message"].edit(embed=embed, view=view)
        except discord.NotFound:
            pass

    async def claim_reward(self, interaction: Interaction, message_id: int) -> None:
        data = self._active_countdowns.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Sự kiện đã kết thúc!", ephemeral=True)
            return

        if not data["triggered"]:
            await interaction.response.send_message("❌ Chưa đến giờ đếm ngược!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["participants"]:
            await interaction.response.send_message("❌ Bạn đã nhận thưởng rồi!", ephemeral=True)
            return

        config = self._get_config(event)
        base_reward = config.get("react_reward", 100)
        bonus = config.get("top_10_bonus", 50) if len(data["participants"]) < 10 else 0
        total_reward = base_reward + bonus

        data["participants"].append(user_id)

        await add_currency(data["guild_id"], user_id, data["event_id"], total_reward)
        await add_contribution(data["guild_id"], user_id, data["event_id"], total_reward)
        await update_community_progress(data["guild_id"], 1)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "❄️"

        position = len(data["participants"])
        bonus_text = f" (Bonus Top 10: +{bonus})" if bonus > 0 else ""
        await interaction.response.send_message(
            f"🎆 Chúc mừng năm mới! Bạn là người thứ **{position}**! +**{total_reward}** {emoji}{bonus_text}",
            ephemeral=True,
        )

    async def end_countdown(self, message_id: int) -> None:
        data = self._active_countdowns.get(message_id)
        if not data:
            return

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "❄️"

        participants_text = []
        for i, user_id in enumerate(data["participants"][:20], 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            star = "⭐" if i <= 10 else ""
            participants_text.append(f"{i}. {name} {star}")

        embed = discord.Embed(
            title="🎆 ĐẾM NGƯỢC KẾT THÚC!",
            description=f"Có **{len(data['participants'])}** người đã tham gia!",
            color=0x808080,
        )
        if participants_text:
            embed.add_field(name="🏆 Người tham gia", value="\n".join(participants_text), inline=False)

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_countdowns.pop(message_id, None)


class CountdownReactView(discord.ui.View):
    def __init__(
        self,
        minigame: CountdownMinigame,
        guild_id: int,
        event_id: str,
        message_id: int,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.message_id = message_id

    @discord.ui.button(emoji="🎆", label="Chúc Mừng Năm Mới!", style=discord.ButtonStyle.success)
    async def celebrate_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.minigame.claim_reward(interaction, self.message_id)

    async def on_timeout(self) -> None:
        await self.minigame.end_countdown(self.message_id)

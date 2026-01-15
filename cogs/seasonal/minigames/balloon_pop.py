from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("BalloonPop")


BALLOON_COLORS = ["🎈", "🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]


@register_minigame("balloon_pop")
class BalloonPopMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_balloons: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Bóng Bay Sinh Nhật"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "random",
            "times_per_day": [5, 8],
            "active_hours": [10, 22],
            "timeout_seconds": 30,
            "reward_range": [10, 30],
            "max_pops": 5,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self.spawn_config
        timeout = config.get("timeout_seconds", 30)
        max_pops = config.get("max_pops", 5)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        balloon_emoji = random.choice(BALLOON_COLORS)

        embed = discord.Embed(
            title="🎈 BÓNG BAY SINH NHẬT!",
            description=f"Bấm nhanh để bóp bóng!\n\n{balloon_emoji} {balloon_emoji} {balloon_emoji}",
            color=event.color if event else 0xFF69B4,
        )
        embed.add_field(name="👥 Còn lại", value=f"{max_pops} slot", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        view = BalloonPopView(self, guild_id, active["event_id"], expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_balloons[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "balloon_emoji": balloon_emoji,
            "poppers": [],
            "max_pops": max_pops,
            "expire_time": expire_time,
            "message": message,
        }

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def pop_balloon(self, interaction: Interaction, message_id: int) -> None:
        data = self._active_balloons.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Bóng đã bay đi!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["poppers"]:
            await interaction.response.send_message("❌ Bạn đã bóp bóng rồi!", ephemeral=True)
            return

        if len(data["poppers"]) >= data["max_pops"]:
            await interaction.response.send_message("❌ Hết bóng rồi!", ephemeral=True)
            return

        data["poppers"].append(user_id)
        position = len(data["poppers"])

        config = self.spawn_config
        reward_range = config.get("reward_range", [10, 30])
        reward = random.randint(reward_range[0], reward_range[1])

        await add_currency(data["guild_id"], user_id, data["event_id"], reward)
        await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
        await update_community_progress(data["guild_id"], 1)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🎈"

        await interaction.response.send_message(
            f"💥 POP! Bạn bóp bóng thứ **{position}**! +**{reward}** {emoji}",
            ephemeral=True,
        )

        if len(data["poppers"]) >= data["max_pops"]:
            await self._end_balloon(data)
        else:
            remaining = data["max_pops"] - len(data["poppers"])
            embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if embed:
                embed.set_field_at(0, name="👥 Còn lại", value=f"{remaining} slot", inline=True)
                try:
                    await data["message"].edit(embed=embed)
                except discord.NotFound:
                    pass

    async def _end_balloon(self, data: dict) -> None:
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🎈"

        poppers_text = []
        for i, user_id in enumerate(data["poppers"], 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            poppers_text.append(f"{i}. {name}")

        embed = discord.Embed(
            title="🎈 BÓNG ĐÃ NỔ HẾT!",
            description="Tất cả bóng đã được bóp!",
            color=0x808080,
        )
        if poppers_text:
            embed.add_field(name="💥 Người bóp", value="\n".join(poppers_text), inline=False)

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_balloons.pop(message.id, None)

    async def expire_balloon(self, message_id: int) -> None:
        data = self._active_balloons.get(message_id)
        if not data:
            return

        if len(data["poppers"]) >= data["max_pops"]:
            return

        await self._end_balloon(data)


class BalloonPopView(discord.ui.View):
    def __init__(
        self,
        minigame: BalloonPopMinigame,
        guild_id: int,
        event_id: str,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.message_id: int | None = None

    @discord.ui.button(emoji="🎈", label="Bóp Bóng!", style=discord.ButtonStyle.danger)
    async def pop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.message_id is None:
            self.message_id = interaction.message.id
        await self.minigame.pop_balloon(interaction, self.message_id)

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.expire_balloon(self.message_id)

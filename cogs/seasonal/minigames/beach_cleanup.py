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

logger = logging.getLogger("BeachCleanup")


DEFAULT_TRASH_TYPES = [
    {"emoji": "🥤", "name": "Ly nhựa", "points": 10},
    {"emoji": "📦", "name": "Hộp giấy", "points": 15},
    {"emoji": "🍾", "name": "Chai thủy tinh", "points": 20},
    {"emoji": "👟", "name": "Giày cũ", "points": 25},
    {"emoji": "🎒", "name": "Túi nylon", "points": 5},
    {"emoji": "🥡", "name": "Hộp xốp", "points": 10},
]


@register_minigame("beach_cleanup")
class BeachCleanupMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_cleanups: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Dọn Bãi Biển"

    def _get_config(self, event: Any) -> dict[str, Any]:
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("beach_cleanup", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self._get_config(event)
        timeout = config.get("timeout_seconds", 20)
        max_collectors = config.get("max_cleaners", 5)
        trash_types = config.get("trash_types", DEFAULT_TRASH_TYPES)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        trash = random.choice(trash_types)

        embed = discord.Embed(
            title="🏖️ DỌN BÃI BIỂN!",
            description=f"Có rác trên bãi biển!\n\n{trash['emoji']} **{trash['name']}**\n\nTop {max_collectors} người nhặt đầu tiên sẽ nhận thưởng!",
            color=event.color if event else 0x228B22,
        )
        embed.add_field(name="🎁 Điểm", value=f"+{trash['points']} 🌱", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        view = BeachCleanupView(self, guild_id, active["event_id"], trash, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_cleanups[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "trash": trash,
            "collectors": [],
            "max_collectors": max_collectors,
            "expire_time": expire_time,
            "message": message,
        }

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def collect_trash(self, interaction: Interaction, message_id: int) -> None:
        data = self._active_cleanups.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Rác đã được dọn hết!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["collectors"]:
            await interaction.response.send_message("❌ Bạn đã nhặt rồi!", ephemeral=True)
            return

        if len(data["collectors"]) >= data["max_collectors"]:
            await interaction.response.send_message("❌ Đã đủ người nhặt!", ephemeral=True)
            return

        data["collectors"].append(user_id)
        position = len(data["collectors"])

        trash = data["trash"]
        reward = trash["points"]

        await add_currency(data["guild_id"], user_id, data["event_id"], reward)
        await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
        await update_community_progress(data["guild_id"], 1)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌱"

        await interaction.response.send_message(
            f"🧹 Bạn nhặt được **{trash['name']}**! (#{position}) +**{reward}** {emoji}",
            ephemeral=True,
        )

        if len(data["collectors"]) >= data["max_collectors"]:
            await self._end_cleanup(data)

    async def _end_cleanup(self, data: dict) -> None:
        message = data["message"]
        trash = data["trash"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🌱"

        collectors_text = []
        for i, user_id in enumerate(data["collectors"], 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            collectors_text.append(f"{i}. {name}")

        embed = discord.Embed(
            title=f"🏖️ ĐÃ DỌN SẠCH! - {trash['name']}",
            description=f"Cảm ơn các bạn đã giúp dọn bãi biển!",
            color=0x808080,
        )
        if collectors_text:
            embed.add_field(name="🧹 Người dọn", value="\n".join(collectors_text), inline=False)

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_cleanups.pop(message.id, None)

    async def expire_cleanup(self, message_id: int) -> None:
        data = self._active_cleanups.get(message_id)
        if not data:
            return

        if len(data["collectors"]) >= data["max_collectors"]:
            return

        await self._end_cleanup(data)


class BeachCleanupView(discord.ui.View):
    def __init__(
        self,
        minigame: BeachCleanupMinigame,
        guild_id: int,
        event_id: str,
        trash: dict,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.trash = trash
        self.message_id: int | None = None

    @discord.ui.button(emoji="🧹", label="Nhặt Rác!", style=discord.ButtonStyle.success)
    async def collect_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.message_id is None:
            self.message_id = interaction.message.id
        await self.minigame.collect_trash(interaction, self.message_id)

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.expire_cleanup(self.message_id)

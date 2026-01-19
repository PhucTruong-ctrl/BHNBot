from __future__ import annotations

from core.logging import get_logger
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = get_logger("seasonal_minigames_leaf_collec")


LEAF_TYPES = [
    {"emoji": "🍁", "name": "Lá Phong", "reward": 15},
    {"emoji": "🍂", "name": "Lá Vàng", "reward": 10},
    {"emoji": "🍃", "name": "Lá Xanh", "reward": 5},
    {"emoji": "🌿", "name": "Lá Thường", "reward": 5},
]


@register_minigame("leaf_collect")
class LeafCollectMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_grids: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Nhặt Lá Thu"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "random",
            "times_per_day": [4, 6],
            "active_hours": [8, 20],
            "timeout_seconds": 45,
            "leaves_count": [3, 5],
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self.spawn_config
        timeout = config.get("timeout_seconds", 45)
        leaves_range = config.get("leaves_count", [3, 5])
        expire_time = datetime.now() + timedelta(seconds=timeout)

        num_leaves = random.randint(leaves_range[0], leaves_range[1])
        leaf_positions = random.sample(range(9), num_leaves)
        leaves = {pos: random.choice(LEAF_TYPES) for pos in leaf_positions}

        embed = self._create_grid_embed(event, num_leaves, 0, expire_time)
        view = LeafGridView(self, guild_id, active["event_id"], leaves, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_grids[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "leaves": leaves,
            "collected": {},
            "expire_time": expire_time,
            "message": message,
        }

    def _create_grid_embed(
        self, event: Any, total_leaves: int, collected_count: int, expire_time: datetime
    ) -> discord.Embed:
        remaining = total_leaves - collected_count

        embed = discord.Embed(
            title="🍂 NHẶT LÁ THU!",
            description=f"Có **{total_leaves}** chiếc lá đang rơi! Chọn ô để nhặt!",
            color=event.color if event else 0xD2691E,
        )
        embed.add_field(name="🍁 Còn lại", value=f"{remaining}/{total_leaves} lá", inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        return embed

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def collect_leaf(self, interaction: Interaction, message_id: int, position: int) -> None:
        data = self._active_grids.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Đã hết thời gian nhặt lá!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian nhặt lá!", ephemeral=True)
            return

        user_id = interaction.user.id

        if position in data["collected"]:
            await interaction.response.send_message("❌ Lá này đã được nhặt rồi!", ephemeral=True)
            return

        if position not in data["leaves"]:
            await interaction.response.send_message("🍂 Chỉ có gió thổi... Không có lá ở đây!", ephemeral=True)
            return

        leaf = data["leaves"][position]
        data["collected"][position] = user_id

        await add_currency(data["guild_id"], user_id, data["event_id"], leaf["reward"])
        await add_contribution(data["guild_id"], user_id, data["event_id"], leaf["reward"])
        await update_community_progress(data["guild_id"], 1)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍂"

        await interaction.response.send_message(
            f"{leaf['emoji']} Bạn nhặt được **{leaf['name']}**! +**{leaf['reward']}** {emoji}",
            ephemeral=True,
        )

        if len(data["collected"]) >= len(data["leaves"]):
            await self._end_collection(data)
        else:
            embed = self._create_grid_embed(
                event, len(data["leaves"]), len(data["collected"]), data["expire_time"]
            )
            try:
                await data["message"].edit(embed=embed)
            except discord.NotFound:
                pass

    async def _end_collection(self, data: dict) -> None:
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍂"

        collectors = {}
        for pos, user_id in data["collected"].items():
            leaf = data["leaves"][pos]
            if user_id not in collectors:
                collectors[user_id] = {"leaves": 0, "reward": 0}
            collectors[user_id]["leaves"] += 1
            collectors[user_id]["reward"] += leaf["reward"]

        collectors_text = []
        for user_id, stats in list(collectors.items())[:10]:
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            collectors_text.append(f"🍁 {name}: {stats['leaves']} lá (+{stats['reward']} {emoji})")

        embed = discord.Embed(
            title="🍂 ĐÃ NHẶT HẾT LÁ!",
            description="Tất cả lá đã được nhặt!",
            color=0x808080,
        )
        if collectors_text:
            embed.add_field(name="👥 Người nhặt", value="\n".join(collectors_text), inline=False)

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_grids.pop(message.id, None)

    async def expire_collection(self, message_id: int) -> None:
        data = self._active_grids.get(message_id)
        if not data:
            return

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍂"

        collected_count = len(data["collected"])
        total_leaves = len(data["leaves"])

        embed = discord.Embed(
            title="🍂 HẾT GIỜ - LÁ BAY ĐI!",
            description=f"Đã nhặt được {collected_count}/{total_leaves} lá trước khi gió cuốn đi!",
            color=0x808080,
        )

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_grids.pop(message_id, None)


class LeafGridView(discord.ui.View):
    EMPTY_EMOJI = "🍃"

    def __init__(
        self,
        minigame: LeafCollectMinigame,
        guild_id: int,
        event_id: str,
        leaves: dict[int, dict],
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.leaves = leaves
        self.message_id: int | None = None

        for i in range(9):
            button = discord.ui.Button(
                emoji="🍃",
                style=discord.ButtonStyle.secondary,
                custom_id=f"leaf_{i}",
                row=i // 3,
            )
            button.callback = self._make_callback(i)
            self.add_item(button)

    def _make_callback(self, position: int):
        async def callback(interaction: discord.Interaction) -> None:
            if self.message_id is None:
                self.message_id = interaction.message.id
            await self.minigame.collect_leaf(interaction, self.message_id, position)

        return callback

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.expire_collection(self.message_id)

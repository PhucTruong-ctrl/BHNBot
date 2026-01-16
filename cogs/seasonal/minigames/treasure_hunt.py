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

logger = logging.getLogger("TreasureHunt")


@register_minigame("treasure_hunt")
class TreasureHuntMinigame(BaseMinigame):
    """Săn Kho Báu - 3x3 grid treasure hunt minigame for Summer event.
    
    Rules:
    - 3x3 grid with 1 hidden treasure
    - Each user can only dig 1 spot
    - Correct guess: +50-100 currency + 1 contribution
    - Wrong guess: "Chỉ có cát!" (no penalty)
    - Timeout: 60 seconds
    """

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_hunts: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Săn Kho Báu"

    def _get_config(self, event: Any) -> dict[str, Any]:
        """Get minigame config from event with fallbacks."""
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("treasure_hunt", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self._get_config(event)
        timeout = config.get("timeout_seconds", 60)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        grid_size = config.get("grid_size", 9)
        treasure_pos = random.randint(0, grid_size - 1)

        embed = self._create_hunt_embed(event, expire_time, 0, None)
        view = TreasureGridView(self, guild_id, active["event_id"], treasure_pos, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_hunts[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "treasure_pos": treasure_pos,
            "diggers": {},
            "expire_time": expire_time,
            "message": message,
            "found_by": None,
            "channel": channel,
        }

    def _create_hunt_embed(
        self, event: Any, expire_time: datetime, dig_count: int, found_by: str | None
    ) -> discord.Embed:
        if found_by:
            embed = discord.Embed(
                title="🏴‍☠️ KHO BÁU ĐÃ ĐƯỢC TÌM THẤY!",
                description=f"**{found_by}** đã tìm thấy kho báu!",
                color=0xFFD700,
            )
        else:
            embed = discord.Embed(
                title="🏴‍☠️ SĂN KHO BÁU!",
                description=(
                    "Một kho báu đang ẩn náu trên bãi biển!\n"
                    "Chọn một ô để đào - mỗi người chỉ được đào **1 lần**!"
                ),
                color=event.color if event else 0x00CED1,
            )
            embed.add_field(name="👥 Đã đào", value=str(dig_count), inline=True)
            embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)
            embed.set_footer(text="🏖️ Tìm kho báu để nhận 🐚 Vỏ Sò!")

        return embed

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def dig(self, interaction: Interaction, message_id: int, position: int) -> None:
        data = self._active_hunts.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Cuộc săn này đã kết thúc!", ephemeral=True)
            return

        if data["found_by"]:
            await interaction.response.send_message("❌ Kho báu đã được tìm thấy!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian săn kho báu!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["diggers"]:
            await interaction.response.send_message("❌ Bạn đã đào rồi! Mỗi người chỉ được đào 1 lần.", ephemeral=True)
            return

        data["diggers"][user_id] = position
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🐚"

        if position == data["treasure_pos"]:
            config = self._get_config(event)
            reward_range = config.get("reward_range", [50, 100])
            contribution = config.get("community_contribution", 1)
            reward = random.randint(reward_range[0], reward_range[1])

            await add_currency(data["guild_id"], user_id, data["event_id"], reward)
            await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
            await update_community_progress(data["guild_id"], contribution)

            data["found_by"] = interaction.user.display_name

            await interaction.response.send_message(
                f"🎉 **TRÚNG RỒI!** Bạn tìm thấy kho báu! +**{reward}** {emoji}",
                ephemeral=True,
            )

            await self._end_hunt(data)
        else:
            await interaction.response.send_message("🏖️ Chỉ có cát! Không có gì ở đây...", ephemeral=True)

            embed = self._create_hunt_embed(event, data["expire_time"], len(data["diggers"]), None)
            try:
                await data["message"].edit(embed=embed)
            except discord.NotFound:
                pass

    async def _end_hunt(self, data: dict) -> None:
        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🐚"

        embed = self._create_hunt_embed(event, data["expire_time"], len(data["diggers"]), data["found_by"])

        diggers_text = []
        for user_id, pos in list(data["diggers"].items())[:10]:
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            result = "🎯" if pos == data["treasure_pos"] else "❌"
            diggers_text.append(f"{result} {name}")

        if diggers_text:
            embed.add_field(name="🔍 Người đào", value="\n".join(diggers_text), inline=False)

        if data["found_by"]:
            embed.add_field(
                name="💰 Phần thưởng",
                value=f"+50-100 {emoji} + 1 điểm cộng đồng",
                inline=False,
            )

        view = TreasureResultView(data["treasure_pos"])

        try:
            await message.edit(embed=embed, view=view)
        except discord.NotFound:
            pass

        self._active_hunts.pop(message.id, None)

    async def expire_hunt(self, message_id: int) -> None:
        data = self._active_hunts.get(message_id)
        if not data:
            return

        if data["found_by"]:
            return

        message = data["message"]
        event = self.event_manager.get_event(data["event_id"])

        embed = discord.Embed(
            title="🏴‍☠️ HẾT GIỜ - KHO BÁU BIẾN MẤT!",
            description="Không ai tìm thấy kho báu... Nó đã bị sóng cuốn đi!",
            color=0x808080,
        )

        if data["diggers"]:
            diggers_text = []
            for user_id, pos in list(data["diggers"].items())[:10]:
                user = self.bot.get_user(user_id)
                name = user.display_name if user else f"User {user_id}"
                diggers_text.append(f"❌ {name}")
            embed.add_field(name="🔍 Người đã đào", value="\n".join(diggers_text), inline=False)

        view = TreasureResultView(data["treasure_pos"])

        try:
            await message.edit(embed=embed, view=view)
        except discord.NotFound:
            pass

        self._active_hunts.pop(message_id, None)


class TreasureGridView(discord.ui.View):
    GRID_EMOJIS = ["🏖️"] * 9

    def __init__(
        self,
        minigame: TreasureHuntMinigame,
        guild_id: int,
        event_id: str,
        treasure_pos: int,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.treasure_pos = treasure_pos
        self.message_id: int | None = None

        for i in range(9):
            button = discord.ui.Button(
                emoji="🏖️",
                style=discord.ButtonStyle.secondary,
                custom_id=f"dig_{i}",
                row=i // 3,
            )
            button.callback = self._make_callback(i)
            self.add_item(button)

    def _make_callback(self, position: int):
        async def callback(interaction: discord.Interaction) -> None:
            if self.message_id is None:
                self.message_id = interaction.message.id
            await self.minigame.dig(interaction, self.message_id, position)

        return callback

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.expire_hunt(self.message_id)


class TreasureResultView(discord.ui.View):
    def __init__(self, treasure_pos: int) -> None:
        super().__init__(timeout=None)

        for i in range(9):
            if i == treasure_pos:
                emoji = "💎"
                style = discord.ButtonStyle.success
            else:
                emoji = "🏖️"
                style = discord.ButtonStyle.secondary

            button = discord.ui.Button(
                emoji=emoji,
                style=style,
                custom_id=f"result_{i}",
                row=i // 3,
                disabled=True,
            )
            self.add_item(button)

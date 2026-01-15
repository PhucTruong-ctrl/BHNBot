from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress
from ..services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("GhostHunt")


GHOST_TYPES = [
    {"emoji": "👻", "name": "Ma Trắng", "reward_range": [20, 30], "rarity": "common"},
    {"emoji": "🎃", "name": "Bí Ngô Ma", "reward_range": [25, 40], "rarity": "common"},
    {"emoji": "💀", "name": "Đầu Lâu", "reward_range": [30, 50], "rarity": "uncommon"},
    {"emoji": "🧛", "name": "Ma Cà Rồng", "reward_range": [40, 60], "rarity": "rare"},
    {"emoji": "🧟", "name": "Xác Sống", "reward_range": [35, 55], "rarity": "uncommon"},
    {"emoji": "👹", "name": "Quỷ Đỏ", "reward_range": [50, 80], "rarity": "rare"},
    {"emoji": "🦇", "name": "Dơi Ma", "reward_range": [15, 25], "rarity": "common"},
    {"emoji": "🕷️", "name": "Nhện Độc", "reward_range": [20, 35], "rarity": "common"},
]


@register_minigame("ghost_hunt")
class GhostHuntMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_ghosts: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Săn Ma"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "random",
            "times_per_day": [5, 8],
            "active_hours": [18, 23],
            "max_catches": 3,
            "timeout_seconds": 45,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self.spawn_config
        max_catches = config.get("max_catches", 3)
        timeout = config.get("timeout_seconds", 45)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        ghost = random.choice(GHOST_TYPES)

        embed = self._create_ghost_embed(event, ghost, max_catches, 0, expire_time)
        view = GhostCatchView(self, guild_id, active["event_id"], ghost, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_ghosts[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "ghost": ghost,
            "catchers": [],
            "max_catches": max_catches,
            "expire_time": expire_time,
            "message": message,
        }

    def _create_ghost_embed(
        self, event: Any, ghost: dict, max_catches: int, caught_count: int, expire_time: datetime
    ) -> discord.Embed:
        remaining = max_catches - caught_count

        embed = discord.Embed(
            title=f"{ghost['emoji']} {ghost['name'].upper()} XUẤT HIỆN!",
            description=f"Một **{ghost['name']}** đang lang thang! Nhanh tay bắt lấy!",
            color=event.color if event else 0xFF6600,
        )
        embed.add_field(name="🎁 Phần thưởng", value=f"{ghost['reward_range'][0]}-{ghost['reward_range'][1]} 🍬", inline=True)
        embed.add_field(name="👥 Còn lại", value=f"{remaining}/{max_catches} slot", inline=True)
        embed.add_field(name="⏰ Biến mất", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        return embed

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def catch_ghost(self, interaction: Interaction, message_id: int) -> None:
        data = self._active_ghosts.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Con ma này đã biến mất!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Con ma đã biến mất!", ephemeral=True)
            return

        user_id = interaction.user.id

        user_catches = await self._get_user_daily_catches(data["guild_id"], user_id, data["event_id"])
        daily_limit = 10
        if user_catches >= daily_limit:
            await interaction.response.send_message(
                f"❌ Bạn đã bắt đủ {daily_limit} con ma hôm nay! Quay lại ngày mai nhé.",
                ephemeral=True,
            )
            return

        if user_id in data["catchers"]:
            await interaction.response.send_message("❌ Bạn đã bắt con ma này rồi!", ephemeral=True)
            return

        if len(data["catchers"]) >= data["max_catches"]:
            await interaction.response.send_message("❌ Con ma đã bị bắt hết!", ephemeral=True)
            return

        data["catchers"].append(user_id)

        ghost = data["ghost"]
        reward = random.randint(ghost["reward_range"][0], ghost["reward_range"][1])

        await add_currency(data["guild_id"], user_id, data["event_id"], reward)
        await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
        await update_community_progress(data["guild_id"], 1)
        await self._record_catch(data["guild_id"], user_id, data["event_id"])

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍬"

        await interaction.response.send_message(
            f"👻 Bạn bắt được **{ghost['name']}**! +**{reward}** {emoji}",
            ephemeral=True,
        )

        if len(data["catchers"]) >= data["max_catches"]:
            await self._end_ghost(data)
        else:
            embed = self._create_ghost_embed(
                event, ghost, data["max_catches"], len(data["catchers"]), data["expire_time"]
            )
            try:
                await data["message"].edit(embed=embed)
            except discord.NotFound:
                pass

    async def _get_user_daily_catches(self, guild_id: int, user_id: int, event_id: str) -> int:
        today = datetime.now().date().isoformat()
        rows = await execute_query(
            """
            SELECT catch_count FROM ghost_hunt_daily
            WHERE guild_id = ? AND user_id = ? AND event_id = ? AND date = ?
            """,
            (guild_id, user_id, event_id, today),
        )
        return rows[0]["catch_count"] if rows else 0

    async def _record_catch(self, guild_id: int, user_id: int, event_id: str) -> None:
        today = datetime.now().date().isoformat()
        await execute_write(
            """
            INSERT INTO ghost_hunt_daily (guild_id, user_id, event_id, date, catch_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT (guild_id, user_id, event_id, date) DO UPDATE SET
                catch_count = ghost_hunt_daily.catch_count + 1
            """,
            (guild_id, user_id, event_id, today),
        )

    async def _end_ghost(self, data: dict) -> None:
        message = data["message"]
        ghost = data["ghost"]
        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍬"

        catchers_text = []
        for user_id in data["catchers"]:
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            catchers_text.append(f"✅ {name}")

        embed = discord.Embed(
            title=f"{ghost['emoji']} {ghost['name'].upper()} ĐÃ BỊ BẮT!",
            description="Con ma đã bị bắt hết!",
            color=0x808080,
        )
        if catchers_text:
            embed.add_field(name="🏆 Người bắt", value="\n".join(catchers_text), inline=False)
        embed.add_field(name="💰 Phần thưởng", value=f"{ghost['reward_range'][0]}-{ghost['reward_range'][1]} {emoji}", inline=True)

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_ghosts.pop(message.id, None)

    async def expire_ghost(self, message_id: int) -> None:
        data = self._active_ghosts.get(message_id)
        if not data:
            return

        ghost = data["ghost"]
        event = self.event_manager.get_event(data["event_id"])

        catchers_text = []
        for user_id in data["catchers"]:
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            catchers_text.append(f"✅ {name}")

        embed = discord.Embed(
            title=f"{ghost['emoji']} {ghost['name'].upper()} ĐÃ BIẾN MẤT!",
            description="Con ma đã biến mất vào bóng tối...",
            color=0x808080,
        )
        if catchers_text:
            embed.add_field(name="🏆 Người đã bắt", value="\n".join(catchers_text), inline=False)

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_ghosts.pop(message_id, None)


class GhostCatchView(discord.ui.View):
    def __init__(
        self,
        minigame: GhostHuntMinigame,
        guild_id: int,
        event_id: str,
        ghost: dict,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.ghost = ghost
        self.message_id: int | None = None

    @discord.ui.button(label="👻 Bắt Ma!", style=discord.ButtonStyle.danger)
    async def catch_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.message_id is None:
            self.message_id = interaction.message.id
        await self.minigame.catch_ghost(interaction, self.message_id)

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.expire_ghost(self.message_id)

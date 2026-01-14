from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager


INGREDIENTS = [
    {"emoji": "🍵", "name": "Lá Trà", "category": "base"},
    {"emoji": "🌿", "name": "Bạc Hà", "category": "base"},
    {"emoji": "🌸", "name": "Hoa Cúc", "category": "base"},
    {"emoji": "🍯", "name": "Mật Ong", "category": "sweetener"},
    {"emoji": "🍬", "name": "Đường", "category": "sweetener"},
    {"emoji": "🍋", "name": "Chanh", "category": "flavor"},
    {"emoji": "🍊", "name": "Cam", "category": "flavor"},
    {"emoji": "🫚", "name": "Gừng", "category": "flavor"},
    {"emoji": "🌰", "name": "Quế", "category": "spice"},
]

SPECIAL_COMBOS = {
    ("🍵", "🍯", "🫚"): {"name": "Trà Gừng Mật Ong", "bonus": 50},
    ("🌿", "🍯", "🍋"): {"name": "Trà Bạc Hà Chanh", "bonus": 40},
    ("🌸", "🍬", "🍊"): {"name": "Trà Cúc Cam", "bonus": 35},
    ("🍵", "🌰", "🍯"): {"name": "Trà Quế Mật Ong", "bonus": 45},
}


@register_minigame("tea_brewing")
class TeaBrewingMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_sessions: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Pha Trà Thu"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "random",
            "times_per_day": [3, 5],
            "active_hours": [14, 21],
            "timeout_seconds": 60,
            "base_reward": 20,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self.spawn_config
        timeout = config.get("timeout_seconds", 60)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        available = random.sample(INGREDIENTS, 6)

        embed = self._create_brewing_embed(event, expire_time, 0)
        view = TeaBrewingView(self, guild_id, active["event_id"], available, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_sessions[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "available": available,
            "brewers": {},
            "expire_time": expire_time,
            "message": message,
        }

    def _create_brewing_embed(self, event: Any, expire_time: datetime, brewer_count: int) -> discord.Embed:
        embed = discord.Embed(
            title="🍵 PHA TRÀ THU!",
            description="Chọn **3 nguyên liệu** để pha trà!\nKết hợp đặc biệt sẽ nhận thưởng bonus!",
            color=event.color if event else 0xD2691E,
        )
        embed.add_field(name="👥 Người pha", value=str(brewer_count), inline=True)
        embed.add_field(name="⏰ Hết hạn", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        combos_text = []
        for combo, info in SPECIAL_COMBOS.items():
            combos_text.append(f"{''.join(combo)} → **{info['name']}** (+{info['bonus']})")
        embed.add_field(name="✨ Công thức đặc biệt", value="\n".join(combos_text), inline=False)

        return embed

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def brew_tea(
        self, interaction: Interaction, message_id: int, selected: list[str]
    ) -> None:
        data = self._active_sessions.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Phiên pha trà đã kết thúc!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian pha trà!", ephemeral=True)
            return

        user_id = interaction.user.id

        if user_id in data["brewers"]:
            await interaction.response.send_message("❌ Bạn đã pha trà rồi!", ephemeral=True)
            return

        if len(selected) != 3:
            await interaction.response.send_message("❌ Phải chọn đúng 3 nguyên liệu!", ephemeral=True)
            return

        config = self.spawn_config
        base_reward = config.get("base_reward", 20)
        total_reward = base_reward

        combo_key = tuple(sorted(selected))
        combo_name = None
        for combo, info in SPECIAL_COMBOS.items():
            if set(combo) == set(selected):
                total_reward += info["bonus"]
                combo_name = info["name"]
                break

        data["brewers"][user_id] = {
            "ingredients": selected,
            "reward": total_reward,
            "combo": combo_name,
        }

        await add_currency(data["guild_id"], user_id, data["event_id"], total_reward)
        await add_contribution(data["guild_id"], user_id, data["event_id"], total_reward)
        await update_community_progress(data["guild_id"], 1)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍂"

        if combo_name:
            msg = f"🍵 Tuyệt vời! Bạn pha được **{combo_name}**! +**{total_reward}** {emoji}"
        else:
            msg = f"🍵 Bạn pha được trà thơm ngon! +**{total_reward}** {emoji}"

        await interaction.response.send_message(msg, ephemeral=True)

        embed = self._create_brewing_embed(event, data["expire_time"], len(data["brewers"]))
        try:
            await data["message"].edit(embed=embed)
        except discord.NotFound:
            pass

    async def expire_session(self, message_id: int) -> None:
        data = self._active_sessions.get(message_id)
        if not data:
            return

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🍂"

        brewers_text = []
        for user_id, info in list(data["brewers"].items())[:10]:
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            combo = f" ({info['combo']})" if info.get("combo") else ""
            brewers_text.append(f"🍵 {name}: +{info['reward']} {emoji}{combo}")

        embed = discord.Embed(
            title="🍵 PHIÊN PHA TRÀ KẾT THÚC!",
            description=f"Có {len(data['brewers'])} người đã pha trà!",
            color=0x808080,
        )
        if brewers_text:
            embed.add_field(name="👥 Người pha", value="\n".join(brewers_text), inline=False)

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_sessions.pop(message_id, None)


class TeaBrewingView(discord.ui.View):
    def __init__(
        self,
        minigame: TeaBrewingMinigame,
        guild_id: int,
        event_id: str,
        available: list[dict],
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.available = available
        self.message_id: int | None = None
        self.selected: dict[int, list[str]] = {}

        for i, ingredient in enumerate(available):
            button = discord.ui.Button(
                emoji=ingredient["emoji"],
                label=ingredient["name"],
                style=discord.ButtonStyle.secondary,
                custom_id=f"ing_{i}",
                row=i // 3,
            )
            button.callback = self._make_ingredient_callback(ingredient["emoji"])
            self.add_item(button)

        brew_button = discord.ui.Button(
            label="🍵 Pha Trà!",
            style=discord.ButtonStyle.success,
            custom_id="brew",
            row=2,
        )
        brew_button.callback = self._brew_callback
        self.add_item(brew_button)

    def _make_ingredient_callback(self, emoji: str):
        async def callback(interaction: discord.Interaction) -> None:
            user_id = interaction.user.id
            if user_id not in self.selected:
                self.selected[user_id] = []

            if emoji in self.selected[user_id]:
                self.selected[user_id].remove(emoji)
                await interaction.response.send_message(
                    f"❌ Đã bỏ {emoji}. Đã chọn: {''.join(self.selected[user_id]) or 'Chưa có'}",
                    ephemeral=True,
                )
            elif len(self.selected[user_id]) >= 3:
                await interaction.response.send_message(
                    f"❌ Đã chọn đủ 3 nguyên liệu! Bấm '🍵 Pha Trà!' để hoàn thành.",
                    ephemeral=True,
                )
            else:
                self.selected[user_id].append(emoji)
                await interaction.response.send_message(
                    f"✅ Đã chọn {emoji}. Đã chọn: {''.join(self.selected[user_id])} ({len(self.selected[user_id])}/3)",
                    ephemeral=True,
                )

        return callback

    async def _brew_callback(self, interaction: discord.Interaction) -> None:
        if self.message_id is None:
            self.message_id = interaction.message.id

        user_id = interaction.user.id
        selected = self.selected.get(user_id, [])

        if len(selected) != 3:
            await interaction.response.send_message(
                f"❌ Phải chọn đúng 3 nguyên liệu! Bạn mới chọn {len(selected)}/3.",
                ephemeral=True,
            )
            return

        await self.minigame.brew_tea(interaction, self.message_id, selected)

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.expire_session(self.message_id)

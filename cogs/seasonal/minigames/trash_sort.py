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

logger = logging.getLogger("TrashSort")


DEFAULT_TRASH_ITEMS = [
    {"emoji": "📦", "name": "Hộp giấy", "category": "recycle", "description": "Giấy carton"},
    {"emoji": "🍾", "name": "Chai nhựa", "category": "recycle", "description": "Nhựa tái chế"},
    {"emoji": "🥫", "name": "Lon thiếc", "category": "recycle", "description": "Kim loại"},
    {"emoji": "🍌", "name": "Vỏ chuối", "category": "organic", "description": "Rác hữu cơ"},
    {"emoji": "🥬", "name": "Rau héo", "category": "organic", "description": "Thực phẩm thừa"},
    {"emoji": "🍂", "name": "Lá khô", "category": "organic", "description": "Rác vườn"},
    {"emoji": "🔋", "name": "Pin cũ", "category": "hazardous", "description": "Chất thải nguy hại"},
    {"emoji": "💊", "name": "Thuốc hết hạn", "category": "hazardous", "description": "Dược phẩm"},
    {"emoji": "🎨", "name": "Hộp sơn", "category": "hazardous", "description": "Hóa chất"},
]

DEFAULT_CATEGORY_INFO = {
    "recycle": {"emoji": "🟢", "name": "Tái Chế", "color": 0x00FF00},
    "organic": {"emoji": "🟡", "name": "Hữu Cơ", "color": 0xFFFF00},
    "hazardous": {"emoji": "🔴", "name": "Nguy Hại", "color": 0xFF0000},
}


@register_minigame("trash_sort")
class TrashSortMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_quizzes: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Phân Loại Rác"

    def _get_config(self, event: Any) -> dict[str, Any]:
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("trash_sort", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self._get_config(event)
        timeout = config.get("timeout_seconds", 30)
        trash_items = config.get("trash_items", DEFAULT_TRASH_ITEMS)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        trash_item = random.choice(trash_items)

        embed = discord.Embed(
            title="🗑️ PHÂN LOẠI RÁC!",
            description=f"Rác này thuộc loại nào?\n\n{trash_item['emoji']} **{trash_item['name']}**\n_{trash_item['description']}_",
            color=event.color if event else 0x228B22,
        )
        embed.add_field(name="⏰ Thời gian", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)
        embed.set_footer(text="Chọn đúng loại thùng rác!")

        view = TrashSortView(self, guild_id, active["event_id"], trash_item, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_quizzes[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "trash_item": trash_item,
            "correct_category": trash_item["category"],
            "answers": {},
            "expire_time": expire_time,
            "message": message,
        }

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def submit_answer(self, interaction: Interaction, message_id: int, category: str) -> None:
        data = self._active_quizzes.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Câu hỏi đã kết thúc!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["answers"]:
            await interaction.response.send_message("❌ Bạn đã trả lời rồi!", ephemeral=True)
            return

        is_correct = category == data["correct_category"]
        data["answers"][user_id] = {"category": category, "correct": is_correct}

        event = self.event_manager.get_event(data["event_id"])
        config = self._get_config(event)
        category_info = config.get("category_info", DEFAULT_CATEGORY_INFO)
        cat_info = category_info[data["correct_category"]]
        emoji = event.currency_emoji if event else "🌱"

        if is_correct:
            reward = config.get("reward_per_correct", 20)
            await add_currency(data["guild_id"], user_id, data["event_id"], reward)
            await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
            await update_community_progress(data["guild_id"], 1)
            await interaction.response.send_message(
                f"✅ Chính xác! Đây là rác **{cat_info['name']}**! +**{reward}** {emoji}",
                ephemeral=True,
            )
        else:
            penalty = config.get("penalty_wrong", -5)
            await add_currency(data["guild_id"], user_id, data["event_id"], penalty)
            selected_cat = category_info[category]
            await interaction.response.send_message(
                f"❌ Sai rồi! Đây là rác **{cat_info['name']}**, không phải {selected_cat['name']}. {penalty} {emoji}",
                ephemeral=True,
            )

    async def end_quiz(self, message_id: int) -> None:
        data = self._active_quizzes.get(message_id)
        if not data:
            return

        trash = data["trash_item"]
        event = self.event_manager.get_event(data["event_id"])
        config = self._get_config(event)
        category_info = config.get("category_info", DEFAULT_CATEGORY_INFO)
        cat_info = category_info[data["correct_category"]]

        correct_users = [uid for uid, ans in data["answers"].items() if ans["correct"]]
        wrong_users = [uid for uid, ans in data["answers"].items() if not ans["correct"]]

        embed = discord.Embed(
            title=f"🗑️ KẾT QUẢ - {trash['name']}",
            description=f"Đáp án đúng: {cat_info['emoji']} **{cat_info['name']}**",
            color=cat_info["color"],
        )
        embed.add_field(name="✅ Đúng", value=str(len(correct_users)), inline=True)
        embed.add_field(name="❌ Sai", value=str(len(wrong_users)), inline=True)

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_quizzes.pop(message_id, None)


class TrashSortView(discord.ui.View):
    def __init__(
        self,
        minigame: TrashSortMinigame,
        guild_id: int,
        event_id: str,
        trash_item: dict,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.trash_item = trash_item
        self.message_id: int | None = None

        for cat_id, cat_data in DEFAULT_CATEGORY_INFO.items():
            button = discord.ui.Button(
                emoji=cat_data["emoji"],
                label=cat_data["name"],
                style=discord.ButtonStyle.secondary,
                custom_id=f"cat_{cat_id}",
            )
            button.callback = self._make_callback(cat_id)
            self.add_item(button)

    def _make_callback(self, category: str):
        async def callback(interaction: discord.Interaction) -> None:
            if self.message_id is None:
                self.message_id = interaction.message.id
            await self.minigame.submit_answer(interaction, self.message_id, category)

        return callback

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.end_quiz(self.message_id)

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from ..core.event_types import EventConfig


class EventInfoView(discord.ui.View):
    def __init__(self, event: EventConfig, user_id: int) -> None:
        super().__init__(timeout=300)
        self.event = event
        self.user_id = user_id
        self.current_page = "info"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📊 Thông tin", style=discord.ButtonStyle.primary, custom_id="event_info")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = "info"
        await interaction.response.defer()

    @discord.ui.button(label="🎯 Mục tiêu", style=discord.ButtonStyle.secondary, custom_id="event_goal")
    async def goal_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = "goal"
        await interaction.response.defer()

    @discord.ui.button(label="🏆 Xếp hạng", style=discord.ButtonStyle.secondary, custom_id="event_leaderboard")
    async def leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = "leaderboard"
        await interaction.response.defer()

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, 'disabled'):
                child.disabled = True
        self.stop()


class QuestView(discord.ui.View):
    def __init__(
        self,
        event: EventConfig,
        user_id: int,
        quests: dict[str, list[dict]],
        claim_callback: Any,
    ) -> None:
        super().__init__(timeout=300)
        self.event = event
        self.user_id = user_id
        self.quests = quests
        self.claim_callback = claim_callback
        self.current_tab = "daily"
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.clear_items()

        daily_style = discord.ButtonStyle.primary if self.current_tab == "daily" else discord.ButtonStyle.secondary
        fixed_style = discord.ButtonStyle.primary if self.current_tab == "fixed" else discord.ButtonStyle.secondary

        self.add_item(TabButton("📅 Hàng ngày", daily_style, "daily", self))
        self.add_item(TabButton("🏆 Thành tựu", fixed_style, "fixed", self))

        current_quests = self.quests.get(self.current_tab, [])
        for quest in current_quests:
            if quest.get("completed") and not quest.get("claimed"):
                self.add_item(ClaimButton(quest, self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, 'disabled'):
                child.disabled = True
        self.stop()

    def create_embed(self) -> discord.Embed:
        current_quests = self.quests.get(self.current_tab, [])
        tab_name = "NHIỆM VỤ HÀNG NGÀY" if self.current_tab == "daily" else "THÀNH TỰU"

        embed = discord.Embed(
            title=f"📋 {tab_name} - {self.event.name}",
            color=self.event.color,
        )

        if not current_quests:
            embed.description = "Không có nhiệm vụ nào!"
            return embed

        lines = []
        for quest in current_quests:
            data = quest.get("quest_data", {})
            name = data.get("name", "Nhiệm vụ")
            progress = quest.get("progress", 0)
            target = quest.get("target", 1)
            completed = quest.get("completed", False)
            claimed = quest.get("claimed", False)

            if claimed:
                status = "✅"
            elif completed:
                status = "🎁"
            else:
                status = "⏳"

            reward = data.get("reward_value") or data.get("reward", 0)
            lines.append(
                f"{status} **{name}**\n"
                f"   └ {progress}/{target} | Thưởng: {reward} {self.event.currency_emoji}"
            )

        embed.description = "\n".join(lines)
        return embed


class TabButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, tab: str, view: QuestView) -> None:
        super().__init__(label=label, style=style)
        self.tab = tab
        self.quest_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.quest_view.current_tab = self.tab
        self.quest_view._update_buttons()
        embed = self.quest_view.create_embed()
        await interaction.response.edit_message(embed=embed, view=self.quest_view)


class ClaimButton(discord.ui.Button):
    def __init__(self, quest: dict, view: QuestView) -> None:
        quest_data = quest.get("quest_data", {})
        label = f"Nhận: {quest_data.get('name', 'Nhiệm vụ')[:20]}"
        super().__init__(label=label, style=discord.ButtonStyle.success, row=2)
        self.quest = quest
        self.quest_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        quest_id = self.quest.get("quest_id")
        if quest_id and self.quest_view.claim_callback:
            result = await self.quest_view.claim_callback(interaction, quest_id)
            if result:
                self.quest["claimed"] = True
                self.quest_view._update_buttons()
                embed = self.quest_view.create_embed()
                await interaction.response.edit_message(embed=embed, view=self.quest_view)
                return

        await interaction.response.send_message("❌ Không thể nhận thưởng!", ephemeral=True)


class ShopView(discord.ui.View):
    def __init__(
        self,
        event: EventConfig,
        user_id: int,
        user_currency: int,
        shop_items: list[dict],
        purchase_callback: Any,
    ) -> None:
        super().__init__(timeout=300)
        self.event = event
        self.user_id = user_id
        self.user_currency = user_currency
        self.shop_items = shop_items
        self.purchase_callback = purchase_callback
        self.current_page = 0
        self.items_per_page = 5
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.clear_items()

        total_pages = (len(self.shop_items) + self.items_per_page - 1) // self.items_per_page

        if self.current_page > 0:
            self.add_item(NavButton("◀️ Trước", "prev", self))
        if self.current_page < total_pages - 1:
            self.add_item(NavButton("Sau ▶️", "next", self))

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.shop_items[start:end]

        for i, item in enumerate(page_items):
            can_afford = self.user_currency >= item.get("price", 0)
            self.add_item(PurchaseButton(item, i, can_afford, self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, 'disabled'):
                child.disabled = True
        self.stop()

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🛒 CỬA HÀNG SỰ KIỆN - {self.event.name}",
            color=self.event.color,
        )

        embed.add_field(
            name="💰 Số dư",
            value=f"{self.user_currency} {self.event.currency_emoji}",
            inline=False,
        )

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.shop_items[start:end]

        if not page_items:
            embed.description = "Cửa hàng trống!"
            return embed

        lines = []
        for item in page_items:
            name = item.get("name", "Vật phẩm")
            price = item.get("price", 0)
            desc = item.get("description", "")
            emoji = item.get("emoji", "📦")

            can_afford = "✅" if self.user_currency >= price else "❌"
            lines.append(f"{emoji} **{name}** - {price} {self.event.currency_emoji} {can_afford}\n   └ {desc}")

        embed.add_field(name="📦 Vật phẩm", value="\n".join(lines), inline=False)

        total_pages = (len(self.shop_items) + self.items_per_page - 1) // self.items_per_page
        embed.set_footer(text=f"Trang {self.current_page + 1}/{total_pages}")

        return embed


class NavButton(discord.ui.Button):
    def __init__(self, label: str, direction: str, view: ShopView) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.direction = direction
        self.shop_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.direction == "prev":
            self.shop_view.current_page = max(0, self.shop_view.current_page - 1)
        else:
            total_pages = (len(self.shop_view.shop_items) + self.shop_view.items_per_page - 1) // self.shop_view.items_per_page
            self.shop_view.current_page = min(total_pages - 1, self.shop_view.current_page + 1)

        self.shop_view._update_buttons()
        embed = self.shop_view.create_embed()
        await interaction.response.edit_message(embed=embed, view=self.shop_view)


class PurchaseButton(discord.ui.Button):
    def __init__(self, item: dict, index: int, can_afford: bool, view: ShopView) -> None:
        label = f"Mua: {item.get('name', 'Vật phẩm')[:15]}"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success if can_afford else discord.ButtonStyle.secondary,
            disabled=not can_afford,
            row=2 + (index // 3),
        )
        self.item = item
        self.shop_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.shop_view.purchase_callback:
            result = await self.shop_view.purchase_callback(interaction, self.item)
            if result:
                self.shop_view.user_currency -= self.item.get("price", 0)
                self.shop_view._update_buttons()
                embed = self.shop_view.create_embed()
                await interaction.response.edit_message(embed=embed, view=self.shop_view)
                return

        await interaction.response.send_message("❌ Không thể mua!", ephemeral=True)


class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=60)
        self.user_id = user_id
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Xác nhận", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = False
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, 'disabled'):
                child.disabled = True
        self.stop()

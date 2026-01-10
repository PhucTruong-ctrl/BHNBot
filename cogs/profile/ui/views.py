from typing import TYPE_CHECKING

import discord
from discord import ui

from ..core.themes import THEMES, get_theme, get_available_themes

if TYPE_CHECKING:
    from ..cog import ProfileCog


class ThemeSelectView(ui.View):
    def __init__(self, user_id: int, vip_tier: int, cog: "ProfileCog"):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.vip_tier = vip_tier
        self.cog = cog
        self._add_select()

    def _add_select(self) -> None:
        options = []
        for theme in THEMES.values():
            is_locked = theme.vip_tier > self.vip_tier
            vip_label = f" (VIP {theme.vip_tier})" if theme.vip_tier > 0 else ""
            lock_label = " 🔒" if is_locked else ""

            options.append(discord.SelectOption(
                label=f"{theme.name}{vip_label}{lock_label}",
                value=theme.key,
                emoji=theme.emoji,
            ))

        select = ui.Select(
            placeholder="🎨 Chọn theme...",
            options=options,
            custom_id="theme_select",
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Đây không phải menu của bạn!", ephemeral=True
            )
            return

        selected_key = interaction.data["values"][0]  # type: ignore
        theme = get_theme(selected_key)

        if theme.vip_tier > self.vip_tier:
            await interaction.response.send_message(
                f"❌ Theme **{theme.name}** yêu cầu VIP {theme.vip_tier}!",
                ephemeral=True
            )
            return

        await self.cog.set_user_theme(interaction, selected_key)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, ui.Select):
                item.disabled = True


class ThemePreviewView(ui.View):
    def __init__(self, user_id: int, theme_key: str, cog: "ProfileCog"):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.theme_key = theme_key
        self.cog = cog

    @ui.button(label="✅ Áp dụng", style=discord.ButtonStyle.success)
    async def apply(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Đây không phải menu của bạn!", ephemeral=True
            )
            return
        await self.cog.confirm_theme(interaction, self.theme_key)

    @ui.button(label="❌ Hủy", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Đây không phải menu của bạn!", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content="Đã hủy thay đổi theme.", embed=None, view=None
        )

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True

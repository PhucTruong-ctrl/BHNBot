import discord
from discord.ext import commands
from typing import List, Any, Optional

class SimpleConfirmView(discord.ui.View):
    """A simple View with Confirm/Cancel buttons."""
    
    def __init__(self, user_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không phải là người thực hiện lệnh này.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Xác nhận", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Hủy", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

class PaginationView(discord.ui.View):
    """A simple pagination view for navigating lists."""
    
    def __init__(self, pages: List[Any], user_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.user_id = user_id
        self.current_page = 0
        self.total_pages = len(pages)
        self.update_buttons()

    def update_buttons(self):
        self.first_page_btn.disabled = (self.current_page == 0)
        self.prev_page_btn.disabled = (self.current_page == 0)
        self.next_page_btn.disabled = (self.current_page == self.total_pages - 1)
        self.last_page_btn.disabled = (self.current_page == self.total_pages - 1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không thể điều khiển menu này.", ephemeral=True)
            return False
        return True

    async def get_page_content(self, page_idx: int):
        """Override this method to return dict(content=..., embed=...)"""
        page = self.pages[page_idx]
        if isinstance(page, discord.Embed):
            return {"embed": page}
        elif isinstance(page, str):
            return {"content": page}
        return page # Assume dict

    async def update_message(self, interaction: discord.Interaction):
        self.update_buttons()
        kwargs = await self.get_page_content(self.current_page)
        await interaction.response.edit_message(**kwargs, view=self)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update_message(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_message(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        await self.update_message(interaction)

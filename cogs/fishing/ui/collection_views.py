"""Collection view for fishing."""

import discord
from discord import ui

from ..constants import COMMON_FISH, RARE_FISH, LEGENDARY_FISH_KEYS, ALL_FISH
from core.logger import setup_logger

logger = setup_logger("CollectionViews", "cogs/fishing/fishing.log")


class FishingCollectionView(ui.View):
    
    def __init__(self, user_id, username, user_collection, stats):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.username = username
        self.user_collection = user_collection
        self.stats = stats
        self.current_page = 0
        self.pages = ["🐟 CÁ THƯỜNG", "✨ CÁ HIẾM", "👑 HUYỀN THOẠI"]
        
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.pages) - 1)

    async def get_current_embed(self):
        if self.current_page == 0:
            category_name = "🐟 CÁ THƯỜNG"
            fish_list = [f['key'] for f in COMMON_FISH]
            found = self.stats['found_common']
            total = self.stats['total_common']
            color = discord.Color.blue()
        elif self.current_page == 1:
            category_name = "✨ CÁ HIẾM"
            fish_list = [f['key'] for f in RARE_FISH]
            found = self.stats['found_rare']
            total = self.stats['total_rare']
            color = discord.Color.purple()
        else:
            category_name = "👑 HUYỀN THOẠI"
            fish_list = LEGENDARY_FISH_KEYS
            found = self.stats['found_legend']
            total = self.stats['total_legend']
            color = discord.Color.gold()
            
        progress_bar = self.create_progress_bar(found, total)
        percent = (found / total * 100) if total > 0 else 0
        
        embed = discord.Embed(
            title=f"📚 Bộ Sưu Tập Cá Của {self.username}",
            description=f"**{category_name}**\n{progress_bar} **{found}/{total}** ({percent:.1f}%)",
            color=color
        )
        
        all_lines = []
        for k in fish_list:
            fish_data = ALL_FISH.get(k, {})
            emoji = fish_data.get('emoji', '🐟')
            name = fish_data.get('name', k)
            
            is_caught = self.user_collection.get(k, 0) > 0
            
            if is_caught:
                all_lines.append(f"✅ {emoji} **{name}**")
            else:
                all_lines.append(f"⬛ ❓❓❓")
        
        if not all_lines:
            embed.add_field(name="Danh Sách", value="*Chưa có dữ liệu cá loại này*", inline=False)
        else:
            mid = (len(all_lines) + 1) // 2
            col1_lines = all_lines[:mid]
            col2_lines = all_lines[mid:]
            
            def create_field_text(lines):
                chunks = []
                current_chunk = ""
                for line in lines:
                    if len(current_chunk) + len(line) + 1 > 1000:
                        chunks.append(current_chunk)
                        current_chunk = line + "\n"
                    else:
                        current_chunk += line + "\n"
                if current_chunk:
                    chunks.append(current_chunk)
                return chunks

            col1_chunks = create_field_text(col1_lines)
            col2_chunks = create_field_text(col2_lines)
            
            max_chunks = max(len(col1_chunks), len(col2_chunks))
            for i in range(max_chunks):
                val1 = col1_chunks[i] if i < len(col1_chunks) else "\u200b"
                embed.add_field(name="Danh Sách" if i == 0 else "\u200b", value=val1, inline=True)
                
                val2 = col2_chunks[i] if i < len(col2_chunks) else "\u200b"
                embed.add_field(name="Danh Sách" if i == 0 else "\u200b", value=val2, inline=True)

        return embed

    def create_progress_bar(self, current, total, length=10):
        if total == 0: 
            return "⬜" * length
        filled = int((current / total) * length)
        return "🟦" * filled + "⬜" * (length - filled)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ Bạn không phải chủ sở hữu của bộ sưu tập này!", ephemeral=True)
            return False
        return True

    @ui.button(label="< Trước", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Sau >", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self.update_buttons()
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

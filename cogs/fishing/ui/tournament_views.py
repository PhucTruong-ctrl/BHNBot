"""Tournament lobby view."""

import discord
from core.database import db_manager


class TournamentLobbyView(discord.ui.View):
    
    def __init__(self, tournament_id: int, host_id: int):
        super().__init__(timeout=900)
        self.tournament_id = tournament_id
        self.host_id = host_id
        
    async def update_embed(self, interaction: discord.Interaction):
        from ..tournament import TournamentManager
        
        count_data = await db_manager.fetchrow(
            "SELECT COUNT(*) as c FROM tournament_entries WHERE tournament_id = $1",
            self.tournament_id
        )
        count = count_data['c'] if count_data else 0
        
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.set_footer(text=f"ID: {self.tournament_id} | Người tham gia: {count}")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Tham Gia", style=discord.ButtonStyle.green, emoji="🎟️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from ..tournament import TournamentManager
        manager = TournamentManager.get_instance()
        success, msg = await manager.join_tournament(self.tournament_id, interaction.user.id)
        
        if success:
            await self.update_embed(interaction)
            await interaction.followup.send(f"✅ {interaction.user.mention} đã tham gia!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

    @discord.ui.button(label="Rời Giải", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Đã tham gia thì không thể rút lui (Hạt đã đóng vào Quỹ)!", ephemeral=True)

    @discord.ui.button(label="Bắt Đầu", style=discord.ButtonStyle.blurple, emoji="⚔️")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("❌ Chỉ Host mới được quyền bắt đầu!", ephemeral=True)
            return
            
        from ..tournament import TournamentManager
        manager = TournamentManager.get_instance()
        success = await manager.start_tournament(self.tournament_id)
        
        if success:
            embed = discord.Embed(
                title="⚔️ GIẢI ĐẤU ĐÃ BẮT ĐẦU!",
                description="Các cần thủ hãy nhanh chóng câu cá!\nThời gian: **10 phút**.\nTính điểm: **Tổng giá trị cá bán được**.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("❌ Cần ít nhất 2 người chơi!", ephemeral=True)

    @discord.ui.button(label="Cập Nhật", style=discord.ButtonStyle.gray, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction)

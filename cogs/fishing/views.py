"""UI views for fishing system."""

import discord
from database_manager import remove_item, add_seeds, get_inventory
from .constants import ALL_FISH

class FishSellView(discord.ui.View):
    """View for selling caught fish."""
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
    
    @discord.ui.button(label="💰 Bán Cá Vừa Câu", style=discord.ButtonStyle.green)
    async def sell_caught_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            total_money = 0
            for fish_key, quantity in self.caught_items.items():
                fish_info = ALL_FISH.get(fish_key)
                if fish_info:
                    base_price = fish_info['sell_price']
                    total_money += base_price * quantity
            
            for fish_key, quantity in self.caught_items.items():
                await remove_item(self.user_id, fish_key, quantity)
            
            await add_seeds(self.user_id, total_money)
            
            if self.user_id in self.cog.caught_items:
                del self.cog.caught_items[self.user_id]
            
            fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
            embed = discord.Embed(
                title=f"**{interaction.user.name}** đã bán {sum(self.caught_items.values())} con cá",
                description=f"\n{fish_summary}\n**Nhận: {total_money} Hạt**",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            fish_count = sum(self.caught_items.values())
            print(f"[FISHING] [SELL] {interaction.user.name} (user_id={self.user_id}) seed_change=+{total_money} fish_count={fish_count} fish_types={len(self.caught_items)}")
        
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

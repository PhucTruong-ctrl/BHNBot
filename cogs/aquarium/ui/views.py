
import discord
from discord import ui
from ..core.shop import aquarium_shop
from ..constants import DECOR_ITEMS

class DecorShopView(ui.View):
    """View for browsing and buying Decor Items."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        
        # Add Select Menu for Categories? Or just buttons for items?
        # For simplicity (MVP), let's use a Select Menu to choose item to buy
        self.add_item(DecorSelect(user_id))

class DecorSelect(ui.Select):
    """Dropdown to select a decor item to view details/buy."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        
        options = []
        for key, item in DECOR_ITEMS.items():
            options.append(discord.SelectOption(
                label=item['name'],
                value=key,
                description=f"{item['price_seeds']:,} S + {item['price_leaf']} 🍃 | {item['desc'][:50]}",
                emoji=item['icon']
            ))
            
        super().__init__(
            placeholder="🛍️ Chọn vật phẩm để xem chi tiết & mua...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Menu này không dành cho bạn!", ephemeral=True)
            
        item_key = self.values[0]
        item = DECOR_ITEMS[item_key]
        
        # Create confirmation embed
        embed = discord.Embed(
            title=f"{item['icon']} {item['name']}",
            description=f"**Mô tả:** {item['desc']}\n\n"
                        f"💰 **Giá:** {item['price_seeds']:,} Seeds\n"
                        f"🍃 **Xu Lá:** {item['price_leaf']}\n\n"
                        f"Vị trí đặt: `{item['type']}`",
            color=0x2ecc71
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/123/store.png") # Placeholder
        
        # Update view with Buy Button for this specific item
        view = DecorConfirmView(self.user_id, item_key)
        await interaction.response.edit_message(embed=embed, view=view)

class DecorConfirmView(ui.View):
    """View to confirm purchase."""
    
    def __init__(self, user_id: int, item_key: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_key = item_key
    
    @ui.button(label="Mua Ngay", style=discord.ButtonStyle.green, emoji="🛒")
    async def buy_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return
            
        await interaction.response.defer()
        
        # Call Shop Logic
        success, msg = await aquarium_shop.buy_decor(self.user_id, self.item_key)
        
        if success:
             # Disable buttons
            for child in self.children:
                child.disabled = True
            
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="Trạng thái", value=msg)
            
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
        else:
            await interaction.followup.send(msg, ephemeral=True)

    @ui.button(label="Quay lại", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return
            
        # Return to main shop View
        embed = discord.Embed(title="🏪 Cửa Hàng Nội Thất", description="Chào mừng! Bạn muốn mua gì hôm nay?", color=0xe67e22)
        view = DecorShopView(self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)

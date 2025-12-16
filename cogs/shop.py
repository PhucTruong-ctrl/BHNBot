import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database_manager import (
    get_user_balance,
    add_seeds,
    get_inventory,
    add_item,
    remove_item
)

DB_PATH = "./data/database.db"

# Shop Items Definition
SHOP_ITEMS = {
    "cafe": {"name": "Cà phê", "cost": 50, "emoji": "☕"},
    "flower": {"name": "Hoa", "cost": 75, "emoji": "🌹"},
    "ring": {"name": "Nhẫn", "cost": 150, "emoji": "💍"},
    "gift": {"name": "Quà", "cost": 100, "emoji": "🎁"},
    "chocolate": {"name": "Sô cô la", "cost": 60, "emoji": "🍫"},
    "card": {"name": "Thiệp", "cost": 40, "emoji": "💌"},
}

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_seeds(self, user_id: int) -> int:
        """Get user's current seeds"""
        return await get_user_balance(user_id)

    async def reduce_seeds(self, user_id: int, amount: int):
        """Reduce user's seeds"""
        await add_seeds(user_id, -amount)

    async def add_item_local(self, user_id: int, item_name: str, quantity: int = 1):
        """Add item to user's inventory"""
        await add_item(user_id, item_name, quantity)

    async def remove_item(self, user_id: int, item_name: str, quantity: int = 1) -> bool:
        """Remove item from user's inventory. Return True if successful"""
        return await remove_item(user_id, item_name, quantity)

    async def get_inventory(self, user_id: int) -> dict:
        """Get user's inventory"""
        return await get_inventory(user_id)

    # ==================== COMMANDS ====================

    @app_commands.command(name="shop", description="Xem cửa hàng quà tặng")
    async def shop(self, interaction: discord.Interaction):
        """Display shop menu"""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="Cửa Hàng Quà Tặng",
            color=discord.Color.purple()
        )
        
        shop_text = ""
        for item_key, item_info in SHOP_ITEMS.items():
            shop_text += f"{item_info['emoji']} **{item_info['name']}** - {item_info['cost']} hạt\n"
        
        embed.description = shop_text
        embed.add_field(
            name="💡 Cách mua",
            value=f"Dùng: `/buy [item_name]`\n\nVí dụ: `/buy cafe`, `/buy flower`, `/buy ring`",
            inline=False
        )
        embed.set_footer(text="Dùng /tangqua để tặng quà cho người khác")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="buy", description="Mua quà")
    @app_commands.describe(item="Tên item (cafe, flower, ring, gift, chocolate, card)")
    async def buy(self, interaction: discord.Interaction, item: str):
        """Buy item from shop"""
        await interaction.response.defer(ephemeral=True)
        
        item = item.lower()
        
        # Check if item exists
        if item not in SHOP_ITEMS:
            available = ", ".join(SHOP_ITEMS.keys())
            await interaction.followup.send(
                f"❌ Item không tồn tại!\nCác item có sẵn: {available}",
                ephemeral=True
            )
            return
        
        item_info = SHOP_ITEMS[item]
        cost = item_info['cost']
        user_id = interaction.user.id
        
        # Check balance
        seeds = await self.get_seeds(user_id)
        if seeds < cost:
            await interaction.followup.send(
                f"❌ Bạn không đủ hạt!\n"
                f"Cần: {cost} hạt | Hiện có: {seeds} hạt",
                ephemeral=True
            )
            return
        
        # Process purchase
        await self.reduce_seeds(user_id, cost)
        await self.add_item_local(user_id, item, 1)
        
        embed = discord.Embed(
            title="✅ Mua thành công!",
            description=f"Bạn vừa mua **{item_info['name']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Trừ", value=f"{cost} hạt", inline=True)
        embed.add_field(name="💾 Còn lại", value=f"{seeds - cost} hạt", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        print(f"[SHOP] {interaction.user.name} bought {item}")

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

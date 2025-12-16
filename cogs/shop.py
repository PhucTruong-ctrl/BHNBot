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
    "worm": {"name": "Giun (Mồi Câu)", "cost": 10, "emoji": "🪱"},  # Money sink for fishing
}

# Reverse mapping: Vietnamese name -> item key
VIETNAMESE_TO_ITEM_KEY = {item_info['name']: key for key, item_info in SHOP_ITEMS.items()}

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_seeds(self, user_id: int) -> int:
        """Get user's current seeds"""
        return await get_user_balance(user_id)

    async def reduce_seeds(self, user_id: int, amount: int):
        """Reduce user's seeds"""
        balance_before = await get_user_balance(user_id)
        await add_seeds(user_id, -amount)
        balance_after = balance_before - amount
        print(
            f"[SHOP] [SEED_UPDATE] user_id={user_id} seed_change=-{amount} "
            f"balance_before={balance_before} balance_after={balance_after}"
        )

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
            value=f"Dùng: `/buy [tên item tiếng Việt]`\n\nVí dụ: `/buy Cà phê`, `/buy Hoa`, `/buy Nhẫn`",
            inline=False
        )
        embed.set_footer(text="Dùng /tangqua để tặng quà cho người khác")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mua", description="Mua quà - Cà phê, Hoa, Nhẫn, Quà, Sô cô la, Thiệp, Giun")
    @app_commands.describe(
        item="Tên item tiếng Việt: Cà phê (50), Hoa (75), Nhẫn (150), Quà (100), Sô cô la (60), Thiệp (40), Giun (10)",
        soluong="Số lượng muốn mua (mặc định: 1)"
    )
    async def buy_slash(self, interaction: discord.Interaction, item: str, soluong: int = 1):
        """Buy item from shop"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate quantity
        if soluong < 1:
            await interaction.followup.send(
                f"❌ Số lượng phải >= 1!",
                ephemeral=True
            )
            return
        
        # Try to match Vietnamese name to item key
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            available = ", ".join(VIETNAMESE_TO_ITEM_KEY.keys())
            await interaction.followup.send(
                f"❌ Item không tồn tại!\nCác item có sẵn: {available}",
                ephemeral=True
            )
            return
        
        item_info = SHOP_ITEMS[item_key]
        cost_per_item = item_info['cost']
        total_cost = cost_per_item * soluong
        user_id = interaction.user.id
        
        # Check balance
        seeds = await self.get_seeds(user_id)
        if seeds < total_cost:
            await interaction.followup.send(
                f"❌ Bạn không đủ hạt!\n"
                f"Cần: {total_cost} hạt | Hiện có: {seeds} hạt",
                ephemeral=True
            )
            return
        
        # Process purchase
        await self.reduce_seeds(user_id, total_cost)
        await self.add_item_local(user_id, item_key, soluong)
        
        quantity_text = f" x{soluong}" if soluong > 1 else ""
        embed = discord.Embed(
            title="✅ Mua thành công!",
            description=f"Bạn vừa mua **{item}{quantity_text}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
        embed.add_field(name="💾 Còn lại", value=f"{seeds - total_cost} hạt", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        new_balance = seeds - total_cost
        print(
            f"[SHOP] [PURCHASE] user_id={user_id} username={interaction.user.name} "
            f"item_key={item_key} quantity={soluong} seed_change=-{total_cost} balance_after={new_balance}"
        )

    @commands.command(name="mua", description="Mua quà - ☕ Cà phê (50), 🌹 Hoa (75), 💍 Nhẫn (150), 🎁 Quà (100), 🍫 Sô cô la (60), 💌 Thiệp (40), 🪱 Giun (10)")
    async def buy_prefix(self, ctx, soluong: int = 1, *, item: str):
        """Buy item from shop via prefix - Usage: !mua [quantity] [item_name]"""
        # Validate quantity
        if soluong < 1:
            await ctx.send(f"❌ Số lượng phải >= 1!")
            return
        
        # Try to match Vietnamese name to item key
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            available = ", ".join(VIETNAMESE_TO_ITEM_KEY.keys())
            await ctx.send(f"❌ Item không tồn tại!\nCác item có sẵn: {available}")
            return
        
        item_info = SHOP_ITEMS[item_key]
        cost_per_item = item_info['cost']
        total_cost = cost_per_item * soluong
        user_id = ctx.author.id
        
        # Check balance
        seeds = await self.get_seeds(user_id)
        if seeds < total_cost:
            await ctx.send(f"❌ Bạn không đủ hạt!\nCần: {total_cost} hạt | Hiện có: {seeds} hạt")
            return
        
        # Process purchase
        await self.reduce_seeds(user_id, total_cost)
        await self.add_item_local(user_id, item_key, soluong)
        
        quantity_text = f" x{soluong}" if soluong > 1 else ""
        embed = discord.Embed(
            title="✅ Mua thành công!",
            description=f"Bạn vừa mua **{item}{quantity_text}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
        embed.add_field(name="💾 Còn lại", value=f"{seeds - total_cost} hạt", inline=True)
        
        await ctx.send(embed=embed)
        new_balance = seeds - total_cost
        print(
            f"[SHOP] [PURCHASE] user_id={user_id} username={ctx.author.name} "
            f"item_key={item_key} quantity={soluong} seed_change=-{total_cost} balance_after={new_balance}"
        )

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

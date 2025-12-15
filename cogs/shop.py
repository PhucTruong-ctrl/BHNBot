import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite

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
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT seeds FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            return row[0] if row else 0

    async def reduce_seeds(self, user_id: int, amount: int):
        """Reduce user's seeds"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE economy_users SET seeds = seeds - ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def add_item(self, user_id: int, item_name: str, quantity: int = 1):
        """Add item to user's inventory"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Check if item exists
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                # Update quantity
                await db.execute(
                    "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?",
                    (quantity, user_id, item_name)
                )
            else:
                # Insert new item
                await db.execute(
                    "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
                    (user_id, item_name, quantity)
                )
            
            await db.commit()

    async def remove_item(self, user_id: int, item_name: str, quantity: int = 1) -> bool:
        """Remove item from user's inventory. Return True if successful"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Check current quantity
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row or row[0] < quantity:
                return False
            
            # Update quantity
            new_quantity = row[0] - quantity
            if new_quantity <= 0:
                await db.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
                    (user_id, item_name)
                )
            else:
                await db.execute(
                    "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?",
                    (new_quantity, user_id, item_name)
                )
            
            await db.commit()
            return True

    async def get_inventory(self, user_id: int) -> dict:
        """Get user's inventory"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT item_name, quantity FROM inventory WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            inventory = {}
            for item_name, quantity in rows:
                inventory[item_name] = quantity
            return inventory

    # ==================== COMMANDS ====================

    @app_commands.command(name="shop", description="Xem cửa hàng quà tặng")
    async def shop(self, interaction: discord.Interaction):
        """Display shop menu"""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🎁 Cửa Hàng Quà Tặng",
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
        await self.add_item(user_id, item, 1)
        
        embed = discord.Embed(
            title="✅ Mua thành công!",
            description=f"Bạn vừa mua **{item_info['name']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Trừ", value=f"{cost} hạt", inline=True)
        embed.add_field(name="💾 Còn lại", value=f"{seeds - cost} hạt", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        print(f"[SHOP] {interaction.user.name} bought {item}")

    @app_commands.command(name="inventory", description="Xem túi đồ của bạn")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    async def inventory(self, interaction: discord.Interaction, user: discord.User = None):
        """Check inventory"""
        await interaction.response.defer(ephemeral=True)
        
        target_user = user or interaction.user
        inventory = await self.get_inventory(target_user.id)
        
        embed = discord.Embed(
            title=f"🎒 Túi đồ của {target_user.name}",
            color=discord.Color.blue()
        )
        
        if not inventory:
            embed.description = "Túi đồ trống rỗng 😢"
        else:
            inv_text = ""
            for item_key, quantity in inventory.items():
                if item_key in SHOP_ITEMS:
                    emoji = SHOP_ITEMS[item_key]['emoji']
                    name = SHOP_ITEMS[item_key]['name']
                    inv_text += f"{emoji} **{name}** x{quantity}\n"
            
            embed.description = inv_text if inv_text else "Túi đồ trống rỗng 😢"
        
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

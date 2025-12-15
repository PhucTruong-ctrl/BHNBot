import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime

DB_PATH = "./data/database.db"

# Shop Items (imported from shop.py)
SHOP_ITEMS = {
    "cafe": {"name": "☕ Cà phê", "cost": 50, "emoji": "☕"},
    "flower": {"name": "🌹 Hoa", "cost": 75, "emoji": "🌹"},
    "ring": {"name": "💍 Nhẫn", "cost": 150, "emoji": "💍"},
    "gift": {"name": "🎁 Quà", "cost": 100, "emoji": "🎁"},
    "chocolate": {"name": "🍫 Sô cô la", "cost": 60, "emoji": "🍫"},
    "card": {"name": "💌 Thiệp", "cost": 40, "emoji": "💌"},
}

class InteractionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_affinity(self, user_id_1: int, user_id_2: int) -> int:
        """Get affinity between two users (normalized to user_id_1 < user_id_2)"""
        if user_id_1 > user_id_2:
            user_id_1, user_id_2 = user_id_2, user_id_1
        
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
                (user_id_1, user_id_2)
            ) as cursor:
                row = await cursor.fetchone()
            return row[0] if row else 0

    async def add_affinity(self, user_id_1: int, user_id_2: int, amount: int):
        """Add affinity between two users"""
        if user_id_1 > user_id_2:
            user_id_1, user_id_2 = user_id_2, user_id_1
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Check if relationship exists
            async with db.execute(
                "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
                (user_id_1, user_id_2)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                await db.execute(
                    "UPDATE relationships SET affinity = affinity + ?, last_interaction = CURRENT_TIMESTAMP WHERE user_id_1 = ? AND user_id_2 = ?",
                    (amount, user_id_1, user_id_2)
                )
            else:
                await db.execute(
                    "INSERT INTO relationships (user_id_1, user_id_2, affinity) VALUES (?, ?, ?)",
                    (user_id_1, user_id_2, amount)
                )
            
            await db.commit()

    async def remove_item(self, user_id: int, item_name: str, quantity: int = 1) -> bool:
        """Remove item from user's inventory"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row or row[0] < quantity:
                return False
            
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

    async def add_item(self, user_id: int, item_name: str, quantity: int = 1):
        """Add item to user's inventory"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                await db.execute(
                    "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?",
                    (quantity, user_id, item_name)
                )
            else:
                await db.execute(
                    "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
                    (user_id, item_name, quantity)
                )
            
            await db.commit()

    async def get_top_affinity_friends(self, user_id: int, limit: int = 3) -> list:
        """Get top affinity friends for a user"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Query as user_id_1
            async with db.execute(
                """SELECT user_id_2 as friend_id, affinity FROM relationships 
                   WHERE user_id_1 = ? ORDER BY affinity DESC LIMIT ?""",
                (user_id, limit)
            ) as cursor:
                rows1 = await cursor.fetchall()
            
            # Query as user_id_2
            async with db.execute(
                """SELECT user_id_1 as friend_id, affinity FROM relationships 
                   WHERE user_id_2 = ? ORDER BY affinity DESC LIMIT ?""",
                (user_id, limit)
            ) as cursor:
                rows2 = await cursor.fetchall()
            
            # Combine and sort
            all_rows = rows1 + rows2
            all_rows.sort(key=lambda x: x[1], reverse=True)
            
            return all_rows[:limit]

    # ==================== COMMANDS ====================

    @app_commands.command(name="tangqua", description="Tặng quà cho ai đó")
    @app_commands.describe(
        user="Người nhận quà",
        item="Item tặng (cafe, flower, ring, gift, chocolate, card)"
    )
    async def gift_item(self, interaction: discord.Interaction, user: discord.User, item: str):
        """Gift an item to another user"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate target is not self
        if user.id == interaction.user.id:
            await interaction.followup.send("❌ Bạn không thể tặng quà cho chính mình!", ephemeral=True)
            return
        
        # Validate target is not bot
        if user.bot:
            await interaction.followup.send("❌ Bạn không thể tặng quà cho bot!", ephemeral=True)
            return
        
        item = item.lower()
        
        # Check if item exists
        if item not in SHOP_ITEMS:
            available = ", ".join(SHOP_ITEMS.keys())
            await interaction.followup.send(
                f"❌ Item không tồn tại!\nCác item có sẵn: {available}",
                ephemeral=True
            )
            return
        
        # Check if sender has item
        success = await self.remove_item(interaction.user.id, item, 1)
        if not success:
            await interaction.followup.send(
                f"❌ Bạn không có **{SHOP_ITEMS[item]['name']}** để tặng!",
                ephemeral=True
            )
            return
        
        # Give item to recipient
        await self.add_item(user.id, item, 1)
        
        # Add affinity (10 points per gift)
        await self.add_affinity(interaction.user.id, user.id, 10)
        
        embed = discord.Embed(
            title="💝 Tặng quà thành công!",
            color=discord.Color.pink()
        )
        embed.add_field(name="Tặng", value=f"**{interaction.user.mention}** tặng", inline=True)
        embed.add_field(name="Nhận", value=f"**{user.mention}**", inline=True)
        embed.add_field(name="Quà", value=f"{SHOP_ITEMS[item]['emoji']} {SHOP_ITEMS[item]['name']}", inline=False)
        embed.add_field(name="💕 Thân thiết", value=f"+10 (cả hai cộng)", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        print(f"[GIFT] {interaction.user.name} gifted {item} to {user.name}")

    @app_commands.command(name="affinity", description="Xem mức độ thân thiết với ai")
    @app_commands.describe(user="Người muốn check (để trống để xem người thân nhất)")
    async def check_affinity(self, interaction: discord.Interaction, user: discord.User = None):
        """Check affinity with another user"""
        await interaction.response.defer(ephemeral=True)
        
        if user and user.id == interaction.user.id:
            await interaction.followup.send("❌ Bạn không thể check thân thiết với chính mình!", ephemeral=True)
            return
        
        if user:
            # Check affinity with specific user
            affinity = await self.get_affinity(interaction.user.id, user.id)
            
            embed = discord.Embed(
                title="💕 Mức độ Thân thiết",
                color=discord.Color.pink()
            )
            embed.add_field(name="Giữa", value=f"{interaction.user.mention} ❤️ {user.mention}", inline=False)
            embed.add_field(name="Điểm", value=f"**{affinity}**", inline=False)
            
            if affinity >= 100:
                embed.set_footer(text="💑 Bạn bè tốt nhất!")
            elif affinity >= 50:
                embed.set_footer(text="🤝 Bạn tốt!")
            elif affinity >= 10:
                embed.set_footer(text="👋 Quen biết nhau")
            else:
                embed.set_footer(text="👤 Chưa thân")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Show top affinity friends
            top_friends = await self.get_top_affinity_friends(interaction.user.id, 5)
            
            embed = discord.Embed(
                title="💕 Top người thân nhất của bạn",
                color=discord.Color.pink()
            )
            
            if not top_friends:
                embed.description = "Bạn chưa có ai thân cả 😢"
            else:
                friends_text = ""
                for idx, (friend_id, affinity) in enumerate(top_friends, 1):
                    try:
                        friend = await self.bot.fetch_user(friend_id)
                        medals = ["🥇", "🥈", "🥉"]
                        medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                        friends_text += f"{medal} **{friend.name}** - {affinity} điểm\n"
                    except:
                        pass
                
                embed.description = friends_text if friends_text else "Bạn chưa có ai thân cả 😢"
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ==================== EVENTS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto add affinity when users interact (reply/mention)"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # Check if message is a reply
        if message.reference:
            try:
                replied_msg = await message.channel.fetch_message(message.reference.message_id)
                if not replied_msg.author.bot and replied_msg.author.id != message.author.id:
                    # Add small affinity (2 points)
                    await self.add_affinity(message.author.id, replied_msg.author.id, 2)
                    print(f"[AFFINITY] {message.author.name} replied to {replied_msg.author.name} (+2)")
            except:
                pass
        
        # Check if message mentions someone
        for mentioned_user in message.mentions:
            if not mentioned_user.bot and mentioned_user.id != message.author.id:
                # Add small affinity (1 point)
                await self.add_affinity(message.author.id, mentioned_user.id, 1)
                print(f"[AFFINITY] {message.author.name} mentioned {mentioned_user.name} (+1)")

async def setup(bot):
    await bot.add_cog(InteractionsCog(bot))

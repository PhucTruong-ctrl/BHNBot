import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime
from database_manager import (
    get_affinity,
    add_affinity,
    remove_item,
    add_item,
    get_top_affinity_friends
)

DB_PATH = "./data/database.db"

# Shop Items (imported from shop.py)
SHOP_ITEMS = {
    "cafe": {"name": "Cà phê", "cost": 50, "emoji": "☕"},
    "flower": {"name": "Hoa", "cost": 75, "emoji": "🌹"},
    "ring": {"name": "Nhẫn", "cost": 150, "emoji": "💍"},
    "gift": {"name": "Quà", "cost": 100, "emoji": "🎁"},
    "chocolate": {"name": "Sô cô la", "cost": 60, "emoji": "🍫"},
    "card": {"name": "Thiệp", "cost": 40, "emoji": "💌"},
}

# Reverse mapping: Vietnamese name -> item key
VIETNAMESE_TO_ITEM_KEY = {item_info['name']: key for key, item_info in SHOP_ITEMS.items()}

class InteractionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_affinity_local(self, user_id_1: int, user_id_2: int) -> int:
        """Get affinity between two users"""
        return await get_affinity(user_id_1, user_id_2)

    async def add_affinity_local(self, user_id_1: int, user_id_2: int, amount: int):
        """Add affinity between two users"""
        await add_affinity(user_id_1, user_id_2, amount)

    async def remove_item(self, user_id: int, item_name: str, quantity: int = 1) -> bool:
        """Remove item from user's inventory"""
        return await remove_item(user_id, item_name, quantity)

    async def add_item_local(self, user_id: int, item_name: str, quantity: int = 1):
        """Add item to user's inventory"""
        await add_item(user_id, item_name, quantity)

    async def get_top_affinity_friends(self, user_id: int, limit: int = 3) -> list:
        """Get top affinity friends for a user"""
        return await get_top_affinity_friends(user_id, limit)

    # ==================== COMMANDS ====================

    @app_commands.command(name="tangqua", description="Tặng quà cho người chơi khác")
    @app_commands.describe(
        user="Người nhận quà",
        item="Item key: cafe, flower, ring, gift, chocolate, card"
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
        
        # Try to match Vietnamese name to item key
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            available = ", ".join(VIETNAMESE_TO_ITEM_KEY.keys())
            await interaction.followup.send(
                f"❌ Item không tồn tại!\nCác item có sẵn: {available}",
                ephemeral=True
            )
            return
        
        # Check if sender has item
        success = await self.remove_item(interaction.user.id, item_key, 1)
        if not success:
            await interaction.followup.send(
                f"❌ Bạn không có **{item}** để tặng!",
                ephemeral=True
            )
            return
        
        # Give item to recipient
        await self.add_item_local(user.id, item_key, 1)
        
        # Add affinity based on item cost (cost // 5, minimum 5 points)
        cost = SHOP_ITEMS[item_key]['cost']
        affinity_gain = max(5, cost // 5)
        await self.add_affinity_local(interaction.user.id, user.id, affinity_gain)
        
        embed = discord.Embed(
            title="💝 Tặng quà thành công!",
            color=discord.Color.pink()
        )
        embed.add_field(name="Tặng", value=f"**{interaction.user.mention}** tặng", inline=True)
        embed.add_field(name="Nhận", value=f"**{user.mention}**", inline=True)
        embed.add_field(name="Quà", value=f"{SHOP_ITEMS[item_key]['emoji']} {SHOP_ITEMS[item_key]['name']}", inline=False)
        embed.add_field(name="💕 Thân thiết", value=f"+10 (cả hai cộng)", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        
        print(
            f"[GIFT] [SEND] sender_id={interaction.user.id} sender={interaction.user.name} "
            f"receiver_id={user.id} receiver={user.name} item_key={item_key} quantity=1 "
            f"affinity_change={affinity_gain}"
        )

    @app_commands.command(name="thanthiet", description="Xem mức độ thân thiết với ai")
    @app_commands.describe(user="Người muốn check (để trống để xem người thân nhất)")
    async def check_affinity_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Check affinity with another user"""
        await interaction.response.defer(ephemeral=False)
        
        if user and user.id == interaction.user.id:
            await interaction.followup.send("❌ Bạn không thể check thân thiết với chính mình!", ephemeral=True)
            return
        
        if user:
            # Check affinity with specific user
            affinity = await self.get_affinity_local(interaction.user.id, user.id)
            
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
            
            await interaction.followup.send(embed=embed, ephemeral=False)
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
            
            await interaction.followup.send(embed=embed, ephemeral=False)

    @commands.command(name="thanthiet", description="Xem mức độ thân thiết với ai")
    async def check_affinity_prefix(self, ctx, user: discord.User = None):
        """Check affinity with another user via prefix"""
        if user and user.id == ctx.author.id:
            await ctx.send("❌ Bạn không thể check thân thiết với chính mình!")
            return
        
        if user:
            affinity = await self.get_affinity_local(ctx.author.id, user.id)
            embed = discord.Embed(
                title="💕 Mức độ Thân thiết",
                color=discord.Color.pink()
            )
            embed.add_field(name="Giữa", value=f"{ctx.author.mention} ❤️ {user.mention}", inline=False)
            embed.add_field(name="Điểm", value=f"**{affinity}**", inline=False)
            
            if affinity >= 100:
                embed.set_footer(text="💑 Bạn bè tốt nhất!")
            elif affinity >= 50:
                embed.set_footer(text="🤝 Bạn tốt!")
            elif affinity >= 10:
                embed.set_footer(text="👋 Quen biết nhau")
            else:
                embed.set_footer(text="👤 Chưa thân")
            await ctx.send(embed=embed)
        else:
            top_friends = await self.get_top_affinity_friends(ctx.author.id, 5)
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
            await ctx.send(embed=embed)

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
                    print(
                        f"[AFFINITY] [REPLY] actor_id={message.author.id} actor={message.author.name} "
                        f"target_id={replied_msg.author.id} target={replied_msg.author.name} affinity_change=+2"
                    )
            except:
                pass
        
        # Check if message mentions someone
        for mentioned_user in message.mentions:
            if not mentioned_user.bot and mentioned_user.id != message.author.id:
                # Add small affinity (1 point)
                await self.add_affinity_local(message.author.id, mentioned_user.id, 1)
                print(
                    f"[AFFINITY] [MENTION] actor_id={message.author.id} actor={message.author.name} "
                    f"target_id={mentioned_user.id} target={mentioned_user.name} affinity_change=+1"
                )

async def setup(bot):
    await bot.add_cog(InteractionsCog(bot))

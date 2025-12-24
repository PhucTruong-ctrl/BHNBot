import discord
from discord import app_commands
from discord.ext import commands
import random
from database_manager import remove_item
from cogs.shop import SHOP_ITEMS, VIETNAMESE_TO_ITEM_KEY
from .constants import GIFT_MESSAGES, COLOR_RELATIONSHIP
from core.logger import setup_logger

logger = setup_logger("RelationshipCog", "cogs/relationship.log")

class RelationshipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tangqua", description="Tặng quà healing cho người khác (Cà phê, Hoa, Quà...)")
    @app_commands.describe(
        user="Người nhận",
        item="Tên vật phẩm (cafe, hoa, nhan...)",
        message="Lời nhắn gửi kèm (Nếu để trống sẽ dùng lời nhắn ngẫu nhiên)",
        an_danh="Gửi ẩn danh (True/False)"
    )
    async def tangqua(self, interaction: discord.Interaction, user: discord.User, item: str, message: str = None, an_danh: bool = False):
        # Defer ephemerally if anonymous to hide usage
        await interaction.response.defer(ephemeral=an_danh)

        if user.id == interaction.user.id:
            return await interaction.followup.send("❌ Hãy thương lấy chính mình trước khi thương người khác nhé! (Nhưng tặng quà cho mình thì hơi kỳ)")
        
        if user.bot:
            return await interaction.followup.send("❌ Bot không biết uống cà phê đâu, cảm ơn tấm lòng nhé!")

        # Normalization & Mapping
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item.lower())
        if not item_key:
            # Try direct key match
            if item.lower() in SHOP_ITEMS:
                item_key = item.lower()
            else:
                 return await interaction.followup.send(f"❌ Không tìm thấy món quà tên '{item}'. Hãy xem lại `/shop` nhé.")
        
        # Check if item is giftable (should be in GIFT_MESSAGES)
        if item_key not in GIFT_MESSAGES and item_key != "gift": # "gift" is generic key
             # Fallback for generic items if needed, but for now stick to healing items
             pass

        # Check inventory
        success = await remove_item(interaction.user.id, item_key, 1)
        if not success:
             return await interaction.followup.send(f"❌ Bạn không có sẵn **{SHOP_ITEMS[item_key]['name']}** trong túi đồ.")

        logger.info(f"Gift: {interaction.user.id} -> {user.id}, item: {item_key}, anonymous: {an_danh}")
        
        # Construct Embed
        sender_name = "Một người giấu tên" if an_danh else interaction.user.display_name
        sender_avatar = "https://cdn.discordapp.com/embed/avatars/0.png" if an_danh else interaction.user.display_avatar.url
        
        # Select Message
        if message:
            final_msg = f'"{message}"'
        else:
            # Use random template
            msgs = GIFT_MESSAGES.get(item_key, [f"**{sender_name}** đã tặng **{user.display_name}** một món quà!"])
            msg_template = random.choice(msgs)
            final_msg = msg_template.format(sender=sender_name, receiver=user.display_name)
        
        embed = discord.Embed(
            description=f"{final_msg}", 
            color=COLOR_RELATIONSHIP
        )
        
        if not an_danh:
            embed.set_author(name=f"Quà tặng từ {sender_name}", icon_url=sender_avatar)
        else:
            embed.set_author(name="Quà tặng bí mật", icon_url=sender_avatar)

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Vật phẩm: {SHOP_ITEMS[item_key]['name']} {SHOP_ITEMS[item_key]['emoji']}")
        
        # Send to channel
        if an_danh:
            # Ephemeral confirm first
            await interaction.followup.send("✅ Đã gửi quà bí mật thành công! (Tin nhắn sẽ xuất hiện trong giây lát)", ephemeral=True)
            # Wait then send public message disconnected from interaction
            import asyncio
            await asyncio.sleep(2)
            await interaction.channel.send(content=user.mention, embed=embed)
        else:
            # Normal reply
            await interaction.followup.send(content=user.mention, embed=embed)

async def setup(bot):
    await bot.add_cog(RelationshipCog(bot))
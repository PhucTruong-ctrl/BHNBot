
import discord
from discord.ext import commands
from discord import app_commands
from core.logger import setup_logger
from .core.economy import aquarium_economy

logger = setup_logger("AquariumCog", "logs/aquarium.log")

class AquariumCog(commands.Cog):
    """
    Project Aquarium: Symbiosis Model
    - Economy (Leaf Coin, Recycle)
    - Housing (Home, Decor)
    - Interaction (Visitors)
    """

from .core.housing import housing_manager
from .ui.render import render_engine
from .ui.views import DecorShopView
from configs.settings import AQUARIUM_FORUM_CHANNEL_ID

# ... (Previous Code)

class AquariumCog(commands.Cog):
    """
    Project Aquarium: Symbiosis Model
    - Economy (Leaf Coin, Recycle)
    - Housing (Home, Decor)
    - Interaction (Visitors)
    """

    def __init__(self, bot):
        self.bot = bot
    
    # Define Groups
    nha_group = app_commands.Group(name="nha", description="Quản lý Nhà Cửa & Hồ Cá")
    decor_group = app_commands.Group(name="trangtri", description="Mua sắm & Sắp xếp Nội thất")

    # ==================== ECONOMY COMMANDS ====================
    # ... (Keep taiche command) ...

    # ==================== HOUSING COMMANDS ====================
    @nha_group.command(name="khoitao", description="Nhận đất và xây hồ cá riêng!")
    async def nha_khoitao(self, interaction: discord.Interaction):
        """Create a new home thread for the user."""
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        # 1. Logic Check: Has house?
        if await housing_manager.has_house(user_id):
            return await interaction.followup.send("❌ Bạn đã có nhà rồi! Đừng tham lam!", ephemeral=True)
        
        # 2. Get Forum Channel
        forum_channel = self.bot.get_channel(AQUARIUM_FORUM_CHANNEL_ID)
        if not forum_channel:
             return await interaction.followup.send(f"❌ Lỗi Config: Không tìm thấy kênh Làng Chài (ID: {AQUARIUM_FORUM_CHANNEL_ID}). Vui lòng báo Admin!", ephemeral=True)
        
        # 3. Create Embed
        embed = discord.Embed(
            title=f"🏠 Nhà của {interaction.user.display_name}",
            description="*Cư dân mới nhập cư*",
            color=0x3498db
        )
        
        # Default visuals
        default_visuals = render_engine.generate_view([None]*5)
        embed.add_field(name="🖼️ Bể Cá & Nội Thất", value=default_visuals, inline=False)
        embed.add_field(name="📊 Thông Tin", value="🍃 **Xu Lá:** 0\n💖 **Charm:** 0", inline=False)
        embed.set_footer(text="Chào mừng đến với Làng Chài! Gõ /trangtri cuahang để mua đồ.")
        
        # 4. Create Thread
        try:
             # Forum Thread Creation
            thread_with_message = await forum_channel.create_thread(
                name=f"Nhà của {interaction.user.display_name}",
                content=f"Chào mừng gia chủ {interaction.user.mention}!",
                embed=embed
            )
            created_thread = thread_with_message.thread
            
            # 5. Register in DB
            success = await housing_manager.register_house(user_id, created_thread.id)
            
            if success:
                await interaction.followup.send(f"✅ Đã xây nhà thành công! Ghé thăm tại đây: {created_thread.mention}")
            else:
        except Exception as e:
            logger.error(f"[HOUSE_CMD_ERROR] {e}", exc_info=True)
            await interaction.followup.send(f"❌ Lỗi khi xây nhà: {e}")

    # ==================== DECOR COMMANDS ====================
    @decor_group.command(name="cuahang", description="🏪 Ghé thăm Cửa Hàng Nội Thất Cá")
    async def decor_cuahang(self, interaction: discord.Interaction):
        """Open the Decor Shop."""
        embed = discord.Embed(
            title="🏪 Cửa Hàng Nội Thất",
            description="Chào mừng! Bạn muốn mua gì hôm nay?\n\n*Dùng **Seeds** và **Xu Lá** để mua sắm.*",
            color=0xe67e22
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/123/store.png")
        
        view = DecorShopView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AquariumCog(bot))

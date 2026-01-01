
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
from .core.economy import aquarium_economy
from .ui.embeds import create_aquarium_dashboard
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
    # ==================== ECONOMY COMMANDS ====================
    @app_commands.command(name="taiche", description="♻️ Tái chế rác thành Xu Lá & Phân Bón")
    async def taiche_slash(self, interaction: discord.Interaction):
        """Recycle trash for Leaf Coins."""
        await interaction.response.defer()
        success, msg, count, coins = await aquarium_economy.process_checklist_recycle(interaction.user.id)
        # Create a nice embed
        embed = discord.Embed(
            title="♻️ Trạm Tái Chế",
            description=msg,
            color=0x2ecc71 if success else 0xe74c3c
        )
        if success:
             embed.set_thumbnail(url="https://media.discordapp.net/attachments/123/recycle.png")
        await interaction.followup.send(embed=embed)

    @commands.command(name="taiche", description="♻️ Tái chế rác thành Xu Lá & Phân Bón")
    async def taiche_prefix(self, ctx):
        """Recycle trash via prefix."""
        success, msg, count, coins = await aquarium_economy.process_checklist_recycle(ctx.author.id)
        embed = discord.Embed(
            title="♻️ Trạm Tái Chế",
            description=msg,
            color=0x2ecc71 if success else 0xe74c3c
        )
        await ctx.send(embed=embed)

    # ==================== SOCIAL COMMANDS ====================
    @app_commands.command(name="thamnha", description="🏠 Ghé thăm nhà hàng xóm (Cơ hội nhận quà!)")
    async def thamnha(self, interaction: discord.Interaction, user: discord.User):
        """Visit another user's home."""
        await interaction.response.defer()
        
        # 1. Check if Target has house
        if not await housing_manager.has_house(user.id):
             return await interaction.followup.send(f"❌ **{user.display_name}** chưa có nhà (Họ là người vô gia cư?)")
        
        # 2. Process Visit
        # Note: can visit self, but HousingManager handles logic (no reward)
        result = await housing_manager.visit_home(interaction.user.id, user.id)
        
        # 3. Prepare House View
        # We want to show the house visuals too
        slots = await housing_manager.get_slots(user.id)
        inventory = await housing_manager.get_inventory(user.id)
        stats = await housing_manager.calculate_home_stats(user.id)
        visuals = render_engine.generate_view(slots)
        
        dashboard = create_aquarium_dashboard(
            user_name=user.display_name,
            user_avatar=user.display_avatar.url,
            view_visuals=visuals,
            stats=stats,
            inventory_count=len(inventory)
        )
        
        # 4. Result Embed
        msg_color = 0x2ecc71 if result["success"] else 0xe74c3c
        if "lại" in result["message"] or "không thể" in result["message"]:
            msg_color = 0x95a5a6 # Grey if already visited/self
            
        embed_result = discord.Embed(
            description=result["message"],
            color=msg_color
        )
        embed_result.set_author(name=f"{interaction.user.display_name} đang ghé thăm {user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        # Send both: Result + Dashboard
        await interaction.followup.send(embeds=[embed_result, dashboard])

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
        
        # 3. Create Embed via Unified Generator
        initial_slots = [None] * 5
        initial_visuals = render_engine.generate_view(initial_slots)
        initial_stats = {"charm": 0, "value": 0, "sets": []}

        embed = create_aquarium_dashboard(
            user_name=interaction.user.display_name,
            user_avatar=interaction.user.display_avatar.url,
            view_visuals=initial_visuals,
            stats=initial_stats,
            inventory_count=0
        )
        
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
                 await interaction.followup.send("❌ Đã tạo thread nhưng lỗi lưu Dữ liệu. Vui lòng báo Admin.")
         
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

    @decor_group.command(name="sapxep", description="🛋️ Sắp xếp nội thất và trang trí hồ cá")
    async def decor_sapxep(self, interaction: discord.Interaction):
        """Arrange decor items."""
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        # 1. Check Housing
        if not await housing_manager.has_house(user_id):
            return await interaction.followup.send("❌ Bạn chưa có nhà! Dùng `/nha khoitao` đi.", ephemeral=True)
            
        # 2. Fetch Data
        try:
            slots = await housing_manager.get_slots(user_id)
            inventory = await housing_manager.get_inventory(user_id)
        except Exception as e:
            logger.error(f"[SAPXEP_CMD] DB Error: {e}")
            return await interaction.followup.send("❌ Lỗi dữ liệu! Thử lại sau.")

        # 3. Prepare Visuals
        visuals = render_engine.generate_view(slots)
        
        embed = discord.Embed(
            title=f"🛋️ Thiết Kế Nội Thất",
            description="Chọn vị trí (1-5) và vật phẩm để đặt.\n*Nhấn 'Lưu' để cập nhật ra thread ngoài.*",
            color=0x9b59b6
        )
        embed.add_field(name="🖼️ Bể Cá & Nội Thất", value=visuals, inline=False)
        embed.set_footer(text=f"Kho: {len(inventory)} loại vật phẩm")
        
        # 4. View
        # Need to import DecorPlacementView here to avoid circular import at top level?
        # Ideally import at top, but views imports housing_manager which imports database...
        # views.py already imports shop/constants. 
        # Let's fix import in cog.py
        from .ui.views import DecorPlacementView
        view = DecorPlacementView(user_id, inventory, slots)
        
        
        await interaction.followup.send(embed=embed, view=view)

    # ==================== ADMIN COMMANDS ====================
    @commands.command(name="themxu", description="Thêm Xu Lá cho user (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_leaf_coins_admin(self, ctx, user: discord.User, amount: int):
        """Add Leaf Coins to a user (Admin only)"""
        if amount == 0:
            await ctx.send("❌ Số lượng phải khác 0!")
            return
            
        success = await aquarium_economy.add_leaf_coins(user.id, amount, reason=f"admin_grant_by_{ctx.author.id}")
        
        if success:
           await ctx.send(f"✅ Đã thêm **{amount} Xu Lá** cho **{user.name}**.")
        else:
           await ctx.send("❌ Lỗi khi thêm tiền. Vui lòng kiểm tra log.")

    @app_commands.command(name="themxu", description="Thêm Xu Lá cho user (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="Người nhận", amount="Số lượng cần thêm")
    async def add_leaf_coins_slash(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Add Leaf Coins to a user (Admin only) - Slash"""
        await interaction.response.defer(ephemeral=True)
        if amount == 0:
            await interaction.followup.send("❌ Số lượng phải khác 0!", ephemeral=True)
            return

        success = await aquarium_economy.add_leaf_coins(user.id, amount, reason=f"admin_grant_by_{interaction.user.id}")
        
        if success:
           await interaction.followup.send(f"✅ Đã thêm **{amount} Xu Lá** cho **{user.name}**.", ephemeral=True)
        else:
           await interaction.followup.send("❌ Lỗi khi thêm tiền.", ephemeral=True)

    # ==================== LISTENERS ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto-bump home dashboard when users chat in home threads."""
        if message.author.bot:
            return
            
        # Optimization: Only check threads in the Forum Channel (if known) 
        # But easier to just check if this thread is a registered house
        # Check cache/db if channel is a house
        
        try:
            # Check if this channel is a house
            owner_id = await housing_manager.get_house_owner(message.channel.id)
            if owner_id:
                # Be careful of race conditions or spam.
                # refresh_dashboard handles "only bump if not latest" check.
                # We can add a debounce here if needed, but for now relies on logic inside refresh.
                await housing_manager.refresh_dashboard(owner_id, self.bot)
        except Exception as e:
            logger.error(f"[AUTO_BUMP_ERROR] {e}")



    # ==================== VIP SYSTEM ====================

    @app_commands.command(name="thuongluu", description="Hệ thống V.I.P Thành Viên")
    async def vip_system(self, interaction: discord.Interaction):
        """Mở menu đăng ký thành viên"""
        from .ui.views import VIPSubscriptionView
        from .core.vip import vip_manager
        
        # Check current status
        current_vip = await vip_manager.get_vip_data(interaction.user.id)
        
        desc = "Chào mừng đến với CLB Thượng Lưu!\nHãy chọn gói thành viên để hưởng đặc quyền."
        color = 0x2b2d31
        
        if current_vip:
            tier_colors = {
                1: "⚪ Bạc (Silver)",
                2: "🟡 Vàng (Gold)",
                3: "💎 Kim Cương (Diamond)"
            }
            tier_name = tier_colors.get(current_vip['tier'], "Unknown")
            
            desc = f"**Bạn đang là thành viên: {tier_name}**\n⏳ Hết hạn: `{current_vip['expiry']}`\n\nBạn có thể gia hạn hoặc nâng cấp bên dưới."
            color = 0xf1c40f # Gold

        embed = discord.Embed(
            title="💎 Hệ Thống Thành Viên (VIP)",
            description=desc,
            color=color
        )
        embed.set_image(url="https://media.discordapp.net/attachments/123/vip_banner.png") # Placeholder
        
        view = VIPSubscriptionView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AquariumCog(bot))

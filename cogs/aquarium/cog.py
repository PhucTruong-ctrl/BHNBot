import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional
from core.logging import get_logger
from datetime import datetime, timedelta, time

from core.database import db_manager
from .logic.housing import HousingEngine
from .logic.market import MarketEngine
from .logic.render import RenderEngine
from .models import UserAquarium
from core.services.vip_service import VIPEngine
from .ui.embeds import create_aquarium_dashboard
from .ui.views import DecorShopView, AutoVisitView
from .constants import AQUARIUM_FORUM_CHANNEL_ID

logger = get_logger("aquarium_cog")

class AquariumCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_auto_visit_task.start()
        self.passive_income_task.start()
        self.last_dashboard_refresh = {}
        logger.info("[AQUARIUM_COG] Cog initialized + Tasks Started")
    
    async def cog_unload(self) -> None:
        self.daily_auto_visit_task.cancel()
        self.passive_income_task.cancel()
    
    # Define Groups
    nha_group = app_commands.Group(name="nha", description="Quản lý Nhà Cửa & Hồ Cá")
    decor_group = app_commands.Group(name="trangtri", description="Mua sắm & Sắp xếp Nội thất")
    loadout_group = app_commands.Group(name="loadout", description="Quản lý Bộ Trang Trí theo Hoạt Động")

    # ==================== CRON TASKS ====================
    @tasks.loop(time=time(hour=8, minute=0, second=0)) # 8 AM
    async def daily_auto_visit_task(self):
        """Run auto-visit for subscribed VIPs."""
        logger.info("[AUTO_VISIT] Starting daily task...")
        
        now = datetime.now().isoformat()
        
        # Fetch active tasks
        rows = await db_manager.fetchall(
            "SELECT user_id, expires_at FROM vip_auto_tasks WHERE task_type='auto_visit' AND expires_at > ?",
            (now,)
        )
        
        if not rows:
            logger.info("[AUTO_VISIT] No active subscriptions.")
            return
            
        count = 0
        total_rewards = 0
        
        for row in rows:
            user_id, _ = row
            
            try:
                # Logic: Visit 5 random neighbors? 
                # For Phase 2.2, just give flat rewards simulating visits.
                # Reward: 100 seeds per day (simulating 5 visits * 20 seeds)
                REWARD = 100
                from database_manager import add_seeds
                
                await add_seeds(user_id, REWARD, "VIP Auto Visit Reward", "aquarium")
                total_rewards += REWARD
                count += 1
                
            except Exception as e:
                logger.error(f"[AUTO_VISIT] Error for user {user_id}: {e}")
                
        logger.info(f"[AUTO_VISIT] Completed. Processed {count} users, Total Rewards: {total_rewards}")

    @tasks.loop(hours=24)
    async def passive_income_task(self):
        """Collect passive income from aquarium set bonuses."""
        logger.info("[PASSIVE_INCOME] Starting daily collection...")
        
        from .logic.effect_manager import get_effect_manager
        from database_manager import add_seeds
        
        effect_manager = get_effect_manager()
        
        users_with_income = await UserAquarium.all().values_list("user_id", flat=True)
        
        collected = 0
        total_income = 0
        
        for user_id_val in users_with_income:
            user_id: int = user_id_val  # type: ignore[assignment]
            try:
                income = await effect_manager.get_total_passive_income(user_id)
                if income > 0:
                    await add_seeds(user_id, income, "Aquarium Passive Income", "aquarium")
                    collected += 1
                    total_income += income
            except Exception as e:
                logger.error(f"[PASSIVE_INCOME] Error for user {user_id}: {e}")
        
        logger.info(f"[PASSIVE_INCOME] Completed. {collected} users collected {total_income} total seeds.")

    # ==================== ECONOMY COMMANDS ====================
    @app_commands.command(name="taiche", description="♻️ Tái chế rác thành Xu Lá & Phân Bón")
    async def taiche_slash(self, interaction: discord.Interaction):
        """Recycle trash for Leaf Coins."""
        await interaction.response.defer()
        success, msg, count, coins = await MarketEngine.recycle_trash(interaction.user.id)
        
        embed = discord.Embed(
            title="♻️ Trạm Tái Chế",
            description=msg,
            color=0x2ecc71 if success else 0xe74c3c
        )
        if success:
             # Basic recycle icon
             embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/337/recycling-symbol_267b.png")
        await interaction.followup.send(embed=embed)

    @commands.command(name="taiche", description="♻️ Tái chế rác thành Xu Lá & Phân Bón")
    async def taiche_prefix(self, ctx):
        """Recycle trash via prefix."""
        success, msg, count, coins = await MarketEngine.recycle_trash(ctx.author.id)
        embed = discord.Embed(
            title="♻️ Trạm Tái Chế",
            description=msg,
            color=0x2ecc71 if success else 0xe74c3c
        )
        await ctx.send(embed=embed)

    # ==================== SOCIAL COMMANDS ====================
    @app_commands.command(name="thamnha", description="🏠 Ghé thăm nhà hàng xóm (Cơ hội nhận quà!) hoặc Đăng ký Tự động")
    @app_commands.describe(user="Người bạn muốn thăm (Để trống để mở menu Auto)")
    async def thamnha(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Visit another user's home or open Auto-Visit Menu."""
        
        # --- MODE 1: AUTO VISIT MENU (No User provided) ---
        if user is None:
            await interaction.response.defer(ephemeral=True)
            
            # Check VIP
            vip = await VIPEngine.get_vip_data(interaction.user.id)
            if not vip or vip['tier'] < 3:
                return await interaction.followup.send("❌ Chức năng Auto-Visit chỉ dành cho VIP 💎 [KIM CƯƠNG]!", ephemeral=True)

            # Check Status
            row = await db_manager.fetchone(
                "SELECT expires_at FROM vip_auto_tasks WHERE user_id = ? AND task_type = 'auto_visit'",
                (interaction.user.id,)
            )
            
            is_active = False
            expiry_str = ""
            if row and row[0]:
                expires = datetime.fromisoformat(row[0])
                if expires > datetime.now():
                    is_active = True
                    expiry_str = f"<t:{int(expires.timestamp())}:R>"
            
            if is_active:
                embed = discord.Embed(
                    title="🤖 Auto-Visit Manager",
                    description=f"✅ **Đang hoạt động!**\n⏳ Hết hạn: {expiry_str}\n\nBot đang tự động thăm 5 nhà/ngày cho bạn.",
                    color=0x2ecc71
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🤖 Auto-Visit Manager",
                    description="**Chưa đăng ký!**\n\nBot sẽ tự động thăm 5 nhà hàng xóm mỗi ngày.\nNhận 100 seeds/ngày.\n\n**Phí:** 50,000 Hạt / 30 ngày.",
                    color=0x95a5a6
                )
                view = AutoVisitView(interaction.user.id)
                await interaction.followup.send(embed=embed, view=view)
            return

        # --- MODE 2: MANUAL VISIT (User provided) ---
        await interaction.response.defer()
        
        # 1. Check if Target has house
        if not await HousingEngine.has_house(user.id):
             return await interaction.followup.send(f"❌ **{user.display_name}** chưa có nhà (Họ là người vô gia cư?)")
        
        # 2. Process Visit
        result = await HousingEngine.visit_home(interaction.user.id, user.id)
        
        # 3. Prepare House View
        slots = await HousingEngine.get_slots(user.id)
        inventory = await HousingEngine.get_inventory(user.id)
        stats = await HousingEngine.calculate_home_stats(user.id)
        visuals = RenderEngine.generate_view(slots)
        
        # Phase 3: Get Theme URL
        theme_url = await HousingEngine.get_theme(user.id)
        
        dashboard = create_aquarium_dashboard(
            user_name=user.display_name,
            user_avatar=user.display_avatar.url,
            view_visuals=visuals,
            stats=stats,
            inventory_count=len(inventory),
            theme_url=theme_url
        )
        
        # 4. Result Embed
        msg_color = 0x2ecc71 if result["success"] else 0xe74c3c
        if "lại" in result["message"] or "không thể" in result["message"]:
            msg_color = 0x95a5a6
            
        # GIVE RANDOM REWARD FOR VISITING
        from database_manager import add_seeds
        import random
        reward = random.randint(10, 30)
        await add_seeds(interaction.user.id, reward, "visit_reward", "aquarium")
        reward_msg = f"\n🎁 Bạn nhận được **{reward} hạt** nhờ ghé thăm hàng xóm!"
            
        embed_result = discord.Embed(
            description=result["message"] + reward_msg,
            color=msg_color
        )
        embed_result.set_author(name=f"{interaction.user.display_name} đang ghé thăm {user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embeds=[embed_result, dashboard])

    # ==================== HOUSING COMMANDS ====================
    @nha_group.command(name="khoitao", description="Nhận đất và xây hồ cá riêng!")
    async def nha_khoitao(self, interaction: discord.Interaction):
        """Create a new home thread for the user."""
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        if await HousingEngine.has_house(user_id):
            return await interaction.followup.send("❌ Bạn đã có nhà rồi! Đừng tham lam!", ephemeral=True)
        
        
        # [Postgres via db_manager]
        row = await db_manager.fetchrow(
            "SELECT aquarium_forum_channel_id FROM server_config WHERE guild_id = $1",
            (interaction.guild_id,)
        )
        forum_id = row['aquarium_forum_channel_id'] if row else None

        if not forum_id:
            return await interaction.followup.send(f"❌ Chưa cấu hình Forum Channel! Báo Admin dùng `/config set kenh_aquarium`.", ephemeral=True)

        forum_channel = self.bot.get_channel(forum_id)
        if not forum_channel:
            # Try fetch
            try:
                forum_channel = await self.bot.fetch_channel(forum_id)
            except Exception:
                return await interaction.followup.send(f"❌ Lỗi Config: Không tìm thấy kênh Làng Chài (ID: {forum_id}).", ephemeral=True)
        
        # Create Embed
        initial_slots: list[str | None] = [None] * 5
        initial_visuals = RenderEngine.generate_view(initial_slots)
        initial_stats = {"charm": 0, "value": 0, "sets": []}

        embed = create_aquarium_dashboard(
            user_name=interaction.user.display_name,
            user_avatar=interaction.user.display_avatar.url,
            view_visuals=initial_visuals,
            stats=initial_stats,
            inventory_count=0
        )
        
        try:
            thread_with_message = await forum_channel.create_thread(
                name=f"Nhà của {interaction.user.display_name}",
                content=f"Chào mừng gia chủ {interaction.user.mention}!",
                embed=embed
            )
            
            created_thread = thread_with_message.thread if hasattr(thread_with_message, 'thread') else thread_with_message
            
            success = await HousingEngine.register_house(user_id, created_thread.id)
            
            if success:
                # Set dashboard ID if possible
                if hasattr(thread_with_message, 'message'):
                    await HousingEngine.set_dashboard_message_id(user_id, thread_with_message.message.id)
                elif hasattr(created_thread, 'starter_message'):
                     if created_thread.starter_message:
                        await HousingEngine.set_dashboard_message_id(user_id, created_thread.starter_message.id)
                
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
            description="Chào mừng! Bạn muốn mua gì hôm nay?\n\n*Dùng **Hạt** và **Xu Lá** để mua sắm.*",
            color=0xe67e22
        )
        embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/337/convenience-store_1f3ea.png")
        
        view = DecorShopView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @decor_group.command(name="sapxep", description="🛋️ Sắp xếp nội thất và trang trí hồ cá")
    async def decor_sapxep(self, interaction: discord.Interaction):
        """Arrange decor items."""
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        if not await HousingEngine.has_house(user_id):
            return await interaction.followup.send("❌ Bạn chưa có nhà! Dùng `/nha khoitao` đi.", ephemeral=True)
            
        try:
            slots = await HousingEngine.get_slots(user_id)
            inventory = await HousingEngine.get_inventory(user_id)
        except Exception as e:
            logger.error(f"[SAPXEP_CMD] DB Error: {e}")
            return await interaction.followup.send("❌ Lỗi dữ liệu! Thử lại sau.")

        visuals = RenderEngine.generate_view(slots)
        
        embed = discord.Embed(
            title=f"🛋️ Thiết Kế Nội Thất",
            description=f"Chọn vị trí (1-5) và vật phẩm để đặt.\n*Nhấn 'Lưu' để cập nhật ra thread ngoài.*\n\n{visuals}",
            color=0x9b59b6
        )
        # embed.add_field(name="🖼️ Bể Cá & Nội Thất", value=visuals, inline=False)
        embed.set_footer(text=f"Kho: {len(inventory)} loại vật phẩm")
        
        from .ui.views import DecorPlacementView
        view = DecorPlacementView(user_id, inventory, slots)
        await interaction.followup.send(embed=embed, view=view)

    @decor_group.command(name="theme", description="[VIP] Đổi hình nền hồ cá (GIF/Ảnh)")
    @app_commands.describe(url="Link ảnh/GIF (Imgur, Discord, Tenor...)")
    async def decor_theme(self, interaction: discord.Interaction, url: str):
        """Set Custom Aquarium Theme (VIP Only)."""
        await interaction.response.defer(ephemeral=True)
        
        # 1. VIP Check (Tier 2+)
        vip = await VIPEngine.get_vip_data(interaction.user.id)
        if not vip or vip['tier'] < 2:
            return await interaction.followup.send("❌ Chức năng đổi Theme chỉ dành cho VIP 🥇 [VÀNG] trở lên!", ephemeral=True)

        # 2. Validate URL (Basic check)
        if not url.startswith("http") or not any(x in url for x in [".jpg", ".png", ".gif", "tenor", "giphy", "discordapp"]):
            return await interaction.followup.send("❌ Link không hợp lệ! Vui lòng dùng link ảnh trực tiếp (JPG/PNG/GIF).", ephemeral=True)

        # 3. Save Theme
        if not await HousingEngine.has_house(interaction.user.id):
             return await interaction.followup.send("❌ Bạn chưa có nhà!", ephemeral=True)
             
        success = await HousingEngine.set_theme(interaction.user.id, url)
        
        if success:
            # Re-generate Dashboard to show effect immediately
            stats = await HousingEngine.calculate_home_stats(interaction.user.id)
            slots = await HousingEngine.get_slots(interaction.user.id)
            
            # Prepare data for dashboard
            inventory = await HousingEngine.get_inventory(interaction.user.id)
            inventory_count = len(inventory)
            visuals = RenderEngine.generate_view(slots)
            
            # Call with correct signature: user_name, user_avatar, view_visuals, stats, inventory_count, theme_url
            dashboard_embed = create_aquarium_dashboard(
                user_name=interaction.user.name,
                user_avatar=interaction.user.avatar.url if interaction.user.avatar else "",
                view_visuals=visuals,
                stats=stats,
                inventory_count=inventory_count,
                theme_url=url
            )
            
            await interaction.followup.send(f"✅ Đã cập nhật Theme thành công!", embed=dashboard_embed, ephemeral=True)
            from .utils import refresh_aquarium_dashboard
            await refresh_aquarium_dashboard(interaction.user.id, self.bot)
        else:
            await interaction.followup.send("❌ Lỗi khi lưu theme. Vui lòng thử lại.", ephemeral=True)

    # ==================== ADMIN COMMANDS ====================
    @commands.command(name="themxu", description="Thêm Xu Lá cho user (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_leaf_coins_admin(self, ctx, user: discord.User, amount: int):
        if amount == 0: return await ctx.send("❌ Số lượng != 0!")
        success = await MarketEngine.add_leaf_coins(user.id, amount, reason=f"admin_grant_by_{ctx.author.id}")
        if success: await ctx.send(f"✅ Đã thêm **{amount} Xu Lá** cho **{user.name}**.")
        else: await ctx.send("❌ Lỗi.")

    @app_commands.command(name="themxu", description="Thêm Xu Lá cho user (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_leaf_coins_slash(self, interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer(ephemeral=True)
        if amount == 0: return await interaction.followup.send("❌ Số lượng != 0!", ephemeral=True)
        success = await MarketEngine.add_leaf_coins(user.id, amount, reason=f"admin_grant_by_{interaction.user.id}")
        if success: await interaction.followup.send(f"✅ Đã thêm **{amount} Xu Lá** cho **{user.name}**.", ephemeral=True)
        else: await interaction.followup.send("❌ Lỗi.", ephemeral=True)

    # ==================== LOADOUT COMMANDS ====================
    
    @loadout_group.command(name="list", description="📋 Xem danh sách các bộ trang trí đã lưu")
    async def loadout_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        from .logic.loadout_service import get_loadout_service
        service = get_loadout_service()
        
        loadouts = await service.get_loadouts(interaction.user.id)
        
        if not loadouts:
            embed = discord.Embed(
                title="📋 Bộ Trang Trí",
                description="Bạn chưa lưu bộ trang trí nào.\n\nDùng `/loadout save` để lưu cấu hình hiện tại.",
                color=0x3498db
            )
            return await interaction.followup.send(embed=embed)
        
        embed = discord.Embed(
            title="📋 Danh Sách Bộ Trang Trí",
            color=0x3498db
        )
        
        for loadout in loadouts:
            status = "✅ Đang dùng" if loadout.is_active else "⬜ Tắt"
            activity_icons = {"fishing": "🎣", "harvest": "🌾", "sell": "💰", "passive": "💤", "global": "🌐"}
            icon = activity_icons.get(loadout.activity, "📦")
            embed.add_field(
                name=f"{icon} {loadout.name}",
                value=f"Hoạt động: `{loadout.activity}`\nTrạng thái: {status}",
                inline=True
            )
        
        embed.set_footer(text=f"Tổng: {len(loadouts)} bộ • /loadout apply <tên> để áp dụng")
        await interaction.followup.send(embed=embed)
    
    @loadout_group.command(name="save", description="💾 Lưu cấu hình nhà hiện tại thành bộ mới")
    @app_commands.describe(
        name="Tên bộ trang trí (VD: 'Câu Cá Pro')",
        activity="Loại hoạt động để kích hoạt bonus"
    )
    @app_commands.choices(activity=[
        app_commands.Choice(name="🎣 Câu Cá", value="fishing"),
        app_commands.Choice(name="🌾 Thu Hoạch", value="harvest"),
        app_commands.Choice(name="💰 Bán Cá", value="sell"),
        app_commands.Choice(name="💤 Thu Nhập Thụ Động", value="passive"),
        app_commands.Choice(name="🌐 Toàn Bộ (XP)", value="global"),
    ])
    async def loadout_save(self, interaction: discord.Interaction, name: str, activity: str):
        await interaction.response.defer()
        
        from .logic.loadout_service import get_loadout_service
        service = get_loadout_service()
        
        try:
            loadout = await service.save_current_home_as_loadout(
                interaction.user.id, name, activity
            )
            
            preview = await service.get_loadout_preview(loadout)
            active_sets = preview.get("active_sets", [])
            
            embed = discord.Embed(
                title=f"✅ Đã Lưu: {name}",
                description=f"Hoạt động: `{activity}`\nCharm: {preview['total_charm']}",
                color=0x2ecc71
            )
            
            if active_sets:
                sets_text = "\n".join([f"• **{s['name']}** ({s['pieces']} mảnh)" for s in active_sets])
                embed.add_field(name="🌟 Set Kích Hoạt", value=sets_text, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except ValueError as e:
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
    
    @loadout_group.command(name="apply", description="🔄 Áp dụng bộ trang trí vào nhà")
    @app_commands.describe(name="Tên bộ trang trí cần áp dụng")
    async def loadout_apply(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        
        from .logic.loadout_service import get_loadout_service
        service = get_loadout_service()
        
        success = await service.apply_loadout_to_home(interaction.user.id, name)
        
        if success:
            await service.activate_loadout(interaction.user.id, name)
            
            loadout = await service.get_loadout_by_name(interaction.user.id, name)
            if not loadout:
                await interaction.followup.send("❌ Lỗi: Không tìm thấy loadout.", ephemeral=True)
                return
            preview = await service.get_loadout_preview(loadout)
            
            embed = discord.Embed(
                title=f"✅ Đã Áp Dụng: {name}",
                description=f"Nội thất đã được thay đổi theo bộ `{name}`.",
                color=0x2ecc71
            )
            
            if preview.get("active_sets"):
                bonuses = []
                for s in preview["active_sets"]:
                    for effect, value in s.get("bonus", {}).items():
                        if isinstance(value, float):
                            bonuses.append(f"+{value*100:.0f}% {effect}")
                        else:
                            bonuses.append(f"+{value} {effect}")
                if bonuses:
                    embed.add_field(name="🎁 Bonus Nhận Được", value="\n".join(bonuses), inline=False)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Không tìm thấy bộ `{name}`.", ephemeral=True)
    
    @loadout_group.command(name="delete", description="🗑️ Xóa bộ trang trí")
    @app_commands.describe(name="Tên bộ trang trí cần xóa")
    async def loadout_delete(self, interaction: discord.Interaction, name: str):
        from .logic.loadout_service import get_loadout_service
        service = get_loadout_service()
        
        success = await service.delete_loadout(interaction.user.id, name)
        
        if success:
            await interaction.response.send_message(f"✅ Đã xóa bộ `{name}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Không tìm thấy bộ `{name}`.", ephemeral=True)

    # ==================== LISTENERS ====================
    
    @commands.command(name="test_autovisit", hidden=True)
    @commands.is_owner()
    async def test_autovisit_cmd(self, ctx):
        """[TEST] Force trigger auto-visit task."""
        await ctx.send("🔄 Force Triggering Auto-Visit Task...")
        try:
            await self.daily_auto_visit_task()
            await ctx.send("✅ Auto-Visit Task Completed. Check Logs.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            return
            
        try:
            if isinstance(message.channel, discord.Thread):
                owner_id = await HousingEngine.get_house_owner(message.channel.id)
                if owner_id:
                    import time
                    now = time.time()
                    last_refresh = self.last_dashboard_refresh.get(message.channel.id, 0)
                    
                    if now - last_refresh < 30:
                        return
                    
                    self.last_dashboard_refresh[message.channel.id] = now
                    
                    from .utils import refresh_aquarium_dashboard
                    await refresh_aquarium_dashboard(owner_id, self.bot)
        except Exception as e:
            logger.error(f"[AUTO_BUMP_ERROR] {e}")

async def setup(bot):
    await bot.add_cog(AquariumCog(bot))

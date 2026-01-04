import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, timedelta, time

from core.database import db_manager
from .logic.housing import HousingEngine
from .logic.market import MarketEngine
from .logic.render import RenderEngine
from core.services.vip_service import VIPEngine
from .ui.embeds import create_aquarium_dashboard
from .ui.views import DecorShopView
from .constants import AQUARIUM_FORUM_CHANNEL_ID

logger = logging.getLogger("AquariumCog")

class AquariumCog(commands.Cog):
    """
    Project Aquarium: Symbiosis Model
    - Economy (Leaf Coin, Recycle)
    - Housing (Home, Decor)
    - Interaction (Visitors)
    """

    def __init__(self, bot):
        self.bot = bot
        # Start auto-visit task
        self.daily_auto_visit_task.start()
        logger.info("[AQUARIUM_COG] Cog initialized + Auto-Visit Task Started")
    
    def cog_unload(self):
        self.daily_auto_visit_task.cancel()
    
    # Define Groups
    nha_group = app_commands.Group(name="nha", description="Quản lý Nhà Cửa & Hồ Cá")
    decor_group = app_commands.Group(name="trangtri", description="Mua sắm & Sắp xếp Nội thất")

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
    @app_commands.command(name="thamnha", description="🏠 Ghé thăm nhà hàng xóm (Cơ hội nhận quà!)")
    async def thamnha(self, interaction: discord.Interaction, user: discord.User):
        """Visit another user's home."""
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
            except:
                return await interaction.followup.send(f"❌ Lỗi Config: Không tìm thấy kênh Làng Chài (ID: {forum_id}).", ephemeral=True)
        
        # Create Embed
        initial_slots = [None] * 5
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

    @nha_group.command(name="auto", description="[VIP 3] Đăng ký tự động thăm nhà (50k/tháng)")
    async def nha_auto(self, interaction: discord.Interaction):
        """Register for Auto-Visit (Tier 3 Only)."""
        await interaction.response.defer(ephemeral=True)
        
        # 1. Check VIP
        vip = await VIPEngine.get_vip_data(interaction.user.id)
        if not vip or vip['tier'] < 3:
            await interaction.followup.send("❌ Chỉ dành cho VIP 💎 [KIM CƯƠNG]!", ephemeral=True)
            return

        # 2. Check Existing
        row = await db_manager.fetchone(
            "SELECT expires_at FROM vip_auto_tasks WHERE user_id = ? AND task_type = 'auto_visit'",
            (interaction.user.id,)
        )
        
        now = datetime.now()
        
        if row and row[0]:
            expires = datetime.fromisoformat(row[0])
            if expires > now:
                remaining = expires - now
                days = remaining.days
                await interaction.followup.send(
                    f"✅ Bạn đang đăng ký tự động thăm! Hết hạn sau: {days} ngày.",
                    ephemeral=True
                )
                return
        
        # 3. Payment
        COST = 50000
        DURATION_DAYS = 30
        
        from database_manager import get_user_balance, add_seeds
        
        balance = await get_user_balance(interaction.user.id)
        if balance < COST:
            await interaction.followup.send(f"❌ Không đủ hạt! Cần {COST:,} hạt.", ephemeral=True)
            return
            
        await add_seeds(interaction.user.id, -COST, "vip_autovisit", "service")
        
        # 4. Register
        expiry = (now + timedelta(days=DURATION_DAYS)).isoformat()
        
        await db_manager.execute(
            """
            INSERT INTO vip_auto_tasks (user_id, task_type, expires_at, last_run_at)
            VALUES (?, 'auto_visit', ?, ?)
            ON CONFLICT(user_id, task_type) DO UPDATE SET
                expires_at = ?,
                last_run_at = ?
            """,
            (interaction.user.id, expiry, now.isoformat(), expiry, now.isoformat())
        )
        
        await interaction.followup.send(
            f"✅ Đăng ký thành công! Bot sẽ tự thăm 5 nhà hàng xóm mỗi ngày (100xp). Đã trừ {COST:,} hạt.",
            ephemeral=True
        )

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
            # Check if this thread/channel is a house
            # Note: This runs on every message. Performance?
            # Optimization: Only check if channel is Thread?
            if isinstance(message.channel, discord.Thread):
                owner_id = await HousingEngine.get_house_owner(message.channel.id)
                if owner_id:
                    # Debounce needed?
                    # refresh_aquarium_dashboard handles "don't update if latest message is dashboard".
                    # But it will send a new dashboard if the last message is USER message.
                    # This means every user chat message triggers a bot dashboard send.
                    # This might be spammy.
                    # Logic: If user chats, we want dashboard to be visible at bottom.
                    # Yes, that's the "Always-on Dashboard" concept.
                    from .utils import refresh_aquarium_dashboard
                    await refresh_aquarium_dashboard(owner_id, self.bot)
        except Exception as e:
            logger.error(f"[AUTO_BUMP_ERROR] {e}")

async def setup(bot):
    await bot.add_cog(AquariumCog(bot))

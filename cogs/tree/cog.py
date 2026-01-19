import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from datetime import datetime, timedelta, time, timezone
from database_manager import db_manager
from core.services.vip_service import VIPEngine
from core.logging import setup_logger

from .tree_manager import TreeManager
from .contributor_manager import ContributorManager
from .models import TreeData, HarvestBuff
from .helpers import create_tree_embed, format_contributor_list, format_all_time_contributors
from .views import ContributeModal, AutoWaterView

logger = setup_logger("TreeCog", "logs/cogs/tree.log")


class TreeCog(commands.Cog):
    """Cog for community tree system.
    
    Manages complete tree lifecycle:
    - Seed contributions
    - Tree growth (6 levels)
    - Seasonal progression
    - Harvest events
    - Contributor rankings
    """
    
    def __init__(self, bot):
        """Initialize the Tree cog.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.contributor_manager = ContributorManager(bot)
        self.tree_manager = TreeManager(bot, self.contributor_manager)
        
        # Start auto-water task
        self.daily_auto_water_task.start()
        logger.info("[TREE_COG] Cog initialized + Auto-Water Task Started")
    
    async def cog_unload(self):
        self.daily_auto_water_task.cancel()
        
    async def cog_load(self):
        """Update all tree messages on bot startup.
        
        Uses skip_if_latest=True to avoid unnecessary delete+resend
        if tree message is already the latest in its channel.
        """
        await super().cog_load()
        logger.info("[TREE] Cog loaded, updating tree messages for all guilds...")
        
        for guild in self.bot.guilds:
            try:
                tree_data = await TreeData.load(guild.id)
                if tree_data.tree_channel_id:
                    await self.tree_manager.update_tree_message(
                        guild.id,
                        tree_data.tree_channel_id,
                        skip_if_latest=True  # Avoid spam on restart
                    )
            except Exception as e:
                logger.error(
                    f"[TREE] Error updating tree on load for guild {guild.id}: {e}",
                    exc_info=True
                )

    #==================== EXTERNAL_API ====================
    
    async def get_tree_data(self, guild_id: int):
        """Get tree data tuple for external display.
        
        Returns:
            (level, progress, total, season, requirement, percentage)
        """
        tree_data = await TreeData.load(guild_id)
        level_reqs = tree_data.get_level_requirements()
        req = level_reqs.get(tree_data.current_level + 1, level_reqs[6])
        percentage = tree_data.calculate_progress_percent()
        
        return (
            tree_data.current_level,
            tree_data.current_progress,
            tree_data.total_contributed,
            tree_data.season,
            req,
            percentage
        )

    async def add_external_contribution(
        self, 
        user_id: int, 
        guild_id: int, 
        amount: int, 
        contribution_type: str = "seeds"
    ):
        """Handle contribution from other cogs (e.g. fertilizer).
        
        Args:
            user_id: User contributing
            guild_id: Guild ID
            amount: Amount/Value to contribute
            contribution_type: Type of contribution
        """
        # Load data
        tree_data = await TreeData.load(guild_id)
        
        # Check max level
        if tree_data.current_level >= 6:
            return  # No effect if maxed
            
        # Add to progress
        # For external contributions like fertilizer, amount IS ALL EXP
        # TreeData stores progress in 'seeds equivalent'
        
        # Update Tree Progress
        new_progress = tree_data.current_progress + amount
        new_total = tree_data.total_contributed + amount # Fertilizer adds to total too
        
        # Handle Level Up
        level_reqs = tree_data.get_level_requirements()
        req = level_reqs.get(tree_data.current_level + 1, level_reqs[6])
        new_level = tree_data.current_level
        
        while new_progress >= req and new_level < 6:
            new_level += 1
            new_progress = new_progress - req
            req = level_reqs.get(new_level + 1, level_reqs[6])
            
        tree_data.current_level = new_level
        tree_data.current_progress = new_progress
        tree_data.total_contributed = new_total
        await tree_data.save()
        
        # Record Contribution
        await self.contributor_manager.add_contribution(
            user_id,
            guild_id,
            tree_data.season,
            amount,
            contribution_type
        )
        
        # Update Message
        if tree_data.tree_channel_id:
            await self.tree_manager.update_tree_message(guild_id, tree_data.tree_channel_id)
            
    #==================== CRON TASKS ====================
    
    @tasks.loop(time=time(hour=7, minute=0, second=0)) # 7 AM
    async def daily_auto_water_task(self):
        """Run auto-watering for subscribed VIPs."""
        logger.info("[AUTO_WATER] Starting daily task...")
        
        now = datetime.now().isoformat()
        
        rows = await db_manager.fetchall(
            "SELECT user_id, expires_at FROM vip_auto_tasks WHERE task_type='auto_water' AND expires_at > $1",
            (now,)
        )
        
        if not rows:
            logger.info("[AUTO_WATER] No active subscriptions.")
            return
            
        count = 0
        
        for row in rows:
            user_id, task_expiry = row
            
            try:
                from core.services.vip_service import VIPEngine
                vip = await VIPEngine.get_vip_data(user_id, use_cache=False)
                
                if not vip or vip['tier'] < 3:
                    logger.warning(f"[AUTO_WATER] User {user_id} task active but VIP expired/downgraded. Skipping.")
                    continue
                
                vip_expiry = vip.get('expiry')
                if vip_expiry:
                    if vip_expiry.tzinfo is None:
                        vip_expiry = vip_expiry.replace(tzinfo=timezone.utc)
                    if vip_expiry < datetime.now(timezone.utc):
                        logger.warning(f"[AUTO_WATER] User {user_id} VIP expired. Skipping.")
                        continue
                
                for guild in self.bot.guilds:
                    member = guild.get_member(user_id)
                    if member:
                        await self.add_external_contribution(user_id, guild.id, 100, "auto_water")
                        count += 1
                        
            except Exception as e:
                logger.error(f"[AUTO_WATER] Error for user {user_id}: {e}")
                
        logger.info(f"[AUTO_WATER] Completed. Watered for {len(rows)} users (Total actions: {count}).")

    #==================== COMMANDS ====================
    
    # Create Group
    tuoi_group = app_commands.Group(name="tuoi", description="Các lệnh chăm sóc cây")



    @app_commands.command(name="gophat", description="Góp Hạt nuôi cây & Đăng ký Auto Tưới")
    @app_commands.describe(amount="Số hạt muốn góp (Mặc định: Mở menu)")
    async def contribute_tree(
        self,
        interaction: discord.Interaction,
        amount: Optional[int] = None
    ):
        """Contribute seeds or open Tree Care Menu."""
        
        # --- MENU & AUTO-WATER (No Amount) ---
        if amount is None:
            await interaction.response.defer(ephemeral=True)
            
            # Check Status
            row = await db_manager.fetchone(
                "SELECT expires_at FROM vip_auto_tasks WHERE user_id = ? AND task_type = 'auto_water'",
                (interaction.user.id,)
            )
            
            status_text = "⚪ **Chưa đăng ký**"
            is_active = False
            
            if row and row[0]:
                expires = datetime.fromisoformat(row[0])
                if expires > datetime.now():
                    is_active = True
                    status_text = f"✅ **Đang hoạt động** (Hết hạn: <t:{int(expires.timestamp())}:R>)"
            
            embed = discord.Embed(
                title="🌳 Chăm Sóc Cây Thần",
                description=f"Bạn muốn làm gì?\n\n**Trạng thái Auto-Tưới:**\n{status_text}\n\n*Auto-Tưới: 100 XP/ngày (50k/tháng)*",
                color=0x2ecc71
            )
            
            view = AutoWaterView(interaction.user.id, self.tree_manager)
            
            # If active, disable subscribe button? Or keep it for extension?
            # For simplicity, keeping it enabled or disabled based on logic in view?
            # View is fresh. Logic in view is barebones. 
            # I can just send view. 
            
            await interaction.followup.send(embed=embed, view=view)
            return

        # --- MANUAL CONTRIBUTION ---
        else:
            # SECURITY FIX #5: Validate amount range
            from .constants import MAX_CONTRIBUTION
            
            if amount <= 0:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send(
                    "❌ Số lượng phải lớn hơn 0!",
                    ephemeral=True
                )
                return
            
            if amount > MAX_CONTRIBUTION:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send(
                    f"❌ Số lượng quá lớn! Tối đa: {MAX_CONTRIBUTION:,} hạt",
                    ephemeral=True
                )
                return
            
            await self.tree_manager.process_contribution(interaction, amount)
    
    @app_commands.command(name="cay", description="Xem trạng thái cây server")
    async def show_tree(self, interaction: discord.Interaction):
        """Show current tree status with rankings.
        
        Displays:
        - Tree level and progress
        - Top contributors
        - Tree image
        """
        await interaction.response.defer()
        
        guild_id = interaction.guild.id
        tree_data = await TreeData.load(guild_id)
        
        embed = await create_tree_embed(interaction.user, tree_data)
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="huyhieu", description="Xem huy hiệu đóng góp của bạn")
    async def show_badge(self, interaction: discord.Interaction):
        """Display user's prestige badge and contribution stats."""
        from .constants import PRESTIGE_TIERS, PRESTIGE_BADGES
        
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        row = await db_manager.fetchone(
            "SELECT contribution_exp FROM tree_contributors WHERE user_id = $1 AND guild_id = $2",
            (user_id, guild_id)
        )
        
        total_exp = row[0] if row else 0
        
        current_tier = 0
        for tier_num in sorted(PRESTIGE_TIERS.keys(), reverse=True):
            if total_exp >= PRESTIGE_TIERS[tier_num]["min_exp"]:
                current_tier = tier_num
                break
        
        if current_tier == 0:
            embed = discord.Embed(
                title="🌱 Huy Hiệu Đóng Góp",
                description=f"Bạn chưa đạt huy hiệu nào!\n\n**Tổng XP hiện tại:** {total_exp:,}\n**Cần:** {1000:,} XP để đạt huy hiệu đầu tiên",
                color=0x95C77D
            )
            embed.add_field(
                name="📊 Tiến độ",
                value=f"{total_exp}/1,000 XP ({int(total_exp/1000*100)}%)",
                inline=False
            )
        else:
            tier_info = PRESTIGE_TIERS[current_tier]
            badge = PRESTIGE_BADGES[current_tier]
            
            next_tier = current_tier + 1
            if next_tier in PRESTIGE_TIERS:
                next_info = PRESTIGE_TIERS[next_tier]
                remaining = next_info["min_exp"] - total_exp
                progress_pct = int((total_exp - tier_info["min_exp"]) / (next_info["min_exp"] - tier_info["min_exp"]) * 100)
                
                embed = discord.Embed(
                    title=f"{badge} Huy Hiệu Đóng Góp",
                    description=f"**{tier_info['name']}**\n\n**Tổng XP:** {total_exp:,}\n**Tiếp theo:** {next_info['name']} (cần {remaining:,} XP nữa)",
                    color=tier_info["color"]
                )
                embed.add_field(
                    name="📊 Tiến độ đến tier tiếp theo",
                    value=f"{total_exp:,}/{next_info['min_exp']:,} XP ({progress_pct}%)",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title=f"{badge} Huy Hiệu Đóng Góp",
                    description=f"**{tier_info['name']}**\n\n**Tổng XP:** {total_exp:,}\n\n🎉 **Bạn đã đạt huy hiệu cao nhất!**",
                    color=tier_info["color"]
                )
        
        embed.add_field(
            name="🏅 Tất cả huy hiệu",
            value=(
                f"🌱 Người Trồng Cây (1,000 XP)\n"
                f"🌿 Người Làm Vườn (5,000 XP)\n"
                f"🌳 Người Bảo Vệ Rừng (25,000 XP)\n"
                f"🌸 Thần Nông (100,000 XP)\n"
                f"🍎 Tiên Nhân (500,000 XP)"
            ),
            inline=False
        )
        embed.set_footer(text="Góp hạt cho cây để tăng XP và nhận huy hiệu!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="thuhoach", description="Thu hoạch cây (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def harvest_tree(self, interaction: discord.Interaction):
        """Harvest the tree when at max level - CLIMAX EVENT.
        
        Requirements:
        - Administrator permission
        - Tree must be level 6
        
        Results:
        - Distributes tiered rewards to contributors
        - Gives memorabilia items
        - Creates role for top contributor
        - Activates 24h server buff
        - Resets tree to season+1
        
        Args:
            interaction: Discord interaction
        """
        await self.tree_manager.execute_harvest(interaction)
    
    # ==================== LISTENERS ====================
    
    @commands.command(name="test_autowater", hidden=True)
    @commands.is_owner()
    async def test_autowater_cmd(self, ctx):
        """[TEST] Force trigger auto-water task."""
        await ctx.send("🔄 Force Triggering Auto-Water Task...")
        try:
            await self.daily_auto_water_task()
            await ctx.send("✅ Auto-Water Task Completed Check Logs.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto-update tree message when any message in tree channel.
        
        Uses debounce (5s cooldown) to prevent spam.
        
        Args:
            message: Discord message
        """
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message is in a tree channel
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return
        
        try:
            # Get tree channel for this guild
            tree_data = await TreeData.load(guild_id)
            if not tree_data.tree_channel_id:
                return
            
            if message.channel.id != tree_data.tree_channel_id:
                return
            
            # Update tree message (with debounce inside)
            await self.tree_manager.update_tree_message(
                guild_id,
                tree_data.tree_channel_id
            )
            
        except Exception as e:
            logger.error(f"[TREE] Error in on_message: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    """Load the Tree cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(TreeCog(bot))

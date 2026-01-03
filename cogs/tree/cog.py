"""Tree Cog - Main orchestrator.

Coordinates tree managers, contributors, and UI components.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from core.logger import setup_logger

from .tree_manager import TreeManager
from .contributor_manager import ContributorManager
from .models import TreeData, HarvestBuff
from .helpers import create_tree_embed, format_contributor_list, format_all_time_contributors
from .views import ContributeModal

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
        logger.info("[TREE_COG] Cog initialized")
    
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
    
    #==================== COMMANDS ====================
    
    @app_commands.command(name="gophat", description="Góp Hạt nuôi cây server")
    @app_commands.describe(amount="Số hạt muốn góp (tuỳ chọn)")
    async def contribute_tree(
        self,
        interaction: discord.Interaction,
        amount: Optional[int] = None
    ):
        """Contribute seeds to the community tree.
        
        If amount is not provided, shows modal for custom input.
        
        Args:
            interaction: Discord interaction
            amount: Optional number of seeds to contribute
        """
        if amount is None:
            # Show modal for custom input
            modal = ContributeModal(self.tree_manager)
            await interaction.response.send_modal(modal)
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
        - Active buffs
        - Top contributors (season + all-time)
        
        Args:
            interaction: Discord interaction
        """
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        
        # Load tree data
        tree_data = await TreeData.load(guild_id)
        
        # Create main embed
        embed = await create_tree_embed(interaction.user, tree_data)
        
        # Add buff info if active
        if await HarvestBuff.is_active(guild_id):
            from database_manager import db_manager
            from datetime import datetime
            
            result = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,)
            )
            if result and result[0]:
                buff_until = datetime.fromisoformat(result[0])
                timestamp = int(buff_until.timestamp())
                embed.add_field(
                    name="🌟 Buff Toàn Server",
                    value=f"X2 hạt còn <t:{timestamp}:R>",
                    inline=False
                )
        
        # Add contributor info
        current_season_contributors = await self.contributor_manager.get_top_contributors_season(
            guild_id,
            tree_data.season,
            3
        )
        all_time_contributors = await self.contributor_manager.get_top_contributors_all_time(guild_id, 3)
        
        if current_season_contributors:
            season_text = await format_contributor_list(
                current_season_contributors,
                self.tree_manager,  # Pass tree_manager for caching
                show_exp=False
            )
            embed.add_field(
                name=f"🏆 Top 3 Người Góp mùa {tree_data.season}",
                value=season_text,
                inline=False
            )
        
        if all_time_contributors:
            all_time_text = await format_all_time_contributors(
                all_time_contributors,
                self.tree_manager  # Pass tree_manager for caching
            )
            embed.add_field(
                name="🏆 Top 3 Người Góp toàn thời gian",
                value=all_time_text,
                inline=False
            )
        
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

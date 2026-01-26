"""
Economy Cog - Discord controller for economy system.

Handles Discord commands and events, delegates to service layer.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time
import time as time_module
from typing import Optional
from cogs.economy.services.economy_service import EconomyService
from cogs.economy.repositories.economy_repository import EconomyRepository
from cogs.economy.ui.economy_ui import EconomyUI
from core.logging import get_logger

logger = get_logger("EconomyCog")


class EconomyCog(commands.Cog):
    """Cog handling the economy system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.repository = EconomyRepository()
        self.service = EconomyService(self.repository)
        self.chat_cooldowns = {}  # {user_id: last_reward_time}
        self.reaction_cooldowns = {}  # {user_id: last_reaction_reward_time}
        self.voice_reward_task.start()
        self.weekly_welfare_task.start()
        self.cleanup_cooldowns_task.start()
    
    def cog_unload(self):
        self.voice_reward_task.cancel()
        self.weekly_welfare_task.cancel()
        self.cleanup_cooldowns_task.cancel()
    
    @tasks.loop(minutes=5)
    async def cleanup_cooldowns_task(self):
        now = time_module.time()
        cooldown_ttl = 300  # 5 minutes
        
        expired_chat = [k for k, v in self.chat_cooldowns.items() if now - v > cooldown_ttl]
        for k in expired_chat:
            del self.chat_cooldowns[k]
        
        expired_reaction = [k for k, v in self.reaction_cooldowns.items() if now - v > cooldown_ttl]
        for k in expired_reaction:
            del self.reaction_cooldowns[k]
        
        total_cleaned = len(expired_chat) + len(expired_reaction)
        if total_cleaned > 0:
            logger.debug(f"Cleaned {total_cleaned} expired cooldown entries")
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="chao", description="Chào buổi sáng (5h-10h) để nhận hạt")
    @app_commands.checks.cooldown(1, 3600.0, key=lambda i: (i.guild_id, i.user.id))
    async def daily_bonus(self, interaction: discord.Interaction):
        """Daily bonus reward between 5 AM - 10 AM with streak system"""
        await interaction.response.defer(ephemeral=True)
        
        user = interaction.user
        success, message, reward_data = await self.service.claim_daily_reward(user.id, user.name)
        
        if not success:
            embed = EconomyUI.create_error_embed("Lỗi", message)
        else:
            embed = EconomyUI.create_daily_reward_embed(reward_data, user)
            # Add current balance to embed
            current_balance = await self.service.get_user_balance(user.id)
            embed.set_field_at(
                len(embed.fields) - 1,
                name="💰 Hạt hiện tại",
                value=f"**{current_balance}**",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="tuido", description="Xem số hạt và túi đồ của bạn")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def balance_alias(self, interaction: discord.Interaction, user: discord.User = None):
        """Check balance and inventory"""
        await interaction.response.defer(ephemeral=False)
        
        target_user = user or interaction.user
        
        # Get balance
        seeds = await self.service.get_user_balance(target_user.id)
        
        # Get inventory (delegate to bot.inventory)
        inventory = await self.bot.inventory.get_all(target_user.id)
        
        # Get rod data from fishing module
        rod_data = None
        try:
            from cogs.fishing.mechanics.rod_system import get_rod_data
            fishing_rod = await get_rod_data(target_user.id)
            if fishing_rod:
                rod_level, rod_durability = fishing_rod
                rod_data = {
                    'name': f"Cần Cấp {rod_level}",
                    'level': rod_level,
                    'durability': rod_durability,
                    'max_durability': 120
                }
        except Exception as e:
            logger.error(f"Could not fetch rod data: {e}")
        
        # Get legendary fish caught (batch query instead of N+1)
        legendary_caught = []
        try:
            from cogs.fishing.constants import LEGENDARY_FISH_KEYS
            from database_manager import get_all_stats
            all_fishing_stats = await get_all_stats(target_user.id, "fishing")
            for fish_key in LEGENDARY_FISH_KEYS:
                if all_fishing_stats.get(f"{fish_key}_caught", 0) > 0:
                    legendary_caught.append(fish_key)
        except Exception as e:
            logger.error(f"Could not fetch legendary fish data: {e}")
        
        # Get VIP Data
        from core.services.vip_service import VIPEngine
        vip_data = await VIPEngine.get_vip_data(target_user.id)
        
        currency_data = {}
        try:
            from cogs.aquarium.models import UserAquarium
            aquarium = await UserAquarium.get_or_none(user_id=target_user.id)
            if aquarium:
                currency_data['leaf_coin'] = aquarium.leaf_coin
        except Exception as e:
            logger.error(f"Could not fetch leaf_coin: {e}")
        
        try:
            from cogs.seasonal.services import get_active_event, get_currency
            if interaction.guild:
                active = await get_active_event(interaction.guild.id)
                if active:
                    event_currency = await get_currency(interaction.guild.id, target_user.id, active["event_id"])
                    if event_currency > 0:
                        currency_data['event_currency'] = event_currency
                        from cogs.seasonal.core.event_manager import get_event_manager
                        event = get_event_manager().get_event(active["event_id"])
                        currency_data['event_emoji'] = event.currency_emoji if event else '🎫'
                        currency_data['event_name'] = event.currency_name if event else 'Token'
        except Exception as e:
            logger.error(f"Could not fetch event currency: {e}")
        
        # Create embed using fishing module
        from cogs.fishing.commands.inventory_display import create_inventory_embed
        embed = await create_inventory_embed(
            user=target_user,
            seeds=seeds,
            inventory=inventory,
            rod_data=rod_data,
            legendary_fish_caught=legendary_caught,
            vip_data=vip_data,
            currency_data=currency_data
        )
        
        await interaction.followup.send(embed=embed, ephemeral=False)
    
    @commands.command(name="tuido", description="Xem số hạt và túi đồ")
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def balance_alias_prefix(self, ctx, user: discord.User = None):
        """Check balance and inventory via prefix"""
        target_user = user or ctx.author
        
        seeds = await self.service.get_user_balance(target_user.id)
        inventory = await self.bot.inventory.get_all(target_user.id)
        
        rod_data = None
        try:
            from cogs.fishing.mechanics.rod_system import get_rod_data
            fishing_rod = await get_rod_data(target_user.id)
            if fishing_rod:
                rod_level, rod_durability = fishing_rod
                rod_data = {
                    'name': f"Cần Cấp {rod_level}",
                    'level': rod_level,
                    'durability': rod_durability,
                    'max_durability': 120
                }
        except Exception as e:
            logger.error(f"Could not fetch rod data: {e}")
        
        legendary_caught = []
        try:
            from cogs.fishing.constants import LEGENDARY_FISH_KEYS
            from database_manager import get_all_stats
            all_fishing_stats = await get_all_stats(target_user.id, "fishing")
            for fish_key in LEGENDARY_FISH_KEYS:
                if all_fishing_stats.get(f"{fish_key}_caught", 0) > 0:
                    legendary_caught.append(fish_key)
        except Exception as e:
            logger.error(f"Could not fetch legendary fish data: {e}")
        
        from core.services.vip_service import VIPEngine
        vip_data = await VIPEngine.get_vip_data(target_user.id)
        
        currency_data = {}
        try:
            from cogs.aquarium.models import UserAquarium
            aquarium = await UserAquarium.get_or_none(user_id=target_user.id)
            if aquarium:
                currency_data['leaf_coin'] = aquarium.leaf_coin
        except Exception as e:
            logger.error(f"Could not fetch leaf_coin: {e}")
        
        try:
            from cogs.seasonal.services import get_active_event, get_currency
            if ctx.guild:
                active = await get_active_event(ctx.guild.id)
                if active:
                    event_currency = await get_currency(ctx.guild.id, target_user.id, active["event_id"])
                    if event_currency > 0:
                        currency_data['event_currency'] = event_currency
                        from cogs.seasonal.core.event_manager import get_event_manager
                        event = get_event_manager().get_event(active["event_id"])
                        currency_data['event_emoji'] = event.currency_emoji if event else '🎫'
                        currency_data['event_name'] = event.currency_name if event else 'Token'
        except Exception as e:
            logger.error(f"Could not fetch event currency: {e}")
        
        from cogs.fishing.commands.inventory_display import create_inventory_embed
        embed = await create_inventory_embed(
            user=target_user,
            seeds=seeds,
            inventory=inventory,
            rod_data=rod_data,
            legendary_fish_caught=legendary_caught,
            vip_data=vip_data,
            currency_data=currency_data
        )
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="chuyen", description="Chuyển hạt cho người khác")
    @app_commands.describe(nguoi_nhan="Người nhận hạt", so_hat="Số hạt muốn chuyển")
    async def transfer_slash(
        self, 
        interaction: discord.Interaction, 
        nguoi_nhan: discord.Member,
        so_hat: app_commands.Range[int, 1, 1000000000]
    ):
        await interaction.response.defer()
        
        success, message, sender_bal, receiver_bal = await self.service.transfer_seeds(
            from_user_id=interaction.user.id,
            to_user_id=nguoi_nhan.id,
            amount=so_hat,
            from_username=interaction.user.name,
            to_username=nguoi_nhan.name
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Chuyển hạt thành công",
                description=f"Đã chuyển **{so_hat:,}** 🌾 cho {nguoi_nhan.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Số dư của bạn", value=f"{sender_bal:,} 🌾", inline=True)
            embed.add_field(name=f"Số dư của {nguoi_nhan.display_name}", value=f"{receiver_bal:,} 🌾", inline=True)
        else:
            embed = discord.Embed(
                title="❌ Không thể chuyển hạt",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed)
    
    @commands.command(name="chuyen", aliases=["give", "transfer"])
    async def transfer_prefix(self, ctx, nguoi_nhan: discord.Member, so_hat: int):
        success, message, sender_bal, receiver_bal = await self.service.transfer_seeds(
            from_user_id=ctx.author.id,
            to_user_id=nguoi_nhan.id,
            amount=so_hat,
            from_username=ctx.author.name,
            to_username=nguoi_nhan.name
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Chuyển hạt thành công",
                description=f"Đã chuyển **{so_hat:,}** 🌾 cho {nguoi_nhan.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Số dư của bạn", value=f"{sender_bal:,} 🌾", inline=True)
            embed.add_field(name=f"Số dư của {nguoi_nhan.display_name}", value=f"{receiver_bal:,} 🌾", inline=True)
        else:
            embed = discord.Embed(
                title="❌ Không thể chuyển hạt",
                description=message,
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="top", description="Xem bảng xếp hạng 10 người có nhiều hạt nhất")
    async def top_leaderboard_slash(self, interaction: discord.Interaction):
        """Show top 10 leaderboard (slash command)"""
        await interaction.response.defer(ephemeral=False)
        
        top_users = await self.service.get_leaderboard(10)
        embed = EconomyUI.create_leaderboard_embed(top_users, interaction.user)
        await interaction.followup.send(embed=embed)
    
    @commands.command(name="top", description="Xem bảng xếp hạng top 10")
    async def top_leaderboard_prefix(self, ctx):
        """Show top 10 leaderboard (prefix command)"""
        top_users = await self.service.get_leaderboard(10)
        embed = EconomyUI.create_leaderboard_embed(top_users, ctx.author)
        await ctx.send(embed=embed)
    
    @commands.command(name="themhat", description="Thêm hạt cho user (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_seeds_admin(self, ctx, user: discord.User, amount: int):
        """Add seeds to a user (Admin only)"""
        success, message = await self.service.admin_add_seeds(user.id, amount, ctx.author.id, ctx.author.name)
        
        if success:
            new_balance = await self.service.get_user_balance(user.id)
            embed = EconomyUI.create_admin_add_seeds_embed(user, amount, new_balance, ctx.author)
            await ctx.send(embed=embed)
        else:
            embed = EconomyUI.create_error_embed("Lỗi", message)
            await ctx.send(embed=embed)
    
    @app_commands.command(name="themhat", description="Thêm hạt cho user (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user="Người nhận hạt",
        amount="Số lượng hạt muốn thêm"
    )
    async def add_seeds_admin_slash(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Add seeds to a user (Admin only) - Slash command"""
        await interaction.response.defer(ephemeral=True)
        
        success, message = await self.service.admin_add_seeds(user.id, amount, interaction.user.id, interaction.user.name)
        
        if success:
            new_balance = await self.service.get_user_balance(user.id)
            embed = EconomyUI.create_admin_add_seeds_embed(user, amount, new_balance, interaction.user)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = EconomyUI.create_error_embed("Lỗi", message)
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # ==================== EVENTS ====================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Reward seeds for chat activity"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # Skip commands
        if message.content.startswith(('!', '/')):
            return
        
        # Check cooldown
        user_id = message.author.id
        now = datetime.now().timestamp()
        
        if user_id in self.chat_cooldowns:
            last_reward = self.chat_cooldowns[user_id]
            if now - last_reward < 60:  # 60 seconds cooldown
                return
        
        # Process reward
        reward = await self.service.process_chat_reward(
            user_id, message.author.name, message.guild.id, message.channel.id
        )
        
        if reward:
            self.chat_cooldowns[user_id] = now
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Reward seeds when someone reacts to a message"""
        if user.bot:
            return
        
        message = reaction.message
        if not message.author or user.id == message.author.id:
            return
        
        if not message.guild:
            return
        
        # Check cooldown for message author
        author_id = message.author.id
        now = datetime.now().timestamp()
        cooldown_key = f"{author_id}_reaction"
        
        if cooldown_key in self.reaction_cooldowns:
            last_reward = self.reaction_cooldowns[cooldown_key]
            if now - last_reward < 120:  # 120 seconds for reactions
                return
        
        # Process reward (same as chat reward)
        reward = await self.service.process_chat_reward(
            author_id, message.author.name, message.guild.id, message.channel.id
        )
        
        if reward:
            self.reaction_cooldowns[cooldown_key] = now
    
    # ==================== TASKS ====================
    
    @tasks.loop(minutes=10)
    async def voice_reward_task(self):
        """Check voice channels and reward members"""
        try:
            for guild in self.bot.guilds:
                is_buff_active = await self.repository.is_harvest_buff_active(guild.id)
                afk_channel_id = guild.afk_channel.id if guild.afk_channel else None
                
                for voice_channel in guild.voice_channels:
                    if voice_channel.id == afk_channel_id:
                        continue
                    
                    speaking_members = [m for m in voice_channel.members 
                                      if not m.bot and m.voice and m.voice.self_mute == False]
                    
                    if not speaking_members:
                        continue
                    
                    party_size = len(speaking_members)
                    music_bot_playing = any(
                        m.bot and m.voice and not m.voice.self_mute 
                        for m in voice_channel.members
                    )
                    
                    for member in speaking_members:
                        await self.service.process_voice_reward(
                            member.id, member.name, guild.id, party_size, music_bot_playing
                        )
        
        except Exception as e:
            logger.error(f"[ECONOMY] Voice reward error: {e}", exc_info=True)
    
    @voice_reward_task.before_loop
    async def before_voice_reward_task(self):
        """Wait for bot to be ready"""
        await self.bot.wait_until_ready()
    
    # Weekly welfare task (simplified)
    @tasks.loop(time=time(hour=12, minute=0))
    async def weekly_welfare_task(self):
        """Weekly welfare for poor active users"""
        try:
            if datetime.now().weekday() != 6:  # Sunday only
                return
            
            logger.info("[WELFARE] Starting weekly welfare distribution...")
            
            # Simplified welfare logic - give 500 seeds to users with <1000 seeds
            # who were active in last 7 days
            # (Full implementation would need more complex queries)
            
            logger.info("[WELFARE] Weekly distribution completed")
        
        except Exception as e:
            logger.error(f"[WELFARE] Error during distribution: {e}", exc_info=True)
    
    @weekly_welfare_task.before_loop
    async def before_weekly_welfare_task(self):
        """Wait for bot to be ready"""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

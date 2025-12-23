import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, time
import random
import asyncio
from database_manager import (
    db_manager,
    get_user_balance,
    add_seeds,
    get_or_create_user,
    get_leaderboard,
    batch_update_seeds
)
from core.logger import setup_logger

logger = setup_logger("EconomyCog", "cogs/economy.log")

DB_PATH = "./data/database.db"

# Constants
DAILY_BONUS = 10  # Seeds received from /chao
DAILY_WINDOW_START = 5  # 5 AM
DAILY_WINDOW_END = 12  # 12 AM
CHAT_REWARD_MIN = 1
CHAT_REWARD_MAX = 3
CHAT_REWARD_COOLDOWN = 60  # seconds
VOICE_REWARD_INTERVAL = 10  # minutes
VOICE_REWARD = 2  # Seeds per 10 minutes in voice

class EconomyCog(commands.Cog):
    """Cog handling the economy system.

    Manages daily rewards, chat/voice activity rewards, and leaderboards.
    """
    def __init__(self, bot):
        self.bot = bot
        self.chat_cooldowns = {}  # {user_id: last_reward_time}
        self.reaction_cooldowns = {}  # {user_id: last_reaction_reward_time}
        self.voice_reward_task.start()
        self.voice_affinity_task.start()

    def cog_unload(self):
        self.voice_reward_task.cancel()
        self.voice_affinity_task.cancel()

    # ==================== HELPER FUNCTIONS ====================
    async def get_or_create_user_local(self, user_id: int, username: str):
        """Retrieves or creates a user in the local database wrapper.

        Args:
            user_id (int): The Discord user ID.
            username (str): The username.

        Returns:
            tuple: User data.
        """
        return await get_or_create_user(user_id, username)

    async def is_harvest_buff_active(self, guild_id: int) -> bool:
        """Checks if the 24h harvest buff is active for the guild.

        Args:
            guild_id (int): The Guild ID.

        Returns:
            bool: True if buff is active and not expired.
        """
        try:
            result = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"harvest_buff_{guild_id}",
                cache_ttl=60
            )
            
            if not result or not result[0]:
                return False
            
            buff_until = datetime.fromisoformat(result[0])
            return datetime.now() < buff_until
        except Exception as e:
            return False

    async def add_seeds_local(self, user_id: int, amount: int):
        """Add seeds to user"""
        balance_before = await get_user_balance(user_id)
        await add_seeds(user_id, amount)
        balance_after = balance_before + amount
        logger.info(
            f"[ECONOMY] [SEED_UPDATE] user_id={user_id} seed_change={amount} "
            f"balance_before={balance_before} balance_after={balance_after}"
        )

    async def get_user_balance_local(self, user_id: int) -> int:
        """Get user balance (seeds only)"""
        return await get_user_balance(user_id)

    async def get_leaderboard_local(self, limit: int = 10) -> list:
        """Get top players by seeds"""
        return await get_leaderboard(limit)

    async def update_last_daily(self, user_id: int):
        """Updates the timestamp of the last daily reward claim.

        Args:
            user_id (int): The Discord user ID.
        """
        await db_manager.modify(
            "UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")

    async def update_last_chat_reward(self, user_id: int):
        """Update last chat reward time"""
        await db_manager.modify(
            "UPDATE users SET last_chat_reward = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")

    async def get_last_daily(self, user_id: int) -> datetime:
        """Get last daily reward time"""
        result = await db_manager.fetchone(
            "SELECT last_daily FROM users WHERE user_id = ?",
            (user_id,)
        )
        if result and result[0]:
            return datetime.fromisoformat(result[0])
        return None

    def is_daily_window(self) -> bool:
        """Check if current time is within daily reward window (5 AM - 10 AM)"""
        now = datetime.now()
        return DAILY_WINDOW_START <= now.hour < DAILY_WINDOW_END

    async def get_excluded_channels(self, guild_id: int) -> list:
        """Get list of excluded channels for a guild"""
        try:
            result = await db_manager.fetchone(
                "SELECT logs_channel_id, exclude_chat_channels FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"excluded_channels_{guild_id}",
                cache_ttl=600
            )
            
            excluded = []
            if result:
                if result[0]:  # logs_channel_id
                    excluded.append(result[0])
                
                # Parse exclude_chat_channels (JSON format)
                if result[1]:
                    try:
                        import json
                        parsed = json.loads(result[1])
                        excluded.extend(parsed)
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
            
            return excluded
        except Exception as e:
            return []

    # ==================== COMMANDS ====================

    @app_commands.command(name="chao", description="Chào buổi sáng (5h-10h) để nhận hạt")
    async def daily_bonus(self, interaction: discord.Interaction):
        """Daily bonus reward between 5 AM - 10 AM"""
        await interaction.response.defer(ephemeral=True)
        
        # Check time window
        if not self.is_daily_window():
            now = datetime.now()
            await interaction.followup.send(
                f"❌ Chỉ nhận hạt từ 5h tới 10h sáng!\n"
                f"Giờ hiện tại: {now.strftime('%H:%M')}",
                ephemeral=True
            )
            return
        
        # Get or create user
        user = interaction.user
        await self.get_or_create_user_local(user.id, user.name)
        
        # Check if already claimed today
        last_daily = await self.get_last_daily(user.id)
        if last_daily:
            today = datetime.now().date()
            if last_daily.date() == today:
                await interaction.followup.send(
                    f"❌ Bạn đã nhận hạt hôm nay rồi! Quay lại vào ngày mai.",
                    ephemeral=True
                )
                return
        
        # Award seeds
        await self.add_seeds_local(user.id, DAILY_BONUS)
        await self.update_last_daily(user.id)
        
        # Get new balance
        seeds = await self.get_user_balance_local(user.id)
        
        embed = discord.Embed(
            title="☀️ Chào buổi sáng!",
            description=f"Bạn nhận được **{DAILY_BONUS} hạt**",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Hạt hiện tại", value=f"**{seeds}**", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tuido", description="Xem số hạt và túi đồ của bạn")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    async def balance_alias(self, interaction: discord.Interaction, user: discord.User = None):
        """Check balance and inventory"""
        await interaction.response.defer(ephemeral=False)
        
        target_user = user or interaction.user
        await self.get_or_create_user_local(target_user.id, target_user.name)
        
        seeds = await self.get_user_balance_local(target_user.id)
        
        # Get inventory
        from database_manager import get_inventory, get_stat
        inventory = await get_inventory(target_user.id)
        
        # Get rod data from fishing module
        rod_data = None
        try:
            from cogs.fishing.mechanics.rod_system import get_rod_data
            fishing_rod = await get_rod_data(target_user.id)
            if fishing_rod:
                # fishing_rod is (level, durability) tuple
                rod_level, rod_durability = fishing_rod
                rod_data = {
                    'name': f"Cần Cấp {rod_level}", # Fallback name logic if not available
                    'level': rod_level,
                    'durability': rod_durability,
                    'max_durability': 120 # Default or fetch constant
                }
        except Exception as e:
            logger.error(f"Could not fetch rod data: {e}")
        
        # Get legendary fish caught
        legendary_caught = []
        try:
            from cogs.fishing.constants import LEGENDARY_FISH_KEYS
            for fish_key in LEGENDARY_FISH_KEYS:
                caught = await get_stat(target_user.id, "fishing", f"{fish_key}_caught")
                if caught and caught > 0:
                    legendary_caught.append(fish_key)
        except Exception as e:
            logger.error(f"Could not fetch legendary fish data: {e}")
        
        # Create embed using new module
        from cogs.fishing.commands.inventory_display import create_inventory_embed
        embed = await create_inventory_embed(
            user=target_user,
            seeds=seeds,
            inventory=inventory,
            rod_data=rod_data,
            legendary_fish_caught=legendary_caught
        )
        
        await interaction.followup.send(embed=embed, ephemeral=False)

    @commands.command(name="tuido", description="Xem số hạt và túi đồ")
    async def balance_alias_prefix(self, ctx, user: discord.User = None):
        """Check balance and inventory via prefix"""
        target_user = user or ctx.author
        await self.get_or_create_user_local(target_user.id, target_user.name)
        
        seeds = await self.get_user_balance_local(target_user.id)
        
        # Get inventory
        from database_manager import get_inventory, get_stat
        inventory = await get_inventory(target_user.id)
        
        # Get rod data from fishing module
        rod_data = None
        try:
            from cogs.fishing.mechanics.rod_system import get_rod_data
            fishing_rod = await get_rod_data(target_user.id)
            if fishing_rod:
                # fishing_rod is (level, durability) tuple
                rod_level, rod_durability = fishing_rod
                rod_data = {
                    'name': f"Cần Cấp {rod_level}", # Fallback name logic if not available
                    'level': rod_level,
                    'durability': rod_durability,
                    'max_durability': 120 # Default or fetch constant
                }
        except Exception as e:
            logger.error(f"Could not fetch rod data: {e}")
        
        # Get legendary fish caught
        legendary_caught = []
        try:
            from cogs.fishing.constants import LEGENDARY_FISH_KEYS
            for fish_key in LEGENDARY_FISH_KEYS:
                caught = await get_stat(target_user.id, "fishing", f"{fish_key}_caught")
                if caught and caught > 0:
                    legendary_caught.append(fish_key)
        except Exception as e:
            logger.error(f"Could not fetch legendary fish data: {e}")
        
        # Create embed using new module
        from cogs.fishing.commands.inventory_display import create_inventory_embed
        embed = await create_inventory_embed(
            user=target_user,
            seeds=seeds,
            inventory=inventory,
            rod_data=rod_data,
            legendary_fish_caught=legendary_caught
        )
        
        await ctx.send(embed=embed)

    async def leaderboard(self, interaction: discord.Interaction):
        """Show leaderboard"""
        await interaction.response.defer(ephemeral=True)
        
        top_users = await self.get_leaderboard_local(10)
        
        if not top_users:
            await interaction.followup.send("❌ Chưa có ai trong bảng xếp hạng!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Bảng Xếp Hạng Hạt",
            color=discord.Color.gold()
        )
        
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, username, seeds) in enumerate(top_users, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}."
            ranking_text += f"{medal} **{username}** - {seeds} Hạt\n"
        
        embed.description = ranking_text
        embed.set_footer(text="Cập nhật hàng ngày • Xếp hạng dựa trên tổng hạt")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _create_leaderboard_embed(self, top_users, requester: discord.User):
        """Create a premium leaderboard embed"""
        if not top_users:
            return None

        # Top 1 user details
        top1_id, top1_name, top1_balance = top_users[0]
        
        embed = discord.Embed(
            title="👑 **BẢNG VÀNG ĐẠI GIA (TOP RICH)** 👑",
            description=f"Vin danh những đại gia giàu nhất **Bên Hiên Nhà**.",
            color=0xFFD700, # Gold
            timestamp=datetime.now()
        )
        
        # Try to get top 1 user avatar
        try:
            top1_user = self.bot.get_user(top1_id)
            if not top1_user:
                top1_user = await self.bot.fetch_user(top1_id)
            if top1_user and top1_user.avatar:
                embed.set_thumbnail(url=top1_user.avatar.url)
        except Exception:
            pass

        # === TOP 3 (VIP Section) ===
        top3_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx in range(min(3, len(top_users))):
            user_id, username, balance = top_users[idx]
            medal = medals[idx]
            # Bold name, nice formatting
            top3_text += f"{medal} **{username}**\n╚═ **{balance:,}** 🌱\n\n"
            
        embed.add_field(name="🏆 **TAM ĐẠI PHÚ HỘ**", value=top3_text, inline=True)

        # === RANKS 4-10 (List Section) ===
        if len(top_users) > 3:
            others_text = "```yaml\n" # Use yaml for semantic highlighting (keys are colored)
            for idx in range(3, len(top_users)):
                user_id, username, balance = top_users[idx]
                # Format: 4. name ... balance
                # Truncate long names
                display_name = (username[:12] + '..') if len(username) > 12 else username
                others_text += f"{idx+1}. {display_name:<14} {balance:,} 🌱\n"
            others_text += "```"
            embed.add_field(name="📜 **CHIẾN THẦN TÍCH LŨY**", value=others_text, inline=False)
            
        # Footer
        embed.set_footer(text=f"Yêu cầu bởi {requester.name}", icon_url=requester.avatar.url if requester.avatar else None)
        # Let's verify if I should add image. Maybe unnecessary. Removing set_image for now to keep it clean.
        
        return embed

    @app_commands.command(name="top", description="Xem bảng xếp hạng 10 người có nhiều hạt nhất")
    async def top_leaderboard_slash(self, interaction: discord.Interaction):
        """Show top 10 leaderboard (slash command)"""
        await interaction.response.defer(ephemeral=False)
        
        top_users = await self.get_leaderboard_local(10)
        
        if not top_users:
            await interaction.followup.send("❌ Chưa có ai trong bảng xếp hạng!", ephemeral=True)
            return
            
        embed = await self._create_leaderboard_embed(top_users, interaction.user)
        await interaction.followup.send(embed=embed)

    @commands.command(name="top", description="Xem bảng xếp hạng top 10")
    async def top_leaderboard_prefix(self, ctx):
        """Show top 10 leaderboard (prefix command)"""
        top_users = await self.get_leaderboard_local(10)
        
        if not top_users:
            await ctx.send("❌ Chưa có ai trong bảng xếp hạng!")
            return
        
        embed = await self._create_leaderboard_embed(top_users, ctx.author)
        await ctx.send(embed=embed)

    @commands.command(name="themhat", description="Thêm hạt cho user (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_seeds_admin(self, ctx, user: discord.User, amount: int):
        """Add seeds to a user (Admin only)"""
        # Validate amount
        if amount <= 0:
            await ctx.send("❌ Số lượng phải lớn hơn 0!")
            return
        
        # Get or create user
        await self.get_or_create_user_local(user.id, user.name)
        
        # Add seeds
        await self.add_seeds_local(user.id, amount)
        
        # Get new balance
        new_balance = await self.get_user_balance_local(user.id)
        
        embed = discord.Embed(
            title="Thêm Hạt Thành Công",
            color=discord.Color.green()
        )
        embed.add_field(name="Người nhận", value=f"**{user.name}**", inline=False)
        embed.add_field(name="Hạt thêm", value=f"**+{amount}**", inline=True)
        embed.add_field(name="Số dư mới", value=f"**{new_balance}**", inline=True)
        embed.set_footer(text=f"Thực hiện bởi {ctx.author.name}")
        
        await ctx.send(embed=embed)
        logger.info(
            f"[ADMIN] [SEED_GRANT] actor={ctx.author.name} actor_id={ctx.author.id} "
            f"target={user.name} target_id={user.id} amount={amount}"
        )

    @app_commands.command(name="themhat", description="Thêm hạt cho user (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user="Người nhận hạt",
        amount="Số lượng hạt muốn thêm"
    )
    async def add_seeds_admin_slash(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Add seeds to a user (Admin only) - Slash command"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate amount
        if amount <= 0:
            await interaction.followup.send("❌ Số lượng phải lớn hơn 0!", ephemeral=True)
            return
        
        # Get or create user
        await self.get_or_create_user_local(user.id, user.name)
        
        # Add seeds
        await self.add_seeds_local(user.id, amount)
        
        # Get new balance
        new_balance = await self.get_user_balance_local(user.id)
        
        embed = discord.Embed(
            title="Thêm Hạt Thành Công",
            color=discord.Color.green()
        )
        embed.add_field(name="Người nhận", value=f"**{user.name}**", inline=False)
        embed.add_field(name="Hạt thêm", value=f"**+{amount}**", inline=True)
        embed.add_field(name="Số dư mới", value=f"**{new_balance}**", inline=True)
        embed.set_footer(text=f"Thực hiện bởi {interaction.user.name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(
            f"[ADMIN] [SEED_GRANT] actor={interaction.user.name} actor_id={interaction.user.id} "
            f"target={user.name} target_id={user.id} amount={amount}"
        )

    # ==================== EVENTS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Reward seeds for chat activity (excludes bot commands)"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # CRITICAL FIX: Skip chat rewards when user invokes a command
        # Check if message starts with command prefix to avoid concurrent DB writes
        if message.content.startswith('!') or message.content.startswith('/'):
            return
        
        # Get excluded channels
        excluded_channels = await self.get_excluded_channels(message.guild.id)
        
        # Don't reward in excluded channels
        if message.channel.id in excluded_channels:
            return
        
        # Check cooldown
        user_id = message.author.id
        now = datetime.now().timestamp()
        
        if user_id in self.chat_cooldowns:
            last_reward = self.chat_cooldowns[user_id]
            if now - last_reward < CHAT_REWARD_COOLDOWN:
                return
        
        # Get or create user
        await self.get_or_create_user_local(user_id, message.author.name)
        
        # Award random seeds
        reward = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
        
        # Check if harvest buff is active (x2 multiplier)
        is_buff_active = await self.is_harvest_buff_active(message.guild.id)
        if is_buff_active:
            reward = reward * 2
        
        logger.info(
            f"[ECONOMY] [CHAT_REWARD] user_id={user_id} username={message.author.name} "
            f"reward={reward} buff_active={is_buff_active}"
        )
        
        await self.add_seeds_local(user_id, reward)
        await self.update_last_chat_reward(user_id)
        
        # Update cooldown
        self.chat_cooldowns[user_id] = now

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Reward seeds when someone reacts to a message or forum post"""
        # Don't reward bot reactions
        if user.bot:
            return
        
        # Get message author (the one who posted the message/forum post)
        message = reaction.message
        if not message.author:
            return
        
        # Don't reward self-reactions
        if user.id == message.author.id:
            return
        
        # Must be in a guild
        if not message.guild:
            return
        
        # Get excluded channels
        excluded_channels = await self.get_excluded_channels(message.guild.id)
        
        # Check if channel is excluded
        if message.channel.id in excluded_channels:
            return
        
        # Check if it's a forum post or regular message
        # Forum posts are in ThreadChannel
        is_forum_post = isinstance(message.channel, discord.Thread) and message.channel.parent and hasattr(message.channel.parent, 'type') and message.channel.parent.type == discord.ChannelType.forum
        
        # Check cooldown for the message author (not the reactor)
        author_id = message.author.id
        now = datetime.now().timestamp()
        
        cooldown_key = f"{author_id}_reaction"
        if cooldown_key in self.reaction_cooldowns:
            last_reward = self.reaction_cooldowns[cooldown_key]
            # Use longer cooldown for reactions (120 seconds)
            if now - last_reward < 120:
                return
        
        # Get or create user
        await self.get_or_create_user_local(author_id, message.author.name)
        
        # Award seeds - same as chat reward
        reward = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
        
        # Check if harvest buff is active
        is_buff_active = await self.is_harvest_buff_active(message.guild.id)
        if is_buff_active:
            reward = reward * 2
        
        # Log with context
        location = "forum_post" if is_forum_post else "message"
        logger.info(
            f"[ECONOMY] [REACTION_REWARD] user_id={author_id} username={message.author.name} "
            f"reward={reward} buff_active={is_buff_active} location={location}"
        )
        
        await self.add_seeds_local(author_id, reward)
        self.reaction_cooldowns[cooldown_key] = now

    @tasks.loop(minutes=VOICE_REWARD_INTERVAL)
    async def voice_reward_task(self):
        """Check voice channels and reward members every 5 minutes - ONLY if speaking"""
        try:
            for guild in self.bot.guilds:
                is_buff_active = await self.is_harvest_buff_active(guild.id)
                
                for voice_channel in guild.voice_channels:
                    # Get members in voice (exclude bots) who are SPEAKING
                    speaking_members = [m for m in voice_channel.members if not m.bot and m.voice and m.voice.self_mute == False]
                    
                    if not speaking_members:
                        continue
                    
                    # Award seeds to each speaking member
                    for member in speaking_members:
                        await self.get_or_create_user_local(member.id, member.name)
                        
                        # Get user rod level (affects reward bonus)
                        try:
                            # get_rod_data returns (level, durability) tuple, NOT dict
                            rod_data = await self.bot.get_cog("FishingCog").get_rod_data(member.id)
                            if rod_data:
                                rod_level, rod_durability = rod_data
                            else:
                                rod_level = 0
                        except Exception as e:
                            rod_level = 0
                            # logger.error(f"[ECONOMY] Error fetching rod data for {member.name}: {e}")
                        
                        reward = VOICE_REWARD
                        if is_buff_active:
                            reward = reward * 2
                        
                        logger.info(
                            f"[ECONOMY] [VOICE_REWARD] user_id={member.id} username={member.name} "
                            f"reward={reward} buff_active={is_buff_active}"
                        )
                        await self.add_seeds_local(member.id, reward)
        
        except Exception as e:
            logger.error(f"[ECONOMY] Voice reward error: {e}", exc_info=True)

    @tasks.loop(minutes=VOICE_REWARD_INTERVAL)
    async def voice_affinity_task(self):
        """Increase affinity between members speaking in the same voice channel"""
        try:
            relationship_cog = self.bot.get_cog("RelationshipCog")
            if not relationship_cog:
                return
            
            for guild in self.bot.guilds:
                for voice_channel in guild.voice_channels:
                    # Get members in voice (exclude bots) who are SPEAKING
                    speaking_members = [m for m in voice_channel.members if not m.bot and m.voice and m.voice.self_mute == False]
                    
                    # Need at least 2 members to increase affinity
                    if len(speaking_members) < 2:
                        continue
                    
                    # Increase affinity between all pairs of speaking members
                    for i, member1 in enumerate(speaking_members):
                        for member2 in speaking_members[i+1:]:
                            # Add 1 affinity point per person pair in voice
                            await relationship_cog.add_affinity(member1.id, member2.id, 1)
                            logger.info(
                                f"[AFFINITY] [VOICE] user1_id={member1.id} user1={member1.name} "
                                f"user2_id={member2.id} user2={member2.name} affinity_change=+1"
                            )
        
        except Exception as e:
            logger.error(f"[ECONOMY] Voice affinity task error: {e}", exc_info=True)

    @voice_reward_task.before_loop
    async def before_voice_reward_task(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()

    @voice_affinity_task.before_loop
    async def before_voice_affinity_task(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

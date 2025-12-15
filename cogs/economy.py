import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, time
import random
import asyncio

DB_PATH = "./data/database.db"

# Constants
DAILY_BONUS = 10  # Hạt nhận từ /chao
DAILY_WINDOW_START = 5  # 5 AM
DAILY_WINDOW_END = 10  # 10 AM
CHAT_REWARD_MIN = 1
CHAT_REWARD_MAX = 3
CHAT_REWARD_COOLDOWN = 60  # seconds
VOICE_REWARD_INTERVAL = 5  # minutes
VOICE_REWARD = 5  # Hạt mỗi 5 phút trong voice

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_cooldowns = {}  # {user_id: last_reward_time}
        self.reaction_cooldowns = {}  # {user_id: last_reaction_reward_time}
        self.voice_reward_task.start()

    def cog_unload(self):
        self.voice_reward_task.cancel()

    # ==================== HELPER FUNCTIONS ====================
    async def get_or_create_user(self, user_id: int, username: str):
        """Get or create user in economy_users table"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                user = await cursor.fetchone()
            
            if not user:
                await db.execute(
                    "INSERT INTO economy_users (user_id, username, seeds) VALUES (?, ?, ?)",
                    (user_id, username, 0)
                )
                await db.commit()
            return user

    async def is_harvest_buff_active(self, guild_id: int) -> bool:
        """Check if 24h harvest buff is active"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
            
            if not row or not row[0]:
                return False
            
            buff_until = datetime.fromisoformat(row[0])
            return datetime.now() < buff_until
        except:
            return False

    async def add_seeds(self, user_id: int, amount: int):
        """Add seeds to user"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE economy_users SET seeds = seeds + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def get_user_balance(self, user_id: int) -> int:
        """Get user balance (seeds only)"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT seeds FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_leaderboard(self, limit: int = 10) -> list:
        """Get top players by seeds"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT user_id, username, seeds FROM economy_users ORDER BY seeds DESC LIMIT ?",
                (limit,)
            ) as cursor:
                return await cursor.fetchall()

    async def update_last_daily(self, user_id: int):
        """Update last daily reward time"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE economy_users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def update_last_chat_reward(self, user_id: int):
        """Update last chat reward time"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE economy_users SET last_chat_reward = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def get_last_daily(self, user_id: int) -> datetime:
        """Get last daily reward time"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT last_daily FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if row and row[0]:
                return datetime.fromisoformat(row[0])
            return None

    def is_daily_window(self) -> bool:
        """Check if current time is within daily reward window (5 AM - 10 AM)"""
        now = datetime.now()
        return DAILY_WINDOW_START <= now.hour < DAILY_WINDOW_END

    async def get_excluded_channels(self, guild_id: int) -> list:
        """Get list of excluded channels for a guild"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT logs_channel_id, exclude_chat_channels FROM server_config WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    config = await cursor.fetchone()
            
            excluded = []
            if config:
                if config[0]:  # logs_channel_id
                    excluded.append(config[0])
                
                # Parse exclude_chat_channels (JSON format)
                if config[1]:
                    try:
                        import json
                        parsed = json.loads(config[1])
                        excluded.extend(parsed)
                    except:
                        pass
            
            return excluded
        except:
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
        await self.get_or_create_user(user.id, user.name)
        
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
        await self.add_seeds(user.id, DAILY_BONUS)
        await self.update_last_daily(user.id)
        
        # Get new balance
        seeds = await self.get_user_balance(user.id)
        
        embed = discord.Embed(
            title="☀️ Chào buổi sáng!",
            description=f"Bạn nhận được **{DAILY_BONUS} hạt**",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Hạt hiện tại", value=f"**{seeds}**", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="bal", description="Xem số hạt hiện tại")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    async def balance(self, interaction: discord.Interaction, user: discord.User = None):
        """Check balance"""
        await interaction.response.defer(ephemeral=True)
        
        target_user = user or interaction.user
        await self.get_or_create_user(target_user.id, target_user.name)
        
        seeds = await self.get_user_balance(target_user.id)
        
        embed = discord.Embed(
            title=f"💰 Số dư của {target_user.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="🌱 Hạt", value=f"**{seeds}**", inline=False)
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tuido", description="Xem số hạt hiện tại (alias của /bal)")
    async def balance_alias(self, interaction: discord.Interaction):
        """Alias for /bal command"""
        await self.balance(interaction)

    @app_commands.command(name="top", description="Xem bảng xếp hạng hạt")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show leaderboard"""
        await interaction.response.defer(ephemeral=True)
        
        top_users = await self.get_leaderboard(10)
        
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

    # ==================== EVENTS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Reward seeds for chat activity"""
        if message.author.bot:
            return
        
        if not message.guild:
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
        await self.get_or_create_user(user_id, message.author.name)
        
        # Award random seeds
        reward = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
        
        # Check if harvest buff is active (x2 multiplier)
        is_buff_active = await self.is_harvest_buff_active(message.guild.id)
        if is_buff_active:
            reward = reward * 2
            print(f"[ECONOMY] 🔥 HARVEST BUFF ACTIVE! {message.author.name} earned {reward} seeds from chat")
        else:
            print(f"[ECONOMY] {message.author.name} earned {reward} seeds from chat")
        
        await self.add_seeds(user_id, reward)
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
        await self.get_or_create_user(author_id, message.author.name)
        
        # Award seeds - same as chat reward
        reward = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
        
        # Check if harvest buff is active
        is_buff_active = await self.is_harvest_buff_active(message.guild.id)
        if is_buff_active:
            reward = reward * 2
        
        # Log with context
        location = f"forum post" if is_forum_post else "message"
        if is_buff_active:
            print(f"[ECONOMY] 🔥 HARVEST BUFF! {message.author.name} earned {reward} seeds from emoji reaction on {location}")
        else:
            print(f"[ECONOMY] {message.author.name} earned {reward} seeds from emoji reaction on {location}")
        
        await self.add_seeds(author_id, reward)
        self.reaction_cooldowns[cooldown_key] = now

    @tasks.loop(minutes=VOICE_REWARD_INTERVAL)
    async def voice_reward_task(self):
        """Check voice channels and reward members every 5 minutes"""
        try:
            for guild in self.bot.guilds:
                is_buff_active = await self.is_harvest_buff_active(guild.id)
                
                for voice_channel in guild.voice_channels:
                    # Get members in voice (exclude bots)
                    members = [m for m in voice_channel.members if not m.bot]
                    
                    if not members:
                        continue
                    
                    # Award seeds to each member
                    for member in members:
                        await self.get_or_create_user(member.id, member.name)
                        
                        reward = VOICE_REWARD
                        if is_buff_active:
                            reward = reward * 2
                            print(f"[ECONOMY] 🔥 HARVEST BUFF! {member.name} earned {reward} seeds from voice (x2)")
                        else:
                            print(f"[ECONOMY] {member.name} earned {reward} seeds from voice")
                        
                        await self.add_seeds(member.id, reward)
        
        except Exception as e:
            print(f"[ECONOMY] Voice reward error: {e}")

    @voice_reward_task.before_loop
    async def before_voice_reward_task(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

"""Disboard Bump Reminder Cog

Automatically reminds users to bump the server on Disboard every 3 hours.
Uses persistent start_time from database to survive bot restarts.
"""

import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timedelta
from core.logger import setup_logger

logger = setup_logger("DisboardReminder", "cogs/disboard.log")

DB_PATH = "./data/database.db"
BUMP_INTERVAL_HOURS = 3
DISBOARD_BOT_ID = 302050872383242240  # Official DISBOARD bot ID


class DisboardReminderCog(commands.Cog):
    """Automatic Disboard bump reminder system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bump_reminder_task.start()
        logger.info("[DISBOARD] Cog loaded, starting bump reminder task")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.bump_reminder_task.cancel()
        logger.info("[DISBOARD] Cog unloaded, stopped bump reminder task")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for DISBOARD bump confirmation and auto-update timer.
        
        When user successfully bumps via /bump, DISBOARD replies with
        "Bump done! :thumbsup:" - we detect this and reset the timer.
        """
        # Ignore messages not from DISBOARD bot
        if message.author.id != DISBOARD_BOT_ID:
            return
        
        # Check if this is a bump confirmation
        # DISBOARD sends embed or regular message with "Bump done"
        is_bump_confirm = False
        
        if message.embeds:
            # Check embed description/title
            for embed in message.embeds:
                embed_text = (embed.description or "") + (embed.title or "")
                if "bump done" in embed_text.lower() or ":thumbsup:" in embed_text.lower():
                    is_bump_confirm = True
                    break
        
        if message.content and "bump done" in message.content.lower():
            is_bump_confirm = True
        
        if not is_bump_confirm:
            return
        
        # Get guild and check if bump reminder is configured
        guild = message.guild
        if not guild:
            return
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if guild has bump reminder configured
                async with db.execute(
                    "SELECT bump_channel_id FROM server_config WHERE guild_id = ?",
                    (guild.id,)
                ) as cursor:
                    row = await cursor.fetchone()
                
                if not row or not row[0]:
                    # Bump reminder not configured for this guild, ignore
                    return
                
                # Update bump_start_time to now
                from datetime import datetime
                now = datetime.now().isoformat()
                await db.execute(
                    "UPDATE server_config SET bump_start_time = ? WHERE guild_id = ?",
                    (now, guild.id)
                )
                await db.commit()
                
                logger.info(
                    f"[BUMP_AUTO_DETECT] Guild {guild.name} ({guild.id}): "
                    f"Detected successful bump, updated timer to {now}"
                )
        
        except Exception as e:
            logger.error(f"[BUMP_AUTO_DETECT] Error updating timer for guild {guild.id}: {e}")
            import traceback
            traceback.print_exc()
    
    @tasks.loop(minutes=30)
    async def bump_reminder_task(self):
        """Check all guilds and send bump reminders if 3 hours have elapsed.
        
        Runs every 30 minutes to check for bump opportunities.
        Uses persistent bump_start_time to calculate next bump time.
        """
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Query all guilds with bump channel configured
                async with db.execute(
                    "SELECT guild_id, bump_channel_id, bump_start_time FROM server_config WHERE bump_channel_id IS NOT NULL"
                ) as cursor:
                    configs = await cursor.fetchall()
                
                if not configs:
                    logger.debug("[BUMP_CHECK] No guilds with bump reminder configured")
                    return
                
                logger.info(f"[BUMP_CHECK] Checking {len(configs)} guild(s) for bump reminder")
                
                for guild_id, bump_channel_id, bump_start_time in configs:
                    await self._check_and_send_bump(db, guild_id, bump_channel_id, bump_start_time)
        
        except Exception as e:
            logger.error(f"[BUMP_CHECK] Unexpected error in bump_reminder_task: {e}")
            import traceback
            traceback.print_exc()
    
    async def _check_and_send_bump(self, db, guild_id, bump_channel_id, bump_start_time):
        """Check if bump is needed and send reminder for a single guild.
        
        Args:
            db: Active aiosqlite connection
            guild_id (int): Guild ID
            bump_channel_id (int): Channel ID to send reminder
            bump_start_time (str): ISO format datetime string
        """
        try:
            # Parse start time
            if not bump_start_time:
                logger.warning(f"[BUMP_CHECK] Guild {guild_id} has no bump_start_time, skipping")
                return
            
            start_dt = datetime.fromisoformat(bump_start_time)
            now = datetime.now()
            elapsed = now - start_dt
            
            # Check if 3 hours have passed
            if elapsed.total_seconds() < (BUMP_INTERVAL_HOURS * 3600):
                remaining = (BUMP_INTERVAL_HOURS * 3600) - elapsed.total_seconds()
                remaining_hours = int(remaining // 3600)
                remaining_minutes = int((remaining % 3600) // 60)
                logger.debug(
                    f"[BUMP_CHECK] Guild {guild_id}: Not yet time to bump "
                    f"(remaining: {remaining_hours}h {remaining_minutes}m)"
                )
                return
            
            # Get guild and channel
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.warning(f"[BUMP_CHECK] Guild {guild_id} not found (bot not in guild?)")
                return
            
            channel = guild.get_channel(bump_channel_id)
            if not channel:
                logger.warning(
                    f"[BUMP_CHECK] Guild {guild.name} ({guild_id}): "
                    f"Channel {bump_channel_id} not found (deleted?)"
                )
                return
            
            # Check bot permissions
            permissions = channel.permissions_for(guild.me)
            if not permissions.send_messages:
                logger.error(
                    f"[BUMP_CHECK] Guild {guild.name} ({guild_id}): "
                    f"No permission to send messages in {channel.name}"
                )
                return
            
            # Send bump reminder (no role pings)
            embed = discord.Embed(
                title="⏰ Đến giờ bump server rồi!",
                description=(
                    "Đã qua 3 giờ kể từ lần bump cuối.\\n"
                    "Sử dụng lệnh `/bump` để đưa server lên top Disboard nhé!\\n\\n"
                    "**Lợi ích:**\\n"
                    "• Tăng khả năng hiển thị server\\n"
                    "• Thu hút thêm member mới\\n"
                    "• Giúp server phát triển\\n"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Reminder tự động mỗi 3 giờ • Cảm ơn bạn!")
            
            try:
                # Send reminder (no content, only embed)
                await channel.send(embed=embed)
                logger.info(f"[BUMP_SENT] Guild {guild.name} ({guild_id}) - Reminder sent to #{channel.name}")
                
                # Update bump_start_time to now
                new_start_time = now.isoformat()
                await db.execute(
                    "UPDATE server_config SET bump_start_time = ? WHERE guild_id = ?",
                    (new_start_time, guild_id)
                )
                await db.commit()
                logger.info(f"[BUMP_UPDATED] Guild {guild_id}: Updated bump_start_time to {new_start_time}")
                
            except discord.Forbidden:
                logger.error(
                    f"[BUMP_FAILED] Guild {guild.name} ({guild_id}): "
                    f"Forbidden to send message (missing permissions?)"
                )
            except discord.HTTPException as e:
                logger.error(
                    f"[BUMP_FAILED] Guild {guild.name} ({guild_id}): "
                    f"HTTP error when sending message: {e}"
                )
        
        except Exception as e:
            logger.error(f"[BUMP_CHECK] Error processing guild {guild_id}: {e}")
            import traceback
            traceback.print_exc()
    
    @bump_reminder_task.before_loop
    async def before_bump_reminder(self):
        """Wait for bot to be ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("[DISBOARD] Bot ready, bump reminder task will start now")


async def setup(bot):
    """Load the DisboardReminderCog"""
    await bot.add_cog(DisboardReminderCog(bot))

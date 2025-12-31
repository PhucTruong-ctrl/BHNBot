"""Bump reminder background task module.

Runs periodic checks (every 30 minutes) to send bump reminders to configured guilds.
"""

import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timezone
from typing import Optional
from core.logger import setup_logger
# Use DB Manager singleton instead of direct connection
from core.database import db_manager

from .constants import (
    DB_PATH,
    BUMP_INTERVAL_SECONDS,
    REMINDER_COOLDOWN_SECONDS
)
from .models import BumpConfig
from .helpers import (
    parse_utc_datetime,
    validate_text_channel,
    build_reminder_embed,
    calculate_time_remaining
)

logger = setup_logger("BumpTask", "cogs/disboard.log")


class BumpReminderTask:
    """Manages the periodic bump reminder checking task.
    
    This class is responsible for:
    1. Running a background task every 30 minutes
    2. Loading all guild configurations from database
    3. Checking each guild for bump eligibility
    4. Sending reminders when conditions are met
    5. Updating last_reminder_sent timestamps
    
    Reminder Conditions:
    - bump_start_time >= 3 hours ago
    - last_reminder_sent is NULL OR >= 1 hour ago (cooldown)
    - Channel exists and is TextChannel
    - Bot has send_messages permission
    """
    
    def __init__(self, bot: commands.Bot):
        """Initialize the bump reminder task manager.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.task: Optional[tasks.Loop] = None
    
    def start(self) -> None:
        """Start the bump reminder background task.
        
        Raises:
            RuntimeError: If task fails to start
        """
        try:
            self.task = self.bump_reminder_loop.start()
            logger.info("[BUMP_TASK] Background task started successfully")
        except Exception as e:
            logger.error(f"[BUMP_TASK] Failed to start task: {e}", exc_info=True)
            raise
    
    def stop(self) -> None:
        """Stop the bump reminder background task."""
        if self.task:
            self.task.cancel()
            logger.info("[BUMP_TASK] Background task stopped")
    
    @tasks.loop(minutes=30)
    async def bump_reminder_loop(self) -> None:
        """Main task loop: check all guilds and send reminders.
        
        Runs every 30 minutes. Loads all configurations, checks each guild,
        and sends reminders where conditions are met.
        
        Note: Does NOT update bump_start_time after sending reminder.
        Only updates last_reminder_sent to prevent spam.
        """
        logger.info("[BUMP_TASK] Starting check iteration")
        
        try:
            # Use singleton db_manager instead of opening new connection
            db = db_manager
            if not db:
                logger.error("[BUMP_TASK] Database not initialized")
                return
            
            # Load all guild configurations
            try:
                configs = await BumpConfig.load_all(db)
            except Exception as query_error:
                logger.error(
                    f"[BUMP_TASK] Database query failed: {query_error}",
                    exc_info=True
                )
                return
            
            if not configs:
                logger.debug("[BUMP_TASK] No guilds with bump reminder configured")
                return
            
            logger.info(
                f"[BUMP_TASK] Found {len(configs)} guild(s) with bump reminder configured"
            )
            
            # Check each guild and send reminders
            reminders_sent = 0
            for config in configs:
                sent = await self._check_and_send_bump(db, config)
                if sent:
                    reminders_sent += 1
            
            # Summary
            if reminders_sent > 0:
                logger.info(f"[BUMP_TASK] Sent {reminders_sent} reminder(s) this iteration")
            else:
                logger.debug("[BUMP_TASK] No reminders sent this iteration")
        
        except Exception as e:
            logger.error(
                f"[BUMP_TASK] Unexpected error in task loop: {e}",
                exc_info=True
            )
    
    async def _check_and_send_bump(
        self,
        db: aiosqlite.Connection,
        config: BumpConfig
    ) -> bool:
        """Check single guild and send reminder if conditions met.
        
        Args:
            db: Active aiosqlite database connection
            config: Guild bump configuration
            
        Returns:
            True if reminder was sent successfully
        """
        guild_id = config.guild_id
        
        try:
            # NULL SAFETY: Initialize bump_start_time if missing
            if not config.bump_start_time:
                logger.warning(
                    f"[BUMP_CHECK] Guild {guild_id}: bump_start_time is NULL, "
                    f"initializing to NOW (likely first config)"
                )
                try:
                    await config.initialize_bump_time(db)
                    logger.info(
                        f"[BUMP_CHECK] Guild {guild_id}: "
                        f"Initialized bump_start_time to {config.bump_start_time}"
                    )
                except Exception as init_error:
                    logger.error(
                        f"[BUMP_CHECK] Guild {guild_id}: "
                        f"Failed to initialize bump_start_time: {init_error}",
                        exc_info=True
                    )
                # Skip this iteration, will check next time
                return False
            
            # Parse bump start time (UTC)
            try:
                start_dt = parse_utc_datetime(config.bump_start_time)
                if start_dt is None:
                    raise ValueError("bump_start_time is NULL after initialization")
            except ValueError as parse_error:
                logger.error(
                    f"[BUMP_CHECK] Guild {guild_id}: "
                    f"Invalid bump_start_time format '{config.bump_start_time}': {parse_error}",
                    exc_info=True
                )
                return False
            
            now_utc = datetime.now(timezone.utc)
            elapsed = (now_utc - start_dt).total_seconds()
            
            # Check if 3 hours have passed since last bump
            if elapsed < BUMP_INTERVAL_SECONDS:
                hours, minutes = calculate_time_remaining(BUMP_INTERVAL_SECONDS - elapsed)
                logger.debug(
                    f"[BUMP_CHECK] Guild {guild_id}: Not yet time to bump "
                    f"(remaining: {hours}h {minutes}m)"
                )
                return False
            
            # COOLDOWN CHECK: If reminder already sent, check cooldown
            if config.last_reminder_sent:
                try:
                    last_reminder_dt = parse_utc_datetime(config.last_reminder_sent)
                    if last_reminder_dt:
                        time_since_reminder = (now_utc - last_reminder_dt).total_seconds()
                        
                        if time_since_reminder < REMINDER_COOLDOWN_SECONDS:
                            cooldown_remaining = REMINDER_COOLDOWN_SECONDS - time_since_reminder
                            cooldown_minutes = int(cooldown_remaining // 60)
                            logger.debug(
                                f"[BUMP_CHECK] Guild {guild_id}: Reminder cooldown active "
                                f"(sent {int(time_since_reminder // 60)}m ago, "
                                f"cooldown: {cooldown_minutes}m remaining)"
                            )
                            return False
                except ValueError as cooldown_parse_error:
                    logger.warning(
                        f"[BUMP_CHECK] Guild {guild_id}: "
                        f"Invalid last_reminder_sent format, ignoring: {cooldown_parse_error}"
                    )
            
            # Get guild and channel
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.warning(
                    f"[BUMP_CHECK] Guild {guild_id} not found (bot removed from guild?). "
                    f"Consider cleaning up config."
                )
                return False
            
            channel = guild.get_channel(config.bump_channel_id)
            if not channel:
                logger.warning(
                    f"[BUMP_CHECK] Guild {guild.name} ({guild_id}): "
                    f"Channel {config.bump_channel_id} not found (deleted?). "
                    f"Admin should run /config bump to update."
                )
                return False
            
            # VALIDATION: Ensure channel is a text channel
            if not validate_text_channel(channel):
                logger.error(
                    f"[BUMP_CHECK] Guild {guild.name} ({guild_id}): "
                    f"Channel {channel.name} (ID: {config.bump_channel_id}) "
                    f"is not a TextChannel (type: {type(channel).__name__}). "
                    f"Admin should run /config bump to set a text channel."
                )
                return False
            
            # Check bot permissions
            permissions = channel.permissions_for(guild.me)
            if not permissions.send_messages:
                logger.error(
                    f"[BUMP_CHECK] Guild {guild.name} ({guild_id}): "
                    f"Bot lacks 'Send Messages' permission in #{channel.name}. "
                    f"Please grant permissions or change channel with /config bump"
                )
                return False
            
            # Calculate elapsed time for display
            elapsed_hours, elapsed_minutes = calculate_time_remaining(elapsed)
            
            # Build and send reminder embed
            embed = build_reminder_embed(elapsed_hours, elapsed_minutes)
            
            try:
                await channel.send(embed=embed)
                logger.info(
                    f"[BUMP_SENT] Guild {guild.name} ({guild_id}): "
                    f"Reminder sent to #{channel.name} (elapsed: {elapsed_hours}h {elapsed_minutes}m)"
                )
                
                # Update last_reminder_sent to prevent spam
                # NOTE: Do NOT update bump_start_time here!
                # Auto-detect (detector.py) will reset both when user actually bumps.
                try:
                    await config.update_reminder_time(db, now_utc)
                    logger.debug(
                        f"[BUMP_SENT] Guild {guild_id}: "
                        f"Updated last_reminder_sent to {config.last_reminder_sent}"
                    )
                except Exception as update_error:
                    logger.error(
                        f"[BUMP_SENT] Guild {guild_id}: "
                        f"Failed to update last_reminder_sent: {update_error}",
                        exc_info=True
                    )
                
                return True
                
            except discord.Forbidden as forbidden_error:
                logger.error(
                    f"[BUMP_FAILED] Guild {guild.name} ({guild_id}): "
                    f"Forbidden to send message in #{channel.name}: {forbidden_error}. "
                    f"Check bot role permissions.",
                    exc_info=True
                )
            except discord.HTTPException as http_error:
                logger.error(
                    f"[BUMP_FAILED] Guild {guild.name} ({guild_id}): "
                    f"HTTP error when sending to #{channel.name}: {http_error}. "
                    f"Discord API might be down or rate limited.",
                    exc_info=True
                )
            except discord.errors.ClientConnectorDNSError as dns_error:
                # CRITICAL FIX: Handle DNS errors gracefully (don't crash task)
                logger.warning(
                    f"[BUMP_FAILED] Guild {guild.name} ({guild_id}): "
                    f"DNS resolution failure (transient network issue): {dns_error}. "
                    f"Skipping this iteration, will retry next cycle."
                )
            except Exception as send_error:
                logger.error(
                    f"[BUMP_FAILED] Guild {guild.name} ({guild_id}): "
                    f"Unexpected error sending reminder: {send_error}",
                    exc_info=True
                )
        
        except Exception as e:
            logger.error(
                f"[BUMP_CHECK] Guild {guild_id}: "
                f"Critical error in check_and_send: {e}",
                exc_info=True
            )
        
        return False
    
    @bump_reminder_loop.before_loop
    async def before_bump_reminder_loop(self) -> None:
        """Wait for bot to be ready before starting the task loop."""
        logger.debug("[BUMP_TASK] Waiting for bot to be ready...")
        await self.bot.wait_until_ready()
        logger.info("[BUMP_TASK] Bot ready, task loop starting now")

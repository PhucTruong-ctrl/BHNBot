"""Discord logging handler for sending ERROR/CRITICAL logs to Discord channels.

This module provides a custom logging handler that sends structured logs
to a Discord channel as embeds, with optional user pinging for critical events.
"""

import json
import logging
import sys
from typing import Any, Optional, Tuple

import discord


class DiscordLogHandler(logging.Handler):
    """Custom logging handler that sends critical logs to Discord channel via embeds.
    
    This handler parses JSON-formatted log messages (from structlog) and creates
    rich Discord embeds with structured information.
    
    Attributes:
        bot: Discord client/bot instance.
        channel_id: Target Discord channel ID for log messages.
        min_level: Minimum log level to send to Discord.
        ping_user_id: User ID to ping on ERROR/CRITICAL (0 = no ping).
    """
    
    def __init__(
        self,
        bot: discord.Client,
        channel_id: int,
        min_level: int = logging.ERROR,
        ping_user_id: int = 0,
    ) -> None:
        """Initialize the Discord log handler.
        
        Args:
            bot: Discord bot/client instance with active event loop.
            channel_id: Discord channel ID where logs will be sent.
            min_level: Minimum logging level to handle (default: ERROR).
            ping_user_id: User ID to ping for ERROR/CRITICAL (0 disables).
        """
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.min_level = min_level
        self.ping_user_id = ping_user_id
        self.setLevel(min_level)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Discord channel (non-blocking).
        
        Schedules the async send operation on the bot's event loop.
        
        Args:
            record: The log record to emit.
        """
        try:
            if record.levelno < self.min_level:
                return
            if self.bot.loop and self.bot.loop.is_running():
                self.bot.loop.create_task(self._send_log_embed(record))
        except Exception as e:
            print(f"[DiscordLogHandler] Failed to schedule log: {e}", file=sys.stderr)
    
    async def _send_log_embed(self, record: logging.LogRecord) -> None:
        """Async send log as Discord embed.
        
        Parses JSON log message and creates a structured embed with
        all available context fields.
        
        Args:
            record: The log record to send.
        """
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                return
            
            # Parse JSON message if available (structlog format)
            log_data = self._parse_log_message(record)
            
            # Determine embed color and title based on level
            color, title = self._get_level_style(record.levelno)
            
            # Build embed
            embed = discord.Embed(
                title=title,
                color=color,
                timestamp=discord.utils.utcnow(),
            )
            
            # Main event/message
            event = log_data.get("event", record.getMessage())
            if len(event) > 1900:
                event = event[:1900] + "..."
            embed.description = f"```\n{event}\n```"
            
            # Add structured fields
            if logger_name := log_data.get("logger", record.name):
                embed.add_field(name="Logger", value=f"`{logger_name}`", inline=True)
            
            embed.add_field(
                name="Location",
                value=f"`{record.filename}:{record.lineno}`",
                inline=True,
            )
            
            # Add context fields from structlog
            context_fields = ["user_id", "guild_id", "command", "request_id", "trace_id"]
            context_parts = []
            for field in context_fields:
                if value := log_data.get(field):
                    context_parts.append(f"**{field}**: `{value}`")
            
            if context_parts:
                embed.add_field(
                    name="Context",
                    value="\n".join(context_parts),
                    inline=False,
                )
            
            # Add exception info if present
            if exc_info := log_data.get("exception"):
                exc_text = exc_info if isinstance(exc_info, str) else str(exc_info)
                if len(exc_text) > 1000:
                    exc_text = exc_text[:1000] + "..."
                embed.add_field(
                    name="Exception",
                    value=f"```\n{exc_text}\n```",
                    inline=False,
                )
            
            # Service tag
            if service := log_data.get("service"):
                embed.set_footer(text=f"Service: {service}")
            
            # Ping user for ERROR/CRITICAL
            content = None
            if record.levelno >= logging.ERROR and self.ping_user_id > 0:
                content = f"<@{self.ping_user_id}>"
            
            await channel.send(content=content, embed=embed)
            
        except Exception as e:
            print(f"[DiscordLogHandler] Send error: {e}", file=sys.stderr)
    
    def _parse_log_message(self, record: logging.LogRecord) -> dict[str, Any]:
        """Parse log message, handling both JSON and plain text.
        
        Args:
            record: The log record with message to parse.
            
        Returns:
            Dictionary with parsed log data, or {"event": message} for plain text.
        """
        message = record.getMessage()
        try:
            return json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return {"event": message}
    
    def _get_level_style(self, level: int) -> Tuple[discord.Color, str]:
        """Get embed color and title for log level.
        
        Args:
            level: Logging level (e.g., logging.ERROR).
            
        Returns:
            Tuple of (discord.Color, title string).
        """
        if level >= logging.CRITICAL:
            return discord.Color.dark_red(), "🚨🚨 CRITICAL"
        elif level >= logging.ERROR:
            return discord.Color.red(), "🚨 ERROR"
        elif level >= logging.WARNING:
            return discord.Color.gold(), "⚠️ WARNING"
        else:
            return discord.Color.blue(), "ℹ️ INFO"


def attach_discord_handler(
    bot: discord.Client,
    channel_id: int = 0,
    ping_user_id: int = 0,
    log_level: str = "ERROR",
) -> int:
    """Attach Discord log handler to all existing loggers.
    
    This function iterates through all registered loggers and attaches
    a DiscordLogHandler to each one that has existing handlers.
    
    Args:
        bot: Discord bot instance with active event loop.
        channel_id: Discord channel ID for logging (0 = disabled).
        ping_user_id: User ID to ping on ERROR/CRITICAL (0 = no ping).
        log_level: Minimum level string (INFO/WARNING/ERROR/CRITICAL).
        
    Returns:
        Number of loggers that received the Discord handler.
    """
    if channel_id <= 0:
        print("[Logging] No channel_id provided, Discord logging disabled")
        return 0
    
    # Convert level string to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    discord_level = level_map.get(log_level.upper(), logging.ERROR)
    
    print(f"[Logging] Attaching Discord handler: channel={channel_id}, ping={ping_user_id}, level={log_level}")
    
    # Get all loggers including root
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    loggers.append(logging.getLogger())  # Root logger
    
    attached_count = 0
    removed_count = 0
    
    for logger in loggers:
        for handler in logger.handlers[:]:
            if isinstance(handler, DiscordLogHandler):
                logger.removeHandler(handler)
                removed_count += 1
        
        # Add new handler if logger has other handlers (file/console)
        if logger.handlers:
            discord_handler = DiscordLogHandler(
                bot=bot,
                channel_id=channel_id,
                min_level=discord_level,
                ping_user_id=ping_user_id,
            )
            logger.addHandler(discord_handler)
            attached_count += 1
    
    if removed_count > 0:
        print(f"[Logging] Removed {removed_count} old Discord handlers")
    
    print(f"[Logging] ✅ Discord handler attached to {attached_count} loggers")
    return attached_count


async def get_log_config_from_db(guild_id: Optional[int] = None) -> Tuple[int, int, str]:
    """Read log config from server_config (PostgreSQL).
    
    Fetches Discord logging configuration from the database, including
    channel ID, ping user ID, and minimum log level.
    
    Args:
        guild_id: Guild ID to get config for (uses first guild if None).
        
    Returns:
        Tuple of (channel_id, ping_user_id, log_level).
        Returns (0, 0, "ERROR") on failure.
    """
    try:
        from core.database import db_manager
        
        if guild_id:
            row = await db_manager.fetchone(
                "SELECT log_discord_channel_id, log_ping_user_id, log_discord_level "
                "FROM server_config WHERE guild_id = $1",
                guild_id,
            )
        else:
            # Get first configured channel
            row = await db_manager.fetchone(
                "SELECT log_discord_channel_id, log_ping_user_id, log_discord_level "
                "FROM server_config WHERE log_discord_channel_id IS NOT NULL LIMIT 1"
            )
        
        if row:
            return (row[0] or 0, row[1] or 0, row[2] or "ERROR")
        return (0, 0, "ERROR")
        
    except Exception as e:
        print(f"[Logging] Failed to read log config from DB: {e}")
        return (0, 0, "ERROR")

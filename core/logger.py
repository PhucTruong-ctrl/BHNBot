import logging
import os
from logging.handlers import TimedRotatingFileHandler
import sys
from pathlib import Path
import discord
import asyncio
from typing import Optional, Tuple
import logging.handlers
from logging.handlers import QueueHandler, QueueListener
import queue

# Base logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Keep track of listeners to prevent GC
_listeners = []

# Track file handlers by path to prevent duplicate handlers for same file
_file_handlers: dict[str, TimedRotatingFileHandler] = {}
_file_handler_lock = __import__("threading").Lock()


class DiscordLogHandler(logging.Handler):
    """Custom logging handler that sends critical logs to Discord channel via embeds."""
    
    def __init__(self, bot: discord.Client, channel_id: int, min_level: int, ping_user_id: int = 0):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.min_level = min_level
        self.ping_user_id = ping_user_id
        self.setLevel(min_level)
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to Discord channel (non-blocking)."""
        try:
            if record.levelno < self.min_level:
                return
            if self.bot.loop and self.bot.loop.is_running():
                self.bot.loop.create_task(self._send_log_embed(record))
        except Exception as e:
            print(f"[DiscordLogHandler] Failed to send log: {e}", file=sys.stderr)
    
    async def _send_log_embed(self, record: logging.LogRecord):
        """Async send log as Discord embed."""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                return
            
            if record.levelno >= logging.CRITICAL:
                color = discord.Color.dark_red()
                title = "🚨🚨 CRITICAL"
            elif record.levelno >= logging.ERROR:
                color = discord.Color.red()
                title = "🚨 ERROR"
            elif record.levelno >= logging.WARNING:
                color = discord.Color.gold()
                title = "⚠️ WARNING"
            else:
                color = discord.Color.blue()
                title = "ℹ️ INFO"
            
            embed = discord.Embed(
                title=title,
                description=f"```\n{record.getMessage()[:1900]}\n```",
                color=color,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Module", value=f"`{record.name}`", inline=True)
            embed.add_field(name="Location", value=f"`{record.filename}:{record.lineno}`", inline=True)
            
            # Ping user only for ERROR/CRITICAL and if configured
            content = None
            if record.levelno >= logging.ERROR:
                print(f"[DEBUG] Log level {record.levelno} >= ERROR. Ping user: {self.ping_user_id}")
                if self.ping_user_id > 0:
                    content = f"<@{self.ping_user_id}>"
            
            await channel.send(content=content, embed=embed)
        except Exception as e:
            print(f"[DiscordLogHandler] Send error: {e}", file=sys.stderr)


def setup_logger(logger_name: str, file_path: str, level=logging.INFO) -> logging.Logger:
    """Configures a non-blocking logger with file (async via queue) and console handlers."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
        
    full_log_path = LOG_DIR / file_path
    full_log_path_str = str(full_log_path)
    os.makedirs(os.path.dirname(full_log_path), exist_ok=True)
    
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    with _file_handler_lock:
        if full_log_path_str in _file_handlers:
            file_handler = _file_handlers[full_log_path_str]
        else:
            file_handler = TimedRotatingFileHandler(
                filename=full_log_path,
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            _file_handlers[full_log_path_str] = file_handler
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    
    listener = QueueListener(log_queue, file_handler, console_handler, respect_handler_level=True)
    listener.start()
    
    _listeners.append(listener)
    
    logger.addHandler(queue_handler)
    
    return logger


def attach_discord_handler(bot: discord.Client, channel_id: int = 0, ping_user_id: int = 0, log_level: str = "WARNING"):
    """Attach Discord log handler to all existing loggers.
    
    Args:
        bot: Discord bot instance
        channel_id: Discord channel ID for logging
        ping_user_id: User ID to ping on ERROR/CRITICAL (0 = no ping)
        log_level: Minimum level to log (INFO/WARNING/ERROR/CRITICAL)
    """
    try:
        if channel_id <= 0:
            print("[Logger] No channel_id provided, Discord logging disabled")
            return
        
        # Convert level string to logging constant
        level_map = {
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        discord_level = level_map.get(log_level.upper() if log_level else "WARNING", logging.WARNING)
        
        print(f"[Logger] Attaching Discord handler: channel={channel_id}, ping={ping_user_id}, level={log_level}")
        
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        loggers.append(logging.getLogger())
        
        attached_count = 0
        removed_count = 0
        for logger in loggers:
            # Remove existing Discord handlers first (allows config updates)
            for h in logger.handlers[:]:  # Copy list to avoid modification during iteration
                if isinstance(h, DiscordLogHandler):
                    logger.removeHandler(h)
                    removed_count += 1
            
            # Add new handler if logger has other handlers (file/console)
            if logger.handlers:
                discord_handler = DiscordLogHandler(
                    bot=bot,
                    channel_id=channel_id,
                    min_level=discord_level,
                    ping_user_id=ping_user_id
                )
                logger.addHandler(discord_handler)
                attached_count += 1
        
        if removed_count > 0:
            print(f"[Logger] Removed {removed_count} old Discord handlers")
        
        print(f"[Logger] ✅ Discord handler attached to {attached_count} loggers")
        
    except Exception as e:
        print(f"[Logger] Discord logging failed: {e}")


async def get_log_config_from_db(guild_id: int = None) -> Tuple[int, int, str]:
    """Read log config from server_config (PostgreSQL).

    Args:
        guild_id: Guild ID to get config for (uses first guild if None)

    Returns:
        Tuple of (channel_id, ping_user_id, log_level)
    """
    try:
        from core.database import db_manager

        if guild_id:
            row = await db_manager.fetchone(
                "SELECT log_discord_channel_id, log_ping_user_id, log_discord_level FROM server_config WHERE guild_id = $1",
                guild_id
            )
        else:
            # Get first configured channel
            row = await db_manager.fetchone(
                "SELECT log_discord_channel_id, log_ping_user_id, log_discord_level FROM server_config WHERE log_discord_channel_id IS NOT NULL LIMIT 1"
            )

        if row:
            return (row[0] or 0, row[1] or 0, row[2] or "WARNING")
        return (0, 0, "WARNING")
    except Exception as e:
        print(f"[Logger] Failed to read log config from DB: {e}")
        return (0, 0, "WARNING")

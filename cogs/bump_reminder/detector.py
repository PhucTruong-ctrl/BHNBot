"""DISBOARD bump detection module.

Listens for DISBOARD bot messages and detects successful bump confirmations.
Updates database when valid bumps are detected.
"""

import discord
from discord.ext import commands
from core.logger import setup_logger
from database_manager import db_manager

logger = setup_logger("BumpDetector", "cogs/disboard.log")


class BumpDetector:
    """Detects and processes DISBOARD bump confirmations.
    
    This class is responsible for:
    1. Listening to all messages in guilds
    2. Identifying messages from official DISBOARD bot
    3. Detecting bump confirmation patterns
    4. Updating bump_start_time and resetting last_reminder_sent in database
    
    Security features:
    - Validates message is from official bot (not user impersonation)
    - Ensures message is in guild (not DM)
    - Uses multiple pattern matching for reliability
    """
    
    def __init__(self, bot: commands.Bot):
        """Initialize the bump detector.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    async def on_message(self, message: discord.Message) -> None:
        """Process incoming message to detect DISBOARD bump confirmations.
        
        Called by cog listener for every message. Performs security checks,
        pattern matching, and database updates.
        
        Args:
            message: Discord message object
            
        Security Validations:
        - Author must be DISBOARD bot ID
        - Author must be a bot (not user)
        - Message must be in guild (not DM)
        """
        # SECURITY: Validate message source
        if message.author.id != DISBOARD_BOT_ID:
            return
        
        if not message.author.bot:
            logger.warning(
                f"[BUMP_DETECT] Message from user ID {message.author.id} "
                f"impersonating DISBOARD (not a bot)"
            )
            return
        
        # Must be in a guild (not DM)
        guild = message.guild
        if not guild:
            logger.debug("[BUMP_DETECT] Ignoring DISBOARD message in DM")
            return
        
        # Check if this is a bump confirmation using multiple patterns
        if not self._is_bump_confirmation(message):
            logger.debug(
                f"[BUMP_DETECT] Guild {guild.id}: "
                f"DISBOARD message not a bump confirmation"
            )
            return
        
        # Process the bump
        await self._process_bump(guild)
    
    def _is_bump_confirmation(self, message: discord.Message) -> bool:
        """Check if message contains bump confirmation patterns.
        
        Args:
            message: Discord message to check
            
        Returns:
            True if message matches any bump confirmation pattern
        """
        # Check embeds first
        if message.embeds:
            for embed in message.embeds:
                embed_text = ((embed.description or "") + (embed.title or "")).lower()
                if any(pattern in embed_text for pattern in BUMP_CONFIRM_PATTERNS):
                    logger.debug(
                        f"[BUMP_DETECT] Detected bump in embed: {embed_text[:100]}"
                    )
                    return True
        
        # Check message content
        if message.content:
            content_lower = message.content.lower()
            if any(pattern in content_lower for pattern in BUMP_CONFIRM_PATTERNS):
                logger.debug(
                    f"[BUMP_DETECT] Detected bump in content: {message.content[:100]}"
                )
                return True
        
        return False
    
    async def _process_bump(self, guild: discord.Guild) -> None:
        """Process detected bump: update database timestamps.
        
        Args:
            guild: Guild where bump was detected
        """
        try:
            # Check if guild has bump reminder configured
            row = await db_manager.fetchone(
                "SELECT bump_channel_id FROM server_config WHERE guild_id = ?",
                (guild.id,)
            )
            
            if not row or not row[0]:
                # Bump reminder not configured for this guild
                logger.debug(
                    f"[BUMP_DETECT] Guild {guild.id} ({guild.name}): "
                    f"Not configured, ignoring bump"
                )
                return
            
            # Update bump_start_time AND reset last_reminder_sent (UTC)
            now_utc = datetime.now(timezone.utc).isoformat()
            
            try:
                await db_manager.modify(
                    "UPDATE server_config SET bump_start_time = ?, last_reminder_sent = NULL WHERE guild_id = ?",
                    (now_utc, guild.id)
                )
                
                logger.info(
                    f"[BUMP_DETECT] Guild {guild.name} ({guild.id}): "
                    f"Detected successful bump, updated timer to {now_utc}"
                )
            except Exception as commit_error:
                logger.error(
                    f"[BUMP_DETECT] Guild {guild.id}: DB commit failed: {commit_error}",
                    exc_info=True
                )
                raise
        
        except Exception as e:
            logger.error(
                f"[BUMP_DETECT] Guild {guild.id}: Unexpected error: {e}",
                exc_info=True
            )

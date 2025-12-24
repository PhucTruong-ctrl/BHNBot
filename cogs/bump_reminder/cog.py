"""Bump Reminder Cog - Main orchestrator.

Coordinates the bump detection and reminder task systems.
"""

from discord.ext import commands
from core.logger import setup_logger

from .detector import BumpDetector
from .task import BumpReminderTask

logger = setup_logger("BumpReminderCog", "cogs/disboard.log")


class BumpReminderCog(commands.Cog):
    """Main cog for DISBOARD bump reminder system.
    
    This cog orchestrates two main components:
    1. BumpDetector: Listens for DISBOARD bump confirmations
    2. BumpReminderTask: Sends periodic reminders every 3 hours
    
    The cog handles:
    - Initialization of both components
    - Lifecycle management (start/stop)
    - Message routing to detector
    """
    
    def __init__(self, bot: commands.Bot):
        """Initialize the bump reminder cog.
        
        Args:
            bot: Discord bot instance
            
        Raises:
            RuntimeError: If initialization fails
        """
        self.bot = bot
        
        try:
            # Initialize detector
            self.detector = BumpDetector(bot)
            logger.info("[BUMP_COG] Detector initialized")
            
            # Initialize and start task
            self.task_manager = BumpReminderTask(bot)
            self.task_manager.start()
            logger.info("[BUMP_COG] Task manager initialized and started")
            
            logger.info("[BUMP_COG] Cog loaded successfully")
            
        except Exception as e:
            logger.error(
                f"[BUMP_COG] Failed to initialize cog: {e}",
                exc_info=True
            )
            raise
    
    def cog_unload(self) -> None:
        """Cleanup when cog is unloaded.
        
        Stops the background task to prevent resource leaks.
        """
        self.task_manager.stop()
        logger.info("[BUMP_COG] Cog unloaded successfully")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Route messages to detector for bump detection.
        
        Args:
            message: Discord message object
        """
        await self.detector.on_message(message)


async def setup(bot: commands.Bot):
    """Load the Bump Reminder cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(BumpReminderCog(bot))

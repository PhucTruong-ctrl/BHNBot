"""Database Maintenance Cog - WAL Checkpoint & Optimization

Handles periodic WAL checkpoints and database health monitoring.
Uses db_manager singleton instead of direct connections.
"""
import discord
from discord.ext import commands, tasks
from pathlib import Path
from core.logging import setup_logger

logger = setup_logger("Maintenance", "cogs/admin/maintenance.log")

CHECKPOINT_INTERVAL_HOURS = 4  # Run every 4 hours


class Maintenance(commands.Cog):
    """Database maintenance tasks for WAL mode optimization.
    
    Runs periodic tasks to:
    1. Checkpoint WAL file (flush to main DB)
    2. Optimize database structure
    3. Prevent WAL file growth
    """
    
    def __init__(self, bot):
        self.bot = bot
        logger.info(f"[MAINTENANCE] Cog loaded (checkpoint every {CHECKPOINT_INTERVAL_HOURS}h)")
    
    async def cog_load(self):
        """Start tasks when cog loads."""
        self.wal_checkpoint_task.start()
        logger.info("[MAINTENANCE] Checkpoint task started")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.wal_checkpoint_task.cancel()
        logger.info("[MAINTENANCE] Checkpoint task stopped")
    
    @tasks.loop(hours=CHECKPOINT_INTERVAL_HOURS)
    async def wal_checkpoint_task(self):
        """Periodic WAL checkpoint to flush changes to main database.
        
        Runs every 4 hours to:
        1. Flush WAL file to main .db file (TRUNCATE mode)
        2. Prevent WAL file from growing too large
        3. Optimize database structure
        """
        try:
            # POSTGRES COMPATIBILITY: WAL Checkpoint is for SQLite only.
            # Since we migrated to Postgres, this task is no longer needed but kept for structure.
            # db = self.bot.db
            # if not db:
            #     logger.warning("[MAINTENANCE] Database not initialized, skipping checkpoint")
            #     return
            pass
            
        except Exception as e:
            logger.error(f"[WAL_CHECKPOINT] ❌ Failed: {e}", exc_info=True)
    
    @wal_checkpoint_task.before_loop
    async def before_checkpoint(self):
        """Wait for bot to be ready before starting checkpoint task."""
        await self.bot.wait_until_ready()
        logger.info("[MAINTENANCE] Bot ready, checkpoint loop starting")


async def setup(bot):
    """Load the Maintenance cog."""
    await bot.add_cog(Maintenance(bot))

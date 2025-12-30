"""Database Maintenance Cog - WAL Checkpoint & Optimization

Handles periodic WAL checkpoints and database health monitoring.
Uses db_manager singleton instead of direct connections.
"""
import discord
from discord.ext import commands, tasks
from pathlib import Path
from core.logger import setup_logger

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
            db = self.bot.db.db
            if not db:
                logger.warning("[MAINTENANCE] Database not initialized, skipping checkpoint")
                return
            
            # Get WAL file size before checkpoint
            wal_path = Path(f"{self.bot.db.db_path}-wal")
            wal_size_before = wal_path.stat().st_size / 1024 if wal_path.exists() else 0
            
            # Perform checkpoint (TRUNCATE = aggressive, resets WAL to 0)
            cursor = await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result = await cursor.fetchone()
            
            # Get WAL file size after checkpoint
            wal_size_after = wal_path.stat().st_size / 1024 if wal_path.exists() else 0
            
            # Log results  
            if result:
                busy, checkpointed, _ = result
                logger.info(
                    f"[WAL_CHECKPOINT] ✅ Completed: "
                    f"{checkpointed} pages synced, "
                    f"WAL: {wal_size_before:.1f}KB → {wal_size_after:.1f}KB"
                )
                
                # Warning if WAL is still large after checkpoint
                if wal_size_after > 5120:  # 5MB
                    logger.warning(
                        f"[WAL_CHECKPOINT] ⚠️  WAL file still large ({wal_size_after/1024:.1f}MB) after checkpoint"
                    )
            
            # Optimize database structure (rebuild indexes, update stats)
            await db.execute("PRAGMA optimize")
            logger.info("[MAINTENANCE] ✅ Database optimization completed")
            
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

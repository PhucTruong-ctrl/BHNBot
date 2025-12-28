"""Database Maintenance Cog - WAL Checkpoint & Monitoring

Handles periodic WAL checkpoints and database health monitoring.
"""
import discord
from discord.ext import commands, tasks
import sqlite3
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger("DB_MAINTENANCE", "cogs/database.log")

DB_PATH = "./data/database.db"
CHECKPOINT_INTERVAL_HOURS = 6


class DatabaseMaintenanceCog(commands.Cog):
    """Database maintenance tasks for WAL mode optimization."""
    
    def __init__(self, bot):
        self.bot = bot
        self.wal_checkpoint_task.start()
        logger.info(f"[DB_MAINTENANCE] Started (checkpoint every {CHECKPOINT_INTERVAL_HOURS}h)")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.wal_checkpoint_task.cancel()
        logger.info("[DB_MAINTENANCE] Stopped")
    
    @tasks.loop(hours=CHECKPOINT_INTERVAL_HOURS)
    async def wal_checkpoint_task(self):
        """Periodic WAL checkpoint to flush changes to main database.
        
        Runs every 6 hours to:
        1. Flush WAL file to main .db file
        2. Prevent WAL file from growing too large
        3. Improve backup consistency
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            
            # Get WAL file size before checkpoint
            wal_path = Path(f"{DB_PATH}-wal")
            wal_size_before = wal_path.stat().st_size / 1024 if wal_path.exists() else 0
            
            # Perform checkpoint (PASSIVE = non-blocking)
            cursor = conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            result = cursor.fetchone()
            conn.close()
            
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
                
                # Warning if WAL is growing too large
                if wal_size_after > 10240:  # 10MB
                    logger.warning(
                        f"[WAL_CHECKPOINT] ⚠️  WAL file is large ({wal_size_after/1024:.1f}MB), "
                        "consider running TRUNCATE checkpoint"
                    )
            
        except Exception as e:
            logger.error(f"[WAL_CHECKPOINT] ❌ Failed: {e}")
    
    @wal_checkpoint_task.before_loop
    async def before_checkpoint(self):
        """Wait for bot to be ready before starting checkpoint task."""
        await self.bot.wait_until_ready()
        logger.info("[DB_MAINTENANCE] Bot ready, checkpoint task initialized")


async def setup(bot):
    """Load the DatabaseMaintenanceCog."""
    await bot.add_cog(DatabaseMaintenanceCog(bot))

"""Automatic Database Backup System

Backs up database.db every 4 hours and maintains maximum 6 backups.
Oldest backups are automatically deleted when limit is exceeded.

Uses SQLite backup API for WAL-safe backups.
"""
import discord
from discord.ext import commands, tasks
import sqlite3
from pathlib import Path
from datetime import datetime
from core.logger import setup_logger

logger = setup_logger("BACKUP", "cogs/database.log")

DB_PATH = "./data/database.db"
BACKUP_DIR = "./data/backups/auto"
MAX_BACKUPS = 6
BACKUP_INTERVAL_HOURS = 4


class DatabaseBackupCog(commands.Cog):
    """Automatic database backup system.
    
    Runs background task every 4 hours to:
    1. Create timestamped backup of database.db
    2. Clean up old backups (keep only 6 most recent)
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Ensure backup directory exists
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        
        # Start background task
        self.auto_backup_task.start()
        logger.info(f"[BACKUP] Auto-backup system started (every {BACKUP_INTERVAL_HOURS}h, max {MAX_BACKUPS} backups)")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.auto_backup_task.cancel()
        logger.info("[BACKUP] Auto-backup system stopped")
    
    @tasks.loop(hours=BACKUP_INTERVAL_HOURS)
    async def auto_backup_task(self):
        """Backup database every 4 hours using SQLite backup API (WAL-safe).
        
        Creates timestamped copy of database.db and deletes oldest backups
        if total count exceeds MAX_BACKUPS.
        """
        try:
            # Step 1: Cleanup old backups first (before creating new one)
            self._cleanup_old_backups()
            
            # Step 2: Create new backup using SQLite backup API (WAL-safe)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = Path(BACKUP_DIR) / f"database_auto_{timestamp}.db"
            
            # Use SQLite backup API (handles WAL files properly)
            source = sqlite3.connect(DB_PATH)
            destination = sqlite3.connect(str(backup_path))
            
            with destination:
                source.backup(destination)
            
            destination.close()
            source.close()
            
            # Optional: Checkpoint WAL after successful backup
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                conn.close()
            except:
                pass  # Non-critical
            
            # Log success with file size
            backup_size = backup_path.stat().st_size / 1024  # KB
            logger.info(
                f"[BACKUP] ✅ Created WAL-safe auto-backup: {backup_path.name} "
                f"({backup_size:.1f} KB)"
            )
            
        except FileNotFoundError:
            logger.error(f"[BACKUP] ❌ Source database not found: {DB_PATH}")
        except PermissionError as e:
            logger.error(f"[BACKUP] ❌ Permission denied: {e}")
        except Exception as e:
            logger.error(f"[BACKUP] ❌ Failed to create auto-backup: {e}")
            import traceback
            traceback.print_exc()
    
    @auto_backup_task.before_loop
    async def before_backup(self):
        """Wait for bot to be ready before starting backup task."""
        await self.bot.wait_until_ready()
        logger.info("[BACKUP] Bot ready, auto-backup task initialized")
    
    def _cleanup_old_backups(self):
        """Delete oldest backups if count exceeds MAX_BACKUPS.
        
        Keeps only the MAX_BACKUPS most recent backup files.
        Files are sorted by modification time (oldest first).
        """
        # Get all auto-backup files sorted by modification time
        backup_files = sorted(
            Path(BACKUP_DIR).glob("database_auto_*.db"),
            key=lambda p: p.stat().st_mtime  # Sort by modification time
        )
        
        # Delete oldest files if we have too many
        deleted_count = 0
        while len(backup_files) >= MAX_BACKUPS:
            oldest = backup_files.pop(0)
            try:
                oldest.unlink()
                deleted_count += 1
                logger.info(f"[BACKUP] 🗑️  Deleted old backup: {oldest.name}")
            except Exception as e:
                logger.error(f"[BACKUP] Failed to delete {oldest.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"[BACKUP] Cleaned up {deleted_count} old backup(s)")


async def setup(bot):
    """Load the DatabaseBackupCog."""
    await bot.add_cog(DatabaseBackupCog(bot))

"""Automatic Database Backup System

Backs up PostgreSQL database every 4 hours and maintains maximum 6 backups.
Oldest backups are automatically deleted when limit is exceeded.

Uses pg_dump for reliable backups.
"""
import discord
import asyncio
from discord.ext import commands, tasks
import subprocess
import os
from pathlib import Path
from datetime import datetime
from core.logging import setup_logger

logger = setup_logger("BACKUP", "cogs/database.log")

# Configuration (defaults match docker/local setup)
BACKUP_DIR = "./data/backups/auto"
MAX_BACKUPS = 6
BACKUP_INTERVAL_HOURS = 4

class DatabaseBackupCog(commands.Cog):
    """Automatic database backup system.
    
    Runs background task every 4 hours to:
    1. Create timestamped backup of PostgreSQL DB
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
        """Backup database every 4 hours using pg_dump.
        
        Creates timestamped dump and deletes oldest backups
        if total count exceeds MAX_BACKUPS.
        """
        try:
            # Step 1: Cleanup old backups first (before creating new one)
            self._cleanup_old_backups()
            
            # Step 2: Create new backup using pg_dump
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"postgres_auto_{timestamp}.dump"
            backup_path = Path(BACKUP_DIR) / backup_filename
            
            # Prepare Environment for Password (avoid warning/process hang)
            env = os.environ.copy()
            # Try getting pass from env, fallback to default if not set
            pg_pass = os.getenv("DB_PASS", "discord_bot_password") 
            env["PGPASSWORD"] = pg_pass
            
            # Connection details
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_user = os.getenv("DB_USER", "discord_bot")
            db_name = os.getenv("DB_NAME", "discord_bot_db")
            
            # Command: pg_dump -h host -p port -U user -F c -f file dbname
            cmd = [
                "pg_dump",
                "-h", db_host,
                "-p", db_port,
                "-U", db_user,
                "-F", "c",          # Custom format (compressed, suitable for pg_restore)
                "-f", str(backup_path),
                db_name
            ]
            
            logger.info(f"[BACKUP] Starting backup for {db_name}...")
            
            # Execute subprocess
            # run_in_executor is recommended for blocking I/O, but subprocess.run is fast enough usually.
            # However, for huge DBs, use asyncio.create_subprocess_exec would be better.
            # Given requirement for non-blocking I/O:
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"[BACKUP] pg_dump failed: {error_msg}")
                raise Exception(f"pg_dump failed with code {process.returncode}")
            
            # Log success with file size
            if backup_path.exists():
                backup_size = backup_path.stat().st_size / 1024  # KB
                logger.info(
                    f"[BACKUP] ✅ Created PostgreSQL backup: {backup_path.name} "
                    f"({backup_size:.1f} KB)"
                )
            else:
                logger.error("[BACKUP] Backup file not found after success code?")
            
        except Exception as e:
            logger.error(f"[BACKUP] ❌ Failed to create auto-backup: {e}")
    
    @auto_backup_task.before_loop
    async def before_backup(self):
        """Wait for bot to be ready before starting backup task."""
        await self.bot.wait_until_ready()
        logger.info("[BACKUP] Bot ready, auto-backup task initialized")
    
    def _cleanup_old_backups(self):
        """Delete oldest backups to maintain MAX_BACKUPS limit."""
        try:
            backups = sorted(Path(BACKUP_DIR).glob("postgres_auto_*.dump"))
            
            if len(backups) >= MAX_BACKUPS:
                # Calculate how many to remove
                to_remove_count = len(backups) - MAX_BACKUPS + 1 
                # (+1 because we are about to create a new one? No, usually keep space for new one)
                # Logic: If 6 backups exist, and max is 6. We delete 1 to make room for 7th? 
                # Or delete after creation? Code deletes BEFORE creation.
                # So if we have 6, we delete 1 -> 5. Create new -> 6. Correct.
                
                to_remove = backups[:to_remove_count]
                
                for backup in to_remove:
                    try:
                        backup.unlink()
                        logger.info(f"[BACKUP] Removed old backup: {backup.name}")
                    except Exception as e:
                        logger.warning(f"[BACKUP] Failed to remove {backup.name}: {e}")
        except Exception as e:
            logger.error(f"[BACKUP] Cleanup error: {e}")

async def setup(bot):
    await bot.add_cog(DatabaseBackupCog(bot))

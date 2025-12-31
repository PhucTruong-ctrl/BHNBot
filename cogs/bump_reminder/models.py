"""Bump reminder data models.

Data classes for managing bump reminder state.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List
import aiosqlite

from .constants import DB_PATH


@dataclass
class BumpConfig:
    """Guild bump reminder configuration loaded from database.
    
    Attributes:
        guild_id: Discord guild ID
        bump_channel_id: Channel ID where reminders are sent
        bump_start_time: UTC datetime of last successful bump (ISO format)
        last_reminder_sent: UTC datetime of last reminder sent (ISO format)
    """
    guild_id: int
    bump_channel_id: int
    bump_start_time: Optional[str]  # ISO format UTC string
    last_reminder_sent: Optional[str]  # ISO format UTC string
    
    @staticmethod
    async def load_all(db) -> List['BumpConfig']:
        """Load all guild configurations with bump reminders enabled.
        
        Args:
            db: DatabaseManager instance
            
        Returns:
            List of BumpConfig objects for guilds with bump_channel_id set
            
        Raises:
            Exception: If database query fails
        """
        rows = await db.fetchall(
            "SELECT guild_id, bump_channel_id, bump_start_time, last_reminder_sent "
            "FROM server_config WHERE bump_channel_id IS NOT NULL"
        )
        
        return [
            BumpConfig(
                guild_id=row[0],
                bump_channel_id=row[1],
                bump_start_time=row[2],
                last_reminder_sent=row[3]
            )
            for row in rows
        ]
    
    async def update_bump_time(self, db: aiosqlite.Connection, bump_time: datetime) -> None:
        """Update bump_start_time and reset last_reminder_sent.
        
        Called when user successfully bumps the server.
        
        Args:
            db: Active aiosqlite database connection
            bump_time: UTC datetime of bump
            
        Raises:
            aiosqlite.Error: If database update fails
        """
        bump_time_iso = bump_time.isoformat()
        await db.modify(
            "UPDATE server_config SET bump_start_time = ?, last_reminder_sent = NULL WHERE guild_id = ?",
            (bump_time_iso, self.guild_id)
        )
        # PostgreSQL auto-commits, no manual commit needed
        self.bump_start_time = bump_time_iso
        self.last_reminder_sent = None
    
    async def update_reminder_time(self, db: aiosqlite.Connection, reminder_time: datetime) -> None:
        """Update last_reminder_sent timestamp.
        
        Called after successfully sending a bump reminder.
        
        Args:
            db: Active aiosqlite database connection
            reminder_time: UTC datetime of reminder sent
            
        Raises:
            aiosqlite.Error: If database update fails
        """
        reminder_time_iso = reminder_time.isoformat()
        await db.modify(
            "UPDATE server_config SET last_reminder_sent = ? WHERE guild_id = ?",
            (reminder_time_iso, self.guild_id)
        )
        # PostgreSQL auto-commits, no manual commit needed
        self.last_reminder_sent = reminder_time_iso
    
    async def initialize_bump_time(self, db: aiosqlite.Connection) -> None:
        """Initialize bump_start_time to NOW if NULL.
        
        Called when config exists but bump_start_time is NULL (first-time setup).
        
        Args:
            db: Active aiosqlite database connection
            
        Raises:
            aiosqlite.Error: If database update fails
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        await db.modify(
            "UPDATE server_config SET bump_start_time = ? WHERE guild_id = ?",
            (now_utc, self.guild_id)
        )
        # PostgreSQL auto-commits, no manual commit needed
        self.bump_start_time = now_utc

"""Data models for tree system.

Defines dataclasses for tree state, contributor tracking, and harvest buffs.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from core.logger import setup_logger
from database_manager import db_manager

from .constants import BASE_LEVEL_REQS, SEASON_SCALING, HARVEST_BUFF_HOURS

logger = setup_logger("TreeModels", "logs/cogs/tree.log")


# PERFORMANCE FIX #11: Module-level cache for TreeData
from .constants import TREE_DATA_CACHE_TTL_SECONDS

_tree_data_cache = {}  # {guild_id: (TreeData, timestamp)}
_tree_cache_ttl = TREE_DATA_CACHE_TTL_SECONDS


@dataclass
class TreeData:
    """Represents the state of a guild's community tree.
    
    Attributes:
        guild_id: Discord guild ID
        current_level: Tree level (1-6)
        current_progress: Seeds contributed toward next level
        total_contributed: Total seeds contributed across all seasons
        season: Current season number
        tree_channel_id: Channel ID where tree message is displayed
        tree_message_id: ID of pinned tree message
    """
    
    guild_id: int
    current_level: int
    current_progress: int
    total_contributed: int
    season: int
    tree_channel_id: Optional[int]
    tree_message_id: Optional[int]
    
    @classmethod
    async def load(cls, guild_id: int, force_refresh: bool = False) -> 'TreeData':
        """Load tree data for a guild, creating defaults if not exists.
        
        PERFORMANCE FIX #11: Uses 60s cache to reduce database queries.
        
        Args:
            guild_id: Discord guild ID
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            TreeData instance with current state
        """
        import time
        current_time = time.time()
        
        # Check cache
        if not force_refresh and guild_id in _tree_data_cache:
            tree_data, cached_at = _tree_data_cache[guild_id]
            if current_time - cached_at < _tree_cache_ttl:
                return tree_data
        
        try:
            row = await db_manager.fetchone(
                """SELECT current_level, current_progress, total_contributed, 
                   season, tree_channel_id, tree_message_id 
                   FROM server_tree WHERE guild_id = ?""",
                (guild_id,)
            )
            
            if not row:
                # Create default tree
                await db_manager.modify(
                    "INSERT INTO server_tree (guild_id) VALUES (?)",
                    (guild_id,)
                )
                tree_data = cls(
                    guild_id=guild_id,
                    current_level=1,
                    current_progress=0,
                    total_contributed=0,
                    season=1,
                    tree_channel_id=None,
                    tree_message_id=None
                )
            else:
                tree_data = cls(
                    guild_id=guild_id,
                    current_level=row[0],
                    current_progress=row[1],
                    total_contributed=row[2],
                    season=row[3],
                    tree_channel_id=row[4],
                    tree_message_id=row[5]
                )
            
            # Cache it
            _tree_data_cache[guild_id] = (tree_data, current_time)
            
            return tree_data
        except Exception as e:
            logger.error(f"Error loading tree data for guild {guild_id}: {e}", exc_info=True)
            raise
    
    async def save(self) -> None:
        """Save current tree state to database.
        
        PERFORMANCE FIX #11: Invalidates cache after save.
        """
        try:
            await db_manager.modify(
                """UPDATE server_tree 
                   SET current_level = ?, current_progress = ?, total_contributed = ?
                   WHERE guild_id = ?""",
                (self.current_level, self.current_progress, self.total_contributed, self.guild_id)
            )
            
            # Invalidate cache
            if self.guild_id in _tree_data_cache:
                del _tree_data_cache[self.guild_id]
                
        except Exception as e:
            logger.error(f"Error saving tree data for guild {self.guild_id}: {e}", exc_info=True)
            raise
    
    def get_level_requirements(self) -> Dict[int, int]:
        """Calculate level requirements for current season.
        
        Returns:
            Dictionary mapping level to seeds required
        """
        multiplier = SEASON_SCALING ** (self.season - 1)
        return {
            int(level): int(float(BASE_LEVEL_REQS[level]) * multiplier) if int(level) > 1 else 0
            for level in BASE_LEVEL_REQS
        }
    
    def get_next_level_requirement(self) -> int:
        """Get seeds required for next level.
        
        Returns:
            Number of seeds needed for next level
        """
        reqs = self.get_level_requirements()
        return reqs.get(self.current_level + 1, reqs[6])
    
    def calculate_progress_percent(self) -> int:
        """Calculate progress percentage for current level.
        
        Returns:
            Progress as percentage (0-100)
        """
        req = self.get_next_level_requirement()
        if self.current_level >= 6:
            return 100
        if req == 0:
            return 0
        return min(100, int((self.current_progress / req) * 100))
    
    def can_harvest(self) -> bool:
        """Check if tree is ready for harvest.
        
        Returns:
            True if level >= 6
        """
        return self.current_level >= 6


@dataclass
class ContributorData:
    """Represents a contributor's statistics for a season.
    
    Attributes:
        user_id: Discord user ID
        guild_id: Discord guild ID
        season: Season number
        amount: Total seeds contributed
        contribution_exp: Experience points earned
    """
    
    user_id: int
    guild_id: int
    season: int
    amount: int
    contribution_exp: int
    
    @classmethod
    async def load(cls, user_id: int, guild_id: int, season: int) -> Optional['ContributorData']:
        """Load contributor data for a user in a specific season.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            season: Season number
            
        Returns:
            ContributorData if exists, None otherwise
        """
        try:
            row = await db_manager.fetchone(
                """SELECT amount, contribution_exp 
                   FROM tree_contributors 
                   WHERE user_id = ? AND guild_id = ? AND season = ?""",
                (user_id, guild_id, season)
            )
            
            if not row:
                return None
            
            return cls(
                user_id=user_id,
                guild_id=guild_id,
                season=season,
                amount=row[0],
                contribution_exp=row[1]
            )
        except Exception as e:
            logger.error(f"Error loading contributor data: {e}", exc_info=True)
            return None
    
    @classmethod
    async def get_top_season(cls, guild_id: int, season: int, limit: int = 3) -> List['ContributorData']:
        """Get top contributors for a specific season.
        
        Args:
            guild_id: Discord guild ID
            season: Season number
            limit: Maximum number of contributors to return
            
        Returns:
            List of ContributorData sorted by amount descending
        """
        try:
            rows = await db_manager.execute(
                """SELECT user_id, amount, contribution_exp 
                   FROM tree_contributors 
                   WHERE guild_id = ? AND season = ? 
                   ORDER BY amount DESC LIMIT ?""",
                (guild_id, season, limit)
            )
            
            return [
                cls(
                    user_id=row[0],
                    guild_id=guild_id,
                    season=season,
                    amount=row[1],
                    contribution_exp=row[2]
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting top season contributors: {e}", exc_info=True)
            return []
    
    @classmethod
    async def get_top_all_time(cls, guild_id: int, limit: int = 3) -> List[Tuple[int, int]]:
        """Get top contributors across all seasons.
        
        Args:
            guild_id: Discord guild ID
            limit: Maximum number of contributors to return
            
        Returns:
            List of tuples (user_id, total_exp)
        """
        try:
            rows = await db_manager.execute(
                """SELECT user_id, SUM(contribution_exp) as total_exp 
                   FROM tree_contributors 
                   WHERE guild_id = ? 
                   GROUP BY user_id 
                   ORDER BY total_exp DESC LIMIT ?""",
                (guild_id, limit)
            )
            
            return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all-time contributors: {e}", exc_info=True)
            return []
    
    async def add_contribution(self, amount: int, exp: int) -> None:
        """Add contribution to this contributor's record.
        
        Creates new record if doesn't exist, updates existing otherwise.
        
        Args:
            amount: Seeds to add
            exp: Experience points to add
        """
        try:
            # Check if exists
            existing = await ContributorData.load(self.user_id, self.guild_id, self.season)
            
            if existing:
                # Update existing
                new_amount = existing.amount + amount
                new_exp = existing.contribution_exp + exp
                await db_manager.modify(
                    """UPDATE tree_contributors 
                       SET amount = ?, contribution_exp = ? 
                       WHERE user_id = ? AND guild_id = ? AND season = ?""",
                    (new_amount, new_exp, self.user_id, self.guild_id, self.season)
                )
                self.amount = new_amount
                self.contribution_exp = new_exp
            else:
                # Insert new
                await db_manager.modify(
                    """INSERT INTO tree_contributors 
                       (user_id, guild_id, season, amount, contribution_exp) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (self.user_id, self.guild_id, self.season, amount, exp)
                )
                self.amount = amount
                self.contribution_exp = exp
                
        except Exception as e:
            logger.error(f"Error adding contribution: {e}", exc_info=True)
            raise


@dataclass
class HarvestBuff:
    """Represents a server-wide buff after harvest.
    
    Attributes:
        guild_id: Discord guild ID
        buff_until: Datetime when buff expires
    """
    
    guild_id: int
    buff_until: datetime
    
    @classmethod
    async def is_active(cls, guild_id: int) -> bool:
        """Check if harvest buff is currently active for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if buff is active
        """
        try:
            row = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"harvest_buff_{guild_id}",
                cache_ttl=60
            )
            
            if not row or not row[0]:
                return False
            
            buff_until = row[0]
            # PostgreSQL returns datetime, legacy SQLite returns string
            if isinstance(buff_until, str):
                buff_until = datetime.fromisoformat(buff_until)
            return datetime.now() < buff_until
        except Exception as e:
            logger.error(f"Error checking harvest buff: {e}", exc_info=True)
            return False
    
    @classmethod
    async def activate(cls, guild_id: int, hours: int = HARVEST_BUFF_HOURS) -> 'HarvestBuff':
        """Activate harvest buff for a guild.
        
        Args:
            guild_id: Discord guild ID
            hours: Duration of buff in hours
            
        Returns:
            HarvestBuff instance
        """
        try:
            from database_manager import set_server_config
            
            buff_until = datetime.now() + timedelta(hours=hours)
            await set_server_config(guild_id, 'harvest_buff_until', buff_until.isoformat())
            
            logger.info(f"[HARVEST_BUFF] Activated {hours}h buff for guild {guild_id}")
            
            return cls(guild_id=guild_id, buff_until=buff_until)
        except Exception as e:
            logger.error(f"Error activating harvest buff: {e}", exc_info=True)
            raise
    
    def get_remaining_time(self) -> timedelta:
        """Get remaining buff duration.
        
        Returns:
            Timedelta until buff expires
        """
        return self.buff_until - datetime.now()
    
    def get_timestamp_for_discord(self) -> int:
        """Get Unix timestamp for Discord timestamp formatting.
        
        Returns:
            Unix timestamp
        """
        return int(self.buff_until.timestamp())

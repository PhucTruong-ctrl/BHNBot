"""
Economy Repository - Database abstraction for economy operations.

Provides clean interface for all database operations related to economy system.
"""

from typing import Optional, List, Tuple
from datetime import datetime
from core.database import db_manager
from core.logging import get_logger

logger = get_logger("EconomyRepository")


class EconomyRepository:
    """Repository for economy-related database operations."""
    
    async def get_or_create_user(self, user_id: int, username: str) -> Optional[Tuple[int, str, int]]:
        """Get or create user and return (user_id, username, seeds)."""
        try:
            user = await db_manager.fetchone(
                "SELECT user_id, username, seeds FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not user:
                logger.info(f"Creating new user: {username} ({user_id})")
                await db_manager.modify(
                    "INSERT INTO users (user_id, username, seeds) VALUES (?, ?, 0)",
                    (user_id, username)
                )
                user = (user_id, username, 0)
            
            return user
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return None
    
    async def get_user_balance(self, user_id: int) -> int:
        """Get user seeds balance."""
        row = await db_manager.fetchone("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
        return row[0] if row else 0
    
    async def add_seeds(self, user_id: int, amount: int, reason: str = "unknown", category: str = "general") -> int:
        """Add seeds to user and return new balance."""
        return await db_manager.add_seeds(user_id, amount, reason, category)
    
    async def get_leaderboard(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get top users by seeds."""
        return await db_manager.get_leaderboard(limit)
    
    async def get_last_daily(self, user_id: int) -> Optional[datetime]:
        """Get last daily reward timestamp."""
        result = await db_manager.fetchrow(
            "SELECT last_daily FROM users WHERE user_id = ?",
            (user_id,)
        )
        if result and result['last_daily']:
            return result['last_daily']
        return None
    
    async def update_last_daily(self, user_id: int):
        """Update last daily reward timestamp."""
        await db_manager.execute(
            "UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
    
    async def get_streak_data(self, user_id: int) -> Tuple[int, bool]:
        """Get daily streak and protection status."""
        result = await db_manager.fetchrow(
            "SELECT daily_streak, streak_protection FROM users WHERE user_id = ?",
            (user_id,)
        )
        if result:
            return (result['daily_streak'] or 0, result['streak_protection'] or False)
        return (0, False)
    
    async def update_streak(self, user_id: int, streak: int, protection: bool):
        """Update daily streak and protection."""
        await db_manager.execute(
            "UPDATE users SET daily_streak = ?, streak_protection = ? WHERE user_id = ?",
            (streak, protection, user_id)
        )
    
    async def claim_daily_atomic(
        self, 
        user_id: int, 
        reward_amount: int, 
        new_streak: int, 
        new_protection: bool,
        reason: str = "daily_reward",
        category: str = "social"
    ) -> int:
        """Atomically claim daily reward - updates seeds, last_daily, and streak in one transaction."""
        async with db_manager.transaction() as conn:
            await conn.execute(
                "UPDATE users SET seeds = seeds + ?, last_daily = CURRENT_TIMESTAMP, "
                "daily_streak = ?, streak_protection = ? WHERE user_id = ?",
                reward_amount, new_streak, new_protection, user_id
            )
            result = await conn.fetchval("SELECT seeds FROM users WHERE user_id = ?", user_id)
            await db_manager.log_transaction(
                user_id, reward_amount, reason, category, 
                balance_before=result - reward_amount if result else 0,
                balance_after=result or 0,
                conn=conn
            )
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
        return result or 0
    
    async def update_last_chat_reward(self, user_id: int):
        """Update last chat reward timestamp."""
        await db_manager.execute(
            "UPDATE users SET last_chat_reward = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
    
    async def is_harvest_buff_active(self, guild_id: int) -> bool:
        """Check if harvest buff is active for guild."""
        try:
            result = await db_manager.fetchrow(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"harvest_buff_{guild_id}",
                cache_ttl=60
            )
            
            if not result or not result['harvest_buff_until']:
                return False
            
            buff_until = result['harvest_buff_until']
            return datetime.now() < buff_until
        except Exception as e:
            return False
    
    async def get_excluded_channels(self, guild_id: int) -> List[int]:
        """Get list of excluded channels for guild."""
        try:
            result = await db_manager.fetchrow(
                "SELECT logs_channel_id, exclude_chat_channels FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"excluded_channels_{guild_id}",
                cache_ttl=600
            )
            
            excluded = []
            if result:
                if result['logs_channel_id']:
                    excluded.append(result['logs_channel_id'])
                
                if result['exclude_chat_channels']:
                    try:
                        import json
                        parsed = json.loads(result['exclude_chat_channels'])
                        excluded.extend(parsed)
                    except Exception as e:
                        logger.error(f"Error parsing exclude_chat_channels: {e}")
            
            return excluded
        except Exception as e:
            return []

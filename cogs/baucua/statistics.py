"""Statistics tracking for Bau Cua achievements.

Tracks game statistics and triggers achievement checks.
"""

from typing import Dict
from core.logger import setup_logger
from database_manager import db_manager

logger = setup_logger("BauCuaStats", "logs/cogs/baucua.log")


class StatisticsTracker:
    """Manages statistics tracking for achievement system.
    
    Tracks various game stats including:
    - Games played
    - Total won/lost amounts
    - Triple wins (jackpot)
    
    All stats are stored in user_stats table with game_id='baucua'.
    """
    
    def __init__(self, bot):
        """Initialize statistics tracker.
        
        Args:
            bot: Discord bot instance (for achievement manager access)
        """
        self.bot = bot
    
    async def increment_stat(self, user_id: int, stat_key: str, value: int) -> None:
        """Increment a user's statistic value.
        
        Creates new stat entry if it doesn't exist, otherwise increments.
        
        Args:
            user_id: Discord user ID
            stat_key: Stat identifier (e.g., 'baucua_played')
            value: Amount to increment by
            
        Note:
            Uses 'baucua' as game_id for all stats
        """
        try:
            game_id = 'baucua'
            
            # Check if stat exists
            sql_check = """
                SELECT value FROM user_stats 
                WHERE user_id = ? AND game_id = ? AND stat_key = ?
            """
            row = await db_manager.fetchone(sql_check, (user_id, game_id, stat_key))
            
            if row:
                # Update existing stat
                sql_update = """
                    UPDATE user_stats 
                    SET value = value + ? 
                    WHERE user_id = ? AND game_id = ? AND stat_key = ?
                """
                await db_manager.execute(sql_update, (value, user_id, game_id, stat_key))
            else:
                # Insert new stat
                sql_insert = """
                    INSERT INTO user_stats (user_id, game_id, stat_key, value) 
                    VALUES (?, ?, ?, ?)
                """
                await db_manager.execute(sql_insert, (user_id, game_id, stat_key, value))
                
            logger.debug(f"Incremented stat {stat_key} by {value} for user {user_id}")
            
        except Exception as e:
            logger.error(
                f"Error updating stat {stat_key} for user {user_id}: {e}",
                exc_info=True
            )
    
    async def get_stat_value(self, user_id: int, stat_key: str) -> int:
        """Get current value of a user's statistic.
        
        Args:
            user_id: Discord user ID
            stat_key: Stat identifier
            
        Returns:
            Current stat value, or 0 if stat doesn't exist
        """
        try:
            game_id = 'baucua'
            sql = """
                SELECT value FROM user_stats 
                WHERE user_id = ? AND game_id = ? AND stat_key = ?
            """
            row = await db_manager.fetchone(sql, (user_id, game_id, stat_key))
            return row[0] if row else 0
            
        except Exception as e:
            logger.error(
                f"Error getting stat {stat_key} for user {user_id}: {e}",
                exc_info=True
            )
            return 0
    
    async def update_game_stats(
        self,
        channel_id: int,
        results: tuple,
        bets_data: Dict
    ) -> None:
        """Update statistics for all players after game completes.
        
        Tracks:
        - baucua_played: +1 for each player
        - baucua_total_won: Total seeds won
        - baucua_total_lost: Total seeds lost
        - baucua_triple_wins: Incremented if player bet on triple result
        
        Args:
            channel_id: Discord channel ID (for achievement notifications)
            results: Tuple of (result1, result2, result3)
            bets_data: Dict mapping user_id to list of (animal_key, amount) tuples
        """
        result1, result2, result3 = results
        final_result = [result1, result2, result3]
        
        # Check for triple (jackpot) result
        is_triple_result = (result1 == result2 == result3)
        
        for user_id, bet_list in bets_data.items():
            try:
                user_winnings = 0
                user_losses = 0
                triple_hit = 0
                
                for animal_key, bet_amount in bet_list:
                    matches = sum(1 for r in final_result if r == animal_key)
                    
                    if matches > 0:
                        # Calculate payout: bet_amount * (matches + 1)
                        payout = bet_amount * (matches + 1)
                        profit = payout - bet_amount
                        user_winnings += profit
                        
                        # Check if user hit triple (bet on correct animal that appeared 3x)
                        if matches == 3:
                            triple_hit = 1
                    else:
                        # Lost bet
                        user_losses += bet_amount
                
                # Update all stats for this user
                await self.increment_stat(user_id, 'baucua_played', 1)
                
                if user_winnings > 0:
                    await self.increment_stat(user_id, 'baucua_total_won', user_winnings)
                
                if user_losses > 0:
                    await self.increment_stat(user_id, 'baucua_total_lost', user_losses)
                
                if triple_hit > 0:
                    await self.increment_stat(user_id, 'baucua_triple_wins', 1)
                
                # Trigger achievement checks
                await self._check_achievements(user_id, channel_id, {
                    'played': user_winnings > 0 or user_losses > 0,
                    'won': user_winnings,
                    'lost': user_losses,
                    'triple': triple_hit
                })
                
            except Exception as e:
                logger.error(
                    f"Error updating stats for user {user_id}: {e}",
                    exc_info=True
                )
    
    async def _check_achievements(
        self,
        user_id: int,
        channel_id: int,
        updates: Dict
    ) -> None:
        """Check and unlock achievements based on stat updates.
        
        Args:
            user_id: User to check achievements for
            channel_id: Channel to send achievement notifications
            updates: Dict with keys: 'played', 'won', 'lost', 'triple'
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            # Check games played achievement
            if updates['played']:
                current_played = await self.get_stat_value(user_id, 'baucua_played')
                await self.bot.achievement_manager.check_unlock(
                    user_id, "baucua", "baucua_played", current_played, channel
                )
            
            # Check total won achievement
            if updates['won'] > 0:
                current_won = await self.get_stat_value(user_id, 'baucua_total_won')
                await self.bot.achievement_manager.check_unlock(
                    user_id, "baucua", "baucua_total_won", current_won, channel
                )
            
            # Check total lost achievement
            if updates['lost'] > 0:
                current_lost = await self.get_stat_value(user_id, 'baucua_total_lost')
                await self.bot.achievement_manager.check_unlock(
                    user_id, "baucua", "baucua_total_lost", current_lost, channel
                )
            
            # Check triple wins achievement
            if updates['triple'] > 0:
                current_triple = await self.get_stat_value(user_id, 'baucua_triple_wins')
                await self.bot.achievement_manager.check_unlock(
                    user_id, "baucua", "baucua_triple_wins", current_triple, channel
                )
                
        except Exception as e:
            logger.error(
                f"Error checking achievements for user {user_id}: {e}",
                exc_info=True
            )

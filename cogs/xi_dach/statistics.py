"""Statistics tracking for Xi Dach (Blackjack) achievements.

Tracks game statistics and triggers achievement checks.
"""

from typing import Dict, List
from core.logging import get_logger
from database_manager import db_manager

logger = get_logger("XiDachStats")

class StatisticsTracker:
    """Manages statistics tracking for Xi Dach achievement system.
    
    Tracks various game stats using 'xidach' as game_id.
    """
    
    def __init__(self, bot):
        """Initialize statistics tracker."""
        self.bot = bot
    
    async def increment_stat(self, user_id: int, stat_key: str, value: int = 1) -> None:
        """Increment a user's statistic value.
        
        Args:
            user_id: Discord user ID
            stat_key: Stat identifier
            value: Amount to increment by
        """
        try:
            game_id = 'xidach'
            
            # Check if stat exists
            sql_check = "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?"
            row = await db_manager.fetchone(sql_check, (user_id, game_id, stat_key))
            
            if row:
                sql_update = "UPDATE user_stats SET value = value + ? WHERE user_id = ? AND game_id = ? AND stat_key = ?"
                await db_manager.execute(sql_update, (value, user_id, game_id, stat_key))
            else:
                sql_insert = "INSERT INTO user_stats (user_id, game_id, stat_key, value) VALUES (?, ?, ?, ?)"
                await db_manager.execute(sql_insert, (user_id, game_id, stat_key, value))
                
        except Exception as e:
            logger.error(f"[STATS] Error updating {stat_key} for {user_id}: {e}")

    async def get_stat_value(self, user_id: int, stat_key: str) -> int:
        """Get current value of a user's statistic."""
        game_id = 'xidach'
        sql = "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?"
        row = await db_manager.fetchone(sql, (user_id, game_id, stat_key))
        return row[0] if row else 0

    async def update_game_stats(self, channel_id: int, player_results: List[Dict]) -> None:
        """Update statistics for players after game completes.
        
        Args:
            channel_id: Channel ID for notifications.
            player_results: List of dicts with keys:
                - user_id: int
                - result: str ('win', 'lose', 'push')
                - payout: int
                - hand_type: HandType enum or str
                - is_bust: bool
        """
        from .services.hand_service import HandType  # Local import
        
        for p in player_results:
            uid = p['user_id']
            result = p['result']
            payout = p['payout']
            hand_type = p['hand_type']
            is_bust = p.get('is_bust', False)
            
            try:
                updates = {
                    'played': True,
                    'won_amount': 0,
                    'win': False,
                    'ngu_linh': False,
                    'xi_ban': False,
                    'bust': False
                }
                
                # 1. Games Played
                await self.increment_stat(uid, 'xidach_played', 1)
                
                # 2. Wins & Money
                if result == 'win':
                    await self.increment_stat(uid, 'xidach_wins', 1)
                    updates['win'] = True
                    
                    if payout > 0:
                        await self.increment_stat(uid, 'xidach_total_won', payout)
                        updates['won_amount'] = payout
                
                # 3. Special Hands
                if hand_type == HandType.NGU_LINH:
                    await self.increment_stat(uid, 'xidach_ngu_linh_wins', 1)
                    updates['ngu_linh'] = True
                
                if hand_type == HandType.XI_BAN:
                    await self.increment_stat(uid, 'xidach_xi_ban_count', 1)
                    updates['xi_ban'] = True
                    
                # 4. Bust
                if is_bust:
                    await self.increment_stat(uid, 'xidach_bust_count', 1)
                    updates['bust'] = True
                    
                # TRIGGER CHECK
                await self._check_unlocks(uid, channel_id, updates)
                
            except Exception as e:
                logger.error(f"[STATS] Failed to update stats for {uid}: {e}", exc_info=True)

    async def _check_unlocks(self, user_id: int, channel_id: int, updates: Dict) -> None:
        """Check against achievement criteria."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel: return
            
            manager = self.bot.achievement_manager
            
            # Novice
            if updates['played']:
                val = await self.get_stat_value(user_id, 'xidach_played')
                await manager.check_unlock(user_id, 'xidach', 'xidach_played', val, channel)
                
            # Expert (Wins)
            if updates['win']:
                val = await self.get_stat_value(user_id, 'xidach_wins')
                await manager.check_unlock(user_id, 'xidach', 'xidach_wins', val, channel)

            # Tycoon (Money)
            if updates['won_amount'] > 0:
                val = await self.get_stat_value(user_id, 'xidach_total_won')
                await manager.check_unlock(user_id, 'xidach', 'xidach_total_won', val, channel)
                
            # Ngu Linh
            if updates['ngu_linh']:
                val = await self.get_stat_value(user_id, 'xidach_ngu_linh_wins')
                await manager.check_unlock(user_id, 'xidach', 'xidach_ngu_linh_wins', val, channel)

            # Xi Ban
            if updates['xi_ban']:
                val = await self.get_stat_value(user_id, 'xidach_xi_ban_count')
                await manager.check_unlock(user_id, 'xidach', 'xidach_xi_ban_count', val, channel)
                
            # Bust
            if updates['bust']:
                val = await self.get_stat_value(user_id, 'xidach_bust_count')
                await manager.check_unlock(user_id, 'xidach', 'xidach_bust_count', val, channel)
                
        except Exception as e:
            logger.error(f"[STATS] Unlock check error: {e}")

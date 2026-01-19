"""Contributor tracking and ranking management.

Manages contributor statistics, rankings, and reward calculations.
"""

from typing import List, Dict, Tuple
from core.logging import get_logger
from database_manager import db_manager

from .constants import HARVEST_REWARDS
from .models import ContributorData
from .helpers import get_contribution_exp

logger = get_logger("ContributorManager")


class ContributorManager:
    """Manages contributor tracking and rankings.
    
    Handles:
    - Adding contributions
    - Getting top contributors (season + all-time)
    - Calculating harvest rewards
    - Giving memorabilia items
    """
    
    def __init__(self, bot):
        """Initialize contributor manager.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    async def add_contribution(
        self,
        user_id: int,
        guild_id: int,
        season: int,
        amount: int,
        contribution_type: str = "seeds"
    ) -> None:
        """Add contribution to user's record for current season.
        
        Experience calculation:
        - Hạt: 1 hạt = 1 exp
        - Phan bon: amount = exp (50-100 range)
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            season: Current season number
            amount: Amount contributed (seeds or phan_bon value)
            contribution_type: 'seeds' or 'phan_bon'
        """
        try:
            # Calculate experience
            exp = get_contribution_exp(contribution_type, amount)
            
            # Load or create contributor data
            contributor = await ContributorData.load(user_id, guild_id, season)
            
            if not contributor:
                contributor = ContributorData(
                    user_id=user_id,
                    guild_id=guild_id,
                    season=season,
                    amount=0,
                    contribution_exp=0
                )
            
            # Add contribution
            await contributor.add_contribution(amount, exp)
            
            logger.info(
                f"[CONTRIB_ADD] user_id={user_id} season={season} amount={amount} "
                f"exp={exp} type={contribution_type}"
            )
            
        except Exception as e:
            logger.error(f"Error adding contribution: {e}", exc_info=True)
            raise
    
    async def get_top_contributors_season(
        self,
        guild_id: int,
        season: int,
        limit: int = 3
    ) -> List[ContributorData]:
        """Get top contributors for a specific season.
        
        Args:
            guild_id: Discord guild ID
            season: Season number
            limit: Maximum number to return
            
        Returns:
            List of ContributorData sorted by amount descending
        """
        return await ContributorData.get_top_season(guild_id, season, limit)
    
    async def get_top_contributors_all_time(
        self,
        guild_id: int,
        limit: int = 3
    ) -> List[Tuple[int, int]]:
        """Get top contributors across all seasons.
        
        Args:
            guild_id: Discord guild ID
            limit: Maximum number to return
            
        Returns:
            List of (user_id, total_exp) tuples
        """
        return await ContributorData.get_top_all_time(guild_id, limit)
    
    async def get_all_season_contributors(
        self,
        guild_id: int,
        season: int
    ) -> List[Tuple[int, int]]:
        """Get ALL contributors for a season (for harvest rewards).
        
        Args:
            guild_id: Discord guild ID
            season: Season number
            
        Returns:
            List of (user_id, contribution_exp) tuples sorted by exp descending
        """
        try:
            rows = await db_manager.execute(
                """SELECT user_id, contribution_exp 
                   FROM tree_contributors 
                   WHERE guild_id = ? AND season = ? 
                   ORDER BY contribution_exp DESC""",
                (guild_id, season)
            )
            
            return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all season contributors: {e}", exc_info=True)
            return []
    
    def calculate_harvest_rewards(
        self,
        contributors: List[Tuple[int, int]]
    ) -> Dict[int, int]:
        """Calculate seed rewards for harvest based on rank.
        
        SECURITY FIX #3: Validates total rewards don't exceed cap.
        
        Rewards:
        - Top 1: 10,000 seeds
        - Top 2: 5,000 seeds
        - Top 3: 3,000 seeds
        - Others: 1,500 seeds
        
        Args:
            contributors: List of (user_id, exp) tuples sorted by exp
            
        Returns:
            Dictionary mapping user_id to seed reward amount
            
        Raises:
            ValueError: If total rewards exceed MAX_TOTAL_REWARDS
        """
        from .constants import MAX_TOTAL_REWARDS
        
        rewards = {}
        total_rewards = 0
        
        for idx, (user_id, exp) in enumerate(contributors):
            if idx == 0:  # Top 1
                reward = HARVEST_REWARDS['top1']
            elif idx == 1:  # Top 2
                reward = HARVEST_REWARDS['top2']
            elif idx == 2:  # Top 3
                reward = HARVEST_REWARDS['top3']
            else:  # Others
                reward = HARVEST_REWARDS['others']
            
            rewards[user_id] = reward
            total_rewards += reward
        
        # Add bonus for top 1
        if contributors:
            top1_user_id = contributors[0][0]
            bonus = HARVEST_REWARDS['top1_bonus']
            rewards[top1_user_id] += bonus
            total_rewards += bonus
        
        # SECURITY: Validate total doesn't exceed cap
        if total_rewards > MAX_TOTAL_REWARDS:
            logger.error(
                f"[HARVEST_OVERFLOW] Total rewards {total_rewards:,} exceeds cap {MAX_TOTAL_REWARDS:,}"
            )
            raise ValueError(
                f"Harvest rewards exceed maximum allowed: {total_rewards:,} > {MAX_TOTAL_REWARDS:,}"
            )
        
        logger.info(
            f"[HARVEST_REWARDS] Calculated rewards for {len(contributors)} contributors: "
            f"Total={total_rewards:,} seeds"
        )
        
        return rewards
    
    async def give_memorabilia_items(
        self,
        contributors: List[Tuple[int, int]],
        season: int
    ) -> None:
        """Give memorabilia items to all contributors.
        
        Args:
            contributors: List of (user_id, exp) tuples
            season: Season number for item name
        """
        try:
            memorabilia_key = f"qua_ngot_mua_{season}"
            
            for user_id, _ in contributors:
                # [CACHE] Use bot.inventory.modify
                await self.bot.inventory.modify(user_id, memorabilia_key, 1)
            
            logger.info(
                f"[MEMORABILIA] Gave {memorabilia_key} to {len(contributors)} contributors"
            )
            
        except Exception as e:
            logger.error(f"Error giving memorabilia items: {e}", exc_info=True)
            raise

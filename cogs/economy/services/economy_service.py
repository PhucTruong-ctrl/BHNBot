"""
Economy Service - Business logic orchestration for economy system.

Combines core business logic with data access through repository.
"""

from typing import Optional, List, Tuple
from datetime import datetime
from cogs.economy.repositories.economy_repository import EconomyRepository
from cogs.economy.core.economy_core import EconomyCore
from core.logging import get_logger

logger = get_logger("EconomyService")


class EconomyService:
    """Service for economy business operations."""
    
    def __init__(self, repository: EconomyRepository):
        self.repository = repository
    
    async def get_or_create_user(self, user_id: int, username: str) -> Optional[Tuple[int, str, int]]:
        """Get or create user."""
        return await self.repository.get_or_create_user(user_id, username)
    
    async def get_user_balance(self, user_id: int) -> int:
        """Get user balance."""
        return await self.repository.get_user_balance(user_id)
    
    async def add_seeds(self, user_id: int, amount: int, reason: str = "unknown", category: str = "general") -> int:
        """Add seeds to user."""
        if not EconomyCore.validate_seed_amount(amount):
            raise ValueError("Amount must be positive")
        
        balance_before = await self.get_user_balance(user_id)
        new_balance = await self.repository.add_seeds(user_id, amount, reason, category)
        
        logger.info(
            f"[ECONOMY] [SEED_UPDATE] user_id={user_id} seed_change={amount} "
            f"balance_before={balance_before} balance_after={new_balance} reason={reason}"
        )
        
        return new_balance
    
    async def get_leaderboard(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get leaderboard."""
        return await self.repository.get_leaderboard(limit)
    
    async def claim_daily_reward(self, user_id: int, username: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Process daily reward claim.
        
        Returns:
            Tuple[bool, str, Optional[dict]]: (success, message, reward_data)
        """
        # Check if in daily window
        if not EconomyCore.is_daily_window():
            now = datetime.now()
            return False, f"❌ Chỉ nhận hạt từ 5h tới 10h sáng!\nGiờ hiện tại: {now.strftime('%H:%M')}", None
        
        # Check if already claimed today
        last_daily = await self.repository.get_last_daily(user_id)
        if not EconomyCore.can_claim_daily(last_daily):
            return False, "❌ Bạn đã nhận hạt hôm nay rồi! Quay lại vào ngày mai.", None
        
        # Get current streak data
        current_streak, has_protection = await self.repository.get_streak_data(user_id)
        
        # Calculate reward
        total_reward, new_streak, protection_used, streak_lost = EconomyCore.calculate_daily_reward(
            current_streak, has_protection, last_daily
        )
        
        new_protection = new_streak >= 7 and not protection_used
        
        # Update database
        await self.add_seeds(user_id, total_reward, 'daily_reward', 'social')
        await self.repository.update_last_daily(user_id)
        await self.repository.update_streak(user_id, new_streak, new_protection)
        
        # Prepare response data
        reward_data = {
            'total_reward': total_reward,
            'base_reward': EconomyCore.DAILY_BONUS,
            'streak_bonus': EconomyCore.calculate_streak_bonus(new_streak),
            'current_streak': new_streak,
            'has_protection': new_protection,
            'protection_used': protection_used,
            'streak_lost': streak_lost,
            'previous_streak': current_streak if streak_lost else None
        }
        
        return True, "Daily reward claimed successfully", reward_data
    
    async def process_chat_reward(self, user_id: int, username: str, guild_id: int, channel_id: int) -> Optional[int]:
        """
        Process chat activity reward.
        
        Returns:
            Optional[int]: Reward amount if given, None if no reward
        """
        # Check excluded channels
        excluded_channels = await self.repository.get_excluded_channels(guild_id)
        if channel_id in excluded_channels:
            return None
        
        # Check cooldown (implement in-memory cache in future)
        # For now, assume repository handles this
        
        # Check harvest buff
        is_buff_active = await self.repository.is_harvest_buff_active(guild_id)
        
        # Calculate reward
        reward = EconomyCore.calculate_chat_reward(is_buff_active)
        
        # Add seeds
        await self.add_seeds(user_id, reward, 'chat_reward', 'social')
        await self.repository.update_last_chat_reward(user_id)
        
        logger.info(
            f"[ECONOMY] [CHAT_REWARD] user_id={user_id} username={username} "
            f"reward={reward} buff_active={is_buff_active}"
        )
        
        return reward
    
    async def process_voice_reward(self, user_id: int, username: str, guild_id: int, 
                                 party_size: int, music_playing: bool) -> int:
        """Process voice channel reward."""
        # Check harvest buff
        is_buff_active = await self.repository.is_harvest_buff_active(guild_id)
        
        # Calculate reward (10 minutes interval, 5 seeds base)
        base_reward = 5
        reward = EconomyCore.calculate_voice_reward(base_reward, party_size, is_buff_active, music_playing)
        
        # Add seeds
        await self.add_seeds(user_id, reward, 'voice_reward', 'social')
        
        logger.info(
            f"[ECONOMY] [VOICE_REWARD] user_id={user_id} username={username} "
            f"reward={reward} buff={is_buff_active} party={party_size} music={music_playing}"
        )
        
        return reward
    
    async def admin_add_seeds(self, user_id: int, amount: int, admin_id: int, admin_name: str) -> Tuple[bool, str]:
        """Admin function to add seeds."""
        if not EconomyCore.validate_seed_amount(amount):
            return False, "❌ Số lượng phải lớn hơn 0!"
        
        # Ensure user exists
        await self.get_or_create_user(user_id, f"User#{user_id}")
        
        # Add seeds
        new_balance = await self.add_seeds(user_id, amount, 'admin_adjustment', 'system')
        
        logger.info(
            f"[ADMIN] [SEED_GRANT] actor={admin_name} actor_id={admin_id} "
            f"target_id={user_id} amount={amount}"
        )
        
        return True, f"Added {amount} seeds. New balance: {new_balance}"

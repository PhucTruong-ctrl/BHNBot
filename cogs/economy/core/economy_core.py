"""
Economy Core - Pure business logic for economy system.

Contains all calculations and business rules without external dependencies.
"""

from datetime import datetime, time
from typing import Tuple, Optional
import random


class EconomyCore:
    """Core business logic for economy operations."""
    
    # Constants
    DAILY_BONUS = 10
    DAILY_WINDOW_START = 5  # 5 AM
    DAILY_WINDOW_END = 10   # 10 AM
    CHAT_REWARD_MIN = 1
    CHAT_REWARD_MAX = 3
    STREAK_BONUS_PER_DAY = 5
    MAX_STREAK_BONUS = 100
    
    @staticmethod
    def calculate_streak_bonus(streak: int) -> int:
        """Calculate bonus seeds for daily streak."""
        return min(streak * EconomyCore.STREAK_BONUS_PER_DAY, EconomyCore.MAX_STREAK_BONUS)
    
    @staticmethod
    def is_daily_window() -> bool:
        """Check if current time is within daily reward window."""
        now = datetime.now()
        return EconomyCore.DAILY_WINDOW_START <= now.hour < EconomyCore.DAILY_WINDOW_END
    
    @staticmethod
    def calculate_daily_reward(current_streak: int, has_protection: bool, last_daily: Optional[datetime]) -> Tuple[int, int, bool, bool]:
        """
        Calculate daily reward details.
        
        Returns:
            Tuple[int, int, bool, bool]: (total_reward, new_streak, protection_used, streak_lost)
        """
        today = datetime.now().date()
        new_streak = current_streak
        protection_used = False
        streak_lost = False
        
        if last_daily:
            days_missed = (today - last_daily.date()).days - 1
            
            if days_missed == 0:
                new_streak = current_streak + 1
            elif days_missed == 1 and has_protection:
                new_streak = current_streak + 1
                protection_used = True
            elif days_missed >= 1:
                new_streak = 1
                streak_lost = current_streak > 0
        else:
            new_streak = 1
        
        new_protection = new_streak >= 7 and not protection_used
        streak_bonus = EconomyCore.calculate_streak_bonus(new_streak)
        total_reward = EconomyCore.DAILY_BONUS + streak_bonus
        
        return total_reward, new_streak, protection_used, streak_lost
    
    @staticmethod
    def calculate_chat_reward(is_buff_active: bool) -> int:
        """Calculate chat reward amount."""
        reward = random.randint(EconomyCore.CHAT_REWARD_MIN, EconomyCore.CHAT_REWARD_MAX)
        if is_buff_active:
            reward *= 2
        return reward
    
    @staticmethod
    def calculate_voice_reward(base_reward: int, party_size: int, is_buff_active: bool, music_playing: bool) -> int:
        """Calculate voice channel reward."""
        reward = base_reward
        if is_buff_active:
            reward *= 2
        
        # Party bonus: +20% per extra person
        party_multiplier = 1.0 + ((party_size - 1) * 0.2)
        reward = int(reward * party_multiplier)
        
        # Music bonus
        if music_playing:
            reward += 2
            
        return reward
    
    @staticmethod
    def validate_seed_amount(amount: int) -> bool:
        """Validate seed amount for operations."""
        return amount > 0
    
    @staticmethod
    def can_claim_daily(last_daily: Optional[datetime]) -> bool:
        """Check if user can claim daily reward."""
        if not last_daily:
            return True
        
        today = datetime.now().date()
        return last_daily.date() != today

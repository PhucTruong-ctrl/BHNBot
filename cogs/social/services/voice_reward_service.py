"""Voice reward service - rewards users for voice activity."""
from datetime import date, datetime
from typing import Optional
from dataclasses import dataclass

from core.database import db_manager
from core.logging import setup_logger

logger = setup_logger("VoiceRewardService", "cogs/social.log")

REWARD_PER_INTERVAL = 10
REWARD_INTERVAL_SECONDS = 600
DAILY_CAP = 300
BUDDY_BONUS_PERCENT = 20


@dataclass
class VoiceRewardData:
    user_id: int
    guild_id: int
    rewarded_seconds: int
    total_rewards_today: int
    last_reward_at: Optional[datetime]
    voice_streak: int
    last_voice_date: Optional[date]

    @property
    def streak_bonus(self) -> int:
        if self.voice_streak >= 30:
            return 5
        elif self.voice_streak >= 14:
            return 3
        elif self.voice_streak >= 7:
            return 2
        return 0

    @property
    def can_earn_more(self) -> bool:
        return self.total_rewards_today < DAILY_CAP


class VoiceRewardService:

    @staticmethod
    async def ensure_table() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS voice_rewards (
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                rewarded_seconds BIGINT DEFAULT 0,
                total_rewards_today INT DEFAULT 0,
                last_reward_at TIMESTAMP,
                last_reward_date DATE,
                voice_streak INT DEFAULT 0,
                last_voice_date DATE,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    @staticmethod
    async def get_reward_data(user_id: int, guild_id: int) -> VoiceRewardData:
        today = date.today()
        
        row = await db_manager.fetchone(
            """SELECT user_id, guild_id, rewarded_seconds, total_rewards_today,
                      last_reward_at, last_reward_date, voice_streak, last_voice_date
               FROM voice_rewards
               WHERE user_id = $1 AND guild_id = $2""",
            (user_id, guild_id)
        )
        
        if row:
            last_reward_date = row[5]
            total_today = row[3] if last_reward_date == today else 0
            
            return VoiceRewardData(
                user_id=row[0],
                guild_id=row[1],
                rewarded_seconds=row[2] or 0,
                total_rewards_today=total_today,
                last_reward_at=row[4],
                voice_streak=row[6] or 0,
                last_voice_date=row[7]
            )
        
        return VoiceRewardData(
            user_id=user_id,
            guild_id=guild_id,
            rewarded_seconds=0,
            total_rewards_today=0,
            last_reward_at=None,
            voice_streak=0,
            last_voice_date=None
        )

    @staticmethod
    async def calculate_and_grant_reward(
        user_id: int,
        guild_id: int,
        session_seconds: int,
        has_buddy_online: bool = False
    ) -> tuple[int, int]:
        """Calculate reward for voice session and grant it.
        
        Returns (base_reward, bonus_reward)
        """
        await VoiceRewardService.ensure_table()
        
        data = await VoiceRewardService.get_reward_data(user_id, guild_id)
        today = date.today()
        
        if not data.can_earn_more:
            return 0, 0
        
        intervals = session_seconds // REWARD_INTERVAL_SECONDS
        if intervals <= 0:
            return 0, 0
        
        base_reward = intervals * REWARD_PER_INTERVAL
        
        remaining_cap = DAILY_CAP - data.total_rewards_today
        base_reward = min(base_reward, remaining_cap)
        
        if base_reward <= 0:
            return 0, 0
        
        bonus_reward = 0
        if has_buddy_online:
            bonus_reward += int(base_reward * BUDDY_BONUS_PERCENT / 100)
        
        bonus_reward += data.streak_bonus * intervals
        
        total_reward = base_reward + bonus_reward
        
        new_streak = data.voice_streak
        if data.last_voice_date is None:
            new_streak = 1
        elif data.last_voice_date == today:
            pass
        elif (today - data.last_voice_date).days == 1:
            new_streak = data.voice_streak + 1
        elif (today - data.last_voice_date).days > 1:
            new_streak = 1
        
        await db_manager.execute(
            """INSERT INTO voice_rewards 
               (user_id, guild_id, rewarded_seconds, total_rewards_today, 
                last_reward_at, last_reward_date, voice_streak, last_voice_date)
               VALUES ($1, $2, $3, $4, NOW(), $5, $6, $5)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   rewarded_seconds = voice_rewards.rewarded_seconds + $3,
                   total_rewards_today = CASE 
                       WHEN voice_rewards.last_reward_date = $5 
                       THEN voice_rewards.total_rewards_today + $4
                       ELSE $4
                   END,
                   last_reward_at = NOW(),
                   last_reward_date = $5,
                   voice_streak = $6,
                   last_voice_date = $5""",
            (user_id, guild_id, session_seconds, base_reward + bonus_reward, today, new_streak)
        )
        
        from cogs.economy import EconomyCog
        await db_manager.execute(
            """UPDATE economy SET balance = balance + $1 
               WHERE user_id = $2 AND guild_id = $3""",
            (total_reward, user_id, guild_id)
        )
        
        logger.info(
            f"Voice reward: {user_id} in {guild_id} earned {base_reward}+{bonus_reward} Hạt "
            f"({session_seconds}s, streak={new_streak})"
        )
        
        return base_reward, bonus_reward

    @staticmethod
    async def get_daily_stats(user_id: int, guild_id: int) -> tuple[int, int, int]:
        """Get today's voice reward stats.
        
        Returns (earned_today, remaining_cap, voice_streak)
        """
        data = await VoiceRewardService.get_reward_data(user_id, guild_id)
        remaining = max(0, DAILY_CAP - data.total_rewards_today)
        return data.total_rewards_today, remaining, data.voice_streak

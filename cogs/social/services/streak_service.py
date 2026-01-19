"""Kindness streak tracking service.

Tracks daily kind actions and provides streak bonuses.
"""
from datetime import date, timedelta
from typing import Optional
from dataclasses import dataclass

from core.database import db_manager
from core.logging import setup_logger

logger = setup_logger("StreakService", "cogs/social.log")

STREAK_MULTIPLIERS = {
    7: 1.10,
    14: 1.15,
    30: 1.25,
    60: 1.35,
    90: 1.50,
}


@dataclass
class StreakData:
    user_id: int
    guild_id: int
    current_streak: int
    longest_streak: int
    last_kind_action: Optional[date]
    streak_protected: bool

    @property
    def multiplier(self) -> float:
        result = 1.0
        for threshold, mult in sorted(STREAK_MULTIPLIERS.items()):
            if self.current_streak >= threshold:
                result = mult
        return result

    @property
    def next_milestone(self) -> Optional[int]:
        for threshold in sorted(STREAK_MULTIPLIERS.keys()):
            if self.current_streak < threshold:
                return threshold
        return None

    @property
    def days_to_next_milestone(self) -> Optional[int]:
        next_ms = self.next_milestone
        if next_ms:
            return next_ms - self.current_streak
        return None


class StreakService:

    @staticmethod
    async def ensure_table() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS kindness_streaks (
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                current_streak INT DEFAULT 0,
                longest_streak INT DEFAULT 0,
                last_kind_action DATE,
                streak_protected BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    @staticmethod
    async def get_streak(user_id: int, guild_id: int) -> StreakData:
        row = await db_manager.fetchone(
            """SELECT user_id, guild_id, current_streak, longest_streak, 
                      last_kind_action, streak_protected
               FROM kindness_streaks 
               WHERE user_id = $1 AND guild_id = $2""",
            (user_id, guild_id)
        )
        
        if row:
            return StreakData(
                user_id=row[0],
                guild_id=row[1],
                current_streak=row[2] or 0,
                longest_streak=row[3] or 0,
                last_kind_action=row[4],
                streak_protected=row[5] or False
            )
        
        return StreakData(
            user_id=user_id,
            guild_id=guild_id,
            current_streak=0,
            longest_streak=0,
            last_kind_action=None,
            streak_protected=False
        )

    @staticmethod
    async def record_kind_action(user_id: int, guild_id: int) -> tuple[StreakData, bool]:
        """Record a kind action and update streak.
        
        Returns (StreakData, streak_increased: bool)
        """
        await StreakService.ensure_table()
        
        today = date.today()
        current = await StreakService.get_streak(user_id, guild_id)
        
        if current.last_kind_action == today:
            return current, False
        
        new_streak = current.current_streak
        streak_increased = False
        
        if current.last_kind_action is None:
            new_streak = 1
            streak_increased = True
        elif current.last_kind_action == today - timedelta(days=1):
            new_streak = current.current_streak + 1
            streak_increased = True
        elif current.last_kind_action < today - timedelta(days=1):
            if current.streak_protected:
                new_streak = current.current_streak
                await db_manager.execute(
                    """UPDATE kindness_streaks SET streak_protected = FALSE
                       WHERE user_id = $1 AND guild_id = $2""",
                    (user_id, guild_id)
                )
                logger.info(f"Streak protection used: {user_id} in guild {guild_id}")
            else:
                new_streak = 1
                streak_increased = True
        
        new_longest = max(current.longest_streak, new_streak)
        
        await db_manager.execute(
            """INSERT INTO kindness_streaks 
               (user_id, guild_id, current_streak, longest_streak, last_kind_action)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   current_streak = $3,
                   longest_streak = $4,
                   last_kind_action = $5""",
            (user_id, guild_id, new_streak, new_longest, today)
        )
        
        updated = await StreakService.get_streak(user_id, guild_id)
        return updated, streak_increased

    @staticmethod
    async def add_streak_protection(user_id: int, guild_id: int) -> bool:
        await StreakService.ensure_table()
        
        current = await StreakService.get_streak(user_id, guild_id)
        if current.streak_protected:
            return False
        
        await db_manager.execute(
            """INSERT INTO kindness_streaks (user_id, guild_id, streak_protected)
               VALUES ($1, $2, TRUE)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   streak_protected = TRUE""",
            (user_id, guild_id)
        )
        return True

    @staticmethod
    async def apply_streak_multiplier(base_score: int, user_id: int, guild_id: int) -> int:
        streak = await StreakService.get_streak(user_id, guild_id)
        return int(base_score * streak.multiplier)

    @staticmethod
    async def get_streak_leaderboard(guild_id: int, limit: int = 10) -> list[tuple[int, int, int]]:
        rows = await db_manager.fetchall(
            """SELECT user_id, current_streak, longest_streak
               FROM kindness_streaks
               WHERE guild_id = $1 AND current_streak > 0
               ORDER BY current_streak DESC, longest_streak DESC
               LIMIT $2""",
            (guild_id, limit)
        )
        return [(row[0], row[1], row[2]) for row in rows]

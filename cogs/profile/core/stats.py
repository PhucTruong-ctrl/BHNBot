from dataclasses import dataclass
from typing import Optional

from core.database import db_manager
from cogs.social.services.voice_service import VoiceService
from cogs.social.services.kindness_service import KindnessService


@dataclass
class ProfileStats:
    seeds: int
    fish_caught: int
    voice_hours: float
    kindness_score: int
    daily_streak: int
    achievements: list[str]
    rank: int
    total_users: int


async def get_seeds(user_id: int) -> int:
    row = await db_manager.fetchone(
        "SELECT seeds FROM users WHERE user_id = $1",
        (user_id,)
    )
    return row[0] if row else 0


async def get_daily_streak(user_id: int) -> int:
    row = await db_manager.fetchone(
        "SELECT daily_streak FROM users WHERE user_id = $1",
        (user_id,)
    )
    return row[0] if row else 0


async def count_fish_collection(user_id: int) -> int:
    row = await db_manager.fetchone(
        "SELECT COUNT(*) FROM fish_collection WHERE user_id = $1",
        (user_id,)
    )
    return row[0] if row else 0


async def get_rank(user_id: int) -> tuple[int, int]:
    all_users = await db_manager.fetchall(
        "SELECT user_id FROM users ORDER BY seeds DESC"
    )
    total = len(all_users)
    rank = 0
    for i, row in enumerate(all_users, 1):
        if row[0] == user_id:
            rank = i
            break
    return (rank, total)


async def get_top_achievements(user_id: int, limit: int = 4) -> list[str]:
    rows = await db_manager.fetchall(
        """SELECT achievement_key FROM user_achievements
           WHERE user_id = $1
           ORDER BY unlocked_at DESC
           LIMIT $2""",
        (user_id, limit)
    )
    return [row[0] for row in rows] if rows else []


async def get_user_stats(user_id: int, guild_id: int) -> ProfileStats:
    seeds = await get_seeds(user_id)
    fish_caught = await count_fish_collection(user_id)
    voice_hours = await VoiceService.get_total_hours(user_id, guild_id)

    kindness_stats = await KindnessService.get_stats(user_id, guild_id)
    kindness_score = kindness_stats.score

    daily_streak = await get_daily_streak(user_id)
    achievements = await get_top_achievements(user_id, limit=4)
    rank, total_users = await get_rank(user_id)

    return ProfileStats(
        seeds=seeds,
        fish_caught=fish_caught,
        voice_hours=voice_hours,
        kindness_score=kindness_score,
        daily_streak=daily_streak,
        achievements=achievements,
        rank=rank,
        total_users=total_users,
    )

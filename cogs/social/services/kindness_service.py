import re
from typing import Optional
from dataclasses import dataclass

from core.database import db_manager


THANKS_PATTERNS = [
    re.compile(r'\bcảm ơn\b', re.IGNORECASE),
    re.compile(r'\bcám ơn\b', re.IGNORECASE),
    re.compile(r'\bcamon\b', re.IGNORECASE),
    re.compile(r'\bthanks?\b', re.IGNORECASE),
    re.compile(r'\bthank you\b', re.IGNORECASE),
    re.compile(r'\bty\b', re.IGNORECASE),
    re.compile(r'\btysm\b', re.IGNORECASE),
]


@dataclass
class KindnessStats:
    user_id: int
    guild_id: int
    reactions_given: int
    reactions_received: int
    thanks_given: int
    thanks_received: int
    gifts_given: int
    gifts_received: int

    @property
    def score(self) -> int:
        return (
            self.reactions_given * 1 +
            int(self.reactions_received * 0.5) +
            self.thanks_given * 2 +
            self.thanks_received * 1 +
            self.gifts_given * 5 +
            self.gifts_received * 2
        )


class KindnessService:

    @staticmethod
    async def ensure_table() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS kindness_stats (
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                reactions_given INT DEFAULT 0,
                reactions_received INT DEFAULT 0,
                thanks_given INT DEFAULT 0,
                thanks_received INT DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    @staticmethod
    async def get_stats(user_id: int, guild_id: int) -> KindnessStats:
        row = await db_manager.fetchone(
            """SELECT user_id, guild_id, reactions_given, reactions_received,
                      thanks_given, thanks_received
               FROM kindness_stats WHERE user_id = $1 AND guild_id = $2""",
            (user_id, guild_id)
        )

        gifts_given = await KindnessService._count_gifts_given(user_id, guild_id)
        gifts_received = await KindnessService._count_gifts_received(user_id, guild_id)

        if row:
            return KindnessStats(
                user_id=row[0],
                guild_id=row[1],
                reactions_given=row[2] or 0,
                reactions_received=row[3] or 0,
                thanks_given=row[4] or 0,
                thanks_received=row[5] or 0,
                gifts_given=gifts_given,
                gifts_received=gifts_received,
            )
        return KindnessStats(
            user_id=user_id,
            guild_id=guild_id,
            reactions_given=0,
            reactions_received=0,
            thanks_given=0,
            thanks_received=0,
            gifts_given=gifts_given,
            gifts_received=gifts_received,
        )

    @staticmethod
    async def _count_gifts_given(user_id: int, guild_id: int) -> int:
        try:
            row = await db_manager.fetchone(
                """SELECT COUNT(*) FROM gift_history
                   WHERE sender_id = $1 AND guild_id = $2""",
                (user_id, guild_id)
            )
            return row[0] if row else 0
        except Exception:
            return 0

    @staticmethod
    async def _count_gifts_received(user_id: int, guild_id: int) -> int:
        try:
            row = await db_manager.fetchone(
                """SELECT COUNT(*) FROM gift_history
                   WHERE receiver_id = $1 AND guild_id = $2""",
                (user_id, guild_id)
            )
            return row[0] if row else 0
        except Exception:
            return 0

    @staticmethod
    async def increment_reaction_given(user_id: int, guild_id: int) -> None:
        await db_manager.execute(
            """INSERT INTO kindness_stats (user_id, guild_id, reactions_given)
               VALUES ($1, $2, 1)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   reactions_given = kindness_stats.reactions_given + 1""",
            (user_id, guild_id)
        )

    @staticmethod
    async def increment_reaction_received(user_id: int, guild_id: int) -> None:
        await db_manager.execute(
            """INSERT INTO kindness_stats (user_id, guild_id, reactions_received)
               VALUES ($1, $2, 1)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   reactions_received = kindness_stats.reactions_received + 1""",
            (user_id, guild_id)
        )

    @staticmethod
    async def increment_thanks_given(user_id: int, guild_id: int) -> None:
        await db_manager.execute(
            """INSERT INTO kindness_stats (user_id, guild_id, thanks_given)
               VALUES ($1, $2, 1)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   thanks_given = kindness_stats.thanks_given + 1""",
            (user_id, guild_id)
        )

    @staticmethod
    async def increment_thanks_received(user_id: int, guild_id: int) -> None:
        await db_manager.execute(
            """INSERT INTO kindness_stats (user_id, guild_id, thanks_received)
               VALUES ($1, $2, 1)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   thanks_received = kindness_stats.thanks_received + 1""",
            (user_id, guild_id)
        )

    @staticmethod
    def contains_thanks(content: str) -> bool:
        for pattern in THANKS_PATTERNS:
            if pattern.search(content):
                return True
        return False

    @staticmethod
    async def get_leaderboard(guild_id: int, limit: int = 10) -> list[tuple[int, int]]:
        rows = await db_manager.fetchall(
            """SELECT user_id,
                      (reactions_given * 1 + 
                       CAST(reactions_received * 0.5 AS INT) +
                       thanks_given * 2 + 
                       thanks_received * 1) as base_score
               FROM kindness_stats
               WHERE guild_id = $1
               ORDER BY base_score DESC
               LIMIT $2""",
            (guild_id, limit)
        )

        result = []
        for row in rows:
            user_id = row[0]
            stats = await KindnessService.get_stats(user_id, guild_id)
            result.append((user_id, stats.score))

        result.sort(key=lambda x: x[1], reverse=True)
        return result[:limit]

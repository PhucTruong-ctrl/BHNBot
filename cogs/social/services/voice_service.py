from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from core.database import db_manager


@dataclass
class VoiceStats:
    user_id: int
    guild_id: int
    total_seconds: int
    sessions_count: int
    last_session_start: Optional[datetime]

    @property
    def total_hours(self) -> float:
        return round(self.total_seconds / 3600, 1)


class VoiceService:

    @staticmethod
    async def ensure_table() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS voice_stats (
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                total_seconds BIGINT DEFAULT 0,
                sessions_count INT DEFAULT 0,
                last_session_start TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    @staticmethod
    async def get_stats(user_id: int, guild_id: int) -> VoiceStats:
        row = await db_manager.fetchone(
            """SELECT user_id, guild_id, total_seconds, sessions_count, last_session_start
               FROM voice_stats WHERE user_id = $1 AND guild_id = $2""",
            (user_id, guild_id)
        )
        if row:
            return VoiceStats(
                user_id=row[0],
                guild_id=row[1],
                total_seconds=row[2] or 0,
                sessions_count=row[3] or 0,
                last_session_start=row[4],
            )
        return VoiceStats(
            user_id=user_id,
            guild_id=guild_id,
            total_seconds=0,
            sessions_count=0,
            last_session_start=None,
        )

    @staticmethod
    async def start_session(user_id: int, guild_id: int) -> None:
        await db_manager.execute(
            """INSERT INTO voice_stats (user_id, guild_id, last_session_start, sessions_count)
               VALUES ($1, $2, $3, 1)
               ON CONFLICT (user_id, guild_id) DO UPDATE SET
                   last_session_start = $3,
                   sessions_count = voice_stats.sessions_count + 1""",
            (user_id, guild_id, datetime.utcnow())
        )

    @staticmethod
    async def end_session(user_id: int, guild_id: int) -> int:
        stats = await VoiceService.get_stats(user_id, guild_id)
        if not stats.last_session_start:
            return 0

        duration = int((datetime.utcnow() - stats.last_session_start).total_seconds())
        if duration < 0:
            duration = 0

        await db_manager.execute(
            """UPDATE voice_stats
               SET total_seconds = total_seconds + $3,
                   last_session_start = NULL
               WHERE user_id = $1 AND guild_id = $2""",
            (user_id, guild_id, duration)
        )
        return duration

    @staticmethod
    async def flush_active_sessions(guild_id: int) -> int:
        rows = await db_manager.fetchall(
            """SELECT user_id, last_session_start FROM voice_stats
               WHERE guild_id = $1 AND last_session_start IS NOT NULL""",
            (guild_id,)
        )
        if not rows:
            return 0

        now = datetime.utcnow()
        count = 0
        for row in rows:
            user_id = row[0]
            start_time = row[1]
            if start_time:
                duration = int((now - start_time).total_seconds())
                if duration > 0:
                    await db_manager.execute(
                        """UPDATE voice_stats
                           SET total_seconds = total_seconds + $3,
                               last_session_start = $4
                           WHERE user_id = $1 AND guild_id = $2""",
                        (user_id, guild_id, duration, now)
                    )
                    count += 1
        return count

    @staticmethod
    async def get_total_hours(user_id: int, guild_id: int) -> float:
        stats = await VoiceService.get_stats(user_id, guild_id)
        return stats.total_hours

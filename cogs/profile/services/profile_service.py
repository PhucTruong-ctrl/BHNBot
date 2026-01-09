from typing import Optional
from dataclasses import dataclass

from core.database import db_manager


DEFAULT_BIO = "Một người bạn thân thiện 🌸"


@dataclass
class UserProfile:
    user_id: int
    theme: str
    badges_display: Optional[str]
    bio: str


class ProfileService:

    @staticmethod
    async def ensure_table() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id BIGINT PRIMARY KEY,
                theme VARCHAR(32) DEFAULT 'forest',
                badges_display VARCHAR(256),
                bio VARCHAR(200) DEFAULT 'Một người bạn thân thiện 🌸'
            )
        """)

    @staticmethod
    async def get_profile(user_id: int) -> UserProfile:
        row = await db_manager.fetchone(
            "SELECT user_id, theme, badges_display, bio FROM user_profiles WHERE user_id = $1",
            (user_id,)
        )
        if row:
            return UserProfile(
                user_id=row[0],
                theme=row[1] or "forest",
                badges_display=row[2],
                bio=row[3] or DEFAULT_BIO,
            )
        return UserProfile(
            user_id=user_id,
            theme="forest",
            badges_display=None,
            bio=DEFAULT_BIO,
        )

    @staticmethod
    async def set_theme(user_id: int, theme: str) -> None:
        await db_manager.execute(
            """INSERT INTO user_profiles (user_id, theme)
               VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET theme = $2""",
            (user_id, theme)
        )

    @staticmethod
    async def set_bio(user_id: int, bio: str) -> None:
        bio = bio[:200]
        await db_manager.execute(
            """INSERT INTO user_profiles (user_id, bio)
               VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET bio = $2""",
            (user_id, bio)
        )

    @staticmethod
    async def set_badges_display(user_id: int, badges: list[str]) -> None:
        import json
        badges_json = json.dumps(badges[:8])
        await db_manager.execute(
            """INSERT INTO user_profiles (user_id, badges_display)
               VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET badges_display = $2""",
            (user_id, badges_json)
        )

    @staticmethod
    async def get_badges_display(user_id: int) -> list[str]:
        import json
        profile = await ProfileService.get_profile(user_id)
        if profile.badges_display:
            try:
                return json.loads(profile.badges_display)
            except json.JSONDecodeError:
                return []
        return []

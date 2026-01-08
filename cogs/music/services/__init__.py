from __future__ import annotations

from typing import Optional, List
from datetime import datetime

from core.database import db_manager
from ..core import UserPlaylist, PlaylistTrack


class PlaylistService:

    @staticmethod
    async def ensure_tables() -> None:
        await db_manager.execute('''
            CREATE TABLE IF NOT EXISTS user_playlists (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, guild_id, name)
            )
        ''')
        await db_manager.execute('''
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id SERIAL PRIMARY KEY,
                playlist_id INT REFERENCES user_playlists(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                uri VARCHAR(500) NOT NULL,
                author VARCHAR(200),
                duration_ms INT DEFAULT 0,
                position INT NOT NULL,
                added_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await db_manager.execute('''
            CREATE INDEX IF NOT EXISTS idx_playlists_user_guild 
            ON user_playlists(user_id, guild_id)
        ''')
        await db_manager.execute('''
            CREATE INDEX IF NOT EXISTS idx_tracks_playlist 
            ON playlist_tracks(playlist_id, position)
        ''')

    @staticmethod
    async def create_playlist(user_id: int, guild_id: int, name: str) -> Optional[int]:
        try:
            row = await db_manager.fetchone('''
                INSERT INTO user_playlists (user_id, guild_id, name)
                VALUES ($1, $2, $3)
                RETURNING id
            ''', user_id, guild_id, name)
            return row[0] if row else None
        except Exception:
            return None

    @staticmethod
    async def get_playlist(user_id: int, guild_id: int, name: str) -> Optional[UserPlaylist]:
        row = await db_manager.fetchone('''
            SELECT id, user_id, guild_id, name, created_at
            FROM user_playlists
            WHERE user_id = $1 AND guild_id = $2 AND LOWER(name) = LOWER($3)
        ''', user_id, guild_id, name)

        if not row:
            return None

        tracks = await PlaylistService._get_tracks(row[0])
        return UserPlaylist(
            id=row[0],
            user_id=row[1],
            guild_id=row[2],
            name=row[3],
            created_at=row[4],
            tracks=tracks
        )

    @staticmethod
    async def get_playlist_by_id(playlist_id: int) -> Optional[UserPlaylist]:
        row = await db_manager.fetchone('''
            SELECT id, user_id, guild_id, name, created_at
            FROM user_playlists WHERE id = $1
        ''', playlist_id)

        if not row:
            return None

        tracks = await PlaylistService._get_tracks(playlist_id)
        return UserPlaylist(
            id=row[0],
            user_id=row[1],
            guild_id=row[2],
            name=row[3],
            created_at=row[4],
            tracks=tracks
        )

    @staticmethod
    async def _get_tracks(playlist_id: int) -> List[PlaylistTrack]:
        rows = await db_manager.fetchall('''
            SELECT id, playlist_id, title, uri, author, duration_ms, position, added_at
            FROM playlist_tracks
            WHERE playlist_id = $1
            ORDER BY position ASC
        ''', playlist_id)

        return [
            PlaylistTrack(
                id=r[0],
                playlist_id=r[1],
                title=r[2],
                uri=r[3],
                author=r[4] or "Unknown",
                duration_ms=r[5],
                position=r[6],
                added_at=r[7]
            )
            for r in rows
        ]

    @staticmethod
    async def list_playlists(user_id: int, guild_id: int) -> List[UserPlaylist]:
        rows = await db_manager.fetchall('''
            SELECT id, user_id, guild_id, name, created_at
            FROM user_playlists
            WHERE user_id = $1 AND guild_id = $2
            ORDER BY name ASC
        ''', user_id, guild_id)

        playlists = []
        for row in rows:
            tracks = await PlaylistService._get_tracks(row[0])
            playlists.append(UserPlaylist(
                id=row[0],
                user_id=row[1],
                guild_id=row[2],
                name=row[3],
                created_at=row[4],
                tracks=tracks
            ))
        return playlists

    @staticmethod
    async def add_track(
        playlist_id: int,
        title: str,
        uri: str,
        author: str,
        duration_ms: int
    ) -> bool:
        try:
            max_pos_row = await db_manager.fetchone('''
                SELECT COALESCE(MAX(position), 0)
                FROM playlist_tracks WHERE playlist_id = $1
            ''', playlist_id)
            next_position = (max_pos_row[0] if max_pos_row else 0) + 1

            await db_manager.execute('''
                INSERT INTO playlist_tracks (playlist_id, title, uri, author, duration_ms, position)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', playlist_id, title, uri, author, duration_ms, next_position)
            return True
        except Exception:
            return False

    @staticmethod
    async def remove_track(playlist_id: int, position: int) -> bool:
        try:
            result = await db_manager.execute('''
                DELETE FROM playlist_tracks
                WHERE playlist_id = $1 AND position = $2
            ''', playlist_id, position)

            await db_manager.execute('''
                UPDATE playlist_tracks
                SET position = position - 1
                WHERE playlist_id = $1 AND position > $2
            ''', playlist_id, position)

            return result is not None and "DELETE" in str(result)
        except Exception:
            return False

    @staticmethod
    async def delete_playlist(user_id: int, guild_id: int, name: str) -> bool:
        try:
            result = await db_manager.execute('''
                DELETE FROM user_playlists
                WHERE user_id = $1 AND guild_id = $2 AND LOWER(name) = LOWER($3)
            ''', user_id, guild_id, name)
            return result is not None and "DELETE" in str(result)
        except Exception:
            return False

    @staticmethod
    async def rename_playlist(user_id: int, guild_id: int, old_name: str, new_name: str) -> bool:
        try:
            result = await db_manager.execute('''
                UPDATE user_playlists
                SET name = $4
                WHERE user_id = $1 AND guild_id = $2 AND LOWER(name) = LOWER($3)
            ''', user_id, guild_id, old_name, new_name)
            return result is not None and "UPDATE" in str(result)
        except Exception:
            return False

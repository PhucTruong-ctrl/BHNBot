from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class PlaylistTrack:
    id: int
    playlist_id: int
    title: str
    uri: str
    author: str
    duration_ms: int
    position: int
    added_at: datetime


@dataclass
class UserPlaylist:
    id: int
    user_id: int
    guild_id: int
    name: str
    created_at: datetime
    tracks: List[PlaylistTrack]

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    @property
    def total_duration_ms(self) -> int:
        return sum(t.duration_ms for t in self.tracks)

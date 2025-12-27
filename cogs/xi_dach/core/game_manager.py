"""Game Manager Singleton."""

import time
from typing import Dict, Optional
from .table import Table, TableStatus

class GameManager:
    """Singleton manager for all active Xi Dach tables."""
    _instance: Optional["GameManager"] = None

    def __new__(cls) -> "GameManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tables: Dict[int, Table] = {}  # channel_id -> Table
            cls._instance._user_tables: Dict[int, int] = {}  # user_id -> channel_id
        return cls._instance

    @property
    def tables(self) -> Dict[int, Table]:
        return self._tables

    def create_table(
        self,
        channel_id: int,
        host_id: int,
        is_solo: bool = False
    ) -> Optional[Table]:
        if channel_id in self._tables:
            return None

        table_id = f"xd_{channel_id}_{int(time.time() * 1000)}"
        table = Table(
            table_id=table_id,
            channel_id=channel_id,
            host_id=host_id,
            is_solo=is_solo
        )
        self._tables[channel_id] = table
        self._user_tables[host_id] = channel_id
        return table

    def get_table(self, channel_id: int) -> Optional[Table]:
        return self._tables.get(channel_id)

    def get_user_table(self, user_id: int) -> Optional[Table]:
        channel_id = self._user_tables.get(user_id)
        if channel_id:
            return self._tables.get(channel_id)
        return None

    def remove_table(self, channel_id: int) -> None:
        table = self._tables.pop(channel_id, None)
        if table:
            for user_id in table.players:
                self._user_tables.pop(user_id, None)

    def add_user_to_table(self, user_id: int, channel_id: int) -> None:
        self._user_tables[user_id] = channel_id

    def cleanup_old_tables(self, max_age_seconds: int = 600) -> int:
        now = time.time()
        to_remove = [
            cid for cid, table in self._tables.items()
            if now - table.created_at > max_age_seconds
        ]
        for cid in to_remove:
            self.remove_table(cid)
        return len(to_remove)

# Global singleton instance
game_manager = GameManager()

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
            cls._instance._tables: Dict[str, Table] = {}  # table_id -> Table
            cls._instance._channel_tables: Dict[int, Set[str]] = {} # channel_id -> Set[table_id]
            cls._instance._user_tables: Dict[int, str] = {}  # user_id -> table_id (host only mapping? No, player mapping)
        return cls._instance

    @property
    def tables(self) -> Dict[str, Table]:
        return self._tables

    def create_table(
        self,
        channel_id: int,
        host_id: int,
        is_solo: bool = False
    ) -> Optional[Table]:
        # Initialize channel set if needed
        if channel_id not in self._channel_tables:
            self._channel_tables[channel_id] = set()

        # Check limit (Max 3 tables per channel)
        if len(self._channel_tables[channel_id]) >= 3:
            return None

        # Check if user is already playing elsewhere
        if host_id in self._user_tables:
            return None # User busy

        table_id = f"xd_{channel_id}_{int(time.time() * 1000)}"
        table = Table(
            table_id=table_id,
            channel_id=channel_id,
            host_id=host_id,
            is_solo=is_solo
        )
        
        self._tables[table_id] = table
        self._channel_tables[channel_id].add(table_id)
        self._user_tables[host_id] = table_id
        
        return table

    def get_table(self, table_id: str) -> Optional[Table]:
        """Get table by ID."""
        return self._tables.get(table_id)

    def get_user_table(self, user_id: int) -> Optional[Table]:
        """Get the table a user is currently participating in."""
        table_id = self._user_tables.get(user_id)
        if table_id:
            return self._tables.get(table_id)
        return None

    def remove_table(self, table_id: str) -> None:
        """Remove a table by its uniquely identified table_id."""
        table = self._tables.pop(table_id, None)
        if table:
            # Remove from channel tracking
            if table.channel_id in self._channel_tables:
                self._channel_tables[table.channel_id].discard(table_id)
                if not self._channel_tables[table.channel_id]:
                    del self._channel_tables[table.channel_id]

            # Remove all players from user tracking
            for user_id in list(table.players.keys()):
                self._user_tables.pop(user_id, None)

    def add_user_to_table(self, user_id: int, table_id: str) -> None:
        self._user_tables[user_id] = table_id

    def cleanup_old_tables(self, max_age_seconds: int = 600) -> int:
        now = time.time()
        to_remove = [
            tid for tid, table in self._tables.items()
            if now - table.created_at > max_age_seconds
        ]
        for tid in to_remove:
            self.remove_table(tid)
        return len(to_remove)

# Global singleton instance
game_manager = GameManager()

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from .event_types import EventConfig, EventRegistryEntry, get_registry_settings, load_registry

if TYPE_CHECKING:
    from discord.ext.commands import Bot

logger = logging.getLogger(__name__)


class EventManager:
    _instance: EventManager | None = None
    _initialized: bool = False

    def __new__(cls, bot: Bot | None = None) -> EventManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, bot: Bot | None = None) -> None:
        if EventManager._initialized:
            return

        self.bot = bot
        self._registry: dict[str, EventRegistryEntry] = {}
        self._configs: dict[str, EventConfig] = {}
        self._active_events: dict[int, str] = {}  # guild_id -> event_id
        self._settings: dict = {}

        self._load_registry()
        EventManager._initialized = True

    def _load_registry(self) -> None:
        self._registry = load_registry()
        self._settings = get_registry_settings()

        for event_id, entry in self._registry.items():
            self._configs[event_id] = EventConfig.load(entry)

        logger.info(f"Loaded {len(self._registry)} events from registry")

    def reload(self) -> None:
        self._registry.clear()
        self._configs.clear()
        self._load_registry()

    def get_event(self, event_id: str) -> EventConfig | None:
        return self._configs.get(event_id)

    def get_registry_entry(self, event_id: str) -> EventRegistryEntry | None:
        return self._registry.get(event_id)

    def get_all_events(self) -> list[EventConfig]:
        return list(self._configs.values())

    def get_current_event(self, now: datetime | None = None) -> EventConfig | None:
        if now is None:
            now = datetime.now()

        for event_id, entry in self._registry.items():
            if entry.is_active(now):
                return self._configs.get(event_id)

        return None

    def get_active_event_for_guild(self, guild_id: int) -> EventConfig | None:
        event_id = self._active_events.get(guild_id)
        if event_id:
            return self._configs.get(event_id)
        return None

    def set_active_event(self, guild_id: int, event_id: str) -> bool:
        if event_id not in self._configs:
            return False
        self._active_events[guild_id] = event_id
        return True

    def clear_active_event(self, guild_id: int) -> None:
        self._active_events.pop(guild_id, None)

    def is_event_active(self, guild_id: int) -> bool:
        return guild_id in self._active_events

    @property
    def settings(self) -> dict:
        return self._settings

    @property
    def auto_start(self) -> bool:
        return self._settings.get("auto_start", True)

    @property
    def timezone(self) -> str:
        return self._settings.get("timezone", "Asia/Ho_Chi_Minh")

    @property
    def event_fish_chance(self) -> float:
        return self._settings.get("event_fish_chance", 0.15)


def get_event_manager(bot: Bot | None = None) -> EventManager:
    return EventManager(bot)

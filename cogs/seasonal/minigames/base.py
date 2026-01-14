from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

MINIGAME_REGISTRY: dict[str, type[BaseMinigame]] = {}


def register_minigame(name: str):
    def decorator(cls: type[BaseMinigame]) -> type[BaseMinigame]:
        MINIGAME_REGISTRY[name] = cls
        return cls
    return decorator


class BaseMinigame(ABC):
    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        self.bot = bot
        self.event_manager = event_manager

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def spawn_config(self) -> dict[str, Any]:
        pass

    @abstractmethod
    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        pass

    @abstractmethod
    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    def is_scheduled(self) -> bool:
        return self.spawn_config.get("spawn_type") in ("scheduled", "mixed")

    def is_random(self) -> bool:
        return self.spawn_config.get("spawn_type") in ("random", "mixed")

    def get_scheduled_times(self) -> list[str]:
        return self.spawn_config.get("scheduled_times", [])

    def get_random_times_per_day(self) -> tuple[int, int]:
        times = self.spawn_config.get("times_per_day", [3, 5])
        if isinstance(times, list) and len(times) == 2:
            return (times[0], times[1])
        return (3, 5)

    def get_active_hours(self) -> tuple[int, int]:
        hours = self.spawn_config.get("active_hours", [8, 23])
        if isinstance(hours, list) and len(hours) == 2:
            return (hours[0], hours[1])
        return (8, 23)


def get_minigame(name: str, bot: Any, event_manager: EventManager) -> BaseMinigame | None:
    cls = MINIGAME_REGISTRY.get(name)
    if cls:
        return cls(bot, event_manager)
    return None


def get_all_minigames(bot: Any, event_manager: EventManager) -> list[BaseMinigame]:
    return [cls(bot, event_manager) for cls in MINIGAME_REGISTRY.values()]

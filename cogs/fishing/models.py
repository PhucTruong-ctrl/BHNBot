"""Data models for fishing game."""

from enum import Enum
from dataclasses import dataclass

class RodLevel(Enum):
    """Rod levels."""
    BAMBOO = 1
    GLASS = 2
    CARBON = 3
    ALLOY = 4
    POSEIDON = 5

@dataclass
class RodData:
    """Rod state."""
    level: int
    durability: int

@dataclass
class CatchResult:
    """Single fishing result."""
    triggered_event: bool
    event_key: str | None
    fish_count: int
    trash_count: int
    chest_count: int
    event_message: str = ""

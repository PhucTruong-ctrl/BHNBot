from .base import (
    MINIGAME_REGISTRY,
    BaseMinigame,
    get_all_minigames,
    get_minigame,
    register_minigame,
)
from .lixi import LixiAutoMinigame

__all__ = [
    "BaseMinigame",
    "LixiAutoMinigame",
    "MINIGAME_REGISTRY",
    "get_all_minigames",
    "get_minigame",
    "register_minigame",
]

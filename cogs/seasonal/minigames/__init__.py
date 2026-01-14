from .base import (
    MINIGAME_REGISTRY,
    BaseMinigame,
    get_all_minigames,
    get_minigame,
    register_minigame,
)
from .balloon_pop import BalloonPopMinigame
from .beach_cleanup import BeachCleanupMinigame
from .boat_race import BoatRaceMinigame
from .countdown import CountdownMinigame
from .ghost_hunt import GhostHuntMinigame
from .lantern_parade import LanternParadeMinigame
from .leaf_collect import LeafCollectMinigame
from .lixi import LixiAutoMinigame
from .quiz import QuizMinigame
from .secret_santa import SecretSantaMinigame
from .snowman import SnowmanMinigame
from .tea_brewing import TeaBrewingMinigame
from .thank_letter import ThankLetterMinigame
from .trash_sort import TrashSortMinigame
from .treasure_hunt import TreasureHuntMinigame
from .trick_treat import TrickTreatMinigame
from .wishes import WishesMinigame

__all__ = [
    "BalloonPopMinigame",
    "BaseMinigame",
    "BeachCleanupMinigame",
    "BoatRaceMinigame",
    "CountdownMinigame",
    "GhostHuntMinigame",
    "LanternParadeMinigame",
    "LeafCollectMinigame",
    "LixiAutoMinigame",
    "QuizMinigame",
    "SecretSantaMinigame",
    "SnowmanMinigame",
    "TeaBrewingMinigame",
    "ThankLetterMinigame",
    "TrashSortMinigame",
    "TreasureHuntMinigame",
    "TrickTreatMinigame",
    "WishesMinigame",
    "MINIGAME_REGISTRY",
    "get_all_minigames",
    "get_minigame",
    "register_minigame",
]

"""Constants for Seasonal Events system."""

from typing import Final

CHANNEL_EVENT: Final[str] = "kenh_sukien"
CHANNEL_MINIGAME: Final[str] = "kenh_sukien_auto"
ROLE_EVENT: Final[str] = "role_sukien"

DAILY_QUEST_RESET_HOUR: Final[int] = 0

MAX_BADGES_DISPLAY: Final[int] = 8
MAX_TITLE_LENGTH: Final[int] = 50
MAX_LETTER_LENGTH: Final[int] = 200
MAX_WISH_LENGTH: Final[int] = 200

TIER_COMMON: Final[str] = "common"
TIER_RARE: Final[str] = "rare"
TIER_EPIC: Final[str] = "epic"

QUEST_DAILY: Final[str] = "daily"
QUEST_FIXED: Final[str] = "fixed"

REWARD_SEEDS: Final[str] = "seeds"
REWARD_CURRENCY: Final[str] = "currency"
REWARD_TITLE: Final[str] = "title"
REWARD_BADGE: Final[str] = "badge"
REWARD_BUFF: Final[str] = "buff"
REWARD_ROLE: Final[str] = "role"

DEFAULT_MINIGAME_TIMEOUT: Final[int] = 60
DEFAULT_ACTIVE_HOURS: Final[tuple[int, int]] = (8, 23)

"""Constants for Seasonal Events system."""

from typing import Final

# Channel config keys
CHANNEL_EVENT: Final[str] = "kenh_sukien"
CHANNEL_MINIGAME: Final[str] = "kenh_sukien_auto"
ROLE_EVENT: Final[str] = "role_sukien"

# Timing
MILESTONE_UPDATE_INTERVAL_HOURS: Final[int] = 6
DAILY_QUEST_RESET_HOUR: Final[int] = 0

# Limits
MAX_DAILY_QUESTS: Final[int] = 3
MAX_BADGES_DISPLAY: Final[int] = 8
MAX_TITLE_LENGTH: Final[int] = 50
MAX_LETTER_LENGTH: Final[int] = 200
MAX_WISH_LENGTH: Final[int] = 200

# Fish
EVENT_FISH_CHANCE: Final[float] = 0.15

# Tiers
TIER_COMMON: Final[str] = "common"
TIER_RARE: Final[str] = "rare"
TIER_EPIC: Final[str] = "epic"

# Quest types
QUEST_DAILY: Final[str] = "daily"
QUEST_FIXED: Final[str] = "fixed"

# Reward types
REWARD_SEEDS: Final[str] = "seeds"
REWARD_CURRENCY: Final[str] = "currency"
REWARD_TITLE: Final[str] = "title"
REWARD_BADGE: Final[str] = "badge"
REWARD_BUFF: Final[str] = "buff"
REWARD_ROLE: Final[str] = "role"

# Embed colors (fallback)
COLOR_SPRING: Final[int] = 0xFFB7C5
COLOR_SUMMER: Final[int] = 0x00CED1
COLOR_AUTUMN: Final[int] = 0xDAA520
COLOR_WINTER: Final[int] = 0x4169E1
COLOR_HALLOWEEN: Final[int] = 0xFF6600
COLOR_EARTHDAY: Final[int] = 0x228B22
COLOR_MIDAUTUMN: Final[int] = 0xFFD700
COLOR_BIRTHDAY: Final[int] = 0xFF69B4

# Default spawn settings
DEFAULT_MINIGAME_TIMEOUT: Final[int] = 60
DEFAULT_ACTIVE_HOURS: Final[tuple[int, int]] = (8, 23)

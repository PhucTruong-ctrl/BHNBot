"""Bump reminder constants and configuration.

All constants used by the bump reminder system.
"""

# Timing constants
BUMP_INTERVAL_HOURS = 3
BUMP_INTERVAL_SECONDS = BUMP_INTERVAL_HOURS * 3600  # 10800 seconds

REMINDER_COOLDOWN_HOURS = 1  # Minimum time between reminder re-sends
REMINDER_COOLDOWN_SECONDS = REMINDER_COOLDOWN_HOURS * 3600  # 3600 seconds

# DISBOARD bot ID (official)
DISBOARD_BOT_ID = 302050872383242240

# Detection patterns for DISBOARD bump confirmation
# These are matched case-insensitively in message content/embeds
BUMP_CONFIRM_PATTERNS = ["bump done", ":thumbsup:", "👍"]

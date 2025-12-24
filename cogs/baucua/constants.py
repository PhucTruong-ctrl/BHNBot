"""Bau Cua game constants and configuration.

All constants used by the Bau Cua dice game system.
"""

# Animal definitions for Bau Cua dice game
# Each animal has a display name (Vietnamese) and emoji representation
ANIMALS = {
    "bau": {"name": "Bầu", "emoji": "🎃"},
    "cua": {"name": "Cua", "emoji": "🦀"},
    "tom": {"name": "Tôm", "emoji": "🦐"},
    "ca": {"name": "Cá", "emoji": "🐟"},
    "ga": {"name": "Gà", "emoji": "🐔"},
    "nai": {"name": "Nai", "emoji": "🦌"},
}

# List of all animal keys for random selection
ANIMAL_LIST = list(ANIMALS.keys())

# Game timing configuration
BETTING_TIME_SECONDS = 45  # Duration of betting phase
ROLL_ANIMATION_DURATION = 6.0  # Duration of dice rolling animation
ROLL_ANIMATION_INTERVAL = 0.5  # Update interval during animation
DICE_STOP_INTERVAL = 0.8  # Pause between each dice stopping (for suspense)

# Game rules
MAX_BET_AMOUNT = 250000  # Maximum seeds allowed per single bet
MIN_TIME_BEFORE_CUTOFF = 3  # Minimum seconds remaining to place bet

# Database configuration
DB_PATH = "./data/database.db"
GAME_ID_PREFIX = "baucua"  # Prefix for game statistics in database

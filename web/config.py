"""
BHNBot Admin Panel - Configuration

Configurable settings for the web admin interface.
"""
import os
from dotenv import load_dotenv

# Load .env from parent directory (BHNBot root)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# Database
DATABASE_PATH = os.path.join(ROOT_DIR, "data", "database.db")

# Discord API
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_API_BASE = "https://discord.com/api/v10"

# Guild Configuration (CONFIGURABLE - not hardcoded)
# Can be set via environment variable or defaults to the main server
DEFAULT_GUILD_ID = os.getenv("DEFAULT_GUILD_ID", "1424116735782682778")

# Role Category IDs (roles that act as category headers)
CATEGORY_ROLE_IDS = [
    "1447197290686058596",  # Thành tựu
    "1447198817014255757",  # Cảnh giới (Level)
    "1447266358000750702",  # Thông tin
    "1447203449744785408",  # Ping/Thông báo
]

# Server settings
HOST = "0.0.0.0"
PORT = int(os.getenv("ADMIN_PORT", 8000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS - Allow frontend dev server
# CORS - Allow all for Tailscale/Remote access
CORS_ORIGINS = ["*"]

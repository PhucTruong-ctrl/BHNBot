import os
import secrets
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "discord_bot_db")
DB_USER = os.getenv("DB_USER", "discord_bot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "discord_bot_password")

# Discord API
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_API_BASE = "https://discord.com/api/v10"

# Guild Configuration (CONFIGURABLE - not hardcoded)
# Can be set via environment variable or defaults to the main server
DEFAULT_GUILD_ID = os.getenv("DEFAULT_GUILD_ID", "1424116735782682778")

# Role Category IDs (roles that act as category headers)
# Now managed dynamically via database server_config table
# See web/routers/roles.py for implementation

# Server settings
HOST = "0.0.0.0"
PORT = int(os.getenv("ADMIN_PORT", 8000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS - Production: specify allowed origins; Development: allow all
# Set CORS_ALLOWED_ORIGINS in .env for production (comma-separated)
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else ["*"]

# Authentication
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv("ADMIN_USER_IDS", "").split(",") if id.strip()]

# Discord OAuth
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", f"http://localhost:{PORT}/api/auth/callback")

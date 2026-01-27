from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
import aiohttp
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import secrets
import logging

from ..config import (
    JWT_SECRET,
    ADMIN_USER_IDS,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
)

logger = logging.getLogger(__name__)

# Discord permission flags
ADMINISTRATOR = 0x8
MANAGE_GUILD = 0x20

router = APIRouter()

DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# In-memory caches (consider Redis for production)
sessions = {}
guild_cache = {}  # user_id -> {guilds: [...], cached_at: datetime}


class GuildInfo(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    permissions: int = 0
    is_admin: bool = False
    is_bot_in_guild: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict


async def fetch_user_guilds(access_token: str) -> List[dict]:
    """Fetch user's guilds from Discord API and filter to those with admin permissions."""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(f"{DISCORD_API_ENDPOINT}/users/@me/guilds", headers=headers) as resp:
            if resp.status != 200:
                logger.warning(f"Failed to fetch guilds: {resp.status}")
                return []
            guilds = await resp.json()
    
    # Filter to guilds where user has ADMINISTRATOR or MANAGE_GUILD permission
    admin_guilds = []
    for guild in guilds:
        perms = int(guild.get("permissions", 0))
        is_admin = (perms & ADMINISTRATOR) == ADMINISTRATOR
        is_manager = (perms & MANAGE_GUILD) == MANAGE_GUILD
        
        if is_admin or is_manager or guild.get("owner", False):
            admin_guilds.append({
                "id": guild["id"],
                "name": guild["name"],
                "icon": guild.get("icon"),
                "permissions": perms,
                "is_admin": is_admin or guild.get("owner", False)
            })
    
    return admin_guilds


async def get_bot_guilds() -> set:
    """Get the set of guild IDs where the bot is present."""
    try:
        from ..main import bot_instance
        if bot_instance and hasattr(bot_instance, 'guilds'):
            return {str(g.id) for g in bot_instance.guilds}
    except Exception as e:
        logger.debug(f"Could not get bot guilds: {e}")
    return set()


def create_jwt_token(user_data: dict, managed_guilds: Optional[List[dict]] = None) -> str:
    """Create JWT with user info and list of manageable guild IDs."""
    guild_ids = [g["id"] for g in (managed_guilds or [])]
    payload = {
        "sub": str(user_data["id"]),
        "username": user_data["username"],
        "avatar": user_data.get("avatar"),
        "managed_guilds": guild_ids,  # Store guild IDs user can manage
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.get("/login")
async def login():
    if not DISCORD_CLIENT_ID:
        return {"error": "Discord OAuth not configured", "message": "Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET environment variables"}
    
    state = secrets.token_urlsafe(32)
    sessions[state] = {"created": datetime.utcnow()}
    
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state
    }
    
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{DISCORD_OAUTH_URL}?{query}")


@router.get("/callback")
async def callback(code: str, state: str):
    if state not in sessions:
        raise HTTPException(status_code=400, detail="Invalid state")
    
    del sessions[state]
    
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="OAuth not configured")
    
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI
        }
        
        async with session.post(DISCORD_TOKEN_URL, data=data) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code")
            token_data = await resp.json()
        
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        async with session.get(f"{DISCORD_API_ENDPOINT}/users/@me", headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            user_data = await resp.json()
    
    user_id = int(user_data["id"])
    if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="You are not authorized to access this dashboard")
    
    # Fetch user's guilds with admin permissions
    user_guilds = await fetch_user_guilds(token_data['access_token'])
    
    # Filter to guilds where bot is present
    bot_guild_ids = await get_bot_guilds()
    managed_guilds = []
    for guild in user_guilds:
        guild["is_bot_in_guild"] = guild["id"] in bot_guild_ids
        if guild["is_bot_in_guild"]:
            managed_guilds.append(guild)
    
    # Store guilds in memory cache for /guilds endpoint
    guild_cache[str(user_id)] = {
        "guilds": managed_guilds,
        "all_admin_guilds": user_guilds,
        "cached_at": datetime.utcnow()
    }
    
    jwt_token = create_jwt_token(user_data, managed_guilds)
    
    response = RedirectResponse(url="/?auth=success")
    response.set_cookie(
        key="auth_token",
        value=jwt_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )
    
    return response


@router.get("/me")
async def get_current_user(request: Request):
    token = request.cookies.get("auth_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {
        "id": payload["sub"],
        "username": payload["username"],
        "avatar": payload.get("avatar"),
        "avatar_url": f"https://cdn.discordapp.com/avatars/{payload['sub']}/{payload['avatar']}.png" if payload.get("avatar") else None
    }


@router.post("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login")
    response.delete_cookie("auth_token")
    return response


@router.get("/status")
async def auth_status(request: Request):
    token = request.cookies.get("auth_token")
    
    if not token:
        return {"authenticated": False}
    
    payload = verify_jwt_token(token)
    if not payload:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "user": {
            "id": payload["sub"],
            "username": payload["username"]
        }
    }


@router.get("/guilds", response_model=List[GuildInfo])
async def get_user_guilds(request: Request):
    """Get list of guilds the current user can manage (where they have admin perms AND bot is present)."""
    token = request.cookies.get("auth_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload["sub"]
    
    # Check cache first
    cache_entry = guild_cache.get(user_id)
    if cache_entry:
        cache_age = datetime.utcnow() - cache_entry["cached_at"]
        if cache_age.total_seconds() < 300:  # 5 minute cache
            return cache_entry["guilds"]
    
    # If no cache, return from JWT (may be stale but works)
    managed_guild_ids = payload.get("managed_guilds", [])
    
    # Try to refresh from bot if available
    bot_guild_ids = await get_bot_guilds()
    
    if cache_entry:
        # Re-filter with current bot guilds
        refreshed = []
        for guild in cache_entry.get("all_admin_guilds", []):
            guild["is_bot_in_guild"] = guild["id"] in bot_guild_ids
            if guild["is_bot_in_guild"]:
                refreshed.append(guild)
        return refreshed
    
    # Fallback: return basic info from JWT
    return [{"id": gid, "name": f"Server {gid}", "is_bot_in_guild": True} for gid in managed_guild_ids]


@router.get("/guilds/{guild_id}")
async def get_guild_info(guild_id: str, request: Request):
    """Get detailed info about a specific guild."""
    token = request.cookies.get("auth_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Verify user has access to this guild
    managed_guild_ids = payload.get("managed_guilds", [])
    if guild_id not in managed_guild_ids:
        raise HTTPException(status_code=403, detail="You don't have admin access to this guild")
    
    # Get guild info from bot
    try:
        from ..main import bot_instance
        if bot_instance:
            guild = bot_instance.get_guild(int(guild_id))
            if guild:
                return {
                    "id": str(guild.id),
                    "name": guild.name,
                    "icon": guild.icon.key if guild.icon else None,
                    "member_count": guild.member_count,
                    "owner_id": str(guild.owner_id),
                    "created_at": guild.created_at.isoformat()
                }
    except Exception as e:
        logger.debug(f"Could not get guild from bot: {e}")
    
    return {"id": guild_id, "name": "Unknown", "member_count": 0}

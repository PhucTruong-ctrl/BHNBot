from fastapi import Request, HTTPException, Depends
from typing import Optional, List
import jwt

from .config import JWT_SECRET, ADMIN_USER_IDS


def get_current_user(request: Request) -> dict:
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {
            "id": int(payload["sub"]),
            "username": payload.get("username", "Unknown"),
            "avatar": payload.get("avatar"),
            "managed_guilds": payload.get("managed_guilds", [])
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["id"] not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_guild_access(guild_id: str):
    """
    Dependency factory that verifies user has admin access to a specific guild.
    
    Usage:
        @router.get("/guilds/{guild_id}/settings")
        async def get_settings(guild_id: str, user: dict = Depends(require_guild_access(guild_id))):
            ...
    
    Or as a direct dependency:
        @router.get("/guilds/{guild_id}/config")
        async def get_config(
            guild_id: str,
            request: Request,
            user: dict = Depends(get_current_user)
        ):
            verify_guild_access(user, guild_id)
            ...
    """
    def dependency(request: Request, user: dict = Depends(get_current_user)) -> dict:
        # Extract guild_id from path parameters
        path_guild_id = request.path_params.get("guild_id", guild_id)
        
        managed_guilds = user.get("managed_guilds", [])
        if path_guild_id not in managed_guilds:
            raise HTTPException(
                status_code=403, 
                detail=f"You don't have admin access to guild {path_guild_id}"
            )
        
        # Add current guild to user context
        user["current_guild_id"] = path_guild_id
        return user
    
    return dependency


def verify_guild_access(user: dict, guild_id: str) -> None:
    """
    Direct verification function for guild access.
    Raises HTTPException if user doesn't have access.
    """
    managed_guilds = user.get("managed_guilds", [])
    if guild_id not in managed_guilds:
        raise HTTPException(
            status_code=403,
            detail=f"You don't have admin access to guild {guild_id}"
        )


class GuildAccessDependency:
    """
    Class-based dependency for guild access verification.
    Extracts guild_id from path and verifies access.
    """
    async def __call__(self, request: Request, user: dict = Depends(get_current_user)) -> dict:
        guild_id = request.path_params.get("guild_id")
        if not guild_id:
            raise HTTPException(status_code=400, detail="guild_id is required")
        
        verify_guild_access(user, guild_id)
        user["current_guild_id"] = guild_id
        return user


# Singleton instance for use as dependency
require_guild = GuildAccessDependency()


async def audit_action(
    request: Request,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None
):
    from .routers.audit import log_action
    
    user = None
    try:
        user = get_current_user(request)
    except HTTPException:
        return
    
    ip = request.client.host if request.client else None
    
    await log_action(
        admin_id=user["id"],
        admin_name=user["username"],
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip
    )

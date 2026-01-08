"""
Shared dependencies for FastAPI routers.
"""
from fastapi import Request, HTTPException, Depends
from typing import Optional
import jwt
import os
import secrets

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv("ADMIN_USER_IDS", "").split(",") if id.strip()]


def get_current_user(request: Request) -> dict:
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {
            "id": int(payload["sub"]),
            "username": payload.get("username", "Unknown"),
            "avatar": payload.get("avatar")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["id"] not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


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

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
import aiohttp
import os
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/api/auth/callback")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))

DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv("ADMIN_USER_IDS", "").split(",") if id.strip()]

sessions = {}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict


def create_jwt_token(user_data: dict) -> str:
    payload = {
        "sub": str(user_data["id"]),
        "username": user_data["username"],
        "avatar": user_data.get("avatar"),
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
    
    jwt_token = create_jwt_token(user_data)
    
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

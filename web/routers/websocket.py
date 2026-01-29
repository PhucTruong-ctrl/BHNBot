"""
WebSocket endpoint for real-time system updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
import asyncio
import json
import jwt
from .system import get_cpu_info, get_memory_info, get_disk_info, get_network_info, get_bot_status, get_gpu_info
from ..config import JWT_SECRET, ADMIN_USER_IDS

router = APIRouter(tags=["WebSocket"])


async def verify_ws_access(websocket: WebSocket):
    token = websocket.cookies.get("auth_token")
    if not token:
        # Try query param for flexible clients
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=4001, reason="Missing authentication")
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload["sub"])
        
        # Admin check
        if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
             await websocket.close(code=4003, reason="Admin access required")
             return None
             
        return user_id
    except Exception:
        await websocket.close(code=4001, reason="Invalid authentication")
        return None


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


def format_uptime(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"


def get_system_snapshot() -> dict:
    cpu = get_cpu_info()
    memory = get_memory_info()
    disk = get_disk_info()
    network = get_network_info()
    bot = get_bot_status()
    
    return {
        "type": "system_stats",
        "data": {
            "cpu": {
                "model": cpu["model"],
                "usage_percent": cpu["usage"],
                "frequency": cpu["frequency"],
                "temperature": cpu["temperature"],
                "cores": cpu["cores"],
                "threads": cpu["threads"]
            },
            "memory": {
                "ram_total_gb": memory["ram"]["total"] / (1024**3),
                "ram_used_gb": memory["ram"]["used"] / (1024**3),
                "ram_percent": memory["ram"]["percent"],
                "ram_free_gb": memory["ram"]["free"] / (1024**3),
                "swap_percent": memory["swap"]["percent"]
            },
            "disk": {
                "total_gb": disk["total"] / (1024**3),
                "used_gb": disk["used"] / (1024**3),
                "free_gb": disk["free"] / (1024**3),
                "usage_percent": disk["percent"]
            },
            "network": {
                "upload_speed": network["upload_speed"],
                "download_speed": network["download_speed"],
                "upload_speed_mbps": network["upload_speed"] * 8 / (1024**2),
                "download_speed_mbps": network["download_speed"] * 8 / (1024**2)
            },
            "gpu": get_gpu_info(),
            "bot": {
                "online": bot["status"] == "online",
                "status": bot["status"],
                "pid": bot.get("pid"),
                "cpu_percent": bot["cpu_percent"],
                "memory_percent": bot["memory_percent"],
                "memory_mb": bot["memory_usage"] / (1024**2) if bot["memory_usage"] else 0,
                "threads": bot["threads"],
                "uptime": format_uptime(bot["uptime"]) if bot["uptime"] else "N/A",
                "uptime_seconds": bot["uptime"]
            }
        }
    }


@router.websocket("/ws/system")
async def websocket_system_stats(websocket: WebSocket):
    user = await verify_ws_access(websocket)
    if not user:
        return

    await manager.connect(websocket)
    try:
        while True:
            stats = get_system_snapshot()
            await websocket.send_json(stats)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

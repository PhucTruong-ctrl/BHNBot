"""
BHNBot Admin Panel - Roles Router

Migrated from tools/role_manager/app.py.
Provides Discord role management via API.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import asyncio
import uuid
import time
import json

from core.logging import get_logger
from ..config import DISCORD_TOKEN, DISCORD_API_BASE, DEFAULT_GUILD_ID
from database_manager import get_server_config, db_manager

router = APIRouter()
logger = get_logger("AdminPanel.Roles")

# Headers for Discord API
HEADERS = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json"
}

# Task storage (in-memory for simplicity)
TASKS: Dict[str, Dict] = {}


class RoleUpdate(BaseModel):
    """Request body for role update."""
    name: Optional[str] = None
    color: Optional[int] = None


class RoleCreate(BaseModel):
    """Request body for role creation."""
    name: str = "New Role"
    is_category: bool = False


class BatchUpdate(BaseModel):
    """Request body for batch operations."""
    updates: List[Dict[str, Any]] = []
    reorder: Optional[Dict[str, Any]] = None


# Helper functions
async def discord_request(method: str, endpoint: str, json_data: Dict = None) -> Optional[Dict]:
    """Make async request to Discord API."""
    url = f"{DISCORD_API_BASE}{endpoint}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.request(method, url, headers=HEADERS, json=json_data)
            if response.status_code < 300:
                return response.json()
            else:
                logger.error(f"Discord API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Discord request failed: {e}")
            return None


async def get_category_role_ids(guild_id: str) -> List[str]:
    """Fetch category role IDs from database."""
    try:
        data = await get_server_config(int(guild_id), "category_roles")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to fetch category roles: {e}")
    return []


async def add_category_role_id(guild_id: str, role_id: str):
    """Add a new category role ID to database."""
    try:
        current_ids = await get_category_role_ids(guild_id)
        if role_id not in current_ids:
            current_ids.append(role_id)
            # Use raw SQL update via db_manager since set_server_config isn't imported/explicit
            await db_manager.modify(
                "UPDATE server_config SET category_roles = ? WHERE guild_id = ?",
                (json.dumps(current_ids), int(guild_id))
            )
            # CRITICAL: Invalidate cache so subsequent fetches see the new category
            db_manager.clear_cache_by_prefix(f"config_{guild_id}")
    except Exception as e:
        logger.error(f"Failed to save category role: {e}")


def process_roles_into_categories(roles: List[Dict], category_ids: List[str]) -> List[Dict]:
    """Group roles by category headers."""
    roles.sort(key=lambda x: x['position'], reverse=True)
    
    categories = []
    current_category = {
        "id": "uncategorized_top",
        "name": "Chưa phân loại",
        "color": 0,
        "roles": [],
        "is_real_category": False
    }
    categories.append(current_category)
    
    for role in roles:
        role_id = role['id']
        if role_id in category_ids:
            new_cat = {
                "id": role_id,
                "name": role['name'],
                "color": role['color'],
                "roles": [],
                "is_real_category": True,
                "position": role['position']
            }
            categories.append(new_cat)
            current_category = new_cat
        else:
            current_category["roles"].append(role)
    
    return categories


# Endpoints
@router.get("/")
async def list_roles(guild_id: str = DEFAULT_GUILD_ID) -> Dict[str, Any]:
    """Get all roles grouped by category."""
    # Parallel fetch: Roles from Discord + Categories from DB
    roles_task = discord_request("GET", f"/guilds/{guild_id}/roles")
    cats_task = get_category_role_ids(guild_id)
    
    roles, category_ids = await asyncio.gather(roles_task, cats_task)
    
    if roles:
        data = process_roles_into_categories(roles, category_ids)
        logger.info(f"Fetched {len(roles)} roles from guild {guild_id}")
        return {"categories": data, "total": len(roles)}
    raise HTTPException(status_code=500, detail="Failed to fetch roles from Discord")


@router.patch("/{role_id}")
async def update_role(
    role_id: str,
    update: RoleUpdate,
    guild_id: str = DEFAULT_GUILD_ID
) -> Dict[str, Any]:
    """Update a single role."""
    payload = {}
    if update.name:
        payload['name'] = update.name
    if update.color is not None:
        payload['color'] = update.color
    
    result = await discord_request(
        "PATCH",
        f"/guilds/{guild_id}/roles/{role_id}",
        payload
    )
    
    if result:
        return {"status": "success", "role": result}
    raise HTTPException(status_code=500, detail="Failed to update role")


@router.post("/create")
async def create_role(role: RoleCreate, guild_id: str = DEFAULT_GUILD_ID) -> Dict[str, Any]:
    """Create a new role."""
    payload = {
        "name": role.name,
        "permissions": "0"
    }
    
    result = await discord_request(
        "POST",
        f"/guilds/{guild_id}/roles",
        payload
    )
    
    if result:
        if role.is_category:
            await add_category_role_id(guild_id, result['id'])
        logger.info(f"Created role: {result['id']} - {result['name']}")
        return result
    raise HTTPException(status_code=500, detail="Failed to create role")


@router.delete("/{role_id}")
async def delete_role(role_id: str, guild_id: str = DEFAULT_GUILD_ID) -> Dict[str, Any]:
    """Delete a role."""
    # Check if category first to remove from DB? 
    # Actually safe to keep ID in DB or we can remove it. For now let's just delete from Discord.
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.delete(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/roles/{role_id}",
            headers=HEADERS
        )
        if response.status_code == 204:
            # Cleanup DB if it was a category
            # (Optional improvement: remove from category_roles list)
            return {"status": "deleted", "role_id": role_id}
        raise HTTPException(status_code=500, detail="Failed to delete role")


# Batch operations (background task)
async def process_batch(task_id: str, updates: List[Dict], reorder: Dict, guild_id: str):
    """Background worker for batch updates."""
    try:
        total = len(updates) + 1
        current = 0
        
        TASKS[task_id].update({"status": "processing", "progress": 0})
        
        # Process individual updates
        for update in updates:
            role_id = update['id']
            payload = {}
            if 'name' in update:
                payload['name'] = update['name']
            if 'color' in update:
                payload['color'] = int(update['color'])
            
            await discord_request("PATCH", f"/guilds/{guild_id}/roles/{role_id}", payload)
            current += 1
            TASKS[task_id]["progress"] = int((current / total) * 100)
            await asyncio.sleep(0.2)  # Rate limit protection
        
        # Process reorder if provided
        if reorder and reorder.get('categories'):
            ordered_ids = []
            for cat in reorder['categories']:
                if cat.get('is_real_category'):
                    ordered_ids.append(cat['id'])
                for rid in cat.get('role_ids', []):
                    ordered_ids.append(rid)
            
            payload = [
                {"id": rid, "position": len(ordered_ids) - i}
                for i, rid in enumerate(ordered_ids)
            ]
            await discord_request("PATCH", f"/guilds/{guild_id}/roles", payload)
        
        TASKS[task_id].update({"status": "completed", "progress": 100})
        
    except Exception as e:
        logger.exception("Batch processing failed")
        TASKS[task_id].update({"status": "failed", "error": str(e)})


@router.post("/batch")
async def submit_batch(
    batch: BatchUpdate,
    background_tasks: BackgroundTasks,
    guild_id: str = DEFAULT_GUILD_ID
) -> Dict[str, Any]:
    """Submit batch update job."""
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "status": "queued",
        "progress": 0,
        "created_at": time.time()
    }
    
    background_tasks.add_task(
        process_batch,
        task_id,
        batch.updates,
        batch.reorder or {},
        guild_id
    )
    
    return {"task_id": task_id, "status": "queued"}


@router.get("/batch/{task_id}")
async def get_batch_status(task_id: str) -> Dict[str, Any]:
    """Get batch job status."""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id]

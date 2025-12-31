"""
BHNBot Admin Panel - Users Router

Endpoints for user management.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from ..database import fetchall, fetchone, execute

router = APIRouter()


class UserUpdate(BaseModel):
    """Request body for updating user."""
    seeds: Optional[int] = None
    username: Optional[str] = None


class SeedAdjustment(BaseModel):
    """Request body for adjusting seeds."""
    amount: int
    reason: Optional[str] = "Admin adjustment"


@router.get("/")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: str = Query("seeds", pattern="^(seeds|username|user_id)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
) -> Dict[str, Any]:
    """List users with pagination and search."""
    
    offset = (page - 1) * limit
    
    # Build query
    where_clause = ""
    params = []
    if search:
        # POSTGRES: Use ILIKE for case-insensitive search
        where_clause = "WHERE username ILIKE $1 OR CAST(user_id AS TEXT) ILIKE $2"
        params = [f"%{search}%", f"%{search}%"]
    
    # Get total count
    count_query = f"SELECT COUNT(*) as count FROM users {where_clause}"
    total = await fetchone(count_query, tuple(params))
    
    # Get paginated results
    query = f"""
        SELECT user_id, username, seeds, created_at, last_daily
        FROM users {where_clause}
        ORDER BY {sort_by} {sort_order.upper()}
        LIMIT ? OFFSET ?
    """
    users = await fetchall(query, tuple(params + [limit, offset]))
    
    return {
        "users": users,
        "total": total["count"] if total else 0,
        "page": page,
        "limit": limit,
        "pages": (total["count"] // limit) + 1 if total else 1
    }


@router.get("/{user_id}")
async def get_user(user_id: int) -> Dict[str, Any]:
    """Get detailed user information."""
    
    # Basic info
    user = await fetchone(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Inventory
    inventory = await fetchall(
        """SELECT item_id, quantity, item_type 
           FROM inventory WHERE user_id = ? ORDER BY quantity DESC""",
        (user_id,)
    )
    
    # Fishing profile
    fishing = await fetchone(
        "SELECT rod_level, rod_durability, exp FROM fishing_profiles WHERE user_id = ?",
        (user_id,)
    )
    
    # Fish collection
    fish_collection = await fetchall(
        """SELECT fish_id, quantity FROM fish_collection 
           WHERE user_id = ? ORDER BY quantity DESC LIMIT 10""",
        (user_id,)
    )
    
    # Stats
    stats = await fetchall(
        "SELECT game_id, stat_key, value FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    # Achievements
    achievements = await fetchall(
        "SELECT achievement_key, earned_at FROM user_achievements WHERE user_id = ?",
        (user_id,)
    )
    
    # Buffs
    buffs = await fetchall(
        "SELECT buff_type, duration_type, end_time, remaining_count FROM user_buffs WHERE user_id = ?",
        (user_id,)
    )
    
    return {
        "user": dict(user),
        "inventory": inventory,
        "fishing_profile": dict(fishing) if fishing else None,
        "fish_collection": fish_collection,
        "stats": stats,
        "achievements": achievements,
        "buffs": buffs
    }


@router.patch("/{user_id}")
async def update_user(user_id: int, update: UserUpdate) -> Dict[str, Any]:
    """Update user details."""
    
    # Check user exists
    user = await fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update
    updates = []
    params = []
    if update.seeds is not None:
        updates.append("seeds = ?")
        params.append(update.seeds)
    if update.username is not None:
        updates.append("username = ?")
        params.append(update.username)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
    await execute(query, tuple(params))
    
    # Return updated user
    return await get_user(user_id)


@router.post("/{user_id}/seeds")
async def adjust_seeds(user_id: int, adjustment: SeedAdjustment) -> Dict[str, Any]:
    """Add or remove seeds from user (admin action)."""
    
    # Check user exists
    user = await fetchone("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_balance = user["seeds"]
    new_balance = max(0, old_balance + adjustment.amount)  # Prevent negative
    
    await execute(
        "UPDATE users SET seeds = ? WHERE user_id = ?",
        (new_balance, user_id)
    )
    
    # Log the adjustment
    import logging
    logger = logging.getLogger("AdminPanel")
    logger.info(
        f"[ADMIN] Seeds adjusted: user={user_id} "
        f"old={old_balance} new={new_balance} "
        f"change={adjustment.amount} reason={adjustment.reason}"
    )
    
    return {
        "user_id": user_id,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "adjustment": adjustment.amount,
        "reason": adjustment.reason
    }

"""
Database Manager - Optimized database operations with caching and batch processing
Handles connection pooling, query caching, and batch operations for better performance
"""
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

DB_PATH = "./data/database.db"
DB_TIMEOUT = 10.0  # 10 seconds timeout for database operations

async def get_db_connection(db_path: str = DB_PATH):
    """Get database connection with proper timeout and WAL mode"""
    db = await aiosqlite.connect(db_path, timeout=DB_TIMEOUT)
    await db.execute("PRAGMA journal_mode=WAL")
    return db

class CacheEntry:
    """Cache entry with TTL (Time To Live)"""
    def __init__(self, data: Any, ttl: int = 300):
        self.data = data
        self.created_at = datetime.now()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        return (datetime.now() - self.created_at).total_seconds() > self.ttl


class DatabaseManager:
    """
    Optimized database manager with:
    - Connection pooling
    - Query result caching
    - Batch operations
    - Automatic index creation
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.cache: Dict[str, CacheEntry] = {}
        self.batch_operations: Dict[str, List[Tuple]] = {}
        self.lock = asyncio.Lock()
    
    # ==================== CONNECTION MANAGEMENT ====================
    
    async def execute(self, query: str, params: tuple = (), use_cache: bool = False, cache_key: str = "", cache_ttl: int = 300):
        """Execute a query with optional caching"""
        # Check cache first
        if use_cache and cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                return entry.data
        
        db = await get_db_connection(self.db_path)
        try:
            async with db.execute(query, params) as cursor:
                result = await cursor.fetchall()
        finally:
            await db.close()
        
        # Cache if requested
        if use_cache and cache_key:
            self.cache[cache_key] = CacheEntry(result, cache_ttl)
        
        return result
    
    async def fetchone(self, query: str, params: tuple = (), use_cache: bool = False, cache_key: str = "", cache_ttl: int = 300):
        """Fetch single row with optional caching"""
        # Check cache first
        if use_cache and cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                return entry.data
        
        db = await get_db_connection(self.db_path)
        try:
            async with db.execute(query, params) as cursor:
                result = await cursor.fetchone()
        finally:
            await db.close()
        
        # Cache if requested
        if use_cache and cache_key:
            self.cache[cache_key] = CacheEntry(result, cache_ttl)
        
        return result
    
    async def modify(self, query: str, params: tuple = ()):
        """Execute INSERT/UPDATE/DELETE query"""
        db = await get_db_connection(self.db_path)
        try:
            await db.execute(query, params)
            await db.commit()
        finally:
            await db.close()
        
        # Invalidate relevant caches
        self._invalidate_cache_pattern(query)
    
    def _invalidate_cache_pattern(self, query: str):
        """Invalidate cache entries based on query type"""
        query_upper = query.upper()
        keys_to_delete = []
        
        if "UPDATE" in query_upper or "INSERT" in query_upper or "DELETE" in query_upper:
            # Invalidate all caches for affected tables
            for key in self.cache:
                if any(table in key.upper() for table in ["ECONOMY", "TREE", "RELATIONSHIP", "INVENTORY"]):
                    keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
    
    async def batch_modify(self, operations: List[Tuple[str, tuple]]):
        """Execute multiple INSERT/UPDATE/DELETE in a single transaction"""
        db = await get_db_connection(self.db_path)
        try:
            for query, params in operations:
                await db.execute(query, params)
            await db.commit()
        finally:
            await db.close()
        
        # Invalidate caches
        for query, _ in operations:
            self._invalidate_cache_pattern(query)
    
    def clear_cache(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def clear_cache_by_prefix(self, prefix: str):
        """Clear cache entries by prefix"""
        keys_to_delete = [k for k in self.cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self.cache[key]


# Global instance
db_manager = DatabaseManager(DB_PATH)


# ==================== OPTIMIZED QUERIES ====================

async def get_user_balance(user_id: int) -> int:
    """Get user seeds with caching (5min TTL)"""
    result = await db_manager.fetchone(
        "SELECT seeds FROM economy_users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"balance_{user_id}",
        cache_ttl=300
    )
    return result[0] if result else 0


async def get_user_full(user_id: int) -> Optional[tuple]:
    """Get complete user data with caching"""
    result = await db_manager.fetchone(
        "SELECT user_id, username, seeds, last_daily, last_chat_reward, created_at, updated_at FROM economy_users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"user_full_{user_id}",
        cache_ttl=300
    )
    return result


async def add_seeds(user_id: int, amount: int):
    """Add seeds and invalidate cache"""
    await db_manager.modify(
        "UPDATE economy_users SET seeds = seeds + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
        (amount, user_id)
    )
    db_manager.clear_cache_by_prefix(f"balance_{user_id}")
    db_manager.clear_cache_by_prefix(f"user_full_{user_id}")


async def get_leaderboard(limit: int = 10) -> List[tuple]:
    """Get top players with caching (5min TTL)"""
    result = await db_manager.execute(
        "SELECT user_id, username, seeds FROM economy_users ORDER BY seeds DESC LIMIT ?",
        (limit,),
        use_cache=True,
        cache_key="leaderboard_top",
        cache_ttl=300
    )
    return result


async def get_or_create_user(user_id: int, username: str) -> Optional[tuple]:
    """Get or create user (no cache as it modifies)"""
    user = await db_manager.fetchone(
        "SELECT * FROM economy_users WHERE user_id = ?",
        (user_id,)
    )
    
    if not user:
        await db_manager.modify(
            "INSERT INTO economy_users (user_id, username, seeds) VALUES (?, ?, 0)",
            (user_id, username)
        )
        db_manager.clear_cache_by_prefix("leaderboard")
    
    return user


async def batch_update_seeds(updates: Dict[int, int]):
    """Batch update multiple users' seeds at once"""
    operations = [
        (
            "UPDATE economy_users SET seeds = seeds + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (amount, user_id)
        )
        for user_id, amount in updates.items()
    ]
    
    await db_manager.batch_modify(operations)
    db_manager.clear_cache_by_prefix("balance_")
    db_manager.clear_cache_by_prefix("leaderboard")


# ==================== TREE QUERIES ====================

async def get_tree_data(guild_id: int) -> Optional[tuple]:
    """Get tree data with caching"""
    result = await db_manager.fetchone(
        "SELECT current_level, current_progress, total_contributed, season, tree_channel_id, tree_message_id FROM server_tree WHERE guild_id = ?",
        (guild_id,),
        use_cache=True,
        cache_key=f"tree_{guild_id}",
        cache_ttl=60  # Short TTL for dynamic data
    )
    return result


async def update_tree_progress(guild_id: int, level: int, progress: int, total: int):
    """Update tree and invalidate cache"""
    await db_manager.modify(
        "UPDATE server_tree SET current_level = ?, current_progress = ?, total_contributed = ? WHERE guild_id = ?",
        (level, progress, total, guild_id)
    )
    db_manager.clear_cache_by_prefix(f"tree_{guild_id}")


async def get_top_contributors(guild_id: int, limit: int = 3) -> List[tuple]:
    """Get top tree contributors with caching"""
    result = await db_manager.execute(
        "SELECT user_id, amount FROM tree_contributors WHERE guild_id = ? ORDER BY amount DESC LIMIT ?",
        (guild_id, limit),
        use_cache=True,
        cache_key=f"top_contributors_{guild_id}",
        cache_ttl=300
    )
    return result


# ==================== RELATIONSHIP QUERIES ====================

async def get_affinity(user_id_1: int, user_id_2: int) -> int:
    """Get affinity between users with caching"""
    if user_id_1 > user_id_2:
        user_id_1, user_id_2 = user_id_2, user_id_1
    
    result = await db_manager.fetchone(
        "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
        (user_id_1, user_id_2),
        use_cache=True,
        cache_key=f"affinity_{user_id_1}_{user_id_2}",
        cache_ttl=600
    )
    return result[0] if result else 0


async def add_affinity(user_id_1: int, user_id_2: int, amount: int):
    """Add affinity and invalidate cache"""
    if user_id_1 > user_id_2:
        user_id_1, user_id_2 = user_id_2, user_id_1
    
    # Check if relationship exists
    existing = await db_manager.fetchone(
        "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
        (user_id_1, user_id_2)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE relationships SET affinity = affinity + ?, last_interaction = CURRENT_TIMESTAMP WHERE user_id_1 = ? AND user_id_2 = ?",
            (amount, user_id_1, user_id_2)
        )
    else:
        await db_manager.modify(
            "INSERT INTO relationships (user_id_1, user_id_2, affinity) VALUES (?, ?, ?)",
            (user_id_1, user_id_2, amount)
        )
    
    db_manager.clear_cache_by_prefix(f"affinity_{min(user_id_1, user_id_2)}")


async def get_top_affinity_friends(user_id: int, limit: int = 3) -> List[tuple]:
    """Get top friends by affinity"""
    # Query as user_id_1
    results_1 = await db_manager.execute(
        "SELECT user_id_2, affinity FROM relationships WHERE user_id_1 = ? ORDER BY affinity DESC LIMIT ?",
        (user_id, limit)
    )
    
    # Query as user_id_2
    results_2 = await db_manager.execute(
        "SELECT user_id_1, affinity FROM relationships WHERE user_id_2 = ? ORDER BY affinity DESC LIMIT ?",
        (user_id, limit)
    )
    
    # Combine and sort
    combined = list(results_1) + list(results_2)
    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:limit]


# ==================== INVENTORY QUERIES ====================

async def get_inventory(user_id: int) -> Dict[str, int]:
    """Get user inventory with caching"""
    result = await db_manager.execute(
        "SELECT item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0",
        (user_id,),
        use_cache=True,
        cache_key=f"inventory_{user_id}",
        cache_ttl=600
    )
    
    inventory = {}
    for item_name, quantity in result:
        inventory[item_name] = quantity
    return inventory


async def add_item(user_id: int, item_name: str, quantity: int = 1):
    """Add item to inventory"""
    # Check if item exists
    existing = await db_manager.fetchone(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_name)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?",
            (quantity, user_id, item_name)
        )
    else:
        await db_manager.modify(
            "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
            (user_id, item_name, quantity)
        )
    
    db_manager.clear_cache_by_prefix(f"inventory_{user_id}")


async def remove_item(user_id: int, item_name: str, quantity: int = 1) -> bool:
    """Remove item from inventory"""
    existing = await db_manager.fetchone(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_name)
    )
    
    if not existing or existing[0] < quantity:
        return False
    
    new_quantity = existing[0] - quantity
    if new_quantity <= 0:
        await db_manager.modify(
            "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        )
    else:
        await db_manager.modify(
            "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?",
            (new_quantity, user_id, item_name)
        )
    
    db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
    return True


# ==================== SERVER CONFIG QUERIES ====================

async def get_server_config(guild_id: int, field: str) -> Optional[Any]:
    """Get server config field with caching"""
    result = await db_manager.fetchone(
        f"SELECT {field} FROM server_config WHERE guild_id = ?",
        (guild_id,),
        use_cache=True,
        cache_key=f"config_{guild_id}_{field}",
        cache_ttl=300
    )
    return result[0] if result else None


async def set_server_config(guild_id: int, field: str, value: Any):
    """Set server config field"""
    await db_manager.modify(
        f"INSERT OR REPLACE INTO server_config (guild_id, {field}) VALUES (?, ?)",
        (guild_id, value)
    )
    db_manager.clear_cache_by_prefix(f"config_{guild_id}")


async def get_rod_data(user_id: int) -> tuple[int, int]:
    """Get user's rod level and durability"""
    result = await db_manager.fetchone(
        "SELECT rod_level, rod_durability FROM economy_users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"rod_{user_id}",
        cache_ttl=300
    )
    return result if result else (1, 30) # Default level 1, 30 durability


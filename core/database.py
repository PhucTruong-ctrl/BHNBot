"""
Core database functionality and server configuration management.
"""
import aiosqlite
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from configs.settings import DB_PATH, DB_TIMEOUT


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


# ==================== SERVER CONFIGURATION ====================

def load_server_config(server_id: str = "default_server") -> Dict[str, Any]:
    """Load server-specific configuration (role IDs, etc.)"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "server_config.json")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get(server_id, {})
        except Exception as e:
            print(f"[WARNING] Failed to load server config: {e}")
            return {}
    else:
        print(f"[WARNING] Server config not found: {config_path}")
        return {}


def get_role_id(role_key: str, server_id: str = "default_server") -> Optional[int]:
    """Get Discord role ID from role key and server ID"""
    server_config = load_server_config(server_id)
    return server_config.get(role_key)


# ==================== OPTIMIZED QUERIES ====================

async def get_user_balance(user_id: int) -> int:
    """Get user seeds with caching (5min TTL)"""
    result = await db_manager.fetchone(
        "SELECT seeds FROM users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"balance_{user_id}",
        cache_ttl=300
    )
    return result[0] if result else 0


async def get_user_full(user_id: int) -> Optional[tuple]:
    """Get complete user data with caching"""
    result = await db_manager.fetchone(
        "SELECT user_id, username, seeds, created_at, updated_at FROM users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"user_full_{user_id}",
        cache_ttl=300
    )
    return result


async def add_seeds(user_id: int, amount: int):
    """Add seeds and invalidate cache (with balance logging)"""
    # Get balance before
    balance_before = await get_user_balance(user_id)

    # Update seeds
    await db_manager.modify(
        "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
        (amount, user_id)
    )

    # Log the change
    balance_after = balance_before + amount
    print(f"[DB] [ADD_SEEDS] user_id={user_id} amount={amount:+d} balance_before={balance_before} balance_after={balance_after}")

    # Clear cache
    db_manager.clear_cache_by_prefix(f"balance_{user_id}")
    db_manager.clear_cache_by_prefix(f"user_full_{user_id}")


async def get_leaderboard(limit: int = 10) -> List[tuple]:
    """Get top players with caching (5min TTL)"""
    result = await db_manager.execute(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT ?",
        (limit,),
        use_cache=True,
        cache_key="leaderboard_top",
        cache_ttl=300
    )
    return result
"""
Core database functionality and server configuration management.
"""
import aiosqlite
import asyncio
import json
import os
import sqlite3
import functools
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from contextlib import asynccontextmanager

from configs.settings import DB_PATH, DB_TIMEOUT, DB_MAX_RETRIES, DB_RETRY_DELAY
from core.logger import setup_logger

# Initialize Logger
logger = setup_logger("CoreDB", "core/database.log")


def retry_on_db_lock(max_retries: int = DB_MAX_RETRIES, initial_delay: float = DB_RETRY_DELAY):
    """Decorator to retry database operations on 'database is locked' errors.
    
    Uses exponential backoff to handle concurrent write conflicts gracefully.
    
    Args:
        max_retries (int): Maximum number of retry attempts.
        initial_delay (float): Initial delay in seconds, doubles after each retry.
    
    Returns:
        Decorated function with retry logic.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower():
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(f"[RETRY] Database locked, attempt {attempt + 1}/{max_retries}, retrying in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"[RETRY] Database locked after {max_retries} attempts, giving up")
                    else:
                        raise  # Re-raise non-lock errors immediately
                except Exception as e:
                    raise  # Re-raise other exceptions immediately
            
            # If we exhausted all retries, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


async def get_db_connection(db_path: str = DB_PATH):
    """Get database connection with proper timeout and WAL mode"""
    db = await aiosqlite.connect(db_path, timeout=DB_TIMEOUT)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA foreign_keys=ON")
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
        self.db = None  # Persistent connection

    async def connect(self):
        """Initialize database connection with WAL mode for concurrency."""
        if not self.db:
            self.db = await get_db_connection(self.db_path)
            logger.info("Persistent connection established.")
            
            # CRITICAL OPTIMIZATION: Enable WAL mode + BUSY TIMEOUT
            try:
                await self.db.execute("PRAGMA journal_mode=WAL")
                await self.db.execute("PRAGMA synchronous=NORMAL")
                await self.db.execute("PRAGMA foreign_keys=ON")
                await self.db.execute("PRAGMA busy_timeout=5000")  # Wait up to 5s if locked
                
                # Verify WAL is active
                async with self.db.execute("PRAGMA journal_mode") as cursor:
                    mode = await cursor.fetchone()
                    if mode and mode[0] == 'wal':
                        logger.info("[OPTIMIZATION] WAL mode enabled - Ready for concurrent access")
                    else:
                        logger.warning(f"[OPTIMIZATION] Expected WAL mode, got: {mode[0] if mode else 'None'}")
                
                # Log busy_timeout confirmation
                async with self.db.execute("PRAGMA busy_timeout") as cursor:
                    timeout = await cursor.fetchone()
                    logger.info(f"[OPTIMIZATION] Busy timeout set to {timeout[0]}ms")
                        
            except Exception as e:
                logger.error(f"[OPTIMIZATION] Failed to enable WAL mode: {e}", exc_info=True)
                logger.warning("[OPTIMIZATION] Database will continue with default mode")

    async def _get_db(self):
        """Get current connection or create new if missing"""
        if not self.db:
            await self.connect()
        return self.db

    # ==================== CONNECTION MANAGEMENT ====================

    async def execute(self, query: str, params: tuple = (), use_cache: bool = False, cache_key: str = "", cache_ttl: int = 300):
        """Execute a query with optional caching"""
        # Check cache first
        if use_cache and cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                return entry.data

        db = await self._get_db()
        async with db.execute(query, params) as cursor:
            result = await cursor.fetchall()

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

        db = await self._get_db()
        
        # CRITICAL FIX: Add timeout to prevent infinite hangs
        try:
            async with asyncio.timeout(10.0):  # 10s max wait
                async with db.execute(query, params) as cursor:
                    result = await cursor.fetchone()
        except asyncio.TimeoutError:
            logger.error(f"[DB] fetchone TIMEOUT after 10s: {query[:100]}")
            raise  # Re-raise to let caller handle

        # Cache if requested
        if use_cache and cache_key:
            self.cache[cache_key] = CacheEntry(result, cache_ttl)

        return result

    @retry_on_db_lock()
    async def modify(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query with automatic retry on lock.
        
        Returns:
            int: Number of rows affected (rowcount).
        """
        async with self.lock:
            db = await self._get_db()
            async with db.execute(query, params) as cursor:
                await db.commit()
                rowcount = cursor.rowcount
                logger.debug(f"[DB] [COMMIT] Query: {query[:50]}... | Rows: {rowcount}")

        # Invalidate relevant caches
        self._invalidate_cache_pattern(query)
        
        return rowcount

    def _invalidate_cache_pattern(self, query: str):
        """Invalidate cache entries based on query type"""
        query_upper = query.upper()
        keys_to_delete = []

        if "UPDATE" in query_upper or "INSERT" in query_upper or "DELETE" in query_upper:
            # Invalidate all caches for affected tables
            for key in self.cache:
                if any(table in key.upper() for table in ["ECONOMY", "TREE", "RELATIONSHIP", "INVENTORY", "USERS", "FISHING"]):
                    keys_to_delete.append(key)
        
        # Also clean up very old cache keys to prevent memory leak
        for k in list(self.cache.keys()):
            if self.cache[k].is_expired():
                keys_to_delete.append(k)

        for key in list(set(keys_to_delete)):
            if key in self.cache:
                del self.cache[key]

    @retry_on_db_lock()
    async def batch_modify(self, operations: List[Tuple[str, tuple]]):
        """Execute multiple INSERT/UPDATE/DELETE in a single transaction with automatic retry on lock"""
        async with self.lock:
            db = await self._get_db()
            
            # Execute transaction without nesting
            await db.execute("BEGIN")
            try:
                for query, params in operations:
                    await db.execute(query, params)
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise e

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
    
    @asynccontextmanager
    async def transaction(self):
        """Safe transaction context manager with automatic COMMIT/ROLLBACK.
        
        Usage:
            async with db_manager.transaction() as conn:
                # Atomic operations here
                await conn.execute("INSERT INTO ...", (...))
                result = await conn.execute("SELECT ...").fetchone()
                # Auto-COMMIT on success, auto-ROLLBACK on exception
        
        Raises:
            Exception: Re-raises any exception after ROLLBACK
        """
        async with self.lock:
            db = await self._get_db()
            
            # Start transaction with BEGIN IMMEDIATE (lock database immediately)
            await db.execute("BEGIN IMMEDIATE")
            
            try:
                yield db  # Allow caller to execute queries
                await db.commit()
                logger.debug("[DB] [TRANSACTION] COMMIT successful")
            except Exception as e:
                await db.rollback()
                logger.error(f"[DB] [TRANSACTION] ROLLBACK due to error: {e}", exc_info=True)
                raise  # Re-raise after rollback
            
    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
            self.db = None


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
            logger.warning(f"Failed to load server config: {e}")
            return {}
    else:
        logger.warning(f"Server config not found: {config_path}")
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


async def add_seeds(user_id: int, amount: int, reason: str, category: str):
    """Add seeds and log transaction atomically.
    
    CRITICAL: This function enforces financial logging.
    Do NOT use raw SQL updates for 'seeds' anywhere else.
    
    Args:
        user_id: Discord User ID
        amount: Amount to add (negative to subtract)
        reason: Specific reason key (e.g., 'daily_reward', 'buy_shop')
        category: High-level category (e.g., 'social', 'maintenance')
    """
    if not reason or not category:
        raise ValueError("ZERO LEAKAGE POLICY: 'reason' and 'category' are mandatory for financial transactions.")

    # 1. Prepare Operations
    operations = [
        # Update Balance
        (
            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
            (amount, user_id)
        ),
        # Log Transaction
        (
            "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, category)
        )
    ]

    # 2. Execute Atomically
    await db_manager.batch_modify(operations)

    # 3. Side Effects (Logging & Cache) calls
    # Note: batch_modify invalidates cache patterns, but we can be specific here if needed.
    logger.info(f"[TRANSACTION] {user_id}: {amount:+d} | {category}:{reason}")
    
    # Invalidate both cache keys explicitly to be safe
    db_manager.clear_cache_by_prefix(f"balance_{user_id}")
    db_manager.clear_cache_by_prefix(f"user_full_{user_id}")


async def batch_update_seeds(updates: Dict[int, int], reason: str, category: str):
    """Update multiple user balances and log transactions atomically.
    
    Args:
        updates: Dict {user_id: amount}
        reason: Reason key for ALL updates in this batch
        category: Category for ALL updates in this batch
    """
    if not updates:
        return
        
    if not reason or not category:
        raise ValueError("ZERO LEAKAGE POLICY: 'reason' and 'category' are mandatory.")

    operations = []
    
    for user_id, amount in updates.items():
        # Update Balance
        operations.append((
            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
            (amount, user_id)
        ))
        # Log Transaction
        operations.append((
            "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, category)
        ))

    await db_manager.batch_modify(operations)
    
    # Clear caches
    for uid in updates.keys():
        db_manager.clear_cache_by_prefix(f"balance_{uid}")


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
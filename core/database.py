import os
import asyncio
import logging
import re
import asyncpg
from typing import Optional, List, Any, Dict, Tuple
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """PostgreSQL Database Manager using asyncpg.
    
    Features:
    - Connection Pooling
    - Automatic '?' to '$n' parameter conversion (sqlite compat)
    - Context Managers for connections and transactions
    - Robust Error Handling
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, 'pool'):
            return
            
        self.pool: Optional[asyncpg.Pool] = None
        # Retrieve credentials from environment (loaded by main bot or dotenv)
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.database = os.getenv("DB_NAME", "discord_bot_db")
        self.user = os.getenv("DB_USER", "discord_bot")
        self.password = os.getenv("DB_PASS", "discord_bot_password")
        
    async def connect(self):
        """Initialize Connection Pool."""
        if self.pool:
            return

        try:
            logger.info("Initializing PostgreSQL Connection Pool...")
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=5,
                max_size=20
            )
            logger.info("PostgreSQL Pool established successfully.")
            
            # Verify connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                
        except Exception as e:
            logger.critical(f"Failed to connect to PostgreSQL: {e}")
            raise e

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL Pool closed.")

    def _convert_sql_params(self, sql: str) -> str:
        """Convert SQLite-style '?' placeholders to Postgres '$1', '$2'..."""
        if "?" not in sql:
            return sql
            
        parts = sql.split("?")
        if len(parts) == 1:
            return sql
            
        new_sql = ""
        for i, part in enumerate(parts[:-1]):
            new_sql += f"{part}${i+1}"
        new_sql += parts[-1]
        return new_sql

    async def execute(self, sql: str, *args) -> str:
        """Execute a query (INSERT/UPDATE/DELETE) within transaction.
        
        Args:
            sql: SQL query with $1, $2, ... placeholders
            *args: Individual parameters OR single tuple of parameters
            
        Returns:
            Status string from asyncpg
        """
        if not self.pool:
            await self.connect()

        # asyncpg expects: execute(sql, arg1, arg2, arg3) OR execute(sql, *tuple)
        # If called with single tuple: execute(sql, (a, b, c))
        # Then args = ((a, b, c),) and we need to unpack it
        # If called with multiple args: execute(sql, a, b, c)  
        # Then args = (a, b, c) and we pass as is
        
        # Check if args is a single tuple containing all params
        if len(args) == 1 and isinstance(args[0], tuple):
            # Called as: execute(sql, (param1, param2, param3))
            params_to_pass = args[0]
        else:
            # Called as: execute(sql, param1, param2, param3)
            params_to_pass = args

        sql = self._convert_sql_params(sql)
        
        async with self.pool.acquire() as conn:
            try:
                # asyncpg returns status string (e.g. "INSERT 0 1")
                return await conn.execute(sql, *params_to_pass)
            except Exception as e:
                logger.error(f"DB Execute Error: {sql} | Params: {params_to_pass} | Error: {e}")
                raise e

    async def executemany(self, sql: str, parameters: List[Tuple]) -> None:
        """Execute batch query."""
        if not self.pool:
            await self.connect()

        sql = self._convert_sql_params(sql)

        async with self.pool.acquire() as conn:
            try:
                await conn.executemany(sql, parameters)
            except Exception as e:
                logger.error(f"DB Batch Error: {sql} | Error: {e}")
                raise e

    async def fetchone(self, sql: str, *args) -> Optional[Tuple]:
        """Fetch a single row."""
        if not self.pool:
            await self.connect()

        # Support legacy tuple passing
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]

        sql = self._convert_sql_params(sql)

        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(sql, *args)
                return tuple(row) if row else None
            except Exception as e:
                logger.error(f"DB FetchOne Error: {sql} | Params: {args} | Error: {e}")
                raise e


    async def fetchall(self, sql: str, *args) -> List[Tuple]:
        """Fetch all rows."""
        if not self.pool:
            await self.connect()

        # Support legacy tuple passing
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]

        sql = self._convert_sql_params(sql)

        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch(sql, *args)
                return [tuple(row) for row in rows]
            except Exception as e:
                logger.error(f"DB FetchAll Error: {sql} | Params: {args} | Error: {e}")
                raise e


    async def fetchrow(self, sql: str, *args):
        """Fetch a single row as a Record object (asyncpg native)."""
        if not self.pool:
            await self.connect()

        # Support legacy tuple passing
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]

        sql = self._convert_sql_params(sql)

        async with self.pool.acquire() as conn:
            try:
                return await conn.fetchrow(sql, *args)
            except Exception as e:
                logger.error(f"DB FetchRow Error: {sql} | Params: {args} | Error: {e}")
                raise e


    async def fetch(self, sql: str, *args):
        """Fetch all rows as Record objects (asyncpg native)."""
        if not self.pool:
            await self.connect()

        # Support legacy tuple passing
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]

        sql = self._convert_sql_params(sql)
        async with self.pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    async def modify(self, sql: str, parameters: Tuple = ()) -> str:
        """Alias for execute (legacy compatibility)."""
        return await self.execute(sql, *parameters)

    @asynccontextmanager
    async def transaction(self):
        """Async Context Manager for Transactions.
        
        Yields:
            asyncpg.Connection: The connection object explicitly.
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            txn = conn.transaction()
            await txn.start()
            try:
                # We wrap the connection to support automatic `?` conversion 
                # inside the transaction execution calls.
                # However, for now, we yield the raw connection and users 
                # must beware.
                # BETTER: Return a proxy helper that does conversion.
                yield _TransactionProxy(conn, self._convert_sql_params)
                await txn.commit()
            except Exception as e:
                await txn.rollback()
                logger.error(f"Transaction Rollback: {e}")
                raise e

class _TransactionProxy:
    """Helper to support '?' param conversion inside transactions."""
    def __init__(self, conn, converter):
        self.conn = conn
        self.converter = converter
        
    async def execute(self, sql, *args):
        """Execute query with auto-flattening of nested tuples.
        
        Handles both calling styles:
        - execute(sql, (p1, p2, p3))  <- Old SQLite style
        - execute(sql, p1, p2, p3)    <- AsyncPG style
        """
        sql = self.converter(sql)
        
        # Auto-flatten if args is a single tuple/list
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]
        
        return await self.conn.execute(sql, *args)
        
    async def fetchrow(self, sql, *args):
        sql = self.converter(sql)
        
        # Auto-flatten if args is a single tuple/list
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]
        
        return await self.conn.fetchrow(sql, *args)
    
    async def fetch(self, sql, *args):
        sql = self.converter(sql)
        
        # Auto-flatten if args is a single tuple/list
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]
        
        return await self.conn.fetch(sql, *args)
    
    async def fetchone(self, sql, *args):
        # Compatibility alias for fetchrow -> returns tuple
        row = await self.fetchrow(sql, *args)
        return tuple(row) if row else None
        
    # Proxy other methods directly if needed
    def __getattr__(self, name):
        return getattr(self.conn, name)

    async def modify(self, sql: str, parameters: Tuple = ()) -> str:
        """Alias for execute to maintain compatibility."""
        return await self.execute(sql, *args)

# Global Instance
db_manager = DatabaseManager()

# --- HELPER FUNCTIONS (Restored for Compatibility) ---

async def get_db_connection():
    """Deprecated: Use db_manager.execute directly."""
    if not db_manager.pool:
         await db_manager.connect()
    return db_manager.pool

async def get_user_balance(user_id: int) -> int:
    """Get user seeds."""
    row = await db_manager.fetchone("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
    return row[0] if row else 0

async def get_user_full(user_id: int) -> Optional[Tuple]:
    """Get full user record."""
    return await db_manager.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

async def add_seeds(user_id: int, amount: int, reason: str = "unknown", category: str = "general") -> int:
    """Add seeds to user and log transaction.
    
    Returns:
        int: New balance
    """
    async with db_manager.transaction() as conn:
        # Update balance
        await conn.execute(
            "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
            amount, user_id
        )
        
        # Log
        await conn.execute(
            "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) "
            "VALUES ($1, $2, $3, $4, NOW())",
            user_id, amount, reason, category
        )
        
        # Get new balance
        row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", user_id)
        return row['seeds'] if row else 0

async def get_leaderboard(limit: int = 10) -> List[Tuple]:
    """Get top rich users."""
    return await db_manager.fetchall(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT ?", 
        (limit,)
    )
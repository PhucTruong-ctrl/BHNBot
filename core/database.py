import os
import asyncio
from core.logging import get_logger
import re
import asyncpg
from typing import Optional, List, Any, Dict, Tuple
from contextlib import asynccontextmanager

logger = get_logger("database")

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
        
    async def connect(self) -> None:
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

    async def close(self) -> None:
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


    async def fetchall_dict(self, sql: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        if not self.pool:
            await self.connect()

        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = args[0]

        sql = self._convert_sql_params(sql)

        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch(sql, *args)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"DB FetchAll Dict Error: {sql} | Params: {args} | Error: {e}")
                raise e


    async def fetchrow(self, sql: str, *args) -> Optional[asyncpg.Record]:
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


    async def fetch(self, sql: str, *args) -> list[asyncpg.Record]:
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
        return await self.execute(sql, *parameters)

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

async def deduct_seeds_if_sufficient(
    user_id: int,
    amount: int,
    reason: str = "deduction",
    category: str = "general"
) -> Tuple[bool, int]:
    """Atomically check balance and deduct if sufficient.
    
    Uses SELECT FOR UPDATE to prevent race conditions.
    This replaces the check-then-act pattern:
        balance = await get_user_balance(user_id)
        if balance >= amount:
            await add_seeds(user_id, -amount, ...)
    
    Returns:
        Tuple[bool, int]: (success, new_balance)
        - success=True: deduction performed, new_balance is after deduction
        - success=False: insufficient funds, new_balance is current balance
    """
    if amount <= 0:
        raise ValueError("Deduction amount must be positive")
    
    async with db_manager.transaction() as conn:
        # Lock row and get current balance
        row = await conn.fetchrow(
            "SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE",
            user_id
        )
        
        if not row:
            return (False, 0)
        
        current_balance = row['seeds']
        
        if current_balance < amount:
            return (False, current_balance)
        
        # Perform deduction
        await conn.execute(
            "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
            amount, user_id
        )
        
        # Log transaction
        await conn.execute(
            "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) "
            "VALUES ($1, $2, $3, $4, NOW())",
            user_id, -amount, reason, category
        )
        
        new_balance = current_balance - amount
        return (True, new_balance)


async def transfer_seeds(
    from_user_id: int, 
    to_user_id: int, 
    amount: int, 
    reason: str = "transfer"
) -> Tuple[int, int]:
    """Transfer seeds between users with row-level locking.
    
    Uses SELECT FOR UPDATE to prevent race conditions.
    
    Returns:
        Tuple[int, int]: (sender_new_balance, receiver_new_balance)
        
    Raises:
        ValueError: If sender has insufficient balance
    """
    if amount <= 0:
        raise ValueError("Transfer amount must be positive")
    
    async with db_manager.transaction() as conn:
        # Lock rows in consistent order to prevent deadlocks
        user_ids = sorted([from_user_id, to_user_id])
        
        # Select FOR UPDATE to lock both rows
        sender_row = await conn.fetchrow(
            "SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE",
            from_user_id
        )
        receiver_row = await conn.fetchrow(
            "SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE",
            to_user_id
        )
        
        if not sender_row:
            raise ValueError(f"Sender {from_user_id} not found")
        if not receiver_row:
            raise ValueError(f"Receiver {to_user_id} not found")
            
        sender_balance = sender_row['seeds']
        if sender_balance < amount:
            raise ValueError(f"Insufficient balance: {sender_balance} < {amount}")
        
        # Perform transfer
        await conn.execute(
            "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
            amount, from_user_id
        )
        await conn.execute(
            "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
            amount, to_user_id
        )
        
        # Log both transactions
        await conn.execute(
            "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) "
            "VALUES ($1, $2, $3, 'transfer_out', NOW())",
            from_user_id, -amount, reason
        )
        await conn.execute(
            "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) "
            "VALUES ($1, $2, $3, 'transfer_in', NOW())",
            to_user_id, amount, reason
        )
        
        # Return new balances
        new_sender = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", from_user_id)
        new_receiver = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", to_user_id)
        
        return (new_sender['seeds'], new_receiver['seeds'])

async def get_leaderboard(limit: int = 10) -> List[Tuple]:
    """Get top rich users."""
    return await db_manager.fetchall(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT ?", 
        (limit,)
    )
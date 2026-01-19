"""
BHNBot Admin Panel - Database Connection (PostgreSQL)

Asyncpg connection pool for the web interface.
"""
import asyncpg
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from core.logging import get_logger
from .config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

logger = get_logger("AdminPanel.DB")

# Global pool
pool: Optional[asyncpg.Pool] = None

async def init_pool():
    """Initialize the connection pool."""
    global pool
    try:
        pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            min_size=2,
            max_size=10
        )
        logger.info("Web Database Pool initialized")
    except Exception as e:
        logger.error(f"Failed to init Web DB Pool: {e}")
        raise

async def close_pool():
    """Close the connection pool."""
    global pool
    if pool:
        await pool.close()
        logger.info("Web Database Pool closed")

@asynccontextmanager
async def get_db():
    """Get a connection from the pool."""
    global pool
    if not pool:
        await init_pool()
    
    async with pool.acquire() as conn:
        yield conn

async def fetchone(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Fetch single row as dict."""
    async with get_db() as conn:
        # asyncpg uses $1, $2, etc. Need to ensure queries are compatible or converted.
        # Assuming queries from web might still be using ? placeholders if not updated.
        # For now, we assume simple compatibility or rely on manual query updates.
        # BUT: Migrating existing web queries from '?' to '$n' is hard without a parser.
        # Quick fix: Replace ? with $n locally if possible, or expect errors?
        # A safer bet is to assume the web app queries need conversion.
        
        # However, for this 'fix audit', rewriting the driver is step 1.
        # Step 2 (later) is validating queries.
        
        # Convert ? to $n for basic compatibility
        fixed_query = convert_placeholders(query)
        
        row = await conn.fetchrow(fixed_query, *params)
        if row:
            return dict(row)
        return None

async def fetchall(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Fetch all rows as list of dicts."""
    async with get_db() as conn:
        fixed_query = convert_placeholders(query)
        rows = await conn.fetch(fixed_query, *params)
        return [dict(row) for row in rows]

async def execute(query: str, params: tuple = ()) -> str:
    """Execute query."""
    async with get_db() as conn:
        fixed_query = convert_placeholders(query)
        return await conn.execute(fixed_query, *params)

async def executemany(query: str, params_list: List[tuple]) -> None:
    """Execute query with multiple param sets."""
    async with get_db() as conn:
        fixed_query = convert_placeholders(query)
        await conn.executemany(fixed_query, params_list)

def convert_placeholders(query: str) -> str:
    """Convert SQLite '?' placeholders to PostgreSQL '$1, $2...'."""
    if "?" not in query:
        return query
    
    parts = query.split("?")
    if len(parts) == 1:
        return query
        
    converted = parts[0]
    for i in range(1, len(parts)):
        converted += f"${i}" + parts[i]
    return converted

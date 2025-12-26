"""
BHNBot Admin Panel - Database Connection

SQLite with WAL mode for concurrent access (Bot + Web).
"""
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Dict, Any, Optional
import logging

from .config import DATABASE_PATH

logger = logging.getLogger("AdminPanel.DB")


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Get database connection with WAL mode enabled.
    
    WAL mode allows concurrent reads from both Bot and Web.
    busy_timeout prevents immediate failure on lock contention.
    """
    db = await aiosqlite.connect(DATABASE_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")  # Wait 5s if locked
    db.row_factory = aiosqlite.Row  # Return dict-like rows
    try:
        yield db
    finally:
        await db.close()


async def fetchone(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Fetch single row as dict."""
    async with get_db() as db:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def fetchall(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Fetch all rows as list of dicts."""
    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def execute(query: str, params: tuple = ()) -> int:
    """Execute query and return lastrowid."""
    async with get_db() as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def executemany(query: str, params_list: List[tuple]) -> None:
    """Execute query with multiple param sets."""
    async with get_db() as db:
        await db.executemany(query, params_list)
        await db.commit()

"""
Inventory Cache System - Write-Through Strategy
Prioritizes data safety and ACID compliance over raw write speed.
"""
import asyncio
from typing import Dict, Optional
import logging

logger = logging.getLogger("InventoryCache")

class InventoryCache:
    """
    Singleton-style Inventory Cache that wraps the DatabaseManager.
    
    Strategy: Write-Through
    - Reads: Check RAM -> Miss? Load from DB.
    - Writes: Write to DB FIRST (ACID) -> Success? Update RAM.
    """
    def __init__(self, db_manager):
        self.db = db_manager
        self._cache: Dict[int, Dict[str, int]] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
        
    def _get_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific user to prevent race conditions."""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def _load_user_inventory(self, user_id: int):
        """Load user inventory from DB into cache."""
        try:
            # Query all items for this user
            rows = await self.db.fetchall(
                "SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0",
                (user_id,)
            )
            # Convert to dict
            self._cache[user_id] = {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"[CACHE] Failed to load inventory for {user_id}: {e}")
            # Ensure we at least have an empty dict to prevent crash loops
            if user_id not in self._cache:
                self._cache[user_id] = {}

    async def get(self, user_id: int, item_key: str) -> int:
        """Get item quantity. Loads from DB on cache miss."""
        if user_id not in self._cache:
            await self._load_user_inventory(user_id)
        
        return self._cache[user_id].get(item_key, 0)

    async def get_all(self, user_id: int) -> Dict[str, int]:
        """Get entire user inventory. Loads from DB on cache miss."""
        if user_id not in self._cache:
            await self._load_user_inventory(user_id)
            
        # Return a COPY to prevent external modification
        return self._cache[user_id].copy()

    async def modify(self, user_id: int, item_key: str, delta: int, item_type: str = "item") -> int:
        """
        Atomic Write-Through Modification.
        
        1. Acquire User Lock.
        2. Write to DB (Upsert).
        3. Update Cache.
        """
        async with self._get_lock(user_id):
            # Ensure cache is primed BEFORE DB write to avoid double counting
            if user_id not in self._cache:
                await self._load_user_inventory(user_id)

            # 1. WRITE TO DB (Upsert)
            # We use ON CONFLICT to handle both INSERT and UPDATE in one go
            # This is safer than SELECT then INSERT/UPDATE
            try:
                if delta == 0:
                    return await self.get(user_id, item_key)

                # Logic: We update the quantity.
                # If row doesn't exist, we insert (quantity = delta).
                # Note: We need to handle the case where result < 0 in DB? 
                # Ideally DB constraint should prevent negative, but here we trust logic validation layer.
                
                await self.db.modify(
                    """
                    INSERT INTO inventory (user_id, item_id, quantity, item_type) 
                    VALUES (?, ?, GREATEST(0, ?), ?)
                    ON CONFLICT(user_id, item_id) 
                    DO UPDATE SET quantity = GREATEST(0, inventory.quantity + EXCLUDED.quantity)
                    """,
                    (user_id, item_key, delta, item_type)
                )
                
                # 2. UPDATE CACHE
                # Calculate new quantity locally
                current_qty = self._cache[user_id].get(item_key, 0)
                new_qty = max(0, current_qty + delta)
                
                if new_qty == 0:
                    # Item depleted, remove from cache to save RAM
                    self._cache[user_id].pop(item_key, None)
                else:
                    self._cache[user_id][item_key] = new_qty
                    
                return new_qty
                
            except Exception as e:
                logger.error(f"[CACHE] Modify failed for {user_id}, {item_key}: {e}")
                # Invalidate cache for this user to ensure we re-read strict truth next time
                await self.invalidate(user_id)
                raise e

    async def invalidate(self, user_id: int):
        """Force remove user from cache. Next access will re-fetch from DB."""
        if user_id in self._cache:
            del self._cache[user_id]
            logger.debug(f"[CACHE] Invalidated user {user_id}")

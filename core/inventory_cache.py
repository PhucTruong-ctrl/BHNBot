"""
Inventory Cache System - Direct Read Strategy
Prioritizes data strict consistency over aggressive caching.
"""
from core.logging import get_logger
from typing import Dict, Any

logger = get_logger("inventory_cache")

class InventoryCache:
    """
    Inventory Management Wrapper.
    
    Strategy: DIRECT READ (No caching for critical data)
    To fix "Infinite Money" / "Ghost Item" bugs, we read directly from DB for !tuido.
    Optimization can be re-introduced later if DB load becomes an issue.
    """
    def __init__(self, db_manager):
        self.db = db_manager
        
    async def get_inventory(self, user_id: int) -> Dict[str, int]:
        """
        Fetch ALL valid items for a user directly from DB.
        
        Returns:
            Dict[item_id, quantity]
        """
        try:
            # Direct DB Fetch - No Cache
            # Note: We use ? for placeholders if using sqlite/aiosqlite as per codebase conventions
            # If underlying is asyncpg it might need $1, but database_manager uses ? so we follow suit.
            # Also, fetchall returns tuples, so we must use index access.
            rows = await self.db.fetchall(
                "SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0",
                (user_id,)
            )
            
            # Convert to dict (Index 0=item_id, Index 1=quantity)
            inventory = {row[0]: row[1] for row in rows}
            return inventory
            
        except Exception as e:
            logger.error(f"[INVENTORY] Failed to fetch inventory for {user_id}: {e}", exc_info=True)
            return {}

    async def get_item(self, user_id: int, item_id: str) -> int:
        """Get specific item quantity directly from DB"""
        try:
            # Check if fetchval exists, otherwise use fetchone
            if hasattr(self.db, 'fetchval'):
                val = await self.db.fetchval(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                )
                return val if val else 0
            else:
                 row = await self.db.fetchone(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                 )
                 return row[0] if row else 0
        except Exception as e:
            logger.error(f"[INVENTORY] Failed to fetch item {item_id} for {user_id}: {e}")
            return 0

    async def get_all(self, user_id: int) -> Dict[str, int]:
        """Alias for get_inventory to match existing code usage."""
        return await self.get_inventory(user_id)

    async def modify(self, user_id: int, item_id: str, amount: int, item_type: str = "tool") -> bool:
        """
        Directly modify item quantity in Database.
        
        Args:
            user_id: User ID
            item_id: Key of the item
            amount: Amount to add (positive) or remove (negative)
            item_type: Category of item (default: tool)
        
        Returns:
             bool: True if successful
        """
        try:
            if amount == 0:
                return True
                
            if amount > 0:
                # UPSERT for addition
                # Using ? placeholder for SQLite compatibility
                await self.db.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, quantity, item_type)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (user_id, item_id) 
                    DO UPDATE SET quantity = inventory.quantity + ?
                    """,
                    user_id, item_id, amount, item_type, amount
                )
            else:
                # UPDATE for subtraction
                await self.db.execute(
                    """
                    UPDATE inventory 
                    SET quantity = quantity + ? 
                    WHERE user_id = ? AND item_id = ?
                    """,
                    amount, user_id, item_id
                )
                
            return True
        except Exception as e:
            logger.error(f"[INVENTORY] Failed to modify {item_id} for {user_id}: {e}")
            return False

    async def invalidate(self, user_id: int):
        """
        Sentinel method for backward compatibility.
        Since we don't cache, this is a no-op, but necessary for existing code calls.
        """
        # No-op in Direct Read mode
        pass

    async def update_local_cache(self, user_id: int, item_id: str, quantity: int):
         """
         Sentinel method for backward compatibility.
         """
         pass

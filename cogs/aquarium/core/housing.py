
from typing import Optional, List, Dict
from core.database import db_manager
from core.logger import setup_logger

logger = setup_logger("AquariumHousing", "logs/aquarium.log")

class HousingManager:
    """Business logic for Housing System (Project Aquarium)."""

    @staticmethod
    async def has_house(user_id: int) -> bool:
        """Check if user already has a house (thread)."""
        rows = await db_manager.execute(
            "SELECT home_thread_id FROM users WHERE user_id = ?", 
            (user_id,)
        )
        return bool(rows and rows[0][0])

    @staticmethod
    async def get_home_thread_id(user_id: int) -> Optional[int]:
        """Get the Discord Thread ID of the user's home."""
        rows = await db_manager.execute(
            "SELECT home_thread_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        return rows[0][0] if rows and rows[0][0] else None

    @staticmethod
    async def register_house(user_id: int, thread_id: int) -> bool:
        """
        Register a new house in the database.
        1. Update users.home_thread_id
        2. Initialize 5 empty slots in home_slots
        3. Create user_house record
        """
        try:
            operations = []
            
            # 1. Update User
            operations.append((
                "UPDATE users SET home_thread_id = ? WHERE user_id = ?",
                (thread_id, user_id)
            ))
            
            # 2. Update User House Table
            operations.append((
                "INSERT OR IGNORE INTO user_house (user_id, thread_id, house_level, slots_unlocked) VALUES (?, ?, 1, 5)",
                (user_id, thread_id)
            ))

            # 3. Init Default Slots (0-4)
            for i in range(5):
                operations.append((
                    "INSERT OR IGNORE INTO home_slots (user_id, slot_index, item_id) VALUES (?, ?, NULL)",
                    (user_id, i)
                ))
            
            await db_manager.batch_modify(operations)
            
            logger.info(f"[HOUSE_CREATE] Registed house for User {user_id}, Thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"[HOUSE_REGISTER_ERROR] User {user_id}: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_slots(user_id: int) -> List[Optional[str]]:
        """Get list of item_ids in slots 0-4."""
        rows = await db_manager.execute(
            "SELECT slot_index, item_id FROM home_slots WHERE user_id = ? ORDER BY slot_index ASC",
            (user_id,)
        )
            
        # Default 5 None
        slots = [None] * 5
        for idx, item in rows:
            if idx < 5: # Limit just in case
                slots[idx] = item
        return slots

housing_manager = HousingManager()

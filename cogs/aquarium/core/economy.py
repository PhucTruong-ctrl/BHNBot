
from typing import Dict, Tuple, List
from core.database import db_manager, DatabaseManager
from core.logger import setup_logger
from cogs.aquarium.constants import TRASH_ITEM_IDS, LEAF_COIN_RATE, STREAK_BONUS_DAYS, STREAK_BONUS_PERCENT

logger = setup_logger("AquariumEconomy", "logs/aquarium.log")

class AquariumEconomy:
    """Business logic for Aquarium Economy (Recycle, Purchasing)."""

    @staticmethod
    async def process_checklist_recycle(user_id: int) -> Tuple[bool, str, int, int]:
        """
        Processes recycling of ALL trash items in user's inventory.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            Tuple(success, message, trash_count, leaf_coins_gained)
        """
        # 1. Get User Inventory
        # execute returns list of rows directly
        inventory_rows = await db_manager.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id = ?", 
            (user_id,)
        )

        user_trash = {row[0]: row[1] for row in inventory_rows if row[0] in TRASH_ITEM_IDS and row[1] > 0}
        
        if not user_trash:
            return False, "Bạn không có rác nào để tái chế! Hãy đi câu cá thêm nhé.", 0, 0

        total_trash_count = sum(user_trash.values())
        base_coins = total_trash_count * LEAF_COIN_RATE
        
        # Streak Calculation (Placeholder for now, implementation later if needed)
        final_coins = base_coins 

        try:
            operations = []
            
            # 2. Remove Trash from Inventory
            # Delete entries for trash items found
            for item_id, amount in user_trash.items():
                operations.append((
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                ))
            
            # 3. Add Leaf Coins to User
            operations.append((
                "UPDATE users SET leaf_coin = leaf_coin + ? WHERE user_id = ?",
                (final_coins, user_id)
            ))
            
            # Execute batch transaction
            await db_manager.batch_modify(operations)
            
            # Log transaction
            logger.info(f"[RECYCLE] User {user_id} recycled {total_trash_count} trash for {final_coins} Leaf Coins.")
                
            return True, f"♻️ Đã tái chế **{total_trash_count}** rác thành **{final_coins} Xu Lá**!", total_trash_count, final_coins

        except Exception as e:
            logger.error(f"[RECYCLE_ERROR] User {user_id}: {e}", exc_info=True)
            return False, "❌ Lỗi hệ thống khi tái chế. Vui lòng thử lại sau.", 0, 0

aquarium_economy = AquariumEconomy()

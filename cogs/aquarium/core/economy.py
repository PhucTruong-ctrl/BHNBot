
from typing import Dict, Tuple, List
import random
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
        # Bonus: 10% chance to get Fertilizer per trash item
        bonus_fertilizer = 0
        for _ in range(total_trash_count):
            if random.random() < 0.1:
                bonus_fertilizer += 1

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
            
            # 4. Add Bonus Fertilizer
            if bonus_fertilizer > 0:
                operations.append((
                    """
                    INSERT INTO inventory (user_id, item_id, quantity) 
                    VALUES (?, 'phan_bon', ?)
                    ON CONFLICT(user_id, item_id) 
                    DO UPDATE SET quantity = quantity + ?
                    """,
                    (user_id, bonus_fertilizer, bonus_fertilizer)
                ))
            
            # Execute batch transaction
            await db_manager.batch_modify(operations)
            
            # Log transaction
            logger.info(f"[RECYCLE] User {user_id} recycled {total_trash_count} trash for {final_coins} Leaf Coins + {bonus_fertilizer} Fertilizer.")
                
            msg = f"♻️ Đã tái chế **{total_trash_count}** rác thành **{final_coins} Xu Lá**!"
            if bonus_fertilizer > 0:
                msg += f"\n💩 Bạn may mắn nhận thêm **{bonus_fertilizer} Phân Bón** (10%)!"
            
            return True, msg, total_trash_count, final_coins

        except Exception as e:
            logger.error(f"[RECYCLE_ERROR] User {user_id}: {e}", exc_info=True)
            return False, "❌ Lỗi hệ thống khi tái chế. Vui lòng thử lại sau.", 0, 0

    @staticmethod
    async def add_leaf_coins(user_id: int, amount: int, reason: str = "admin_grant") -> bool:
        """
        Add (or subtract) Leaf Coins for a user.
        
        Args:
            user_id: User ID
            amount: Amount to add (negative to subtract)
            reason: Reason for logging
        """
        try:
            # Atomic update
            # We use direct SQL as transactions are now manual (autocommit off) 
            # batch_modify handles BEGIN/COMMIT since we fixed database.py
            
            operations = [(
                "UPDATE users SET leaf_coin = leaf_coin + ? WHERE user_id = ?",
                (amount, user_id)
            )]
            
            await db_manager.batch_modify(operations)
            logger.info(f"[LEAF_COIN] User {user_id} Change: {amount:+d} Reason: {reason}")
            return True
        except Exception as e:
            logger.error(f"[LEAF_COIN_ERROR] User {user_id}: {e}", exc_info=True)
            return False

aquarium_economy = AquariumEconomy()

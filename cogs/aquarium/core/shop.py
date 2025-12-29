
from typing import Tuple, Optional
from core.database import db_manager
from core.logger import setup_logger
from ..constants import DECOR_ITEMS

logger = setup_logger("AquariumShop", "logs/aquarium.log")

class AquariumShop:
    """Business logic for Buying/Selling Decor."""

    @staticmethod
    async def buy_decor(user_id: int, item_id: str) -> Tuple[bool, str]:
        """
        Process purchase of a decor item.
        Checks: valid item, sufficient balances (Seeds + Leaf).
        Result: Deduct balance, Add to user_decor.
        """
        if item_id not in DECOR_ITEMS:
            return False, "❌ Vật phẩm không tồn tại trong cửa hàng."
            
        item = DECOR_ITEMS[item_id]
        cost_seeds = item['price_seeds']
        cost_leaf = item['price_leaf']
        item_name = item['name']

        # 1. Check Balances
        # We need to fetch seeds and leaf_coin
        rows = await db_manager.execute(
            "SELECT seeds, leaf_coin FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if not rows:
            return False, "❌ Không tìm thấy thông tin người dùng."
            
        current_seeds, current_leaf = rows[0]
        
        if current_seeds < cost_seeds:
            return False, f"❌ Bạn không đủ Seeds! Cần thêm {cost_seeds - current_seeds:,.0f} Seeds."
        
        if current_leaf < cost_leaf:
            return False, f"❌ Bạn không đủ Xu Lá! Cần thêm {cost_leaf - current_leaf} Xu Lá."

        # 2. Process Transaction
        try:
            operations = []
            
            # Deduct Money
            operations.append((
                "UPDATE users SET seeds = seeds - ?, leaf_coin = leaf_coin - ? WHERE user_id = ?",
                (cost_seeds, cost_leaf, user_id)
            ))
            
            # Add Item (Upsert)
            operations.append((
                """INSERT INTO user_decor (user_id, item_id, quantity) 
                   VALUES (?, ?, 1) 
                   ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1""",
                (user_id, item_id)
            ))
            
            await db_manager.batch_modify(operations)
            
            logger.info(f"[BUY_DECOR] User {user_id} bought {item_id} (-{cost_seeds}S, -{cost_leaf}L)")
            return True, f"✅ Mua thành công **{item_name}**! (-{cost_seeds:,} Seeds, -{cost_leaf} Xu Lá)"
            
        except Exception as e:
            logger.error(f"[BUY_ERROR] User {user_id}: {e}", exc_info=True)
            return False, "❌ Lỗi hệ thống khi giao dịch."

aquarium_shop = AquariumShop()

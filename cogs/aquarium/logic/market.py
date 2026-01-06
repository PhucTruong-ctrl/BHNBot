from typing import Tuple, Dict
from core.database import db_manager, get_user_balance
from ..models import UserAquarium, UserDecor
from ..constants import LEAF_COIN_RATE, DECOR_ITEMS, TRASH_ITEM_IDS
import logging
import random

logger = logging.getLogger("MarketEngine")

class MarketEngine:
    """
    Handles Economy (Buying/Recycling).
    HYBRID SYSTEM:
    - Uses SQLite (`db_manager`) for Base Economy (Hạt, Inventory).
    - Uses Postgres (`Tortoise`) for Aquarium Economy (Leaf Coin, Decor).
    """

    @staticmethod
    async def recycle_trash(user_id: int) -> Tuple[bool, str, int, int]:
        """
        Recycle all trash from SQLite Inventory -> Leaf Coins in Postgres.
        Returns: (Success, Message, TrashCount, CoinsGained)
        """
        # 1. [Postgres] Scan Inventory
        # execute -> fetchall for SELECT
        rows = await db_manager.fetchall(
            "SELECT item_id, quantity FROM inventory WHERE user_id = $1", 
            (user_id,)
        )
        user_trash = {row[0]: row[1] for row in rows if row[0] in TRASH_ITEM_IDS and row[1] > 0}
        
        if not user_trash:
            return False, "Bạn không có rác nào để tái chế! Hãy đi câu cá thêm nhé.", 0, 0

        total_trash = sum(user_trash.values())
        leaf_coins = total_trash * LEAF_COIN_RATE
        
        # Bonus Fertilizer Logic (10% chance per item)
        bonus_fertilizer = 0
        for _ in range(total_trash):
            if random.random() < 0.1:
                bonus_fertilizer += 1

        try:
            # 2. [SQLite] Delete Trash & Give Fertilizer
            # We do this first. If it fails, we abort.
            operations = []
            for item_id, _ in user_trash.items():
                operations.append((
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                ))
            
            if bonus_fertilizer > 0:
                operations.append((
                    """
                    INSERT INTO inventory (user_id, item_id, quantity) 
                    VALUES (?, 'phan_bon', ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
                    """,
                    (user_id, bonus_fertilizer, bonus_fertilizer)
                ))
            
            await db_manager.batch_modify(operations)

            # 3. [Postgres] Add Leaf Coins
            # If this fails, we hold a Critical Error (User lost trash but got no coins)
            # Todo: Implement recovery queue?
            user, _ = await UserAquarium.get_or_create(user_id=user_id)
            user.leaf_coin += leaf_coins
            await user.save()

            msg = f"♻️ Đã tái chế **{total_trash}** rác thành **{leaf_coins} Xu Lá**!"
            if bonus_fertilizer > 0:
                msg += f"\n💩 Bạn nhận thêm **{bonus_fertilizer} Phân Bón** (10%)!"
                
            return True, msg, total_trash, leaf_coins

        except Exception as e:
            logger.error(f"[RECYCLE_ERROR] User {user_id}: {e}", exc_info=True)
            return False, "❌ Lỗi hệ thống khi giao dịch.", 0, 0

    @staticmethod
    async def buy_decor(user_id: int, item_key: str, currency: str = 'seeds') -> tuple[bool, str]:
        """
        Buy item. Currency: 'seeds', 'leaf', or 'magic_fruit' (mixed).
        Refactored to use Unified Inventory & ItemSystem.
        """
        from core.item_system import item_system
        
        # 1. Validate Item
        item = item_system.get_item(item_key)
        if not item or item.get('type') != 'decor': 
            return False, "Vật phẩm không tồn tại hoặc không phải nội thất."
        
        # 2. Parse Costs
        price_seeds = item.get('price', {}).get('buy', 999999)
        attrs = item.get('attributes', {})
        price_leaf = attrs.get('price_leaf', 999999)
        price_magic = attrs.get('price_magic_fruit', 0)
        item_name = item.get('name', item_key)
        
        try:
             async with db_manager.transaction() as conn:
                # 3. Check Balance
                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", user_id)
                main_user_bal = row['seeds'] if row else 0
                
                # Check Leaf Coins (Stored in Postgres UserAquarium but we access via ORM outside transaction? 
                # No, better to fetch via SQL if possible, or use hybrid approach.
                # UserAquarium is Tortoise model. We can't lock it via asyncpg conn easily.
                # Risk: Race condition on Leaf Coin if user spams.
                # Solution: For now keep legacy Tortoise for Leaf Coin, but move Decor to Inventory.
                
                user = await UserAquarium.get_or_none(user_id=user_id)
                if not user:
                    user = await UserAquarium.create(user_id=user_id)
                
                if currency == 'seeds':
                    if main_user_bal < price_seeds:
                        return False, f"Thiếu Hạt! Cần {price_seeds:,}."
                    
                    await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", price_seeds, user_id)
                    await conn.execute(
                        "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, $3, $4, NOW())",
                        user_id, -price_seeds, f"buy_decor_{item_key}", "aquarium"
                    )
                    
                elif currency == 'leaf':
                    if user.leaf_coin < price_leaf:
                        return False, f"Thiếu Xu Lá! Cần {price_leaf}."
                    # Deduct via ORM (Separate Connection)
                    user.leaf_coin -= price_leaf
                    await user.save()
                    
                elif currency == 'magic_fruit':
                    if main_user_bal < price_seeds:
                         return False, f"Thiếu Hạt! Cần {price_seeds:,}."
                    
                    row_fruit = await conn.fetchrow("SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = 'magic_fruit'", user_id)
                    fruit_count = row_fruit['quantity'] if row_fruit else 0
                    
                    if fruit_count < price_magic:
                        return False, f"Thiếu Quả Thần! Cần {price_magic}."
                        
                    await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", price_seeds, user_id)
                    await conn.execute(
                        "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, $3, $4, NOW())",
                        user_id, -price_seeds, f"buy_decor_special_{item_key}", "aquarium"
                    )
                    await conn.execute("UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = 'magic_fruit'", price_magic, user_id)
                    
                else:
                    return False, "Loại tiền tệ không hợp lệ."

                # 4. Add to Unified Inventory (Main DB)
                # Replaces old UserDecor table logic
                await conn.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, quantity) 
                    VALUES ($1, $2, 1)
                    ON CONFLICT(user_id, item_id) 
                    DO UPDATE SET quantity = inventory.quantity + 1
                    """,
                    user_id, item_key
                )
                
                return True, f"Mua thành công **{item_name}**!"
        except Exception as e:
            logger.error(f"[BUY_ERROR] {e}")
            return False, "Lỗi giao dịch."

    @staticmethod
    async def add_leaf_coins(user_id: int, amount: int, reason: str = "") -> bool:
        """Admin/System grant Leaf Coins."""
        try:
            user, _ = await UserAquarium.get_or_create(user_id=user_id)
            user.leaf_coin += amount
            await user.save()
            logger.info(f"[ADMIN_GRANT] User {user_id} +{amount} LeafCoins. Reason: {reason}")
            return True
        except Exception as e:
            logger.error(f"[ADMIN_GRANT_ERROR] User {user_id}: {e}", exc_info=True)
            return False

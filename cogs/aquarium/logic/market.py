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
        """
        item = DECOR_ITEMS.get(item_key)
        if not item: return False, "Vật phẩm không tồn tại."
        
        cost_seeds = item.get('price_seeds', 999999)
        cost_leaf = item.get('price_leaf', 999999)
        cost_magic_fruit = item.get('price_magic_fruit', 0)
        
        try:
             async with db_manager.transaction() as conn:
                # 1. Check Balance
                # Note: For strict ACID, we should fetch balance via 'conn' here, but get_user_balance uses db_manager.fetchone (new conn).
                # Ideally read via conn.
                
                # Manual fetch via conn for ACID
                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", user_id)
                main_user_bal = row['seeds'] if row else 0
                
                user = await UserAquarium.get_or_none(user_id=user_id)
                if not user:
                    user = await UserAquarium.create(user_id=user_id) # This is separate Postgres transaction (Tortoise). Acceptable hybrid risk.
                
                if currency == 'seeds':
                    if main_user_bal < cost_seeds:
                        return False, f"Thiếu Hạt! Cần {cost_seeds:,}."
                    # Deduct with Log (Inline for Atomicity)
                    await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", cost_seeds, user_id)
                    await conn.execute(
                        "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, $3, $4, NOW())",
                        user_id, -cost_seeds, f"buy_decor_{item_key}", "aquarium"
                    )
                    
                elif currency == 'leaf':
                    if user.leaf_coin < cost_leaf:
                        return False, f"Thiếu Xu Lá! Cần {cost_leaf}."
                    # Deduct via ORM
                    user.leaf_coin -= cost_leaf
                    await user.save()
                    
                elif currency == 'magic_fruit':
                    # Special: Requires Seeds AND Magic Fruit
                    if main_user_bal < cost_seeds:
                         return False, f"Thiếu Hạt! Cần {cost_seeds:,}."
                    
                    # Check Magic Fruit (Inventory) - Use conn
                    # Note: db_manager uses $1 params, but inventory schema uses user_id, item_id
                    row_fruit = await conn.fetchrow("SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = 'magic_fruit'", user_id)
                    fruit_count = row_fruit['quantity'] if row_fruit else 0
                    
                    if fruit_count < cost_magic_fruit:
                        return False, f"Thiếu Quả Thần! Cần {cost_magic_fruit}."
                        
                    # Deduct Seeds
                    await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", cost_seeds, user_id)
                    await conn.execute(
                        "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES ($1, $2, $3, $4, NOW())",
                        user_id, -cost_seeds, f"buy_decor_special_{item_key}", "aquarium"
                    )
                    
                    # Deduct Fruit
                    await conn.execute("UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = 'magic_fruit'", cost_magic_fruit, user_id)
                    
                else:
                    return False, "Loại tiền tệ không hợp lệ."

                # 2. Add to Decor Inventory
                # This is separate Postgres transaction via Tortoise.
                # If this fails, the SQLite transaction (conn) rolls back automatically due to Exception bubbling?
                # Yes, if await decor.save() raises, exception is caught by except block, which calls txn.rollback() inside db_manager.transaction() context?
                # No, db_manager.transaction handles rollback on exception exit.
                decor, _ = await UserDecor.get_or_create(user=user, item_id=item_key)
                decor.quantity += 1
                await decor.save()
                
                return True, f"Mua thành công **{item['name']}**!"
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

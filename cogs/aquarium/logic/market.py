
from typing import Tuple, Dict
from core.database import db_manager # SQLite
from ..models import UserAquarium, UserDecor # Postgres
from ..constants import DECOR_ITEMS, TRASH_ITEM_IDS, LEAF_COIN_RATE
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
    async def buy_decor(user_id: int, item_key: str, currency: str = 'leaf') -> Tuple[bool, str]:
        """
        Buy decor item.
        currency: 'leaf' (Postgres) or 'seeds' (SQLite).
        """
        item = DECOR_ITEMS.get(item_key)
        if not item:
            return False, "Vật phẩm không tồn tại."

        price = item.get('price_leaf') if currency == 'leaf' else item.get('price_seeds')
        if price is None:
            return False, f"Vật phẩm này không bán bằng {currency}."

        try:
            # 1. Deduct Money
            if currency == 'leaf':
                # [Postgres]
                user = await UserAquarium.get_or_none(user_id=user_id)
                if not user or user.leaf_coin < price:
                    return False, f"Không đủ Xu Lá! (Cần {price})"
                
                user.leaf_coin -= price
                await user.save()
            else:
                # [SQLite]
                # Check balance first
                # [Postgres via db_manager]
                # Check balance first
                rows = await db_manager.fetchone("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
                balance = rows[0] if rows else 0
                if balance < price:
                    return False, f"Không đủ Hạt Giống! (Cần {price})"
                
                # Dedudct
                await db_manager.execute("UPDATE users SET seeds = seeds - ? WHERE user_id = ?", (price, user_id))

            # 2. Add Item to Decor Inventory [Postgres]
            user_obj = await UserAquarium.get_or_create(user_id=user_id)
            decor, _ = await UserDecor.get_or_create(user=user_obj[0], item_id=item_key)
            decor.quantity += 1
            await decor.save()
            
            return True, f"Đã mua **{item['name']}** với {price} {currency}!"

        except Exception as e:
            logger.error(f"[BUY_ERROR] User {user_id} Item {item_key}: {e}", exc_info=True)
            # Note: Potential distributed transaction inconsistency if step 2 fails after step 1.
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

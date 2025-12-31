import logging
from database_manager import db_manager, get_user_balance, add_seeds
from core.item_system import item_system
from configs.item_constants import ItemKeys
from cogs.fishing.mechanics.legendary_quest_helper import is_legendary_caught

logger = logging.getLogger("ShopLogic")

async def get_user_balance_local(user_id: int) -> int:
    return await get_user_balance(user_id)

async def check_buy_conditions(user_id: int, item_key: str, amount: int, cost: int) -> tuple[bool, str]:
    """Validates if purchase can proceed."""
    if amount <= 0:
        return False, "Số lượng không hợp lệ."
    
    # Balance Check
    balance = await get_user_balance_local(user_id)
    if balance < cost:
        return False, f"Bạn không đủ hạt! Cần {cost}, có {balance}."
        
    # Legendary Check
    if item_key == ItemKeys.MAY_DO_SONG:
        if await is_legendary_caught(user_id, "ca_voi_52hz"):
            return False, "📡 TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI (Bạn đã hoàn thành cốt truyện Cá Voi)."
            
    return True, ""

async def execute_purchase(user_id: int, item_key: str, amount: int, cost: int) -> bool:
    """Executes the purchase transaction safely."""
    try:
        async with db_manager.transaction() as conn:
            # 1. Double check balance
            row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
            current_seeds = row['seeds'] if row else 0
            
            if current_seeds < cost:
                return False

            # 2. Deduct Money
            await conn.execute(
                "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                (cost, user_id)
            )
            
            # 3. Add Item
            await conn.execute(
                """INSERT INTO inventory (user_id, item_id, quantity) 
                   VALUES ($1, $2, $3)
                   ON CONFLICT(user_id, item_id) 
                   DO UPDATE SET quantity = inventory.quantity + $3""",
                (user_id, item_key, amount)
            )
            
            # 4. Log
            await conn.execute(
                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                (user_id, -cost, f'buy_{item_key}', 'shop')
            )
            
        return True
    except Exception as e:
        logger.error(f"Purchase failed: {e}")
        return False

def get_buyable_items_map():
    """Returns mapping and all items."""
    mapping = {}
    all_items = item_system.get_all_items()
    for key, item_data in all_items.items():
        if item_data.get("flags", {}).get("buyable", False):
            mapping[item_data["name"]] = key
    return mapping, all_items

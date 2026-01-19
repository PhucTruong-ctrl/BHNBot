
from core.database import db_manager, get_user_balance
from core.item_system import item_system
from cogs.aquarium.logic.market import MarketEngine
from core.logging import get_logger
logger = get_logger("unified_shop_logic")

class ShopController:
    @staticmethod
    async def process_purchase(user_id: int, item_key: str, quantity: int = 1, currency: str = "seeds") -> tuple[bool, str]:
        """
        Unified purchase handler.
        Routes to specific engine if needed (e.g., Decor) or handles generic items.
        Returns: (success, message)
        """
        # 0. SPECIAL: ROD UPGRADE
        if item_key == "dynamic_rod_upgrade":
             # Rod upgrade is always seeds for now
             if currency != "seeds": return False, "Nâng cấp cần chỉ dùng Hạt."
             return await ShopController._process_rod_upgrade(user_id)

        item = item_system.get_item(item_key)
        if not item:
            return False, "Vật phẩm không tồn tại."
            
        item_type = item.get('type')
        
        # 1. DECOR ROUTING
        if item_type == 'decor':
            # MarketEngine currently handles SINGLE item purchase logic
            success_count = 0
            last_msg = ""
            for _ in range(quantity):
                ok, msg = await MarketEngine.buy_decor(user_id, item_key, currency) 
                if ok:
                    success_count += 1
                    logger.info(f"[SHOP] [DECOR] User {user_id} bought {item_key} ({currency})")
                else:
                    last_msg = msg
                    break
            
            if success_count == quantity:
                return True, f"Mua thành công {quantity}x **{item['name']}**!"
            elif success_count > 0:
                return True, f"Mua được {success_count}/{quantity} món. Lỗi món còn lại: {last_msg}"
            else:
                return False, last_msg

        # 2. GENERIC ITEM LOGIC (Consumables, Tools, etc.)
        if currency != "seeds":
            return False, "Vật phẩm này chỉ bán bằng Hạt."
        # Price Check
        price = item.get("price", {}).get("buy", 0)
        total_price = price * quantity
        
        if total_price <= 0:
            return False, "Vật phẩm này không bán."

        # Transaction
        try:
            async with db_manager.postgre_pool.acquire() as conn:
                async with conn.transaction():
                    # Check Balance
                    row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", user_id)
                    if not row or row['seeds'] < total_price:
                        return False, f"Không đủ hạt. Cần {total_price:,} Hạt."

                    # Deduct Money
                    await conn.execute(
                        "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                        total_price, user_id
                    )

                    # Add Item (Upsert)
                    # Use INSERT ... ON CONFLICT
                    await conn.execute("""
                        INSERT INTO inventory (user_id, item_id, quantity)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, item_id) 
                        DO UPDATE SET quantity = inventory.quantity + $3
                    """, user_id, item_key, quantity)
                    
            logger.info(f"[SHOP] [ITEM] User {user_id} bought {quantity}x {item_key} (-{total_price} seeds)")
            return True, f"Mua thành công {quantity}x **{item['name']}** (-{total_price} Hạt)"

        except Exception as e:
            logger.error(f"[SHOP] [ERROR] User {user_id}, Item {item_key}: {e}")
            return False, "Lỗi giao dịch hệ thống."

    @staticmethod
    async def _process_rod_upgrade(user_id: int) -> tuple[bool, str]:
        """Specific logic for upgrading rod via shop."""
        try:
            from cogs.fishing.mechanics.rod_system import get_rod_data, update_rod_data
            from configs.settings import ROD_LEVELS
            
            level, durability = await get_rod_data(user_id)
            next_lvl = level + 1
            
            if next_lvl not in ROD_LEVELS:
                return False, "Bạn đã đạt cấp cần câu tối đa!"
                
            next_data = ROD_LEVELS[next_lvl]
            cost = next_data.get("cost", 0)
            
            # Transaction
            async with db_manager.postgre_pool.acquire() as conn:
                 async with conn.transaction():
                    # Check Balance
                    row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", user_id)
                    if not row or row['seeds'] < cost:
                        return False, f"Không đủ hạt. Cần {cost:,} Hạt để nâng cấp."
                        
                    # Deduct
                    await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", cost, user_id)
                    
                    # Upgrade Rod
                    # We use update_rod_data logic but inside this transaction for safety?
                    # mechanics/rod_system uses db_manager.execute which is separate.
                    # Best to replicate SQL here for Atomicity.
                    await conn.execute(
                        "UPDATE fishing_profiles SET rod_level = $1, rod_durability = $2 WHERE user_id = $3",
                        next_lvl, next_data['durability'], user_id
                    )
            
            logger.info(f"[SHOP] [ROD] User {user_id} upgraded rod to Lv {next_lvl} (-{cost} seeds)")
            return True, f"🎉 Chúc mừng! Đã nâng cấp lên **{next_data['name']}**!"
            
        except Exception as e:
            logger.error(f"[SHOP] [ROD_ERROR] Upgrade failed for {user_id}: {e}")
            return False, "Lỗi hệ thống khi nâng cấp cần."

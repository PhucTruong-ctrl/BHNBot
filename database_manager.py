"""
Database Manager - Optimized database operations with caching and batch processing
Handles connection pooling, query caching, and batch operations for better performance
"""
import time
import asyncio
from typing import Optional, Dict, List, Any, Tuple
from core.database import db_manager, get_user_balance, get_user_full, add_seeds, get_leaderboard, get_db_connection
from configs.settings import DB_PATH
from core.logger import setup_logger

logger = setup_logger("DBManager", "core/database.log")


async def get_or_create_user(user_id: int, username: str) -> Optional[tuple]:
    """Retrieves a user by ID or creates a new one if they don't exist.

    This function does NOT use caching because it modifies the database directly for new users.

    Args:
        user_id (int): The Discord user ID.
        username (str): The username display string.

    Returns:
        Optional[tuple]: A tuple containing (user_id, username, seeds) or None if an error occurs.
    """
    try:
        user = await db_manager.fetchone(
            "SELECT user_id, username, seeds FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if not user:
            logger.info(f"Creating new user: {username} ({user_id})")
            await db_manager.modify(
                "INSERT INTO users (user_id, username, seeds) VALUES (?, ?, 0)",
                (user_id, username)
            )
            db_manager.clear_cache_by_prefix("leaderboard")
            user = (user_id, username, 0)
        
        return user
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        return None


async def batch_update_seeds(updates: Dict[int, int], reason: str, category: str):
    """Updates seed balances for multiple users in a single batch operation.

    Args:
        updates (Dict[int, int]): A dictionary mapping user_id to the amount of seeds to add (can be negative).
        reason (str): Reason for the transaction (e.g., 'xi_dach_win', 'baucua_payout')
        category (str): Category for the transaction (e.g., 'xidach', 'baucua', 'social')

    Example:
        >>> await batch_update_seeds({12345: 100, 67890: -50}, reason='xi_dach_win', category='xidach')
    """
    # Import datetime for transaction logging
    from datetime import datetime
    
    # Prepare balance updates
    balance_operations = [
        (
            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
            (amount, user_id)
        )
        for user_id, amount in updates.items()
    ]
    
    # Prepare transaction log entries
    transaction_operations = [
        (
            "INSERT INTO transaction_logs (user_id, amount, reason, category, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, reason, category, datetime.now())
        )
        for user_id, amount in updates.items()
    ]
    
    # Execute all operations in single batch
    all_operations = balance_operations + transaction_operations
    await db_manager.batch_modify(all_operations)
    
    # Clear caches
    db_manager.clear_cache_by_prefix("balance_")
    db_manager.clear_cache_by_prefix("leaderboard")


# ==================== TREE QUERIES ====================

async def get_tree_data(guild_id: int) -> Optional[tuple]:
    """Retrieves server tree data with caching.

    Args:
        guild_id (int): The Discord guild ID.

    Returns:
        Optional[tuple]: A tuple containing (current_level, current_progress, total_contributed, season, tree_channel_id, tree_message_id), or None if not found.
    """
    result = await db_manager.fetchone(
        "SELECT current_level, current_progress, total_contributed, season, tree_channel_id, tree_message_id FROM server_tree WHERE guild_id = ?",
        (guild_id,),
        use_cache=True,
        cache_key=f"tree_{guild_id}",
        cache_ttl=60  # Short TTL for dynamic data
    )
    return result


async def update_tree_progress(guild_id: int, level: int, progress: int, total: int):
    """Update tree and invalidate cache"""
    await db_manager.modify(
        "UPDATE server_tree SET current_level = ?, current_progress = ?, total_contributed = ? WHERE guild_id = ?",
        (level, progress, total, guild_id)
    )
    db_manager.clear_cache_by_prefix(f"tree_{guild_id}")


async def get_top_contributors(guild_id: int, limit: int = 3) -> List[tuple]:
    """Get top tree contributors with caching"""
    result = await db_manager.execute(
        "SELECT user_id, amount FROM tree_contributors WHERE guild_id = ? ORDER BY amount DESC LIMIT ?",
        (guild_id, limit),
        use_cache=True,
        cache_key=f"top_contributors_{guild_id}",
        cache_ttl=300
    )
    return result





# ==================== INVENTORY QUERIES ====================

async def get_inventory(user_id: int) -> Dict[str, int]:
    """Retrieves the user's inventory from the database.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        Dict[str, int]: A dictionary mapping item_id to quantity. Example: {'worm': 10, 'rod': 1}
    """
    result = await db_manager.execute(
        "SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0",
        (user_id,),
        use_cache=True,
        cache_key=f"inventory_{user_id}",
        cache_ttl=600
    )
    
    inventory = {}
    for item_id, quantity in result:
        inventory[item_id] = quantity
    return inventory


async def add_item(user_id: int, item_id: str, quantity: int = 1):
    """Adds an item to the user's inventory.

    Args:
        user_id (int): The Discord user ID.
        item_id (str): The unique identifier of the item.
        quantity (int): The amount to add. Defaults to 1.

    Returns:
        bool: True if the operation was successful.
    """
    # Check if item exists
    existing = await db_manager.fetchone(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
        (user_id, item_id)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?",
            (quantity, user_id, item_id)
        )
    else:
        await db_manager.modify(
            "INSERT INTO inventory (user_id, item_id, item_type, quantity) VALUES (?, ?, 'item', ?)",
            (user_id, item_id, quantity)
        )
    
    db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
    return True


async def remove_item(user_id: int, item_id: str, quantity: int = 1) -> bool:
    """Removes an item from the user's inventory.

    Args:
        user_id (int): The Discord user ID.
        item_id (str): The unique identifier of the item.
        quantity (int): The amount to remove. Defaults to 1.

    Returns:
        bool: True if the item was successfully removed (user had enough quantity), False otherwise.
    """
    existing = await db_manager.fetchone(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
        (user_id, item_id)
    )
    
    if not existing or existing[0] < quantity:
        return False
    
    new_quantity = existing[0] - quantity
    if new_quantity <= 0:
        await db_manager.modify(
            "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        )
    else:
        await db_manager.modify(
            "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?",
            (new_quantity, user_id, item_id)
        )
    
    db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
    return True


# ==================== SERVER CONFIG QUERIES ====================

async def get_server_config(guild_id: int, field: str) -> Optional[Any]:
    """Retrieves a specific configuration field for a server.

    Args:
        guild_id (int): The Discord guild ID.
        field (str): The column name in the server_config table to retrieve.

    Returns:
        Optional[Any]: The value of the config field, or None if not found.
    """
    result = await db_manager.fetchone(
        f"SELECT {field} FROM server_config WHERE guild_id = ?",
        (guild_id,),
        use_cache=True,
        cache_key=f"config_{guild_id}_{field}",
        cache_ttl=300
    )
    return result[0] if result else None


async def set_server_config(guild_id: int, field: str, value: Any):
    """Sets a specific configuration field for a server.

    Args:
        guild_id (int): The Discord guild ID.
        field (str): The column name in the server_config table to update.
        value (Any): The value to set.
    """
    await db_manager.modify(
        f"INSERT OR REPLACE INTO server_config (guild_id, {field}) VALUES (?, ?)",
        (guild_id, value)
    )
    db_manager.clear_cache_by_prefix(f"config_{guild_id}")


async def get_rod_data(user_id: int) -> tuple[int, int]:
    """Retrieves fishing rod data for a user.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        tuple[int, int]: A tuple containing (rod_level, rod_durability). Defaults to (1, 30) if not found.
    """
    result = await db_manager.fetchone(
        "SELECT rod_level, rod_durability FROM fishing_profiles WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"rod_{user_id}",
        cache_ttl=300
    )
    return result if result else (1, 30) # Default level 1, 30 durability


# ==================== NEW MODULAR SCHEMA QUERIES ====================
# Use these for new functionality targeting optimized schema
# Gradually migrate old queries to these new functions

# ----- CORE USER OPERATIONS (New Schema) -----

async def get_or_create_user_new(user_id: int, username: str) -> Optional[tuple]:
    """Retrieves or creates a user in the optimized 'users' table.

    Args:
        user_id (int): The Discord user ID.
        username (str): The username display string.

    Returns:
        Optional[tuple]: User data record or None.
    """
    user = await db_manager.fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"user_new_{user_id}",
        cache_ttl=300
    )
    
    if not user:
        await db_manager.modify(
            "INSERT OR IGNORE INTO users (user_id, username, seeds) VALUES (?, ?, 0)",
            (user_id, username)
        )
        db_manager.clear_cache_by_prefix(f"user_new_{user_id}")
    
    return user


async def get_user_seeds_new(user_id: int) -> int:
    """Get user seeds from new 'users' table"""
    result = await db_manager.fetchone(
        "SELECT seeds FROM users WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"seeds_{user_id}",
        cache_ttl=300
    )
    return result[0] if result else 0


async def add_seeds_new(user_id: int, amount: int):
    """Add seeds to user in new schema"""
    await db_manager.modify(
        "UPDATE users SET seeds = seeds + ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
        (amount, user_id)
    )
    db_manager.clear_cache_by_prefix(f"seeds_{user_id}")


async def get_leaderboard_new(limit: int = 10) -> List[tuple]:
    """Get top players by seeds (new schema)"""
    result = await db_manager.execute(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT ?",
        (limit,),
        use_cache=True,
        cache_key="leaderboard_top_new",
        cache_ttl=300
    )
    return result


# ----- USER STATS OPERATIONS (Generic Key-Value Stats) -----

async def increment_stat(user_id: int, game_id: str, stat_key: str, amount: int = 1):
    """Increments a generic user statistic for a specific game module.

    Args:
        user_id (int): The Discord user ID.
        game_id (str): The game identifier (e.g., 'fishing', 'werewolf').
        stat_key (str): The specific statistic key (e.g., 'fish_caught').
        amount (int): The amount to increment. Defaults to 1.
    """
    existing = await db_manager.fetchone(
        "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?",
        (user_id, game_id, stat_key)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE user_stats SET value = value + ? WHERE user_id = ? AND game_id = ? AND stat_key = ?",
            (amount, user_id, game_id, stat_key)
        )
    else:
        await db_manager.modify(
            "INSERT INTO user_stats (user_id, game_id, stat_key, value) VALUES (?, ?, ?, ?)",
            (user_id, game_id, stat_key, amount)
        )
    
    db_manager.clear_cache_by_prefix(f"stat_{user_id}_{game_id}_{stat_key}")


async def get_stat(user_id: int, game_id: str, stat_key: str, default: int = 0) -> int:
    """Retrieves a specific user statistic.

    Args:
        user_id (int): The Discord user ID.
        game_id (str): The game identifier.
        stat_key (str): The statistic key.
        default (int): Default value if not found. Defaults to 0.

    Returns:
        int: The statistic value.
    """
    result = await db_manager.fetchone(
        "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?",
        (user_id, game_id, stat_key),
        use_cache=True,
        cache_key=f"stat_{user_id}_{game_id}_{stat_key}",
        cache_ttl=600
    )
    return result[0] if result else default


async def get_all_stats(user_id: int, game_id: str = None) -> Dict[str, int]:
    """Retrieves all statistics for a user, optionally filtered by game.

    Args:
        user_id (int): The Discord user ID.
        game_id (str, optional): The game identifier filter. Defaults to None.

    Returns:
        Dict[str, int]: A dictionary mapping stat_key to value.
    """
    if game_id:
        result = await db_manager.execute(
            "SELECT stat_key, value FROM user_stats WHERE user_id = ? AND game_id = ?",
            (user_id, game_id),
            use_cache=True,
            cache_key=f"all_stats_{user_id}_{game_id}",
            cache_ttl=600
        )

# ==================== GLOBAL EVENT PERSISTENCE ====================

async def get_global_state(event_key: str, default: dict = None) -> dict:
    """Retrieve persistent state for a global event.
    
    Args:
        event_key: Unique key for the event (e.g., 'cthulhu_raid')
        default: Default dict if not found
        
    Returns:
        Dict containing state data (parsed from JSON)
    """
    import json
    if default is None: default = {}
    
    result = await db_manager.fetchone(
        "SELECT state_data FROM global_event_state WHERE event_key = ?",
        (event_key,)
    )
    
    if result:
        try:
            return json.loads(result[0])
        except Exception as e:
            logger.error(f"[DB] Failed to parse global state for {event_key}: {e}")
            return default
    return default

async def set_global_state(event_key: str, state_data: dict):
    """Save persistent state for a global event.
    
    Args:
        event_key: Unique key
        state_data: Dict to serialize and save
    """
    import json
    try:
        json_str = json.dumps(state_data)
        await db_manager.modify(
            "INSERT OR REPLACE INTO global_event_state (event_key, state_data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (event_key, json_str)
        )
    except Exception as e:
        logger.error(f"[DB] Failed to save global state for {event_key}: {e}")



async def get_stat_leaderboard(game_id: str, stat_key: str, limit: int = 10) -> List[tuple]:
    """Get top users for a specific stat in a game"""
    result = await db_manager.execute(
        """
        SELECT u.user_id, u.username, us.value 
        FROM users u
        JOIN user_stats us ON u.user_id = us.user_id
        WHERE us.game_id = ? AND us.stat_key = ?
        ORDER BY us.value DESC
        LIMIT ?
        """,
        (game_id, stat_key, limit),
        use_cache=True,
        cache_key=f"leaderboard_{game_id}_{stat_key}",
        cache_ttl=300
    )
    return result


# ----- FISHING PROFILE OPERATIONS -----

async def get_fishing_profile(user_id: int) -> Optional[tuple]:
    """Retrieves the fishing profile for a user.

    Unlike get_rod_data, this returns experience (exp) as well.
    Auto-creates a profile with default values if one does not exist.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        Optional[tuple]: A tuple containing (rod_level, rod_durability, exp).
    """
    result = await db_manager.fetchone(
        "SELECT rod_level, rod_durability, exp FROM fishing_profiles WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"fishing_{user_id}",
        cache_ttl=300
    )
    
    # If profile exists, return it
    if result:
        return result
    
    # For new users: auto-create fishing profile
    # (Instead of returning None and causing errors)
    created = await create_fishing_profile(user_id)
    
    if created:
        # Return default values for newly created profile
        return (1, 30, 0)  # rod_level=1, durability=30, exp=0
    else:
        # If creation failed, might mean profile already exists (race condition)
        # Try fetching again
        result = await db_manager.fetchone(
            "SELECT rod_level, rod_durability, exp FROM fishing_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result if result else (1, 30, 0)


async def update_fishing_profile(user_id: int, rod_level: int = None, rod_durability: int = None, exp: int = None):
    """Update fishing profile fields"""
    updates = []
    params = []
    
    if rod_level is not None:
        updates.append("rod_level = ?")
        params.append(rod_level)
    if rod_durability is not None:
        updates.append("rod_durability = ?")
        params.append(rod_durability)
    if exp is not None:
        updates.append("exp = ?")
        params.append(exp)
    
    if updates:
        params.append(user_id)
        query = f"UPDATE fishing_profiles SET {', '.join(updates)} WHERE user_id = ?"
        await db_manager.modify(query, tuple(params))
        db_manager.clear_cache_by_prefix(f"fishing_{user_id}")


# ----- FISH COLLECTION OPERATIONS -----

async def add_fish(user_id: int, fish_id: str, quantity: int = 1):
    """Adds a fish to the user's collection.

    Args:
        user_id (int): The Discord user ID.
        fish_id (str): The unique identifier of the fish.
        quantity (int): The number of fish to add. Defaults to 1.
    """
    existing = await db_manager.fetchone(
        "SELECT quantity FROM fish_collection WHERE user_id = ? AND fish_id = ?",
        (user_id, fish_id)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE fish_collection SET quantity = quantity + ? WHERE user_id = ? AND fish_id = ?",
            (quantity, user_id, fish_id)
        )
    else:
        await db_manager.modify(
            "INSERT INTO fish_collection (user_id, fish_id, quantity) VALUES (?, ?, ?)",
            (user_id, fish_id, quantity)
        )
    
    db_manager.clear_cache_by_prefix(f"collection_{user_id}")


async def get_fish_collection(user_id: int) -> Dict[str, int]:
    """Retrieves the user's fish collection.
    
    Args:
        user_id (int): The Discord user ID.

    Returns:
        Dict[str, int]: A dictionary mapping fish_id to quantity caught.
    """
    result = await db_manager.execute(
        "SELECT fish_id, quantity FROM fish_collection WHERE user_id = ? AND quantity > 0",
        (user_id,),
        use_cache=True,
        cache_key=f"collection_{user_id}",
        cache_ttl=600
    )
    return {row[0]: row[1] for row in result}


async def remove_fish(user_id: int, fish_id: str, quantity: int = 1) -> bool:
    """Removes a fish from the user's collection.

    Args:
        user_id (int): The Discord user ID.
        fish_id (str): The unique identifier of the fish.
        quantity (int): The amount to remove.

    Returns:
        bool: True if the operation was successful, False if the user has insufficient quantity.
    """
    existing = await db_manager.fetchone(
        "SELECT quantity FROM fish_collection WHERE user_id = ? AND fish_id = ?",
        (user_id, fish_id)
    )
    
    if not existing or existing[0] < quantity:
        return False
    
    new_quantity = existing[0] - quantity
    if new_quantity <= 0:
        await db_manager.modify(
            "DELETE FROM fish_collection WHERE user_id = ? AND fish_id = ?",
            (user_id, fish_id)
        )
    else:
        await db_manager.modify(
            "UPDATE fish_collection SET quantity = ? WHERE user_id = ? AND fish_id = ?",
            (new_quantity, user_id, fish_id)
        )
    
    db_manager.clear_cache_by_prefix(f"collection_{user_id}")
    return True


async def get_fish_count(user_id: int, fish_id: str) -> int:
    """Checks if a user has caught a specific fish.

    Args:
        user_id (int): The Discord user ID.
        fish_id (str): The fish identifier.

    Returns:
        int: 1 if the user has the fish, 0 otherwise.
    """
    result = await db_manager.fetchone(
        "SELECT 1 FROM fish_collection WHERE user_id = ? AND fish_id = ?",
        (user_id, fish_id),
        use_cache=True,
        cache_key=f"fish_{user_id}_{fish_id}",
        cache_ttl=600
    )
    return 1 if result else 0


# ----- OPTIMIZED INVENTORY OPERATIONS -----

# ==================== DEPRECATED: inventory_v2 functions (table doesn't exist) ====================
# These functions are deprecated - inventory_v2 table was never created
# Use regular inventory (item_id) and the standard add_item/remove_item functions instead

async def add_item_v2(user_id: int, item_id: str, quantity: int = 1, item_category: str = None):
    """DEPRECATED: Use add_item() instead"""
    return await add_item(user_id, item_id, quantity)

async def get_inventory_v2(user_id: int) -> Dict[str, int]:
    """DEPRECATED: Use get_inventory() instead"""
    return await get_inventory(user_id)

async def remove_item_v2(user_id: int, item_id: str, quantity: int = 1) -> bool:
    """DEPRECATED: Use remove_item() instead"""
    return await remove_item(user_id, item_id, quantity)

# ==================== CRITICAL TRANSACTION OPERATIONS ====================

async def buy_shop_item(user_id: int, item_id: str, cost: int, quantity: int = 1, item_category: str = "consumable") -> tuple[bool, str]:
    """Purchases an item in a transaction (Atomic Operation).

    Ensures both seed deduction and item addition happen together or both fail.

    Args:
        user_id (int): The Discord user ID.
        item_id (str): The item identifier.
        cost (int): The cost per unit (or total cost? Logic implies total cost deducted is `cost`? No, check logic. `UPDATE users SET seeds = seeds - ?` uses `cost`. So `cost` argument is TOTAL cost).
        quantity (int): Quantity to buy. Defaults to 1.
        item_category (str): Category (e.g., 'consumable'). Defaults to "consumable".

    Returns:
        tuple[bool, str]: Success status and message.
    """
    db = await get_db_connection(DB_PATH)
    try:
        await db.execute("BEGIN")
        
        # Step 1: Check user exists and has enough seeds
        cursor = await db.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if not row:
            await db.rollback()
            return False, "User không tồn tại!"
        
        if row[0] < cost:
            await db.rollback()
            return False, f"Không đủ tiền! Cần {cost}, hiện có {row[0]}"
        
        # Step 2: Deduct seeds
        await db.execute(
            "UPDATE users SET seeds = seeds - ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (cost, user_id)
        )
        
        # Step 3: Add item (Upsert - insert or update if exists)
        await db.execute("""
            INSERT INTO inventory (user_id, item_id, item_type, quantity)
            VALUES (?, ?, 'item', ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
        """, (user_id, item_id, quantity, quantity))
        
        # Commit transaction
        await db.commit()
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
        db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
        
        return True, "Mua thành công!"
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction error (buy_shop_item): {e}")
        return False, f"Lỗi hệ thống: {str(e)}"
    
    finally:
        await db.close()


async def use_consumable_item(user_id: int, item_id: str) -> tuple[bool, str]:
    """
    Use a consumable item (remove from inventory).
    Returns: (success: bool, message: str)
    """
    success = await remove_item_v2(user_id, item_id, quantity=1)
    
    if success:
        return True, f"Đã sử dụng {item_id}!"
    else:
        return False, "Bạn không có vật phẩm này hoặc số lượng không đủ!"


async def upgrade_fishing_rod(user_id: int, upgrade_cost: int) -> tuple[bool, str]:
    """Upgrades the user's fishing rod using a transaction.
    
    Deducts seeds, increases rod_level, and resets durability to max.

    Args:
        user_id (int): The Discord user ID.
        upgrade_cost (int): The cost of the upgrade.

    Returns:
        tuple[bool, str]: Success status and message.
    """
    db = await get_db_connection(DB_PATH)
    try:
        await db.execute("BEGIN")
        
        # Check balance
        cursor = await db.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if not row or row[0] < upgrade_cost:
            await db.rollback()
            return False, f"Không đủ tiền để nâng cấp! Cần {upgrade_cost}"
        
        # Deduct seeds
        await db.execute(
            "UPDATE users SET seeds = seeds - ? WHERE user_id = ?",
            (upgrade_cost, user_id)
        )
        
        # Upgrade rod (level +1, durability to 30)
        await db.execute("""
            UPDATE fishing_profiles 
            SET rod_level = rod_level + 1, rod_durability = 30
            WHERE user_id = ?
        """, (user_id,))
        
        await db.commit()
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
        db_manager.clear_cache_by_prefix(f"fishing_{user_id}")
        
        return True, "Nâng cấp cần câu thành công!"
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction error (upgrade_fishing_rod): {e}")
        return False, f"Lỗi nâng cấp: {str(e)}"
    
    finally:
        await db.close()


# ==================== FISHING PROFILE AUTO-CREATION ====================

async def create_fishing_profile(user_id: int) -> bool:
    """Creates a default fishing profile for a new user.

    Default values: rod_level=1, rod_durability=30, exp=0.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        bool: True if created successfully, False if already exists.
    """
    try:
        existing = await db_manager.fetchone(
            "SELECT user_id FROM fishing_profiles WHERE user_id = ?",
            (user_id,)
        )
        
        if existing:
            return False  # Already exists
        
        # Create default profile
        await db_manager.modify(
            "INSERT INTO fishing_profiles (user_id, rod_level, rod_durability, exp) VALUES (?, 1, 30, 0)",
            (user_id,)
        )
        
        db_manager.clear_cache_by_prefix(f"fishing_{user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating fishing profile: {e}")
        return False


async def get_or_create_fishing_profile(user_id: int) -> Optional[tuple]:
    """Retrieves or creates a fishing profile.

    Args:
        user_id (int): The Discord user ID.

    Returns:
        Optional[tuple]: A tuple containing (rod_level, rod_durability, exp).
    """
    # Try to get existing profile
    result = await db_manager.fetchone(
        "SELECT rod_level, rod_durability, exp FROM fishing_profiles WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"fishing_{user_id}",
        cache_ttl=300
    )
    
    if result:
        return result
    
    # Create if doesn't exist
    created = await create_fishing_profile(user_id)
    
    if created:
        return (1, 30, 0)  # Default values
    else:
        return None


async def repair_fishing_rod(user_id: int, repair_cost: int) -> tuple[bool, str]:
    """Repairs the user's fishing rod using a transaction.

    Deducts seeds and resets rod_durability to 30.

    Args:
        user_id (int): The Discord user ID.
        repair_cost (int): The cost to repair.

    Returns:
        tuple[bool, str]: Success status and message.
    """
    db = await get_db_connection(DB_PATH)
    try:
        await db.execute("BEGIN")
        
        # Check balance
        cursor = await db.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if not row or row[0] < repair_cost:
            await db.rollback()
            return False, f"Không đủ tiền để sửa cần! Cần {repair_cost}"
        
        # Deduct seeds
        await db.execute(
            "UPDATE users SET seeds = seeds - ? WHERE user_id = ?",
            (repair_cost, user_id)
        )
        
        # Repair rod
        await db.execute(
            "UPDATE fishing_profiles SET rod_durability = 30 WHERE user_id = ?",
            (user_id,)
        )
        
        # Track stat
        existing_stat = await db_manager.fetchone(
            "SELECT value FROM user_stats WHERE user_id = ? AND stat_key = ?",
            (user_id, "fishing_rods_repaired")
        )
        
        if existing_stat:
            await db.execute(
                "UPDATE user_stats SET value = value + 1 WHERE user_id = ? AND stat_key = ?",
                (user_id, "fishing_rods_repaired")
            )
        else:
            await db.execute(
                "INSERT INTO user_stats (user_id, stat_key, value) VALUES (?, ?, 1)",
                (user_id, "fishing_rods_repaired")
            )
        
        await db.commit()
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
        db_manager.clear_cache_by_prefix(f"fishing_{user_id}")
        
        return True, "Sửa cần câu thành công!"
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction error (repair_fishing_rod): {e}")
        return False, f"Lỗi sửa cần: {str(e)}"
    
    finally:
        await db.close()
async def sell_items_atomic(user_id: int, items: Dict[str, int], total_money: int) -> tuple[bool, str]:
    """Atomically sells multiple items.

    Verifies availability and quantity of all items before processing the transaction.

    Args:
        user_id (int): The Discord user ID.
        items (Dict[str, int]): A dictionary mapping item_ids to quantities to sell.
        total_money (int): Total seeds to add to user balance.

    Returns:
        tuple[bool, str]: Success status and message.
    """
    db = await get_db_connection(DB_PATH)
    try:
        await db.execute("BEGIN")
        
        # 1. Verify and deduct items
        for item_id, quantity in items.items():
            # Check if user has enough
            cursor = await db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] < quantity:
                await db.rollback()
                return False, f"Không đủ số lượng cho {item_id}! Cần {quantity}, có {row[0] if row else 0}"
            
            # Deduct item
            await db.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                (quantity, user_id, item_id)
            )
            
        # 2. Cleanup zero quantity items
        await db.execute("DELETE FROM inventory WHERE user_id = ? AND quantity <= 0", (user_id,))
        
        # 3. Add money
        await db.execute(
            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
            (total_money, user_id)
        )
        
        await db.commit()
        
        # Clear caches
        db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
        db_manager.clear_cache_by_prefix(f"balance_{user_id}")
        
        return True, "Giao dịch thành công!"
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction error (sell_items_atomic): {e}")
        return False, f"Lỗi giao dịch: {str(e)}"
    finally:
        await db.close()


# ==================== BUFF OPERATIONS ====================

async def save_user_buff(user_id: int, buff_type: str, duration_type: str, end_time: float = 0, remaining_count: int = 0):
    """Save or update a user buff."""
    await db_manager.modify(
        """INSERT OR REPLACE INTO user_buffs 
           (user_id, buff_type, duration_type, end_time, remaining_count) 
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, buff_type, duration_type, end_time, remaining_count)
    )
    db_manager.clear_cache_by_prefix(f"buffs_{user_id}")

async def get_user_buffs(user_id: int) -> Dict[str, dict]:
    """Get all active buffs for a user.
    
    Returns:
        Dict: {buff_type: {data}}
    """
    results = await db_manager.execute(
        "SELECT buff_type, duration_type, end_time, remaining_count FROM user_buffs WHERE user_id = ?",
        (user_id,),
        use_cache=True,
        cache_key=f"buffs_{user_id}",
        cache_ttl=60
    )
    
    buffs = {}
    current_time = time.time()
    
    for row in results:
        buff_type, duration_type, end_time, remaining_count = row
        
        # Filter expired time-based buffs
        if duration_type == 'time' and end_time < current_time:
            # Cleanup expired (using create_task to not block)
            asyncio.create_task(remove_user_buff(user_id, buff_type))
            continue
            
        buffs[buff_type] = {
            "type": buff_type,
            "duration_type": duration_type,
            "end_time": end_time,
            "remaining": remaining_count if duration_type == 'counter' else 0,
            "data": row # Raw data just in case
        }
    return buffs

async def remove_user_buff(user_id: int, buff_type: str):
    """Remove a specific buff."""
    await db_manager.modify(
        "DELETE FROM user_buffs WHERE user_id = ? AND buff_type = ?",
        (user_id, buff_type)
    )
    db_manager.clear_cache_by_prefix(f"buffs_{user_id}")


async def get_collection(user_id: int) -> Dict[str, int]:
    """Retrieves the user's fishing collection (stats).
    
    Args:
        user_id (int): The Discord user ID.

    Returns:
        Dict[str, int]: A dictionary of {stat_key: value}.
    """
    rows = await db_manager.execute(
        "SELECT stat_key, value FROM user_stats WHERE user_id = ? AND game_id = 'fishing'",
        (user_id,),
        use_cache=True,
        cache_key=f"collection_{user_id}",
        cache_ttl=60
    )
    
    if not rows:
        return {}
        
    return {row[0]: row[1] for row in rows}

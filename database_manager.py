"""
Database Manager - Optimized database operations with caching and batch processing
Handles connection pooling, query caching, and batch operations for better performance
"""
from typing import Optional, Dict, List, Any, Tuple
from core.database import db_manager, get_user_balance, get_user_full, add_seeds, get_leaderboard


async def get_or_create_user(user_id: int, username: str) -> Optional[tuple]:
    """Get or create user (no cache as it modifies)"""
    user = await db_manager.fetchone(
        "SELECT user_id, username, seeds FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    if not user:
        await db_manager.modify(
            "INSERT INTO users (user_id, username, seeds) VALUES (?, ?, 0)",
            (user_id, username)
        )
        db_manager.clear_cache_by_prefix("leaderboard")
    
    return user


async def batch_update_seeds(updates: Dict[int, int]):
    """Batch update multiple users' seeds at once"""
    operations = [
        (
            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
            (amount, user_id)
        )
        for user_id, amount in updates.items()
    ]
    
    await db_manager.batch_modify(operations)
    db_manager.clear_cache_by_prefix("balance_")
    db_manager.clear_cache_by_prefix("leaderboard")


# ==================== TREE QUERIES ====================

async def get_tree_data(guild_id: int) -> Optional[tuple]:
    """Get tree data with caching"""
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


# ==================== RELATIONSHIP QUERIES ====================

async def get_affinity(user_id_1: int, user_id_2: int) -> int:
    """Get affinity between users with caching"""
    if user_id_1 > user_id_2:
        user_id_1, user_id_2 = user_id_2, user_id_1
    
    result = await db_manager.fetchone(
        "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
        (user_id_1, user_id_2),
        use_cache=True,
        cache_key=f"affinity_{user_id_1}_{user_id_2}",
        cache_ttl=600
    )
    return result[0] if result else 0


async def add_affinity(user_id_1: int, user_id_2: int, amount: int):
    """Add affinity and invalidate cache"""
    if user_id_1 > user_id_2:
        user_id_1, user_id_2 = user_id_2, user_id_1
    
    # Check if relationship exists
    existing = await db_manager.fetchone(
        "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
        (user_id_1, user_id_2)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE relationships SET affinity = affinity + ?, last_interaction = CURRENT_TIMESTAMP WHERE user_id_1 = ? AND user_id_2 = ?",
            (amount, user_id_1, user_id_2)
        )
    else:
        await db_manager.modify(
            "INSERT INTO relationships (user_id_1, user_id_2, affinity) VALUES (?, ?, ?)",
            (user_id_1, user_id_2, amount)
        )
    
    db_manager.clear_cache_by_prefix(f"affinity_{min(user_id_1, user_id_2)}")


async def get_top_affinity_friends(user_id: int, limit: int = 3) -> List[tuple]:
    """Get top friends by affinity"""
    # Query as user_id_1
    results_1 = await db_manager.execute(
        "SELECT user_id_2, affinity FROM relationships WHERE user_id_1 = ? ORDER BY affinity DESC LIMIT ?",
        (user_id, limit)
    )
    
    # Query as user_id_2
    results_2 = await db_manager.execute(
        "SELECT user_id_1, affinity FROM relationships WHERE user_id_2 = ? ORDER BY affinity DESC LIMIT ?",
        (user_id, limit)
    )
    
    # Combine and sort
    combined = list(results_1) + list(results_2)
    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:limit]


# ==================== INVENTORY QUERIES ====================

async def get_inventory(user_id: int) -> Dict[str, int]:
    """Get user inventory with caching"""
    result = await db_manager.execute(
        "SELECT item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0",
        (user_id,),
        use_cache=True,
        cache_key=f"inventory_{user_id}",
        cache_ttl=600
    )
    
    inventory = {}
    for item_name, quantity in result:
        inventory[item_name] = quantity
    return inventory


async def add_item(user_id: int, item_id: str, quantity: int = 1):
    """Add item to inventory"""
    # Check if item exists
    existing = await db_manager.fetchone(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_id)
    )
    
    if existing:
        await db_manager.modify(
            "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?",
            (quantity, user_id, item_id)
        )
    else:
        await db_manager.modify(
            "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
            (user_id, item_id, quantity)
        )
    
    db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
    return True


async def remove_item(user_id: int, item_id: str, quantity: int = 1) -> bool:
    """Remove item from inventory"""
    existing = await db_manager.fetchone(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_id)
    )
    
    if not existing or existing[0] < quantity:
        return False
    
    new_quantity = existing[0] - quantity
    if new_quantity <= 0:
        await db_manager.modify(
            "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_id)
        )
    else:
        await db_manager.modify(
            "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?",
            (new_quantity, user_id, item_id)
        )
    
    db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
    return True


# ==================== SERVER CONFIG QUERIES ====================

async def get_server_config(guild_id: int, field: str) -> Optional[Any]:
    """Get server config field with caching"""
    result = await db_manager.fetchone(
        f"SELECT {field} FROM server_config WHERE guild_id = ?",
        (guild_id,),
        use_cache=True,
        cache_key=f"config_{guild_id}_{field}",
        cache_ttl=300
    )
    return result[0] if result else None


async def set_server_config(guild_id: int, field: str, value: Any):
    """Set server config field"""
    await db_manager.modify(
        f"INSERT OR REPLACE INTO server_config (guild_id, {field}) VALUES (?, ?)",
        (guild_id, value)
    )
    db_manager.clear_cache_by_prefix(f"config_{guild_id}")


async def get_rod_data(user_id: int) -> tuple[int, int]:
    """Get user's rod level and durability"""
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
    """Get or create user in new 'users' table"""
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
    """Increment a user stat for a specific game (create if not exists)"""
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
    """Get a specific user stat for a game"""
    result = await db_manager.fetchone(
        "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?",
        (user_id, game_id, stat_key),
        use_cache=True,
        cache_key=f"stat_{user_id}_{game_id}_{stat_key}",
        cache_ttl=600
    )
    return result[0] if result else default


async def get_all_stats(user_id: int, game_id: str = None) -> Dict[str, int]:
    """Get all stats for a user (optionally filtered by game_id). For achievements."""
    if game_id:
        result = await db_manager.execute(
            "SELECT stat_key, value FROM user_stats WHERE user_id = ? AND game_id = ?",
            (user_id, game_id),
            use_cache=True,
            cache_key=f"all_stats_{user_id}_{game_id}",
            cache_ttl=600
        )
    else:
        result = await db_manager.execute(
            "SELECT stat_key, value FROM user_stats WHERE user_id = ?",
            (user_id,),
            use_cache=True,
            cache_key=f"all_stats_{user_id}",
            cache_ttl=600
        )
    return {row[0]: row[1] for row in result}


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
    """
    Get fishing profile (rod_level, rod_durability, exp).
    Auto-creates profile if user is new (doesn't have fishing profile yet).
    
    Returns: (rod_level, rod_durability, exp) or None on error
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
    """Add fish to collection (or increment if exists)"""
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
    """Get user's fish collection"""
    result = await db_manager.execute(
        "SELECT fish_id, quantity FROM fish_collection WHERE user_id = ? AND quantity > 0",
        (user_id,),
        use_cache=True,
        cache_key=f"collection_{user_id}",
        cache_ttl=600
    )
    return {row[0]: row[1] for row in result}


async def remove_fish(user_id: int, fish_id: str, quantity: int = 1) -> bool:
    """Remove fish from collection"""
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
    """Get count of specific fish"""
    result = await db_manager.fetchone(
        "SELECT quantity FROM fish_collection WHERE user_id = ? AND fish_id = ?",
        (user_id, fish_id),
        use_cache=True,
        cache_key=f"fish_{user_id}_{fish_id}",
        cache_ttl=600
    )
    return result[0] if result else 0


# ----- OPTIMIZED INVENTORY OPERATIONS -----

# ==================== DEPRECATED: inventory_v2 functions (table doesn't exist) ====================
# These functions are deprecated - inventory_v2 table was never created
# Use regular inventory (item_name) and the standard add_item/remove_item functions instead

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
    """
    Purchase item with transaction (ATOMIC operation).
    Ensures both seed deduction AND item addition happen together or both fail.
    
    Returns: (success: bool, message: str)
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
            INSERT INTO inventory (user_id, item_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?
        """, (user_id, item_id, quantity, quantity))
        
        # Commit transaction
        await db.commit()
        db_manager.clear_cache_by_prefix(f"seeds_{user_id}")
        db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
        
        return True, "Mua thành công!"
        
    except Exception as e:
        await db.rollback()
        print(f"❌ Transaction error (buy_shop_item): {e}")
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
    """
    Upgrade fishing rod with transaction.
    - Deduct seeds
    - Increase rod_level
    - Reset durability to max
    
    Returns: (success: bool, message: str)
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
        print(f"❌ Transaction error (upgrade_fishing_rod): {e}")
        return False, f"Lỗi nâng cấp: {str(e)}"
    
    finally:
        await db.close()


# ==================== FISHING PROFILE AUTO-CREATION ====================

async def create_fishing_profile(user_id: int) -> bool:
    """
    Auto-create fishing profile for new user (if doesn't exist).
    Sets default: rod_level=1, rod_durability=30, exp=0
    
    Returns: True if created, False if already exists
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
        print(f"❌ Error creating fishing profile: {e}")
        return False


async def get_or_create_fishing_profile(user_id: int) -> Optional[tuple]:
    """
    Get fishing profile, auto-create if doesn't exist.
    Returns: (rod_level, rod_durability, exp) or None on error
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
    """
    Repair fishing rod with transaction.
    - Deduct seeds
    - Reset rod_durability to 30
    
    Returns: (success: bool, message: str)
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
        print(f"❌ Transaction error (repair_fishing_rod): {e}")
        return False, f"Lỗi sửa cần: {str(e)}"
    
    finally:
        await db.close()
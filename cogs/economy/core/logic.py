import logging
from datetime import datetime
from database_manager import (
    db_manager,
    get_user_balance,
    add_seeds,
    get_or_create_user,
    get_leaderboard,
    batch_update_seeds
)

logger = logging.getLogger("EconomyCore")

# ==================== DAO / LOGIC LAYER ====================

async def get_or_create_user_local(user_id: int, username: str):
    """Retrieves or creates a user. Ensuring strict integer type."""
    return await get_or_create_user(int(user_id), username)

async def is_harvest_buff_active(guild_id: int) -> bool:
    """Checks if the 24h harvest buff is active for the guild."""
    try:
        result = await db_manager.fetchrow(
            "SELECT harvest_buff_until FROM server_config WHERE guild_id = $1",
            (int(guild_id),),
            use_cache=True,
            cache_key=f"harvest_buff_{guild_id}",
            cache_ttl=60
        )
        
        if not result or not result['harvest_buff_until']:
            return False
        
        buff_until = result['harvest_buff_until']
        return datetime.now() < buff_until
    except Exception as e:
        logger.error(f"Error checking harvest buff: {e}")
        return False

async def add_seeds_local(user_id: int, amount: int, reason: str = 'generic_reward', category: str = 'system'):
    """Add seeds to user with logging."""
    user_id = int(user_id)
    amount = int(amount)
    
    balance_before = await get_user_balance(user_id)
    await add_seeds(user_id, amount, reason, category)
    
    logger.info(
        f"[SEED_UPDATE] user_id={user_id} seed_change={amount} "
        f"reason={reason}"
    )

async def get_user_balance_local(user_id: int) -> int:
    """Get user balance (seeds only)"""
    return await get_user_balance(int(user_id))

async def get_leaderboard_local(limit: int = 10) -> list:
    """Get top players by seeds"""
    return await get_leaderboard(int(limit))

async def update_last_daily(user_id: int):
    """Updates the timestamp of the last daily reward claim."""
    await db_manager.execute(
        "UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = $1",
        (int(user_id),)
    )
    db_manager.clear_cache_by_prefix(f"seeds_{user_id}")

async def update_last_chat_reward(user_id: int):
    """Update last chat reward time"""
    await db_manager.execute(
        "UPDATE users SET last_chat_reward = CURRENT_TIMESTAMP WHERE user_id = $1",
        (int(user_id),)
    )
    db_manager.clear_cache_by_prefix(f"seeds_{user_id}")

async def get_last_daily(user_id: int) -> datetime:
    """Get last daily reward time"""
    result = await db_manager.fetchrow(
        "SELECT last_daily FROM users WHERE user_id = $1",
        (int(user_id),)
    )
    if result and result['last_daily']:
        return result['last_daily']
    return None

async def get_excluded_channels(guild_id: int) -> list:
    """Get list of channels excluded from rewards."""
    try:
        rows = await db_manager.fetchall(
            "SELECT channel_id FROM excluded_channels WHERE guild_id = $1",
            (int(guild_id),),
            use_cache=True,
            cache_key=f"excluded_channels_{guild_id}",
            cache_ttl=300
        )
        return [row['channel_id'] for row in rows]
    except Exception as e:
        logger.error(f"Error getting excluded channels: {e}")
        return []

import asyncio
import os
import sys
import time
import logging

# Add project root to path
sys.path.append(os.getcwd())

from database_manager import db_manager, save_user_buff, get_user_buffs, remove_user_buff, get_or_create_user
from cogs.fishing.mechanics.buffs import EmotionalStateManager

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BuffTest")

TEST_USER_ID = 999999

async def test_persistence():
    logger.info("=== STARTING PERSISTENCE TEST ===")
    
    # 0. Create user to satisfy FK
    await get_or_create_user(TEST_USER_ID, "TestUserVal")
    
    # 1. Clean previous test data
    logger.info("Cleaning previous data...")
    await db_manager.execute("DELETE FROM user_buffs WHERE user_id = ?", (TEST_USER_ID,))
    
    # 2. Apply Buffs via Manager
    manager = EmotionalStateManager()
    
    logger.info("Applying Lucky Buff (Type: Counter, Duration: 1)...")
    await manager.apply_emotional_state(TEST_USER_ID, "lucky_buff", 1)
    
    logger.info("Applying Keo Ly Buff (Type: Time, Duration: 5s)...")
    await manager.apply_emotional_state(TEST_USER_ID, "keo_ly", 5)
    
    # 3. Verify DB Content directly
    rows = await db_manager.execute("SELECT buff_type, duration_type, remaining_count FROM user_buffs WHERE user_id = ?", (TEST_USER_ID,))
    logger.info(f"DB Rows: {rows}")
    
    found_types = [r[0] for r in rows]
    if "lucky_buff" in found_types and "keo_ly" in found_types:
        logger.info("✅ Buffs found in database!")
    else:
        logger.error(f"❌ Buffs missing! Found: {found_types}")
        return

    # 4. Simulate Restart (New Manager / Clear Cache in DB Manager)
    # Note: db_manager cache is internal. We can't easily clear it from here unless we access private attr or method.
    # But get_user_buffs has weak cache.
    # Let's create a NEW manager instance.
    manager2 = EmotionalStateManager()
    
    # 5. Check State using New Manager
    logger.info("Checking state with new Manager instance...")
    is_lucky = await manager2.check_emotional_state(TEST_USER_ID, "lucky_buff")
    is_keo_ly = await manager2.check_emotional_state(TEST_USER_ID, "keo_ly")
    
    if is_lucky:
        logger.info("✅ Lucky Buff persisted and active.")
    else:
        logger.error("❌ Lucky Buff lost!")
        
    if is_keo_ly:
        logger.info("✅ Keo Ly Buff persisted and active.")
    else:
        logger.error("❌ Keo Ly Buff lost!")
        
    # 6. Test Consumption (Counter)
    logger.info("Decremeting Lucky Buff...")
    remaining = await manager2.decrement_counter(TEST_USER_ID, "lucky_buff")
    logger.info(f"Remaining: {remaining}")
    
    is_lucky_now = await manager2.check_emotional_state(TEST_USER_ID, "lucky_buff")
    if not is_lucky_now:
        logger.info("✅ Lucky Buff consumed and removed (Correct).")
    else:
        logger.error("❌ Lucky Buff still active after consumption!")

    # 7. Test Expiry (Time)
    logger.info("Waiting 6 seconds for Keo Ly to expire...")
    await asyncio.sleep(6)
    
    is_keo_ly_now = await manager2.check_emotional_state(TEST_USER_ID, "keo_ly")
    if not is_keo_ly_now:
        logger.info("✅ Keo Ly Buff expired (Correct).")
    else:
        logger.error("❌ Keo Ly Buff still active after timeout!")

    # Cleanup
    await db_manager.execute("DELETE FROM user_buffs WHERE user_id = ?", (TEST_USER_ID,))
    logger.info("=== TEST COMPLETED ===")

async def main():
    try:
        await db_manager.connect()
        # Create table if not exists (in case setup_data didn't run or we want to be sure)
        await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS user_buffs (
            user_id INTEGER,
            buff_type TEXT,
            duration_type TEXT,
            end_time REAL,
            remaining_count INTEGER,
            data TEXT,
            PRIMARY KEY (user_id, buff_type)
        )
        """)
        await test_persistence()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())

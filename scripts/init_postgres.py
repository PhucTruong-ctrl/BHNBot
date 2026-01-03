import sys
import os
import asyncio
from dotenv import load_dotenv
import logging

# Add root dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env before imports
load_dotenv()

from core.database import db_manager
from core.logger import setup_logger

setup_logger("InitPG", "logs/init_pg.log")
logger = logging.getLogger("InitPG")

async def init_postgres():
    print("Initializing PostgreSQL Database...")
    try:
        await db_manager.connect()
        
        # 1. USERS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                seeds BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily TIMESTAMP,
                last_chat_reward TIMESTAMP
            )
        """)

        # 2. USER STATS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id BIGINT,
                game_id TEXT,
                stat_key TEXT,
                value BIGINT DEFAULT 0,
                PRIMARY KEY (user_id, game_id, stat_key)
            )
        """)

        # 3. USER ACHIEVEMENTS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id BIGINT,
                achievement_key TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, achievement_key)
            )
        """)

        # 4. INVENTORY
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id BIGINT,
                item_id TEXT,
                quantity INTEGER DEFAULT 1,
                item_type TEXT,
                PRIMARY KEY (user_id, item_id)
            )
        """)

        # 5. FISHING PROFILES
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS fishing_profiles (
                user_id BIGINT PRIMARY KEY,
                rod_level INTEGER DEFAULT 1,
                rod_durability INTEGER DEFAULT 30
            )
        """)

        # 6. LEGENDARY QUESTS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS legendary_quests (
                user_id BIGINT,
                fish_key TEXT,
                quest_status INTEGER DEFAULT 0,
                quest_completed BOOLEAN DEFAULT FALSE,
                legendary_caught BOOLEAN DEFAULT FALSE,
                last_progress_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, fish_key)
            )
        """)

        # 7. FISH COLLECTION
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS fish_collection (
                user_id BIGINT,
                fish_id TEXT,
                quantity INTEGER DEFAULT 0,
                biggest_size REAL DEFAULT 0,
                PRIMARY KEY (user_id, fish_id)
            )
        """)

        # 8. RELATIONSHIPS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                user_id_1 BIGINT,
                user_id_2 BIGINT,
                affinity INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id_1, user_id_2)
            )
        """)

        # 9. SHARED PETS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS shared_pets (
                id SERIAL PRIMARY KEY,
                user_id_1 BIGINT,
                user_id_2 BIGINT,
                name TEXT DEFAULT 'Mèo Béo',
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                last_fed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id_1, user_id_2)
            )
        """)

        # 10. SERVER CONFIG
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id BIGINT PRIMARY KEY,
                logs_channel_id BIGINT,
                noitu_channel_id BIGINT,
                fishing_channel_id BIGINT,
                giveaway_channel_id BIGINT,
                exclude_chat_channels TEXT,
                harvest_buff_until TIMESTAMP,
                bump_channel_id BIGINT,
                bump_start_time TEXT,
                last_reminder_sent TEXT,
                category_roles TEXT DEFAULT '[]',
                log_discord_channel_id BIGINT,
                log_ping_user_id BIGINT,
                log_discord_level TEXT DEFAULT 'WARNING'
            )
        """)

        # 11. SERVER TREE
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS server_tree (
                guild_id BIGINT PRIMARY KEY,
                current_level INTEGER DEFAULT 1,
                current_progress INTEGER DEFAULT 0,
                total_contributed BIGINT DEFAULT 0,
                season INTEGER DEFAULT 1,
                tree_channel_id BIGINT,
                tree_message_id BIGINT,
                last_harvest TIMESTAMP
            )
        """)

        # 12. TREE CONTRIBUTORS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS tree_contributors (
                user_id BIGINT,
                guild_id BIGINT,
                amount BIGINT DEFAULT 0,
                contribution_exp INTEGER DEFAULT 0,
                season INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id, season)
            )
        """)

        # 13. GIVEAWAYS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id BIGINT PRIMARY KEY,
                channel_id BIGINT,
                guild_id BIGINT,
                host_id BIGINT,
                prize TEXT,
                winners_count INTEGER,
                end_time TIMESTAMP,
                requirements TEXT, 
                status TEXT DEFAULT 'active',
                image_url TEXT
            )
        """)

        # 14. GIVEAWAY PARTICIPANTS
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_participants (
                id SERIAL PRIMARY KEY,
                giveaway_id BIGINT,
                user_id BIGINT,
                entries INTEGER DEFAULT 1,
                UNIQUE(giveaway_id, user_id)
            )
        """)

        # 15. USER INVITES
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS user_invites (
                inviter_id BIGINT,
                joined_user_id BIGINT,
                is_valid BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (inviter_id, joined_user_id)
            )
        """)
        
        # 16. GLOBAL EVENT STATE
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS global_event_state (
                event_key TEXT PRIMARY KEY,
                state_data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 17. SESSION & BUFFS
        # Handling potential NULL PK issues by using SERIAL ID or careful schema
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                session_id SERIAL PRIMARY KEY, -- Surrogate key to allow NULL voice_channel
                guild_id BIGINT,
                game_type TEXT,
                voice_channel_id BIGINT, 
                channel_id BIGINT,
                game_state TEXT,
                last_saved TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS user_buffs (
                user_id BIGINT,
                buff_type TEXT,
                duration_type TEXT,
                end_time REAL DEFAULT 0,
                remaining_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, buff_type)
            )
        """)
        
        # 19. RECREATE TRANSACTION LOGS
        # Dropping to ensure currency column exists
        await db_manager.execute("DROP TABLE IF EXISTS transaction_logs")
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS transaction_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount BIGINT NOT NULL,
                currency TEXT DEFAULT 'seeds',
                reason TEXT NOT NULL,
                category TEXT DEFAULT 'uncategorized',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("✓ All tables created successfully.")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(init_postgres())

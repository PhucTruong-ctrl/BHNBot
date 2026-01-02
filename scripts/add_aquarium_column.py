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

setup_logger("MigrateConfig", "logs/migration.log")
logger = logging.getLogger("MigrateConfig")

async def migrate():
    print("Migrating Database Schema...")
    try:
        await db_manager.connect()
        
        # Add aquarium_forum_channel_id column
        try:
            await db_manager.execute("""
                ALTER TABLE server_config 
                ADD COLUMN aquarium_forum_channel_id BIGINT
            """)
            print("✓ Added aquarium_forum_channel_id to server_config")
        except Exception as e:
            if "already exists" in str(e):
                print("⚠ Column aquarium_forum_channel_id already exists")
            else:
                print(f"ERROR adding column: {e}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(migrate())

import asyncio
import os
import sys

# Add root to sys.path
sys.path.append(os.getcwd())

from database_manager import db_manager, DB_PATH
from core.logger import setup_logger

async def check_db():
    print(f"Checking DB at: {DB_PATH}")
    await db_manager.connect()
    
    # Check server_config
    rows = await db_manager.execute("SELECT * FROM server_config")
    print(f"Rows in server_config: {len(rows)}")
    for row in rows:
        print(f"Row: {row}")
        
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_db())

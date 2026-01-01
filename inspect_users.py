
import asyncio
import os
import sys

# Ensure current directory is in python path
sys.path.append(os.getcwd())

from core.database import db_manager

async def list_users():
    print("Listing top 20 users...")
    users = await db_manager.fetchall("SELECT user_id, username, seeds FROM users LIMIT 50")
    for u in users:
        print(f"ID: {u[0]} | Name: {u[1]} | Seeds: {u[2]}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_users())

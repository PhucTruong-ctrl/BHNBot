#!/usr/bin/env python3
"""
Migration Script: Move leaf_coin from inventory table to user_aquarium.leaf_coin

This fixes the bug where leaf_coin was incorrectly stored as an inventory item
instead of being added to the user's aquarium currency balance.

Run: python scripts/migrate_leaf_coin_inventory.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_manager


async def migrate_leaf_coin_inventory():
    await db_manager.connect()
    
    try:
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id, quantity FROM inventory WHERE item_id = 'leaf_coin' AND quantity > 0"
            )
            
            if not rows:
                print("No leaf_coin entries found in inventory. Nothing to migrate.")
                return
            
            print(f"Found {len(rows)} users with leaf_coin in inventory")
            
            migrated = 0
            for row in rows:
                user_id = row['user_id']
                quantity = row['quantity']
                
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO user_aquarium (user_id, leaf_coin)
                        VALUES ($1, $2)
                        ON CONFLICT (user_id)
                        DO UPDATE SET leaf_coin = user_aquarium.leaf_coin + $2
                        """,
                        user_id, quantity
                    )
                    
                    await conn.execute(
                        "DELETE FROM inventory WHERE user_id = $1 AND item_id = 'leaf_coin'",
                        user_id
                    )
                
                migrated += 1
                print(f"  Migrated user {user_id}: {quantity} leaf_coin")
            
            print(f"\nMigration complete: {migrated}/{len(rows)} users migrated successfully")
            
    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate_leaf_coin_inventory())


import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from core.logger import setup_logger
from database_manager import db_manager
from cogs.tree.models import TreeData

logger = setup_logger("TreeRepair", "logs/repair_tree.log")

async def repair_tree_progress():
    print("Starting Tree Progress Repair...")
    try:
        # Get all guilds with tree data
        rows = await db_manager.execute("SELECT guild_id FROM server_tree")
        guilds = [row[0] for row in rows]
        
        for guild_id in guilds:
            print(f"Checking guild {guild_id}...")
            
            # Load current tree state
            # Force refresh to bypass cache
            if hasattr(TreeData, 'load'):
                tree_data = await TreeData.load(guild_id, force_refresh=True)
            else:
                # Fallback if load signature changed (it hasn't)
                tree_data = await TreeData.load(guild_id)
            
            current_season = tree_data.season
            
            # Get actual total contributions for this season
            contrib_row = await db_manager.fetchone(
                "SELECT SUM(amount) FROM tree_contributors WHERE guild_id = ? AND season = ?",
                (guild_id, current_season)
            )
            
            actual_total = contrib_row[0] if contrib_row and contrib_row[0] else 0
            
            print(f"  > Season: {current_season}")
            print(f"  > DB total_contributed: {tree_data.total_contributed}")
            print(f"  > Actual contributions sum: {actual_total}")
            print(f"  > DB Level: {tree_data.current_level} Progress: {tree_data.current_progress}")
            
            if actual_total != tree_data.total_contributed:
                print("  ! Mismatch found. Recalculating state...")
                
                # Recalculate level and progress
                # We need to simulate growth from 0 with the actual_total seeds
                
                level_reqs = tree_data.get_level_requirements()
                
                new_level = 1
                remaining_seeds = actual_total
                
                # Logic copied/adapted from TreeManager.process_contribution
                # Max level is 6
                while new_level < 6:
                    req = level_reqs.get(new_level + 1, level_reqs[6])
                    if remaining_seeds >= req:
                        remaining_seeds -= req
                        new_level += 1
                        # Update req for next iteration loop logic check (though loop condition handles it)
                    else:
                        break
                
                new_progress = remaining_seeds
                
                print(f"  -> New State: Level {new_level}, Progress {new_progress}, Total {actual_total}")
                
                # Update DB
                await db_manager.modify(
                    """UPDATE server_tree 
                    SET current_level = ?, current_progress = ?, total_contributed = ?
                    WHERE guild_id = ?""",
                    (new_level, new_progress, actual_total, guild_id)
                )
                print("  ✓ Database updated.")
            else:
                 # Even if total matches, check if level/progress math is consistent?
                 # Assume consistent if total matches for now, or minimal drift.
                 # Actually, logic above handles re-calculation perfectly.
                 pass

    except Exception as e:
        print(f"Error during repair: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(repair_tree_progress())

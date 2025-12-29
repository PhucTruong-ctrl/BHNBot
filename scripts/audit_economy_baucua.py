
import asyncio
import sqlite3
import random
import os
import sys

# Simulation Constants
SIMULATIONS = 100_000
BET_AMOUNT = 100

def simulate_baucua_ev():
    """Simulate Bầu Cua games to verify Expected Value."""
    print(f"\n--- SIMULATING BẦU CUA ({SIMULATIONS} games) ---")
    
    total_bet = 0
    total_payout = 0
    
    # 0 matches: Lose bet (-100)
    # 1 match: Payout 200 (+100)
    # 2 matches: Payout 300 (+200)
    # 3 matches: Payout 400 (+300)
    
    wins = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for _ in range(SIMULATIONS):
        # Bet on "Deer" (0)
        bet_choice = 0 
        total_bet += BET_AMOUNT
        
        # Roll 3 dice (0-5)
        dice = [random.randint(0, 5) for _ in range(3)]
        matches = dice.count(bet_choice)
        wins[matches] += 1
        
        if matches > 0:
            payout = BET_AMOUNT * (matches + 1)
            total_payout += payout
            
    net = total_payout - total_bet
    house_edge = (-net / total_bet) * 100
    
    print(f"Total Wet: {total_bet:,}")
    print(f"Total Payout: {total_payout:,}")
    print(f"Net Player Profit: {net:,}")
    print(f"House Edge: {house_edge:.2f}% (Expected ~7.87%)")
    print(f"Match Distribution: {wins}")
    return house_edge

async def audit_trash():
    """Audit trash items in inventory."""
    print("\n--- AUDITING TRASH INVENTORY ---")
    db_path = "data.db"
    
    if not os.path.exists(db_path):
        # Fallback to bhnbot.db if data.db missing
        db_path = "bhnbot.db"
    
    if not os.path.exists(db_path):
        print("Error: No database file found!")
        return

    print(f"Connecting into {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all trash items
    # Assuming trash items have 'trash' in key or we check a known list.
    # Since I don't have the full ItemKeys list loaded, I'll filter by item_id containing 'trash' 
    # OR item_type='trash' if that column exists.
    
    try:
        # Check columns
        cursor.execute("PRAGMA table_info(inventory)")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Inventory Columns: {cols}")
        
        if 'item_type' in cols:
            query = "SELECT user_id, item_id, amount FROM inventory WHERE item_type = 'trash'"
        else:
            query = "SELECT user_id, item_id, amount FROM inventory WHERE item_id LIKE '%trash%'"
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        total_trash = 0
        user_trash = {}
        unique_trash_types = set()
        
        for uid, item, amount in rows:
            total_trash += amount
            unique_trash_types.add(item)
            user_trash[uid] = user_trash.get(uid, 0) + amount
            
        print(f"Total Trash Items: {total_trash:,}")
        print(f"Unique Users holding Trash: {len(user_trash)}")
        
        if user_trash:
            avg_trash = total_trash / len(user_trash)
            max_trash = max(user_trash.values())
            min_trash = min(user_trash.values())
            print(f"Average Trash/User: {avg_trash:.2f}")
            print(f"Max Trash held by one user: {max_trash}")
        else:
            print("No trash found.")
            
        # Also check Top Rich to see connection
        # cursor.execute("SELECT user_id, amount FROM balance ORDER BY amount DESC LIMIT 5")
        # rich = cursor.fetchall()
        # print("\nTop 5 Rich Users:")
        # for r in rich:
        #     print(f"User {r[0]}: {r[1]:,} Seeds")
            
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    simulate_baucua_ev()
    asyncio.run(audit_trash())

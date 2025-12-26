
import sqlite3
import os

DB_PATH = "data/database.db"
USER_ID = 598046112959430657

def check_affinity():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"🔍 Checking affinity for user {USER_ID}...")
        
        # Query user_stats table
        # user_id, game_id, stat_key, value
        cursor.execute("SELECT stat_key, value FROM user_stats WHERE user_id = ? AND game_id = 'npc_affinity'", (USER_ID,))
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ No affinity stats found for this user.")
        else:
            print(f"✅ Found {len(rows)} affinity records:")
            print("-" * 40)
            print(f"{'NPC Key':<25} | {'Affinity':<10}")
            print("-" * 40)
            for key, value in rows:
                print(f"{key:<25} | {value:<10}")
            print("-" * 40)
            
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_affinity()

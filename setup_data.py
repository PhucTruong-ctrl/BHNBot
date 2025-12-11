import os
import sqlite3

# Configuration
DATA_DIR = "./data"
DB_PATH = os.path.join(DATA_DIR, "database.db")

def setup_folder():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory {DATA_DIR}")

def init_database():
    print("Initializing SQLite Database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Server Config: Store admin/game channels per server
    c.execute('''CREATE TABLE IF NOT EXISTS server_config (
                    guild_id INTEGER PRIMARY KEY,
                    admin_channel_id INTEGER,
                    noitu_channel_id INTEGER
                )''')
    
    conn.commit()
    conn.close()
    print("Done! Database initialized (server_config table ready).")

if __name__ == "__main__":
    setup_folder()
    init_database()
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
    """Initialize SQLite database with server_config and player_stats tables."""
    print("Initializing SQLite Database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Server Config: Store admin/game channels per server
    c.execute('''CREATE TABLE IF NOT EXISTS server_config (
                    guild_id INTEGER PRIMARY KEY,
                    admin_channel_id INTEGER,
                    noitu_channel_id INTEGER,
                    werewolf_voice_channel_id INTEGER
                )''')
    
    # Player Stats: Track wins and correct words per user
    c.execute('''CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    wins INTEGER DEFAULT 0,
                    correct_words INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Migration: Add werewolf_voice_channel_id column if it doesn't exist
    try:
        c.execute("ALTER TABLE server_config ADD COLUMN werewolf_voice_channel_id INTEGER")
        print("✓ Added werewolf_voice_channel_id column to server_config")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ werewolf_voice_channel_id column already exists")
        else:
            raise
    
    conn.commit()
    conn.close()
    print("Done! Database initialized (server_config and player_stats tables ready).")

if __name__ == "__main__":
    setup_folder()
    init_database()
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

    # Server Config: Store logs/game channels per server
    c.execute('''CREATE TABLE IF NOT EXISTS server_config (
                    guild_id INTEGER PRIMARY KEY,
                    logs_channel_id INTEGER,
                    noitu_channel_id INTEGER,
                    wolf_channel_id INTEGER,
                    giveaway_channel_id INTEGER
                )''')
    
    # Player Stats: Track wins and correct words per user
    c.execute('''CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    wins INTEGER DEFAULT 0,
                    correct_words INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Migration: Rename admin_channel_id to logs_channel_id (if table exists with old schema)
    try:
        c.execute("PRAGMA table_info(server_config)")
        columns = [row[1] for row in c.fetchall()]
        
        if "admin_channel_id" in columns and "logs_channel_id" not in columns:
            print("🔄 Migrating: admin_channel_id → logs_channel_id")
            # SQLite doesn't support direct column rename, so we need to recreate table
            c.execute('''
                CREATE TABLE server_config_new (
                    guild_id INTEGER PRIMARY KEY,
                    logs_channel_id INTEGER,
                    noitu_channel_id INTEGER,
                    wolf_channel_id INTEGER,
                    giveaway_channel_id INTEGER
                )
            ''')
            c.execute('''
                INSERT INTO server_config_new (guild_id, logs_channel_id, noitu_channel_id, wolf_channel_id, giveaway_channel_id)
                SELECT guild_id, admin_channel_id, noitu_channel_id, werewolf_voice_channel_id, NULL FROM server_config
            ''')
            c.execute('DROP TABLE server_config')
            c.execute('ALTER TABLE server_config_new RENAME TO server_config')
            print("✓ Migration completed: admin_channel_id → logs_channel_id")
        
        # Add missing columns if needed
        if "giveaway_channel_id" not in columns:
            try:
                c.execute("ALTER TABLE server_config ADD COLUMN giveaway_channel_id INTEGER")
                print("✓ Added giveaway_channel_id column")
            except sqlite3.OperationalError:
                print("ℹ️ giveaway_channel_id column already exists")
        
        if "wolf_channel_id" not in columns:
            try:
                c.execute("ALTER TABLE server_config ADD COLUMN wolf_channel_id INTEGER")
                print("✓ Added wolf_channel_id column")
            except sqlite3.OperationalError:
                print("ℹ️ wolf_channel_id column already exists")
        
        if "logs_channel_id" not in columns:
            try:
                c.execute("ALTER TABLE server_config ADD COLUMN logs_channel_id INTEGER")
                print("✓ Added logs_channel_id column")
            except sqlite3.OperationalError:
                print("ℹ️ logs_channel_id column already exists")
    
    except Exception as e:
        print(f"⚠️ Migration check error: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Done! Database initialized (server_config and player_stats tables ready).")

if __name__ == "__main__":
    setup_folder()
    init_database()
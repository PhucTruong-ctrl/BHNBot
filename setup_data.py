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
                    giveaway_channel_id INTEGER,
                    exclude_chat_channels TEXT,
                    harvest_buff_until DATETIME
                )''')
    
    # Player Stats: Track wins and correct words per user
    c.execute('''CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    wins INTEGER DEFAULT 0,
                    correct_words INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Economy: Track seeds, XP, and level per user
    c.execute('''CREATE TABLE IF NOT EXISTS economy_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    seeds INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_daily DATETIME,
                    last_chat_reward DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Relationships: Track affinity between users
    c.execute('''CREATE TABLE IF NOT EXISTS relationships (
                    user_id_1 INTEGER,
                    user_id_2 INTEGER,
                    affinity INTEGER DEFAULT 0,
                    last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id_1, user_id_2)
                )''')
    
    # Inventory: Track items owned by users
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_name TEXT,
                    quantity INTEGER DEFAULT 1,
                    obtained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_name)
                )''')
    
    # Server Tree: Community-wide tree that grows with contributions
    c.execute('''CREATE TABLE IF NOT EXISTS server_tree (
                    guild_id INTEGER PRIMARY KEY,
                    current_level INTEGER DEFAULT 1,
                    current_progress INTEGER DEFAULT 0,
                    total_contributed INTEGER DEFAULT 0,
                    season INTEGER DEFAULT 1,
                    tree_channel_id INTEGER,
                    tree_message_id INTEGER,
                    last_harvest DATETIME
                )''')
    
    # Tree Contributors: Track who contributed to the tree
    c.execute('''CREATE TABLE IF NOT EXISTS tree_contributors (
                    user_id INTEGER,
                    guild_id INTEGER,
                    amount INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
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
        
        if "harvest_buff_until" not in columns:
            try:
                c.execute("ALTER TABLE server_config ADD COLUMN harvest_buff_until DATETIME")
                print("✓ Added harvest_buff_until column")
            except sqlite3.OperationalError:
                print("ℹ️ harvest_buff_until column already exists")
    
    except Exception as e:
        print(f"⚠️ Migration check error: {e}")
    
    # Check and migrate relationships table
    try:
        c.execute("PRAGMA table_info(relationships)")
        rel_columns = [row[1] for row in c.fetchall()]
        
        # Check if table exists but is missing required columns
        if "user_id_1" not in rel_columns or "user_id_2" not in rel_columns:
            print("🔄 Migrating: Recreating relationships table with correct schema")
            try:
                # Drop old table and recreate with correct schema
                c.execute("DROP TABLE IF EXISTS relationships_old")
                c.execute("ALTER TABLE relationships RENAME TO relationships_old")
                
                # Create new table with correct schema
                c.execute('''CREATE TABLE relationships (
                                user_id_1 INTEGER,
                                user_id_2 INTEGER,
                                affinity INTEGER DEFAULT 0,
                                last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
                                PRIMARY KEY (user_id_1, user_id_2)
                            )''')
                
                # Try to migrate old data if it exists
                try:
                    c.execute("INSERT INTO relationships SELECT * FROM relationships_old")
                except:
                    pass
                
                c.execute("DROP TABLE IF EXISTS relationships_old")
                print("✓ Relationships table recreated with correct schema")
            except Exception as e:
                print(f"⚠️ Migration error (attempting to recreate): {e}")
        
        # Now add any missing columns to the correct schema
        c.execute("PRAGMA table_info(relationships)")
        rel_columns = [row[1] for row in c.fetchall()]
        
        if "affinity" not in rel_columns:
            try:
                c.execute("ALTER TABLE relationships ADD COLUMN affinity INTEGER DEFAULT 0")
                print("✓ Added affinity column to relationships table")
            except sqlite3.OperationalError:
                print("ℹ️ affinity column already exists")
        
        if "last_interaction" not in rel_columns:
            try:
                c.execute("ALTER TABLE relationships ADD COLUMN last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP")
                print("✓ Added last_interaction column to relationships table")
            except sqlite3.OperationalError:
                print("ℹ️ last_interaction column already exists")
    except Exception as e:
        print(f"⚠️ Relationships table check error: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Done! Database initialized with all tables ready.")

if __name__ == "__main__":
    setup_folder()
    init_database()
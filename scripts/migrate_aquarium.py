
import sqlite3
import os

DB_PATH = "data/database.db"

def migrate():
    print("🌊 Starting Project Aquarium Migration...")
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Update USERS table
    print("Checking 'users' table columns...")
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    
    updates = {
        "leaf_coin": "INTEGER DEFAULT 0",
        "charm_point": "INTEGER DEFAULT 0",
        "vip_tier": "TEXT DEFAULT 'none'",
        "home_thread_id": "INTEGER DEFAULT NULL"
    }
    
    for col, definition in updates.items():
        if col not in columns:
            print(f"  + Adding column: {col}")
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError as e:
                print(f"    ! Error adding {col}: {e}")
        else:
            print(f"  = Column {col} exists.")

    # 2. Re-create USER_DECOR table (New Schema)
    print("Migrating 'user_decor' table...")
    # Drop old table if exists (since schema changed significantly)
    c.execute("DROP TABLE IF EXISTS user_decor")
    c.execute('''CREATE TABLE user_decor (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_id TEXT,
                    quantity INTEGER DEFAULT 0,
                    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_id)
                )''')
    print("  ✓ user_decor table created (New Schema).")

    # 3. Create HOME_SLOTS table
    print("Creating 'home_slots' table...")
    c.execute('''CREATE TABLE IF NOT EXISTS home_slots (
                    user_id INTEGER,
                    slot_index INTEGER,
                    item_id TEXT,
                    placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, slot_index)
                )''')
    print("  ✓ home_slots table checked/created.")
    
    # 4. Create HOME_VISITS table (if not exists)
    print("Creating 'home_visits' table...")
    c.execute('''CREATE TABLE IF NOT EXISTS home_visits (
                    visitor_id INTEGER,
                    host_id INTEGER,
                    visited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (visitor_id, host_id, visited_at)
                )''')
    print("  ✓ home_visits table checked/created.")

    conn.commit()
    conn.close()
    print("✅ Migration Complete!")

if __name__ == "__main__":
    migrate()

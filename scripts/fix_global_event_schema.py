import sqlite3
import os

DB_PATH = "data/database.db"

def fix_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("⚠️  Dropping old global_event_state table...")
    c.execute("DROP TABLE IF EXISTS global_event_state")
    
    print("✨ Creating new global_event_state table...")
    c.execute('''CREATE TABLE IF NOT EXISTS global_event_state (
                    event_key TEXT PRIMARY KEY,
                    state_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    
    conn.commit()
    conn.close()
    print("✅ Schema fix complete.")

if __name__ == "__main__":
    fix_schema()

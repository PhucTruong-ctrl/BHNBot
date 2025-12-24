
import sqlite3
import os

DB_PATH = "./data/database.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(server_config)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "last_reminder_sent" not in columns:
            print("Adding missing column 'last_reminder_sent' to server_config...")
            cursor.execute("ALTER TABLE server_config ADD COLUMN last_reminder_sent TEXT")
            conn.commit()
            print("Migration successful: Added 'last_reminder_sent'")
        else:
            print("Column 'last_reminder_sent' already exists.")

    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

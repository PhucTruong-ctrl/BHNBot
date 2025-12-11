import os
import requests
import sqlite3
import json

# Configuration
DATA_DIR = "./data"
DB_PATH = os.path.join(DATA_DIR, "database.db")
TXT_PATH = os.path.join(DATA_DIR, "tu_dien.txt")
URL_TU_DIEN = "https://raw.githubusercontent.com/undertheseanlp/dictionary/master/dictionary/words.txt"

def setup_folder():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory {DATA_DIR}")

def download_tu_dien():
    print("Downloading dictionary...")
    response = requests.get(URL_TU_DIEN)
    if response.status_code == 200:
        with open(TXT_PATH, "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Downloaded dictionary file successfully")
        return response.text.splitlines()
    else:
        print("Error downloading file")
        return []

def init_database(word_list):
    print("Initializing SQLite Database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Main dictionary
    c.execute('''CREATE TABLE IF NOT EXISTS dictionary (word TEXT PRIMARY KEY)''')

    # 2. Pending words (Waiting for approval)
    c.execute('''CREATE TABLE IF NOT EXISTS pending_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE,
                    user_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # 3. Server Config (NEW: To store admin channel ID)
    c.execute('''CREATE TABLE IF NOT EXISTS server_config (
                    guild_id INTEGER PRIMARY KEY,
                    admin_channel_id INTEGER,
                    noitu_channel_id INTEGER
                )''')

    # Load data
    print("Loading data into Database...")
    count = 0
    for line in word_list:
        try:
            data = json.loads(line)
            raw_word = data.get("text", "")
        except json.JSONDecodeError:
            raw_word = line
            
        clean_word = raw_word.strip().lower()
        
        # Filter: Only words with 2 syllables, no special chars
        if clean_word and len(clean_word.split()) > 1 and clean_word.replace(" ", "").isalpha():
            try:
                c.execute("INSERT OR IGNORE INTO dictionary (word) VALUES (?)", (clean_word,))
                count += 1
            except:
                pass
    
    conn.commit()
    conn.close()
    print(f"Done! Loaded {count} words.")

if __name__ == "__main__":
    setup_folder()
    words = download_tu_dien()
    if words:
        init_database(words)
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
    """Initialize SQLite database with the NEW MODULAR SCHEMA."""
    print("Initializing SQLite Database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. CORE: USERS (Thay thế economy_users)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    seeds INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_daily DATETIME,
                    last_chat_reward DATETIME
                )''')

    # 2. CORE: USER STATS (Thay thế player_stats & các cột lẻ tẻ)
    # Lưu mọi chỉ số: wins nối từ, số lần câu, số cá bắt được...
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER,
                    game_id TEXT, -- 'fishing', 'noitu', 'wolf'
                    stat_key TEXT, -- 'wins', 'worms_used', 'bad_events'
                    value INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, game_id, stat_key)
                )''')

    # 3. CORE: INVENTORY
    # Using item_id to match database_manager.py (NOT item_name)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id TEXT, -- Khớp với key trong constants.py
                    quantity INTEGER DEFAULT 1,
                    item_type TEXT, -- 'tool', 'consumable', 'material'
                    obtained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, item_id)
                )''')

    # 4. MODULE: FISHING PROFILES
    c.execute('''CREATE TABLE IF NOT EXISTS fishing_profiles (
                    user_id INTEGER PRIMARY KEY,
                    rod_level INTEGER DEFAULT 1,
                    rod_durability INTEGER DEFAULT 30,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    # 5. MODULE: FISH COLLECTION (Túi Cá)
    c.execute('''CREATE TABLE IF NOT EXISTS fish_collection (
                    user_id INTEGER,
                    fish_id TEXT,
                    quantity INTEGER DEFAULT 0,
                    biggest_size REAL DEFAULT 0,
                    PRIMARY KEY (user_id, fish_id)
                )''')

    # 6. MODULE: RELATIONSHIPS (Thân thiết)
    c.execute('''CREATE TABLE IF NOT EXISTS relationships (
                    user_id_1 INTEGER,
                    user_id_2 INTEGER,
                    affinity INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending', -- 'pending', 'accepted'
                    last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
                    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id_1, user_id_2)
                )''')

    # 7. MODULE: SHARED PETS
    c.execute('''CREATE TABLE IF NOT EXISTS shared_pets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id_1 INTEGER,
                    user_id_2 INTEGER,
                    name TEXT DEFAULT 'Mèo Béo',
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    last_fed DATETIME DEFAULT CURRENT_TIMESTAMP,
                    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id_1, user_id_2)
                )''')

    # 8. CONFIG & OTHERS (Giữ nguyên)
    c.execute('''CREATE TABLE IF NOT EXISTS server_config (
                    guild_id INTEGER PRIMARY KEY,
                    logs_channel_id INTEGER,
                    noitu_channel_id INTEGER,
                    wolf_channel_id INTEGER,
                    giveaway_channel_id INTEGER,
                    exclude_chat_channels TEXT,
                    harvest_buff_until DATETIME
                )''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS tree_contributors (
                    user_id INTEGER,
                    guild_id INTEGER,
                    amount INTEGER DEFAULT 0,
                    contribution_exp INTEGER DEFAULT 0,
                    season INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, guild_id, season)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    host_id INTEGER,
                    prize TEXT,
                    winners_count INTEGER,
                    end_time TIMESTAMP,
                    requirements TEXT, 
                    status TEXT DEFAULT 'active'
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS giveaway_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id INTEGER,
                    user_id INTEGER,
                    entries INTEGER DEFAULT 1,
                    UNIQUE(giveaway_id, user_id)
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_invites (
                    inviter_id INTEGER,
                    joined_user_id INTEGER,
                    is_valid BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (inviter_id, joined_user_id)
                )''')

    conn.commit()
    
    # ==================== INDEXES (Tối Ưu Hóa) ====================
    print("\n[CREATING INDEXES FOR OPTIMIZATION]")
    
    # Index cho tiền tệ (BXH đại gia)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_seeds ON users(seeds DESC)")
        print("✓ Created index: users(seeds DESC)")
    except:
        pass
    
    # Index cho last_daily (Daily rewards)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_last_daily ON users(last_daily)")
        print("✓ Created index: users(last_daily)")
    except:
        pass
    
    # Index cho Stats (Tìm thành tựu nhanh)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_user_stats_lookup ON user_stats(user_id, game_id)")
        print("✓ Created index: user_stats(user_id, game_id)")
    except:
        pass
    
    # Index cho Stats leaderboard (Top theo giá trị)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_user_stats_value ON user_stats(stat_key, value DESC)")
        print("✓ Created index: user_stats(stat_key, value DESC) - For leaderboards")
    except:
        pass
    
    # Index cho Inventory (Tìm đồ nhanh)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(user_id, item_type)")
        print("✓ Created index: inventory(user_id, item_type)")
    except:
        pass
    
    # Index cho Fish Collection (Túi Cá)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_fish_collection_user ON fish_collection(user_id)")
        print("✓ Created index: fish_collection(user_id)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_fish_collection_qty ON fish_collection(quantity DESC)")
        print("✓ Created index: fish_collection(quantity DESC)")
    except:
        pass
    
    # Index cho Fishing Profiles
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_fishing_rod_level ON fishing_profiles(rod_level)")
        print("✓ Created index: fishing_profiles(rod_level)")
    except:
        pass
    
    # Index cho Relationships (BXH thân thiết)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_relationships_affinity ON relationships(affinity DESC)")
        print("✓ Created index: relationships(affinity DESC)")
    except:
        pass
    
    # Index cho Relationships status (Lời mời kết bạn)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_relationships_status ON relationships(status)")
        print("✓ Created index: relationships(status)")
    except:
        pass
    
    # Index cho Invites (Đếm invite nhanh)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_invites_valid ON user_invites(inviter_id, is_valid)")
        print("✓ Created index: user_invites(inviter_id, is_valid)")
    except:
        pass
    
    # Index cho Server Tree
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tree_guild ON server_tree(guild_id)")
        print("✓ Created index: server_tree(guild_id)")
    except:
        pass
    
    # Index cho Tree Contributors (Leaderboard)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tree_contrib_exp ON tree_contributors(guild_id, contribution_exp DESC)")
        print("✓ Created index: tree_contributors(guild_id, contribution_exp DESC)")
    except:
        pass

    conn.commit()
    
    # ==================== VACUUM DATABASE ====================
    print("\n[OPTIMIZING DATABASE]")
    c.execute("VACUUM")
    print("✓ Database vacuumed")
    
    c.execute("PRAGMA optimize")
    print("✓ Query optimization enabled")
    
    conn.commit()
    conn.close()
    print("\n✅ Database Setup Complete! All tables and indexes created.")

if __name__ == "__main__":
    setup_folder()
    init_database()

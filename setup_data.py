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
    
    # Enable foreign key constraints
    c.execute("PRAGMA foreign_keys = ON")
    print("✓ Foreign key constraints enabled")

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

    # 2.5. CORE: USER ACHIEVEMENTS (Lưu thành tựu đã đạt được)
    # Tránh trao thưởng lặp lại
    c.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_key TEXT,
                    unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_key),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    # 3. CORE: INVENTORY
    # Using item_id to match database_manager.py (NOT item_id)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id TEXT, -- Khớp với key trong constants.py
                    quantity INTEGER DEFAULT 1,
                    item_type TEXT, -- 'tool', 'consumable', 'material'
                    PRIMARY KEY (user_id, item_id)
                )''')

    # 4. MODULE: FISHING PROFILES
    c.execute('''CREATE TABLE IF NOT EXISTS fishing_profiles (
                    user_id INTEGER PRIMARY KEY,
                    rod_level INTEGER DEFAULT 1,
                    rod_durability INTEGER DEFAULT 30,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    # 4.5. MODULE: LEGENDARY QUESTS (Tiến độ từng cá huyền thoại)
    # Mỗi con cá có cơ chế riêng:
    # thuong_luong: quest_status = số lần hiến tế (0-3)
    # ca_ngan_ha: quest_status = 0 (chưa chế tạo mồi), 1 (đã chế tạo)
    # ca_phuong_hoang: quest_status = 0 (chưa chuẩn bị), 1 (đã chuẩn bị)
    # cthulhu_con: quest_status = số mảnh bản đồ (0-4), quest_completed = true để kích hoạt
    # ca_voi_52hz: quest_status = 0 (chưa mua), 1 (có máy), 2 (đã dò được 52Hz)
    c.execute('''CREATE TABLE IF NOT EXISTS legendary_quests (
                    user_id INTEGER,
                    fish_key TEXT,
                    quest_status INTEGER DEFAULT 0,
                    quest_completed BOOLEAN DEFAULT FALSE,
                    legendary_caught BOOLEAN DEFAULT FALSE,
                    last_progress_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, fish_key),
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
                    fishing_channel_id INTEGER,
                    giveaway_channel_id INTEGER,
                    exclude_chat_channels TEXT,
                    harvest_buff_until DATETIME,
                    bump_channel_id INTEGER,
                    bump_start_time TEXT,
                    last_reminder_sent TEXT,
                    category_roles TEXT DEFAULT '[]' -- JSON list of role IDs
                )''')

    # Add category_roles column if not exists
    try:
        c.execute("ALTER TABLE server_config ADD COLUMN category_roles TEXT DEFAULT '[]'")
        print("✓ Added category_roles column to server_config table")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
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

    # Migrate tree_contributors table if primary key is wrong
    try:
        c.execute("PRAGMA table_info(tree_contributors)")
        columns = c.fetchall()
        pk_columns = [col[1] for col in columns if col[5] == 1]  # col[5] is pk flag
        if pk_columns != ['user_id', 'guild_id', 'season']:
            print("Migrating tree_contributors table to include season in primary key...")
            # Create new table
            c.execute('''CREATE TABLE tree_contributors_new (
                            user_id INTEGER,
                            guild_id INTEGER,
                            amount INTEGER DEFAULT 0,
                            contribution_exp INTEGER DEFAULT 0,
                            season INTEGER DEFAULT 1,
                            PRIMARY KEY (user_id, guild_id, season)
                        )''')
            # Copy data, using current season from server_tree if exists, else 1
            c.execute('''INSERT INTO tree_contributors_new (user_id, guild_id, amount, contribution_exp, season)
                        SELECT tc.user_id, tc.guild_id, tc.amount, tc.contribution_exp, COALESCE(st.season, 1)
                        FROM tree_contributors tc
                        LEFT JOIN server_tree st ON tc.guild_id = st.guild_id''')
            # Drop old table
            c.execute("DROP TABLE tree_contributors")
            # Rename new table
            c.execute("ALTER TABLE tree_contributors_new RENAME TO tree_contributors")
            print("✓ Migrated tree_contributors table")
    except Exception as e:
        print(f"Error migrating tree_contributors: {e}")

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

    # Add image_url column if not exists
    try:
        c.execute("ALTER TABLE giveaways ADD COLUMN image_url TEXT")
        print("✓ Added image_url column to giveaways table")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Add start_date column to relationships if not exists
    try:
        c.execute("ALTER TABLE relationships ADD COLUMN start_date DATETIME")
        print("✓ Added start_date column to relationships table")
        # Update existing rows with current timestamp
        c.execute("UPDATE relationships SET start_date = CURRENT_TIMESTAMP WHERE start_date IS NULL")
        print("✓ Updated existing relationships with start_date")
    except sqlite3.OperationalError:
        # Column already exists
        pass

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

    # 9. GAME SESSIONS (Persistence cho game đang chơi)
    c.execute('''CREATE TABLE IF NOT EXISTS game_sessions (
                    guild_id INTEGER,
                    game_type TEXT, -- 'werewolf', 'noitu'
                    voice_channel_id INTEGER, -- For werewolf voice games, NULL for text
                    channel_id INTEGER,
                    game_state TEXT, -- JSON serialized state
                    last_saved DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, game_type, voice_channel_id)
                )''')

    # 10. MODULE: USER BUFFS (Persistence cho buff/emotional state)
    # Lưu trạng thái buff/debuff để không mất khi restart
    c.execute('''CREATE TABLE IF NOT EXISTS user_buffs (
                    user_id INTEGER,
                    buff_type TEXT, -- 'suy', 'keo_ly', 'lag', 'lucky_buff', 'legendary_buff'
                    duration_type TEXT, -- 'time' hoặc 'counter'
                    end_time REAL DEFAULT 0, -- Timestamp khi hết hạn (cho time-based)
                    remaining_count INTEGER DEFAULT 0, -- Số lượt còn lại (cho counter-based)
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, buff_type),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    # 11. GLOBAL EVENTS (Persistence State)
    c.execute('''CREATE TABLE IF NOT EXISTS global_event_state (
                    event_key TEXT PRIMARY KEY,
                    state_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

    # 12. TRANSACTION LOGS (Cash Flow Tracking)
    # New table for comprehensive cash flow analysis
    c.execute('''CREATE TABLE IF NOT EXISTS transaction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT DEFAULT 'seeds',
                    reason TEXT NOT NULL,          -- e.g., 'daily_reward', 'buy_item'
                    category TEXT DEFAULT 'uncategorized', -- e.g., 'social', 'fishing'
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Create indexes for transaction_logs
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_trans_created ON transaction_logs(created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_trans_cat ON transaction_logs(category)")
        print("✓ Created indexes for transaction_logs")
    except:
        pass

    # 13. LEGACY SNAPSHOT MIGRATION (One-time)
    # Check if transaction_logs is empty but users have money
    t_count = c.execute("SELECT COUNT(*) FROM transaction_logs").fetchone()[0]
    if t_count == 0:
        # Check total money in circulation
        users_money = c.execute("SELECT user_id, seeds FROM users WHERE seeds > 0").fetchall()
        if users_money:
            print(f"Creating Legacy Snapshot for {len(users_money)} users...")
            legacy_entries = []
            for uid, amount in users_money:
                legacy_entries.append((uid, amount, 'seeds', 'legacy_balance', 'system'))
            
            c.executemany('''
                INSERT INTO transaction_logs (user_id, amount, currency, reason, category)
                VALUES (?, ?, ?, ?, ?)
            ''', legacy_entries)
            print(f"✓ Created {len(legacy_entries)} legacy transaction logs.")
    
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
    
    # Index cho Legendary Quests
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_legendary_quests_user ON legendary_quests(user_id)")
        print("✓ Created index: legendary_quests(user_id)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_legendary_quests_status ON legendary_quests(fish_key, quest_completed)")
        print("✓ Created index: legendary_quests(fish_key, quest_completed)")
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
    
    # Index cho Game Sessions (Quick lookup)
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_lookup ON game_sessions(guild_id, game_type, voice_channel_id)")
        print("✓ Created index: game_sessions(guild_id, game_type, voice_channel_id)")
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

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
    
    # Economy: Track seeds per user
    c.execute('''CREATE TABLE IF NOT EXISTS economy_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    seeds INTEGER DEFAULT 0,
                    last_daily DATETIME,
                    last_chat_reward DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sacrifice_count INTEGER DEFAULT 0
                )''')
    
    # Relationships: Track affinity between users
    c.execute('''CREATE TABLE IF NOT EXISTS relationships (
                    user_id_1 INTEGER,
                    user_id_2 INTEGER,
                    affinity INTEGER DEFAULT 0,
                    last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
                    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id_1, user_id_2)
                )''')
    
    # Shared Pets: Track shared pets between users
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
    
    # Tree Contributors: Track who contributed to the tree (per season)
    c.execute('''CREATE TABLE IF NOT EXISTS tree_contributors (
                    user_id INTEGER,
                    guild_id INTEGER,
                    amount INTEGER DEFAULT 0,
                    contribution_exp INTEGER DEFAULT 0,
                    season INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, guild_id, season)
                )''')
    
    # Game Sessions: Save game state for resume after bot restart
    c.execute('''CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    game_state TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Giveaway: Track active giveaways
    c.execute('''CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    host_id INTEGER,
                    prize TEXT,
                    winners_count INTEGER,
                    end_time TIMESTAMP,
                    requirements TEXT, -- JSON
                    status TEXT DEFAULT 'active'
                )''')

    # Giveaway Participants: Track users who joined
    c.execute('''CREATE TABLE IF NOT EXISTS giveaway_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id INTEGER,
                    user_id INTEGER,
                    entries INTEGER DEFAULT 1,
                    UNIQUE(giveaway_id, user_id)
                )''')

    # User Achievements: Persistent achievement tracking (so achievements are only awarded once)
    c.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    achievement_key TEXT,
                    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, achievement_key)
                )''')

    # Invite Tracking: Track user invites for requirements
    c.execute('''CREATE TABLE IF NOT EXISTS user_invites (
                    inviter_id INTEGER,
                    joined_user_id INTEGER,
                    is_valid BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (inviter_id, joined_user_id)
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
        
        if "exclude_chat_channels" not in columns:
            try:
                c.execute("ALTER TABLE server_config ADD COLUMN exclude_chat_channels TEXT")
                print("✓ Added exclude_chat_channels column")
            except sqlite3.OperationalError:
                print("ℹ️ exclude_chat_channels column already exists")
    
    except Exception as e:
        print(f"⚠️ Migration check error: {e}")
    
    # Cleanup: Remove XP and Level columns from economy_users if they exist
    try:
        c.execute("PRAGMA table_info(economy_users)")
        eco_columns = [row[1] for row in c.fetchall()]
        
        if "xp" in eco_columns or "level" in eco_columns:
            print("🔄 Cleaning up: Removing XP/Level columns from economy_users")
            try:
                # Recreate table without xp and level columns
                c.execute('''
                    CREATE TABLE economy_users_new (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        seeds INTEGER DEFAULT 0,
                        last_daily DATETIME,
                        last_chat_reward DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Migrate data (only keep the columns we want)
                c.execute('''
                    INSERT INTO economy_users_new (user_id, username, seeds, last_daily, last_chat_reward, created_at, updated_at)
                    SELECT user_id, username, seeds, last_daily, last_chat_reward, created_at, updated_at FROM economy_users
                ''')
                
                c.execute('DROP TABLE economy_users')
                c.execute('ALTER TABLE economy_users_new RENAME TO economy_users')
                print("✓ Removed XP/Level columns from economy_users")
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")
        
        # Add fishing rod columns if missing
        if "rod_level" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN rod_level INTEGER DEFAULT 1")
                print("✓ Added rod_level column to economy_users (fishing rod tier)")
            except sqlite3.OperationalError:
                print("ℹ️ rod_level column already exists")
        
        if "rod_durability" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN rod_durability INTEGER DEFAULT 30")
                print("✓ Added rod_durability column to economy_users (fishing rod durability)")
            except sqlite3.OperationalError:
                print("ℹ️ rod_durability column already exists")
        
        # New achievement tracking columns
        if "bad_events_encountered" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN bad_events_encountered INTEGER DEFAULT 0")
                print("✓ Added bad_events_encountered column")
            except sqlite3.OperationalError:
                print("ℹ️ bad_events_encountered column already exists")
        
        if "global_reset_triggered" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN global_reset_triggered INTEGER DEFAULT 0")
                print("✓ Added global_reset_triggered column")
            except sqlite3.OperationalError:
                print("ℹ️ global_reset_triggered column already exists")
        
        if "chests_caught" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN chests_caught INTEGER DEFAULT 0")
                print("✓ Added chests_caught column")
            except sqlite3.OperationalError:
                print("ℹ️ chests_caught column already exists")
        
        if "market_boom_sales" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN market_boom_sales INTEGER DEFAULT 0")
                print("✓ Added market_boom_sales column")
            except sqlite3.OperationalError:
                print("ℹ️ market_boom_sales column already exists")
        
        if "robbed_count" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN robbed_count INTEGER DEFAULT 0")
                print("✓ Added robbed_count column")
            except sqlite3.OperationalError:
                print("ℹ️ robbed_count column already exists")
        
        if "god_of_wealth_encountered" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN god_of_wealth_encountered INTEGER DEFAULT 0")
                print("✓ Added god_of_wealth_encountered column")
            except sqlite3.OperationalError:
                print("ℹ️ god_of_wealth_encountered column already exists")
        
        if "rods_repaired" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN rods_repaired INTEGER DEFAULT 0")
                print("✓ Added rods_repaired column")
            except sqlite3.OperationalError:
                print("ℹ️ rods_repaired column already exists")
        
        if "trash_recycled" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN trash_recycled INTEGER DEFAULT 0")
                print("✓ Added trash_recycled column")
            except sqlite3.OperationalError:
                print("ℹ️ trash_recycled column already exists")
        
        if "legendary_fish" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN legendary_fish TEXT DEFAULT '[]'")
                print("✓ Added legendary_fish column (JSON list)")
            except sqlite3.OperationalError:
                print("ℹ️ legendary_fish column already exists")
        
        if "legendary_fish_count" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN legendary_fish_count INTEGER DEFAULT 0")
                print("✓ Added legendary_fish_count column")
            except sqlite3.OperationalError:
                print("ℹ️ legendary_fish_count column already exists")
        
        if "legendary_hall_of_fame" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN legendary_hall_of_fame TEXT DEFAULT '{}'")
                print("✓ Added legendary_hall_of_fame column (JSON dict)")
            except sqlite3.OperationalError:
                print("ℹ️ legendary_hall_of_fame column already exists")
        
        # Additional achievement tracking columns
        if "worms_used" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN worms_used INTEGER DEFAULT 0")
                print("✓ Added worms_used column (for worm_destroyer achievement)")
            except sqlite3.OperationalError:
                print("ℹ️ worms_used column already exists")
        
        if "trash_caught" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN trash_caught INTEGER DEFAULT 0")
                print("✓ Added trash_caught column (for trash_master achievement)")
            except sqlite3.OperationalError:
                print("ℹ️ trash_caught column already exists")
        
        if "good_events_encountered" not in eco_columns:
            try:
                c.execute("ALTER TABLE economy_users ADD COLUMN good_events_encountered INTEGER DEFAULT 0")
                print("✓ Added good_events_encountered column (for lucky achievement)")
            except sqlite3.OperationalError:
                print("ℹ️ good_events_encountered column already exists")
    
    except Exception as e:
        print(f"⚠️ Economy table check error: {e}")
    
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
                
        if "start_date" not in rel_columns:
            try:
                c.execute("ALTER TABLE relationships ADD COLUMN start_date DATETIME DEFAULT CURRENT_TIMESTAMP")
                print("✓ Added start_date column to relationships table")
            except sqlite3.OperationalError:
                print("ℹ️ start_date column already exists")
    except Exception as e:
        print(f"⚠️ Relationships table check error: {e}")
    
    # Add type column to inventory table (for item classification)
    try:
        c.execute("PRAGMA table_info(inventory)")
        inv_columns = [row[1] for row in c.fetchall()]
        
        if "type" not in inv_columns:
            try:
                c.execute("ALTER TABLE inventory ADD COLUMN type TEXT DEFAULT 'gift'")
                print("✓ Added type column to inventory table (fish, gift, tool, trash)")
            except sqlite3.OperationalError:
                print("ℹ️ type column already exists in inventory table")
    except Exception as e:
        print(f"⚠️ Inventory table check error: {e}")
    
    # Check and migrate tree_contributors table - add contribution_exp and season columns
    try:
        c.execute("PRAGMA table_info(tree_contributors)")
        tree_contrib_columns = [row[1] for row in c.fetchall()]
        
        if "contribution_exp" not in tree_contrib_columns:
            print("🔄 Migrating: Adding contribution_exp column to tree_contributors")
            try:
                # Add contribution_exp column
                c.execute("ALTER TABLE tree_contributors ADD COLUMN contribution_exp INTEGER DEFAULT 0")
                # Migrate old data: copy amount values to contribution_exp (for backward compatibility)
                c.execute("UPDATE tree_contributors SET contribution_exp = amount WHERE contribution_exp = 0")
                print("✓ Added contribution_exp column to tree_contributors and migrated data from amount")
            except Exception as e:
                print(f"⚠️ Migration error for tree_contributors: {e}")
        
        if "season" not in tree_contrib_columns:
            print("🔄 Migrating: Adding season column to tree_contributors")
            try:
                # Add season column
                c.execute("ALTER TABLE tree_contributors ADD COLUMN season INTEGER DEFAULT 1")
                print("✓ Added season column to tree_contributors")
            except Exception as e:
                print(f"⚠️ Migration error for tree_contributors season: {e}")
    except Exception as e:
        print(f"⚠️ Tree contributors table check error: {e}")
    
    conn.commit()
    
    # ==================== CREATE INDEXES FOR OPTIMIZATION ====================
    print("\n[CREATING INDEXES FOR OPTIMIZATION]")
    
    # Economy indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_economy_seeds ON economy_users(seeds DESC)")
        print("✓ Created index: economy_users(seeds)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_economy_last_daily ON economy_users(last_daily)")
        print("✓ Created index: economy_users(last_daily)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_economy_username ON economy_users(username)")
        print("✓ Created index: economy_users(username)")
    except:
        pass
    
    # Tree indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tree_contributors_exp ON tree_contributors(contribution_exp DESC)")
        print("✓ Created index: tree_contributors(contribution_exp)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tree_guild ON server_tree(guild_id)")
        print("✓ Created index: server_tree(guild_id)")
    except:
        pass
    
    # Relationship indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_relationships_affinity ON relationships(affinity DESC)")
        print("✓ Created index: relationships(affinity)")
    except:
        pass
    
    # Inventory indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)")
        print("✓ Created index: inventory(user_id)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_item ON inventory(item_name)")
        print("✓ Created index: inventory(item_name)")
    except:
        pass
    
    # Server config indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_server_config_guild ON server_config(guild_id)")
        print("✓ Created index: server_config(guild_id)")
    except:
        pass
    
    # Player stats indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_wins ON player_stats(wins DESC)")
        print("✓ Created index: player_stats(wins)")
    except:
        pass
    
    # Game sessions indexes
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_guild_game ON game_sessions(guild_id, game_type)")
        print("✓ Created index: game_sessions(guild_id, game_type)")
    except:
        pass
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_created ON game_sessions(created_at DESC)")
        print("✓ Created index: game_sessions(created_at)")
    except:
        pass
    
    conn.commit()
    
    # ==================== VACUUM DATABASE ====================
    print("\n[OPTIMIZING DATABASE]")
    c.execute("VACUUM")
    print("✓ Database vacuumed and optimized")
    
    # Enable query optimization
    c.execute("PRAGMA optimize")
    print("✓ Query optimization enabled")
    
    conn.commit()
    conn.close()
    print("\n✅ Done! Database initialized with all tables and indexes ready.")

if __name__ == "__main__":
    setup_folder()
    init_database()
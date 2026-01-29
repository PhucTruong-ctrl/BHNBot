#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script for BHNBot.
Replaces the obsolete SQLite setup_data.py.

Usage:
    python setup_postgres.py              # Full setup (create all tables)
    python setup_postgres.py --migrate    # Only create missing tables
    python setup_postgres.py --check      # Check which tables exist/missing

Environment Variables Required:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
    Or: DATABASE_URL
"""

import asyncio
import os
import sys
from typing import Optional

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

async def get_connection() -> asyncpg.Connection:
    """Get database connection from environment variables."""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return await asyncpg.connect(database_url)
    
    return await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "bhnbot"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", ""),
    )


# =============================================================================
# TABLE DEFINITIONS - PostgreSQL Schema
# =============================================================================

TABLES = {
    # =========================================================================
    # CORE TABLES
    # =========================================================================
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            seeds BIGINT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_daily TIMESTAMPTZ,
            last_chat_reward TIMESTAMPTZ
        )
    """,
    
    "user_stats": """
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id BIGINT,
            game_id TEXT,
            stat_key TEXT,
            value BIGINT DEFAULT 0,
            PRIMARY KEY (user_id, game_id, stat_key)
        )
    """,
    
    "user_achievements": """
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id BIGINT,
            achievement_key TEXT,
            unlocked_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, achievement_key)
        )
    """,
    
    "inventory": """
        CREATE TABLE IF NOT EXISTS inventory (
            user_id BIGINT,
            item_id TEXT,
            quantity INTEGER DEFAULT 1,
            item_type TEXT,
            PRIMARY KEY (user_id, item_id)
        )
    """,
    
    "transaction_logs": """
        CREATE TABLE IF NOT EXISTS transaction_logs (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            amount BIGINT NOT NULL,
            currency TEXT DEFAULT 'seeds',
            reason TEXT NOT NULL,
            category TEXT DEFAULT 'uncategorized',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    # =========================================================================
    # FISHING MODULE
    # =========================================================================
    "fishing_profiles": """
        CREATE TABLE IF NOT EXISTS fishing_profiles (
            user_id BIGINT PRIMARY KEY,
            rod_level INTEGER DEFAULT 1,
            rod_durability INTEGER DEFAULT 30
        )
    """,
    
    "fish_collection": """
        CREATE TABLE IF NOT EXISTS fish_collection (
            user_id BIGINT,
            fish_id TEXT,
            quantity INTEGER DEFAULT 0,
            biggest_size REAL DEFAULT 0,
            PRIMARY KEY (user_id, fish_id)
        )
    """,
    
    "legendary_quests": """
        CREATE TABLE IF NOT EXISTS legendary_quests (
            user_id BIGINT,
            fish_key TEXT,
            quest_status INTEGER DEFAULT 0,
            quest_completed BOOLEAN DEFAULT FALSE,
            legendary_caught BOOLEAN DEFAULT FALSE,
            last_progress_time TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, fish_key)
        )
    """,
    
    "auto_fishing": """
        CREATE TABLE IF NOT EXISTS auto_fishing (
            user_id BIGINT PRIMARY KEY,
            is_active BOOLEAN DEFAULT FALSE,
            started_at TIMESTAMPTZ,
            fish_count INTEGER DEFAULT 0,
            total_value BIGINT DEFAULT 0,
            worms_used INTEGER DEFAULT 0,
            last_tick TIMESTAMPTZ
        )
    """,
    
    "auto_fish_storage": """
        CREATE TABLE IF NOT EXISTS auto_fish_storage (
            user_id BIGINT,
            fish_id TEXT,
            quantity INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, fish_id)
        )
    """,
    
    # =========================================================================
    # SOCIAL MODULE
    # =========================================================================
    "relationships": """
        CREATE TABLE IF NOT EXISTS relationships (
            user_id_1 BIGINT,
            user_id_2 BIGINT,
            affinity INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            last_interaction TIMESTAMPTZ DEFAULT NOW(),
            start_date TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id_1, user_id_2)
        )
    """,
    
    "shared_pets": """
        CREATE TABLE IF NOT EXISTS shared_pets (
            id BIGSERIAL PRIMARY KEY,
            user_id_1 BIGINT,
            user_id_2 BIGINT,
            name TEXT DEFAULT 'Meo Beo',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            last_fed TIMESTAMPTZ DEFAULT NOW(),
            start_date TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id_1, user_id_2)
        )
    """,
    
    "buddy_bonds": """
        CREATE TABLE IF NOT EXISTS buddy_bonds (
            id BIGSERIAL PRIMARY KEY,
            user_id_1 BIGINT NOT NULL,
            user_id_2 BIGINT NOT NULL,
            bond_level INTEGER DEFAULT 1,
            bond_exp INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_activity TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id_1, user_id_2)
        )
    """,
    
    "buddy_requests": """
        CREATE TABLE IF NOT EXISTS buddy_requests (
            id BIGSERIAL PRIMARY KEY,
            from_user_id BIGINT NOT NULL,
            to_user_id BIGINT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(from_user_id, to_user_id)
        )
    """,
    
    "gift_history": """
        CREATE TABLE IF NOT EXISTS gift_history (
            id BIGSERIAL PRIMARY KEY,
            from_user_id BIGINT NOT NULL,
            to_user_id BIGINT NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    "user_profiles": """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id BIGINT PRIMARY KEY,
            bio TEXT,
            favorite_fish TEXT,
            title TEXT,
            badge TEXT,
            theme TEXT DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    # =========================================================================
    # KINDNESS MODULE
    # =========================================================================
    "kindness_stats": """
        CREATE TABLE IF NOT EXISTS kindness_stats (
            user_id BIGINT PRIMARY KEY,
            given_count INTEGER DEFAULT 0,
            received_count INTEGER DEFAULT 0,
            total_given_value BIGINT DEFAULT 0,
            total_received_value BIGINT DEFAULT 0,
            last_given TIMESTAMPTZ,
            last_received TIMESTAMPTZ
        )
    """,
    
    "kindness_streaks": """
        CREATE TABLE IF NOT EXISTS kindness_streaks (
            user_id BIGINT PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            last_streak_date DATE
        )
    """,
    
    # =========================================================================
    # VOICE MODULE
    # =========================================================================
    "voice_stats": """
        CREATE TABLE IF NOT EXISTS voice_stats (
            user_id BIGINT,
            guild_id BIGINT,
            total_minutes INTEGER DEFAULT 0,
            sessions_count INTEGER DEFAULT 0,
            last_session TIMESTAMPTZ,
            PRIMARY KEY (user_id, guild_id)
        )
    """,
    
    "voice_rewards": """
        CREATE TABLE IF NOT EXISTS voice_rewards (
            user_id BIGINT,
            guild_id BIGINT,
            last_reward TIMESTAMPTZ,
            pending_minutes INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
    """,
    
    # =========================================================================
    # SERVER CONFIG & TREE
    # =========================================================================
    "server_config": """
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id BIGINT PRIMARY KEY,
            logs_channel_id BIGINT,
            noitu_channel_id BIGINT,
            fishing_channel_id BIGINT,
            giveaway_channel_id BIGINT,
            exclude_chat_channels TEXT,
            harvest_buff_until TIMESTAMPTZ,
            bump_channel_id BIGINT,
            bump_start_time TEXT,
            last_reminder_sent TEXT,
            category_roles TEXT DEFAULT '[]',
            log_discord_channel_id BIGINT,
            log_ping_user_id BIGINT,
            log_discord_level TEXT DEFAULT 'WARNING',
            event_channel_id BIGINT,
            event_auto_channel_id BIGINT,
            event_role_id BIGINT,
            shop_channel_id BIGINT,
            shop_message_id BIGINT
        )
    """,
    
    "server_tree": """
        CREATE TABLE IF NOT EXISTS server_tree (
            guild_id BIGINT PRIMARY KEY,
            current_level INTEGER DEFAULT 1,
            current_progress INTEGER DEFAULT 0,
            total_contributed INTEGER DEFAULT 0,
            season INTEGER DEFAULT 1,
            tree_channel_id BIGINT,
            tree_message_id BIGINT,
            last_harvest TIMESTAMPTZ
        )
    """,
    
    "tree_contributors": """
        CREATE TABLE IF NOT EXISTS tree_contributors (
            user_id BIGINT,
            guild_id BIGINT,
            amount INTEGER DEFAULT 0,
            contribution_exp INTEGER DEFAULT 0,
            season INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, guild_id, season)
        )
    """,
    
    "tree_daily_water": """
        CREATE TABLE IF NOT EXISTS tree_daily_water (
            user_id BIGINT,
            guild_id BIGINT,
            water_date DATE,
            water_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id, water_date)
        )
    """,
    
    "tree_water_log": """
        CREATE TABLE IF NOT EXISTS tree_water_log (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT,
            guild_id BIGINT,
            amount INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    # =========================================================================
    # GIVEAWAY MODULE
    # =========================================================================
    "giveaways": """
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id BIGINT PRIMARY KEY,
            channel_id BIGINT,
            guild_id BIGINT,
            host_id BIGINT,
            prize TEXT,
            winners_count INTEGER,
            end_time TIMESTAMPTZ,
            requirements TEXT,
            status TEXT DEFAULT 'active',
            image_url TEXT
        )
    """,
    
    "giveaway_participants": """
        CREATE TABLE IF NOT EXISTS giveaway_participants (
            id BIGSERIAL PRIMARY KEY,
            giveaway_id BIGINT,
            user_id BIGINT,
            entries INTEGER DEFAULT 1,
            UNIQUE(giveaway_id, user_id)
        )
    """,
    
    # =========================================================================
    # INVITE TRACKING
    # =========================================================================
    "user_invites": """
        CREATE TABLE IF NOT EXISTS user_invites (
            inviter_id BIGINT,
            joined_user_id BIGINT,
            is_valid BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (inviter_id, joined_user_id)
        )
    """,
    
    # =========================================================================
    # GAME SESSIONS & BUFFS
    # =========================================================================
    "game_sessions": """
        CREATE TABLE IF NOT EXISTS game_sessions (
            guild_id BIGINT,
            game_type TEXT,
            voice_channel_id BIGINT,
            channel_id BIGINT,
            game_state TEXT,
            last_saved TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (guild_id, game_type, voice_channel_id)
        )
    """,
    
    "user_buffs": """
        CREATE TABLE IF NOT EXISTS user_buffs (
            user_id BIGINT,
            buff_type TEXT,
            duration_type TEXT,
            end_time DOUBLE PRECISION DEFAULT 0,
            remaining_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, buff_type)
        )
    """,
    
    "global_event_state": """
        CREATE TABLE IF NOT EXISTS global_event_state (
            event_key TEXT PRIMARY KEY,
            state_data TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    # =========================================================================
    # QUEST MODULE
    # =========================================================================
    "quest_config": """
        CREATE TABLE IF NOT EXISTS quest_config (
            guild_id BIGINT PRIMARY KEY,
            quest_channel_id BIGINT,
            quest_message_id BIGINT,
            quest_role_id BIGINT,
            daily_reset_hour INTEGER DEFAULT 0
        )
    """,
    
    "quest_contributions": """
        CREATE TABLE IF NOT EXISTS quest_contributions (
            user_id BIGINT,
            guild_id BIGINT,
            quest_date DATE,
            quest_type TEXT,
            contribution INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id, quest_date, quest_type)
        )
    """,
    
    "server_daily_quests": """
        CREATE TABLE IF NOT EXISTS server_daily_quests (
            guild_id BIGINT,
            quest_date DATE,
            quest_type TEXT,
            target INTEGER,
            current INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT FALSE,
            reward_distributed BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (guild_id, quest_date, quest_type)
        )
    """,
    
    "server_quest_streak": """
        CREATE TABLE IF NOT EXISTS server_quest_streak (
            guild_id BIGINT PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            last_completed_date DATE
        )
    """,
    
    # =========================================================================
    # VIP & PREMIUM
    # =========================================================================
    "vip_subscriptions": """
        CREATE TABLE IF NOT EXISTS vip_subscriptions (
            user_id BIGINT PRIMARY KEY,
            tier TEXT DEFAULT 'none',
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    "vip_auto_tasks": """
        CREATE TABLE IF NOT EXISTS vip_auto_tasks (
            user_id BIGINT,
            task_type TEXT,
            is_active BOOLEAN DEFAULT FALSE,
            config TEXT DEFAULT '{}',
            last_run TIMESTAMPTZ,
            PRIMARY KEY (user_id, task_type)
        )
    """,
    
    "vip_tournaments": """
        CREATE TABLE IF NOT EXISTS vip_tournaments (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            tournament_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            config TEXT DEFAULT '{}',
            prize_pool BIGINT DEFAULT 0,
            start_time TIMESTAMPTZ,
            end_time TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    "tournament_entries": """
        CREATE TABLE IF NOT EXISTS tournament_entries (
            id BIGSERIAL PRIMARY KEY,
            tournament_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            score BIGINT DEFAULT 0,
            data TEXT DEFAULT '{}',
            joined_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(tournament_id, user_id)
        )
    """,
    
    "premium_consumable_usage": """
        CREATE TABLE IF NOT EXISTS premium_consumable_usage (
            user_id BIGINT,
            consumable_type TEXT,
            used_count INTEGER DEFAULT 0,
            last_used TIMESTAMPTZ,
            PRIMARY KEY (user_id, consumable_type)
        )
    """,
    
    # =========================================================================
    # MUSIC MODULE
    # =========================================================================
    "user_playlists": """
        CREATE TABLE IF NOT EXISTS user_playlists (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            is_public BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, name)
        )
    """,
    
    "playlist_tracks": """
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            id BIGSERIAL PRIMARY KEY,
            playlist_id BIGINT NOT NULL,
            track_url TEXT NOT NULL,
            track_title TEXT,
            added_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    # =========================================================================
    # AQUARIUM & HOME
    # =========================================================================
    "user_aquarium": """
        CREATE TABLE IF NOT EXISTS user_aquarium (
            user_id BIGINT PRIMARY KEY,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            capacity INTEGER DEFAULT 10,
            theme TEXT DEFAULT 'default',
            theme_url TEXT,
            last_collect TIMESTAMPTZ
        )
    """,
    
    "user_decor": """
        CREATE TABLE IF NOT EXISTS user_decor (
            user_id BIGINT,
            decor_id TEXT,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, decor_id)
        )
    """,
    
    "home_slots": """
        CREATE TABLE IF NOT EXISTS home_slots (
            user_id BIGINT,
            slot_index INTEGER,
            fish_id TEXT,
            fish_size REAL,
            placed_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, slot_index)
        )
    """,
    
    "home_visits": """
        CREATE TABLE IF NOT EXISTS home_visits (
            visitor_id BIGINT,
            owner_id BIGINT,
            visited_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (visitor_id, owner_id, visited_at)
        )
    """,
    
    # =========================================================================
    # BAUCUA & MINIGAMES
    # =========================================================================
    "baucua_daily_stats": """
        CREATE TABLE IF NOT EXISTS baucua_daily_stats (
            user_id BIGINT,
            stat_date DATE,
            games_played INTEGER DEFAULT 0,
            total_bet BIGINT DEFAULT 0,
            total_won BIGINT DEFAULT 0,
            PRIMARY KEY (user_id, stat_date)
        )
    """,
    
    # =========================================================================
    # SYSTEM & ADMIN
    # =========================================================================
    "module_settings": """
        CREATE TABLE IF NOT EXISTS module_settings (
            guild_id BIGINT,
            module_name TEXT,
            is_enabled BOOLEAN DEFAULT TRUE,
            settings TEXT DEFAULT '{}',
            PRIMARY KEY (guild_id, module_name)
        )
    """,
    
    "audit_logs": """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT,
            user_id BIGINT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id BIGINT,
            details TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    "cog_config": """
        CREATE TABLE IF NOT EXISTS cog_config (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            cog_name VARCHAR(50) NOT NULL,
            settings JSONB DEFAULT '{}',
            enabled BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (guild_id, cog_name)
        )
    """,
    
    "command_usage": """
        CREATE TABLE IF NOT EXISTS command_usage (
            id BIGSERIAL PRIMARY KEY,
            command_name TEXT NOT NULL,
            user_id BIGINT,
            guild_id BIGINT,
            used_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    "user_activity": """
        CREATE TABLE IF NOT EXISTS user_activity (
            user_id BIGINT,
            guild_id BIGINT,
            activity_date DATE,
            message_count INTEGER DEFAULT 0,
            command_count INTEGER DEFAULT 0,
            voice_minutes INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id, activity_date)
        )
    """,
    
    "achievement_roles": """
        CREATE TABLE IF NOT EXISTS achievement_roles (
            guild_id BIGINT,
            achievement_key TEXT,
            role_id BIGINT,
            PRIMARY KEY (guild_id, achievement_key)
        )
    """,
    
    # =========================================================================
    # SEASONAL EVENTS
    # =========================================================================
    "active_events": """
        CREATE TABLE IF NOT EXISTS active_events (
            guild_id BIGINT PRIMARY KEY,
            event_id TEXT NOT NULL,
            started_at TIMESTAMPTZ DEFAULT NOW(),
            ends_at TIMESTAMPTZ,
            community_progress BIGINT DEFAULT 0,
            community_goal BIGINT DEFAULT 10000,
            milestones_reached TEXT DEFAULT '[]',
            announcement_channel_id BIGINT,
            announcement_message_id BIGINT,
            last_progress_update BIGINT DEFAULT 0
        )
    """,
    
    "event_participation": """
        CREATE TABLE IF NOT EXISTS event_participation (
            guild_id BIGINT,
            user_id BIGINT,
            event_id TEXT,
            currency BIGINT DEFAULT 0,
            contributions BIGINT DEFAULT 0,
            last_contribution TIMESTAMPTZ,
            PRIMARY KEY (guild_id, user_id, event_id)
        )
    """,
    
    "event_quests": """
        CREATE TABLE IF NOT EXISTS event_quests (
            guild_id BIGINT,
            user_id BIGINT,
            event_id TEXT,
            quest_id TEXT,
            progress INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT FALSE,
            claimed BOOLEAN DEFAULT FALSE,
            completed_at TIMESTAMPTZ,
            PRIMARY KEY (guild_id, user_id, event_id, quest_id)
        )
    """,
    
    "event_purchases": """
        CREATE TABLE IF NOT EXISTS event_purchases (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT,
            user_id BIGINT,
            event_id TEXT,
            item_id TEXT,
            quantity INTEGER DEFAULT 1,
            price BIGINT,
            purchased_at TIMESTAMPTZ DEFAULT NOW()
        )
    """,
    
    "user_titles": """
        CREATE TABLE IF NOT EXISTS user_titles (
            user_id BIGINT,
            title_key TEXT,
            title_name TEXT,
            unlocked_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, title_key)
        )
    """,
    
    "equipped_titles": """
        CREATE TABLE IF NOT EXISTS equipped_titles (
            user_id BIGINT PRIMARY KEY,
            title_key TEXT NOT NULL
        )
    """,
}

# =============================================================================
# INDEXES
# =============================================================================

INDEXES = [
    # Users
    "CREATE INDEX IF NOT EXISTS idx_users_seeds ON users(seeds DESC)",
    "CREATE INDEX IF NOT EXISTS idx_users_last_daily ON users(last_daily)",
    
    # User Stats
    "CREATE INDEX IF NOT EXISTS idx_user_stats_lookup ON user_stats(user_id, game_id)",
    "CREATE INDEX IF NOT EXISTS idx_user_stats_value ON user_stats(stat_key, value DESC)",
    
    # Inventory
    "CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(user_id, item_type)",
    
    # Fish Collection
    "CREATE INDEX IF NOT EXISTS idx_fish_collection_user ON fish_collection(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_fish_collection_qty ON fish_collection(quantity DESC)",
    
    # Fishing
    "CREATE INDEX IF NOT EXISTS idx_fishing_rod_level ON fishing_profiles(rod_level)",
    "CREATE INDEX IF NOT EXISTS idx_legendary_quests_user ON legendary_quests(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_legendary_quests_status ON legendary_quests(fish_key, quest_completed)",
    
    # Relationships
    "CREATE INDEX IF NOT EXISTS idx_relationships_affinity ON relationships(affinity DESC)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_status ON relationships(status)",
    
    # Invites
    "CREATE INDEX IF NOT EXISTS idx_invites_valid ON user_invites(inviter_id, is_valid)",
    
    # Tree
    "CREATE INDEX IF NOT EXISTS idx_tree_contrib_exp ON tree_contributors(guild_id, contribution_exp DESC)",
    
    # Transaction Logs
    "CREATE INDEX IF NOT EXISTS idx_trans_created ON transaction_logs(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_trans_cat ON transaction_logs(category)",
    "CREATE INDEX IF NOT EXISTS idx_trans_user ON transaction_logs(user_id)",
    
    # Voice
    "CREATE INDEX IF NOT EXISTS idx_voice_stats_guild ON voice_stats(guild_id)",
    
    # Commands
    "CREATE INDEX IF NOT EXISTS idx_command_usage_name ON command_usage(command_name)",
    "CREATE INDEX IF NOT EXISTS idx_command_usage_time ON command_usage(used_at)",
    
    # Activity
    "CREATE INDEX IF NOT EXISTS idx_user_activity_date ON user_activity(activity_date)",
    
    # Audit
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_guild ON audit_logs(guild_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs(created_at)",
    
    # Events
    "CREATE INDEX IF NOT EXISTS idx_event_participation_event ON event_participation(event_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_quests_user ON event_quests(user_id)",
]


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

async def get_existing_tables(conn: asyncpg.Connection) -> set[str]:
    """Get list of existing tables in database."""
    rows = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    return {row['table_name'] for row in rows}


async def check_tables(conn: asyncpg.Connection) -> None:
    """Check which tables exist and which are missing."""
    existing = await get_existing_tables(conn)
    defined = set(TABLES.keys())
    
    print(f"\n{'='*60}")
    print(f"DATABASE TABLE CHECK")
    print(f"{'='*60}\n")
    
    print(f"Total defined tables: {len(defined)}")
    print(f"Existing tables: {len(existing)}")
    
    missing = defined - existing
    extra = existing - defined
    
    if missing:
        print(f"\n[MISSING] {len(missing)} tables need to be created:")
        for table in sorted(missing):
            print(f"  - {table}")
    else:
        print("\n[OK] All defined tables exist!")
    
    if extra:
        print(f"\n[EXTRA] {len(extra)} tables exist but not in schema (may be legacy):")
        for table in sorted(extra):
            print(f"  ? {table}")
    
    print()


async def create_tables(conn: asyncpg.Connection, migrate_only: bool = False) -> None:
    """Create all tables (or only missing ones if migrate_only=True)."""
    existing = await get_existing_tables(conn) if migrate_only else set()
    
    print(f"\n{'='*60}")
    print(f"{'MIGRATION MODE' if migrate_only else 'FULL SETUP'}")
    print(f"{'='*60}\n")
    
    created = 0
    skipped = 0
    errors = 0
    
    for table_name, ddl in TABLES.items():
        if migrate_only and table_name in existing:
            skipped += 1
            continue
        
        try:
            await conn.execute(ddl)
            print(f"[OK] Created table: {table_name}")
            created += 1
        except Exception as e:
            print(f"[ERROR] Failed to create {table_name}: {e}")
            errors += 1
    
    print(f"\n--- Tables ---")
    print(f"Created: {created}")
    if migrate_only:
        print(f"Skipped (already exist): {skipped}")
    if errors:
        print(f"Errors: {errors}")
    
    # Create indexes
    print(f"\n--- Creating Indexes ---")
    idx_created = 0
    for idx_sql in INDEXES:
        try:
            await conn.execute(idx_sql)
            idx_created += 1
        except Exception as e:
            print(f"[WARN] Index error: {e}")
    
    print(f"Indexes created/verified: {idx_created}/{len(INDEXES)}")
    
    print(f"\n{'='*60}")
    print(f"SETUP COMPLETE")
    print(f"{'='*60}\n")


async def main() -> None:
    """Main entry point."""
    # Parse arguments
    migrate_only = "--migrate" in sys.argv
    check_only = "--check" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return
    
    # Connect to database
    try:
        conn = await get_connection()
        print(f"[OK] Connected to PostgreSQL")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        print("\nMake sure these environment variables are set:")
        print("  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS")
        print("  Or: DATABASE_URL")
        sys.exit(1)
    
    try:
        if check_only:
            await check_tables(conn)
        else:
            await create_tables(conn, migrate_only=migrate_only)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

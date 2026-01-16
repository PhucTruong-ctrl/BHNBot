from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.database import DatabaseManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

db_manager = DatabaseManager()

SEASONAL_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS active_events (
    guild_id BIGINT PRIMARY KEY,
    event_id TEXT,
    started_at TEXT,
    ends_at TEXT,
    community_progress INTEGER DEFAULT 0,
    community_goal INTEGER DEFAULT 0,
    milestones_reached TEXT DEFAULT '[]',
    announcement_channel_id BIGINT,
    announcement_message_id BIGINT,
    last_progress_update INTEGER DEFAULT 0,
    is_test_event BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS event_participation (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    currency INTEGER DEFAULT 0,
    contributions INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id)
);

CREATE TABLE IF NOT EXISTS event_quest_progress (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    quest_id TEXT,
    quest_type TEXT,
    current_value INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    completed_at TEXT,
    last_reset TEXT,
    PRIMARY KEY (guild_id, user_id, event_id, quest_id)
);

CREATE TABLE IF NOT EXISTS event_fish_collection (
    user_id BIGINT,
    fish_key TEXT,
    event_id TEXT,
    quantity INTEGER DEFAULT 1,
    first_caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, fish_key)
);

CREATE TABLE IF NOT EXISTS user_titles (
    user_id BIGINT,
    title_key TEXT,
    title_name TEXT,
    source TEXT,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, title_key)
);

CREATE TABLE IF NOT EXISTS secret_santa (
    guild_id BIGINT,
    event_id TEXT,
    giver_id BIGINT,
    receiver_id BIGINT,
    gift_item TEXT,
    gift_message TEXT,
    revealed INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, event_id, giver_id)
);

CREATE TABLE IF NOT EXISTS thank_letters (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    event_id TEXT,
    sender_id BIGINT,
    receiver_id BIGINT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boat_race_history (
    guild_id BIGINT,
    boat_id TEXT,
    wins INTEGER DEFAULT 0,
    races INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, boat_id)
);

CREATE TABLE IF NOT EXISTS boat_race_streaks (
    guild_id BIGINT,
    user_id BIGINT,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS event_shop_purchases (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    item_key TEXT,
    quantity INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id, item_key)
);

CREATE TABLE IF NOT EXISTS event_quests (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    quest_id TEXT,
    quest_type TEXT,
    quest_data TEXT,
    progress INTEGER DEFAULT 0,
    target INTEGER DEFAULT 1,
    completed INTEGER DEFAULT 0,
    claimed INTEGER DEFAULT 0,
    assigned_date TEXT,
    PRIMARY KEY (guild_id, user_id, event_id, quest_id)
);

CREATE TABLE IF NOT EXISTS ghost_hunt_daily (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    date TEXT,
    catch_count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id, date)
);

CREATE TABLE IF NOT EXISTS trick_treat_daily (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    date TEXT,
    use_count INTEGER DEFAULT 0,
    last_use TIMESTAMP,
    PRIMARY KEY (guild_id, user_id, event_id, date)
);

CREATE TABLE IF NOT EXISTS snowman_contributions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    amount INTEGER DEFAULT 0,
    contributed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lantern_parade (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    lanterns INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id)
);

CREATE TABLE IF NOT EXISTS lantern_voice_time (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    minutes INTEGER DEFAULT 0,
    tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS birthday_wishes (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS treasure_hunt_daily (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    date TEXT,
    hunts_completed INTEGER DEFAULT 0,
    treasures_found INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id, date)
);

CREATE TABLE IF NOT EXISTS beach_cleanup_daily (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    date TEXT,
    trash_collected INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id, date)
);

CREATE TABLE IF NOT EXISTS quiz_scores (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    correct_answers INTEGER DEFAULT 0,
    total_answers INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id)
);

CREATE TABLE IF NOT EXISTS countdown_participants (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    participated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bonus_received INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id)
);

CREATE TABLE IF NOT EXISTS balloon_pop_daily (
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    date TEXT,
    pops_count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, event_id, date)
);

CREATE TABLE IF NOT EXISTS user_active_title (
    user_id BIGINT PRIMARY KEY,
    title_key TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_milestones_reached (
    guild_id BIGINT,
    event_id TEXT,
    milestone_percentage INTEGER,
    reached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, event_id, milestone_percentage)
);
"""


async def init_seasonal_tables() -> None:
    for statement in SEASONAL_TABLES_SQL.strip().split(";"):
        statement = statement.strip()
        if statement:
            try:
                await db_manager.execute(statement)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Table creation warning: {e}")
    
    migrations = [
        "ALTER TABLE event_quests ADD COLUMN IF NOT EXISTS quest_type TEXT DEFAULT 'daily'",
    ]
    for migration in migrations:
        try:
            await db_manager.execute(migration)
        except Exception as e:
            if "already exists" not in str(e).lower() and "duplicate column" not in str(e).lower():
                logger.debug(f"Migration skipped: {e}")
    
    logger.info("Seasonal events tables initialized (PostgreSQL)")


async def execute_query(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    rows = await db_manager.fetchall(query, *params)
    if not rows:
        return []
    
    query_converted = db_manager._convert_sql_params(query)
    async with db_manager.pool.acquire() as conn:
        records = await conn.fetch(query_converted, *params)
        return [dict(record) for record in records]
        return [dict(record) for record in records]


async def execute_write(query: str, params: tuple = ()) -> int:
    await db_manager.execute(query, *params)
    return 0


async def execute_many(query: str, params_list: list[tuple]) -> None:
    await db_manager.executemany(query, params_list)


async def get_notification_role(guild_id: int) -> int | None:
    """Get notification role from server_config.event_role_id.
    
    This uses the existing server_config table set via /config set role_sukien.
    """
    query = "SELECT event_role_id FROM server_config WHERE guild_id = ?"
    row = await db_manager.fetchrow(query, guild_id)
    if row and row.get("event_role_id"):
        return row["event_role_id"]
    return None

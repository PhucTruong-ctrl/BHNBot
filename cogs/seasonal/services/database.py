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
    last_progress_update INTEGER DEFAULT 0
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

"""
Pytest configuration and fixtures for BHNBot test suite.

This module provides:
- Database mocking fixtures
- Discord.py object mocks
- Seasonal events test fixtures
- Common test utilities

IMPORTANT: Database mocking strategy:
The seasonal services import execute_query/execute_write from database.py.
We mock these functions directly to avoid real database connections.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Pytest Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Mocking - MUST use autouse to prevent real connections
# =============================================================================

@pytest.fixture(autouse=True)
def mock_database_init():
    """
    Auto-use fixture that mocks DatabaseManager initialization.
    Prevents real PostgreSQL connections at import time.
    """
    # Mock the DatabaseManager class itself
    with patch("core.database.DatabaseManager") as MockClass:
        mock_instance = MagicMock()
        mock_instance.pool = MagicMock()
        mock_instance.initialized = True
        mock_instance.initialize = AsyncMock()
        mock_instance.close = AsyncMock()
        mock_instance.fetchall = AsyncMock(return_value=[])
        mock_instance.fetchrow = AsyncMock(return_value=None)
        mock_instance.execute = AsyncMock()
        mock_instance.executemany = AsyncMock()
        mock_instance._convert_sql_params = lambda self, q: q
        MockClass.return_value = mock_instance
        
        # Also patch the already-created db_manager instance in seasonal database
        with patch("cogs.seasonal.services.database.db_manager", mock_instance):
            yield mock_instance


@pytest.fixture
def mock_execute_query():
    """
    Mock execute_query function from seasonal services.
    Tests should configure return_value based on their needs.
    """
    mock = AsyncMock(return_value=[])
    with patch("cogs.seasonal.services.database.execute_query", mock):
        with patch("cogs.seasonal.services.event_service.execute_query", mock):
            with patch("cogs.seasonal.services.participation_service.execute_query", mock):
                with patch("cogs.seasonal.services.quest_service.execute_query", mock):
                    yield mock


@pytest.fixture
def mock_execute_write():
    """
    Mock execute_write function from seasonal services.
    Returns 1 by default (rows affected).
    """
    mock = AsyncMock(return_value=1)
    with patch("cogs.seasonal.services.database.execute_write", mock):
        with patch("cogs.seasonal.services.event_service.execute_write", mock):
            with patch("cogs.seasonal.services.participation_service.execute_write", mock):
                with patch("cogs.seasonal.services.quest_service.execute_write", mock):
                    yield mock


# =============================================================================
# Discord.py Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_bot():
    """Create a mock Discord bot instance."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.user.name = "TestBot"
    bot.guilds = []
    bot.loop = asyncio.get_event_loop()
    return bot


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock()
    guild.id = 987654321
    guild.name = "Test Server"
    guild.member_count = 100
    guild.owner_id = 111111111
    return guild


@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = MagicMock()
    user.id = 222222222
    user.name = "TestUser"
    user.display_name = "Test User"
    user.avatar = MagicMock()
    user.avatar.url = "https://cdn.discordapp.com/avatars/test.png"
    user.mention = "<@222222222>"
    return user


@pytest.fixture
def mock_interaction(mock_guild, mock_user):
    """Create a mock Discord interaction."""
    interaction = MagicMock()
    interaction.user = mock_user
    interaction.guild = mock_guild
    interaction.guild_id = mock_guild.id
    interaction.channel_id = 333333333
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    return interaction


# =============================================================================
# Seasonal Events Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_event_config() -> dict:
    """Sample event configuration matching real event JSON structure."""
    return {
        "event_id": "test_event_2026",
        "name": "Test Event",
        "description": "A test event for unit testing",
        "theme_color": "#FF5733",
        "currency": {
            "name": "Test Coin",
            "emoji": "🪙"
        },
        "daily_quests": [
            {
                "id": "test_daily_1",
                "name": "Test Daily Quest",
                "description": "Complete a test action",
                "type": "fish_catch",
                "target": 5,
                "reward": 100
            }
        ],
        "fixed_quests": [
            {
                "id": "test_fixed_1",
                "name": "Test Fixed Quest",
                "description": "Complete many test actions",
                "type": "fish_catch",
                "target": 50,
                "reward": 500
            }
        ],
        "shop": {
            "items": [
                {
                    "id": "test_item_1",
                    "name": "Test Item",
                    "description": "A test shop item",
                    "price": 100,
                    "stock": -1,
                    "type": "cosmetic"
                }
            ]
        },
        "minigames": {
            "test_game": {
                "enabled": True,
                "cooldown": 60,
                "rewards": {
                    "min": 10,
                    "max": 50
                }
            }
        },
        "milestones": [
            {
                "target": 1000,
                "reward_multiplier": 1.1,
                "announcement": "First milestone reached!"
            },
            {
                "target": 5000,
                "reward_multiplier": 1.25,
                "announcement": "Halfway there!"
            }
        ]
    }


@pytest.fixture
def active_event_data(mock_guild) -> dict:
    """Sample active event database row."""
    return {
        "guild_id": mock_guild.id,
        "event_id": "test_event_2026",
        "started_at": datetime.now().isoformat(),
        "ends_at": (datetime.now() + timedelta(days=7)).isoformat(),
        "community_progress": 500,
        "community_goal": 10000,
        "milestones_reached": "[]",
        "announcement_channel_id": 444444444,
        "announcement_message_id": 555555555,
        "last_progress_update": 0,
        "is_test_event": True
    }


@pytest.fixture
def sample_participation_data(mock_guild, mock_user) -> dict:
    """Sample participation database row."""
    return {
        "guild_id": mock_guild.id,
        "user_id": mock_user.id,
        "event_id": "test_event_2026",
        "currency": 250,
        "contributions": 10
    }


@pytest.fixture
def sample_quest_data(mock_guild, mock_user) -> dict:
    """Sample quest progress database row."""
    return {
        "guild_id": mock_guild.id,
        "user_id": mock_user.id,
        "event_id": "test_event_2026",
        "quest_id": "test_daily_1",
        "quest_type": "fish_catch",
        "current_value": 3,
        "completed": 0,
        "completed_at": None,
        "last_reset": datetime.now().date().isoformat()
    }


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def events_data_path() -> str:
    """Return the path to events data directory."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data", "events")


@pytest.fixture
def load_event_json(events_data_path):
    """Factory fixture to load event JSON files."""
    def _load(filename: str) -> dict:
        filepath = os.path.join(events_data_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return _load


# =============================================================================
# Async Test Helpers
# =============================================================================

@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run

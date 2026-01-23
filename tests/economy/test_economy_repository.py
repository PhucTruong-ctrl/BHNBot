"""
Unit tests for EconomyRepository.

Tests the economy database operations including:
- User creation and retrieval
- Balance operations
- Daily rewards and streaks
- Guild configuration

Uses pytest with mocked database to avoid real DB connections.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import the module under test
from cogs.economy.repositories.economy_repository import EconomyRepository


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def economy_repo():
    """Create an EconomyRepository instance."""
    return EconomyRepository()


@pytest.fixture
def mock_db_manager():
    """Mock the db_manager for testing."""
    with patch("cogs.economy.repositories.economy_repository.db_manager") as mock:
        mock.fetchone = AsyncMock()
        mock.fetchrow = AsyncMock()
        mock.modify = AsyncMock()
        mock.execute = AsyncMock()
        mock.add_seeds = AsyncMock()
        mock.get_leaderboard = AsyncMock()
        mock.clear_cache_by_prefix = MagicMock()
        yield mock


# =============================================================================
# Test: get_or_create_user
# =============================================================================

class TestGetOrCreateUser:
    """Tests for get_or_create_user method."""

    @pytest.mark.asyncio
    async def test_returns_existing_user(self, economy_repo, mock_db_manager):
        """Should return existing user data when user exists."""
        # Arrange
        mock_db_manager.fetchone.return_value = (123456789, "TestUser", 1000)
        
        # Act
        result = await economy_repo.get_or_create_user(123456789, "TestUser")
        
        # Assert
        assert result == (123456789, "TestUser", 1000)
        mock_db_manager.modify.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_user_when_not_exists(self, economy_repo, mock_db_manager):
        """Should create new user with 0 seeds when user doesn't exist."""
        # Arrange
        mock_db_manager.fetchone.return_value = None
        
        # Act
        result = await economy_repo.get_or_create_user(123456789, "NewUser")
        
        # Assert
        assert result == (123456789, "NewUser", 0)
        mock_db_manager.modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_on_database_error(self, economy_repo, mock_db_manager):
        """Should return None when database error occurs."""
        # Arrange
        mock_db_manager.fetchone.side_effect = Exception("Database error")
        
        # Act
        result = await economy_repo.get_or_create_user(123456789, "TestUser")
        
        # Assert
        assert result is None


# =============================================================================
# Test: get_user_balance
# =============================================================================

class TestGetUserBalance:
    """Tests for get_user_balance method."""

    @pytest.mark.asyncio
    async def test_returns_balance_when_user_exists(self, economy_repo, mock_db_manager):
        """Should return user's seed balance."""
        # Arrange
        mock_db_manager.fetchone.return_value = (5000,)
        
        # Act
        result = await economy_repo.get_user_balance(123456789)
        
        # Assert
        assert result == 5000

    @pytest.mark.asyncio
    async def test_returns_zero_when_user_not_exists(self, economy_repo, mock_db_manager):
        """Should return 0 when user doesn't exist."""
        # Arrange
        mock_db_manager.fetchone.return_value = None
        
        # Act
        result = await economy_repo.get_user_balance(123456789)
        
        # Assert
        assert result == 0


# =============================================================================
# Test: add_seeds
# =============================================================================

class TestAddSeeds:
    """Tests for add_seeds method."""

    @pytest.mark.asyncio
    async def test_adds_seeds_and_returns_new_balance(self, economy_repo, mock_db_manager):
        """Should add seeds and return new balance."""
        # Arrange
        mock_db_manager.add_seeds.return_value = 1500
        
        # Act
        result = await economy_repo.add_seeds(123456789, 500, "test", "test_category")
        
        # Assert
        assert result == 1500
        mock_db_manager.add_seeds.assert_called_once_with(
            123456789, 500, "test", "test_category"
        )


# =============================================================================
# Test: get_leaderboard
# =============================================================================

class TestGetLeaderboard:
    """Tests for get_leaderboard method."""

    @pytest.mark.asyncio
    async def test_returns_top_users(self, economy_repo, mock_db_manager):
        """Should return leaderboard with specified limit."""
        # Arrange
        mock_db_manager.get_leaderboard.return_value = [
            (1, "User1", 10000),
            (2, "User2", 8000),
            (3, "User3", 5000),
        ]
        
        # Act
        result = await economy_repo.get_leaderboard(limit=3)
        
        # Assert
        assert len(result) == 3
        assert result[0][2] == 10000  # Highest balance first
        mock_db_manager.get_leaderboard.assert_called_once_with(3)


# =============================================================================
# Test: Daily Rewards
# =============================================================================

class TestDailyRewards:
    """Tests for daily reward related methods."""

    @pytest.mark.asyncio
    async def test_get_last_daily_returns_timestamp(self, economy_repo, mock_db_manager):
        """Should return last daily timestamp when exists."""
        # Arrange
        expected_time = datetime.now() - timedelta(hours=12)
        mock_db_manager.fetchrow.return_value = {"last_daily": expected_time}
        
        # Act
        result = await economy_repo.get_last_daily(123456789)
        
        # Assert
        assert result == expected_time

    @pytest.mark.asyncio
    async def test_get_last_daily_returns_none_when_never_claimed(
        self, economy_repo, mock_db_manager
    ):
        """Should return None when user never claimed daily."""
        # Arrange
        mock_db_manager.fetchrow.return_value = {"last_daily": None}
        
        # Act
        result = await economy_repo.get_last_daily(123456789)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_last_daily_clears_cache(self, economy_repo, mock_db_manager):
        """Should update timestamp and clear cache."""
        # Act
        await economy_repo.update_last_daily(123456789)
        
        # Assert
        mock_db_manager.execute.assert_called_once()
        mock_db_manager.clear_cache_by_prefix.assert_called_once_with("seeds_123456789")


# =============================================================================
# Test: Streak System
# =============================================================================

class TestStreakSystem:
    """Tests for streak related methods."""

    @pytest.mark.asyncio
    async def test_get_streak_data_returns_streak_and_protection(
        self, economy_repo, mock_db_manager
    ):
        """Should return streak count and protection status."""
        # Arrange
        mock_db_manager.fetchrow.return_value = {
            "daily_streak": 7,
            "streak_protection": True,
        }
        
        # Act
        streak, protection = await economy_repo.get_streak_data(123456789)
        
        # Assert
        assert streak == 7
        assert protection is True

    @pytest.mark.asyncio
    async def test_get_streak_data_returns_defaults_for_new_user(
        self, economy_repo, mock_db_manager
    ):
        """Should return (0, False) when user has no streak data."""
        # Arrange
        mock_db_manager.fetchrow.return_value = None
        
        # Act
        streak, protection = await economy_repo.get_streak_data(123456789)
        
        # Assert
        assert streak == 0
        assert protection is False

    @pytest.mark.asyncio
    async def test_update_streak_updates_database(self, economy_repo, mock_db_manager):
        """Should update streak and protection in database."""
        # Act
        await economy_repo.update_streak(123456789, 10, True)
        
        # Assert
        mock_db_manager.execute.assert_called_once()
        call_args = mock_db_manager.execute.call_args
        assert 10 in call_args[0][1]  # streak value
        assert True in call_args[0][1]  # protection value


# =============================================================================
# Test: Guild Configuration
# =============================================================================

class TestGuildConfiguration:
    """Tests for guild configuration methods."""

    @pytest.mark.asyncio
    async def test_harvest_buff_active_when_not_expired(
        self, economy_repo, mock_db_manager
    ):
        """Should return True when harvest buff is not expired."""
        # Arrange
        future_time = datetime.now() + timedelta(hours=1)
        mock_db_manager.fetchrow.return_value = {"harvest_buff_until": future_time}
        
        # Act
        result = await economy_repo.is_harvest_buff_active(987654321)
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_harvest_buff_inactive_when_expired(
        self, economy_repo, mock_db_manager
    ):
        """Should return False when harvest buff is expired."""
        # Arrange
        past_time = datetime.now() - timedelta(hours=1)
        mock_db_manager.fetchrow.return_value = {"harvest_buff_until": past_time}
        
        # Act
        result = await economy_repo.is_harvest_buff_active(987654321)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_harvest_buff_inactive_when_no_config(
        self, economy_repo, mock_db_manager
    ):
        """Should return False when no guild config exists."""
        # Arrange
        mock_db_manager.fetchrow.return_value = None
        
        # Act
        result = await economy_repo.is_harvest_buff_active(987654321)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_excluded_channels_returns_list(
        self, economy_repo, mock_db_manager
    ):
        """Should return list of excluded channel IDs."""
        # Arrange
        mock_db_manager.fetchrow.return_value = {
            "logs_channel_id": 111111111,
            "exclude_chat_channels": "[222222222, 333333333]",
        }
        
        # Act
        result = await economy_repo.get_excluded_channels(987654321)
        
        # Assert
        assert 111111111 in result  # logs channel
        assert 222222222 in result  # excluded channel 1
        assert 333333333 in result  # excluded channel 2

    @pytest.mark.asyncio
    async def test_get_excluded_channels_handles_empty_config(
        self, economy_repo, mock_db_manager
    ):
        """Should return empty list when no excluded channels."""
        # Arrange
        mock_db_manager.fetchrow.return_value = {
            "logs_channel_id": None,
            "exclude_chat_channels": None,
        }
        
        # Act
        result = await economy_repo.get_excluded_channels(987654321)
        
        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_excluded_channels_handles_database_error(
        self, economy_repo, mock_db_manager
    ):
        """Should return empty list on database error."""
        # Arrange
        mock_db_manager.fetchrow.side_effect = Exception("Database error")
        
        # Act
        result = await economy_repo.get_excluded_channels(987654321)
        
        # Assert
        assert result == []

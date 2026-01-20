"""
Tests for Participation Service - User currency and participation tracking.

Tests cover:
- Getting/creating participation records
- Currency operations (add, spend, get)
- Contribution tracking
- Leaderboards and statistics
"""
import pytest
from unittest.mock import AsyncMock, patch


# =============================================================================
# Participation Record Tests
# =============================================================================

class TestParticipationRecords:
    """Test participation record management."""
    
    @pytest.mark.asyncio
    async def test_get_participation_returns_none_when_not_found(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Getting participation for non-existent user should return None."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = []
        
        result = await participation_service.get_participation(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_participation_returns_record(
        self, mock_guild, mock_user, mock_execute_query, sample_participation_data
    ):
        """Getting participation should return the record."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [sample_participation_data]
        
        result = await participation_service.get_participation(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result is not None
        assert result["currency"] == 250
        assert result["contributions"] == 10
    
    @pytest.mark.asyncio
    async def test_ensure_participation_creates_if_not_exists(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Ensure participation should create record if it doesn't exist."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = []  # Not found
        
        result = await participation_service.ensure_participation(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert mock_execute_write.called
        assert result["currency"] == 0
        assert result["contributions"] == 0
    
    @pytest.mark.asyncio
    async def test_ensure_participation_returns_existing(
        self, mock_guild, mock_user, mock_execute_query, sample_participation_data
    ):
        """Ensure participation should return existing record without creating."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [sample_participation_data]
        
        result = await participation_service.ensure_participation(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result["currency"] == 250


# =============================================================================
# Currency Operations Tests
# =============================================================================

class TestCurrencyOperations:
    """Test currency add/spend/get operations."""
    
    @pytest.mark.asyncio
    async def test_add_currency_increments_balance(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Adding currency should increment the user's balance."""
        from cogs.seasonal.services import participation_service
        
        # First call for ensure_participation, second for get new balance
        mock_execute_query.side_effect = [
            [{"guild_id": mock_guild.id, "user_id": mock_user.id, "event_id": "test_event_2026", "currency": 100, "contributions": 0}],
            [{"currency": 200}]
        ]
        
        result = await participation_service.add_currency(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            amount=100
        )
        
        assert mock_execute_write.called
        assert result == 200  # New balance
    
    @pytest.mark.asyncio
    async def test_spend_currency_returns_true_when_sufficient(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write, sample_participation_data
    ):
        """Spending currency with sufficient balance should return True."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [sample_participation_data]  # Has 250 currency
        
        result = await participation_service.spend_currency(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            amount=100  # Less than 250
        )
        
        assert result is True
        assert mock_execute_write.called
    
    @pytest.mark.asyncio
    async def test_spend_currency_returns_false_when_insufficient(
        self, mock_guild, mock_user, mock_execute_query, sample_participation_data
    ):
        """Spending more than balance should return False."""
        from cogs.seasonal.services import participation_service
        
        sample_participation_data["currency"] = 100
        mock_execute_query.return_value = [sample_participation_data]
        
        result = await participation_service.spend_currency(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            amount=500
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_currency_returns_balance(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Getting currency should return the current balance."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [{"currency": 750}]
        
        result = await participation_service.get_currency(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result == 750
    
    @pytest.mark.asyncio
    async def test_get_currency_returns_zero_when_not_found(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Getting currency for non-participant should return 0."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = []
        
        result = await participation_service.get_currency(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result == 0


# =============================================================================
# Contribution Tests
# =============================================================================

class TestContributions:
    """Test contribution tracking."""
    
    @pytest.mark.asyncio
    async def test_add_contribution_increments_count(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Adding contribution should increment the count."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.side_effect = [
            [{"guild_id": mock_guild.id, "user_id": mock_user.id, "event_id": "test_event_2026", "currency": 0, "contributions": 10}],
            [{"contributions": 15}]
        ]
        
        result = await participation_service.add_contribution(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            amount=5
        )
        
        assert mock_execute_write.called
        assert result == 15


# =============================================================================
# Leaderboard Tests
# =============================================================================

class TestLeaderboard:
    """Test leaderboard functionality."""
    
    @pytest.mark.asyncio
    async def test_get_participants_returns_list(
        self, mock_guild, mock_execute_query
    ):
        """Getting participants should return list sorted by currency."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [
            {"user_id": 1, "currency": 1000},
            {"user_id": 2, "currency": 500},
            {"user_id": 3, "currency": 250},
        ]
        
        result = await participation_service.get_participants(
            guild_id=mock_guild.id,
            event_id="test_event_2026"
        )
        
        assert len(result) == 3
        assert result[0]["currency"] == 1000  # Highest first
    
    @pytest.mark.asyncio
    async def test_get_leaderboard_respects_limit(
        self, mock_guild, mock_execute_query
    ):
        """Getting leaderboard should respect the limit parameter."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [
            {"user_id": 1, "currency": 1000},
            {"user_id": 2, "currency": 500},
        ]
        
        result = await participation_service.get_leaderboard(
            guild_id=mock_guild.id,
            event_id="test_event_2026",
            limit=5
        )
        
        # Check that LIMIT was passed in query
        call_args = str(mock_execute_query.call_args)
        assert "LIMIT" in call_args
    
    @pytest.mark.asyncio
    async def test_get_participant_count_returns_count(
        self, mock_guild, mock_execute_query
    ):
        """Getting participant count should return the count."""
        from cogs.seasonal.services import participation_service
        
        mock_execute_query.return_value = [{"count": 42}]
        
        result = await participation_service.get_participant_count(
            guild_id=mock_guild.id,
            event_id="test_event_2026"
        )
        
        assert result == 42

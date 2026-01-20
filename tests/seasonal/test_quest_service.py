"""
Tests for Quest Service - Quest management and progress tracking.

Tests cover:
- Daily quest initialization and refresh
- Fixed quest initialization
- Quest progress updates
- Quest reward claiming
- Quest statistics
"""
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch


# =============================================================================
# Daily Quest Tests
# =============================================================================

class TestDailyQuests:
    """Test daily quest initialization and management."""
    
    @pytest.mark.asyncio
    async def test_init_daily_quests_creates_quests(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write, sample_event_config
    ):
        """Initializing daily quests should create quest records."""
        from cogs.seasonal.services import quest_service
        
        # No existing quests
        mock_execute_query.return_value = []
        
        result = await quest_service.init_daily_quests(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            event_config=sample_event_config
        )
        
        # Should create quests from daily_quests pool
        assert len(result) > 0
        assert all(q["quest_type"] == "daily" for q in result)
    
    @pytest.mark.asyncio
    async def test_init_daily_quests_returns_existing_for_today(
        self, mock_guild, mock_user, mock_execute_query, sample_event_config
    ):
        """If quests exist for today, should return them without creating new ones."""
        from cogs.seasonal.services import quest_service
        
        today = datetime.now().date().isoformat()
        existing_quests = [
            {
                "quest_id": "daily_fish_5",
                "quest_type": "daily",
                "quest_data": json.dumps(sample_event_config["daily_quests"][0]),
                "progress": 2,
                "target": 5,
                "completed": False,
                "assigned_date": today
            }
        ]
        mock_execute_query.return_value = existing_quests
        
        result = await quest_service.init_daily_quests(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            event_config=sample_event_config
        )
        
        assert result == existing_quests
    
    @pytest.mark.asyncio
    async def test_init_daily_quests_empty_when_no_pool(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """If event has no daily_quests, should return empty list."""
        from cogs.seasonal.services import quest_service
        
        mock_execute_query.return_value = []
        
        result = await quest_service.init_daily_quests(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            event_config={"daily_quests": []}  # Empty pool
        )
        
        assert result == []


# =============================================================================
# Fixed Quest Tests
# =============================================================================

class TestFixedQuests:
    """Test fixed/achievement quest management."""
    
    @pytest.mark.asyncio
    async def test_init_fixed_quests_creates_quests(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write, sample_event_config
    ):
        """Initializing fixed quests should create quest records."""
        from cogs.seasonal.services import quest_service
        
        mock_execute_query.return_value = []  # No existing quests
        
        result = await quest_service.init_fixed_quests(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            event_config=sample_event_config
        )
        
        assert len(result) == len(sample_event_config["fixed_quests"])
        assert all(q["quest_type"] == "fixed" for q in result)
    
    @pytest.mark.asyncio
    async def test_init_fixed_quests_preserves_existing_progress(
        self, mock_guild, mock_user, mock_execute_query, sample_event_config
    ):
        """Fixed quests should preserve existing progress."""
        from cogs.seasonal.services import quest_service
        
        existing = {
            "quest_id": "master_fisher",
            "quest_type": "fixed",
            "quest_data": json.dumps(sample_event_config["fixed_quests"][0]),
            "progress": 50,
            "target": 100,
            "completed": False
        }
        
        # Return existing for get_quest_progress
        mock_execute_query.return_value = [existing]
        
        result = await quest_service.init_fixed_quests(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            event_config=sample_event_config
        )
        
        assert len(result) == 1
        assert result[0]["progress"] == 50  # Preserved


# =============================================================================
# Quest Progress Tests
# =============================================================================

class TestQuestProgress:
    """Test quest progress updates."""
    
    @pytest.mark.asyncio
    async def test_update_quest_progress_increments(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Updating quest progress should increment matching quests."""
        from cogs.seasonal.services import quest_service
        
        quest_data = {
            "id": "daily_fish_5",
            "type": "fish_count",
            "target": 5
        }
        mock_execute_query.return_value = [
            {
                "quest_id": "daily_fish_5",
                "quest_data": json.dumps(quest_data),
                "progress": 3,
                "target": 5,
                "completed": False
            }
        ]
        
        result = await quest_service.update_quest_progress(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            quest_type_filter="fish_count",
            increment=1
        )
        
        assert mock_execute_write.called
    
    @pytest.mark.asyncio
    async def test_update_quest_progress_returns_completed_quests(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Should return list of quests that were just completed."""
        from cogs.seasonal.services import quest_service
        
        quest_data = {
            "id": "daily_fish_5",
            "type": "fish_count",
            "target": 5,
            "reward_value": 100
        }
        mock_execute_query.return_value = [
            {
                "quest_id": "daily_fish_5",
                "quest_data": json.dumps(quest_data),
                "progress": 4,  # One away from completion
                "target": 5,
                "completed": False
            }
        ]
        
        result = await quest_service.update_quest_progress(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            quest_type_filter="fish_count",
            increment=1
        )
        
        # Should contain the just-completed quest
        assert len(result) == 1
        assert result[0]["quest_id"] == "daily_fish_5"
    
    @pytest.mark.asyncio
    async def test_update_quest_progress_ignores_non_matching_type(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Should not update quests with different type."""
        from cogs.seasonal.services import quest_service
        
        quest_data = {
            "id": "daily_lixi_3",
            "type": "lixi_sent",  # Different type
            "target": 3
        }
        mock_execute_query.return_value = [
            {
                "quest_id": "daily_lixi_3",
                "quest_data": json.dumps(quest_data),
                "progress": 0,
                "target": 3,
                "completed": False
            }
        ]
        
        result = await quest_service.update_quest_progress(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            quest_type_filter="fish_count",  # Different filter
            increment=1
        )
        
        # Should not update non-matching quest
        assert len(result) == 0


# =============================================================================
# Quest Reward Tests
# =============================================================================

class TestQuestRewards:
    """Test quest reward claiming."""
    
    @pytest.mark.asyncio
    async def test_claim_quest_reward_returns_reward_info(
        self, mock_guild, mock_user, mock_execute_query, mock_execute_write
    ):
        """Claiming reward should return reward info."""
        from cogs.seasonal.services import quest_service
        
        quest_data = {
            "id": "daily_fish_5",
            "reward_type": "currency",
            "reward_value": 100
        }
        mock_execute_query.side_effect = [
            [{"quest_id": "daily_fish_5", "quest_data": json.dumps(quest_data), "progress": 5, "target": 5, "completed": True}],
            [{"claimed": False}],
            [{"user_id": mock_user.id}],
            [{"currency": 100}],
        ]
        
        result = await quest_service.claim_quest_reward(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            quest_id="daily_fish_5"
        )
        
        assert result is not None
        assert result["reward_type"] == "currency"
        assert result["reward_value"] == 100
    
    @pytest.mark.asyncio
    async def test_claim_quest_reward_returns_none_if_not_completed(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Claiming incomplete quest should return None."""
        from cogs.seasonal.services import quest_service
        
        mock_execute_query.return_value = [{
            "quest_id": "daily_fish_5",
            "quest_data": "{}",
            "progress": 3,
            "target": 5,
            "completed": False  # Not completed
        }]
        
        result = await quest_service.claim_quest_reward(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            quest_id="daily_fish_5"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_claim_quest_reward_returns_none_if_already_claimed(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Claiming already-claimed quest should return None."""
        from cogs.seasonal.services import quest_service
        
        mock_execute_query.side_effect = [
            # get_quest_progress
            [{
                "quest_id": "daily_fish_5",
                "quest_data": "{}",
                "progress": 5,
                "target": 5,
                "completed": True
            }],
            # Check if already claimed
            [{"claimed": True}]  # Already claimed!
        ]
        
        result = await quest_service.claim_quest_reward(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026",
            quest_id="daily_fish_5"
        )
        
        assert result is None


# =============================================================================
# Quest Statistics Tests
# =============================================================================

class TestQuestStats:
    """Test quest statistics."""
    
    @pytest.mark.asyncio
    async def test_get_quest_stats_returns_summary(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Getting quest stats should return summary."""
        from cogs.seasonal.services import quest_service
        
        mock_execute_query.return_value = [{
            "total": 5,
            "completed": 3,
            "claimed": 2
        }]
        
        result = await quest_service.get_quest_stats(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result["total"] == 5
        assert result["completed"] == 3
        assert result["claimed"] == 2
    
    @pytest.mark.asyncio
    async def test_get_quest_stats_returns_zeros_when_no_quests(
        self, mock_guild, mock_user, mock_execute_query
    ):
        """Getting stats with no quests should return zeros."""
        from cogs.seasonal.services import quest_service
        
        mock_execute_query.return_value = []
        
        result = await quest_service.get_quest_stats(
            guild_id=mock_guild.id,
            user_id=mock_user.id,
            event_id="test_event_2026"
        )
        
        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["claimed"] == 0

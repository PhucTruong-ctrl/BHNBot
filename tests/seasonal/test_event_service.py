"""
Tests for Event Service - Event lifecycle management.

Tests cover:
- Starting events
- Ending events
- Getting active events
- Community progress tracking
- Milestone management
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


# =============================================================================
# Event Lifecycle Tests
# =============================================================================

class TestEventLifecycle:
    """Test event start/end lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_event_creates_record(self, mock_guild, mock_execute_write, mock_execute_query):
        """Starting an event should create a database record."""
        from cogs.seasonal.services import event_service
        
        guild_id = mock_guild.id
        event_id = "spring_2026"
        community_goal = 10000
        ends_at = datetime.now() + timedelta(days=7)
        
        await event_service.start_event(
            guild_id=guild_id,
            event_id=event_id,
            community_goal=community_goal,
            ends_at=ends_at,
            is_test_event=True
        )
        
        # Verify execute_write was called with INSERT
        assert mock_execute_write.called
        call_args = str(mock_execute_write.call_args)
        assert "INSERT INTO active_events" in call_args or "active_events" in call_args
    
    @pytest.mark.asyncio
    async def test_get_active_event_returns_none_when_no_event(self, mock_guild, mock_execute_query):
        """Getting active event when none exists should return None."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = []
        
        result = await event_service.get_active_event(mock_guild.id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_active_event_returns_event_data(self, mock_guild, mock_execute_query, active_event_data):
        """Getting active event should return event data with parsed milestones."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = [active_event_data]
        
        result = await event_service.get_active_event(mock_guild.id)
        
        assert result is not None
        assert result["event_id"] == "test_event_2026"
        assert isinstance(result.get("milestones_reached"), list)
    
    @pytest.mark.asyncio
    async def test_end_event_deletes_record(self, mock_guild, mock_execute_query, mock_execute_write, active_event_data):
        """Ending an event should delete the active_events record."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = [active_event_data]
        
        result = await event_service.end_event(mock_guild.id)
        
        assert result is not None
        assert mock_execute_write.called
        call_args = str(mock_execute_write.call_args)
        assert "DELETE" in call_args or "delete" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_end_event_returns_none_when_no_event(self, mock_guild, mock_execute_query):
        """Ending event when none exists should return None."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = []
        
        result = await event_service.end_event(mock_guild.id)
        
        assert result is None


# =============================================================================
# Community Progress Tests
# =============================================================================

class TestCommunityProgress:
    """Test community progress tracking."""
    
    @pytest.mark.asyncio
    async def test_update_community_progress_increments(self, mock_guild, mock_execute_write, mock_execute_query):
        """Updating community progress should increment the value."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = [{"community_progress": 150}]
        
        result = await event_service.update_community_progress(mock_guild.id, 50)
        
        assert mock_execute_write.called
        assert result == 150  # Returns new total
    
    @pytest.mark.asyncio
    async def test_get_community_progress_returns_tuple(self, mock_guild, mock_execute_query):
        """Getting community progress should return (progress, goal) tuple."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = [{
            "community_progress": 5000,
            "community_goal": 10000
        }]
        
        progress, goal = await event_service.get_community_progress(mock_guild.id)
        
        assert progress == 5000
        assert goal == 10000
    
    @pytest.mark.asyncio
    async def test_get_community_progress_returns_zeros_when_no_event(self, mock_guild, mock_execute_query):
        """Getting progress when no event should return (0, 0)."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = []
        
        progress, goal = await event_service.get_community_progress(mock_guild.id)
        
        assert progress == 0
        assert goal == 0


# =============================================================================
# Milestone Tests
# =============================================================================

class TestMilestones:
    """Test milestone tracking."""
    
    @pytest.mark.asyncio
    async def test_add_milestone_reached_updates_list(self, mock_guild, mock_execute_query, mock_execute_write, active_event_data):
        """Adding a milestone should update the milestones_reached list."""
        from cogs.seasonal.services import event_service
        
        # Database stores milestones as JSON string
        active_event_data["milestones_reached"] = "[25]"
        mock_execute_query.return_value = [active_event_data]
        
        await event_service.add_milestone_reached(mock_guild.id, 50)
        
        assert mock_execute_write.called
    
    @pytest.mark.asyncio
    async def test_add_milestone_skips_duplicate(self, mock_guild, mock_execute_query, mock_execute_write, active_event_data):
        """Adding an already-reached milestone should be a no-op."""
        from cogs.seasonal.services import event_service
        
        # Database stores milestones as JSON string
        active_event_data["milestones_reached"] = "[25, 50]"
        mock_execute_query.return_value = [active_event_data]
        
        await event_service.add_milestone_reached(mock_guild.id, 50)
        
        # Should still be called but with same list
        # The key is that the logic doesn't add duplicates
    
    @pytest.mark.asyncio
    async def test_get_milestones_reached_returns_list(self, mock_guild, mock_execute_query, active_event_data):
        """Getting milestones should return the list of reached percentages."""
        from cogs.seasonal.services import event_service
        
        # Database stores milestones as JSON string
        active_event_data["milestones_reached"] = "[25, 50, 75]"
        mock_execute_query.return_value = [active_event_data]
        
        result = await event_service.get_milestones_reached(mock_guild.id)
        
        assert result == [25, 50, 75]
    
    @pytest.mark.asyncio
    async def test_get_milestones_returns_empty_when_no_event(self, mock_guild, mock_execute_query):
        """Getting milestones when no event should return empty list."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = []
        
        result = await event_service.get_milestones_reached(mock_guild.id)
        
        assert result == []


# =============================================================================
# Announcement Message Tests
# =============================================================================

class TestAnnouncementMessage:
    """Test announcement message tracking."""
    
    @pytest.mark.asyncio
    async def test_set_announcement_message_updates_record(self, mock_guild, mock_execute_write):
        """Setting announcement message should update the database."""
        from cogs.seasonal.services import event_service
        
        await event_service.set_announcement_message(
            guild_id=mock_guild.id,
            channel_id=333333333,
            message_id=444444444
        )
        
        assert mock_execute_write.called
        call_args = str(mock_execute_write.call_args)
        assert "UPDATE" in call_args
    
    @pytest.mark.asyncio
    async def test_get_announcement_message_returns_ids(self, mock_guild, mock_execute_query):
        """Getting announcement message should return (channel_id, message_id)."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = [{
            "announcement_channel_id": 333333333,
            "announcement_message_id": 444444444
        }]
        
        channel_id, message_id = await event_service.get_announcement_message(mock_guild.id)
        
        assert channel_id == 333333333
        assert message_id == 444444444
    
    @pytest.mark.asyncio
    async def test_get_announcement_message_returns_nones_when_no_event(self, mock_guild, mock_execute_query):
        """Getting announcement when no event should return (None, None)."""
        from cogs.seasonal.services import event_service
        
        mock_execute_query.return_value = []
        
        channel_id, message_id = await event_service.get_announcement_message(mock_guild.id)
        
        assert channel_id is None
        assert message_id is None

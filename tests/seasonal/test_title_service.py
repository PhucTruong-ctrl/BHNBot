"""Tests for title_service.py - Title unlock and management."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestUnlockTitle:
    """Tests for unlock_title function."""

    @pytest.mark.asyncio
    async def test_unlock_title_success(self):
        """Test successfully unlocking a title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.title_service.execute_write", new_callable=AsyncMock) as mock_write:
                mock_query.return_value = []  # No existing title
                mock_write.return_value = None

                from cogs.seasonal.services import title_service

                result = await title_service.unlock_title(
                    user_id=12345,
                    title_key="master_fisher",
                    title_name="Master Fisher",
                    source="quest_reward"
                )

                assert result is True
                mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlock_title_already_owned(self):
        """Test unlocking a title user already has."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"exists": 1}]  # Title already exists

            from cogs.seasonal.services import title_service

            result = await title_service.unlock_title(
                user_id=12345,
                title_key="master_fisher",
                title_name="Master Fisher",
                source="quest_reward"
            )

            assert result is False


class TestGetUserTitles:
    """Tests for get_user_titles function."""

    @pytest.mark.asyncio
    async def test_get_user_titles_returns_list(self):
        """Test getting all titles for a user."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [
                {"title_key": "master_fisher", "title_name": "Master Fisher", "source": "quest"},
                {"title_key": "event_champion", "title_name": "Event Champion", "source": "milestone"},
            ]

            from cogs.seasonal.services import title_service

            result = await title_service.get_user_titles(user_id=12345)

            assert len(result) == 2
            assert result[0]["title_key"] == "master_fisher"

    @pytest.mark.asyncio
    async def test_get_user_titles_empty(self):
        """Test getting titles for user with none."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            from cogs.seasonal.services import title_service

            result = await title_service.get_user_titles(user_id=12345)

            assert result == []


class TestHasTitle:
    """Tests for has_title function."""

    @pytest.mark.asyncio
    async def test_has_title_true(self):
        """Test checking user has a specific title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"title_key": "master_fisher"}]

            from cogs.seasonal.services import title_service

            result = await title_service.has_title(user_id=12345, title_key="master_fisher")

            assert result is True

    @pytest.mark.asyncio
    async def test_has_title_false(self):
        """Test checking user doesn't have a title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            from cogs.seasonal.services import title_service

            result = await title_service.has_title(user_id=12345, title_key="master_fisher")

            assert result is False


class TestActiveTitle:
    """Tests for active title management."""

    @pytest.mark.asyncio
    async def test_get_active_title(self):
        """Test getting user's active title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"active_title": "master_fisher"}]

            from cogs.seasonal.services import title_service

            result = await title_service.get_active_title(user_id=12345)

            assert result == "master_fisher"

    @pytest.mark.asyncio
    async def test_get_active_title_none(self):
        """Test getting active title when none set."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            from cogs.seasonal.services import title_service

            result = await title_service.get_active_title(user_id=12345)

            assert result is None

    @pytest.mark.asyncio
    async def test_set_active_title_success(self):
        """Test setting active title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.title_service.execute_write", new_callable=AsyncMock) as mock_write:
                # User has the title
                mock_query.return_value = [{"title_key": "master_fisher"}]
                mock_write.return_value = None

                from cogs.seasonal.services import title_service

                result = await title_service.set_active_title(user_id=12345, title_key="master_fisher")

                assert result is True

    @pytest.mark.asyncio
    async def test_clear_active_title(self):
        """Test clearing active title."""
        with patch("cogs.seasonal.services.title_service.execute_write", new_callable=AsyncMock) as mock_write:
            mock_write.return_value = None

            from cogs.seasonal.services import title_service

            # Should not raise
            await title_service.clear_active_title(user_id=12345)

            mock_write.assert_called_once()


class TestGetTitleDisplay:
    """Tests for get_title_display function."""

    @pytest.mark.asyncio
    async def test_get_title_display_with_active(self):
        """Test getting display name for active title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            # First call: get_active_title query
            # Second call: get title_name
            mock_query.side_effect = [
                [{"active_title": "master_fisher"}],  # get_active_title
                [{"title_name": "Master Fisher"}],    # get title display name
            ]

            from cogs.seasonal.services import title_service

            result = await title_service.get_title_display(user_id=12345)

            assert result == "Master Fisher"

    @pytest.mark.asyncio
    async def test_get_title_display_no_active(self):
        """Test getting display when no active title."""
        with patch("cogs.seasonal.services.title_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []  # No active title

            from cogs.seasonal.services import title_service

            result = await title_service.get_title_display(user_id=12345)

            assert result is None

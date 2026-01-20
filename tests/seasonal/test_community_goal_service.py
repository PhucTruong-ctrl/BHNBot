"""Tests for community_goal_service.py - Community goals and milestones."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestMilestoneDataclass:
    """Tests for Milestone dataclass."""

    def test_milestone_creation(self):
        """Test creating a Milestone instance."""
        from cogs.seasonal.services.community_goal_service import Milestone

        milestone = Milestone(
            percentage=50,
            title_key="halfway_hero",
            currency_bonus=100,
            description="Halfway there!"
        )

        assert milestone.percentage == 50
        assert milestone.title_key == "halfway_hero"
        assert milestone.currency_bonus == 100

    def test_milestone_optional_fields(self):
        """Test Milestone with optional fields as None."""
        from cogs.seasonal.services.community_goal_service import Milestone

        milestone = Milestone(
            percentage=25,
            title_key=None,
            currency_bonus=50,
            description="Quarter done"
        )

        assert milestone.title_key is None


class TestCommunityGoalStatus:
    """Tests for CommunityGoalStatus dataclass."""

    def test_status_creation(self):
        """Test creating a CommunityGoalStatus instance."""
        from cogs.seasonal.services.community_goal_service import CommunityGoalStatus, Milestone

        milestones = [
            Milestone(25, None, 50, "25%"),
            Milestone(50, "half_hero", 100, "50%"),
        ]

        status = CommunityGoalStatus(
            goal_type="fish_caught",
            goal_target=10000,
            current_progress=2500,
            percentage=25.0,
            milestones=milestones,
            reached_milestones=[25],
            next_milestone=milestones[1]
        )

        assert status.goal_type == "fish_caught"
        assert status.percentage == 25.0
        assert len(status.reached_milestones) == 1

    def test_status_no_next_milestone(self):
        """Test status when all milestones reached."""
        from cogs.seasonal.services.community_goal_service import CommunityGoalStatus

        status = CommunityGoalStatus(
            goal_type="fish_caught",
            goal_target=10000,
            current_progress=10000,
            percentage=100.0,
            milestones=[],
            reached_milestones=[25, 50, 75, 100],
            next_milestone=None
        )

        assert status.next_milestone is None
        assert status.percentage == 100.0


class TestGetCommunityGoalStatus:
    """Tests for get_community_goal_status function."""

    @pytest.mark.asyncio
    async def test_get_status_no_event(self):
        """Test getting status when event doesn't exist."""
        with patch("cogs.seasonal.services.community_goal_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            from cogs.seasonal.services import community_goal_service

            status = await community_goal_service.get_community_goal_status(
                guild_id=111,
                event_id="nonexistent"
            )

            assert status is None

    @pytest.mark.asyncio
    async def test_get_status_with_progress(self):
        """Test getting goal status with existing progress."""
        from cogs.seasonal.services.community_goal_service import Milestone

        with patch("cogs.seasonal.services.community_goal_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.community_goal_service._load_event_milestones") as mock_load:
                with patch("cogs.seasonal.services.community_goal_service.get_community_progress", new_callable=AsyncMock) as mock_progress:
                    with patch("cogs.seasonal.services.community_goal_service.get_milestones_reached", new_callable=AsyncMock) as mock_reached:
                        mock_query.return_value = [{"event_type": "spring"}]
                        mock_load.return_value = (
                            {"type": "fish_caught", "target": 10000},
                            [Milestone(25, None, 50, "25%"), Milestone(50, "half", 100, "50%")]
                        )
                        mock_progress.return_value = 5000
                        mock_reached.return_value = [25]

                        from cogs.seasonal.services import community_goal_service

                        status = await community_goal_service.get_community_goal_status(
                            guild_id=111,
                            event_id="evt_123"
                        )

                        assert status is not None
                        assert status.percentage == 50.0
                        assert status.current_progress == 5000


class TestAddCommunityContribution:
    """Tests for add_community_contribution function."""

    @pytest.mark.asyncio
    async def test_add_contribution_no_milestone(self):
        """Test adding contribution that doesn't cross a milestone."""
        from cogs.seasonal.services.community_goal_service import Milestone

        with patch("cogs.seasonal.services.community_goal_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.community_goal_service._load_event_milestones") as mock_load:
                with patch("cogs.seasonal.services.community_goal_service.get_community_progress", new_callable=AsyncMock) as mock_progress:
                    with patch("cogs.seasonal.services.community_goal_service.get_milestones_reached", new_callable=AsyncMock) as mock_reached:
                        with patch("cogs.seasonal.services.community_goal_service.update_community_progress", new_callable=AsyncMock):
                            # Before: 1000/10000 = 10%
                            # After:  1010/10000 = 10.1%
                            mock_query.return_value = [{"event_type": "spring"}]
                            mock_load.return_value = (
                                {"type": "fish_caught", "target": 10000},
                                [Milestone(25, None, 50, "25%")]
                            )
                            mock_progress.return_value = 1000
                            mock_reached.return_value = []

                            from cogs.seasonal.services import community_goal_service

                            crossed = await community_goal_service.add_community_contribution(
                                guild_id=111,
                                event_id="evt_123",
                                amount=10
                            )

                            assert crossed == []

    @pytest.mark.asyncio
    async def test_add_contribution_crosses_milestone(self):
        """Test adding contribution that crosses a milestone."""
        from cogs.seasonal.services.community_goal_service import Milestone

        milestone_25 = Milestone(25, "quarter", 50, "25%")

        with patch("cogs.seasonal.services.community_goal_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.community_goal_service._load_event_milestones") as mock_load:
                with patch("cogs.seasonal.services.community_goal_service.get_community_progress", new_callable=AsyncMock) as mock_progress:
                    with patch("cogs.seasonal.services.community_goal_service.get_milestones_reached", new_callable=AsyncMock) as mock_reached:
                        with patch("cogs.seasonal.services.community_goal_service.update_community_progress", new_callable=AsyncMock):
                            with patch("cogs.seasonal.services.community_goal_service.add_milestone_reached", new_callable=AsyncMock):
                                # Before: 2400/10000 = 24%
                                # After adding 200: 2600/10000 = 26% -> crosses 25%
                                mock_query.return_value = [{"event_type": "spring"}]
                                mock_load.return_value = (
                                    {"type": "fish_caught", "target": 10000},
                                    [milestone_25, Milestone(50, "half", 100, "50%")]
                                )
                                mock_progress.return_value = 2400
                                mock_reached.return_value = []

                                from cogs.seasonal.services import community_goal_service

                                crossed = await community_goal_service.add_community_contribution(
                                    guild_id=111,
                                    event_id="evt_123",
                                    amount=200
                                )

                                assert len(crossed) == 1
                                assert crossed[0].percentage == 25


class TestDistributeMilestoneRewards:
    """Tests for distribute_milestone_rewards function."""

    @pytest.mark.asyncio
    async def test_distribute_rewards_no_participants(self):
        """Test distributing when no participants."""
        from cogs.seasonal.services.community_goal_service import Milestone

        with patch("cogs.seasonal.services.community_goal_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            from cogs.seasonal.services import community_goal_service

            milestone = Milestone(50, None, 100, "50%")

            rewarded = await community_goal_service.distribute_milestone_rewards(
                guild_id=111,
                event_id="evt_123",
                milestone=milestone
            )

            assert rewarded == []

    @pytest.mark.asyncio
    async def test_distribute_rewards_to_participants(self):
        """Test distributing milestone rewards to all participants."""
        from cogs.seasonal.services.community_goal_service import Milestone

        with patch("cogs.seasonal.services.participation_service.get_participants", new_callable=AsyncMock) as mock_participants:
            with patch("cogs.seasonal.services.community_goal_service.add_currency", new_callable=AsyncMock):
                mock_participants.return_value = [
                    {"user_id": 111},
                    {"user_id": 222},
                    {"user_id": 333},
                ]

                from cogs.seasonal.services import community_goal_service

                milestone = Milestone(
                    percentage=50,
                    title_key=None,
                    currency_bonus=100,
                    description="50% complete!"
                )

                rewarded = await community_goal_service.distribute_milestone_rewards(
                    guild_id=111,
                    event_id="evt_123",
                    milestone=milestone
                )

                assert len(rewarded) == 3


class TestMilestoneTracking:
    """Tests for milestone tracking in database."""

    @pytest.mark.asyncio
    async def test_already_reached_milestones_not_recrossed(self):
        """Test that already reached milestones aren't triggered again."""
        from cogs.seasonal.services.community_goal_service import Milestone

        milestone_25 = Milestone(25, None, 50, "25%")
        milestone_50 = Milestone(50, "half", 100, "50%")

        with patch("cogs.seasonal.services.community_goal_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.community_goal_service._load_event_milestones") as mock_load:
                with patch("cogs.seasonal.services.community_goal_service.get_community_progress", new_callable=AsyncMock) as mock_progress:
                    with patch("cogs.seasonal.services.community_goal_service.get_milestones_reached", new_callable=AsyncMock) as mock_reached:
                        with patch("cogs.seasonal.services.community_goal_service.update_community_progress", new_callable=AsyncMock):
                            # Already at 30%, 25% was already reached
                            mock_query.return_value = [{"event_type": "spring"}]
                            mock_load.return_value = (
                                {"type": "fish_caught", "target": 10000},
                                [milestone_25, milestone_50]
                            )
                            mock_progress.return_value = 3000  # 30%
                            mock_reached.return_value = [25]  # 25% already reached

                            from cogs.seasonal.services import community_goal_service

                            # Add more but stay below 50%
                            crossed = await community_goal_service.add_community_contribution(
                                guild_id=111,
                                event_id="evt_123",
                                amount=500  # 35% now
                            )

                            # 25% already reached, shouldn't be in crossed list
                            assert 25 not in [m.percentage for m in crossed]

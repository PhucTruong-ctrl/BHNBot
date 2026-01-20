"""Tests for shop_service.py - Event shop and purchases."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestShopItem:
    """Tests for ShopItem dataclass."""

    def test_shop_item_creation(self):
        """Test creating a ShopItem instance."""
        from cogs.seasonal.services.shop_service import ShopItem

        item = ShopItem(
            key="rod_upgrade",
            name="Rod Upgrade",
            description="Upgrade your fishing rod",
            price=100,
            emoji="🎣",
            category="equipment",
            stock=None,
            limit_per_user=None,
            requires_title=None
        )

        assert item.key == "rod_upgrade"
        assert item.price == 100


class TestPurchaseResult:
    """Tests for PurchaseResult dataclass."""

    def test_purchase_result_success(self):
        """Test creating a successful purchase result."""
        from cogs.seasonal.services.shop_service import PurchaseResult

        result = PurchaseResult(
            success=True,
            message="Purchase successful",
            item=MagicMock(name="Test Item"),
            new_balance=400
        )

        assert result.success is True
        assert result.new_balance == 400

    def test_purchase_result_failure(self):
        """Test creating a failed purchase result."""
        from cogs.seasonal.services.shop_service import PurchaseResult

        result = PurchaseResult(
            success=False,
            message="Insufficient funds"
        )

        assert result.success is False
        assert result.item is None


class TestGetUserPurchaseCount:
    """Tests for get_user_purchase_count function."""

    @pytest.mark.asyncio
    async def test_get_purchase_count_with_purchases(self):
        """Test getting purchase count for user with purchases."""
        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"total": 3}]

            from cogs.seasonal.services import shop_service

            count = await shop_service.get_user_purchase_count(
                guild_id=111,
                user_id=222,
                event_id="evt_123",
                item_key="rod_upgrade"
            )

            assert count == 3

    @pytest.mark.asyncio
    async def test_get_purchase_count_no_purchases(self):
        """Test getting purchase count for user with no purchases."""
        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"total": 0}]

            from cogs.seasonal.services import shop_service

            count = await shop_service.get_user_purchase_count(
                guild_id=111,
                user_id=222,
                event_id="evt_123",
                item_key="rod_upgrade"
            )

            assert count == 0


class TestGetGlobalStockRemaining:
    """Tests for get_global_stock_remaining function."""

    @pytest.mark.asyncio
    async def test_stock_remaining_with_purchases(self):
        """Test calculating remaining stock."""
        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            # 7 total purchased
            mock_query.return_value = [{"total": 7}]

            from cogs.seasonal.services import shop_service

            remaining = await shop_service.get_global_stock_remaining(
                guild_id=111,
                event_id="evt_123",
                item_key="limited_item",
                max_stock=10
            )

            assert remaining == 3

    @pytest.mark.asyncio
    async def test_stock_remaining_unlimited(self):
        """Test stock for unlimited items returns None."""
        from cogs.seasonal.services import shop_service

        remaining = await shop_service.get_global_stock_remaining(
            guild_id=111,
            event_id="evt_123",
            item_key="unlimited_item",
            max_stock=None
        )

        assert remaining is None


class TestPurchaseItem:
    """Tests for purchase_item function."""

    @pytest.mark.asyncio
    async def test_purchase_item_not_found(self):
        """Test purchasing non-existent item."""
        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.shop_service._load_shop_items") as mock_load:
                mock_load.return_value = []
                mock_query.return_value = [{"event_type": "spring"}]

                from cogs.seasonal.services import shop_service

                result = await shop_service.purchase_item(
                    guild_id=111,
                    user_id=222,
                    event_id="evt_123",
                    item_key="nonexistent"
                )

                assert result.success is False

    @pytest.mark.asyncio
    async def test_purchase_success_basic(self):
        """Test successful basic item purchase."""
        from cogs.seasonal.services.shop_service import ShopItem

        mock_item = ShopItem(
            key="bait",
            name="Bait Pack",
            description="Basic bait",
            price=50,
            emoji="🪱",
            category="consumable",
            stock=None,
            limit_per_user=None,
            requires_title=None
        )

        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.shop_service.execute_write", new_callable=AsyncMock) as mock_write:
                with patch("cogs.seasonal.services.shop_service._load_shop_items") as mock_load:
                    with patch("cogs.seasonal.services.shop_service.get_currency", new_callable=AsyncMock) as mock_currency:
                        with patch("cogs.seasonal.services.shop_service.spend_currency", new_callable=AsyncMock) as mock_spend:
                            mock_load.return_value = [mock_item]
                            mock_query.return_value = [{"event_type": "spring"}]
                            mock_currency.return_value = 500  # Has enough
                            mock_spend.return_value = True

                            from cogs.seasonal.services import shop_service

                            result = await shop_service.purchase_item(
                                guild_id=111,
                                user_id=222,
                                event_id="evt_123",
                                item_key="bait"
                            )

                            assert result.success is True
                            assert result.item.key == "bait"

    @pytest.mark.asyncio
    async def test_purchase_insufficient_balance(self):
        """Test purchasing with insufficient balance."""
        from cogs.seasonal.services.shop_service import ShopItem

        mock_item = ShopItem(
            key="expensive",
            name="Expensive Item",
            description="Very expensive",
            price=1000,
            emoji="💎",
            category="rare",
            stock=None,
            limit_per_user=None,
            requires_title=None
        )

        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.shop_service._load_shop_items") as mock_load:
                with patch("cogs.seasonal.services.shop_service.get_currency", new_callable=AsyncMock) as mock_currency:
                    mock_load.return_value = [mock_item]
                    mock_query.return_value = [{"event_type": "spring"}]
                    mock_currency.return_value = 100  # Only 100, need 1000

                    from cogs.seasonal.services import shop_service

                    result = await shop_service.purchase_item(
                        guild_id=111,
                        user_id=222,
                        event_id="evt_123",
                        item_key="expensive"
                    )

                    assert result.success is False

    @pytest.mark.asyncio
    async def test_purchase_requires_title_not_owned(self):
        """Test purchasing item that requires a title user doesn't have."""
        from cogs.seasonal.services.shop_service import ShopItem

        mock_item = ShopItem(
            key="vip_item",
            name="VIP Item",
            description="VIP only",
            price=100,
            emoji="👑",
            category="vip",
            stock=None,
            limit_per_user=None,
            requires_title="vip_member"
        )

        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.shop_service._load_shop_items") as mock_load:
                with patch("cogs.seasonal.services.shop_service.get_currency", new_callable=AsyncMock) as mock_currency:
                    mock_load.return_value = [mock_item]
                    mock_query.return_value = [{"event_type": "spring"}]
                    mock_currency.return_value = 500

                    from cogs.seasonal.services import shop_service

                    result = await shop_service.purchase_item(
                        guild_id=111,
                        user_id=222,
                        event_id="evt_123",
                        item_key="vip_item",
                        user_titles=[]  # No titles
                    )

                    assert result.success is False

    @pytest.mark.asyncio
    async def test_purchase_limit_exceeded(self):
        """Test purchasing when user limit exceeded."""
        from cogs.seasonal.services.shop_service import ShopItem

        mock_item = ShopItem(
            key="limited",
            name="Limited Item",
            description="Max 2 per user",
            price=100,
            emoji="⭐",
            category="limited",
            stock=None,
            limit_per_user=2,  # Max 2 per user
            requires_title=None
        )

        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.shop_service._load_shop_items") as mock_load:
                with patch("cogs.seasonal.services.shop_service.get_currency", new_callable=AsyncMock) as mock_currency:
                    with patch("cogs.seasonal.services.shop_service.get_user_purchase_count", new_callable=AsyncMock) as mock_count:
                        mock_load.return_value = [mock_item]
                        mock_query.return_value = [{"event_type": "spring"}]
                        mock_currency.return_value = 500
                        mock_count.return_value = 2  # Already bought max

                        from cogs.seasonal.services import shop_service

                        result = await shop_service.purchase_item(
                            guild_id=111,
                            user_id=222,
                            event_id="evt_123",
                            item_key="limited"
                        )

                        assert result.success is False

    @pytest.mark.asyncio
    async def test_purchase_out_of_stock(self):
        """Test purchasing when global stock exhausted."""
        from cogs.seasonal.services.shop_service import ShopItem

        mock_item = ShopItem(
            key="rare",
            name="Rare Item",
            description="Limited stock",
            price=100,
            emoji="💫",
            category="rare",
            stock=10,  # Global limit of 10
            limit_per_user=None,
            requires_title=None
        )

        with patch("cogs.seasonal.services.shop_service.execute_query", new_callable=AsyncMock) as mock_query:
            with patch("cogs.seasonal.services.shop_service._load_shop_items") as mock_load:
                with patch("cogs.seasonal.services.shop_service.get_currency", new_callable=AsyncMock) as mock_currency:
                    with patch("cogs.seasonal.services.shop_service.get_global_stock_remaining", new_callable=AsyncMock) as mock_stock:
                        mock_load.return_value = [mock_item]
                        mock_query.return_value = [{"event_type": "spring"}]
                        mock_currency.return_value = 500
                        mock_stock.return_value = 0  # Out of stock

                        from cogs.seasonal.services import shop_service

                        result = await shop_service.purchase_item(
                            guild_id=111,
                            user_id=222,
                            event_id="evt_123",
                            item_key="rare"
                        )

                        assert result.success is False

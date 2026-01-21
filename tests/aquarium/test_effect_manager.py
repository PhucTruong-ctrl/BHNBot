"""
Unit tests for EffectManager and SetsDataLoader.

Tests the aquarium set effects system including:
- SetsDataLoader: JSON loading and caching
- EffectManager: multiplier calculations, set activation, charm calculations

Uses pytest with mocked database to avoid real DB connections.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Import the modules under test
from cogs.aquarium.logic.effect_manager import (
    SetsDataLoader,
    EffectManager,
    EffectType,
    get_effect_manager,
    SETS_JSON_PATH,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_sets_data():
    """Sample sets.json structure for testing."""
    return {
        "sets": {
            "hai_duong_cung": {
                "name": "Hải Dương Cung",
                "icon": "🌊",
                "tier": 1,
                "activity": "fishing",
                "required_pieces": 2,
                "effects": {
                    "catch_rate_bonus": 0.05
                },
                "items": ["hdc_01", "hdc_02", "hdc_03", "hdc_04"]
            },
            "au_lac_thanh": {
                "name": "Âu Lạc Thành",
                "icon": "🏛️",
                "tier": 3,
                "activity": "global",
                "required_pieces": 2,
                "effects": {
                    "all_bonus": 0.05
                },
                "items": ["alt_01", "alt_02", "alt_03", "alt_04"]
            },
            "bach_van_trai": {
                "name": "Bạch Vân Trại",
                "icon": "☁️",
                "tier": 1,
                "activity": "passive",
                "required_pieces": 2,
                "effects": {
                    "passive_income": 50
                },
                "items": ["bvt_01", "bvt_02", "bvt_03", "bvt_04"]
            }
        },
        "items": {
            "hdc_01": {
                "name": "Đèn Lồng Biển",
                "icon": "🏮",
                "desc": "Đèn lồng thắp sáng",
                "type": "decoration",
                "price_seeds": 1000,
                "price_leaf": 0,
                "charm": 10,
                "set_id": "hai_duong_cung"
            },
            "hdc_02": {
                "name": "San Hô Xanh",
                "icon": "🪸",
                "desc": "San hô đẹp",
                "type": "decoration",
                "price_seeds": 1000,
                "price_leaf": 0,
                "charm": 10,
                "set_id": "hai_duong_cung"
            },
            "hdc_03": {
                "name": "Vỏ Sò Ngọc",
                "icon": "🐚",
                "desc": "Vỏ sò quý",
                "type": "decoration",
                "price_seeds": 1200,
                "price_leaf": 0,
                "charm": 12,
                "set_id": "hai_duong_cung"
            },
            "bvt_01": {
                "name": "Mây Trắng",
                "icon": "☁️",
                "desc": "Mây nhẹ",
                "type": "decoration",
                "price_seeds": 800,
                "price_leaf": 0,
                "charm": 8,
                "set_id": "bach_van_trai"
            },
            "bvt_02": {
                "name": "Sương Mai",
                "icon": "💧",
                "desc": "Sương sớm",
                "type": "decoration",
                "price_seeds": 800,
                "price_leaf": 0,
                "charm": 8,
                "set_id": "bach_van_trai"
            },
            "alt_01": {
                "name": "Cột Đồng",
                "icon": "🏛️",
                "desc": "Cột cổ",
                "type": "decoration",
                "price_seeds": 5000,
                "price_leaf": 0,
                "charm": 25,
                "set_id": "au_lac_thanh"
            },
            "alt_02": {
                "name": "Trống Đồng",
                "icon": "🥁",
                "desc": "Trống thiêng",
                "type": "decoration",
                "price_seeds": 5000,
                "price_leaf": 0,
                "charm": 25,
                "set_id": "au_lac_thanh"
            }
        }
    }


@pytest.fixture
def reset_sets_cache():
    """Reset SetsDataLoader cache before each test."""
    SetsDataLoader._cache = None
    yield
    SetsDataLoader._cache = None


# =============================================================================
# SetsDataLoader Tests
# =============================================================================

class TestSetsDataLoader:
    """Tests for the SetsDataLoader class."""
    
    def test_load_returns_empty_on_missing_file(self, reset_sets_cache):
        """Should return empty structure if JSON file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = SetsDataLoader.load()
            assert result == {"sets": {}, "items": {}}
    
    def test_load_caches_data(self, reset_sets_cache, sample_sets_data):
        """Should cache data after first load."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(sample_sets_data)
                with patch("json.load", return_value=sample_sets_data):
                    # First load
                    result1 = SetsDataLoader.load()
                    # Second load (should use cache)
                    result2 = SetsDataLoader.load()
                    
                    assert result1 == result2
                    assert SetsDataLoader._cache is not None
    
    def test_get_sets_returns_sets_dict(self, reset_sets_cache, sample_sets_data):
        """Should return the 'sets' portion of the data."""
        SetsDataLoader._cache = sample_sets_data
        
        sets = SetsDataLoader.get_sets()
        
        assert "hai_duong_cung" in sets
        assert "au_lac_thanh" in sets
        assert len(sets) == 3
    
    def test_get_items_returns_items_dict(self, reset_sets_cache, sample_sets_data):
        """Should return the 'items' portion of the data."""
        SetsDataLoader._cache = sample_sets_data
        
        items = SetsDataLoader.get_items()
        
        assert "hdc_01" in items
        assert "bvt_01" in items
        assert len(items) == 7
    
    def test_get_set_returns_specific_set(self, reset_sets_cache, sample_sets_data):
        """Should return a specific set by ID."""
        SetsDataLoader._cache = sample_sets_data
        
        set_data = SetsDataLoader.get_set("hai_duong_cung")
        
        assert set_data is not None
        assert set_data["name"] == "Hải Dương Cung"
        assert set_data["tier"] == 1
    
    def test_get_set_returns_none_for_missing(self, reset_sets_cache, sample_sets_data):
        """Should return None for non-existent set."""
        SetsDataLoader._cache = sample_sets_data
        
        result = SetsDataLoader.get_set("nonexistent_set")
        
        assert result is None
    
    def test_get_item_returns_specific_item(self, reset_sets_cache, sample_sets_data):
        """Should return a specific item by ID."""
        SetsDataLoader._cache = sample_sets_data
        
        item = SetsDataLoader.get_item("hdc_01")
        
        assert item is not None
        assert item["name"] == "Đèn Lồng Biển"
        assert item["charm"] == 10
        assert item["set_id"] == "hai_duong_cung"
    
    def test_reload_clears_cache(self, reset_sets_cache, sample_sets_data):
        """Should clear cache when reload is called."""
        SetsDataLoader._cache = sample_sets_data
        
        with patch("os.path.exists", return_value=False):
            SetsDataLoader.reload()
        
        # After reload with missing file, cache should be empty structure
        assert SetsDataLoader._cache == {"sets": {}, "items": {}}


# =============================================================================
# EffectManager Tests
# =============================================================================

class TestEffectManager:
    """Tests for the EffectManager class."""
    
    @pytest.fixture
    def effect_manager(self, reset_sets_cache, sample_sets_data):
        """Create an EffectManager with mocked data."""
        SetsDataLoader._cache = sample_sets_data
        return EffectManager()
    
    @pytest.mark.asyncio
    async def test_get_placed_items_returns_list(self, effect_manager):
        """Should return a list of 5 elements for home slots."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="hdc_01"),
            MagicMock(slot_index=1, item_id="hdc_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_placed_items(user_id=123)
            
            assert len(result) == 5
            assert result[0] == "hdc_01"
            assert result[1] == "hdc_02"
            assert result[2] is None
    
    @pytest.mark.asyncio
    async def test_get_active_sets_no_items(self, effect_manager):
        """Should return empty list when no items are placed."""
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=[])
            
            result = await effect_manager.get_active_sets(user_id=123)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_active_sets_with_2_piece_bonus(self, effect_manager):
        """Should activate set when user has 2+ pieces from same set."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="hdc_01"),
            MagicMock(slot_index=1, item_id="hdc_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_active_sets(user_id=123)
            
            assert len(result) == 1
            assert result[0]["id"] == "hai_duong_cung"
            assert result[0]["active_pieces"] == 2
    
    @pytest.mark.asyncio
    async def test_get_active_sets_needs_2_pieces(self, effect_manager):
        """Should not activate set with only 1 piece."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="hdc_01"),  # Only 1 piece
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_active_sets(user_id=123)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_multiplier_no_bonus(self, effect_manager):
        """Should return 1.0 when no set is active."""
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=[])
            
            result = await effect_manager.get_multiplier(user_id=123, effect_type="catch_rate_bonus")
            
            assert result == 1.0
    
    @pytest.mark.asyncio
    async def test_get_multiplier_with_bonus(self, effect_manager):
        """Should return 1.0 + bonus when set is active."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="hdc_01"),
            MagicMock(slot_index=1, item_id="hdc_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_multiplier(user_id=123, effect_type="catch_rate_bonus")
            
            # hai_duong_cung gives catch_rate_bonus: 0.05
            assert result == 1.05
    
    @pytest.mark.asyncio
    async def test_get_multiplier_with_all_bonus(self, effect_manager):
        """Should add all_bonus to other multipliers."""
        # Place 2 pieces of au_lac_thanh (all_bonus: 0.05) + 2 pieces of hai_duong_cung
        mock_slots = [
            MagicMock(slot_index=0, item_id="alt_01"),
            MagicMock(slot_index=1, item_id="alt_02"),
            MagicMock(slot_index=2, item_id="hdc_01"),
            MagicMock(slot_index=3, item_id="hdc_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_multiplier(user_id=123, effect_type="catch_rate_bonus")
            
            # catch_rate_bonus: 0.05 + all_bonus: 0.05 = 1.10
            assert result == 1.10
    
    @pytest.mark.asyncio
    async def test_get_flat_bonus_passive_income(self, effect_manager):
        """Should return flat passive_income value."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="bvt_01"),
            MagicMock(slot_index=1, item_id="bvt_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_flat_bonus(user_id=123, effect_type="passive_income")
            
            # bach_van_trai gives passive_income: 50
            assert result == 50
    
    @pytest.mark.asyncio
    async def test_get_total_passive_income(self, effect_manager):
        """Convenience method should return int."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="bvt_01"),
            MagicMock(slot_index=1, item_id="bvt_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_total_passive_income(user_id=123)
            
            assert result == 50
            assert isinstance(result, int)
    
    @pytest.mark.asyncio
    async def test_get_user_charm(self, effect_manager):
        """Should sum charm values from placed items."""
        mock_slots = [
            MagicMock(slot_index=0, item_id="hdc_01"),  # charm: 10
            MagicMock(slot_index=1, item_id="hdc_02"),  # charm: 10
            MagicMock(slot_index=2, item_id="hdc_03"),  # charm: 12
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            result = await effect_manager.get_user_charm(user_id=123)
            
            assert result == 32  # 10 + 10 + 12
    
    @pytest.mark.asyncio
    async def test_get_active_effects_with_activity_filter(self, effect_manager):
        """Should filter effects by activity."""
        # hai_duong_cung is activity: fishing
        mock_slots = [
            MagicMock(slot_index=0, item_id="hdc_01"),
            MagicMock(slot_index=1, item_id="hdc_02"),
        ]
        
        with patch("cogs.aquarium.models.HomeSlot") as MockHomeSlot:
            MockHomeSlot.filter.return_value.all = AsyncMock(return_value=mock_slots)
            
            # Should get effects for fishing activity
            fishing_effects = await effect_manager.get_active_effects(user_id=123, activity="fishing")
            assert "catch_rate_bonus" in fishing_effects
            
            # Should not get effects for harvest activity
            harvest_effects = await effect_manager.get_active_effects(user_id=123, activity="harvest")
            assert "catch_rate_bonus" not in harvest_effects


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for get_effect_manager factory function."""
    
    def test_get_effect_manager_returns_instance(self):
        """Should return an EffectManager instance."""
        manager = get_effect_manager()
        
        assert isinstance(manager, EffectManager)
    
    def test_get_effect_manager_returns_new_instances(self):
        """Should return new instances each call (not singleton)."""
        manager1 = get_effect_manager()
        manager2 = get_effect_manager()
        
        # Not the same instance (factory, not singleton)
        assert manager1 is not manager2


# =============================================================================
# Integration Test with Real JSON
# =============================================================================

class TestRealJSONIntegration:
    """Integration tests using the actual sets.json file."""
    
    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset cache before each test."""
        SetsDataLoader._cache = None
        yield
        SetsDataLoader._cache = None
    
    def test_load_real_json_file(self):
        """Should load the actual sets.json file without errors."""
        # This test uses the real file
        data = SetsDataLoader.load()
        
        # Should have sets and items
        assert "sets" in data
        assert "items" in data
        
        # Should have 18 sets
        assert len(data["sets"]) == 18
        
        # Should have 72 items (4 per set)
        assert len(data["items"]) == 72
    
    def test_all_items_have_valid_set_ids(self):
        """All items should reference valid set IDs."""
        data = SetsDataLoader.load()
        sets = data["sets"]
        items = data["items"]
        
        for item_id, item in items.items():
            set_id = item.get("set_id")
            assert set_id is not None, f"Item {item_id} has no set_id"
            assert set_id in sets, f"Item {item_id} references unknown set {set_id}"
    
    def test_all_sets_have_required_fields(self):
        """All sets should have required fields."""
        data = SetsDataLoader.load()
        required_fields = ["name", "tier", "activity", "effects", "items"]
        
        for set_id, set_data in data["sets"].items():
            for field in required_fields:
                assert field in set_data, f"Set {set_id} missing field: {field}"
    
    def test_all_items_have_required_fields(self):
        """All items should have required fields."""
        data = SetsDataLoader.load()
        required_fields = ["name", "icon", "description", "charm", "set_id"]
        
        for item_id, item_data in data["items"].items():
            for field in required_fields:
                assert field in item_data, f"Item {item_id} missing field: {field}"
    
    def test_sets_have_exactly_4_items(self):
        """Each set should reference exactly 4 items."""
        data = SetsDataLoader.load()
        
        for set_id, set_data in data["sets"].items():
            items = set_data.get("items", [])
            assert len(items) == 4, f"Set {set_id} has {len(items)} items, expected 4"

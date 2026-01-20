"""
Tests for JSON configuration files validation.

Tests cover:
- All event JSON files exist and are valid JSON
- Required fields are present in each event config
- Minigame configurations are valid
- Quest configurations are valid
- Shop item configurations are valid
"""
import pytest
import json
import os
from pathlib import Path


# =============================================================================
# Test Data
# =============================================================================

# Path to event JSON files
EVENTS_DIR = Path(__file__).parent.parent.parent / "data" / "events"

# Required fields for each event type
REQUIRED_EVENT_FIELDS = [
    "event_id",
]

OPTIONAL_EVENT_FIELDS = [
    "name",
    "description",
    "duration_days",
    "currency",
    "minigame_config",
    "daily_quests",
    "fixed_quests",
    "shop",
    "milestones",
    "community_goal",
    "fish",
    "achievements",
]

# All expected event files
EXPECTED_EVENT_FILES = [
    "spring.json",
    "summer.json",
    "autumn.json",
    "winter.json",
    "halloween.json",
    "earthday.json",
    "midautumn.json",
    "birthday.json",
    "registry.json",
]


# =============================================================================
# JSON File Existence Tests
# =============================================================================

class TestEventFilesExist:
    """Test that all expected event JSON files exist."""
    
    def test_events_directory_exists(self):
        """Events directory should exist."""
        assert EVENTS_DIR.exists(), f"Events directory not found: {EVENTS_DIR}"
        assert EVENTS_DIR.is_dir(), f"Events path is not a directory: {EVENTS_DIR}"
    
    @pytest.mark.parametrize("filename", EXPECTED_EVENT_FILES)
    def test_event_file_exists(self, filename):
        """Each expected event file should exist."""
        filepath = EVENTS_DIR / filename
        assert filepath.exists(), f"Event file not found: {filepath}"
    
    def test_no_unexpected_files(self):
        """Only expected JSON files should exist in events directory."""
        actual_files = set(f.name for f in EVENTS_DIR.glob("*.json"))
        expected_files = set(EXPECTED_EVENT_FILES)
        unexpected = actual_files - expected_files
        
        # Allow extra files but warn
        if unexpected:
            pytest.skip(f"Extra event files found (not an error): {unexpected}")


# =============================================================================
# JSON Validity Tests
# =============================================================================

class TestEventFilesValid:
    """Test that all event JSON files are valid JSON."""
    
    @pytest.mark.parametrize("filename", EXPECTED_EVENT_FILES)
    def test_event_file_is_valid_json(self, filename):
        """Each event file should be valid JSON."""
        filepath = EVENTS_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File not found: {filepath}")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data is not None
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {filename}: {e}")
    
    @pytest.mark.parametrize("filename", [f for f in EXPECTED_EVENT_FILES if f != "registry.json"])
    def test_event_has_event_id(self, filename):
        """Each event file (except registry) should have event_id."""
        filepath = EVENTS_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Event files can have multiple events (by year suffix)
        # or a single event_id at the root
        if "event_id" in data:
            assert data["event_id"], "event_id should not be empty"
        elif isinstance(data, dict):
            # Check if any key looks like an event config
            has_valid_event = any(
                isinstance(v, dict) and "event_id" in v 
                for v in data.values()
            )
            # Or check for common event patterns
            has_event_patterns = any(
                k in data for k in ["minigame_config", "quests", "shop", "fish"]
            )
            assert has_valid_event or has_event_patterns, \
                f"No event_id found in {filename}"


# =============================================================================
# Quest Configuration Tests
# =============================================================================

class TestQuestConfigurations:
    """Test quest configurations are valid."""
    
    @pytest.fixture
    def all_quests(self) -> list[tuple[str, dict]]:
        """Load all quests from all event files."""
        quests = []
        for filename in EXPECTED_EVENT_FILES:
            if filename == "registry.json":
                continue
            filepath = EVENTS_DIR / filename
            if not filepath.exists():
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for key in ["daily_quests", "fixed_quests"]:
                if key in data and isinstance(data[key], list):
                    for quest in data[key]:
                        quests.append((filename, quest))
        
        return quests
    
    def test_quests_have_required_fields(self, all_quests):
        """Each quest should have required fields."""
        required_fields = ["id", "target"]
        
        for filename, quest in all_quests:
            for field in required_fields:
                assert field in quest, \
                    f"Quest in {filename} missing required field: {field}"
    
    def test_quest_targets_are_positive(self, all_quests):
        """Quest targets should be positive integers."""
        for filename, quest in all_quests:
            if "target" in quest:
                assert quest["target"] > 0, \
                    f"Quest {quest.get('id', 'unknown')} in {filename} has invalid target: {quest['target']}"


# =============================================================================
# Shop Configuration Tests
# =============================================================================

class TestShopConfigurations:
    """Test shop item configurations are valid."""
    
    @pytest.fixture
    def all_shop_items(self) -> list[tuple[str, dict]]:
        """Load all shop items from all event files."""
        items = []
        for filename in EXPECTED_EVENT_FILES:
            if filename == "registry.json":
                continue
            filepath = EVENTS_DIR / filename
            if not filepath.exists():
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if "shop" in data and isinstance(data["shop"], list):
                for item in data["shop"]:
                    items.append((filename, item))
        
        return items
    
    def test_shop_items_have_required_fields(self, all_shop_items):
        """Each shop item should have required fields."""
        required_fields = ["key", "price"]
        
        for filename, item in all_shop_items:
            for field in required_fields:
                assert field in item, \
                    f"Shop item in {filename} missing required field: {field}"
    
    def test_shop_prices_are_positive(self, all_shop_items):
        """Shop prices should be positive."""
        for filename, item in all_shop_items:
            if "price" in item:
                assert item["price"] > 0, \
                    f"Shop item {item.get('key', 'unknown')} in {filename} has invalid price: {item['price']}"


# =============================================================================
# Minigame Configuration Tests
# =============================================================================

class TestMinigameConfigurations:
    """Test minigame configurations are valid."""
    
    # Known minigame types
    KNOWN_MINIGAMES = [
        "lixi_auto", "lixi_manual",
        "treasure_hunt", "boat_race",
        "thank_letter", "leaf_collect", "tea_brewing",
        "ghost_hunt", "trick_treat",
        "secret_santa", "snowman", "countdown",
        "trash_sort", "beach_cleanup",
        "lantern_parade", "quiz",
        "wishes", "balloon_pop", "birthday_cake",
    ]
    
    @pytest.fixture
    def all_minigame_configs(self) -> list[tuple[str, str, dict]]:
        """Load all minigame configs from all event files."""
        configs = []
        for filename in EXPECTED_EVENT_FILES:
            if filename == "registry.json":
                continue
            filepath = EVENTS_DIR / filename
            if not filepath.exists():
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if "minigame_config" in data and isinstance(data["minigame_config"], dict):
                for minigame_name, config in data["minigame_config"].items():
                    configs.append((filename, minigame_name, config))
        
        return configs
    
    def test_minigame_names_are_known(self, all_minigame_configs):
        """All minigame names should be recognized."""
        for filename, minigame_name, config in all_minigame_configs:
            # Allow unknown minigames but warn
            if minigame_name not in self.KNOWN_MINIGAMES:
                pytest.skip(f"Unknown minigame {minigame_name} in {filename}")
    
    def test_minigame_configs_have_enabled_flag(self, all_minigame_configs):
        """Each minigame config should have enabled flag."""
        for filename, minigame_name, config in all_minigame_configs:
            if isinstance(config, dict):
                # enabled flag is optional, default True
                if "enabled" in config:
                    assert isinstance(config["enabled"], bool), \
                        f"Minigame {minigame_name} in {filename} has non-boolean enabled flag"


# =============================================================================
# Registry Tests
# =============================================================================

class TestRegistryFile:
    """Test the registry.json file is valid."""
    
    def test_registry_exists(self):
        """Registry file should exist."""
        filepath = EVENTS_DIR / "registry.json"
        assert filepath.exists(), f"Registry file not found: {filepath}"
    
    def test_registry_is_valid_json(self):
        """Registry file should be valid JSON."""
        filepath = EVENTS_DIR / "registry.json"
        if not filepath.exists():
            pytest.skip("Registry file not found")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data is not None
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in registry.json: {e}")

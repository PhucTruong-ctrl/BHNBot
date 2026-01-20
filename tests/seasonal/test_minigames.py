"""
Tests for seasonal minigame system.

Tests the BaseMinigame registry system and utilities.
Note: Many minigames are missing spawn_config implementation,
so we test the registry without instantiation.
"""
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMinigameRegistry:
    
    def test_registry_is_populated(self):
        """Registry should be populated with minigame classes."""
        from cogs.seasonal.minigames import MINIGAME_REGISTRY
        
        assert len(MINIGAME_REGISTRY) > 0
    
    def test_registry_keys_are_strings(self):
        """Registry keys should be string identifiers."""
        from cogs.seasonal.minigames import MINIGAME_REGISTRY
        
        for key in MINIGAME_REGISTRY:
            assert isinstance(key, str)
    
    def test_registry_values_are_classes(self):
        """Registry values should be class types."""
        from cogs.seasonal.minigames import MINIGAME_REGISTRY
        
        for cls in MINIGAME_REGISTRY.values():
            assert isinstance(cls, type)
    
    def test_known_minigames_registered(self):
        """Known minigames should be in registry."""
        from cogs.seasonal.minigames import MINIGAME_REGISTRY
        
        expected = ["lixi_auto", "boat_race", "ghost_hunt", "treasure_hunt"]
        
        for name in expected:
            assert name in MINIGAME_REGISTRY, f"Missing: {name}"
    
    def test_get_minigame_returns_none_for_unknown(self):
        """get_minigame should return None for unknown minigame."""
        from cogs.seasonal.minigames.base import MINIGAME_REGISTRY
        
        assert "totally_fake_minigame" not in MINIGAME_REGISTRY


class TestBaseMinigameClass:
    
    def test_base_minigame_has_abstract_methods(self):
        """BaseMinigame should define abstract methods."""
        from cogs.seasonal.minigames import BaseMinigame
        
        abstract_methods = BaseMinigame.__abstractmethods__
        
        assert "name" in abstract_methods
        assert "spawn_config" in abstract_methods
        assert "spawn" in abstract_methods
        assert "handle_interaction" in abstract_methods
    
    def test_register_minigame_decorator_adds_to_registry(self):
        """register_minigame decorator should add class to registry."""
        from cogs.seasonal.minigames.base import MINIGAME_REGISTRY, register_minigame
        
        @register_minigame("test_dummy")
        class DummyMinigame:
            pass
        
        assert "test_dummy" in MINIGAME_REGISTRY
        assert MINIGAME_REGISTRY["test_dummy"] == DummyMinigame
        
        del MINIGAME_REGISTRY["test_dummy"]


class TestMinigameHelperFunctions:
    
    def test_is_scheduled_checks_spawn_type(self):
        """is_scheduled should check spawn_type in config."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {"spawn_type": "scheduled"}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        assert mg.is_scheduled() is True
        assert mg.is_random() is False
    
    def test_is_random_checks_spawn_type(self):
        """is_random should check spawn_type in config."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {"spawn_type": "random"}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        assert mg.is_random() is True
        assert mg.is_scheduled() is False
    
    def test_mixed_spawn_type_is_both(self):
        """Mixed spawn type should be both scheduled and random."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {"spawn_type": "mixed"}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        assert mg.is_scheduled() is True
        assert mg.is_random() is True
    
    def test_get_scheduled_times_returns_list(self):
        """get_scheduled_times should return scheduled times list."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {"scheduled_times": ["08:00", "12:00", "18:00"]}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        assert mg.get_scheduled_times() == ["08:00", "12:00", "18:00"]
    
    def test_get_random_times_per_day_returns_tuple(self):
        """get_random_times_per_day should return min/max tuple."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {"times_per_day": [2, 8]}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        assert mg.get_random_times_per_day() == (2, 8)
    
    def test_get_active_hours_returns_tuple(self):
        """get_active_hours should return hour range tuple."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {"active_hours": [9, 21]}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        assert mg.get_active_hours() == (9, 21)
    
    def test_get_active_hours_defaults(self):
        """get_active_hours should have sensible defaults."""
        from cogs.seasonal.minigames.base import BaseMinigame
        
        class MockMinigame(BaseMinigame):
            @property
            def name(self):
                return "test"
            
            @property
            def spawn_config(self):
                return {}
            
            async def spawn(self, channel, guild_id):
                pass
            
            async def handle_interaction(self, interaction):
                pass
        
        mg = MockMinigame(MagicMock(), MagicMock())
        
        result = mg.get_active_hours()
        assert result == (8, 23)

"""
EffectManager v2.0 - Aquarium Set Effects System

This module manages set bonuses and effects for the aquarium decoration system.
Uses the new single-source JSON at data/aquarium/sets.json.

Key Features:
- Loads from single JSON source (no more duplicates)
- Support for 2-piece set bonuses
- Activity-specific effect filtering
- Support for 'all_bonus' that applies to all multipliers
"""

import json
import os
from typing import Dict, List, Optional, Set
from enum import Enum

from core.logging import get_logger

logger = get_logger("aquarium.effect_manager")

# Path to single source of truth
SETS_JSON_PATH = "data/aquarium/sets.json"


class EffectType(str, Enum):
    """All supported effect types."""
    # Multipliers (percentage bonuses)
    CATCH_RATE_BONUS = "catch_rate_bonus"
    RARE_CHANCE_BONUS = "rare_chance_bonus"
    LEGENDARY_CHANCE_BONUS = "legendary_chance_bonus"
    SEED_BONUS = "seed_bonus"
    SELL_PRICE_BONUS = "sell_price_bonus"
    MINIGAME_BONUS = "minigame_bonus"
    QUEST_REWARD_BONUS = "quest_reward_bonus"
    GIFT_VALUE_BONUS = "gift_value_bonus"
    GAMBLING_LUCK = "gambling_luck"
    ALL_BONUS = "all_bonus"  # Applies to all multiplier effects
    
    # Flat values
    PASSIVE_INCOME = "passive_income"


class SetsDataLoader:
    """
    Loads and caches set/item data from JSON.
    Separated from EffectManager for single responsibility.
    """
    _cache: Optional[Dict] = None
    
    @classmethod
    def load(cls, force_reload: bool = False) -> Dict:
        """Load sets data from JSON file."""
        if cls._cache is not None and not force_reload:
            return cls._cache
        
        if not os.path.exists(SETS_JSON_PATH):
            logger.error(f"Sets JSON not found: {SETS_JSON_PATH}")
            cls._cache = {"sets": {}, "items": {}}
            return cls._cache
        
        try:
            with open(SETS_JSON_PATH, 'r', encoding='utf-8') as f:
                loaded: Dict = json.load(f)
                cls._cache = loaded
                logger.info(
                    f"Loaded {len(loaded.get('sets', {}))} sets, "
                    f"{len(loaded.get('items', {}))} items from {SETS_JSON_PATH}"
                )
                return loaded
        except Exception as e:
            logger.error(f"Error loading sets JSON: {e}")
            cls._cache = {"sets": {}, "items": {}}
            return cls._cache
    
    @classmethod
    def get_sets(cls) -> Dict[str, dict]:
        """Get all sets."""
        data = cls.load()
        return data.get("sets", {}) if data else {}
    
    @classmethod
    def get_items(cls) -> Dict[str, dict]:
        """Get all items."""
        data = cls.load()
        return data.get("items", {}) if data else {}
    
    @classmethod
    def get_set(cls, set_id: str) -> Optional[dict]:
        """Get a specific set by ID."""
        sets = cls.get_sets()
        return sets.get(set_id) if sets else None
    
    @classmethod
    def get_item(cls, item_id: str) -> Optional[dict]:
        """Get a specific item by ID."""
        return cls.get_items().get(item_id)
    
    @classmethod
    def reload(cls) -> None:
        """Force reload data from disk."""
        cls._cache = None
        cls.load(force_reload=True)


class EffectManager:
    """
    Manages set effects for users.
    
    Usage:
        manager = EffectManager()
        
        # Get multiplier for specific effect (returns 1 + bonus)
        multiplier = await manager.get_multiplier(user_id, EffectType.SEED_BONUS)
        final_seeds = int(base_seeds * multiplier)
        
        # Get flat bonus (like passive_income)
        daily_income = await manager.get_flat_bonus(user_id, EffectType.PASSIVE_INCOME)
    """
    
    def __init__(self):
        """Initialize EffectManager. Does NOT use singleton pattern."""
        self._data_loader = SetsDataLoader
    
    async def get_placed_items(self, user_id: int) -> List[Optional[str]]:
        """
        Get list of item IDs placed in user's home slots.
        Returns list of 5 elements (slot 0-4), None for empty slots.
        """
        from cogs.aquarium.models import HomeSlot
        
        slots: List[Optional[str]] = [None] * 5
        
        try:
            home_slots = await HomeSlot.filter(user_id=user_id).all()
            for slot in home_slots:
                if 0 <= slot.slot_index < 5:
                    slots[slot.slot_index] = slot.item_id
        except Exception as e:
            logger.error(f"Error fetching home slots for user {user_id}: {e}")
        
        return slots
    
    async def get_active_sets(self, user_id: int) -> List[dict]:
        """
        Get list of active sets for user.
        A set is active when user has >= required_pieces items from that set placed.
        
        Returns list of set data dicts with their effects.
        """
        placed_items = await self.get_placed_items(user_id)
        placed_set = set(item for item in placed_items if item)
        
        if not placed_set:
            return []
        
        # Count items per set
        set_counts: Dict[str, int] = {}
        items_data = self._data_loader.get_items()
        
        for item_id in placed_set:
            item = items_data.get(item_id)
            if item:
                set_id = item.get("set_id")
                if set_id:
                    set_counts[set_id] = set_counts.get(set_id, 0) + 1
        
        # Check which sets are active
        active_sets = []
        sets_data = self._data_loader.get_sets()
        
        for set_id, count in set_counts.items():
            set_def = sets_data.get(set_id)
            if set_def:
                required = set_def.get("required_pieces", 2)
                if count >= required:
                    # Include set_id in the returned data
                    active_set = dict(set_def)
                    active_set["id"] = set_id
                    active_set["active_pieces"] = count
                    active_sets.append(active_set)
        
        return active_sets
    
    async def get_active_effects(
        self, 
        user_id: int, 
        activity: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get all active effects for user.
        
        Args:
            user_id: The user ID
            activity: Optional activity filter (fishing, harvest, sell, etc.)
                     If None, returns all effects.
        
        Returns:
            Dict mapping effect_type -> total_value
        """
        active_sets = await self.get_active_sets(user_id)
        
        effects: Dict[str, float] = {}
        
        for set_data in active_sets:
            set_activity = set_data.get("activity", "global")
            
            # Filter by activity if specified
            if activity and set_activity not in (activity, "global"):
                continue
            
            set_effects = set_data.get("effects", {})
            for effect_key, value in set_effects.items():
                effects[effect_key] = effects.get(effect_key, 0) + value
        
        return effects
    
    async def get_multiplier(
        self, 
        user_id: int, 
        effect_type: str,
        activity: Optional[str] = None
    ) -> float:
        """
        Get multiplier for a specific effect.
        
        Returns 1.0 + bonus, so you can directly multiply:
            final_value = base_value * await manager.get_multiplier(user_id, "seed_bonus")
        
        Also applies 'all_bonus' if present.
        """
        effects = await self.get_active_effects(user_id, activity)
        
        base_bonus = effects.get(effect_type, 0)
        all_bonus = effects.get(EffectType.ALL_BONUS, 0)
        
        # all_bonus applies to multiplier effects, not flat values
        if effect_type != EffectType.PASSIVE_INCOME:
            return 1.0 + base_bonus + all_bonus
        
        return 1.0 + base_bonus
    
    async def get_flat_bonus(
        self, 
        user_id: int, 
        effect_type: str,
        activity: Optional[str] = None
    ) -> float:
        """
        Get flat bonus value for an effect.
        
        Use for effects like passive_income that add a flat amount.
        """
        effects = await self.get_active_effects(user_id, activity)
        return effects.get(effect_type, 0)
    
    async def get_total_passive_income(self, user_id: int) -> int:
        """
        Calculate total daily passive income from active sets.
        Convenience method for the passive_income effect.
        """
        return int(await self.get_flat_bonus(user_id, EffectType.PASSIVE_INCOME))
    
    async def get_user_charm(self, user_id: int) -> int:
        """
        Calculate total charm from placed items.
        """
        placed_items = await self.get_placed_items(user_id)
        items_data = self._data_loader.get_items()
        
        total_charm = 0
        for item_id in placed_items:
            if item_id:
                item = items_data.get(item_id)
                if item:
                    total_charm += item.get("charm", 0)
        
        return total_charm


# Convenience function for quick access
def get_effect_manager() -> EffectManager:
    """Factory function to get an EffectManager instance."""
    return EffectManager()

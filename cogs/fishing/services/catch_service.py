"""Catch rolling service for fishing.

Pure functions for determining fish counts, loot tables, and catch types.
No Discord dependencies - just probability math.
"""

from __future__ import annotations

import random
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class LootTableType(Enum):
    """Types of loot tables available."""
    NORMAL = "normal"
    BOOST = "boost"  # With worm buff
    NO_WORM = "no_worm"  # Fishing without bait
    DARK_MAP = "dark_map"  # Cthulhu map active


class CatchType(Enum):
    """Types of catches possible."""
    COMMON = "common"
    RARE = "rare"
    TRASH = "trash"
    LEGENDARY = "legendary"


def roll_fish_counts(
    base_count: int = 1,
    max_count: int = 5,
    rod_bonus: int = 0,
    buff_bonus: int = 0,
) -> tuple[int, int, int]:
    """Roll the number of fish, trash, and chests for a cast.
    
    Args:
        base_count: Minimum fish count
        max_count: Maximum fish count
        rod_bonus: Bonus from rod level
        buff_bonus: Bonus from active buffs
        
    Returns:
        tuple[int, int, int]: (fish_count, trash_count, chest_count)
    """
    # Fish count: weighted random 1-5, with bonuses
    weights = [40, 30, 15, 10, 5]  # Favor lower counts
    fish_count = random.choices(range(1, 6), weights=weights)[0]
    fish_count = min(max_count, fish_count + rod_bonus + buff_bonus)
    fish_count = max(base_count, fish_count)
    
    # Trash count: 0-2, mostly 0
    trash_weights = [70, 20, 10]
    trash_count = random.choices(range(3), weights=trash_weights)[0]
    
    # Chest count: 0-1, rare
    chest_count = 1 if random.random() < 0.05 else 0
    
    return fish_count, trash_count, chest_count


def select_loot_table(
    has_worm: bool,
    has_boost: bool = False,
    dark_map_active: bool = False,
) -> LootTableType:
    """Select which loot table to use for this cast.
    
    Args:
        has_worm: Whether user consumed a worm/bait
        has_boost: Whether a boost is active
        dark_map_active: Whether Cthulhu dark map is active
        
    Returns:
        LootTableType: The loot table to use
    """
    if dark_map_active:
        return LootTableType.DARK_MAP
    if not has_worm:
        return LootTableType.NO_WORM
    if has_boost:
        return LootTableType.BOOST
    return LootTableType.NORMAL


def roll_catch_type(
    rare_ratio: float,
    trash_ratio: float = 0.05,
    is_guaranteed_rare: bool = False,
) -> CatchType:
    """Roll the type of catch for a single fish.
    
    Args:
        rare_ratio: Chance of rare catch (0.0-1.0)
        trash_ratio: Chance of trash catch (0.0-1.0)
        is_guaranteed_rare: Force rare catch
        
    Returns:
        CatchType: The type of catch rolled
    """
    if is_guaranteed_rare:
        return CatchType.RARE
        
    roll = random.random()
    
    if roll < trash_ratio:
        return CatchType.TRASH
    elif roll < trash_ratio + rare_ratio:
        return CatchType.RARE
    else:
        return CatchType.COMMON


def select_fish_from_pool(
    pool: list[dict[str, Any]],
    count: int = 1,
    exclude_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Select fish from a weighted pool.
    
    Args:
        pool: List of fish dicts with 'key', 'name', 'weight' fields
        count: Number of fish to select
        exclude_keys: Fish keys to exclude from selection
        
    Returns:
        list[dict]: Selected fish entries
    """
    if exclude_keys is None:
        exclude_keys = set()
        
    # Filter pool
    available = [f for f in pool if f.get("key") not in exclude_keys]
    if not available:
        return []
        
    # Extract weights
    weights = [f.get("weight", 1.0) for f in available]
    
    # Select with replacement (can catch duplicates)
    selected = random.choices(available, weights=weights, k=count)
    
    return selected

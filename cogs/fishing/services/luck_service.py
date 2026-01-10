"""Luck calculation service for fishing.

Pure functions for calculating user luck from various sources.
No Discord dependencies - just math and data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


def calculate_base_luck(rod_level: int, rod_levels_config: dict[int, dict[str, Any]]) -> float:
    """Calculate base luck from rod level.
    
    Args:
        rod_level: Current rod level (1-10)
        rod_levels_config: ROD_LEVELS configuration dict
        
    Returns:
        float: Base luck value from rod (e.g. 0.05 for 5%)
    """
    rod_config = rod_levels_config.get(rod_level, rod_levels_config.get(1, {}))
    return rod_config.get("luck", 0.0)


def calculate_buff_luck(buffs: dict[str, Any]) -> float:
    """Calculate luck modifier from active buffs.
    
    Args:
        buffs: Dict of active buffs from get_user_buffs()
        
    Returns:
        float: Luck modifier from buffs (can be negative)
    """
    luck = 0.0
    
    if "lucky_buff" in buffs:
        # From events (Double Rainbow, etc) - huge bonus
        luck += 0.5  # +50%
        
    if "suy" in buffs:
        # Debuff state reduces luck
        luck -= 0.2  # -20%
        
    if "legendary_buff" in buffs:
        # Ghost NPC buff
        luck += 0.3  # +30%
        
    return luck


def calculate_total_luck(
    rod_level: int,
    rod_levels_config: dict[int, dict[str, Any]],
    buffs: dict[str, Any],
    global_luck_bonus: float = 0.0,
) -> float:
    """Calculate total luck from all sources.
    
    This is a pure function version of FishingCog.get_user_total_luck().
    
    Args:
        rod_level: Current rod level
        rod_levels_config: ROD_LEVELS configuration
        buffs: Active buffs dict
        global_luck_bonus: Bonus from global events
        
    Returns:
        float: Total luck value (can be negative, but typically 0.0-1.0+)
    """
    luck = 0.0
    
    # Rod luck
    luck += calculate_base_luck(rod_level, rod_levels_config)
    
    # Buff luck
    luck += calculate_buff_luck(buffs)
    
    # Global event bonus
    luck += global_luck_bonus
    
    return luck


def calculate_rare_ratio(
    base_rare_ratio: float,
    user_luck: float,
    disaster_penalty: float = 0.0,
    min_ratio: float = 0.01,
    max_ratio: float = 0.95,
) -> float:
    """Calculate final rare catch ratio with all modifiers.
    
    Args:
        base_rare_ratio: Base rare ratio from loot table (e.g. 0.15)
        user_luck: Total user luck value
        disaster_penalty: Penalty from active disaster (0.0-1.0)
        min_ratio: Minimum allowed ratio
        max_ratio: Maximum allowed ratio
        
    Returns:
        float: Final rare ratio clamped to [min_ratio, max_ratio]
    """
    # Apply luck bonus
    ratio = base_rare_ratio + user_luck
    
    # Apply disaster penalty (multiplicative)
    if disaster_penalty > 0:
        ratio *= (1.0 - disaster_penalty)
    
    # Clamp to valid range
    return max(min_ratio, min(max_ratio, ratio))

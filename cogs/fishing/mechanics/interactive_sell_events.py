"""Helper functions for interactive sell events.

Provides event detection, condition checking, and View creation.
"""
import random
import discord
from typing import Optional, Dict, Any
from database_manager import get_stat, get_user_balance
from core.logger import setup_logger

logger = setup_logger("InteractiveSellEvents", "cogs/fishing/fishing.log")


async def check_interactive_event(
    user_id: int, 
    fish_items: Dict[str, int], 
    base_value: int,
    sell_events_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Check if an interactive sell event should trigger.
    
    Args:
        user_id: Discord user ID
        fish_items: Dict of fish being sold
        base_value: Calculated base sell value
        sell_events_data: Loaded sell_events.json data
        
    Returns:
        Event data dict if triggered, None otherwise
    """
    events = sell_events_data.get('events', {})
    
    # Filter to interactive events only
    interactive_events = {
        key: event for key, event in events.items()
        if event.get('type') == 'interactive'
    }
    
    if not interactive_events:
        return None
    
    # Check each event
    for event_key, event_data in interactive_events.items():
        # Check condition first (faster to fail early)
        if 'condition' in event_data:
            if not await _check_condition(user_id, fish_items, base_value, event_data['condition']):
                continue
        
        # Roll RNG
        chance = event_data.get('chance', 0.0)
        if random.random() < chance:
            # Event triggered!
            logger.info(
                f"[INTERACTIVE_EVENT] Triggered {event_key} for user {user_id} "
                f"(chance={chance*100:.2f}%)"
            )
            
            # Return event data with key included
            return {**event_data, 'key': event_key}
    
    return None


async def _check_condition(
    user_id: int,
    fish_items: Dict[str, int],
    base_value: int,
    condition: Dict[str, Any]
) -> bool:
    """Check if event condition is met.
    
    Supports various condition types:
    - base_value: Check sell value
    - fish_count: Check number of fish types
    - user_balance: Check player's seed balance
    - has_legendary: Check for legendary fish
    
    Args:
        user_id: Discord user ID
        fish_items: Fish being sold
        base_value: Base sell value
        condition: Condition config dict
        
    Returns:
        True if condition met, False otherwise
    """
    try:
        cond_type = condition.get('type')
        operator = condition.get('operator', '>=')
        value = condition.get('value')
        
        if cond_type == 'base_value':
            check_value = base_value
        elif cond_type == 'fish_count':
            check_value = len(fish_items)
        elif cond_type == 'user_balance':
            check_value = await get_user_balance(user_id)
        elif cond_type == 'has_legendary':
            # Check if any fish is legendary
            from ..constants import LEGENDARY_FISH_KEYS
            check_value = any(k in LEGENDARY_FISH_KEYS for k in fish_items.keys())
            return check_value  # Boolean, no operator needed
        elif cond_type == 'rod_durability':
            # Check rod durability
            # get_rod_data returns tuple(level, durability)
            from database_manager import get_rod_data
            rod_level, rod_durability = await get_rod_data(user_id)
            check_value = rod_durability
        elif cond_type == 'max_fish_value':
            # Check maximum value of any single fish type in the batch
            from ..constants import ALL_FISH
            max_val = 0
            for fish_key in fish_items.keys():
                fish_data = ALL_FISH.get(fish_key)
                if fish_data:
                    price = fish_data.get('sell_price', 0)
                    if price > max_val:
                        max_val = price
            check_value = max_val
        else:
            logger.warning(f"[CONDITION] Unknown condition type: {cond_type}")
            return True  # Default to allowing event
        
        # Apply operator
        if operator == '>=':
            return check_value >= value
        elif operator == '>':
            return check_value > value
        elif operator == '<=':
            return check_value <= value
        elif operator == '<':
            return check_value < value
        elif operator == '==':
            return check_value == value
        elif operator == '!=':
            return check_value != value
        else:
            logger.warning(f"[CONDITION] Unknown operator: {operator}")
            return True
            
    except Exception as e:
        logger.error(f"[CONDITION_ERROR] {e}", exc_info=True)
        return True  # Default to allowing event on error


def create_interactive_view(event_data: Dict, cog, user_id: int, fish_items: Dict, base_value: int, ctx):
    """Factory function to create appropriate interactive View.
    
    Args:
        event_data: Event configuration
        cog: FishingCog instance
        user_id: Discord user ID
        fish_items: Fish being sold
        base_value: Base sell value
        ctx: Command context
        
    Returns:
        InteractiveSellEventView instance
    """
    from ..ui import InteractiveSellEventView
    
    # For now, use base class for all events
    # Later can add event-specific View classes
    return InteractiveSellEventView(
        cog=cog,
        user_id=user_id,
        fish_items=fish_items,
        base_value=base_value,
        event_data=event_data,
        ctx_or_interaction=ctx
    )


def create_interactive_embed(event_data: Dict, base_value: int, fish_items: Dict) -> 'discord.Embed':
    """Create embed to display interactive event choices.
    
    Args:
        event_data: Event configuration
        base_value: Base sell value
        fish_items: Fish being sold
        
    Returns:
        Discord Embed
    """
    
    title = event_data.get('name', 'Sự Kiện Bán Cá')
    description = event_data.get('description', '')
    
    # Format placeholders
    total_fish = sum(item['quantity'] for item in fish_items.values())
    description = description.format(
        base_value=f"{base_value:,}",
        total_fish=total_fish
    )
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    
    # Add choices as fields
    choices = event_data.get('interactive', {}).get('choices', [])
    for choice in choices:
        # Show outcomes briefly
        outcome_text = []
        for outcome in choice['outcomes']:
            weight = outcome.get('weight', 1.0)
            mul = outcome.get('mul', 1.0)
            flat = outcome.get('flat', 0)
            msg = outcome.get('message', '')
            
            prob = int(weight * 100) if len(choice['outcomes']) > 1 else 100
            
            if mul != 1.0:
                outcome_text.append(f"{prob}%: x{mul} {msg}")
            elif flat != 0:
                outcome_text.append(f"{prob}%: {flat:+d} {msg}")
        
        embed.add_field(
            name=choice['label'],
            value="\n".join(outcome_text) if outcome_text else choice.get('description', ''),
            inline=False
        )
    
    timeout = event_data.get('interactive', {}).get('timeout', 30)
    embed.set_footer(text=f"⏰ {timeout}s để quyết định")
    
    return embed

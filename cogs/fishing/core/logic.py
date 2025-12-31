import logging
import time
import random
import asyncio
from typing import Tuple, Dict, Any, Optional

from database_manager import db_manager, get_user_balance, add_seeds, increment_stat, get_stat
from configs.item_constants import ItemKeys
from configs.settings import (
    WORM_COST, CATCH_COUNT_WEIGHTS, LOOT_TABLE_NORMAL, LOOT_TABLE_BOOST, LOOT_TABLE_NO_WORM,
    ROD_LEVELS
)
from .constants import ALL_FISH
from .models import get_rod_data, update_rod_data


logger = logging.getLogger("FishingLogic")

async def get_cast_parameters(user_id: int):
    """
    Phase 1: Get data needed for UI and pre-checks.
    Returns: (rod_level, rod_durability, rod_config, wait_time)
    """
    rod_lvl, rod_durability = await get_rod_data(user_id)
    rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
    wait_time = random.randint(1, 5)
    return rod_lvl, rod_durability, rod_config, wait_time

async def process_fishing_failure(
    user_id: int, 
    rod_level: int,
    event_data: Dict[str, Any],
    bot_inventory
) -> Dict[str, Any]:
    """
    Handles 'Terminal' events (bad luck) that occur before casting finishes.
    Deducts bait/durability if the event says so (e.g. Broken Rod, Snapped Line).
    Updates database immediately.
    """
    result = {
        "status": "failed",
        "reason": event_data.get("type", "unknown_event"),
        "message": event_data.get("message", ""),
        "durability_loss": 0,
        "lost_worm": False
    }
    
    async with db_manager.transaction():
        # Inventory / Rod Updates
        # Events like 'snapped_line' imply losing the worm even if cast failed
        if event_data.get("lose_worm", False):
            # Check inventory first? Or just deduct if event roll passed check
            # For simplicity, we try to deduct. If 0, no change.
            curr_worms = await bot_inventory.get_all(user_id)
            if curr_worms.get(ItemKeys.MOI, 0) > 0:
                await bot_inventory.modify(user_id, ItemKeys.MOI, -1)
                result["lost_worm"] = True
                await increment_stat(user_id, "fishing", "worms_used", 1) # Even lost worms count? Maybe.

        # Durability Hit
        dura_loss = event_data.get("durability_loss", 0)
        # Some events explicitly break rod (set durability to 0) or reduce it
        if event_data.get("type") == "equipment_break":
            # Force break logic
            pass # Implementation dependent, assume handler sets big dura_loss
        
        if dura_loss > 0:
            current_lvl, current_durability = await get_rod_data(user_id)
            new_durability = max(0, current_durability - dura_loss)
            await update_rod_data(user_id, new_durability)
            result["durability_loss"] = dura_loss
            result["new_durability"] = new_durability
            
    return result

async def execute_cast_transaction(
    user_id: int, 
    guild_id: int,
    bot_inventory, # Dependency Injection for Inventory
    cog_instance,  # For events
    rod_lvl: int,
    rod_config: dict,
    forced_event: Dict[str, Any] = None, # Passed from Cog (Pre-Roll)
    has_lucky_buff: bool = False,
    is_boosted: bool = False
) -> Dict[str, Any]:
    """
    Phase 2: Atomic Execution of the cast.
    - Consumes bait (or auto-buys)
    - Applies forced_event effects (Bonus catch, etc)
    - Calculates Loot
    - Updates Durability
    - Returns detailed result dict
    """
    result = {
        "status": "success",
        "caught_items": {},
        "events_triggered": [forced_event] if forced_event and forced_event["triggered"] else [],
        "durability_loss": 0,
        "cooldown_end": 0,
        "auto_bought_worm": False,
        "used_worm": False,
        "rod_broken": False,
        "xp_gained": 0,
        "money_gained": 0 
    }

    async with db_manager.transaction():
        # 1. Re-Verify Rod Durability
        current_lvl, current_durability = await get_rod_data(user_id)
        if current_durability <= 0:
            result["status"] = "broken_rod"
            result["rod_broken"] = True
            return result

        # 2. Bait Management
        inventory = await bot_inventory.get_all(user_id)
        worm_count = inventory.get(ItemKeys.MOI, 0)
        has_worm = worm_count > 0
        
        # Auto-buy logic
        if not has_worm:
            balance = await get_user_balance(user_id)
            if balance >= WORM_COST:
                await add_seeds(user_id, -WORM_COST, 'auto_buy_worm', 'fishing')
                has_worm = True
                result["auto_bought_worm"] = True
                # No inventory update needed for worm since we assume immediate use
                
        # Consume Bait (if not Chrono Rod passive)
        used_worm = False
        if has_worm:
            skip_worm = False
            # Check Rod Passive (level 7)
            if rod_lvl == 7 and random.random() < rod_config.get("passive_chance", 0.10):
                skip_worm = True
            
            # Check Event Passive/Effect (e.g. Free Cast)
            if forced_event and forced_event.get("custom_effect") == "free_cast":
                skip_worm = True

            if not skip_worm:
                if result["auto_bought_worm"]:
                    pass # Already paid
                else:
                    await bot_inventory.modify(user_id, ItemKeys.MOI, -1)
                
                # Stats
                await increment_stat(user_id, "fishing", "worms_used", 1)
                used_worm = True
        
        result["used_worm"] = used_worm

        # 3. Durability Calculation
        durability_loss = 1
        # Check Event Modifier
        if forced_event:
            # If default durability loss is modified (e.g. protected)
            # Or if event adds damage (e.g. Plastic Trap)
            evt_loss = forced_event.get("durability_loss", 0)
            if evt_loss != 0:
                durability_loss += evt_loss # Could increase or decrease
            
            if forced_event.get("custom_effect") == "restore_durability":
                 # Actually negative loss or just set?
                 # Assuming handler sets logic, but here base cost is 1.
                 pass

        # Apply Durability Check
        # Ensure we don't heal unintendedly unless event says so
        final_loss = max(0, durability_loss)
        new_durability = max(0, current_durability - final_loss)
        
        # Handle Durability Restore event logic explicitly if needed
        if forced_event and forced_event.get("custom_effect") == "restore_durability":
             restore_amt = forced_event.get("restore_amount", 20)
             new_durability = min(rod_config.get("durability", 100), new_durability + restore_amt)
             final_loss = current_durability - new_durability # Negative implies gain

        await update_rod_data(user_id, new_durability)
        result["durability_loss"] = final_loss
        result["new_durability"] = new_durability
        result["rod_broken"] = (new_durability <= 0)

        # 4. Catch Logic
        # Apply Event Modifiers
        bonus_fish = 0
        duplicate_mult = 1
        
        if forced_event:
            if forced_event.get("lose_catch", False):
                # Catastrophe! No fish.
                result["caught_items"] = {}
                return result # Exit early (after bait/dura consumed)
            
            bonus_fish = forced_event.get("bonus_catch", 0)
            duplicate_mult = forced_event.get("duplicate_multiplier", 1)

        # Determine Num Fish
        if has_worm:
            num_fish = random.choices([1, 2, 3, 4, 5], weights=CATCH_COUNT_WEIGHTS, k=1)[0]
            num_fish += bonus_fish
        else:
            num_fish = 1
        
        # Determine Trash
        if has_worm:
            trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
        else:
            trash_count = random.choices([0, 1], weights=[50, 50], k=1)[0]
            
        # Determine Chest
        chest_count = 0
        if has_worm:
            chest_weights = [95, 5] if not (is_boosted or has_lucky_buff) else [90, 10]
            chest_count = random.choices([0, 1], weights=chest_weights, k=1)[0]
            
            # Event Bonus Chest
            if forced_event and forced_event.get("gain_items"):
                 # direct item injection handled separately or here?
                 # handler result has "gain_items". Merge it.
                 pass

        # Resolve actual items (RNG)
        loot_table = LOOT_TABLE_NORMAL
        if not has_worm:
            loot_table = LOOT_TABLE_NO_WORM
        elif is_boosted or has_lucky_buff:
            loot_table = LOOT_TABLE_BOOST
            
        final_items = {}
        total_xp = 0
        
        # Helper to add item
        def add_item(k, v):
            final_items[k] = final_items.get(k, 0) + v
        
        # Resolve Fish
        for _ in range(num_fish):
            fish_key = random.choices(
               list(loot_table.keys()), 
               weights=list(loot_table.values()), 
               k=1
            )[0]
            
            count = 1 * duplicate_mult
            
            # Void Rod Passive (x2)
            if rod_lvl == 6 and random.random() < 0.05:
                 count *= 2
                     
            add_item(fish_key, count)
            
            # XP Calc (Simplified)
            fish_data = ALL_FISH.get(fish_key, {"xp": 10})
            total_xp += fish_data.get("xp", 10) * count

        # Resolve Trash
        for _ in range(trash_count):
            add_item("rac", 1)
            total_xp += 1
        
        # Resolve Chest
        if chest_count > 0:
             add_item(ItemKeys.RUONG_KHO_BAU, chest_count)
             
        # Resolve Event Items (e.g. Chest from event)
        if forced_event and forced_event.get("gain_items"):
            for k, v in forced_event["gain_items"].items():
                add_item(k, v)

        # Update Inventory & XP
        # We need to process "rac" into actual items? Or keep as "rac" key?
        # Assuming inventory supports "rac" or specific keys.
        # Logic says "rac" is generic.
        
        for key, qty in final_items.items():
            if key == "rac": 
                 # Handle random trash items logic if needed, or pass 'rac' if DB supports it
                 # Usually trash is instantly converted or stored as specific trash items
                 pass 
            else:
                await bot_inventory.modify(user_id, key, qty)

        # XP Update
        await increment_stat(user_id, "fishing", "exp", total_xp)
        # Check level up? (Handled by listener usually)
        
        result["caught_items"] = final_items
        result["xp_gained"] = total_xp

        # 5. Cooldown Setting
        cd = rod_config["cd"]
        # Apply modifiers...
        result["cooldown_end"] = time.time() + cd
        
        return result


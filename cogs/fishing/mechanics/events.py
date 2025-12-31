"""Random event system for fishing with Strategy Pattern."""

import random
from ..constants import DB_PATH, RANDOM_EVENTS, RANDOM_EVENT_MESSAGES, CRYPTO_LOSS_CAP, AUDIT_TAX_CAP
from configs.item_constants import ItemKeys

from database_manager import increment_stat

# ==================== EFFECT HANDLERS ====================
# Each handler function processes one effect type
# This replaces the long if/elif chain

async def handle_lose_worm(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: User loses bait and catch."""
    result["lose_worm"] = True
    result["lose_catch"] = True
    return result

async def handle_lose_catch(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Lose catch."""
    result["lose_worm"] = True
    result["lose_catch"] = True
    return result

async def handle_thief(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Thief (Cat/Otter) - steals the biggest fish."""
    result["custom_effect"] = "cat_steal"
    result["lose_worm"] = True
    return result

def handle_lose_money(amount: int):
    """Factory: Creates a handler to deduct money."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["lose_money"] = amount
        return result
    return handler

def handle_cooldown(seconds: int):
    """Factory: Creates a handler to add cooldown."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["cooldown_increase"] = seconds
        return result
    return handler

async def handle_durability_hit(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Durability loss."""
    result["custom_effect"] = "durability_hit"
    result["durability_loss"] = -5
    return result

async def handle_lose_all_bait(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Lose all bait (Sea Sickness)."""
    result["custom_effect"] = "lose_all_bait"
    return result

def handle_gain_money(amount_min: int, amount_max: int):
    """Factory: Creates a handler to add random money."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["gain_money"] = random.randint(amount_min, amount_max)
        return result
    return handler

def handle_gain_money_fixed(amount: int):
    """Factory: Creates a handler to add fixed money."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["gain_money"] = amount
        return result
    return handler

async def handle_lose_money_percent(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Deduct % of assets (Snake Bite)."""
    result["custom_effect"] = "snake_bite"
    return result

async def handle_gain_money_percent(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Gain % of assets (Crypto Pump)."""
    result["custom_effect"] = "gain_money_percent"
    return result

def handle_gain_items(items: dict):
    """Factory: Creates a handler to add items."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["gain_items"] = items
        return result
    return handler

async def handle_gain_random_map_piece(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Receive a random map piece."""
    map_pieces = ["manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d"]
    piece = random.choice(map_pieces)
    result["gain_items"] = {piece: 1}
    return result

def handle_bonus_catch(count: int):
    """Factory: Creates a handler for bonus fish catch."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["bonus_catch"] = count
        return result
    return handler

def handle_duplicate_catch(multiplier: int):
    """Factory: Creates a handler to multiply caught fish."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["duplicate_multiplier"] = multiplier
        return result
    return handler

async def handle_reset_cooldown(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Reset cooldown."""
    result["cooldown_increase"] = -999
    return result

async def handle_restore_durability(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Restore durability."""
    result["custom_effect"] = "restore_durability"
    return result

async def handle_lucky_buff(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Lucky buff."""
    result["custom_effect"] = "lucky_buff"
    return result

async def handle_avoid_bad_event(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Sixth sense - avoid bad events."""
    result["custom_effect"] = "sixth_sense"
    return result

async def handle_global_reset(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Global reset (Level 3+)."""
    result["custom_effect"] = "global_reset"
    return result

async def handle_bet_win(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Bet win."""
    amount = random.randint(200, 400)
    result["gain_money"] = amount
    if "user_id" in kwargs:
        print(f"[EVENT] handle_bet_win: user_id={kwargs['user_id']} gain_money={amount}")
    return result

async def handle_bet_loss(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Bet loss."""
    amount = random.randint(50, 150)
    result["lose_money"] = amount
    if "user_id" in kwargs:
        print(f"[EVENT] handle_bet_loss: user_id={kwargs['user_id']} lose_money={amount}")
    return result

async def handle_crypto_loss(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Crypto scam - lose 50% current balance (Capped)."""
    # Get user balance from kwargs (passed by trigger_random_event)
    if "user_id" in kwargs:
        from database_manager import get_user_balance
        balance = await get_user_balance(kwargs["user_id"])
        lost = int(balance * 0.5)
        
        # Apply strict cap
        if lost > CRYPTO_LOSS_CAP:
            lost = CRYPTO_LOSS_CAP
            
        result["lose_money"] = lost
        print(f"[EVENT] handle_crypto_loss: user_id={kwargs['user_id']} balance={balance} lost={lost} (Capped at {CRYPTO_LOSS_CAP})")
    else:
        result["lose_money"] = 200
    return result

async def handle_suy_debuff(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Depression debuff - 50% rare catch rate for 5 casts."""
    result["custom_effect"] = "suy_debuff"
    result["debuff_type"] = "suy"
    result["debuff_duration"] = 5  # 5 casts
    return result

async def handle_keo_ly_buff(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Slay buff - 2x sell price for 10 minutes."""
    result["custom_effect"] = "keo_ly_buff"
    result["buff_type"] = "keo_ly"
    result["buff_duration"] = 600  # 10 minutes in seconds
    return result

async def handle_lag_debuff(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Lag debuff - 3s delay per cast for 5 minutes."""
    result["custom_effect"] = "lag_debuff"
    result["debuff_type"] = "lag"
    result["debuff_duration"] = 300  # 5 minutes in seconds
    result["lag_delay"] = 3  # 3 second delay
    return result

# --- CÁC HANDLER MỚI ---

async def handle_audit_check(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Audit Check - Tax the rich, support the poor."""
    if "user_id" in kwargs:
        from database_manager import get_user_balance
        balance = await get_user_balance(kwargs["user_id"])
        
        if balance >= 5000:
            tax = int(balance * 0.1)
            # Apply Cap
            if tax > AUDIT_TAX_CAP:
                tax = AUDIT_TAX_CAP
                
            result["lose_money"] = tax
            result["message"] += f"\n📉 Bạn quá giàu nên bị thu thuế **{tax} Hạt**!"
        elif balance <= 100:
            support = 200
            result["gain_money"] = support
            result["message"] += f"\n📈 Bạn thuộc hộ nghèo, được trợ cấp **{support} Hạt**!"
        else:
            result["message"] += "\n😐 Tài khoản minh bạch, không ai quan tâm."
    return result

async def handle_blind_box(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Blind Box - Random outcome."""
    outcome = random.choices(["trash", "money", "fee"], weights=[40, 30, 30])[0]
    
    if outcome == "trash":
        result["convert_to_trash"] = True  # Assumes main logic handles this flag to convert fish to trash
        result["message"] += "\n📦 Mở ra toàn giấy lộn! (Nhận được Rác)"
    elif outcome == "money":
        result["gain_money"] = 500
        result["message"] += "\n💰 Mở ra thấy 500 Hạt kẹp trong đáy hộp!"
    else:
        result["lose_money"] = 100
        result["message"] += "\n💸 Phải trả 100 Hạt tiền Ship COD. Cay!"
    return result

async def handle_flexing(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Flexing - Gain money but lose durability."""
    result["gain_money"] = 150
    result["durability_loss"] = -20  # Heavy durability loss
    return result

async def handle_free_cast(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Forgot Bait - No bait cost."""
    result["gain_items"] = {ItemKeys.MOI: 1}  # Refund 1 bait (treated as no cost)
    return result

async def handle_isekai(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Isekai - Receive Isekai Fish + 10 minute cooldown."""
    # Receive legendary fish from another world
    # NOTE: Item addition handled in cog.py to prevent spoiler in generic message
    # result["gain_items"] = {ItemKeys.CA_ISEKAI: 1} 
    result["cooldown_increase"] = 600  # 10 minute stun
    return result

async def handle_inflation(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Inflation - Price drop debuff."""
    result["custom_effect"] = "market_crash"
    result["debuff_type"] = "price_drop"
    result["debuff_duration"] = 600
    return result

async def handle_hack_map(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Hack Map - Bonus catch + Ban penalty."""
    # Item addition logic handled in main cog, this returns dict
    result["bonus_catch"] = 3 
    result["cooldown_increase"] = 300  # 5 minute penalty
    return result

async def handle_gain_vat_lieu_nang_cap_small(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Gain 1-2 rod materials."""
    amount = random.randint(1, 2)
    result["gain_items"] = {"vat_lieu_nang_cap": amount}
    result["message"] += f"\n🛠️ Nhặt được **{amount} Vật Liệu**!"
    return result

async def handle_gain_vat_lieu_nang_cap_medium(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Gain 3-5 rod materials."""
    amount = random.randint(3, 5)
    result["gain_items"] = {"vat_lieu_nang_cap": amount}
    result["message"] += f"\n🛠️ Nhặt được **{amount} Vật Liệu**!"
    return result

async def handle_gain_vat_lieu_nang_cap_large(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Gain 6-10 rod materials."""
    amount = random.randint(6, 10)
    result["gain_items"] = {"vat_lieu_nang_cap": amount}
    result["message"] += f"\n🛠️ Nhặt được **{amount} Vật Liệu**!"
    return result

async def handle_gain_vat_lieu_nang_cap_random(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Gain 1-10 rod materials."""
    amount = random.randint(1, 10)
    result["gain_items"] = {"vat_lieu_nang_cap": amount}
    result["message"] += f"\n🛠️ Nhặt được **{amount} Vật Liệu**!"
    return result

# ==================== EFFECT HANDLERS MAPPING ====================
# Dictionary mapping effect names to their handlers
# EASY TO EXTEND: Just add a new handler + add entry to this dict
EFFECT_HANDLERS = {
    "lose_worm": handle_lose_worm,
    "lose_catch": handle_lose_catch,
    "thief": handle_thief,
    "lose_money_50": handle_lose_money(50),
    "lose_money_100": handle_lose_money(100),
    "lose_money_200": handle_lose_money(200),
    "cooldown_short": handle_cooldown(120),
    "cooldown_medium": handle_cooldown(300),
    "cooldown_long": handle_cooldown(600),
    "lose_turn": handle_lose_catch,  # Same as lose_catch
    "durability_hit": handle_durability_hit,
    "lose_all_bait": handle_lose_all_bait,
    "gain_money_small": handle_gain_money(30, 80),
    "gain_money_medium": handle_gain_money(100, 250),
    "gain_money_large": handle_gain_money(300, 600),
    "gain_money_huge": handle_gain_money(1000, 2000),
    "gain_money_percent": handle_gain_money_percent,
    "lose_money_percent": handle_lose_money_percent,
    "gain_worm_5": handle_gain_items({ItemKeys.MOI: 5}),
    "gain_worm_10": handle_gain_items({ItemKeys.MOI: 10}),
    "bet_loss": handle_bet_loss,
    "gain_chest_1": handle_gain_items({ItemKeys.RUONG_KHO_BAU: 1}),
    "gain_chest_2": handle_gain_items({ItemKeys.RUONG_KHO_BAU: 2}),
    "gain_ngoc_trai": handle_gain_items({ItemKeys.NGOC_TRAI: 1}),
    "gain_ring": handle_gain_items({"ring": 1}),
    "gain_map_piece": handle_gain_random_map_piece,
    "bonus_catch_2": handle_bonus_catch(2),
    "bonus_catch_3": handle_bonus_catch(3),
    "duplicate_catch_2": handle_duplicate_catch(2),
    "duplicate_catch_3": handle_duplicate_catch(3),
    "reset_cooldown": handle_reset_cooldown,
    "restore_durability": handle_restore_durability,
    "lucky_buff": handle_lucky_buff,
    "avoid_bad_event": handle_avoid_bad_event,
    "global_reset": handle_global_reset,
    "bet_win": handle_bet_win,
    "crypto_loss": handle_crypto_loss,
    "suy_debuff": handle_suy_debuff,
    "keo_ly_buff": handle_keo_ly_buff,
    "lag_debuff": handle_lag_debuff,
    "audit_check": handle_audit_check,
    "blind_box": handle_blind_box,
    "flexing": handle_flexing,
    "free_cast": handle_free_cast,
    "forgot_bait": handle_free_cast,  # Alias for free_cast
    "isekai": handle_isekai,
    "inflation": handle_inflation,
    "hack_map": handle_hack_map,
    "mlm_scheme": handle_lose_money(200),
    "lucky_cat": handle_lucky_buff,
    "football_bet": handle_crypto_loss,
    "gain_vat_lieu_nang_cap_small": handle_gain_vat_lieu_nang_cap_small,
    "gain_vat_lieu_nang_cap_medium": handle_gain_vat_lieu_nang_cap_medium,
    "gain_vat_lieu_nang_cap_large": handle_gain_vat_lieu_nang_cap_large,
    "gain_vat_lieu_nang_cap_random": handle_gain_vat_lieu_nang_cap_random,
}

import random
from typing import Dict, Optional, Any

from database_manager import get_user_balance, increment_stat, get_stat
from ..core.constants import (
    RANDOM_EVENTS, RANDOM_EVENT_MESSAGES, NPC_ENCOUNTERS, 
    NPC_AFFINITY_THRESHOLDS, FISHING_EVENT_STAT_MAPPING
)

# Keep the handlers dictionary, but ensure imports are clean if needed
# ... existing Handler imports ...

# ==================== PUBLIC API ====================

async def roll_fishing_event(
    cog, 
    user_id: int, 
    rod_level: int = 1, 
    luck: float = 0.0,
    check_protection: bool = True
) -> Dict[str, Any]:
    """
    Rolls for a standard 'Fishing Event' (Mechanic) from fishing_events.json.
    These events happen *during* the cast (Pre-calculation).
    
    Returns a result dict containing event type, message, and effects.
    Does NOT auto-execute side effects involving DB writes (mostly).
    """
    result = {
        "triggered": False, 
        "type": None, 
        "message": "", 
        "category": "neutral", # good/bad/neutral
        "is_terminal": False,  # If true, fishing stops (e.g. lose turn)
        "effect_data": {}      # Handled effect data
    }
    
    # 1. PENDING EVENTS (Forced)
    if hasattr(cog, "pending_fishing_event") and user_id in cog.pending_fishing_event:
        pending_key = cog.pending_fishing_event.pop(user_id)
        if pending_key in RANDOM_EVENTS:
            return await _process_specific_event(cog, user_id, pending_key, result)

    # 2. STANDARD ROLL
    # Filter eligible events
    eligible_events = {}
    for key, data in RANDOM_EVENTS.items():
        if await check_event_condition(user_id, data):
             eligible_events[key] = data
             
    if not eligible_events:
        return result

    items = list(eligible_events.items())
    random.shuffle(items) # Shuffle for fairness in iteration
    
    current_chance_acc = 0
    rand = random.random()
    
    for event_key, event_data in items:
        base_chance = event_data["chance"]
        category = event_data.get("type", "neutral")
        
        # Luck Modifier
        modified_chance = base_chance
        if category == "good":
            modified_chance *= (1.0 + luck * 2.0)
        elif category == "bad":
            modified_chance *= max(0.1, (1.0 - luck))
            
        current_chance_acc += modified_chance
        
        if rand < current_chance_acc:
             # Global Reset Constraint
             if event_data.get("effect") == "global_reset" and rod_level < 3:
                 return result
                 
             # Check Protection (Bad events only)
             if check_protection and category == "bad":
                 has_protection = hasattr(cog, "avoid_event_users") and cog.avoid_event_users.get(user_id, False)
                 if has_protection:
                     cog.avoid_event_users[user_id] = False
                     result["triggered"] = True
                     result["type"] = event_key
                     result["message"] = f"🛡️ Bạn đã tránh được sự kiện xấu: **{event_data.get('name', event_key)}**!"
                     result["avoided"] = True
                     return result
            
             return await _process_specific_event(cog, user_id, event_key, result, event_data)
             
    return result

async def roll_npc_event(
    cog,
    user_id: int,
    catch_result: Dict[str, Any] # Pass the catches to determine eligibility if needed
) -> Optional[Dict[str, Any]]:
    """
    Rolls for an NPC Encounter from npc_events.json.
    These events happen *after* the catch (Interactive).
    
    Returns: NPC Data dict or None.
    """
    if not NPC_ENCOUNTERS:
        return None
        
    rand = random.random()
    # Simple independent probability check for each NPC? 
    # Or weighted list? JSON structure suggests individual "chance" keys.
    # We iterate and check.
    
    # Shuffle to avoid priority bias
    npc_ids = list(NPC_ENCOUNTERS.keys())
    random.shuffle(npc_ids)
    
    for npc_id in npc_ids:
        npc_data = NPC_ENCOUNTERS[npc_id]
        chance = npc_data.get("chance", 0.0)
        
        # Hardcoded: reduce NPC spam? Max 1 NPC per fish.
        if rand < chance:
            # Check Affinity Override
            # (Logic to fetch current affinity and swap data)
            # For MVP, we return base data + affinity key lookup
            return {
                "id": npc_id,
                "base_data": npc_data,
                "triggered": True
            }
            
    return None

# ==================== INTERNAL HELPER ====================

async def _process_specific_event(cog, user_id: int, event_key: str, result_template: dict, event_data: dict = None) -> dict:
    """Populates the result dict for a specific triggered event."""
    if not event_data:
        event_data = RANDOM_EVENTS.get(event_key)
        
    result = result_template.copy()
    result["triggered"] = True
    result["type"] = event_key
    result["message"] = RANDOM_EVENT_MESSAGES.get(event_key, event_data.get("name", event_key))
    result["category"] = event_data.get("type", "neutral")
    
    # Check if terminal (Loss of turn/worm etc.)
    effect = event_data.get("effect")
    if effect in ["lose_turn", "lose_worm", "break_rod", "hospital_fee"]:
        result["is_terminal"] = True
    
    # Execute Handler (Strategy Pattern) to calculate details
    handler = EFFECT_HANDLERS.get(effect)
    if handler:
        # We pass a fresh dict to handler to avoid polluting the template
        # handler returns a dict with keys like 'lose_worm', 'bonus_catch' etc.
        # We merge it into effect_data
        handler_result = await handler(
            input_data={}, # Start empty
            event_data=event_data, 
            user_id=user_id, 
            cog=cog
        )
        result.update(handler_result) # merging directly for now
        
    # Track Stats
    try:
        if event_key in FISHING_EVENT_STAT_MAPPING:
             await increment_stat(user_id, "fishing", FISHING_EVENT_STAT_MAPPING[event_key], 1)
        if result["category"] == "bad":
             await increment_stat(user_id, "fishing", "bad_events_encountered", 1)
    except: pass
    
    return result

async def check_event_condition(user_id: int, event_data: dict) -> bool:
    """Check if user meets requirements for conditional event."""
    if "condition" not in event_data or event_data["condition"] is None:
        return True
    
    cond = event_data["condition"]
    stat_key = cond.get("stat_key")
    op = cond.get("operator")
    val = cond.get("value")
    
    if not stat_key or not op or val is None:
        return True
        
    try:
        # Resolve 'seeds' or general stats
        current = 0
        if stat_key == "seeds" or stat_key == "total_money_earned":
             current = await get_user_balance(user_id)
        else:
             current = await get_stat(user_id, "fishing", stat_key)
             
        if op == ">=": return current >= val
        if op == ">": return current > val
        if op == "<=": return current <= val
        if op == "<": return current < val
        if op == "==": return current == val
    except:
        return True # Fail safe open
        
    return True




# ==================== DEPRECATED / COMPATIBILITY ====================

async def trigger_random_event(
    cog, 
    user_id: int, 
    guild_id: int, # Unused in new logic but kept for sig combat
    rod_level: int, 
    channel, 
    luck: float = 0.0,
    check_protection: bool = True
) -> Dict[str, Any]:
    """
    DEPRECATED: Use roll_fishing_event instead.
    Wrapper for backward compatibility.
    """
    # Simply call the new function
    # Note: reset effects are handled via side effects in new function?
    # No, roll_fishing_event returns data. 
    # OLD trigger_random_event executed side effects!
    # So we must replicate execution logic here if legacy code relies on it.
    
    event_result = await roll_fishing_event(cog, user_id, rod_level, luck, check_protection)
    
    # If triggered, execute common logic?
    # New system separates Roll vs Execute. 
    # Old system did both.
    # If consumable calls this, it expects the event to HAPPEN.
    # But consumable mainly cares about "is_terminal" or "message".
    
    # To be safe, if we are calling this from legacy, we assume it's pre-fishing.
    # We return the dict.
    return event_result

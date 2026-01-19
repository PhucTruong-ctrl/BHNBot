"""Random event system for fishing with Strategy Pattern."""

import random
from ..constants import DB_PATH, RANDOM_EVENTS, RANDOM_EVENT_MESSAGES, CRYPTO_LOSS_CAP, AUDIT_TAX_CAP
from configs.item_constants import ItemKeys

from database_manager import increment_stat, get_stat

from core.logging import get_logger
logger = get_logger("fishing_events")


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
        logger.debug("[event]_handle_bet_win", user_id=kwargs['user_id'])
    return result

async def handle_bet_loss(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Bet loss."""
    amount = random.randint(50, 150)
    result["lose_money"] = amount
    if "user_id" in kwargs:
        logger.debug("[event]_handle_bet_loss", user_id=kwargs['user_id'])
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
        logger.debug("[event]_handle_crypto_loss", user_id=kwargs['user_id'])
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

async def trigger_random_event(cog, user_id: int, guild_id: int, rod_level: int = 1, channel=None, luck: float = 0.0) -> dict:
    """Trigger random event during fishing using Strategy Pattern."""
    result = {
        "triggered": False, "type": None, "message": "",
        "lose_worm": False, "lose_catch": False, "lose_money": 0, "gain_money": 0,
        "cooldown_increase": 0, "bonus_catch": 0, "duplicate_multiplier": 1, "convert_to_trash": False,
        "gain_items": {}, "custom_effect": None, "durability_loss": 0, "avoided": False
    }
    
    # CHECK FOR PENDING FISHING EVENT FIRST
    if hasattr(cog, "pending_fishing_event") and user_id in cog.pending_fishing_event:
        pending_event_key = cog.pending_fishing_event.pop(user_id)
        logger.debug("[events]_triggering_pending_fi", pending_event_key=pending_event_key)
        
        if pending_event_key in RANDOM_EVENTS:
            event_data = RANDOM_EVENTS[pending_event_key]
            result["triggered"] = True
            result["type"] = pending_event_key
            result["message"] = RANDOM_EVENT_MESSAGES.get(pending_event_key, f"Event: {pending_event_key}")
            
            # Track achievement stats for fishing events
            from ..constants import FISHING_EVENT_STAT_MAPPING
            if pending_event_key in FISHING_EVENT_STAT_MAPPING:
                stat_key = FISHING_EVENT_STAT_MAPPING[pending_event_key]
                try:
                    await increment_stat(user_id, "fishing", stat_key, 1)
                    current_value = await get_stat(user_id, "fishing", stat_key)
                    if hasattr(cog, 'bot') and hasattr(cog.bot, 'achievement_manager'):
                        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, channel)
                    logger.debug("[achievement]_tracked__for_use", stat_key=stat_key)
                except Exception as e:
                    logger.debug("[achievement]_error_tracking__", stat_key=stat_key)
            
            # ===== STRATEGY PATTERN: Call appropriate handler =====
            effect = event_data.get("effect")
            handler = EFFECT_HANDLERS.get(effect)
            
            if handler:
                result = await handler(result, event_data, user_id=user_id, cog=cog, luck=luck)
            else:
                logger.debug("[events]_warning:_no_handler_f", effect=effect)
            
            return result
        else:
            logger.debug("[events]_pending_fishing_event", pending_event_key=pending_event_key)
    
    # Check for protection
    has_protection = hasattr(cog, "avoid_event_users") and cog.avoid_event_users.get(user_id, False)
    if has_protection:
        cog.avoid_event_users[user_id] = False
    
    rand = random.random()
    current_chance = 0
    
    # Shuffle events to prevent bias towards early events due to probability accumulation?
    # Actually, iterate in fixed order but with accumulative probability is standard Weighted Random Selection.
    # However, here we emulate independent probabilities in a single pass?
    # No, the logic `rand < current_chance` implies events share the 0.0-1.0 space.
    # This means total probability MUST be <= 1.0. 
    # Adjusting probabilities dynamically allows leveraging this.
    
    # Sort events? No need if we trust the accumulated math.
    
    # We Iterate over items.
    # NOTE: Since we modify chances, we should probably ensure we don't exceed 1.0 logic logic if Luck is too high.
    # But for now simple multiplier is fine.
    
    # PRE-FILTER: Only include events user is eligible for (Phase 2: Conditional Events)
    eligible_events = {}
    for event_key, event_data in RANDOM_EVENTS.items():
        if await check_event_condition(user_id, event_data):
            eligible_events[event_key] = event_data
    
    # If no eligible events, return early
    if not eligible_events:
        return result  # No event triggered
    
    items = list(eligible_events.items())
    random.shuffle(items) # Optional shuffle to randomize precedence if overlaps occur (though math says they are distinct segments)
    
    for event_type, event_data in items:
        base_chance = event_data["chance"]
        modified_chance = base_chance
        
        # APPLY LUCK MODIFIERS
        e_type = event_data.get("type", "neutral")
        if e_type == "good":
            # Luck increases chance of good events significantly
            # Example: 0.1 luck -> 1.2x chance
            modified_chance = base_chance * (1.0 + luck * 2.0)
        elif e_type == "bad":
             # Luck decreases chance of bad events
             # Example: 0.1 luck -> 0.9x chance
             modified_chance = base_chance * max(0.1, (1.0 - luck))
        
        current_chance += modified_chance
        
        if rand < current_chance:
            # Skip global_reset if rod level < 3
            if event_data.get("effect") == "global_reset" and rod_level < 3:
                return result
            
            # Update stats in DB
            try:
                from database_manager import db_manager
                if event_data.get("type") == "bad":
                    await increment_stat(user_id, "fishing", "bad_events_encountered", 1)
                if event_data.get("effect") == "global_reset":
                    await increment_stat(user_id, "fishing", "global_reset_triggered", 1)
            except Exception as e:
                pass
            
            # If protection active and bad event, avoid it
            if has_protection and event_data.get("type") == "bad":
                result["triggered"] = True
                result["type"] = event_type
                result["message"] = RANDOM_EVENT_MESSAGES[event_type]
                result["avoided"] = True
                return result
            
            # Build result
            result["triggered"] = True
            result["type"] = event_type
            result["message"] = RANDOM_EVENT_MESSAGES[event_type]
            
            # Track achievement stats for fishing events
            from ..constants import FISHING_EVENT_STAT_MAPPING
            if event_type in FISHING_EVENT_STAT_MAPPING:
                stat_key = FISHING_EVENT_STAT_MAPPING[event_type]
                try:
                    await increment_stat(user_id, "fishing", stat_key, 1)
                    current_value = await get_stat(user_id, "fishing", stat_key)
                    if hasattr(cog, 'bot') and hasattr(cog.bot, 'achievement_manager'):
                        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, channel)
                except Exception as e:
                    pass
            
            # Skip bad events if user has no seeds
            from database_manager import get_user_balance
            if event_data.get("type") == "bad":
                user_seeds = await get_user_balance(user_id)
                if user_seeds <= 0:
                    return result
            
            # ===== STRATEGY PATTERN: Call appropriate handler =====
            effect = event_data.get("effect")
            handler = EFFECT_HANDLERS.get(effect)
            
            if handler:
                result = await handler(result, event_data, user_id=user_id, cog=cog, luck=luck)
            else:
                logger.debug("[events]_warning:_no_handler_f", effect=effect)
            
            return result
    
    return result

async def check_event_condition(user_id: int, event_data: dict) -> bool:
    """Check if user meets requirements for conditional event.
    
    Args:
        user_id: Discord user ID
        event_data: Event dict from fishing_events.json
        
    Returns:
        bool: True if user is eligible, False otherwise
    """
    # No condition = always eligible (backward compatible)
    if "condition" not in event_data or event_data["condition"] is None:
        return True

async def check_conditional_unlocks(user_id: int, stat_key: str, new_value: int, channel=None):
    """Check conditional unlocks - handled by achievement system."""
    return


"""Random event system for fishing."""

import random
import aiosqlite
from .constants import DB_PATH, RANDOM_EVENTS, RANDOM_EVENT_MESSAGES

async def trigger_random_event(cog, user_id: int, guild_id: int, rod_level: int = 1) -> dict:
    """Trigger random event during fishing."""
    result = {
        "triggered": False, "type": None, "message": "",
        "lose_worm": False, "lose_catch": False, "lose_money": 0, "gain_money": 0,
        "cooldown_increase": 0, "bonus_catch": 0, "duplicate_multiplier": 1, "convert_to_trash": False,
        "gain_items": {}, "custom_effect": None, "durability_loss": 0, "avoided": False
    }
    
    # Check for protection
    has_protection = hasattr(cog, "avoid_event_users") and cog.avoid_event_users.get(user_id, False)
    if has_protection:
        cog.avoid_event_users[user_id] = False
    
    rand = random.random()
    current_chance = 0
    
    for event_type, event_data in RANDOM_EVENTS.items():
        current_chance += event_data["chance"]
        if rand < current_chance:
            # Update stats in DB
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    if event_data.get("type") == "bad":
                        await db.execute(
                            "UPDATE economy_users SET bad_events_encountered = bad_events_encountered + 1 WHERE user_id = ?",
                            (user_id,)
                        )
                    if event_data.get("effect") == "global_reset":
                        await db.execute(
                            "UPDATE economy_users SET global_reset_triggered = global_reset_triggered + 1 WHERE user_id = ?",
                            (user_id,)
                        )
                    await db.commit()
            except:
                pass
            
            # Skip global_reset if rod level < 3
            if event_data.get("effect") == "global_reset" and rod_level < 3:
                return result
            
            # If protection active and bad event, avoid it
            if has_protection and event_data.get("type") == "bad":
                result["triggered"] = True
                result["type"] = event_type
                result["message"] = f"**{event_data['name']}** {RANDOM_EVENT_MESSAGES[event_type]}"
                result["avoided"] = True
                return result
            
            # Build result
            result["triggered"] = True
            result["type"] = event_type
            result["message"] = f"**{event_data['name']}** {RANDOM_EVENT_MESSAGES[event_type]}"
            
            # Skip bad events if user has no seeds
            from database_manager import get_user_balance
            if event_data.get("type") == "bad":
                user_seeds = await get_user_balance(user_id)
                if user_seeds <= 0:
                    return result
            
            # Handle effects (same logic as before)
            effect = event_data.get("effect")
            
            if effect == "lose_worm":
                result["lose_worm"] = True
                result["lose_catch"] = True
            elif effect == "lose_catch":
                result["lose_worm"] = True
                result["lose_catch"] = True
            elif effect == "thief":
                # Mèo/rái cá: mất mồi và bị lấy cá to nhất nhưng vẫn tiếp tục mẻ câu
                result["custom_effect"] = "cat_steal"
                result["lose_worm"] = True
            elif effect == "lose_money_50":
                result["lose_money"] = 50
            elif effect == "lose_money_100":
                result["lose_money"] = 100
            elif effect == "lose_money_200":
                result["lose_money"] = 200
            elif effect == "cooldown_short":
                result["cooldown_increase"] = 120
            elif effect == "cooldown_medium":
                result["cooldown_increase"] = 300
            elif effect == "cooldown_long":
                result["cooldown_increase"] = 600
            elif effect == "lose_turn":
                result["lose_catch"] = True
            elif effect == "durability_hit":
                # Mất độ bền nhưng vẫn nhận mẻ cá
                result["custom_effect"] = "durability_hit"
                result["durability_loss"] = -5
            elif effect == "lose_all_bait":
                result["custom_effect"] = "lose_all_bait"
            elif effect == "gain_money_small":
                result["gain_money"] = random.randint(30, 80)
            elif effect == "gain_money_medium":
                result["gain_money"] = random.randint(100, 200)
            elif effect == "gain_money_large":
                result["gain_money"] = random.randint(300, 500)
            elif effect == "gain_money_huge":
                result["gain_money"] = 1000
            elif effect == "lose_money_percent":
                # Phạt % tài sản (rắn cắn / viện phí)
                result["custom_effect"] = "snake_bite"
            elif effect == "gain_worm_5":
                result["gain_items"] = {"worm": 5}
            elif effect == "gain_worm_10":
                result["gain_items"] = {"worm": 10}
            elif effect == "bet_loss":
                # Lose a random amount on bad bet
                result["lose_money"] = random.randint(50, 150)
            elif effect == "gain_chest_1":
                result["gain_items"] = {"treasure_chest": 1}
            elif effect == "gain_chest_2":
                result["gain_items"] = {"treasure_chest": 2}
            elif effect == "gain_pearl":
                result["gain_items"] = {"pearl": 1}
            elif effect == "gain_ring":
                result["gain_items"] = {"ring": 1}
            elif effect == "bonus_catch_2":
                result["bonus_catch"] = 2
            elif effect == "bonus_catch_3":
                result["bonus_catch"] = 3
            elif effect == "duplicate_catch_2":
                result["duplicate_multiplier"] = 2
            elif effect == "duplicate_catch_3":
                result["duplicate_multiplier"] = 3
            elif effect == "reset_cooldown":
                result["cooldown_increase"] = -999
            elif effect == "restore_durability":
                result["custom_effect"] = "restore_durability"
            elif effect == "lucky_buff":
                result["custom_effect"] = "lucky_buff"
            elif effect == "avoid_bad_event":
                result["custom_effect"] = "sixth_sense"
            elif effect == "global_reset":
                result["custom_effect"] = "global_reset"
            elif effect == "bet_win":
                result["gain_money"] = random.randint(200, 400)
            
            return result
    
    return result
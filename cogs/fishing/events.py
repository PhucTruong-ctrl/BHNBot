"""Random event system for fishing with Strategy Pattern."""

import random
from .constants import DB_PATH, RANDOM_EVENTS, RANDOM_EVENT_MESSAGES
from database_manager import increment_stat

# ==================== EFFECT HANDLERS ====================
# Each handler function processes one effect type
# This replaces the long if/elif chain

async def handle_lose_worm(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Người chơi mất mồi và mẻ câu."""
    result["lose_worm"] = True
    result["lose_catch"] = True
    return result

async def handle_lose_catch(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Mất mẻ câu."""
    result["lose_worm"] = True
    result["lose_catch"] = True
    return result

async def handle_thief(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Mèo/rái cá - cướp con cá to nhất."""
    result["custom_effect"] = "cat_steal"
    result["lose_worm"] = True
    return result

def handle_lose_money(amount: int):
    """Factory: Tạo handler để trừ tiền."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["lose_money"] = amount
        return result
    return handler

def handle_cooldown(seconds: int):
    """Factory: Tạo handler để thêm cooldown."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["cooldown_increase"] = seconds
        return result
    return handler

async def handle_durability_hit(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Mất độ bền."""
    result["custom_effect"] = "durability_hit"
    result["durability_loss"] = -5
    return result

async def handle_lose_all_bait(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Mất hết mồi (say tàu)."""
    result["custom_effect"] = "lose_all_bait"
    return result

def handle_gain_money(amount_min: int, amount_max: int):
    """Factory: Tạo handler để thêm tiền ngẫu nhiên."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["gain_money"] = random.randint(amount_min, amount_max)
        return result
    return handler

def handle_gain_money_fixed(amount: int):
    """Factory: Tạo handler để thêm tiền cố định."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["gain_money"] = amount
        return result
    return handler

async def handle_lose_money_percent(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Phạt % tài sản (rắn cắn)."""
    result["custom_effect"] = "snake_bite"
    return result

def handle_gain_items(items: dict):
    """Factory: Tạo handler để thêm vật phẩm."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["gain_items"] = items
        return result
    return handler

async def handle_gain_random_map_piece(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Nhận mảnh bản đồ ngẫu nhiên."""
    map_pieces = ["manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d"]
    piece = random.choice(map_pieces)
    result["gain_items"] = {piece: 1}
    return result

def handle_bonus_catch(count: int):
    """Factory: Tạo handler để thêm cá bonus."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["bonus_catch"] = count
        return result
    return handler

def handle_duplicate_catch(multiplier: int):
    """Factory: Tạo handler để nhân đôi cá."""
    async def handler(result: dict, event_data: dict, **kwargs) -> dict:
        result["duplicate_multiplier"] = multiplier
        return result
    return handler

async def handle_reset_cooldown(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Reset cooldown."""
    result["cooldown_increase"] = -999
    return result

async def handle_restore_durability(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Phục hồi độ bền."""
    result["custom_effect"] = "restore_durability"
    return result

async def handle_lucky_buff(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Buff may mắn."""
    result["custom_effect"] = "lucky_buff"
    return result

async def handle_avoid_bad_event(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Sixth sense - tránh sự kiện xấu."""
    result["custom_effect"] = "sixth_sense"
    return result

async def handle_global_reset(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Global reset (cấp 3+)."""
    result["custom_effect"] = "global_reset"
    return result

async def handle_bet_win(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Cược thắng."""
    amount = random.randint(200, 400)
    result["gain_money"] = amount
    if "user_id" in kwargs:
        print(f"[EVENT] handle_bet_win: user_id={kwargs['user_id']} gain_money={amount}")
    return result

async def handle_bet_loss(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Cược thua."""
    amount = random.randint(50, 150)
    result["lose_money"] = amount
    if "user_id" in kwargs:
        print(f"[EVENT] handle_bet_loss: user_id={kwargs['user_id']} lose_money={amount}")
    return result

async def handle_crypto_loss(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Crypto scam - lose 50% current balance."""
    # Get user balance from kwargs (passed by trigger_random_event)
    if "user_id" in kwargs:
        from database_manager import get_user_balance
        balance = await get_user_balance(kwargs["user_id"])
        lost = int(balance * 0.5)
        result["lose_money"] = lost
        print(f"[EVENT] handle_crypto_loss: user_id={kwargs['user_id']} balance={balance} lost={lost}")
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
    """Handler: Sao Kê - Trừ % nếu giàu, tặng tiền nếu nghèo."""
    if "user_id" in kwargs:
        from database_manager import get_user_balance
        balance = await get_user_balance(kwargs["user_id"])
        
        if balance >= 5000:
            tax = int(balance * 0.1)
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
    """Handler: Hộp Mù - Random kết quả."""
    outcome = random.choices(["trash", "money", "fee"], weights=[40, 30, 30])[0]
    
    if outcome == "trash":
        result["convert_to_trash"] = True  # Giả định code chính có xử lý cờ này để biến cá thành rác
        result["message"] += "\n📦 Mở ra toàn giấy lộn! (Nhận được Rác)"
    elif outcome == "money":
        result["gain_money"] = 500
        result["message"] += "\n💰 Mở ra thấy 500 Hạt kẹp trong đáy hộp!"
    else:
        result["lose_money"] = 100
        result["message"] += "\n💸 Phải trả 100 Hạt tiền Ship COD. Cay!"
    return result

async def handle_flexing(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Flexing - Tăng tiền nhưng hỏng cần."""
    result["gain_money"] = 150
    result["durability_loss"] = -20  # Trừ nhiều độ bền
    return result

async def handle_free_cast(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Quên lắp mồi - Không tốn mồi."""
    result["gain_items"] = {"worm": 1}  # Trả lại 1 mồi (coi như không mất)
    return result

async def handle_isekai(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Isekai - Nhận Cá Isekai + Cooldown 10 phút."""
    # Nhận cá legendary từ thế giới khác
    result["gain_items"] = {"ca_isekai": 1}
    result["cooldown_increase"] = 600  # 10 phút choáng
    return result

async def handle_inflation(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Bão giá - Debuff giảm giá bán."""
    result["custom_effect"] = "market_crash"
    result["debuff_type"] = "price_drop"
    result["debuff_duration"] = 600
    return result

async def handle_hack_map(result: dict, event_data: dict, **kwargs) -> dict:
    """Handler: Hack Map - Nhận nhiều cá + Ban."""
    # Logic cộng item cần xử lý ở main cog, ở đây trả về dict
    result["bonus_catch"] = 3 
    result["cooldown_increase"] = 300  # Phạt 5 phút
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
    "gain_money_medium": handle_gain_money(100, 200),
    "gain_money_large": handle_gain_money(300, 500),
    "gain_money_huge": handle_gain_money_fixed(1000),
    "lose_money_percent": handle_lose_money_percent,
    "gain_worm_5": handle_gain_items({"worm": 5}),
    "gain_worm_10": handle_gain_items({"worm": 10}),
    "bet_loss": handle_bet_loss,
    "gain_chest_1": handle_gain_items({"treasure_chest": 1}),
    "gain_chest_2": handle_gain_items({"treasure_chest": 2}),
    "gain_pearl": handle_gain_items({"pearl": 1}),
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
}

async def trigger_random_event(cog, user_id: int, guild_id: int, rod_level: int = 1, channel=None) -> dict:
    """Trigger random event during fishing using Strategy Pattern."""
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
                    # Achievement check for global reset is handled by the stat tracking above
            except:
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
            from .constants import FISHING_EVENT_STAT_MAPPING
            if event_type in FISHING_EVENT_STAT_MAPPING:
                stat_key = FISHING_EVENT_STAT_MAPPING[event_type]
                try:
                    await increment_stat(user_id, "fishing", stat_key, 1)
                    current_value = await get_stat(user_id, "fishing", stat_key)
                    if hasattr(cog, 'bot') and hasattr(cog.bot, 'achievement_manager'):
                        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, channel)
                    print(f"[ACHIEVEMENT] Tracked {stat_key} for user {user_id} on fishing event {event_type}")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error tracking {stat_key} for {user_id}: {e}")
            
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
                result = await handler(result, event_data, user_id=user_id, cog=cog)
            else:
                print(f"[EVENTS] Warning: No handler for effect '{effect}'")
            
            return result
    
    return result

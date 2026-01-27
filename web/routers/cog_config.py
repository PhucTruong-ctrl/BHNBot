"""
Cog Configuration API - Per-module settings management with guild support
"""
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel
from typing import Any, Dict, Optional
import json
from ..database import execute, fetchone, fetchall
from ..dependencies import require_admin

router = APIRouter(prefix="/cogs", tags=["cogs"], dependencies=[Depends(require_admin)])

# =============================================================================
# CATEGORY DEFINITIONS
# =============================================================================
COG_CATEGORIES = {
    "core": {"name": "Core", "icon": "💰", "description": "Hệ thống nền tảng"},
    "game": {"name": "Games", "icon": "🎮", "description": "Minigames và giải trí"},
    "social": {"name": "Social", "icon": "💝", "description": "Tương tác xã hội"},
    "utility": {"name": "Utility", "icon": "🔧", "description": "Tiện ích"},
    "vip": {"name": "VIP", "icon": "⭐", "description": "Tính năng VIP"},
    "admin": {"name": "Admin", "icon": "🛡️", "description": "Quản trị"},
}

# =============================================================================
# COG CONFIGURATIONS
# =============================================================================
COG_CONFIGS = {
    # === CORE ===
    "economy": {
        "name": "Kinh tế",
        "icon": "💰",
        "category": "core",
        "description": "Hệ thống hạt và giao dịch",
        "settings": {
            "daily_amount": {"type": "number", "default": 100, "min": 10, "max": 10000, "label": "Điểm danh (hạt)"},
            "voice_reward_per_minute": {"type": "number", "default": 1, "min": 0, "max": 10, "label": "Thưởng voice/phút"},
            "chat_reward": {"type": "number", "default": 5, "min": 0, "max": 100, "label": "Thưởng chat"},
            "chat_cooldown": {"type": "number", "default": 60, "min": 10, "max": 600, "label": "Cooldown chat (giây)"},
            "transfer_tax_percent": {"type": "number", "default": 5, "min": 0, "max": 50, "label": "Thuế chuyển (%)"},
        }
    },
    "unified_shop": {
        "name": "Cửa hàng",
        "icon": "🛒",
        "category": "core",
        "description": "Mua bán vật phẩm",
        "settings": {
            "sell_price_percent": {"type": "number", "default": 50, "min": 10, "max": 100, "label": "Giá bán (% giá gốc)"},
            "restock_hours": {"type": "number", "default": 24, "min": 1, "max": 168, "label": "Restock (giờ)"},
            "max_purchase_per_item": {"type": "number", "default": 10, "min": 1, "max": 100, "label": "Mua tối đa/item"},
        }
    },
    # === GAMES ===
    "fishing": {
        "name": "Câu cá",
        "icon": "🎣",
        "category": "game",
        "description": "Hệ thống câu cá với 100+ loài",
        "settings": {
            "cooldown_seconds": {"type": "number", "default": 30, "min": 10, "max": 300, "label": "Cooldown (giây)"},
            "legendary_rate": {"type": "number", "default": 0.01, "min": 0, "max": 0.1, "step": 0.001, "label": "Tỷ lệ cá huyền thoại"},
            "event_bonus_multiplier": {"type": "number", "default": 1.5, "min": 1, "max": 5, "label": "Bonus event (x)"},
            "max_bait_stack": {"type": "number", "default": 100, "min": 10, "max": 1000, "label": "Mồi tối đa"},
        }
    },
    "baucua": {
        "name": "Bầu Cua",
        "icon": "🎲",
        "category": "game",
        "description": "Game Bầu Cua truyền thống",
        "settings": {
            "min_bet": {"type": "number", "default": 10, "min": 1, "max": 1000, "label": "Cược tối thiểu"},
            "max_bet": {"type": "number", "default": 10000, "min": 100, "max": 1000000, "label": "Cược tối đa"},
            "house_edge_percent": {"type": "number", "default": 2, "min": 0, "max": 10, "label": "Lợi thế nhà cái (%)"},
            "jackpot_chance": {"type": "number", "default": 0.001, "min": 0, "max": 0.01, "step": 0.0001, "label": "Tỷ lệ jackpot"},
        }
    },
    "xi_dach": {
        "name": "Xì Dách",
        "icon": "🃏",
        "category": "game",
        "description": "Game bài Xì Dách/Blackjack",
        "settings": {
            "min_bet": {"type": "number", "default": 50, "min": 10, "max": 1000, "label": "Cược tối thiểu"},
            "max_bet": {"type": "number", "default": 50000, "min": 1000, "max": 1000000, "label": "Cược tối đa"},
            "lobby_timeout_seconds": {"type": "number", "default": 60, "min": 30, "max": 180, "label": "Timeout lobby (giây)"},
            "turn_timeout_seconds": {"type": "number", "default": 30, "min": 10, "max": 60, "label": "Timeout lượt (giây)"},
            "max_players": {"type": "number", "default": 5, "min": 2, "max": 8, "label": "Số người chơi tối đa"},
            "blackjack_payout": {"type": "number", "default": 1.5, "min": 1, "max": 3, "step": 0.1, "label": "Payout Blackjack (x)"},
        }
    },
    "noi_tu": {
        "name": "Nối từ",
        "icon": "📝",
        "category": "game",
        "description": "Game nối từ tiếng Việt",
        "settings": {
            "reward_per_word": {"type": "number", "default": 5, "min": 1, "max": 50, "label": "Thưởng/từ đúng"},
            "streak_bonus": {"type": "number", "default": 2, "min": 0, "max": 20, "label": "Bonus streak/từ"},
            "max_streak_multiplier": {"type": "number", "default": 5, "min": 1, "max": 20, "label": "Nhân streak tối đa"},
            "word_timeout_seconds": {"type": "number", "default": 30, "min": 10, "max": 120, "label": "Timeout/từ (giây)"},
            "min_word_length": {"type": "number", "default": 2, "min": 1, "max": 5, "label": "Độ dài từ tối thiểu"},
            "channel_id": {"type": "text", "default": "", "label": "Channel nối từ (ID)"},
        }
    },
    "werewolf": {
        "name": "Ma Sói",
        "icon": "🐺",
        "category": "game",
        "description": "Game Ma Sói với nhiều role đặc biệt",
        "settings": {
            "min_players": {"type": "number", "default": 6, "min": 4, "max": 10, "label": "Số người tối thiểu"},
            "max_players": {"type": "number", "default": 16, "min": 8, "max": 24, "label": "Số người tối đa"},
            "day_phase_seconds": {"type": "number", "default": 300, "min": 60, "max": 600, "label": "Thời gian ban ngày (giây)"},
            "night_phase_seconds": {"type": "number", "default": 60, "min": 30, "max": 180, "label": "Thời gian ban đêm (giây)"},
            "discussion_seconds": {"type": "number", "default": 120, "min": 30, "max": 300, "label": "Thời gian thảo luận (giây)"},
            "vote_seconds": {"type": "number", "default": 60, "min": 20, "max": 120, "label": "Thời gian bỏ phiếu (giây)"},
            "enable_voice_channels": {"type": "boolean", "default": True, "label": "Sử dụng voice channel"},
            "winner_reward": {"type": "number", "default": 500, "min": 0, "max": 10000, "label": "Thưởng người thắng"},
            "participation_reward": {"type": "number", "default": 50, "min": 0, "max": 1000, "label": "Thưởng tham gia"},
        }
    },
    "aquarium": {
        "name": "Hồ cá",
        "icon": "🐠",
        "category": "game",
        "description": "Hồ cá cá nhân và tái chế",
        "settings": {
            "base_tank_slots": {"type": "number", "default": 10, "min": 5, "max": 50, "label": "Slot hồ cơ bản"},
            "max_tank_slots": {"type": "number", "default": 100, "min": 20, "max": 500, "label": "Slot hồ tối đa"},
            "recycle_value_percent": {"type": "number", "default": 30, "min": 10, "max": 100, "label": "Giá trị tái chế (%)"},
            "leaf_coin_name": {"type": "text", "default": "🍃", "label": "Icon Leaf Coin"},
            "decor_unlock_level": {"type": "number", "default": 5, "min": 1, "max": 50, "label": "Level mở decor"},
            "auto_feed_enabled": {"type": "boolean", "default": False, "label": "Tự động cho ăn"},
        }
    },
    # === SOCIAL ===
    "relationship": {
        "name": "Quan hệ",
        "icon": "💕",
        "category": "social",
        "description": "Hệ thống buddy và tình bạn",
        "settings": {
            "max_buddies": {"type": "number", "default": 5, "min": 1, "max": 20, "label": "Số buddy tối đa"},
            "buddy_xp_bonus_percent": {"type": "number", "default": 10, "min": 0, "max": 50, "label": "Bonus XP buddy (%)"},
            "gift_cooldown_hours": {"type": "number", "default": 24, "min": 1, "max": 168, "label": "CD tặng quà (giờ)"},
            "bond_level_cap": {"type": "number", "default": 10, "min": 1, "max": 100, "label": "Level bond tối đa"},
            "bond_xp_per_interaction": {"type": "number", "default": 5, "min": 1, "max": 50, "label": "XP bond/tương tác"},
            "enable_marriage": {"type": "boolean", "default": True, "label": "Cho phép kết hôn"},
        }
    },
    "social": {
        "name": "Xã hội",
        "icon": "👥",
        "category": "social",
        "description": "Thưởng voice và hoạt động",
        "settings": {
            "voice_xp_per_minute": {"type": "number", "default": 2, "min": 0, "max": 20, "label": "XP voice/phút"},
            "voice_coins_per_minute": {"type": "number", "default": 1, "min": 0, "max": 10, "label": "Hạt voice/phút"},
            "voice_xp_cap_per_day": {"type": "number", "default": 1000, "min": 100, "max": 10000, "label": "Cap XP voice/ngày"},
            "buddy_voice_bonus_percent": {"type": "number", "default": 20, "min": 0, "max": 100, "label": "Bonus voice với buddy (%)"},
            "afk_timeout_minutes": {"type": "number", "default": 5, "min": 1, "max": 30, "label": "Timeout AFK (phút)"},
            "enable_voice_leaderboard": {"type": "boolean", "default": True, "label": "Bảng xếp hạng voice"},
        }
    },
    "profile": {
        "name": "Hồ sơ",
        "icon": "👤",
        "category": "social",
        "description": "Tùy chỉnh hồ sơ cá nhân",
        "settings": {
            "default_background": {"type": "text", "default": "default", "label": "Background mặc định"},
            "enable_custom_backgrounds": {"type": "boolean", "default": True, "label": "Cho phép background tùy chỉnh"},
            "badge_slots": {"type": "number", "default": 5, "min": 1, "max": 20, "label": "Số slot huy hiệu"},
            "bio_max_length": {"type": "number", "default": 200, "min": 50, "max": 500, "label": "Độ dài bio tối đa"},
            "enable_achievements": {"type": "boolean", "default": True, "label": "Hiển thị achievement"},
            "profile_cooldown_seconds": {"type": "number", "default": 5, "min": 1, "max": 60, "label": "CD xem profile (giây)"},
        }
    },
    # === UTILITY ===
    "music": {
        "name": "Âm nhạc",
        "icon": "🎵",
        "category": "utility",
        "description": "Phát nhạc từ YouTube, Spotify",
        "settings": {
            "max_queue_size": {"type": "number", "default": 100, "min": 10, "max": 500, "label": "Queue tối đa"},
            "default_volume": {"type": "number", "default": 50, "min": 1, "max": 100, "label": "Âm lượng mặc định"},
            "auto_disconnect_minutes": {"type": "number", "default": 5, "min": 1, "max": 60, "label": "Tự ngắt (phút)"},
            "allow_playlists": {"type": "boolean", "default": True, "label": "Cho phép playlist"},
        }
    },
    "giveaway": {
        "name": "Giveaway",
        "icon": "🎁",
        "category": "utility",
        "description": "Tổ chức giveaway",
        "settings": {
            "min_duration_minutes": {"type": "number", "default": 5, "min": 1, "max": 60, "label": "Thời gian tối thiểu (phút)"},
            "max_duration_days": {"type": "number", "default": 7, "min": 1, "max": 30, "label": "Thời gian tối đa (ngày)"},
            "max_winners": {"type": "number", "default": 10, "min": 1, "max": 50, "label": "Số người thắng tối đa"},
        }
    },
    "tree": {
        "name": "Cây cối",
        "icon": "🌳",
        "category": "utility",
        "description": "Trồng và chăm sóc cây",
        "settings": {
            "water_cooldown_hours": {"type": "number", "default": 4, "min": 1, "max": 24, "label": "CD tưới (giờ)"},
            "growth_per_water": {"type": "number", "default": 10, "min": 1, "max": 100, "label": "Tăng trưởng/tưới"},
            "max_tree_level": {"type": "number", "default": 100, "min": 10, "max": 1000, "label": "Level tối đa"},
        }
    },
    "quest": {
        "name": "Nhiệm vụ",
        "icon": "📋",
        "category": "utility",
        "description": "Hệ thống nhiệm vụ hàng ngày",
        "settings": {
            "daily_quest_count": {"type": "number", "default": 3, "min": 1, "max": 10, "label": "Số quest/ngày"},
            "weekly_quest_count": {"type": "number", "default": 5, "min": 1, "max": 10, "label": "Số quest/tuần"},
            "quest_refresh_hour": {"type": "number", "default": 7, "min": 0, "max": 23, "label": "Giờ reset quest (UTC+7)"},
            "streak_bonus_percent": {"type": "number", "default": 10, "min": 0, "max": 100, "label": "Bonus streak (%)"},
            "max_streak_bonus": {"type": "number", "default": 100, "min": 0, "max": 500, "label": "Bonus streak tối đa (%)"},
            "quest_reward_multiplier": {"type": "number", "default": 1.0, "min": 0.5, "max": 5, "step": 0.1, "label": "Nhân thưởng quest"},
        }
    },
    "seasonal": {
        "name": "Sự kiện",
        "icon": "🎄",
        "category": "utility",
        "description": "Quản lý sự kiện theo mùa",
        "settings": {
            "current_event": {"type": "text", "default": "", "label": "Event hiện tại (ID)"},
            "event_bonus_multiplier": {"type": "number", "default": 2.0, "min": 1, "max": 10, "step": 0.1, "label": "Bonus event (x)"},
            "event_shop_enabled": {"type": "boolean", "default": True, "label": "Bật shop event"},
            "daily_event_points": {"type": "number", "default": 100, "min": 0, "max": 1000, "label": "Điểm event/ngày"},
            "event_currency_name": {"type": "text", "default": "🎄", "label": "Icon tiền event"},
            "leaderboard_rewards_enabled": {"type": "boolean", "default": True, "label": "Thưởng bảng xếp hạng"},
        }
    },
    "bump_reminder": {
        "name": "Bump Reminder",
        "icon": "📢",
        "category": "utility",
        "description": "Nhắc bump server",
        "settings": {
            "reminder_channel_id": {"type": "text", "default": "", "label": "Channel nhắc (ID)"},
            "bump_cooldown_hours": {"type": "number", "default": 2, "min": 1, "max": 24, "label": "CD bump (giờ)"},
            "reward_per_bump": {"type": "number", "default": 50, "min": 0, "max": 500, "label": "Thưởng/bump"},
            "ping_role_id": {"type": "text", "default": "", "label": "Role ping (ID)"},
            "auto_remind": {"type": "boolean", "default": True, "label": "Tự động nhắc"},
        }
    },
    # === VIP ===
    "vip": {
        "name": "VIP",
        "icon": "⭐",
        "category": "vip",
        "description": "Hệ thống VIP 3 tier",
        "settings": {
            "bronze_daily_bonus": {"type": "number", "default": 50, "min": 0, "max": 1000, "label": "Bronze bonus/ngày"},
            "silver_daily_bonus": {"type": "number", "default": 100, "min": 0, "max": 2000, "label": "Silver bonus/ngày"},
            "gold_daily_bonus": {"type": "number", "default": 200, "min": 0, "max": 5000, "label": "Gold bonus/ngày"},
            "fishing_cooldown_reduction": {"type": "number", "default": 20, "min": 0, "max": 50, "label": "Giảm CD câu cá (%)"},
        }
    },
    "auto_fishing": {
        "name": "Auto Fishing",
        "icon": "🤖",
        "category": "vip",
        "description": "Câu cá tự động VIP",
        "settings": {
            "enabled": {"type": "boolean", "default": True, "label": "Bật tính năng"},
            "vip_only": {"type": "boolean", "default": True, "label": "Chỉ VIP"},
            "storage_base": {"type": "number", "default": 20, "min": 5, "max": 100, "label": "Kho cơ bản"},
            "storage_max": {"type": "number", "default": 200, "min": 50, "max": 1000, "label": "Kho tối đa"},
            "upgrade_cost_multiplier": {"type": "number", "default": 1.5, "min": 1, "max": 3, "step": 0.1, "label": "Nhân giá nâng cấp"},
            "fish_per_hour": {"type": "number", "default": 10, "min": 1, "max": 60, "label": "Cá/giờ"},
            "legendary_chance": {"type": "number", "default": 0.005, "min": 0, "max": 0.05, "step": 0.001, "label": "Tỷ lệ cá hiếm"},
        }
    },
    "pets": {
        "name": "Thú cưng",
        "icon": "🐾",
        "category": "vip",
        "description": "Hệ thống thú cưng đồng hành",
        "settings": {
            "max_pets": {"type": "number", "default": 3, "min": 1, "max": 10, "label": "Số pet tối đa"},
            "pet_egg_base_cost": {"type": "number", "default": 1000, "min": 100, "max": 10000, "label": "Giá trứng cơ bản"},
            "feed_cooldown_hours": {"type": "number", "default": 4, "min": 1, "max": 24, "label": "CD cho ăn (giờ)"},
            "hunger_decay_per_hour": {"type": "number", "default": 5, "min": 1, "max": 20, "label": "Đói/giờ"},
            "pet_xp_bonus_percent": {"type": "number", "default": 5, "min": 0, "max": 50, "label": "Bonus XP từ pet (%)"},
            "enable_pet_battles": {"type": "boolean", "default": False, "label": "Cho phép đấu pet"},
            "max_pet_level": {"type": "number", "default": 50, "min": 10, "max": 100, "label": "Level pet tối đa"},
        }
    },
    # === ADMIN ===
    "admin": {
        "name": "Quản trị",
        "icon": "🛡️",
        "category": "admin",
        "description": "Cài đặt quản trị server",
        "settings": {
            "command_prefix": {"type": "text", "default": "!", "label": "Prefix lệnh"},
            "mod_log_channel_id": {"type": "text", "default": "", "label": "Channel mod log (ID)"},
            "enable_auto_mod": {"type": "boolean", "default": False, "label": "Bật auto-mod"},
            "maintenance_mode": {"type": "boolean", "default": False, "label": "Chế độ bảo trì"},
            "announcement_channel_id": {"type": "text", "default": "", "label": "Channel thông báo (ID)"},
            "bot_nickname": {"type": "text", "default": "", "label": "Nickname bot"},
        }
    },
}

# =============================================================================
# DATABASE
# =============================================================================
async def ensure_cog_config_table():
    """Ensure cog_config table exists with enabled column."""
    await execute('''
        CREATE TABLE IF NOT EXISTS cog_config (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT DEFAULT 0,
            cog_name VARCHAR(50) NOT NULL,
            settings JSONB DEFAULT '{}',
            enabled BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(guild_id, cog_name)
        )
    ''')
    try:
        await execute('ALTER TABLE cog_config ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT TRUE')
    except Exception:
        pass


async def _log_audit(request: Request, action: str, cog_name: str, details: dict):
    """Log audit entry for cog changes."""
    try:
        from .audit import log_action
        from ..dependencies import get_current_user
        user = get_current_user(request)
        ip = request.client.host if request.client else None
        await log_action(
            admin_id=user["id"],
            admin_name=user["username"],
            action=action,
            target_type="cog",
            target_id=cog_name,
            details=details,
            ip_address=ip
        )
    except Exception:
        pass


# =============================================================================
# MODELS
# =============================================================================
class CogSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


class CogToggle(BaseModel):
    enabled: bool


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.get("/categories")
async def get_categories():
    """Return available cog categories."""
    return {"categories": COG_CATEGORIES}


@router.get("/")
async def get_cog_list(guild_id: Optional[int] = Query(default=0)):
    """List all cogs with their enabled status for a guild."""
    await ensure_cog_config_table()
    gid = guild_id or 0
    
    rows = await fetchall(
        "SELECT cog_name, enabled FROM cog_config WHERE guild_id = $1",
        (gid,)
    )
    db_states = {r["cog_name"]: r["enabled"] for r in rows}
    
    cogs = []
    for cog_id, config in COG_CONFIGS.items():
        cogs.append({
            "id": cog_id,
            "name": config["name"],
            "icon": config["icon"],
            "category": config["category"],
            "description": config["description"],
            "enabled": db_states.get(cog_id, True),
        })
    
    return {"cogs": cogs}


@router.get("/{cog_name}")
async def get_cog_config(cog_name: str, guild_id: Optional[int] = Query(default=0)):
    """Get detailed config for a specific cog."""
    if cog_name not in COG_CONFIGS:
        raise HTTPException(status_code=404, detail="Cog not found")
    
    await ensure_cog_config_table()
    gid = guild_id or 0
    config = COG_CONFIGS[cog_name]
    
    row = await fetchone(
        "SELECT settings, enabled FROM cog_config WHERE guild_id = $1 AND cog_name = $2",
        (gid, cog_name)
    )
    
    saved_settings = row["settings"] if row else {}
    enabled = row["enabled"] if row else True
    
    settings_with_values = {}
    for key, schema in config["settings"].items():
        settings_with_values[key] = {
            **schema,
            "value": saved_settings.get(key, schema["default"])
        }
    
    return {
        "id": cog_name,
        "name": config["name"],
        "icon": config["icon"],
        "category": config["category"],
        "description": config["description"],
        "enabled": enabled,
        "settings": settings_with_values
    }


@router.post("/{cog_name}")
async def update_cog_config(
    cog_name: str,
    data: CogSettingsUpdate,
    request: Request,
    guild_id: Optional[int] = Query(default=0)
):
    """Update cog settings for a guild."""
    if cog_name not in COG_CONFIGS:
        raise HTTPException(status_code=404, detail="Cog not found")
    
    await ensure_cog_config_table()
    gid = guild_id or 0
    config = COG_CONFIGS[cog_name]
    validated = {}
    
    for key, value in data.settings.items():
        if key not in config["settings"]:
            continue
        schema = config["settings"][key]
        if schema["type"] == "number":
            validated[key] = max(schema.get("min", 0), min(schema.get("max", 999999), float(value)))
        elif schema["type"] == "boolean":
            validated[key] = bool(value)
        else:
            validated[key] = str(value)
    
    await execute('''
        INSERT INTO cog_config (guild_id, cog_name, settings, updated_at)
        VALUES ($1, $2, $3::jsonb, NOW())
        ON CONFLICT (guild_id, cog_name)
        DO UPDATE SET settings = $3::jsonb, updated_at = NOW()
    ''', gid, cog_name, json.dumps(validated))
    
    await _log_audit(request, "cog_config_update", cog_name, {"guild_id": gid, "settings": validated})
    return {"success": True, "cog": cog_name, "settings": validated}


@router.post("/{cog_name}/toggle")
async def toggle_cog(
    cog_name: str,
    data: CogToggle,
    request: Request,
    guild_id: Optional[int] = Query(default=0)
):
    """Enable or disable a cog for a guild."""
    if cog_name not in COG_CONFIGS:
        raise HTTPException(status_code=404, detail="Cog not found")
    
    await ensure_cog_config_table()
    gid = guild_id or 0
    
    await execute('''
        INSERT INTO cog_config (guild_id, cog_name, enabled, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (guild_id, cog_name)
        DO UPDATE SET enabled = $3, updated_at = NOW()
    ''', gid, cog_name, data.enabled)
    
    await _log_audit(request, "cog_toggle", cog_name, {"guild_id": gid, "enabled": data.enabled})
    return {"success": True, "cog": cog_name, "enabled": data.enabled}

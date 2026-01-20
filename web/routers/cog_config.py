"""
Cog Configuration API - Per-module settings management
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Any, Dict, Optional
from ..database import execute, fetchone, fetchall
from ..dependencies import require_admin

router = APIRouter(prefix="/cogs", tags=["cogs"], dependencies=[Depends(require_admin)])


COG_CONFIGS = {
    "fishing": {
        "name": "Câu cá",
        "description": "Hệ thống câu cá với 100+ loài",
        "settings": {
            "cooldown_seconds": {"type": "number", "default": 30, "min": 10, "max": 300, "label": "Cooldown (giây)"},
            "legendary_rate": {"type": "number", "default": 0.01, "min": 0, "max": 0.1, "step": 0.001, "label": "Tỷ lệ cá huyền thoại"},
            "event_bonus_multiplier": {"type": "number", "default": 1.5, "min": 1, "max": 5, "label": "Bonus event (x)"},
            "max_bait_stack": {"type": "number", "default": 100, "min": 10, "max": 1000, "label": "Mồi tối đa"},
        }
    },
    "economy": {
        "name": "Kinh tế",
        "description": "Hệ thống hạt và giao dịch",
        "settings": {
            "daily_amount": {"type": "number", "default": 100, "min": 10, "max": 10000, "label": "Điểm danh (hạt)"},
            "voice_reward_per_minute": {"type": "number", "default": 1, "min": 0, "max": 10, "label": "Thưởng voice/phút"},
            "chat_reward": {"type": "number", "default": 5, "min": 0, "max": 100, "label": "Thưởng chat"},
            "chat_cooldown": {"type": "number", "default": 60, "min": 10, "max": 600, "label": "Cooldown chat (giây)"},
            "transfer_tax_percent": {"type": "number", "default": 5, "min": 0, "max": 50, "label": "Thuế chuyển (%)"},
        }
    },
    "gambling": {
        "name": "Cờ bạc",
        "description": "Bầu Cua, Xì Dách, Slot",
        "settings": {
            "min_bet": {"type": "number", "default": 10, "min": 1, "max": 1000, "label": "Cược tối thiểu"},
            "max_bet": {"type": "number", "default": 10000, "min": 100, "max": 1000000, "label": "Cược tối đa"},
            "house_edge_percent": {"type": "number", "default": 2, "min": 0, "max": 10, "label": "Lợi thế nhà cái (%)"},
            "jackpot_chance": {"type": "number", "default": 0.001, "min": 0, "max": 0.01, "step": 0.0001, "label": "Tỷ lệ jackpot"},
        }
    },
    "shop": {
        "name": "Cửa hàng",
        "description": "Mua bán vật phẩm",
        "settings": {
            "sell_price_percent": {"type": "number", "default": 50, "min": 10, "max": 100, "label": "Giá bán (% giá gốc)"},
            "restock_hours": {"type": "number", "default": 24, "min": 1, "max": 168, "label": "Restock (giờ)"},
            "max_purchase_per_item": {"type": "number", "default": 10, "min": 1, "max": 100, "label": "Mua tối đa/item"},
        }
    },
    "music": {
        "name": "Âm nhạc",
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
        "description": "Tổ chức giveaway",
        "settings": {
            "min_duration_minutes": {"type": "number", "default": 5, "min": 1, "max": 60, "label": "Thời gian tối thiểu (phút)"},
            "max_duration_days": {"type": "number", "default": 7, "min": 1, "max": 30, "label": "Thời gian tối đa (ngày)"},
            "max_winners": {"type": "number", "default": 10, "min": 1, "max": 50, "label": "Số người thắng tối đa"},
        }
    },
    "vip": {
        "name": "VIP",
        "description": "Hệ thống VIP 3 tier",
        "settings": {
            "bronze_daily_bonus": {"type": "number", "default": 50, "min": 0, "max": 1000, "label": "Bronze bonus/ngày"},
            "silver_daily_bonus": {"type": "number", "default": 100, "min": 0, "max": 2000, "label": "Silver bonus/ngày"},
            "gold_daily_bonus": {"type": "number", "default": 200, "min": 0, "max": 5000, "label": "Gold bonus/ngày"},
            "fishing_cooldown_reduction": {"type": "number", "default": 20, "min": 0, "max": 50, "label": "Giảm CD câu cá (%)"},
        }
    },
    "tree": {
        "name": "Cây cối",
        "description": "Trồng và chăm sóc cây",
        "settings": {
            "water_cooldown_hours": {"type": "number", "default": 4, "min": 1, "max": 24, "label": "CD tưới (giờ)"},
            "growth_per_water": {"type": "number", "default": 10, "min": 1, "max": 100, "label": "Tăng trưởng/tưới"},
            "max_tree_level": {"type": "number", "default": 100, "min": 10, "max": 1000, "label": "Level tối đa"},
        }
    },
}


async def ensure_cog_config_table():
    await execute('''
        CREATE TABLE IF NOT EXISTS cog_config (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT DEFAULT 0,
            cog_name VARCHAR(50) NOT NULL,
            settings JSONB DEFAULT '{}',
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(guild_id, cog_name)
        )
    ''')


@router.get("/")
async def get_cog_list():
    return {"cogs": [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in COG_CONFIGS.items()
    ]}


@router.get("/{cog_name}")
async def get_cog_config(cog_name: str):
    if cog_name not in COG_CONFIGS:
        raise HTTPException(status_code=404, detail="Cog not found")
    
    await ensure_cog_config_table()
    
    config = COG_CONFIGS[cog_name]
    row = await fetchone(
        "SELECT settings FROM cog_config WHERE guild_id = 0 AND cog_name = $1",
        (cog_name,)
    )
    
    saved_settings = row["settings"] if row else {}
    
    settings_with_values = {}
    for key, schema in config["settings"].items():
        settings_with_values[key] = {
            **schema,
            "value": saved_settings.get(key, schema["default"])
        }
    
    return {
        "id": cog_name,
        "name": config["name"],
        "description": config["description"],
        "settings": settings_with_values
    }


class CogSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


@router.post("/{cog_name}")
async def update_cog_config(cog_name: str, data: CogSettingsUpdate, request: Request):
    if cog_name not in COG_CONFIGS:
        raise HTTPException(status_code=404, detail="Cog not found")
    
    await ensure_cog_config_table()
    
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
    
    import json
    await execute('''
        INSERT INTO cog_config (guild_id, cog_name, settings, updated_at)
        VALUES (0, $1, $2::jsonb, NOW())
        ON CONFLICT (guild_id, cog_name)
        DO UPDATE SET settings = $2::jsonb, updated_at = NOW()
    ''', cog_name, json.dumps(validated))
    
    from .audit import log_action
    from ..dependencies import get_current_user
    try:
        user = get_current_user(request)
        ip = request.client.host if request.client else None
        await log_action(
            admin_id=user["id"],
            admin_name=user["username"],
            action="cog_config_update",
            target_type="cog",
            target_id=cog_name,
            details={"settings": validated},
            ip_address=ip
        )
    except Exception:
        pass
    
    return {"success": True, "cog": cog_name, "settings": validated}

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..database import fetchall, fetchone, execute
from ..dependencies import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class ModuleToggle(BaseModel):
    enabled: bool


class ModuleInfo(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    usage_count: int
    last_used: Optional[str]


MODULES = {
    "fishing": {"name": "Câu cá", "description": "Hệ thống câu cá với 100+ loài cá"},
    "economy": {"name": "Kinh tế", "description": "Hạt, cửa hàng, giao dịch"},
    "gambling": {"name": "Cờ bạc", "description": "Bầu Cua, Xì Dách, Slot"},
    "werewolf": {"name": "Ma Sói", "description": "Game Ma Sói đầy đủ vai trò"},
    "music": {"name": "Âm nhạc", "description": "Phát nhạc từ YouTube, Spotify"},
    "tree": {"name": "Cây cối", "description": "Trồng và chăm sóc cây"},
    "aquarium": {"name": "Bể cá", "description": "Bể cá và trang trí"},
    "relationship": {"name": "Quan hệ", "description": "Kết bạn, tặng quà"},
    "achievements": {"name": "Thành tựu", "description": "Hệ thống thành tựu"},
    "giveaway": {"name": "Giveaway", "description": "Tổ chức giveaway"},
    "noitu": {"name": "Nối Từ", "description": "Game nối từ"},
    "vip": {"name": "VIP", "description": "Hệ thống VIP"},
}


async def ensure_module_settings_table():
    await execute('''
        CREATE TABLE IF NOT EXISTS module_settings (
            guild_id BIGINT NOT NULL,
            module_id VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            settings JSONB DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (guild_id, module_id)
        )
    ''')


@router.get("/")
async def get_modules():
    await ensure_module_settings_table()
    
    # Get all module settings from DB (guild_id=0 for global)
    settings_rows = await fetchall('''
        SELECT module_id, enabled FROM module_settings WHERE guild_id = 0
    ''')
    enabled_map = {row["module_id"]: row["enabled"] for row in settings_rows}
    
    # Get usage counts from command_usage table
    usage_rows = await fetchall('''
        SELECT LOWER(cog_name) as cog, COUNT(*) as count, MAX(used_at) as last_used
        FROM command_usage 
        WHERE cog_name IS NOT NULL
        GROUP BY LOWER(cog_name)
    ''')
    usage_map = {row["cog"]: {"count": row["count"], "last_used": row["last_used"]} for row in usage_rows}
    
    modules = []
    for mod_id, mod_info in MODULES.items():
        usage_info = usage_map.get(mod_id, {"count": 0, "last_used": None})
        modules.append({
            "id": mod_id,
            "name": mod_info["name"],
            "description": mod_info["description"],
            "enabled": enabled_map.get(mod_id, True),  # Default True if not in DB
            "usage_count": usage_info["count"],
            "last_used": str(usage_info["last_used"]) if usage_info["last_used"] else None
        })
    
    return {"modules": modules}


@router.get("/{module_id}")
async def get_module(module_id: str):
    if module_id not in MODULES:
        raise HTTPException(status_code=404, detail="Module not found")
    
    await ensure_module_settings_table()
    
    # Get settings from DB
    row = await fetchone('''
        SELECT enabled, settings FROM module_settings
        WHERE guild_id = 0 AND module_id = $1
    ''', module_id)
    
    mod_info = MODULES[module_id]
    return {
        "id": module_id,
        "name": mod_info["name"],
        "description": mod_info["description"],
        "enabled": row["enabled"] if row else True,
        "settings": row["settings"] if row else {}
    }


@router.post("/{module_id}/toggle")
async def toggle_module(module_id: str, data: ModuleToggle, request: Request):
    if module_id not in MODULES:
        raise HTTPException(status_code=404, detail="Module not found")
    
    await ensure_module_settings_table()
    
    await execute('''
        INSERT INTO module_settings (guild_id, module_id, enabled, updated_at)
        VALUES (0, $1, $2, NOW())
        ON CONFLICT (guild_id, module_id)
        DO UPDATE SET enabled = $2, updated_at = NOW()
    ''', module_id, data.enabled)
    
    from .audit import log_action
    from ..dependencies import get_current_user
    try:
        user = get_current_user(request)
        ip = request.client.host if request.client else None
        await log_action(
            admin_id=user["id"],
            admin_name=user["username"],
            action="module_toggle",
            target_type="module",
            target_id=module_id,
            details={"enabled": data.enabled, "module_name": MODULES[module_id]["name"]},
            ip_address=ip
        )
    except Exception:
        pass
    
    return {
        "success": True,
        "module_id": module_id,
        "enabled": data.enabled
    }


@router.get("/{module_id}/settings")
async def get_module_settings(module_id: str, guild_id: int = 0):
    if module_id not in MODULES:
        raise HTTPException(status_code=404, detail="Module not found")
    
    await ensure_module_settings_table()
    
    row = await fetchone('''
        SELECT settings FROM module_settings
        WHERE guild_id = $1 AND module_id = $2
    ''', guild_id, module_id)
    
    return {"settings": row[0] if row else {}}


@router.post("/{module_id}/settings")
async def update_module_settings(module_id: str, settings: dict, guild_id: int = 0):
    if module_id not in MODULES:
        raise HTTPException(status_code=404, detail="Module not found")
    
    await ensure_module_settings_table()
    
    import json
    await execute('''
        INSERT INTO module_settings (guild_id, module_id, settings, updated_at)
        VALUES ($1, $2, $3::jsonb, NOW())
        ON CONFLICT (guild_id, module_id)
        DO UPDATE SET settings = $3::jsonb, updated_at = NOW()
    ''', guild_id, module_id, json.dumps(settings))
    
    return {"success": True}

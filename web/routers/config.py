
"""
BHNBot Admin Panel - Game Configuration Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
import time

from ..database import fetchone, execute
from ..config import ROOT_DIR

router = APIRouter()

# Path to settings file
SETTINGS_PATH = os.path.join(ROOT_DIR, "configs", "settings.py")


class GameConfig(BaseModel):
    """Game configuration updates."""
    worm_cost: Optional[int] = None
    fish_bucket_limit: Optional[int] = None
    npc_encounter_chance: Optional[float] = None
    daily_bonus: Optional[int] = None
    chat_reward_min: Optional[int] = None
    chat_reward_max: Optional[int] = None


@router.get("/")
async def get_config() -> Dict[str, Any]:
    """Get current game configuration."""
    # Get server configs from DB
    server_config = await fetchone("SELECT * FROM server_config LIMIT 1")
    
    # Read current settings.py values
    settings = {}
    try:
        with open(SETTINGS_PATH, 'r') as f:
            content = f.read()
            # Parse key values (simple extraction)
            import re
            patterns = {
                'worm_cost': r'WORM_COST\s*=\s*(\d+)',
                'fish_bucket_limit': r'FISH_BUCKET_LIMIT\s*=\s*(\d+)',
                'npc_encounter_chance': r'NPC_ENCOUNTER_CHANCE\s*=\s*([\d.]+)',
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    value = match.group(1)
                    settings[key] = float(value) if '.' in value else int(value)
    except Exception as e:
        settings["error"] = str(e)
    
    return {
        "server_config": dict(server_config) if server_config else {},
        "game_settings": settings
    }


@router.post("/")
async def update_config(config: GameConfig) -> Dict[str, Any]:
    """Update game configuration and trigger Hot Reload."""
    updates = config.model_dump(exclude_unset=True)
    
    if not updates:
        return {"status": "no_change"}

    # 1. Update DB for Hot Reload Signal (Using global_event_state table)
    # Note: Game settings are file-based (settings.py), so we don't store them in DB.
    # We only update the timestamp to trigger bot reload.
    
    timestamp = str(int(time.time()))
    # Use global_event_state as a KV store for system signals
    await execute(
        """
        INSERT INTO global_event_state (event_key, state_data, updated_at) 
        VALUES ('last_config_update', $1, CURRENT_TIMESTAMP)
        ON CONFLICT (event_key) DO UPDATE SET state_data = $1, updated_at = CURRENT_TIMESTAMP
        """, 
        (timestamp,)
    )
    
    # 2. Update settings.py file (for persistence)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            updated_line = False
            for key, value in updates.items():
                # Simple variable assignment check
                if line.strip().upper().startswith(f"{key.upper()} ="):
                    # Preserve comments if any
                    comment = ""
                    if "#" in line:
                        comment = " # " + line.split("#", 1)[1].strip()
                    
                    # Handle types
                    val_str = str(value)
                    if isinstance(value, str):
                        val_str = f'"{value}"'
                    
                    new_lines.append(f"{key.upper()} = {val_str}{comment}\n")
                    updated_line = True
                    break
            
            if not updated_line:
                new_lines.append(line)
        
        # Write back
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        return {"status": "success", "note": "Config updated via Hot Reload Signal"}
    except Exception as e:
        return {"status": "partial_success", "note": f"DB updated but file write failed: {e}"}


@router.get("/events")
async def get_event_config() -> Dict[str, Any]:
    """Get event configuration from JSON files."""
    try:
        data_dir = os.path.join(ROOT_DIR, "data")
        
        # Try different possible filenames since user might have standard names
        files_to_check = {
            "disasters": "disaster_events.json",
            "sell_events": "sell_events.json"
        }
        
        result = {}
        for key, filename in files_to_check.items():
            path = os.path.join(data_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Summary for large files
                        if key == "sell_events":
                            result[key] = {
                                "total": len(data.get("events", {})),
                                "bad_events": sum(1 for e in data.get("events", {}).values() if e.get("type") == "bad")
                            }
                        else:
                            result[key] = data
                except Exception as e:
                    result[key] = {"error": str(e)}
            else:
                result[key] = "File not found"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

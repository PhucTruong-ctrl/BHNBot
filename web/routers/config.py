"""
BHNBot Admin Panel - Game Configuration Router

Endpoints for viewing and updating game settings.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os

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
    """Get current game configuration.
    
    Reads from server_config table and settings.py
    """
    # Get server configs from DB
    server_config = await fetchone(
        "SELECT * FROM server_config LIMIT 1"
    )
    
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
    """Update game configuration.
    
    Note: This updates settings.py - requires bot restart to take effect.
    For production, consider moving these to database.
    """
    updates = []
    
    try:
        with open(SETTINGS_PATH, 'r') as f:
            content = f.read()
        
        import re
        
        if config.worm_cost is not None:
            content = re.sub(
                r'WORM_COST\s*=\s*\d+',
                f'WORM_COST = {config.worm_cost}',
                content
            )
            updates.append(f"WORM_COST = {config.worm_cost}")
        
        if config.fish_bucket_limit is not None:
            content = re.sub(
                r'FISH_BUCKET_LIMIT\s*=\s*\d+',
                f'FISH_BUCKET_LIMIT = {config.fish_bucket_limit}',
                content
            )
            updates.append(f"FISH_BUCKET_LIMIT = {config.fish_bucket_limit}")
        
        if config.npc_encounter_chance is not None:
            content = re.sub(
                r'NPC_ENCOUNTER_CHANCE\s*=\s*[\d.]+',
                f'NPC_ENCOUNTER_CHANCE = {config.npc_encounter_chance}',
                content
            )
            updates.append(f"NPC_ENCOUNTER_CHANCE = {config.npc_encounter_chance}")
        
        with open(SETTINGS_PATH, 'w') as f:
            f.write(content)
        
        import logging
        logger = logging.getLogger("AdminPanel")
        logger.info(f"[ADMIN] Config updated: {updates}")
        
        return {
            "status": "success",
            "updates": updates,
            "note": "Bot restart required for changes to take effect"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_event_config() -> Dict[str, Any]:
    """Get event configuration from JSON files."""
    events = {}
    
    data_dir = os.path.join(ROOT_DIR, "data")
    
    # Read disaster events
    try:
        with open(os.path.join(data_dir, "disaster_events.json"), 'r') as f:
            events["disasters"] = json.load(f)
    except Exception as e:
        events["disasters"] = {"error": str(e)}
    
    # Read sell events summary (too large to return full)
    try:
        with open(os.path.join(data_dir, "sell_events.json"), 'r') as f:
            data = json.load(f)
            events["sell_events"] = {
                "total": len(data.get("events", {})),
                "bad_events": sum(1 for e in data.get("events", {}).values() if e.get("type") == "bad")
            }
    except Exception as e:
        events["sell_events"] = {"error": str(e)}
    
    return events

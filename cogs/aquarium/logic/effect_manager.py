import json
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("EffectManager")

class EffectManager:
    """
    Centralized Manager for Global Gameplay Effects.
    Handles Set Bonuses, VIP Perks, and Item Buffs.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EffectManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.sets_data: Dict[str, dict] = {}
        self.sets_path = "data/sets/feng_shui_sets.json"
        
        self.load_sets()
        self._initialized = True
        
    def load_sets(self) -> bool:
        """Load set definitions from JSON."""
        try:
            from core.data_cache import data_cache
            cached = data_cache.get_feng_shui_sets()
            if cached:
                self.sets_data = cached.get("sets", {})
                logger.info(f"Loaded {len(self.sets_data)} Feng Shui Sets from cache.")
                return True
        except Exception:
            pass
        
        if not os.path.exists(self.sets_path):
            logger.error(f"Sets config not found: {self.sets_path}")
            return False
            
        try:
            with open(self.sets_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sets_data = data.get("sets", {})
                logger.info(f"Loaded {len(self.sets_data)} Feng Shui Sets from file.")
                return True
        except Exception as e:
            logger.error(f"Error loading sets: {e}")
            return False

    async def get_active_sets(self, user_id: int) -> List[dict]:
        """
        Determine which sets are active for a user based on their placed decor.
        Circular Dependency Avoidance: We assume HousingEngine exposes get_slots via a simple query,
        but HousingEngine might depend on EffectManager. Ideally, EffectManager queries DB directly or
        HousingEngine passes slots. 
        
        For clean architecture, we will use HousingEngine static method (if not cyclic).
        Or better, we query the DB directly here for slots to be independent.
        """
        from cogs.aquarium.logic.housing import HousingEngine
        
        # Get Placed Items
        current_slots = await HousingEngine.get_slots(user_id)
        placed_items = set(item for item in current_slots if item)
        
        active = []
        for key, set_data in self.sets_data.items():
            required = set(set_data.get("required", []))
            if not required: continue
            
            if required.issubset(placed_items):
                # Inject key if missing
                if "key" not in set_data: set_data["key"] = key
                active.append(set_data)
                
        return active

    async def get_total_bonus(self, user_id: int, effect_type: str) -> float:
        """
        Calculate total generic bonus for a specific effect type.
        (e.g., 'harvest_bonus_percent', 'sell_bonus_percent')
        """
        total = 0.0
        active_sets = await self.get_active_sets(user_id)
        
        for s in active_sets:
            effects = s.get("effects", {})
            val = effects.get(effect_type, 0)
            total += val
            
        return total

# Global Instance
effect_manager = EffectManager()

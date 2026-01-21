"""
Loadout Service - Activity-Bound Decoration Configurations

Manages user loadouts for different activities.
Each loadout binds to an activity type and auto-applies when that activity triggers.
"""

from typing import List, Optional, Dict, Any
from ..models import Loadout, HomeSlot, UserAquarium
from .effect_manager import SetsDataLoader, get_effect_manager
from core.logging import get_logger

logger = get_logger("aquarium_loadout_service")

# Valid activity types that can have loadouts
ACTIVITY_TYPES = [
    "fishing",      # Fishing bonuses (catch_rate, rare_chance)
    "harvest",      # Tree harvest bonuses (seed_bonus)
    "sell",         # Selling bonuses (sell_price_bonus)
    "passive",      # Passive income (passive_income)
    "seasonal",     # Seasonal minigames (minigame_bonus)
    "quest",        # Quest rewards (quest_reward_bonus)
    "relationship", # Gift value (gift_value_bonus)
    "gambling",     # Gambling luck (gambling_luck)
]

# Map effect types to activities for auto-activation
EFFECT_TO_ACTIVITY = {
    "catch_rate_bonus": "fishing",
    "rare_chance_bonus": "fishing",
    "legendary_chance_bonus": "fishing",
    "seed_bonus": "harvest",
    "sell_price_bonus": "sell",
    "passive_income": "passive",
    "minigame_bonus": "seasonal",
    "quest_reward_bonus": "quest",
    "gift_value_bonus": "relationship",
    "gambling_luck": "gambling",
    "all_bonus": "global",  # All bonus applies globally
}


class LoadoutService:
    """
    Service for managing user loadouts.
    
    Usage:
        service = LoadoutService()
        await service.create_loadout(user_id, "Fishing Build", "fishing", [item1, item2, ...])
        await service.activate_loadout(user_id, "Fishing Build")
        await service.get_active_loadout_for_activity(user_id, "fishing")
    """
    
    @staticmethod
    async def create_loadout(
        user_id: int,
        name: str,
        activity: str,
        items: List[Optional[str]]
    ) -> Loadout:
        """
        Create a new loadout for a user.
        
        Args:
            user_id: Discord user ID
            name: Loadout name (max 50 chars)
            activity: Activity type (fishing, harvest, sell, etc.)
            items: List of item IDs for slots 0-4 (None for empty slots)
            
        Returns:
            Created Loadout instance
            
        Raises:
            ValueError: If activity type is invalid or loadout name exists
        """
        if activity not in ACTIVITY_TYPES:
            raise ValueError(f"Invalid activity type: {activity}. Must be one of: {ACTIVITY_TYPES}")
        
        # Ensure user exists
        user, _ = await UserAquarium.get_or_create(user_id=user_id)
        
        # Check if name already exists
        existing = await Loadout.filter(user_id=user_id, name=name).first()
        if existing:
            raise ValueError(f"Loadout '{name}' already exists")
        
        # Validate items exist in sets.json
        items_data = SetsDataLoader.get_items()
        for item_id in items:
            if item_id and item_id not in items_data:
                raise ValueError(f"Item '{item_id}' not found in decoration catalog")
        
        # Pad items list to 5 slots
        items = (items + [None] * 5)[:5]
        
        loadout = await Loadout.create(
            user_id=user_id,
            name=name,
            activity=activity,
            slot_0=items[0],
            slot_1=items[1],
            slot_2=items[2],
            slot_3=items[3],
            slot_4=items[4],
            is_active=False
        )
        
        logger.info(f"[LOADOUT] Created '{name}' for user {user_id} (activity: {activity})")
        return loadout
    
    @staticmethod
    async def get_loadouts(user_id: int) -> List[Loadout]:
        """Get all loadouts for a user."""
        return await Loadout.filter(user_id=user_id).all()
    
    @staticmethod
    async def get_loadout_by_name(user_id: int, name: str) -> Optional[Loadout]:
        """Get a specific loadout by name."""
        return await Loadout.filter(user_id=user_id, name=name).first()
    
    @staticmethod
    async def get_active_loadout_for_activity(user_id: int, activity: str) -> Optional[Loadout]:
        """
        Get the active loadout for a specific activity.
        
        Args:
            user_id: Discord user ID
            activity: Activity type
            
        Returns:
            Active Loadout for that activity, or None
        """
        return await Loadout.filter(
            user_id=user_id,
            activity=activity,
            is_active=True
        ).first()
    
    @staticmethod
    async def activate_loadout(user_id: int, name: str) -> bool:
        """
        Activate a loadout (deactivates other loadouts for same activity).
        
        Args:
            user_id: Discord user ID
            name: Loadout name to activate
            
        Returns:
            True if activation succeeded
        """
        loadout = await Loadout.filter(user_id=user_id, name=name).first()
        if not loadout:
            return False
        
        # Deactivate all other loadouts for same activity
        await Loadout.filter(
            user_id=user_id,
            activity=loadout.activity
        ).update(is_active=False)
        
        # Activate this loadout
        loadout.is_active = True
        await loadout.save()
        
        logger.info(f"[LOADOUT] Activated '{name}' for user {user_id} (activity: {loadout.activity})")
        return True
    
    @staticmethod
    async def deactivate_loadout(user_id: int, name: str) -> bool:
        """Deactivate a specific loadout."""
        updated = await Loadout.filter(
            user_id=user_id,
            name=name
        ).update(is_active=False)
        return updated > 0
    
    @staticmethod
    async def delete_loadout(user_id: int, name: str) -> bool:
        """Delete a loadout."""
        deleted = await Loadout.filter(user_id=user_id, name=name).delete()
        if deleted:
            logger.info(f"[LOADOUT] Deleted '{name}' for user {user_id}")
        return deleted > 0
    
    @staticmethod
    async def apply_loadout_to_home(user_id: int, name: str) -> bool:
        """
        Apply a loadout's items to the user's home slots.
        
        This physically moves items from the loadout config to home slots.
        
        Args:
            user_id: Discord user ID
            name: Loadout name to apply
            
        Returns:
            True if application succeeded
        """
        loadout = await Loadout.filter(user_id=user_id, name=name).first()
        if not loadout:
            return False
        
        items = [
            loadout.slot_0,
            loadout.slot_1,
            loadout.slot_2,
            loadout.slot_3,
            loadout.slot_4,
        ]
        
        # Update home slots
        for slot_index, item_id in enumerate(items):
            slot, _ = await HomeSlot.get_or_create(
                user_id=user_id,
                slot_index=slot_index,
                defaults={"item_id": item_id}
            )
            slot.item_id = item_id
            await slot.save()
        
        logger.info(f"[LOADOUT] Applied '{name}' to home for user {user_id}")
        return True
    
    @staticmethod
    async def save_current_home_as_loadout(
        user_id: int,
        name: str,
        activity: str
    ) -> Loadout:
        """
        Save current home configuration as a new loadout.
        
        Args:
            user_id: Discord user ID
            name: Name for the new loadout
            activity: Activity type to bind
            
        Returns:
            Created Loadout
        """
        # Get current home slots
        slots = await HomeSlot.filter(user_id=user_id).order_by("slot_index").all()
        items = [None] * 5
        for slot in slots:
            if 0 <= slot.slot_index < 5:
                items[slot.slot_index] = slot.item_id
        
        return await LoadoutService.create_loadout(user_id, name, activity, items)
    
    @staticmethod
    async def get_loadout_preview(loadout: Loadout) -> Dict[str, Any]:
        """
        Get a preview of what bonuses a loadout would provide.
        
        Args:
            loadout: Loadout instance
            
        Returns:
            Dict with set info and bonus preview
        """
        items = [
            loadout.slot_0,
            loadout.slot_1,
            loadout.slot_2,
            loadout.slot_3,
            loadout.slot_4,
        ]
        
        items_data = SetsDataLoader.get_items()
        sets_data = SetsDataLoader.get_sets()
        
        # Count items per set
        set_counts: Dict[str, int] = {}
        total_charm = 0
        
        for item_id in items:
            if not item_id:
                continue
            item = items_data.get(item_id)
            if not item:
                continue
            
            set_id = item.get("set_id")
            if set_id:
                set_counts[set_id] = set_counts.get(set_id, 0) + 1
            
            total_charm += item.get("charm", 0)
        
        # Calculate bonuses from active sets (2+ pieces)
        active_sets = []
        for set_id, count in set_counts.items():
            if count >= 2 and set_id in sets_data:
                set_info = sets_data[set_id]
                active_sets.append({
                    "id": set_id,
                    "name": set_info.get("name"),
                    "pieces": count,
                    "bonus": set_info.get("bonus", {})
                })
        
        return {
            "name": loadout.name,
            "activity": loadout.activity,
            "is_active": loadout.is_active,
            "total_charm": total_charm,
            "active_sets": active_sets,
            "items": items
        }


# Singleton-style access
_loadout_service: Optional[LoadoutService] = None

def get_loadout_service() -> LoadoutService:
    """Get or create the LoadoutService instance."""
    global _loadout_service
    if _loadout_service is None:
        _loadout_service = LoadoutService()
    return _loadout_service

"""
Housing Engine - Aquarium Home System Logic

Manages user home slots, decoration placement, and set bonuses.
Uses new SetsDataLoader for item/set data (single source of truth).
"""

from typing import List, Optional, Dict
from tortoise.transactions import in_transaction
from ..models import UserAquarium, HomeSlot, UserDecor, HomeVisit
from .effect_manager import SetsDataLoader, get_effect_manager
from core.logging import get_logger

logger = get_logger("aquarium_logic_housing")

class HousingEngine:
    """
    Business logic for Housing System (Project Aquarium).
    Uses Tortoise ORM.
    """

    @staticmethod
    async def has_house(user_id: int) -> bool:
        """Check if user has a registered house."""
        user = await UserAquarium.get_or_none(user_id=user_id)
        return bool(user and user.home_thread_id)

    @staticmethod
    async def get_home_thread_id(user_id: int) -> Optional[int]:
        """Get the Discord Thread ID of the user's home."""
        user = await UserAquarium.get_or_none(user_id=user_id)
        return user.home_thread_id if user else None

    @staticmethod
    async def register_house(user_id: int, thread_id: int) -> bool:
        """
        Register a new house.
        1. Create/Update UserAquarium
        2. Create 5 empty HomeSlots
        """
        try:
            async with in_transaction():
                # 1. Create UserAquarium
                user, created = await UserAquarium.get_or_create(
                    user_id=user_id,
                    defaults={'home_thread_id': thread_id}
                )
                if not created:
                    user.home_thread_id = thread_id
                    await user.save()

                # 2. Init Default Slots (0-4)
                # Check if slots exist first to avoid error if re-registering
                existing_count = await HomeSlot.filter(user=user).count()
                if existing_count < 5:
                    for i in range(5):
                        await HomeSlot.get_or_create(user=user, slot_index=i, defaults={'item_id': None})
            
            logger.info(f"[HOUSE_CREATE] Registered house for User {user_id}, Thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"[HOUSE_REGISTER_ERROR] User {user_id}: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_slots(user_id: int) -> List[Optional[str]]:
        """Get list of item_ids in slots 0-4."""
        slots_qs = await HomeSlot.filter(user_id=user_id).order_by('slot_index').all()
        
        # Map to list
        slot_map = {s.slot_index: s.item_id for s in slots_qs}
        result = [slot_map.get(i) for i in range(5)]
        return result

    @staticmethod
    async def get_inventory(user_id: int) -> Dict[str, int]:
        """Get user's available decor inventory from MAIN inventory."""
        from core.item_system import item_system
        from database_manager import db_manager
        
        # Fetch all inventory
        # Returns List[tuple] -> [(item_id, quantity), ...]
        rows = await db_manager.fetchall("SELECT item_id, quantity FROM inventory WHERE user_id = $1 AND quantity > 0", (user_id,))
        inventory = {}
        for r in rows:
            # r is tuple (item_id, quantity)
            item_id = r[0]
            quantity = r[1]
            
            # New Validation Logic: Check if item is decor via ItemSystem
            item_data = item_system.get_item(item_id)
            if item_data and item_data.get('type') == 'decor':
                 inventory[item_id] = quantity
        return inventory

    @staticmethod
    async def update_slot(user_id: int, slot_index: int, new_item_id: Optional[str]) -> tuple[bool, str]:
        """
        Update a decor slot. Handles Inventory swapping using MAIN inventory.
        """
        try:
            from database_manager import db_manager
            
            # Hybrid Transaction: We use Tortoise for Slot metadata and DBManager for Inventory
            # Ideally should be fully migrated, but this bridges the gap.
            
            async with in_transaction():
                user = await UserAquarium.get(user_id=user_id)
                slot = await HomeSlot.get(user=user, slot_index=slot_index)
                old_item_id = slot.item_id

                if old_item_id == new_item_id:
                    return True, "Không có thay đổi."

                # 1. Return OLD item to inventory (Main DB)
                if old_item_id:
                    await db_manager.execute(
                        """INSERT INTO inventory (user_id, item_id, quantity) 
                           VALUES ($1, $2, 1)
                           ON CONFLICT(user_id, item_id) 
                           DO UPDATE SET quantity = inventory.quantity + 1""",
                        (user_id, old_item_id)
                    )

                # 2. Take NEW item from inventory (Main DB)
                if new_item_id:
                    # Check stock first
                    row = await db_manager.fetchrow(
                        "SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2",
                        (user_id, new_item_id)
                    )
                    # fetchrow might return tuple or None. 
                    # Row is (quantity,)
                    if not row or row[0] < 1:
                         return False, "Không đủ vật phẩm trong kho."
                    
                    # Deduct
                    await db_manager.execute(
                        "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = $1 AND item_id = $2",
                        (user_id, new_item_id)
                    )

                # 3. Update Slot (Tortoise)
                slot.item_id = new_item_id
                await slot.save()

            logger.info(f"[HOUSE_UPDATE] User {user_id} Slot {slot_index}: {old_item_id} -> {new_item_id}")
            return True, "Cập nhật thành công."

        except Exception as e:
            logger.error(f"[HOUSE_UPDATE_ERROR] User {user_id}: {e}", exc_info=True)
            return False, f"Lỗi hệ thống: {e}"

    @staticmethod
    async def get_active_sets(user_id: int) -> List[Dict]:
        """Check which sets are active (Delegated to EffectManager)."""
        manager = get_effect_manager()
        return await manager.get_active_sets(user_id)

    @staticmethod
    async def calculate_home_stats(user_id: int) -> Dict:
        """Calculate total value and charm using SetsDataLoader (new JSON source)."""
        manager = get_effect_manager()
        items_data = SetsDataLoader.get_items()
        
        current_slots = await HousingEngine.get_slots(user_id)
        active_sets = await HousingEngine.get_active_sets(user_id)
        
        total_charm = 0
        total_value = 0
        
        for item_id in current_slots:
            if item_id:
                item = items_data.get(item_id)
                if not item:
                    continue
                
                # Use direct charm field (no more parsing from description)
                total_charm += item.get('charm', 0)
                             
                # Price Value
                total_value += item.get('price_seeds', 0)

        return {
            "charm_point": total_charm,
            "total_value": total_value,
            "active_sets_count": len(active_sets)
        }

    @staticmethod
    async def get_dashboard_message_id(user_id: int) -> Optional[int]:
        """Get the ID of the floating dashboard message."""
        user = await UserAquarium.get_or_none(user_id=user_id)
        return user.dashboard_message_id if user else None

    @staticmethod
    async def set_dashboard_message_id(user_id: int, message_id: int):
        """Update the ID of the floating dashboard message."""
        user, _ = await UserAquarium.get_or_create(user_id=user_id)
        user.dashboard_message_id = message_id
        await user.save()

    @staticmethod
    async def get_house_owner(thread_id: int) -> Optional[int]:
        """Reverse lookup: Thread ID -> User ID."""
        user = await UserAquarium.get_or_none(home_thread_id=thread_id)
        return user.user_id if user else None

    @staticmethod
    async def visit_home(visitor_id: int, host_id: int) -> Dict:
        """
        Process a home visit.
        - Log visit.
        - (Future) random rewards?
        """
        if visitor_id == host_id:
             return {"success": False, "message": "Bạn đang ở nhà mình mà?"}
        
        try:
            host = await UserAquarium.get_or_none(user_id=host_id)
            if not host or not host.home_thread_id:
                return {"success": False, "message": "Người này chưa có nhà!"}

            # Log visit
            # Check cooldown? (Simple daily check)
            # For now just log
            await HomeVisit.create(host_id=host_id, visitor_id=visitor_id)
            
            # Message
            return {
                "success": True, 
                "message": "👋 Bạn đã ghé thăm nhà thành công! (Chức năng trộm cá/nhặt quà chưa mở)"
            }

        except Exception as e:
            logger.error(f"[VISIT_ERROR] {e}", exc_info=True)
            return {"success": False, "message": "Lỗi khi ghé thăm."}
    @staticmethod
    async def set_theme(user_id: int, url: str) -> bool:
        """Set custom aquarium theme URL (VIP feature)."""
        try:
            user = await UserAquarium.get(user_id=user_id)
            user.theme_url = url
            await user.save()
            return True
        except Exception as e:
            logger.error(f"[SET_THEME_ERROR] User {user_id}: {e}")
            return False

    @staticmethod
    async def get_theme(user_id: int) -> Optional[str]:
        """Get user's custom theme URL."""
        user = await UserAquarium.get_or_none(user_id=user_id)
        return user.theme_url if user else None

    @staticmethod
    async def is_set_active(user_id: int, set_id: str, min_items: int = 2) -> bool:
        """
        Check if user has a specific set active.
        
        DEPRECATED: Use EffectManager.get_active_sets() instead.
        This method is kept for backwards compatibility.
        
        Args:
            user_id: The user ID
            set_id: The set ID to check (e.g., 'hai_duong_cung')
            min_items: Minimum items required (default 2)
            
        Returns:
            bool: True if set is active
        """
        try:
            manager = get_effect_manager()
            active_sets = await manager.get_active_sets(user_id)
            
            for set_data in active_sets:
                if set_data.get("id") == set_id:
                    return set_data.get("active_pieces", 0) >= min_items
            
            return False
        except Exception as e:
            logger.error(f"[SET_CHECK] Error checking set {set_id} for {user_id}: {e}")
            return False

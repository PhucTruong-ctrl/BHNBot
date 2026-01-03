
from typing import List, Optional, Dict
from tortoise.transactions import in_transaction
from ..models import UserAquarium, HomeSlot, UserDecor, HomeVisit
from ..constants import DECOR_ITEMS, FENG_SHUI_SETS
import logging

logger = logging.getLogger("HousingEngine")

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
        """Get user's available decor inventory."""
        # user_decor table
        items = await UserDecor.filter(user_id=user_id, quantity__gt=0).all()
        return {item.item_id: item.quantity for item in items}

    @staticmethod
    async def update_slot(user_id: int, slot_index: int, new_item_id: Optional[str]) -> tuple[bool, str]:
        """
        Update a decor slot. Handles Inventory swapping.
        Atomic transaction.
        """
        try:
            async with in_transaction():
                user = await UserAquarium.get(user_id=user_id)
                slot = await HomeSlot.get(user=user, slot_index=slot_index)
                old_item_id = slot.item_id

                if old_item_id == new_item_id:
                    return True, "Không có thay đổi."

                # 1. Return OLD item to inventory
                if old_item_id:
                    # Using get_or_create logic
                    decor, _ = await UserDecor.get_or_create(user=user, item_id=old_item_id)
                    decor.quantity += 1
                    await decor.save()

                # 2. Take NEW item from inventory
                if new_item_id:
                    decor = await UserDecor.get_or_none(user=user, item_id=new_item_id)
                    if not decor or decor.quantity < 1:
                        return False, "Không đủ vật phẩm trong kho."
                    
                    decor.quantity -= 1
                    if decor.quantity == 0:
                        await decor.delete() # Clean up
                    else:
                        await decor.save()

                # 3. Update Slot
                slot.item_id = new_item_id
                await slot.save()

            logger.info(f"[HOUSE_UPDATE] User {user_id} Slot {slot_index}: {old_item_id} -> {new_item_id}")
            return True, "Cập nhật thành công."

        except Exception as e:
            logger.error(f"[HOUSE_UPDATE_ERROR] User {user_id}: {e}", exc_info=True)
            return False, f"Lỗi hệ thống: {e}"

    @staticmethod
    async def get_active_sets(user_id: int) -> List[Dict]:
        """Check which Feng Shui sets are active."""
        current_slots = await HousingEngine.get_slots(user_id)
        placed_items = set(item for item in current_slots if item)
        
        active = []
        for set_data in FENG_SHUI_SETS.values():
            required = set(set_data.get("required", []))
            if required.issubset(placed_items):
                active.append(set_data)
        return active

    @staticmethod
    async def calculate_home_stats(user_id: int) -> Dict:
        """Calculate total value and charm."""
        current_slots = await HousingEngine.get_slots(user_id)
        active_sets = await HousingEngine.get_active_sets(user_id)
        
        total_charm = 0
        total_value = 0
        
        for item_id in current_slots:
            if item_id and item_id in DECOR_ITEMS:
                item = DECOR_ITEMS[item_id]
                # Parse Charm from desc if needed
                desc = item.get('desc', '')
                if "(+" in desc and "Charm)" in desc:
                    try:
                        charm_part = desc.split("(+")[1].split(" Charm)")[0]
                        total_charm += int(charm_part)
                    except:
                        pass
                
                total_value += item.get('price_leaf', 0)
        
        return {
            "charm": total_charm,
            "value": total_value,
            "sets": active_sets
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

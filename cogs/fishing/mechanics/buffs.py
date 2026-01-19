"""Buff and emotional state mechanics for fishing system.

Handles emotional states (suy, keo_ly, lag) for players.
"""
from core.logging import get_logger
import time
from typing import Dict, Optional

logger = get_logger("fishing_mechanics_buffs")


class EmotionalStateManager:
    """Manages emotional states (debuffs/buffs) for users with Database Persistence."""
    
    def __init__(self):
        # We don't need local state anymore as we use DB + Caching
        pass
    
    async def apply_emotional_state(self, user_id: int, state_type: str, duration: int) -> None:
        """Apply emotional state (debuff/buff) to user.
        
        Args:
            user_id: User ID
            state_type: "suy", "keo_ly", "lag", "lucky_buff", "legendary_buff"
            duration: In casts (counter) or seconds (time) depending on type
        """
        duration_type = 'time'
        end_time = 0
        remaining_count = 0
        
        # Determine type
        if state_type in ["suy", "lucky_buff", "legendary_buff"]:
            duration_type = 'counter'
            remaining_count = duration
        elif state_type in ["keo_ly", "lag"]:
            duration_type = 'time'
            end_time = time.time() + duration
            
        from database_manager import save_user_buff
        await save_user_buff(user_id, state_type, duration_type, end_time, remaining_count)
        
        logger.info(f"[BUFF] Applied {state_type} to user {user_id} ({duration_type}={duration})")
    
    async def check_emotional_state(self, user_id: int, state_type: str) -> bool:
        """Check if user has active emotional state of type."""
        from database_manager import get_user_buffs
        buffs = await get_user_buffs(user_id)
        return state_type in buffs
    
    async def get_emotional_state(self, user_id: int, state_type: str = None) -> Optional[Dict]:
        """Get specfic state data."""
        from database_manager import get_user_buffs
        buffs = await get_user_buffs(user_id)
        if state_type:
            return buffs.get(state_type)
        return buffs # Return all if no type? Warning: Signature mismatch risk
    
    async def decrement_suy_cast(self, user_id: int) -> int:
        """Decrement suy debuff (or any counter buff)."""
        # Note: Logic specific to 'suy', but can be generalized
        return await self.decrement_counter(user_id, "suy")

    async def decrement_counter(self, user_id: int, state_type: str) -> int:
        """Generic decrement for counter-based buffs."""
        from database_manager import get_user_buffs, save_user_buff, remove_user_buff
        
        buffs = await get_user_buffs(user_id)
        if state_type in buffs:
            data = buffs[state_type]
            if data['duration_type'] == 'counter':
                new_count = data['remaining'] - 1
                if new_count <= 0:
                    await remove_user_buff(user_id, state_type)
                    logger.info(f"[BUFF] {state_type} expired for user {user_id}")
                    return 0
                else:
                    await save_user_buff(user_id, state_type, 'counter', remaining_count=new_count)
                    return new_count
        return 0

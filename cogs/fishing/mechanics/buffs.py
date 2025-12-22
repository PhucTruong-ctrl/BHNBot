"""Buff and emotional state mechanics for fishing system.

Handles emotional states (suy, keo_ly, lag) for players.
"""
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger("fishing")


class EmotionalStateManager:
    """Manages emotional states (debuffs/buffs) for users."""
    
    def __init__(self):
        self.emotional_states: Dict[int, Dict] = {}
    
    def apply_emotional_state(self, user_id: int, state_type: str, duration: int) -> None:
        """Apply emotional state (debuff/buff) to user.
        
        Args:
            user_id: User ID
            state_type: "suy" (50% rare reduction for 5 casts), "keo_ly" (2x sell for 10 min), "lag" (3s delay for 5 min)
            duration: In casts for "suy", in seconds for "keo_ly" and "lag"
        """
        self.emotional_states[user_id] = {
            "type": state_type,
            "duration": duration,
            "start_time": time.time(),
            "remaining": duration  # For suy, this is remaining casts
        }
        logger.info(f"[BUFF] Applied {state_type} to user {user_id} for {duration}")
    
    def check_emotional_state(self, user_id: int, state_type: str) -> bool:
        """Check if user has active emotional state of type.
        
        Args:
            user_id: User ID
            state_type: Emotional state type to check
            
        Returns:
            bool: True if user has active state of this type
        """
        if user_id not in self.emotional_states:
            return False
        
        state = self.emotional_states[user_id]
        if state["type"] != state_type:
            return False
        
        elapsed = time.time() - state["start_time"]
        
        if state_type == "suy":
            # For suy, check remaining casts
            return state["remaining"] > 0
        else:
            # For keo_ly and lag, check time duration
            return elapsed < state["duration"]
    
    def get_emotional_state(self, user_id: int) -> Optional[Dict]:
        """Get current emotional state or None if expired.
        
        Args:
            user_id: User ID
            
        Returns:
            dict or None: Current emotional state data
        """
        if user_id not in self.emotional_states:
            return None
        
        state = self.emotional_states[user_id]
        elapsed = time.time() - state["start_time"]
        
        if state["type"] == "suy":
            if state["remaining"] <= 0:
                del self.emotional_states[user_id]
                return None
        else:
            if elapsed >= state["duration"]:
                del self.emotional_states[user_id]
                return None
        
        return state
    
    def decrement_suy_cast(self, user_id: int) -> int:
        """Decrement suy debuff cast count.
        
        Args:
            user_id: User ID
            
        Returns:
            int: Remaining casts (0 if expired/not exists)
        """
        if user_id in self.emotional_states and self.emotional_states[user_id]["type"] == "suy":
            self.emotional_states[user_id]["remaining"] -= 1
            remaining = self.emotional_states[user_id]["remaining"]
            if remaining <= 0:
                del self.emotional_states[user_id]
                logger.info(f"[BUFF] Suy debuff expired for user {user_id}")
            return remaining
        return 0

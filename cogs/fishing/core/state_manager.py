"""Centralized state management for the Fishing cog.

This module consolidates all RAM-based state tracking (cooldowns, buffs, 
pending events, disaster effects) into a single manager class. This:
1. Reduces cog.py complexity
2. Makes state easier to test and persist
3. Centralizes cleanup logic
"""

from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from ..constants import GLOBAL_DISASTER_COOLDOWN

if TYPE_CHECKING:
    import discord


@dataclass
class DisasterState:
    """Tracks active disaster effects."""
    is_frozen: bool = False
    freeze_end_time: float = 0.0
    last_disaster_time: float = 0.0
    cooldown_seconds: int = GLOBAL_DISASTER_COOLDOWN
    current_disaster: Optional[str] = None
    culprit_id: Optional[int] = None
    catch_rate_penalty: float = 0.0
    cooldown_penalty: int = 0
    fine_amount: int = 0
    display_glitch: bool = False
    effect_end_time: float = 0.0
    channel: Optional["discord.TextChannel"] = None

    def reset(self) -> None:
        """Reset all disaster effects to defaults."""
        self.is_frozen = False
        self.freeze_end_time = 0.0
        self.current_disaster = None
        self.culprit_id = None
        self.catch_rate_penalty = 0.0
        self.cooldown_penalty = 0
        self.fine_amount = 0
        self.display_glitch = False
        self.effect_end_time = 0.0
        self.channel = None

    def is_active(self) -> bool:
        """Check if any disaster effect is currently active."""
        return time.time() < self.effect_end_time


@dataclass
class DarkMapState:
    """Tracks dark map (Cthulhu) activation per user."""
    active: dict[int, bool] = field(default_factory=dict)
    remaining_casts: dict[int, int] = field(default_factory=dict)
    current_cast: dict[int, int] = field(default_factory=dict)

    def activate(self, user_id: int, total_casts: int = 10) -> None:
        """Activate dark map for a user."""
        self.active[user_id] = True
        self.remaining_casts[user_id] = total_casts
        self.current_cast[user_id] = 0

    def deactivate(self, user_id: int) -> None:
        """Deactivate dark map for a user."""
        self.active.pop(user_id, None)
        self.remaining_casts.pop(user_id, None)
        self.current_cast.pop(user_id, None)

    def is_active(self, user_id: int) -> bool:
        """Check if user has dark map active."""
        return self.active.get(user_id, False)

    def use_cast(self, user_id: int) -> int:
        """Use one cast and return remaining. Returns -1 if not active."""
        if not self.is_active(user_id):
            return -1
        self.current_cast[user_id] = self.current_cast.get(user_id, 0) + 1
        self.remaining_casts[user_id] = max(0, self.remaining_casts.get(user_id, 0) - 1)
        return self.remaining_casts[user_id]


@dataclass
class PendingEvents:
    """Tracks forced/pending events per user."""
    disaster: dict[int, str] = field(default_factory=dict)
    fishing_event: dict[int, str] = field(default_factory=dict)
    sell_event: dict[int, str] = field(default_factory=dict)
    npc_event: dict[int, str] = field(default_factory=dict)
    meteor_shower: set[int] = field(default_factory=set)

    def clear_user(self, user_id: int) -> None:
        """Clear all pending events for a user."""
        self.disaster.pop(user_id, None)
        self.fishing_event.pop(user_id, None)
        self.sell_event.pop(user_id, None)
        self.npc_event.pop(user_id, None)
        self.meteor_shower.discard(user_id)


class FishingStateManager:
    """Centralized manager for all fishing cog RAM state.
    
    Consolidates 25+ state variables from the original cog into
    organized, typed data structures with cleanup methods.
    """

    def __init__(self) -> None:
        # User cooldowns and temporary data
        self.fishing_cooldown: dict[int, float] = {}
        self.caught_items: dict[int, list[Any]] = {}
        self._caught_items_timestamps: dict[int, float] = {}
        self.user_titles: dict[int, str] = {}
        self.user_stats: dict[int, dict[str, Any]] = {}
        
        # Session-based flags
        self.avoid_event_users: dict[int, bool] = {}
        self.sell_processing: dict[int, float] = {}
        self.guaranteed_catch_users: dict[int, bool] = {}
        
        # Legendary/special mechanics
        self.dark_map = DarkMapState()
        self.phoenix_buff_active: dict[int, float] = {}  # user_id -> expiry_time
        self.thuong_luong_timers: dict[int, float] = {}  # user_id -> timestamp
        
        # Global disaster state
        self.disaster = DisasterState()
        
        # Pending events
        self.pending = PendingEvents()
        
        # Meteor wishes
        self.meteor_wish_count: dict[int, dict[str, Any]] = {}
        
        # Asyncio locks for user operations
        self.user_locks: dict[int, asyncio.Lock] = {}

    def get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create an asyncio lock for a user."""
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]

    def set_cooldown(self, user_id: int, duration: float) -> None:
        """Set fishing cooldown for a user."""
        self.fishing_cooldown[user_id] = time.time() + duration

    def get_cooldown_remaining(self, user_id: int) -> float:
        """Get remaining cooldown in seconds. Returns 0 if no cooldown."""
        if user_id not in self.fishing_cooldown:
            return 0.0
        remaining = self.fishing_cooldown[user_id] - time.time()
        return max(0.0, remaining)

    def is_on_cooldown(self, user_id: int) -> bool:
        """Check if user is on fishing cooldown."""
        return self.get_cooldown_remaining(user_id) > 0

    def store_caught_items(self, user_id: int, items: list[Any]) -> None:
        """Store caught items for a user (for sell interactions)."""
        self.caught_items[user_id] = items
        self._caught_items_timestamps[user_id] = time.time()

    def get_caught_items(self, user_id: int) -> list[Any]:
        """Get stored caught items for a user."""
        return self.caught_items.get(user_id, [])

    def clear_caught_items(self, user_id: int) -> None:
        """Clear stored caught items for a user."""
        self.caught_items.pop(user_id, None)
        self._caught_items_timestamps.pop(user_id, None)

    def cleanup_stale_state(self, max_age_hours: int = 24) -> int:
        """Clean up expired state entries. Returns count of cleaned items."""
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned = 0

        # Clean expired cooldowns
        expired_cooldowns = [
            uid for uid, ts in self.fishing_cooldown.items()
            if ts < now
        ]
        for uid in expired_cooldowns:
            del self.fishing_cooldown[uid]
            cleaned += 1

        # Clean stale caught items (older than 1 hour)
        stale_caught = [
            uid for uid, ts in self._caught_items_timestamps.items()
            if now - ts > 3600
        ]
        for uid in stale_caught:
            self.clear_caught_items(uid)
            cleaned += 1

        # Clean expired phoenix buffs
        expired_phoenix = [
            uid for uid, expiry in self.phoenix_buff_active.items()
            if expiry < now
        ]
        for uid in expired_phoenix:
            del self.phoenix_buff_active[uid]
            cleaned += 1

        # Clean expired sell processing locks (older than 30 seconds)
        expired_sells = [
            uid for uid, ts in self.sell_processing.items()
            if now - ts > 30
        ]
        for uid in expired_sells:
            del self.sell_processing[uid]
            cleaned += 1

        # Clean stale user locks (older than max_age)
        # Note: Only clean if lock is not currently held
        stale_locks = []
        for uid, lock in self.user_locks.items():
            if not lock.locked():
                stale_locks.append(uid)
        # Keep some locks around, only clean if we have too many
        if len(stale_locks) > 100:
            for uid in stale_locks[:50]:
                del self.user_locks[uid]
                cleaned += 1

        # Reset disaster state if expired
        if self.disaster.is_active() is False and self.disaster.current_disaster:
            self.disaster.reset()
            cleaned += 1

        return cleaned

    def reset_user_state(self, user_id: int) -> None:
        """Completely reset all state for a user (for testing/admin)."""
        self.fishing_cooldown.pop(user_id, None)
        self.clear_caught_items(user_id)
        self.user_titles.pop(user_id, None)
        self.user_stats.pop(user_id, None)
        self.avoid_event_users.pop(user_id, None)
        self.sell_processing.pop(user_id, None)
        self.guaranteed_catch_users.pop(user_id, None)
        self.dark_map.deactivate(user_id)
        self.phoenix_buff_active.pop(user_id, None)
        self.thuong_luong_timers.pop(user_id, None)
        self.pending.clear_user(user_id)
        self.meteor_wish_count.pop(user_id, None)
        self.user_locks.pop(user_id, None)

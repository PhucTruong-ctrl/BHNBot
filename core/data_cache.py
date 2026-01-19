"""
Centralized JSON Data Cache System

Loads all static JSON data at startup and provides instant sync access.
Supports hot-reload with async locking for runtime updates.

Usage:
    from core.data_cache import data_cache
    
    # At startup (in main.py):
    await data_cache.load_all()
    
    # In any cog (instant, no I/O):
    fish_data = data_cache.get("fishing_data")
    achievements = data_cache.get("achievements")
    
    # Hot reload (admin command):
    await data_cache.reload("fishing_data")
    await data_cache.reload_all()
"""

import json
import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
from core.logging import get_logger

logger = get_logger("data_cache")


class DataCache:
    """
    Singleton cache for all static JSON data.
    
    Thread-safe for reads (GIL), async-safe for reloads (Lock).
    """
    
    _instance: Optional["DataCache"] = None
    _initialized: bool = False
    
    # Thread pool for non-blocking file I/O
    _executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DataCache")
    
    def __new__(cls) -> "DataCache":
        if cls._instance is None:
            cls._instance = super(DataCache, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cache: Dict[str, Any] = {}
        self._reload_lock = asyncio.Lock()
        self._base_path = Path("data")
        
        # Registry of all data files to cache
        # Format: cache_key -> relative path from data/
        self._registry: Dict[str, str] = {
            # === Core Fishing ===
            "fishing_data": "fishing_data.json",
            "legendary_fish": "legendaryFish_data.json",
            "vip_fish": "fishing_vip_fish.json",
            "fishing_events": "fishing_events.json",
            "fishing_global_events": "fishing_global_events.json",
            "disaster_events": "disaster_events.json",
            "npc_events": "npc_events.json",
            "sell_events": "sell_events.json",
            
            # === Achievements ===
            "achievements": "achievements.json",
            
            # === Tree System ===
            "tree_config": "tree_config.json",
            
            # === Items (loaded separately via ItemSystem, but cache for direct access) ===
            "items_consumables": "items/consumables.json",
            "items_materials": "items/materials.json",
            "items_misc": "items/misc.json",
            "items_special": "items/special.json",
            "items_premium": "items/premium.json",
            "items_shop": "items/shop.json",
            "items_decor": "items/decor_items.json",
            
            # === Sets ===
            "feng_shui_sets": "sets/feng_shui_sets.json",
            
            # === Events (seasonal) ===
            "event_registry": "events/registry.json",
            "event_spring": "events/spring.json",
            "event_summer": "events/summer.json",
            "event_autumn": "events/autumn.json",
            "event_winter": "events/winter.json",
            "event_halloween": "events/halloween.json",
            "event_earthday": "events/earthday.json",
            "event_midautumn": "events/midautumn.json",
            "event_birthday": "events/birthday.json",
            
            # === Noi Tu (word game) ===
            "words_dict": "words_dict.json",
        }
        
        self._initialized = True
        logger.info("datacache_initialized_with_%d_", len(self._registry))
    
    def _load_json_sync(self, file_path: Path) -> Optional[Dict]:
        """
        Synchronous JSON load (runs in thread pool).
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data or None on error
        """
        try:
            if not file_path.exists():
                logger.warning("file_not_found:_%s", file_path)
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error("json_parse_error_in_%s:_%s", file_path, e)
            return None
        except Exception as e:
            logger.error("failed_to_load_%s:_%s", file_path, e)
            return None
    
    def _load_all_sync(self) -> Dict[str, Any]:
        """
        Load all registered JSON files synchronously.
        Called from thread pool executor.
        
        Returns:
            Dict of cache_key -> data
        """
        loaded = {}
        success_count = 0
        error_count = 0
        
        for cache_key, relative_path in self._registry.items():
            file_path = self._base_path / relative_path
            data = self._load_json_sync(file_path)
            
            if data is not None:
                loaded[cache_key] = data
                success_count += 1
            else:
                error_count += 1
        
        logger.info(
            "Sync load complete: %d success, %d errors", 
            success_count, error_count
        )
        
        return loaded
    
    async def load_all(self) -> bool:
        """
        Load all registered JSON files asynchronously (non-blocking).
        Call this at bot startup in main.py.
        
        Returns:
            True if all files loaded successfully
        """
        async with self._reload_lock:
            try:
                loop = asyncio.get_running_loop()
                loaded = await loop.run_in_executor(self._executor, self._load_all_sync)
                
                # Atomic update
                self._cache.update(loaded)
                
                logger.info(
                    "DataCache loaded: %d keys cached", 
                    len(self._cache)
                )
                
                return len(loaded) == len(self._registry)
                
            except Exception as e:
                logger.error("failed_to_load_all_data:_%s", e)
                return False
    
    async def reload(self, cache_key: str) -> bool:
        """
        Reload a specific cache entry.
        
        Args:
            cache_key: Key to reload (e.g., "fishing_data")
            
        Returns:
            True if reload successful
        """
        if cache_key not in self._registry:
            logger.warning("unknown_cache_key:_%s", cache_key)
            return False
        
        async with self._reload_lock:
            try:
                loop = asyncio.get_running_loop()
                file_path = self._base_path / self._registry[cache_key]
                
                data = await loop.run_in_executor(
                    self._executor,
                    self._load_json_sync,
                    file_path
                )
                
                if data is not None:
                    self._cache[cache_key] = data
                    logger.info("reloaded:_%s", cache_key)
                    return True
                
                return False
                
            except Exception as e:
                logger.error("failed_to_reload_%s:_%s", cache_key, e)
                return False
    
    async def reload_all(self) -> bool:
        """
        Reload all cached data.
        
        Returns:
            True if all reloads successful
        """
        return await self.load_all()
    
    def get(self, cache_key: str, default: Any = None) -> Any:
        """
        Get cached data by key (instant, no I/O).
        
        Args:
            cache_key: Key to retrieve (e.g., "fishing_data")
            default: Default value if key not found
            
        Returns:
            Cached data or default
        """
        return self._cache.get(cache_key, default)
    
    def get_fish_data(self) -> Dict:
        """Convenience: Get main fishing data."""
        return self._cache.get("fishing_data", {})
    
    def get_legendary_fish(self) -> Dict:
        """Convenience: Get legendary fish data."""
        return self._cache.get("legendary_fish", {})
    
    def get_vip_fish(self) -> Dict:
        """Convenience: Get VIP fish data."""
        return self._cache.get("vip_fish", {})
    
    def get_achievements(self) -> Dict:
        """Convenience: Get achievements data."""
        return self._cache.get("achievements", {})
    
    def get_disaster_events(self) -> Dict:
        """Convenience: Get disaster events data."""
        return self._cache.get("disaster_events", {})
    
    def get_npc_events(self) -> Dict:
        """Convenience: Get NPC events data."""
        return self._cache.get("npc_events", {})
    
    def get_sell_events(self) -> Dict:
        """Convenience: Get sell events data."""
        return self._cache.get("sell_events", {})
    
    def get_tree_config(self) -> Dict:
        """Convenience: Get tree config."""
        return self._cache.get("tree_config", {})
    
    def get_event(self, event_id: str) -> Optional[Dict]:
        """
        Get seasonal event data by ID.
        
        Args:
            event_id: Event identifier (e.g., "spring", "halloween")
            
        Returns:
            Event data or None
        """
        cache_key = f"event_{event_id}"
        return self._cache.get(cache_key)
    
    def get_items_by_category(self, category: str) -> Dict:
        """
        Get items by category.
        
        Args:
            category: Item category (consumables, materials, misc, etc.)
            
        Returns:
            Items data for that category
        """
        cache_key = f"items_{category}"
        return self._cache.get(cache_key, {})
    
    def get_all_items(self) -> Dict[str, Any]:
        """
        Get all items from all categories merged.
        
        Returns:
            Merged dict of all items
        """
        all_items = {}
        categories = [
            "consumables", "materials", "misc", 
            "special", "premium", "shop", "decor"
        ]
        
        for category in categories:
            data = self.get_items_by_category(category)
            if isinstance(data, dict) and "items" in data:
                all_items.update(data["items"])
            elif isinstance(data, dict):
                all_items.update(data)
        
        return all_items
    
    def get_words_dict(self) -> Dict:
        """Convenience: Get words dictionary for noi tu game."""
        return self._cache.get("words_dict", {})
    
    def get_feng_shui_sets(self) -> Dict:
        """Convenience: Get feng shui sets data."""
        return self._cache.get("feng_shui_sets", {})
    
    def is_loaded(self, cache_key: str) -> bool:
        """Check if a specific key is loaded."""
        return cache_key in self._cache
    
    def get_loaded_keys(self) -> List[str]:
        """Get list of all loaded cache keys."""
        return list(self._cache.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        return {
            "total_registered": len(self._registry),
            "total_loaded": len(self._cache),
            "loaded_keys": list(self._cache.keys()),
            "missing_keys": [
                k for k in self._registry.keys() 
                if k not in self._cache
            ]
        }
    
    def clear(self):
        """Clear all cached data (for testing)."""
        self._cache.clear()
        logger.info("cache_cleared")


# Global singleton instance
data_cache = DataCache()

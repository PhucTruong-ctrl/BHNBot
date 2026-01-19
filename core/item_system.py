import json
import os
import copy
from typing import Dict, Optional, List
from core.logging import get_logger
from configs.item_constants import ItemKeys

logger = get_logger("ItemSystem")

class ItemSystem:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ItemSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.items: Dict[str, dict] = {}
        self.data_dir = "data/items"  # Changed from single file to directory
        
        # Default fallback (same as before)
        self.fallback_items = {
            "moi": {
                "key": "moi",
                "name": "Giun",
                "emoji": "🪱",
                "type": "consumable",
                "price": {"buy": 10, "sell": 2},
                "flags": {"buyable": True}
            }
        }
        
        self.load_items()
        self._initialized = True
    
    def _load_from_json(self) -> Dict[str, dict]:
        """Internal: Load items from disk without side effects."""
        loaded_items = {}
        file_count = 0
        
        try:
            if not os.path.exists(self.data_dir):
                logger.error(f"Item data directory not found: {self.data_dir}")
                return copy.deepcopy(self.fallback_items)

            # Scan all .json files in directory
            for filename in os.listdir(self.data_dir):
                if not filename.endswith(".json"):
                    continue
                    
                file_path = os.path.join(self.data_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        items_in_file = data.get("items", {})
                        loaded_items.update(items_in_file)
                        file_count += 1
                        logger.info(f"Loaded {len(items_in_file)} items from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load {filename}: {e}")
            
            if not loaded_items:
                logger.warning("No items found in any file!")
                return copy.deepcopy(self.fallback_items)

            return self._validate_and_index_items(loaded_items)
            
        except Exception as e:
            logger.error(f"Error scanning item directory: {e}")
            return copy.deepcopy(self.fallback_items)

    def load_items(self) -> bool:
        """Atomic load (Public API)."""
        new_items = self._load_from_json()
        if new_items:
            self.items = new_items
            logger.info(f"Total: Loaded {len(self.items)} items.")
            return True
        return False
            

            
    def reload(self) -> bool:
        """Reload items from disk (Public API)."""
        logger.info("Reloading items...")
        return self.load_items()
        
    def _validate_and_index_items(self, raw_items: Dict[str, dict]) -> Dict[str, dict]:
        """Validate raw items and build internal index."""
        valid_items = {}
        
        for key, item in raw_items.items():
            # 1. Basic Validation
            if "key" not in item:
                item["key"] = key
            
            if "name" not in item:
                logger.warning(f"Item '{key}' missing 'name'. Skipping.")
                continue
                
            # 2. Schema Normalization
            # Ensure price dict structure
            if "price" not in item:
                item["price"] = {"buy": 0, "sell": 0}
            elif isinstance(item["price"], (int, float)):
                # Legacy format support (if any)
                item["price"] = {"buy": 0, "sell": int(item["price"])}
                
            # Ensure flags dict
            if "flags" not in item:
                item["flags"] = {}
                
            valid_items[key] = item
            
        return valid_items

    def get_item(self, key: str) -> Optional[dict]:
        """Get item data by key."""
        return self.items.get(key)
        
    def get_all_items(self) -> Dict[str, dict]:
        """Get all items."""
        return self.items

    def validate_item_key(self, key: str) -> bool:
        """Check if item key exists."""
        return key in self.items

    def get_shop_items(self) -> List[dict]:
        """Get all items that can be bought in shop."""
        shop_items = []
        for item in self.items.values():
            if item.get("flags", {}).get("buyable", False):
                shop_items.append(item)
        
        # Sort by buy price
        return sorted(shop_items, key=lambda x: x["price"].get("buy", 0))
    
    def get_vip_items(self) -> List[dict]:
        """Get VIP-only premium items (tier-locked)."""  
        vip_items = []
        for item in self.items.values():
            if "tier_required" in item:
                vip_items.append(item)
        return sorted(vip_items, key=lambda x: (x.get("tier_required", 0), x.get("buy_price", 0)))

    def get_protected_items(self) -> set:
        """Get set of protected items that cannot be auto-sold."""
        return {
            # === CHESTS ===
            ItemKeys.RUONG_KHO_BAU,
            "ruong_go", "ruong_bac", "ruong_vang", "ruong_kim_cuong",
            
            # === GIFTS ===
            "cafe", "flower", "ring", "gift", "chocolate", "card",
            
            # === CONSUMABLES ===
            ItemKeys.MOI,
            "co_bon_la", "phan_bon",
            "nuoc_tang_luc", "gang_tay_xin", "thao_tac_tinh_vi", "tinh_yeu_ca", "tinh_cau",
            
            # === LEGENDARY COMPONENTS ===
            "long_vu_lua",
            
            # === PUZZLE PIECES ===
            "manh_ghep_a", "manh_ghep_b", "manh_ghep_c", "manh_ghep_d",
            
            # === COMMEMORATIVE ===
            "qua_ngot_mua_1", "qua_ngot_mua_2", "qua_ngot_mua_3", "qua_ngot_mua_4", "qua_ngot_mua_5",
            
            # === SPECIAL ===
            "ngoc_trai",
        }

# Global Instance
item_system = ItemSystem()

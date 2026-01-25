"""
Content Rotation Service for Seasonal Events.

Handles yearly rotation of fish, shop items, and cosmetics using:
- Pool-based content selection
- 2-year cooldown for rotating items
- Seed-based RNG for reproducibility
- Exclusive yearly content (1 Epic fish + 1 frame + 1 bg + 1 title)
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.database import db_manager


@dataclass(frozen=True)
class FishDefinition:
    """Immutable fish definition from pool."""
    key: str
    name: str
    emoji: str
    tier: str
    base_drop_rate: float
    currency_reward: dict[str, int]
    introduced_year: int


@dataclass(frozen=True)
class CosmeticDefinition:
    """Immutable cosmetic definition."""
    key: str
    name: str
    asset_pattern: str
    yearly_exclusive: bool = True


@dataclass
class YearlyContent:
    """Content selected for a specific year."""
    year: int
    event_type: str
    fish: list[FishDefinition] = field(default_factory=list)
    exclusive_fish: Optional[FishDefinition] = None
    shop_items: list[dict] = field(default_factory=list)
    frame: Optional[dict] = None
    background: Optional[dict] = None
    title: Optional[dict] = None
    seed: str = ""


class ContentRotationService:
    """
    Manages yearly content rotation for seasonal events.
    
    Design principles:
    - Max tier = EPIC (legendary is quest-triggered, separate system)
    - 2-year cooldown for rotating pool items
    - Each year has 1 exclusive Epic fish + 1 frame + 1 background + 1 title
    - Seed-based RNG for reproducibility
    """
    
    COOLDOWN_YEARS = 2
    POOLS_BASE_PATH = Path("data/events/pools")
    
    def __init__(self):
        self._pool_cache: dict[str, dict] = {}
        self._exclusive_cache: dict[tuple[str, int], dict] = {}
    
    # =========================================================================
    # Pool Loading
    # =========================================================================
    
    def _load_pool(self, event_type: str) -> dict:
        """Load pool.json for an event type, with caching."""
        if event_type in self._pool_cache:
            return self._pool_cache[event_type]
        
        pool_path = self.POOLS_BASE_PATH / event_type / "pool.json"
        if not pool_path.exists():
            raise FileNotFoundError(f"Pool not found for event: {event_type}")
        
        with open(pool_path, "r", encoding="utf-8") as f:
            pool = json.load(f)
        
        self._pool_cache[event_type] = pool
        return pool
    
    def _load_exclusive(self, event_type: str, year: int) -> Optional[dict]:
        """Load exclusives/{year}.json for an event, with caching."""
        cache_key = (event_type, year)
        if cache_key in self._exclusive_cache:
            return self._exclusive_cache[cache_key]
        
        exclusive_path = self.POOLS_BASE_PATH / event_type / "exclusives" / f"{year}.json"
        if not exclusive_path.exists():
            return None
        
        with open(exclusive_path, "r", encoding="utf-8") as f:
            exclusive = json.load(f)
        
        self._exclusive_cache[cache_key] = exclusive
        return exclusive
    
    # =========================================================================
    # Content History (Database)
    # =========================================================================
    
    async def get_content_history(
        self, 
        event_type: str, 
        content_type: str,
        years_back: int = 2
    ) -> list[Any]:
        """Get content used in recent years for cooldown checking."""
        current_year = datetime.now().year
        min_year = current_year - years_back
        
        sql = """
            SELECT content_key, year, tier, is_exclusive
            FROM event_content_history
            WHERE event_type = $1 
              AND content_type = $2
              AND year >= $3
            ORDER BY year DESC
        """
        rows = await db_manager.fetch(sql, event_type, content_type, min_year)
        return list(rows) if rows else []
    
    async def record_content_usage(
        self,
        event_type: str,
        year: int,
        content_type: str,
        content_key: str,
        tier: str,
        is_exclusive: bool,
        seed: str
    ) -> None:
        """Record content selection for history tracking."""
        sql = """
            INSERT INTO event_content_history 
                (event_type, year, content_type, content_key, tier, is_exclusive, seed_used)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (event_type, year, content_type, content_key) DO NOTHING
        """
        await db_manager.execute(
            sql, event_type, year, content_type, content_key, tier, is_exclusive, seed
        )
    
    # =========================================================================
    # Seed Generation
    # =========================================================================
    
    def generate_seed(self, event_type: str, year: int, salt: str = "") -> str:
        """
        Generate deterministic seed for reproducible RNG.
        
        Same event + year + salt = same content selection.
        """
        seed_input = f"{event_type}:{year}:{salt}:BHNBot"
        return hashlib.sha256(seed_input.encode()).hexdigest()[:16]
    
    def _seeded_random(self, seed: str) -> random.Random:
        """Create seeded random generator."""
        rng = random.Random()
        rng.seed(seed)
        return rng
    
    # =========================================================================
    # Fish Selection
    # =========================================================================
    
    async def select_fish_for_year(
        self,
        event_type: str,
        year: int,
        force_refresh: bool = False
    ) -> list[FishDefinition]:
        """
        Select fish for a specific year's event.
        
        Algorithm:
        1. Load pool.json
        2. Get history of recently used fish (2-year cooldown)
        3. Filter out fish on cooldown
        4. Use seeded RNG to select from eligible pool
        5. Add yearly exclusive fish
        6. Record selection in history
        """
        pool = self._load_pool(event_type)
        exclusive = self._load_exclusive(event_type, year)
        
        # Check if we already have recorded content for this year
        if not force_refresh:
            existing = await self.get_content_history(event_type, "fish", years_back=0)
            existing_this_year = [r for r in existing if r["year"] == year]
            if existing_this_year:
                # Return from pre-computed exclusive file
                if exclusive and "selected_rotating_fish" in exclusive:
                    return self._build_fish_list(pool, exclusive)
        
        # Get fish on cooldown
        history = await self.get_content_history(event_type, "fish", self.COOLDOWN_YEARS)
        on_cooldown = {r["content_key"] for r in history if not r["is_exclusive"]}
        
        # Filter eligible fish
        all_fish = pool.get("fish", [])
        eligible_fish = [
            f for f in all_fish
            if f["key"] not in on_cooldown
            and f.get("introduced_year", 2024) <= year
        ]
        
        # Get tier distribution from pool meta
        meta = pool.get("meta", {})
        event_size = "major_event" if meta.get("tier_distribution", {}).get("major_event") else "mini_event"
        distribution = meta.get("tier_distribution", {}).get(event_size, {})
        
        # Select fish by tier using seeded RNG
        seed = self.generate_seed(event_type, year)
        rng = self._seeded_random(seed)
        
        selected = []
        for tier, count in distribution.items():
            tier_fish = [f for f in eligible_fish if f["tier"] == tier]
            selected.extend(rng.sample(tier_fish, min(count, len(tier_fish))))
        
        # Add exclusive fish (always included, no cooldown)
        exclusive_fish = None
        if exclusive and exclusive.get("exclusive_fish"):
            ef = exclusive["exclusive_fish"]
            exclusive_fish = FishDefinition(
                key=ef["key"],
                name=ef["name"],
                emoji=ef["emoji"],
                tier=ef["tier"],
                base_drop_rate=ef.get("drop_rate", 0.05),
                currency_reward=ef.get("currency_reward", {"min": 50, "max": 100}),
                introduced_year=year
            )
        
        # Record selections in history
        for fish_data in selected:
            await self.record_content_usage(
                event_type, year, "fish", fish_data["key"],
                fish_data["tier"], False, seed
            )
        
        if exclusive_fish:
            await self.record_content_usage(
                event_type, year, "fish", exclusive_fish.key,
                exclusive_fish.tier, True, seed
            )
        
        # Convert to FishDefinition objects
        result = [
            FishDefinition(
                key=f["key"],
                name=f["name"],
                emoji=f["emoji"],
                tier=f["tier"],
                base_drop_rate=f["base_drop_rate"],
                currency_reward=f["currency_reward"],
                introduced_year=f.get("introduced_year", 2024)
            )
            for f in selected
        ]
        
        if exclusive_fish:
            result.append(exclusive_fish)
        
        return result
    
    def _build_fish_list(self, pool: dict, exclusive: dict) -> list[FishDefinition]:
        """Build fish list from pre-computed exclusive file."""
        all_fish = {f["key"]: f for f in pool.get("fish", [])}
        selected_keys = exclusive.get("selected_rotating_fish", [])
        
        result = []
        for key in selected_keys:
            if key in all_fish:
                f = all_fish[key]
                result.append(FishDefinition(
                    key=f["key"],
                    name=f["name"],
                    emoji=f["emoji"],
                    tier=f["tier"],
                    base_drop_rate=f["base_drop_rate"],
                    currency_reward=f["currency_reward"],
                    introduced_year=f.get("introduced_year", 2024)
                ))
        
        # Add exclusive fish
        ef = exclusive.get("exclusive_fish")
        if ef:
            result.append(FishDefinition(
                key=ef["key"],
                name=ef["name"],
                emoji=ef["emoji"],
                tier=ef["tier"],
                base_drop_rate=ef.get("drop_rate", 0.05),
                currency_reward=ef.get("currency_reward", {"min": 50, "max": 100}),
                introduced_year=exclusive.get("year", 2026)
            ))
        
        return result
    
    # =========================================================================
    # Cosmetics Selection
    # =========================================================================
    
    async def get_yearly_cosmetics(
        self,
        event_type: str,
        year: int
    ) -> dict[str, Any]:
        """
        Get yearly exclusive cosmetics (frame, background, title).
        
        These are ALWAYS exclusive to the year - no rotation/cooldown.
        """
        exclusive = self._load_exclusive(event_type, year)
        pool = self._load_pool(event_type)
        
        result: dict[str, Any] = {
            "frame": None,
            "background": None,
            "title": None
        }
        
        if exclusive and "exclusive_cosmetics" in exclusive:
            cosmetics = exclusive["exclusive_cosmetics"]
            result["frame"] = cosmetics.get("frame")
            result["background"] = cosmetics.get("background")
            result["title"] = cosmetics.get("title")
        else:
            # Generate from pool patterns
            cosmetics = pool.get("cosmetics", {})
            
            frames = cosmetics.get("frames", [])
            if frames:
                f = frames[0]
                result["frame"] = {
                    "key": f"{f['key']}_{year}",
                    "name": f["name"].replace("{year}", str(year)) if "{year}" in f.get("name", "") else f"{f['name']} {year}",
                    "asset": f"assets/frames/{f['asset_pattern'].replace('{year}', str(year))}"
                }
            
            backgrounds = cosmetics.get("backgrounds", [])
            if backgrounds:
                b = backgrounds[0]
                result["background"] = {
                    "key": f"{b['key']}_{year}",
                    "name": b["name"].replace("{year}", str(year)) if "{year}" in b.get("name", "") else f"{b['name']} {year}",
                    "asset": f"assets/profile/{b['asset_pattern'].replace('{year}', str(year))}"
                }
            
            titles = cosmetics.get("titles", [])
            if titles:
                t = titles[0]
                result["title"] = {
                    "key": f"{t['key']}_{year}",
                    "name": t["name_pattern"].replace("{year}", str(year))
                }
        
        return result
    
    # =========================================================================
    # Full Content Generation
    # =========================================================================
    
    async def generate_yearly_content(
        self,
        event_type: str,
        year: int,
        force_refresh: bool = False
    ) -> YearlyContent:
        """
        Generate complete content package for a year's event.
        
        Returns YearlyContent with fish, cosmetics, and metadata.
        """
        pool = self._load_pool(event_type)
        exclusive = self._load_exclusive(event_type, year)
        seed = self.generate_seed(event_type, year)
        
        # Get fish
        fish_list = await self.select_fish_for_year(event_type, year, force_refresh)
        
        # Separate exclusive fish
        exclusive_fish = None
        rotating_fish = []
        for fish in fish_list:
            if fish.introduced_year == year and fish.tier == "epic":
                exclusive_fish = fish
            else:
                rotating_fish.append(fish)
        
        # Get cosmetics
        cosmetics = await self.get_yearly_cosmetics(event_type, year)
        
        # Get shop items (no cooldown for now, use pool directly)
        shop_items = pool.get("shop_items", [])
        
        return YearlyContent(
            year=year,
            event_type=event_type,
            fish=rotating_fish,
            exclusive_fish=exclusive_fish,
            shop_items=shop_items,
            frame=cosmetics.get("frame"),
            background=cosmetics.get("background"),
            title=cosmetics.get("title"),
            seed=seed
        )
    
    # =========================================================================
    # Export for Event Config
    # =========================================================================
    
    async def export_event_config(
        self,
        event_type: str,
        year: int
    ) -> dict:
        """
        Export content in format compatible with existing event config.
        
        This can be used to generate/update data/events/{event}.json
        """
        content = await self.generate_yearly_content(event_type, year)
        
        # Convert to existing format
        fish_list = []
        for fish in content.fish:
            fish_list.append({
                "key": fish.key,
                "name": fish.name,
                "emoji": fish.emoji,
                "tier": fish.tier,
                "drop_rate": fish.base_drop_rate,
                "currency_reward": fish.currency_reward
            })
        
        if content.exclusive_fish:
            fish_list.append({
                "key": content.exclusive_fish.key,
                "name": content.exclusive_fish.name,
                "emoji": content.exclusive_fish.emoji,
                "tier": content.exclusive_fish.tier,
                "drop_rate": content.exclusive_fish.base_drop_rate,
                "currency_reward": content.exclusive_fish.currency_reward,
                "is_yearly_exclusive": True
            })
        
        return {
            "fish": fish_list,
            "shop": content.shop_items,
            "cosmetics": {
                "frame": content.frame,
                "background": content.background,
                "title": content.title
            },
            "_meta": {
                "generated_at": datetime.now().isoformat(),
                "seed": content.seed,
                "year": year
            }
        }


# Singleton instance
rotation_service = ContentRotationService()

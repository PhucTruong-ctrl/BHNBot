from typing import Optional
import random
from dataclasses import dataclass
from cogs.fishing.constants import ALL_FISH


@dataclass
class UpgradeConfig:
    efficiency: list[int] = None
    duration: list[int] = None
    quality: list[int] = None
    costs: dict[str, list[int]] = None

    def __post_init__(self):
        # TODO: TESTING MODE - revert to [5, 10, 20, 40, 100] after testing
        self.efficiency = [5, 10, 20, 40, 100]  # 60x faster for testing
        self.duration = [4, 8, 12, 18, 24]
        self.quality = [5, 10, 20, 35, 50]
        self.costs = {
            "efficiency": [100, 500, 2000, 5000, 10000],
            "duration": [50, 200, 800, 2000, 5000],
            "quality": [150, 600, 2500, 6000, 12000],
        }


UPGRADE_CONFIG = UpgradeConfig()

ESSENCE_PER_RARITY = {
    "common": 1,
    "rare": 5,
    "epic": 25,
    "legendary": 100,
}


def get_efficiency(level: int) -> int:
    return UPGRADE_CONFIG.efficiency[min(level - 1, 4)]


def get_max_duration(level: int) -> int:
    return UPGRADE_CONFIG.duration[min(level - 1, 4)]


def get_quality_bonus(level: int) -> int:
    return UPGRADE_CONFIG.quality[min(level - 1, 4)]


def get_upgrade_cost(upgrade_type: str, current_level: int) -> Optional[int]:
    if current_level >= 5:
        return None
    return UPGRADE_CONFIG.costs[upgrade_type][current_level]


def calculate_fish_catch(hours: float, efficiency: int, quality_bonus: int) -> dict[str, int]:
    total_fish = int(hours * efficiency)
    caught: dict[str, int] = {}

    fish_pool = list(ALL_FISH.items())
    rarity_weights = {"common": 100, "rare": 20, "epic": 5, "legendary": 1}

    for _ in range(total_fish):
        adjusted_weights = []
        for fish_key, fish_data in fish_pool:
            rarity = fish_data.get("rarity", "common")
            weight = rarity_weights.get(rarity, 100)
            if rarity in ("rare", "epic", "legendary"):
                weight = int(weight * (1 + quality_bonus / 100))
            adjusted_weights.append(weight)

        chosen_fish = random.choices(fish_pool, weights=adjusted_weights, k=1)[0]
        fish_key = chosen_fish[0]
        caught[fish_key] = caught.get(fish_key, 0) + 1

    return caught


def calculate_essence(fish_dict: dict[str, int]) -> int:
    total = 0
    for fish_key, count in fish_dict.items():
        fish_data = ALL_FISH.get(fish_key, {})
        rarity = fish_data.get("rarity", "common")
        total += count * ESSENCE_PER_RARITY.get(rarity, 1)
    return total


def calculate_sell_value(fish_dict: dict[str, int]) -> int:
    total = 0
    for fish_key, count in fish_dict.items():
        fish_data = ALL_FISH.get(fish_key, {})
        total += fish_data.get("sell_price", 10) * count
    return total

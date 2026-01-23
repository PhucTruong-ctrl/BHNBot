from typing import Optional
from datetime import datetime
import json
from dataclasses import dataclass

from core.database import db_manager
from ..core.calculator import (
    get_efficiency,
    get_max_duration,
    get_quality_bonus,
    get_upgrade_cost,
    calculate_fish_catch,
    calculate_essence,
    calculate_sell_value,
    ESSENCE_PER_RARITY,
)
from cogs.fishing.constants import ALL_FISH


@dataclass
class AutoFishData:
    user_id: int
    is_active: bool = False
    efficiency_level: int = 1
    duration_level: int = 1
    quality_level: int = 1
    total_essence: int = 0
    last_harvest: Optional[datetime] = None

    @property
    def efficiency(self) -> int:
        return get_efficiency(self.efficiency_level)

    @property
    def max_duration(self) -> int:
        return get_max_duration(self.duration_level)

    @property
    def quality_bonus(self) -> int:
        return get_quality_bonus(self.quality_level)


class AutoFishingService:

    @staticmethod
    async def ensure_tables():
        await db_manager.modify("""
            CREATE TABLE IF NOT EXISTS auto_fishing (
                user_id BIGINT PRIMARY KEY,
                is_active BOOLEAN DEFAULT FALSE,
                efficiency_level INT DEFAULT 1,
                duration_level INT DEFAULT 1,
                quality_level INT DEFAULT 1,
                total_essence INT DEFAULT 0,
                last_harvest TIMESTAMP
            )
        """)
        await db_manager.modify("""
            CREATE TABLE IF NOT EXISTS auto_fish_storage (
                user_id BIGINT,
                fish_key VARCHAR(64),
                quantity INT DEFAULT 0,
                PRIMARY KEY (user_id, fish_key)
            )
        """)
        await db_manager.modify("""
            CREATE INDEX IF NOT EXISTS idx_auto_fish_storage_user
            ON auto_fish_storage(user_id)
        """)

    @staticmethod
    async def get_user_data(user_id: int) -> Optional[AutoFishData]:
        row = await db_manager.fetchone(
            """SELECT user_id, is_active, efficiency_level, duration_level, 
                      quality_level, total_essence, last_harvest 
               FROM auto_fishing WHERE user_id = $1""",
            (user_id,)
        )
        if not row:
            return None
        return AutoFishData(
            user_id=row[0],
            is_active=bool(row[1]),
            efficiency_level=row[2],
            duration_level=row[3],
            quality_level=row[4],
            total_essence=row[5],
            last_harvest=row[6],
        )

    @staticmethod
    async def create_user(user_id: int) -> AutoFishData:
        await db_manager.modify(
            """INSERT INTO auto_fishing (user_id, is_active, efficiency_level, duration_level, quality_level, total_essence)
               VALUES ($1, FALSE, 1, 1, 1, 0)
               ON CONFLICT (user_id) DO NOTHING""",
            (user_id,)
        )
        return AutoFishData(user_id=user_id)

    @staticmethod
    async def toggle_active(user_id: int, active: bool) -> None:
        now = datetime.now() if active else None
        await db_manager.modify(
            "UPDATE auto_fishing SET is_active = $1, last_harvest = $2 WHERE user_id = $3",
            (active, now, user_id)
        )

    @staticmethod
    async def harvest_fish(user_id: int, data: AutoFishData) -> dict[str, int]:
        if not data.is_active or not data.last_harvest:
            return {}

        now = datetime.now()
        elapsed_hours = (now - data.last_harvest).total_seconds() / 3600
        elapsed_hours = min(elapsed_hours, data.max_duration)

        if elapsed_hours < 0.005:
            return {}

        caught = calculate_fish_catch(elapsed_hours, data.efficiency, data.quality_bonus)

        for fish_key, count in caught.items():
            await db_manager.modify(
                """INSERT INTO auto_fish_storage (user_id, fish_key, quantity)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (user_id, fish_key) DO UPDATE SET quantity = auto_fish_storage.quantity + $3""",
                (user_id, fish_key, count)
            )

        await db_manager.modify(
            "UPDATE auto_fishing SET last_harvest = $1 WHERE user_id = $2",
            (now, user_id)
        )

        return caught

    @staticmethod
    async def get_storage(user_id: int) -> dict[str, int]:
        rows = await db_manager.fetchall(
            "SELECT fish_key, quantity FROM auto_fish_storage WHERE user_id = $1 AND quantity > 0",
            (user_id,)
        )
        return {row[0]: row[1] for row in rows}

    @staticmethod
    async def transfer_to_inventory(user_id: int, bot, fish_key: Optional[str] = None) -> tuple[int, int]:
        if fish_key:
            rows = await db_manager.fetchall(
                "SELECT fish_key, quantity FROM auto_fish_storage WHERE user_id = $1 AND fish_key = $2 AND quantity > 0",
                (user_id, fish_key)
            )
        else:
            rows = await db_manager.fetchall(
                "SELECT fish_key, quantity FROM auto_fish_storage WHERE user_id = $1 AND quantity > 0",
                (user_id,)
            )

        total_transferred = 0
        total_types = 0

        for row in rows:
            fkey, qty = row[0], row[1]
            await bot.inventory.modify(user_id, fkey, qty)
            await db_manager.modify(
                "UPDATE auto_fish_storage SET quantity = 0 WHERE user_id = $1 AND fish_key = $2",
                (user_id, fkey)
            )
            total_transferred += qty
            total_types += 1

        return total_types, total_transferred

    @staticmethod
    async def sacrifice_fish(user_id: int, rarity: Optional[str] = None) -> tuple[int, int]:
        storage = await AutoFishingService.get_storage(user_id)
        if not storage:
            return 0, 0

        to_sacrifice = {}
        for fish_key, count in storage.items():
            fish_data = ALL_FISH.get(fish_key, {})
            fish_rarity = fish_data.get("rarity", "common")
            if rarity is None or fish_rarity == rarity:
                to_sacrifice[fish_key] = count

        if not to_sacrifice:
            return 0, 0

        total_essence = calculate_essence(to_sacrifice)
        total_fish = sum(to_sacrifice.values())

        for fish_key in to_sacrifice:
            await db_manager.modify(
                "UPDATE auto_fish_storage SET quantity = 0 WHERE user_id = $1 AND fish_key = $2",
                (user_id, fish_key)
            )

        await db_manager.modify(
            "UPDATE auto_fishing SET total_essence = total_essence + $1 WHERE user_id = $2",
            (total_essence, user_id)
        )

        return total_fish, total_essence

    @staticmethod
    async def sell_fish(user_id: int, bot, rarity: Optional[str] = None) -> tuple[int, int]:
        storage = await AutoFishingService.get_storage(user_id)
        if not storage:
            return 0, 0

        to_sell = {}
        for fish_key, count in storage.items():
            fish_data = ALL_FISH.get(fish_key, {})
            fish_rarity = fish_data.get("rarity", "common")
            if rarity is None or fish_rarity == rarity:
                to_sell[fish_key] = count

        if not to_sell:
            return 0, 0

        total_value = calculate_sell_value(to_sell)
        total_fish = sum(to_sell.values())

        for fish_key in to_sell:
            await db_manager.modify(
                "UPDATE auto_fish_storage SET quantity = 0 WHERE user_id = $1 AND fish_key = $2",
                (user_id, fish_key)
            )

        await bot.economy.add_money(user_id, total_value)

        return total_fish, total_value

    @staticmethod
    async def upgrade(user_id: int, upgrade_type: str) -> tuple[bool, str]:
        data = await AutoFishingService.get_user_data(user_id)
        if not data:
            return False, "Chưa có hệ thống auto-fish"

        # SECURITY: Whitelist validation to prevent SQL injection
        VALID_UPGRADE_TYPES = {"efficiency", "duration", "quality"}
        if upgrade_type not in VALID_UPGRADE_TYPES:
            return False, "Loại nâng cấp không hợp lệ"

        level_map = {
            "efficiency": data.efficiency_level,
            "duration": data.duration_level,
            "quality": data.quality_level,
        }
        current_level = level_map.get(upgrade_type, 0)

        if current_level >= 5:
            return False, "Đã đạt cấp tối đa"

        cost = get_upgrade_cost(upgrade_type, current_level)
        if cost is None:
            return False, "Đã đạt cấp tối đa"

        if data.total_essence < cost:
            return False, f"Thiếu tinh chất. Cần {cost}, có {data.total_essence}"

        # Safe to use f-string after whitelist validation
        await db_manager.modify(
            f"UPDATE auto_fishing SET {upgrade_type}_level = {upgrade_type}_level + 1, total_essence = total_essence - $1 WHERE user_id = $2",
            (cost, user_id)
        )

        return True, f"Nâng cấp thành công! Cấp mới: {current_level + 1}"

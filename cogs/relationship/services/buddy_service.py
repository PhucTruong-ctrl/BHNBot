"""Buddy bond management service.

Handles buddy requests, bonds, and bonus calculations.
This is a friendship/companion system (NOT dating/marriage).
"""
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from core.database import db_manager
from core.logging import get_logger

logger = get_logger("BuddyService")

MAX_BUDDIES = 3
REQUEST_EXPIRY_HOURS = 24

BOND_TITLES = {
    1: "Người quen",
    2: "Bạn câu",
    3: "Tri kỷ",
    4: "Đồng đội",
    5: "Chiến hữu",
}


@dataclass
class BuddyBond:
    id: int
    user_id_1: int
    user_id_2: int
    guild_id: int
    bond_level: int
    shared_xp: int
    created_at: datetime
    last_activity: Optional[datetime]

    @property
    def bond_title(self) -> str:
        return BOND_TITLES.get(min(self.bond_level, 5), "Chiến hữu")

    @property
    def xp_bonus_percent(self) -> float:
        base = 10
        per_level = 3
        return min(base + (self.bond_level - 1) * per_level, 25)


@dataclass
class BuddyRequest:
    id: int
    from_user_id: int
    to_user_id: int
    guild_id: int
    created_at: datetime
    expires_at: datetime


class BuddyService:

    @staticmethod
    async def ensure_tables() -> None:
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS buddy_bonds (
                id SERIAL PRIMARY KEY,
                user_id_1 BIGINT NOT NULL,
                user_id_2 BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                bond_level INT DEFAULT 1,
                shared_xp BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                last_activity TIMESTAMP,
                UNIQUE(user_id_1, user_id_2, guild_id)
            )
        """)
        
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS buddy_requests (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT NOT NULL,
                to_user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP,
                UNIQUE(from_user_id, to_user_id, guild_id)
            )
        """)
        
        await db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_buddy_bonds_users 
            ON buddy_bonds(user_id_1, guild_id)
        """)
        await db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_buddy_bonds_users2 
            ON buddy_bonds(user_id_2, guild_id)
        """)

    @staticmethod
    async def get_buddy_count(user_id: int, guild_id: int) -> int:
        row = await db_manager.fetchone(
            """SELECT COUNT(*) FROM buddy_bonds 
               WHERE guild_id = $1 AND (user_id_1 = $2 OR user_id_2 = $2)""",
            (guild_id, user_id)
        )
        return row[0] if row else 0

    @staticmethod
    async def get_buddies(user_id: int, guild_id: int) -> list[BuddyBond]:
        rows = await db_manager.fetchall(
            """SELECT id, user_id_1, user_id_2, guild_id, bond_level, 
                      shared_xp, created_at, last_activity
               FROM buddy_bonds 
               WHERE guild_id = $1 AND (user_id_1 = $2 OR user_id_2 = $2)
               ORDER BY bond_level DESC, shared_xp DESC""",
            (guild_id, user_id)
        )
        
        return [
            BuddyBond(
                id=row[0],
                user_id_1=row[1],
                user_id_2=row[2],
                guild_id=row[3],
                bond_level=row[4] or 1,
                shared_xp=row[5] or 0,
                created_at=row[6],
                last_activity=row[7]
            )
            for row in rows
        ]

    @staticmethod
    async def get_bond(user_id_1: int, user_id_2: int, guild_id: int) -> Optional[BuddyBond]:
        u1, u2 = min(user_id_1, user_id_2), max(user_id_1, user_id_2)
        
        row = await db_manager.fetchone(
            """SELECT id, user_id_1, user_id_2, guild_id, bond_level, 
                      shared_xp, created_at, last_activity
               FROM buddy_bonds 
               WHERE guild_id = $1 AND user_id_1 = $2 AND user_id_2 = $3""",
            (guild_id, u1, u2)
        )
        
        if not row:
            return None
            
        return BuddyBond(
            id=row[0],
            user_id_1=row[1],
            user_id_2=row[2],
            guild_id=row[3],
            bond_level=row[4] or 1,
            shared_xp=row[5] or 0,
            created_at=row[6],
            last_activity=row[7]
        )

    @staticmethod
    async def are_buddies(user_id_1: int, user_id_2: int, guild_id: int) -> bool:
        bond = await BuddyService.get_bond(user_id_1, user_id_2, guild_id)
        return bond is not None

    @staticmethod
    async def create_request(from_user_id: int, to_user_id: int, guild_id: int) -> tuple[bool, str]:
        if await BuddyService.are_buddies(from_user_id, to_user_id, guild_id):
            return False, "Hai bạn đã là bạn thân rồi!"
        
        sender_count = await BuddyService.get_buddy_count(from_user_id, guild_id)
        if sender_count >= MAX_BUDDIES:
            return False, f"Bạn đã có tối đa {MAX_BUDDIES} bạn thân rồi!"
        
        receiver_count = await BuddyService.get_buddy_count(to_user_id, guild_id)
        if receiver_count >= MAX_BUDDIES:
            return False, f"Người này đã có tối đa {MAX_BUDDIES} bạn thân rồi!"
        
        existing = await db_manager.fetchone(
            """SELECT id FROM buddy_requests 
               WHERE from_user_id = $1 AND to_user_id = $2 AND guild_id = $3""",
            (from_user_id, to_user_id, guild_id)
        )
        if existing:
            return False, "Bạn đã gửi lời mời cho người này rồi!"
        
        reverse = await db_manager.fetchone(
            """SELECT id FROM buddy_requests 
               WHERE from_user_id = $1 AND to_user_id = $2 AND guild_id = $3""",
            (to_user_id, from_user_id, guild_id)
        )
        if reverse:
            return False, "Người này đã gửi lời mời cho bạn! Dùng `/banthan chapnhan` để chấp nhận."
        
        expires_at = datetime.now() + timedelta(hours=REQUEST_EXPIRY_HOURS)
        await db_manager.execute(
            """INSERT INTO buddy_requests (from_user_id, to_user_id, guild_id, expires_at)
               VALUES ($1, $2, $3, $4)""",
            (from_user_id, to_user_id, guild_id, expires_at)
        )
        
        logger.info(f"Buddy request: {from_user_id} -> {to_user_id} in guild {guild_id}")
        return True, "Đã gửi lời mời kết bạn thân!"

    @staticmethod
    async def get_pending_requests(user_id: int, guild_id: int) -> list[BuddyRequest]:
        await db_manager.execute(
            "DELETE FROM buddy_requests WHERE expires_at < NOW()"
        )
        
        rows = await db_manager.fetchall(
            """SELECT id, from_user_id, to_user_id, guild_id, created_at, expires_at
               FROM buddy_requests 
               WHERE to_user_id = $1 AND guild_id = $2
               ORDER BY created_at DESC""",
            (user_id, guild_id)
        )
        
        return [
            BuddyRequest(
                id=row[0],
                from_user_id=row[1],
                to_user_id=row[2],
                guild_id=row[3],
                created_at=row[4],
                expires_at=row[5]
            )
            for row in rows
        ]

    @staticmethod
    async def accept_request(from_user_id: int, to_user_id: int, guild_id: int) -> tuple[bool, str]:
        request = await db_manager.fetchone(
            """SELECT id FROM buddy_requests 
               WHERE from_user_id = $1 AND to_user_id = $2 AND guild_id = $3""",
            (from_user_id, to_user_id, guild_id)
        )
        
        if not request:
            return False, "Không tìm thấy lời mời từ người này!"
        
        await db_manager.execute(
            """DELETE FROM buddy_requests 
               WHERE from_user_id = $1 AND to_user_id = $2 AND guild_id = $3""",
            (from_user_id, to_user_id, guild_id)
        )
        
        u1, u2 = min(from_user_id, to_user_id), max(from_user_id, to_user_id)
        
        await db_manager.execute(
            """INSERT INTO buddy_bonds (user_id_1, user_id_2, guild_id, last_activity)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (user_id_1, user_id_2, guild_id) DO NOTHING""",
            (u1, u2, guild_id)
        )
        
        logger.info(f"Buddy bond created: {u1} <-> {u2} in guild {guild_id}")
        return True, "Chúc mừng! Hai bạn đã trở thành bạn thân!"

    @staticmethod
    async def decline_request(from_user_id: int, to_user_id: int, guild_id: int) -> tuple[bool, str]:
        result = await db_manager.execute(
            """DELETE FROM buddy_requests 
               WHERE from_user_id = $1 AND to_user_id = $2 AND guild_id = $3""",
            (from_user_id, to_user_id, guild_id)
        )
        
        if result and "DELETE" in str(result):
            return True, "Đã từ chối lời mời bạn thân."
        return False, "Không tìm thấy lời mời từ người này!"

    @staticmethod
    async def remove_buddy(user_id: int, buddy_id: int, guild_id: int) -> tuple[bool, str]:
        u1, u2 = min(user_id, buddy_id), max(user_id, buddy_id)
        
        result = await db_manager.execute(
            """DELETE FROM buddy_bonds 
               WHERE user_id_1 = $1 AND user_id_2 = $2 AND guild_id = $3""",
            (u1, u2, guild_id)
        )
        
        if result and "DELETE" in str(result):
            logger.info(f"Buddy bond removed: {u1} <-> {u2} in guild {guild_id}")
            return True, "Đã huỷ liên kết bạn thân."
        return False, "Không tìm thấy liên kết bạn thân với người này!"

    @staticmethod
    async def add_shared_xp(user_id_1: int, user_id_2: int, guild_id: int, xp: int) -> None:
        u1, u2 = min(user_id_1, user_id_2), max(user_id_1, user_id_2)
        
        await db_manager.execute(
            """UPDATE buddy_bonds 
               SET shared_xp = shared_xp + $1, last_activity = NOW()
               WHERE user_id_1 = $2 AND user_id_2 = $3 AND guild_id = $4""",
            (xp, u1, u2, guild_id)
        )
        
        bond = await BuddyService.get_bond(user_id_1, user_id_2, guild_id)
        if bond:
            new_level = min(1 + bond.shared_xp // 1000, 5)
            if new_level > bond.bond_level:
                await db_manager.execute(
                    """UPDATE buddy_bonds SET bond_level = $1
                       WHERE user_id_1 = $2 AND user_id_2 = $3 AND guild_id = $4""",
                    (new_level, u1, u2, guild_id)
                )
                logger.info(f"Buddy bond level up: {u1} <-> {u2} -> Level {new_level}")

    @staticmethod
    async def get_active_buddy_bonus(user_id: int, guild_id: int, online_users: set[int]) -> float:
        buddies = await BuddyService.get_buddies(user_id, guild_id)
        
        if not buddies:
            return 0.0
        
        max_bonus = 0.0
        for bond in buddies:
            buddy_id = bond.user_id_2 if bond.user_id_1 == user_id else bond.user_id_1
            
            if buddy_id in online_users:
                bonus = bond.xp_bonus_percent / 100.0
                max_bonus = max(max_bonus, bonus)
        
        return max_bonus

    @staticmethod
    def get_buddy_id(bond: BuddyBond, user_id: int) -> int:
        return bond.user_id_2 if bond.user_id_1 == user_id else bond.user_id_1

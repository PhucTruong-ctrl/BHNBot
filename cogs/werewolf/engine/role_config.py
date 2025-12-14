"""Dynamic role configuration based on player count and expansions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from ..roles.base import Alignment, Expansion


@dataclass
class RoleSlot:
    """Represents a single role slot in the game."""

    name: str
    alignment: Alignment
    expansion: Expansion
    count: int = 1


class RoleConfig:
    """Manages role distribution based on player count and active expansions."""

    # Base game roles (expansion == BASIC)
    BASE_ROLES = [
        # Werewolves (4 fixed)
        RoleSlot("Ma Sói", Alignment.WEREWOLF, Expansion.BASIC, count=4),
        # Villagers (13 fixed in base)
        RoleSlot("Dân Làng", Alignment.VILLAGE, Expansion.BASIC, count=13),
        RoleSlot("Tiên Tri", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Cô Bé", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Phù Thủy", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Thợ Săn", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Thần Tình Yêu", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Tên Trộm", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Trưởng Làng", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Kẻ Thế Thân", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Bảo Vệ", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Con Quạ", Alignment.VILLAGE, Expansion.BASIC, count=1),
    ]

    # New Moon expansion roles
    NEWMOON_ROLES = [
        RoleSlot("Thằng Ngốc", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),
        RoleSlot("Già Làng", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),
        RoleSlot("Kẻ Thế Thân", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),
        RoleSlot("Bảo Vệ", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),
        RoleSlot("Thổi Sáo", Alignment.NEUTRAL, Expansion.NEW_MOON, count=1),
        RoleSlot("Hai Chị Em", Alignment.VILLAGE, Expansion.NEW_MOON, count=2),
    ]

    # The Village expansion roles
    THEVILLAGE_ROLES = [
        RoleSlot("Con Quạ", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Sói Trắng", Alignment.NEUTRAL, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Kẻ Phóng Hỏa", Alignment.NEUTRAL, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Sói To Xấu Xa", Alignment.WEREWOLF, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Sói Quỷ", Alignment.WEREWOLF, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Sói Lai", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Đứa Con Hoang", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Hiệp Sĩ", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Ảnh Tử", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Nguyệt Nữ", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Cổ Hoặc Sư", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Dược Sĩ", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
    ]

    @staticmethod
    def calculate_werewolves(player_count: int) -> int:
        """
        Calculate werewolf count using the Square Root Rule.
        Formula: Werewolves = floor(sqrt(player_count))
        
        Examples:
        - 8 players: sqrt(8) ≈ 2.8 → 2 Werewolves
        - 12 players: sqrt(12) ≈ 3.4 → 3 Werewolves
        - 16 players: sqrt(16) = 4 → 4 Werewolves
        """
        werewolf_count = int(math.sqrt(player_count))
        # Clamp between 1 and reasonable maximum
        return max(1, min(werewolf_count, player_count // 2))

    @staticmethod
    def should_have_neutral(player_count: int) -> bool:
        """
        Determine if neutral roles should be included.
        - Under 10 players: No neutral roles
        - 10+ players: Can have neutral roles
        """
        return player_count >= 10

    @staticmethod
    def get_neutral_count(player_count: int) -> int:
        """
        Determine how many neutral roles to include.
        - Under 10 players: 0
        - 10-14 players: 0-1
        - 15+ players: 1-2
        """
        if player_count < 10:
            return 0
        elif player_count < 15:
            return 1
        else:
            return 2

    @classmethod
    def build_role_distribution(
        cls,
        player_count: int,
        expansions: Optional[Set[Expansion]] = None,
    ) -> Dict[str, int]:
        """
        Build the complete role distribution for a game.
        
        Returns a dict mapping role names to their counts.
        """
        if expansions is None:
            expansions = {Expansion.BASIC}

        distribution: Dict[str, int] = {}

        # Calculate dynamic counts
        werewolf_count = cls.calculate_werewolves(player_count)
        neutral_count = cls.get_neutral_count(player_count) if cls.should_have_neutral(player_count) else 0

        # Start with werewolves (dynamic)
        distribution["Ma Sói"] = werewolf_count

        # Add essential village roles (only 1 of each)
        essential_roles = [
            "Tiên Tri", "Phù Thủy", "Thợ Săn", "Thần Tình Yêu",
            "Cô Bé", "Tên Trộm", "Trưởng Làng"
        ]
        for role_name in essential_roles:
            distribution[role_name] = 1

        # Add optional expansion roles (if available and enabled)
        optional_expansion_roles = {
            Expansion.NEW_MOON: ["Thằng Ngốc", "Già Làng", "Kẻ Thế Thân", "Bảo Vệ", "Hai Chị Em"],
            Expansion.THE_VILLAGE: ["Con Quạ", "Kẻ Phóng Hỏa"],
        }

        for exp, roles in optional_expansion_roles.items():
            if exp in expansions:
                for role_name in roles:
                    # Special case for Two Sisters (2 slots) and Hai Chị Em
                    if role_name in ["Hai Chị Em"]:
                        distribution[role_name] = 2
                    else:
                        distribution[role_name] = 1

        # Add neutral roles (limited)
        neutral_roles = {
            Expansion.NEW_MOON: "Thổi Sáo",
            Expansion.THE_VILLAGE: ["Sói Trắng", "Kẻ Phóng Hỏa"],
        }

        if neutral_count > 0:
            if Expansion.NEW_MOON in expansions and neutral_count > 0:
                distribution["Thổi Sáo"] = 1
                neutral_count -= 1

            if Expansion.THE_VILLAGE in expansions and neutral_count > 0:
                for neutral_role in ["Sói Trắng", "Kẻ Phóng Hỏa"]:
                    if neutral_count > 0 and neutral_role not in distribution:
                        distribution[neutral_role] = 1
                        neutral_count -= 1

        # Calculate total and fill with villagers
        total_assigned = sum(distribution.values())
        villagers_needed = max(0, player_count - total_assigned)
        distribution["Dân Làng"] = villagers_needed

        return distribution

    @classmethod
    def get_role_list(
        cls,
        player_count: int,
        expansions: Optional[Set[Expansion]] = None,
    ) -> List[str]:
        """
        Get a flat list of role names, properly distributed.
        
        Example: ["Werewolf", "Werewolf", "Seer", "Villager", ...]
        """
        distribution = cls.build_role_distribution(player_count, expansions)
        roles: List[str] = []
        for role_name, count in distribution.items():
            roles.extend([role_name] * count)
        return roles

    @classmethod
    def get_balance_info(
        cls,
        player_count: int,
        expansions: Optional[Set[Expansion]] = None,
    ) -> Dict[str, int]:
        """
        Get balance info grouped by alignment.
        
        Returns: {"village": count, "werewolf": count, "neutral": count}
        """
        distribution = cls.build_role_distribution(player_count, expansions)
        
        # Map role names to alignments (simplified)
        alignment_map = {
            "Ma Sói": Alignment.WEREWOLF,
            "Sói Trắng": Alignment.NEUTRAL,
            "Thổi Sáo": Alignment.NEUTRAL,
            "Kẻ Phóng Hỏa": Alignment.NEUTRAL,
        }

        info = {
            Alignment.VILLAGE: 0,
            Alignment.WEREWOLF: 0,
            Alignment.NEUTRAL: 0,
        }

        for role_name, count in distribution.items():
            alignment = alignment_map.get(role_name, Alignment.VILLAGE)
            info[alignment] += count

        return info

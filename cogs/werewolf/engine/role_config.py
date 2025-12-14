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
        RoleSlot("Werewolf", Alignment.WEREWOLF, Expansion.BASIC, count=4),
        # Villagers (13 fixed in base)
        RoleSlot("Villager", Alignment.VILLAGE, Expansion.BASIC, count=13),
        RoleSlot("Seer", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Little Girl", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Witch", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Hunter", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Cupid", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Thief", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Mayor", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Scapegoat", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Guard", Alignment.VILLAGE, Expansion.BASIC, count=1),
        RoleSlot("Raven", Alignment.VILLAGE, Expansion.BASIC, count=1),
    ]

    # New Moon expansion roles
    NEWMOON_ROLES = [
        RoleSlot("Idiot", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),
        RoleSlot("Elder", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),
        RoleSlot("Scapegoat", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),  # Thế thân
        RoleSlot("Guard", Alignment.VILLAGE, Expansion.NEW_MOON, count=1),  # Bảo vệ
        RoleSlot("Pied Piper", Alignment.NEUTRAL, Expansion.NEW_MOON, count=1),
        RoleSlot("Two Sisters", Alignment.VILLAGE, Expansion.NEW_MOON, count=2),
    ]

    # The Village expansion roles
    THEVILLAGE_ROLES = [
        RoleSlot("Raven", Alignment.VILLAGE, Expansion.THE_VILLAGE, count=1),
        RoleSlot("White Werewolf", Alignment.NEUTRAL, Expansion.THE_VILLAGE, count=1),
        RoleSlot("Pyromaniac", Alignment.NEUTRAL, Expansion.THE_VILLAGE, count=1),
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

        # Add base roles
        for role in cls.BASE_ROLES:
            if role.name == "Werewolf":
                # Override with calculated count
                distribution[role.name] = werewolf_count
            else:
                distribution[role.name] = role.count

        # Add expansion roles
        if Expansion.NEW_MOON in expansions:
            for role in cls.NEWMOON_ROLES:
                distribution[role.name] = distribution.get(role.name, 0) + role.count

        if Expansion.THE_VILLAGE in expansions:
            for role in cls.THEVILLAGE_ROLES:
                if role.alignment == Alignment.NEUTRAL:
                    # Only add neutral roles if allowed
                    if neutral_count > 0:
                        distribution[role.name] = distribution.get(role.name, 0) + min(role.count, neutral_count)
                        neutral_count -= min(role.count, neutral_count)
                else:
                    distribution[role.name] = distribution.get(role.name, 0) + role.count

        # Adjust villager count to balance total
        total_assigned = sum(distribution.values())
        villagers_needed = max(0, player_count - total_assigned)
        distribution["Villager"] = distribution.get("Villager", 0) + villagers_needed

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
            "Werewolf": Alignment.WEREWOLF,
            "White Werewolf": Alignment.NEUTRAL,
            "Pied Piper": Alignment.NEUTRAL,
            "Pyromaniac": Alignment.NEUTRAL,
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

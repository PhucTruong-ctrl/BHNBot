"""Dynamic role configuration based on player count and expansions with point-based balancing."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ..roles.base import Alignment, Expansion


@dataclass
class RoleSlot:
    """Represents a single role slot in the game."""

    name: str
    alignment: Alignment
    expansion: Expansion
    count: int = 1


class RoleConfig:
    """
    Manages role distribution based on player count and point-based balancing.
    
    Goal: Total game points should be close to 0 for balance.
    - Negative points: Werewolves and Neutrals
    - Positive points: Village roles
    """

    # Role point values (negative = wolf advantage, positive = village advantage)
    ROLE_POINTS = {
        # Werewolves (negative = wolf team)
        "Ma Sói": -6,
        "Sói To Xấu Xa": -8,
        "Sói Quỷ": -9,
        "Sói Lửa": -7,
        "Sói Anh": -6,
        "Sói Em": -6,
        
        # Neutrals (variable)
        "Sói Trắng": -10,
        "Thổi Sáo": 0,
        "Kẻ Phóng Hỏa": -3,
        "Kẻ Báo Thù": 2,
        "Thằng Ngốc": -1,
        "Bô Lão": 1,
        
        # Village - Tier 1: Powerful
        "Tiên Tri": 7,
        "Phù Thủy": 4,
        
        # Village - Tier 2: Strong
        "Bảo Vệ": 3,
        "Hiệp Sĩ": 3,
        "Thợ Săn": 3,
        "Con Quạ": 3,
        
        # Village - Tier 3: Medium
        "Trưởng Làng": 2,
        "Thẩm Phán": 2,
        "Cáo": 2,
        "Thần Gấu": 2,
        
        # Village - Tier 4: Utility
        "Phù Thủy": 4,
        "Cô Bé": 1,
        "Oan Nhân": 1,
        "Đứa Con Hoang": 2,
        "Sói Lai": 2,
        "Thần Tình Yêu": 1,
        "Tên Trộm": 1,
        "Cổ Hoặc Sư": 1,
        "Dược Sĩ": 2,
        "Thích Khách": 2,
        "Kỵ Sĩ": 2,
        "Ảnh Tử": 2,
        "Nguyệt Nữ": 2,
        "Người Tôi Tớ Trung Thành": 2,
        "Hai Chị Em": 1,
        "Già Làng": 1,
        
        # Base villager
        "Dân Làng": 1,
        
        # Diễn Viên (variable based on abilities selected)
        "Diễn Viên": 0,
    }

    # Predefined setups for specific player counts
    PRESETS = {
        # Small games (8-9 players)
        "small": {
            "player_range": (8, 9),
            "core_setup": {
                "Ma Sói": 2,
                "Tiên Tri": 1,
            },
            "fill_order": [
                ("Bảo Vệ", 1),
                ("Phù Thủy", 1),
                ("Thợ Săn", 1),
                ("Dân Làng", 3),
            ],
        },
        # Standard games (12-15 players)
        "standard": {
            "player_range": (12, 15),
            "core_setup": {
                "Ma Sói": 3,
                "Tiên Tri": 1,
            },
            "fill_order": [
                ("Phù Thủy", 1),
                ("Bảo Vệ", 1),
                ("Thợ Săn", 1),
                ("Sói Trắng", 1),
                ("Thần Tình Yêu", 1),
                ("Dân Làng", 6),
            ],
        },
        # Large games (16+ players)
        "large": {
            "player_range": (16, 100),
            "core_setup": {
                "Ma Sói": 4,
                "Tiên Tri": 1,
            },
            "fill_order": [
                ("Phù Thủy", 1),
                ("Bảo Vệ", 1),
                ("Thợ Săn", 1),
                ("Con Quạ", 1),
                ("Thần Tình Yêu", 1),
                ("Kẻ Phóng Hỏa", 1),
                ("Thổi Sáo", 1),
                ("Dân Làng", 8),
            ],
        },
    }

    @staticmethod
    def calculate_werewolves(player_count: int) -> int:
        """
        Calculate werewolf count: floor(player_count / 3).
        
        Examples:
        - 8 players: floor(8/3) = 2 Werewolves
        - 12 players: floor(12/3) = 4 Werewolves → clamped to 3
        - 15 players: floor(15/3) = 5 Werewolves → clamped to 4
        """
        base_count = player_count // 3
        # Clamp between 1 and player_count // 2
        return max(1, min(base_count, player_count // 2))

    @staticmethod
    def calculate_total_points(distribution: Dict[str, int]) -> float:
        """Calculate total game points for a distribution."""
        total = 0.0
        for role_name, count in distribution.items():
            points = RoleConfig.ROLE_POINTS.get(role_name, 0)
            total += points * count
        return total

    @classmethod
    def get_preset_for_players(cls, player_count: int) -> Optional[str]:
        """Get the preset name for a given player count."""
        for preset_name, preset_config in cls.PRESETS.items():
            min_p, max_p = preset_config["player_range"]
            if min_p <= player_count <= max_p:
                return preset_name
        return None

    @classmethod
    def build_role_distribution(
        cls,
        player_count: int,
        expansions: Optional[Set[Expansion]] = None,
    ) -> Dict[str, int]:
        """
        Build role distribution using predefined presets and point-based balancing.
        
        Algorithm:
        1. Select preset based on player count
        2. Add core roles (Seer + Werewolves)
        3. Fill remaining slots to balance toward 0 total points
        4. Fill any remaining slots with Villagers
        """
        if expansions is None:
            expansions = {Expansion.BASIC}

        distribution: Dict[str, int] = {}

        # Get matching preset
        preset_name = cls.get_preset_for_players(player_count)
        
        if preset_name:
            preset = cls.PRESETS[preset_name]
            
            # Add core roles
            for role, count in preset["core_setup"].items():
                distribution[role] = count
            
            # Fill using the preset order
            remaining_slots = player_count - sum(distribution.values())
            for role, count in preset["fill_order"]:
                if remaining_slots > 0:
                    add_count = min(count, remaining_slots)
                    distribution[role] = distribution.get(role, 0) + add_count
                    remaining_slots -= add_count
            
            # Fill any remaining with Villagers
            if remaining_slots > 0:
                distribution["Dân Làng"] = distribution.get("Dân Làng", 0) + remaining_slots
        else:
            # Fallback: use simple algorithm
            werewolf_count = cls.calculate_werewolves(player_count)
            distribution["Ma Sói"] = werewolf_count
            distribution["Tiên Tri"] = 1
            
            remaining_slots = player_count - werewolf_count - 1
            
            # Add powerful roles to balance
            if remaining_slots > 0:
                distribution["Phù Thủy"] = 1
                remaining_slots -= 1
            if remaining_slots > 0:
                distribution["Bảo Vệ"] = 1
                remaining_slots -= 1
            if remaining_slots > 0:
                distribution["Thợ Săn"] = 1
                remaining_slots -= 1
            
            # Fill rest with villagers
            if remaining_slots > 0:
                distribution["Dân Làng"] = remaining_slots

        return distribution

    @classmethod
    def get_role_list(
        cls,
        player_count: int,
        expansions: Optional[Set[Expansion]] = None,
    ) -> List[str]:
        """
        Get a flat list of role names, properly distributed.
        
        Example: ["Ma Sói", "Ma Sói", "Tiên Tri", "Dân Làng", ...]
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
    ) -> Dict[str, object]:
        """
        Get comprehensive balance info for a distribution.
        
        Returns: {
            "village": count,
            "werewolf": count,
            "neutral": count,
            "total_points": float,
            "distribution": Dict[str, int],
        }
        """
        distribution = cls.build_role_distribution(player_count, expansions)
        
        # Map role names to alignments
        alignment_map = {
            # Werewolves
            "Ma Sói": Alignment.WEREWOLF,
            "Sói To Xấu Xa": Alignment.WEREWOLF,
            "Sói Quỷ": Alignment.WEREWOLF,
            "Sói Lửa": Alignment.WEREWOLF,
            "Sói Anh": Alignment.WEREWOLF,
            "Sói Em": Alignment.WEREWOLF,
            # Neutrals
            "Sói Trắng": Alignment.NEUTRAL,
            "Thổi Sáo": Alignment.NEUTRAL,
            "Kẻ Phóng Hỏa": Alignment.NEUTRAL,
            "Kẻ Báo Thù": Alignment.NEUTRAL,
            "Thằng Ngốc": Alignment.NEUTRAL,
            "Bô Lão": Alignment.NEUTRAL,
        }

        alignment_counts = {
            Alignment.VILLAGE: 0,
            Alignment.WEREWOLF: 0,
            Alignment.NEUTRAL: 0,
        }

        for role_name, count in distribution.items():
            alignment = alignment_map.get(role_name, Alignment.VILLAGE)
            alignment_counts[alignment] += count

        total_points = cls.calculate_total_points(distribution)

        return {
            Alignment.VILLAGE: alignment_counts[Alignment.VILLAGE],
            Alignment.WEREWOLF: alignment_counts[Alignment.WEREWOLF],
            Alignment.NEUTRAL: alignment_counts[Alignment.NEUTRAL],
            "total_points": total_points,
            "distribution": distribution,
        }

    @classmethod
    def get_setup_debug_info(cls, player_count: int) -> str:
        """Get debug info about role distribution and points."""
        distribution = cls.build_role_distribution(player_count)
        total_points = cls.calculate_total_points(distribution)
        balance_info = cls.get_balance_info(player_count)
        
        lines = [
            f"🎮 **Setup cho {player_count} người chơi**",
            f"",
            f"**Phân bố vai trò:**",
        ]
        
        for role_name, count in sorted(distribution.items()):
            points = cls.ROLE_POINTS.get(role_name, 0)
            total_role_points = points * count
            lines.append(f"  • {role_name}: {count} (Điểm: {points} × {count} = {total_role_points})")
        
        lines.extend([
            f"",
            f"**Thống kê:**",
            f"  • Dân làng: {balance_info[Alignment.VILLAGE]}",
            f"  • Ma sói: {balance_info[Alignment.WEREWOLF]}",
            f"  • Trung lập: {balance_info[Alignment.NEUTRAL]}",
            f"  • **Tổng điểm: {total_points:.1f}**",
        ])
        
        return "\n".join(lines)

"""State representations for the Werewolf game."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Set

import discord

from ..roles.base import Alignment, Expansion, Role


class Phase(Enum):
    """Game phases."""

    LOBBY = auto()
    NIGHT = auto()
    DAY = auto()
    ENDED = auto()


@dataclass(slots=True)
class GameSettings:
    """Runtime configuration for a Werewolf match with dynamic day phase timing."""

    expansions: Set[Expansion] = field(default_factory=set)
    wolf_thread_name: str = "Hội Sói"
    
    # Night phase timing (static)
    lobby_timeout: int = 180
    night_intro_duration: int = 15
    night_vote_duration: int = 45  # Reduced from 90 to 45 seconds for faster night resolution
    
    # Day phase base times (will be calculated dynamically based on alive players)
    day_discussion_base: int = 60          # Base discussion time (seconds)
    day_discussion_per_player: int = 30    # Additional seconds per alive player
    day_vote_duration: int = 45            # Voting phase (seconds)
    day_defense_duration: int = 75         # Defense/Biện hộ phase (seconds)
    day_judgment_duration: int = 20        # Judgment/Biểu quyết phase (seconds)
    day_last_words_duration: int = 10      # Last words before execution (seconds)
    
    # Feature toggles
    allow_self_target_roles: Set[str] = field(default_factory=set)
    allow_skip_vote: bool = True           # Allow players to skip discussion phase
    
    def calculate_discussion_time(self, alive_players: int) -> int:
        """
        Calculate dynamic discussion time based on number of alive players.
        
        Formula: base_time + (alive_players * per_player_time)
        
        Examples:
        - 10 players: 60 + (10 * 30) = 360s (6 minutes)
        - 4 players: 60 + (4 * 30) = 180s (3 minutes)
        """
        return self.day_discussion_base + (alive_players * self.day_discussion_per_player)
    
    def get_day_phases_duration(self, alive_players: int) -> dict:
        """
        Get all day phase durations as a dictionary.
        
        Returns a dict with timing for each phase.
        """
        return {
            "discussion": self.calculate_discussion_time(alive_players),
            "vote": self.day_vote_duration,
            "defense": self.day_defense_duration,
            "judgment": self.day_judgment_duration,
            "last_words": self.day_last_words_duration,
        }


@dataclass(slots=True)
class PlayerState:
    """Represents a single player in a Werewolf match."""

    member: discord.Member
    roles: List[Role] = field(default_factory=list)
    alive: bool = True
    lover_id: Optional[int] = None
    charmed: bool = False
    vote_disabled: bool = False
    skills_disabled: bool = False  # Fire Wolf: vô hiệu hóa kỹ năng vĩnh viễn
    mayor: bool = False
    vote_weight: int = 1
    house_token: Optional[str] = None
    protected_last_night: bool = False
    is_sister: bool = False
    marked_by_raven: bool = False
    death_pending: bool = False

    @property
    def role(self) -> Optional[Role]:
        """Get primary (first) role for backward compatibility."""
        return self.roles[0] if self.roles else None

    @role.setter
    def role(self, value: Optional[Role]) -> None:
        """Set role, replacing all existing roles."""
        if value is None:
            self.roles.clear()
        else:
            self.roles = [value]

    def add_role(self, role: Role) -> None:
        """Add an additional role to the player."""
        self.roles.append(role)

    def remove_role(self, role_name: str) -> bool:
        """Remove a role by name. Returns True if removed."""
        for i, r in enumerate(self.roles):
            if r.metadata.name == role_name:
                self.roles.pop(i)
                return True
        return False

    def has_role(self, role_name: str) -> bool:
        """Check if player has a role by name."""
        return any(r.metadata.name == role_name for r in self.roles)

    def get_alignment_priority(self) -> Alignment:
        """Get primary alignment (Werewolf > Neutral > Village)."""
        if any(r.alignment == Alignment.WEREWOLF for r in self.roles):
            return Alignment.WEREWOLF
        if any(r.alignment == Alignment.NEUTRAL for r in self.roles):
            return Alignment.NEUTRAL
        return Alignment.VILLAGE

    def reset_night_flags(self) -> None:
        self.protected_last_night = False
        self.marked_by_raven = False
        self.death_pending = False

    @property
    def user_id(self) -> int:
        return self.member.id

    def faction_view(self) -> str:
        alignment = self.get_alignment_priority()
        if alignment == Alignment.WEREWOLF:
            return "Phe Ma Sói"
        if alignment == Alignment.NEUTRAL:
            return "Phe Trung Lập"
        return "Phe Dân Làng"

    def display_name(self) -> str:
        return self.member.display_name

    def is_alive(self) -> bool:
        return self.alive and not self.death_pending
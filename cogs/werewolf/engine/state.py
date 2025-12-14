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
    """Runtime configuration for a Werewolf match."""

    expansions: Set[Expansion] = field(default_factory=set)
    wolf_thread_name: str = "Hội Sói"
    lobby_timeout: int = 180
    night_intro_duration: int = 30
    night_vote_duration: int = 90
    day_discussion_duration: int = 60
    day_vote_duration: int = 120
    allow_self_target_roles: Set[str] = field(default_factory=set)


@dataclass(slots=True)
class PlayerState:
    """Represents a single player in a Werewolf match."""

    member: discord.Member
    roles: List[Role] = field(default_factory=list)
    alive: bool = True
    lover_id: Optional[int] = None
    charmed: bool = False
    vote_disabled: bool = False
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
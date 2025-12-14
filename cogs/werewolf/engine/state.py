"""State representations for the Werewolf game."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Set

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
    night_intro_duration: int = 15
    night_vote_duration: int = 45
    day_discussion_duration: int = 30
    day_vote_duration: int = 60
    allow_self_target_roles: Set[str] = field(default_factory=set)


@dataclass(slots=True)
class PlayerState:
    """Represents a single player in a Werewolf match."""

    member: discord.Member
    role: Optional[Role] = None
    alive: bool = True
    lover_id: Optional[int] = None
    charmed: bool = False
    vote_disabled: bool = False
    mayor: bool = False
    vote_weight: int = 1
    house_token: Optional[str] = None
    protected_last_night: bool = False
    marked_by_raven: bool = False
    death_pending: bool = False

    def reset_night_flags(self) -> None:
        self.protected_last_night = False
        self.marked_by_raven = False
        self.death_pending = False

    @property
    def user_id(self) -> int:
        return self.member.id

    def faction_view(self) -> str:
        if self.role and self.role.alignment == Alignment.WEREWOLF:
            return "Phe Ma Sói"
        if self.role and self.role.alignment == Alignment.NEUTRAL:
            return "Phe Trung Lập"
        return "Phe Dân Làng"

    def display_name(self) -> str:
        return self.member.display_name

    def is_alive(self) -> bool:
        return self.alive and not self.death_pending
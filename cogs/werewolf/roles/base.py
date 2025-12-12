"""Common role definitions for the Werewolf game."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional


class Alignment(str, Enum):
    """Faction alignment options."""

    VILLAGE = "village"
    WEREWOLF = "werewolf"
    NEUTRAL = "neutral"


class Expansion(str, Enum):
    """Role expansion source."""

    BASIC = "basic"
    NEW_MOON = "new_moon"
    THE_VILLAGE = "the_village"


@dataclass(slots=True)
class RoleMetadata:
    """Static information that describes a role."""

    name: str
    alignment: Alignment
    expansion: Expansion
    description: str
    max_count: Optional[int] = None
    first_night_only: bool = False
    night_order: int = 100
    priority: int = 100
    tags: tuple[str, ...] = field(default_factory=tuple)


class Role:
    """Base class for role behaviour."""

    metadata: RoleMetadata

    def __init__(self) -> None:
        if not hasattr(self, "metadata"):
            raise ValueError("Role subclasses must define a metadata attribute")
        self._self_target_used: bool = False

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def alignment(self) -> Alignment:
        return self.metadata.alignment

    @property
    def expansion(self) -> Expansion:
        return self.metadata.expansion

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def first_night_only(self) -> bool:
        return self.metadata.first_night_only

    @property
    def night_order(self) -> int:
        return self.metadata.night_order

    def can_self_target(self) -> bool:
        """Return True if the role can target itself at least once."""

        return "self_target" in self.metadata.tags and not self._self_target_used

    def mark_self_target(self) -> None:
        """Remember that the self-target option was consumed."""

        self._self_target_used = True

    async def on_assign(self, game: "WerewolfGame", player: "PlayerState") -> None:
        """Called when the role is assigned."""

        return None

    async def on_first_night(self, game: "WerewolfGame", player: "PlayerState") -> None:
        """Hook for roles that only act on night zero."""

        return None

    async def on_night(self, game: "WerewolfGame", player: "PlayerState", night_number: int) -> None:
        """Hook executed every night after assignment."""

        return None

    async def on_day(self, game: "WerewolfGame", player: "PlayerState", day_number: int) -> None:
        """Hook executed at the start of each day."""

        return None

    async def on_vote_result(
        self,
        game: "WerewolfGame",
        player: "PlayerState",
        vote_context: Dict[str, Any],
    ) -> None:
        """Hook executed after a vote resolves."""

        return None

    async def on_death(
        self,
        game: "WerewolfGame",
        player: "PlayerState",
        cause: str,
    ) -> None:
        """Hook executed when the player dies."""

        return None

    async def nightly_targets(
        self,
        game: "WerewolfGame",
        player: "PlayerState",
    ) -> Iterable["PlayerState"]:
        """Return iterable of valid targets for night action."""

        return ()

    def format_private_information(self) -> str:
        """Return the information to DM to the player upon assignment."""

        return self.description


# Forward reference imports for type checking only
if TYPE_CHECKING:  # pragma: nocover
    from ..engine.game import WerewolfGame
    from ..engine.state import PlayerState

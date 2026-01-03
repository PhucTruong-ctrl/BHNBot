"""Player domain model."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import discord

from .deck import Card
# Note: calculated properties 'hand_value' and 'hand_type' need services.
# BUT models shouldn't depend on services.
# They should just hold state. Logic moves to services.
# However, to keep it backward compatible easily, we import calculation logic?
# The guide says "Business Logic (Pure Python)" in core.
# So importing `calculation_service` here is acceptable or just move calculation here?
# `hand_eval` is complex logic -> Services.
# Properties in Model -> Convenient but couples model to logic.
# I will keep properties but import the functions from services.
# Circular dependency risk: Service needs Card/Player. Player needs Service.
# Solution: Import inside property.

class PlayerStatus(Enum):
    """Player status in a Xi Dach game."""
    WAITING = "waiting"       # Waiting for turn
    PLAYING = "playing"       # Currently playing their turn
    STAND = "stand"           # Stood (finished)
    BUST = "bust"             # Busted (over 21)
    BLACKJACK = "blackjack"   # Got Xi Dach/Xi Ban
    SPECTATING = "spectating" # Just watching (multiplayer)

@dataclass
class Player:
    """Represents a player in Xi Dach game."""
    user_id: int
    username: str
    bet: int = 0
    hand: List[Card] = field(default_factory=list)
    status: PlayerStatus = PlayerStatus.WAITING
    is_doubled: bool = False
    is_ready: bool = False
    interaction: Optional[discord.Interaction] = None

    @property
    def hand_value(self) -> int:
        from ..services.hand_service import calculate_hand_value
        return calculate_hand_value(self.hand)

    @property
    def hand_type(self):
        from ..services.hand_service import determine_hand_type
        _, hand_type = determine_hand_type(self.hand)
        return hand_type

    @property
    def is_bust(self) -> bool:
        return self.hand_value > 21

    @property
    def can_double(self) -> bool:
        return len(self.hand) == 2 and not self.is_doubled

    def add_card(self, card: Card) -> None:
        self.hand.append(card)
        if self.hand_value > 21:
            self.status = PlayerStatus.BUST
        elif len(self.hand) == 2:
            from ..services.hand_service import determine_hand_type, HandType
            _, hand_type = determine_hand_type(self.hand)
            if hand_type == HandType.XI_BAN:
                self.status = PlayerStatus.BLACKJACK

    def reset(self) -> None:
        self.bet = 0
        self.hand = []
        self.status = PlayerStatus.WAITING
        self.is_doubled = False
        self.is_ready = False

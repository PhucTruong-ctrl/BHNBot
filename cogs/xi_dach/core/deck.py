"""Deck implementation."""

import random
from dataclasses import dataclass, field
from typing import List
from enum import Enum

class Suit(Enum):
    """Card suits with emoji representation."""
    SPADE = "♠️"
    HEART = "♥️"
    DIAMOND = "♦️"
    CLUB = "♣️"

class Rank(Enum):
    """Card ranks with their base values."""
    ACE = ("A", 11)  # Ace can be 1 or 11
    TWO = ("2", 2)
    THREE = ("3", 3)
    FOUR = ("4", 4)
    FIVE = ("5", 5)
    SIX = ("6", 6)
    SEVEN = ("7", 7)
    EIGHT = ("8", 8)
    NINE = ("9", 9)
    TEN = ("10", 10)
    JACK = ("J", 10)
    QUEEN = ("Q", 10)
    KING = ("K", 10)

    def __init__(self, symbol: str, value: int):
        self.symbol = symbol
        self.base_value = value

@dataclass
class Card:
    """Represents a playing card."""
    suit: Suit
    rank: Rank

    @property
    def value(self) -> int:
        return self.rank.base_value

    @property
    def is_ace(self) -> bool:
        return self.rank == Rank.ACE

    @property
    def is_ten_value(self) -> bool:
        return self.rank in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING)

    def __str__(self) -> str:
        return f"{self.rank.symbol}{self.suit.value}"

    def to_emoji(self) -> str:
        """Get emoji representation for Discord display."""
        return f"**`{self.rank.symbol}`**{self.suit.value}"

@dataclass
class Deck:
    """A standard 52-card deck."""
    cards: List[Card] = field(default_factory=list)

    def __post_init__(self):
        self.reset()

    def reset(self) -> None:
        self.cards = [Card(suit, rank) for suit in Suit for rank in Rank]
        self.shuffle()

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def draw(self, count: int = 1) -> List[Card]:
        if count > len(self.cards):
            self.reset()
        drawn = self.cards[:count]
        self.cards = self.cards[count:]
        return drawn

    def draw_one(self) -> Card:
        return self.draw(1)[0]

    def __len__(self) -> int:
        return len(self.cards)

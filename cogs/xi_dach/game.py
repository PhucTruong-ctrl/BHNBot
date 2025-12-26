"""
Xi Dach (Vietnamese Blackjack) - Core Game Logic

Contains card, deck, and hand calculation logic following Vietnamese Blackjack rules.
"""
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
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


class HandType(Enum):
    """Special hand types in Xi Dach."""
    XI_DACH = "xidach"      # Blackjack: A + 10-value card (21 in 2 cards)
    XI_BAN = "xiban"        # Two Aces
    NGU_LINH = "ngulinh"    # 5 cards with total <= 21
    NORMAL = "normal"       # Regular hand
    BUST = "bust"           # Over 21


@dataclass
class Card:
    """Represents a playing card.
    
    Attributes:
        suit (Suit): The card's suit.
        rank (Rank): The card's rank.
    """
    suit: Suit
    rank: Rank

    @property
    def value(self) -> int:
        """Get base value of the card."""
        return self.rank.base_value

    @property
    def is_ace(self) -> bool:
        """Check if card is an Ace."""
        return self.rank == Rank.ACE

    @property
    def is_ten_value(self) -> bool:
        """Check if card is 10, J, Q, or K."""
        return self.rank in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING)

    def __str__(self) -> str:
        """Display card as 'Rank Suit' (e.g., 'A ♠️')."""
        return f"{self.rank.symbol}{self.suit.value}"

    def to_emoji(self) -> str:
        """Get emoji representation for Discord display with colored suits."""
        # Use colored backgrounds for red/black suits
        if self.suit in (Suit.HEART, Suit.DIAMOND):
            return f"**`{self.rank.symbol}`**{self.suit.value}"
        else:
            return f"**`{self.rank.symbol}`**{self.suit.value}"
    
    def to_fancy(self) -> str:
        """Get fancy card display with box styling."""
        return f"「{self.rank.symbol}{self.suit.value}」"


@dataclass
class Deck:
    """A standard 52-card deck with shuffle and draw functionality.
    
    Attributes:
        cards (List[Card]): Remaining cards in the deck.
    """
    cards: List[Card] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and shuffle the deck."""
        self.reset()

    def reset(self) -> None:
        """Reset deck to full 52 cards and shuffle."""
        self.cards = [
            Card(suit, rank)
            for suit in Suit
            for rank in Rank
        ]
        self.shuffle()

    def shuffle(self) -> None:
        """Shuffle the deck in place."""
        random.shuffle(self.cards)

    def draw(self, count: int = 1) -> List[Card]:
        """Draw cards from the deck.
        
        Args:
            count (int): Number of cards to draw.
            
        Returns:
            List[Card]: Drawn cards.
            
        Raises:
            ValueError: If not enough cards in deck.
        """
        if count > len(self.cards):
            # Auto-reset deck if running low
            self.reset()
        
        drawn = self.cards[:count]
        self.cards = self.cards[count:]
        return drawn

    def draw_one(self) -> Card:
        """Draw a single card from the deck.
        
        Returns:
            Card: The drawn card.
        """
        return self.draw(1)[0]

    def __len__(self) -> int:
        return len(self.cards)


def calculate_hand_value(cards: List[Card]) -> int:
    """Calculate the total value of a hand, treating Aces optimally.
    
    Aces count as 11 unless that would bust the hand, then count as 1.
    
    Args:
        cards (List[Card]): Cards in hand.
        
    Returns:
        int: Best possible hand value.
    """
    total = 0
    count = len(cards)
    initial_aces_as_10 = 0

    for i, card in enumerate(cards):
        if not card.is_ace:
            total += card.value
        else:
            # Ace Logic provided by User:
            
            # 1. Drawn Ace (3rd card onwards, index >= 2) -> Always 1 point
            if i >= 2:
                total += 1
                continue
                
            # 2. Initial Ace (First 2 cards, index 0 or 1)
            # - Hand size 2: 11 points (Xì)
            # - Hand size 3: 10 points (Flexible to 1 if bust)
            # - Hand size 4+: 1 point
            if count == 2:
                total += 11
            elif count == 3:
                total += 10
                initial_aces_as_10 += 1
            else:
                total += 1  # 4 or 5 cards
                
    # If Bust with Ace=10 (at 3 cards), reduce to 1
    while total > 21 and initial_aces_as_10 > 0:
        total -= 9  # Change 10 to 1
        initial_aces_as_10 -= 1
        
    return total


def determine_hand_type(cards: List[Card]) -> Tuple[int, HandType]:
    """Determine the hand type and value.
    
    Args:
        cards (List[Card]): Cards in hand.
        
    Returns:
        Tuple[int, HandType]: (hand_value, hand_type)
    """
    value = calculate_hand_value(cards)
    
    # Check special hands
    if len(cards) == 2:
        # Xi Ban: Two Aces
        if all(card.is_ace for card in cards):
            return value, HandType.XI_BAN
        
        # Xi Dach: A + 10-value card = 21
        if value == 21:
            has_ace = any(card.is_ace for card in cards)
            has_ten = any(card.is_ten_value for card in cards)
            if has_ace and has_ten:
                return value, HandType.XI_DACH

    # Ngu Linh: 5 cards with total <= 21
    if len(cards) == 5 and value <= 21:
        return value, HandType.NGU_LINH

    # Bust: Over 21
    if value > 21:
        return value, HandType.BUST

    return value, HandType.NORMAL


def format_hand(cards: List[Card], hide_first: bool = False) -> str:
    """Format a hand for Discord display (text fallback).
    
    Args:
        cards (List[Card]): Cards to display.
        hide_first (bool): If True, hide the first card (for dealer).
        
    Returns:
        str: Formatted string of cards.
    """
    if not cards:
        return "*(Không có bài)*"
    
    if hide_first and len(cards) > 1:
        return f"🎴 {cards[1].to_emoji()}"  # Hidden card + visible card
    
    return " ".join(card.to_emoji() for card in cards)


async def render_hand_image(
    cards: List[Card],
    player_name: str = "Bài của bạn"
) -> bytes:
    """Render a hand of cards to PNG image bytes with player name label.
    
    Uses Pillow via card_renderer module (non-blocking).
    
    Args:
        cards (List[Card]): Cards to render.
        player_name (str): Name to display as label.
        
    Returns:
        bytes: PNG image data.
    """
    from .card_renderer import render_player_hand
    from core.logger import setup_logger
    
    logger = setup_logger("GameLogic", "cogs/game_logic.log")
    
    try:
        logger.info(f"[GAME_RENDER] Start rendering for {player_name}, cards={len(cards)}")
        # Convert Card objects to (rank, suit) tuples
        card_tuples = [(card.rank.symbol, card.suit.value) for card in cards]
        
        result = await render_player_hand(card_tuples, player_name)
        logger.info(f"[GAME_RENDER] Success, size={len(result)} bytes")
        return result
    except Exception as e:
        logger.error(f"[GAME_RENDER_ERROR] Failed: {e}", exc_info=True)
        raise


async def render_game_state_image(
    dealer_cards: List[Card],
    players_data: list,
    hide_dealer: bool = True
) -> bytes:
    """Render complete game state (dealer + all players) as single image.
    
    Args:
        dealer_cards: Dealer's cards
        players_data: List of dicts with 'name', 'cards' (List[Card]), 'score', 'bet'
        hide_dealer: Whether to hide dealer's first card
        
    Returns:
        bytes: PNG image data
    """
    from .card_renderer import render_game_state
    
    # Convert dealer cards
    dealer_tuples = [(c.rank.symbol, c.suit.value) for c in dealer_cards]
    
    # Convert player data
    players = []
    for p in players_data:
        card_tuples = [(c.rank.symbol, c.suit.value) for c in p.get('cards', [])]
        players.append({
            'name': p.get('name', 'Player'),
            'cards': card_tuples,
            'score': p.get('score', 0),
            'bet': p.get('bet', 0)
        })
    
    return await render_game_state(dealer_tuples, players, hide_dealer)


def get_hand_description(hand_type: HandType) -> str:
    """Get Vietnamese description for hand type.
    
    Args:
        hand_type (HandType): The hand type.
        
    Returns:
        str: Vietnamese description.
    """
    descriptions = {
        HandType.XI_DACH: "🎰 **XÌ DÁCH!**",
        HandType.XI_BAN: "🎰 **XÌ BÀN!** (2 Aces)",
        HandType.NGU_LINH: "🐉 **NGŨ LINH!** (5 lá ≤ 21)",
        HandType.BUST: "💥 **QUÁ 21!**",
        HandType.NORMAL: "",
    }
    return descriptions.get(hand_type, "")


def compare_hands(
    player_cards: List[Card],
    dealer_cards: List[Card]
) -> Tuple[str, float]:
    """Compare player and dealer hands to determine winner.
    
    Args:
        player_cards (List[Card]): Player's hand.
        dealer_cards (List[Card]): Dealer's hand.
        
    Returns:
        Tuple[str, float]: (result, multiplier)
            result: 'win', 'lose', 'push' (tie)
            multiplier: Payout multiplier (e.g., 2.0 for Xi Dach win)
    """
    p_value, p_type = determine_hand_type(player_cards)
    d_value, d_type = determine_hand_type(dealer_cards)

    # Player under 16 (Chua du tuoi) = instant loss (regardless of dealer)
    if p_value < 16 and p_type == HandType.NORMAL:
        return "lose", 0.0

    # Player bust = instant loss
    if p_type == HandType.BUST:
        return "lose", 0.0

    # Dealer bust = player wins
    if d_type == HandType.BUST:
        return "win", 2.0

    # Xi Ban beats everything
    if p_type == HandType.XI_BAN:
        if d_type == HandType.XI_BAN:
            return "push", 1.0
        return "win", 4.0  # Xi Ban pays x3 (Profit) -> 4.0 Total

    if d_type == HandType.XI_BAN:
        return "lose", 0.0

    # Ngu Linh beats Xi Dach and Normal (User Rule)
    if p_type == HandType.NGU_LINH:
        if d_type == HandType.NGU_LINH:
            # Compare values
            if p_value > d_value:
                return "win", 2.0
            elif p_value < d_value:
                return "lose", 0.0
            return "push", 1.0
        return "win", 2.0

    if d_type == HandType.NGU_LINH:
        return "lose", 0.0

    # Xi Dach beats Normal (but loses to Ngu Linh/Xi Ban)
    if p_type == HandType.XI_DACH:
        if d_type == HandType.XI_DACH:
            return "push", 1.0
        return "win", 3.0  # Xi Dach pays x2 (Profit) -> 3.0 Total

    if d_type == HandType.XI_DACH:
        return "lose", 0.0

    # Normal comparison
    if p_value > d_value:
        return "win", 2.0
    elif p_value < d_value:
        return "lose", 0.0
    return "push", 1.0

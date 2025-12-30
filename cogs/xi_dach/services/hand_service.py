"""
Xi Dach Hand Evaluation Service.

Rules Engine implementing proper Vietnamese Xi Dach rules:
- Hand Ranking: XI_BAN > XI_DACH > NGU_LINH > NORMAL > BUST
- Ngũ Linh (5 cards <= 21): Lower score wins in mirror match
- Xi Ban/Xi Dach only valid for initial 2 cards
"""

from enum import Enum, auto
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.deck import Card


class HandType(Enum):
    """Hand types in order of strength (higher value = stronger)."""
    BUST = 0        # Over 21
    NORMAL = 1      # Standard hand
    NGU_LINH = 2    # 5 cards <= 21 (lower score wins in mirror)
    XI_DACH = 3     # Ace + 10/J/Q/K (only 2 cards)
    XI_BAN = 4      # Two Aces (only 2 cards)


def calculate_hand_value(hand: List["Card"]) -> int:
    """
    Calculate the best possible hand value.
    Aces count as 11 or 1, whichever is better without busting.
    
    Args:
        hand: List of Card objects
        
    Returns:
        Best possible score (<=21 if possible)
    """
    if not hand:
        return 0
    
    total = 0
    
    # USER RULE: Ace = 1 if hand has > 2 cards.
    # Ace = 11 (or 1 if bust) if hand has <= 2 cards.
    
    if len(hand) > 2:
        # Strict Mode: Ace always 1
        for card in hand:
            if card.is_ace:
                total += 1
            else:
                total += card.value
    else:
        # Standard Mode (<= 2 cards): Ace starts at 11
        ace_count = 0
        for card in hand:
            if card.is_ace:
                ace_count += 1
                total += 11
            else:
                total += card.value
        
        # Downgrade if bust
        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1
            
    return total


def determine_hand_type(hand: List["Card"]) -> Tuple[int, HandType]:
    """
    Determine hand type and score.
    
    IMPORTANT: XI_BAN and XI_DACH only apply to exactly 2 cards.
    3+ Aces = Normal hand (not Xi Ban).
    
    Args:
        hand: List of Card objects
        
    Returns:
        Tuple of (score, HandType)
    """
    if not hand:
        return 0, HandType.NORMAL
    
    score = calculate_hand_value(hand)
    card_count = len(hand)
    
    # Bust check first
    if score > 21:
        return score, HandType.BUST
    
    # Special hands only for exactly 2 cards
    if card_count == 2:
        ace_count = sum(1 for c in hand if c.is_ace)
        ten_count = sum(1 for c in hand if c.is_ten_value)
        
        # Xi Ban: Two Aces
        if ace_count == 2:
            return score, HandType.XI_BAN
        
        # Xi Dach: One Ace + One 10-value card
        if ace_count == 1 and ten_count == 1:
            return score, HandType.XI_DACH
    
    # Ngu Linh: 5 cards without busting
    if card_count == 5 and score <= 21:
        return score, HandType.NGU_LINH
    
    return score, HandType.NORMAL


def is_du_tuoi(hand: List["Card"]) -> bool:
    """
    Check if hand meets minimum score requirement to Stand (16+).
    Special hands always qualify.
    
    Args:
        hand: List of Card objects
        
    Returns:
        True if player can Stand
    """
    score, hand_type = determine_hand_type(hand)
    
    # Special hands always qualify
    if hand_type in (HandType.XI_BAN, HandType.XI_DACH, HandType.NGU_LINH):
        return True
    
    return score >= 16


def get_hand_description(hand_type: HandType) -> str:
    """Get Vietnamese description for hand type."""
    descriptions = {
        HandType.BUST: "💥 QUÁ 21!",
        HandType.NORMAL: "",
        HandType.NGU_LINH: "🏆 Ngũ Linh",
        HandType.XI_DACH: "🎰 Xì Dách",
        HandType.XI_BAN: "👑 Xì Bàn",
    }
    return descriptions.get(hand_type, "")


def format_hand(hand: List["Card"], hide_first: bool = False) -> str:
    """Format hand for Discord display."""
    if not hand:
        return "🃏"
    
    if hide_first:
        formatted = ["❓"] + [c.to_emoji() for c in hand[1:]]
    else:
        formatted = [c.to_emoji() for c in hand]
    
    return " ".join(formatted)


def compare_hands(
    player_hand: List["Card"],
    dealer_hand: List["Card"]
) -> Tuple[str, float]:
    """
    Compare player hand vs dealer hand.
    
    Rules:
    - Player BUST: Always loses (even if dealer busts later)
    - Dealer BUST: Player wins (if player not bust)
    - NGU_LINH vs NGU_LINH: Lower score wins
    - NGU_LINH vs NORMAL: NGU_LINH wins
    - Same type: Higher score wins
    
    Args:
        player_hand: Player's cards
        dealer_hand: Dealer's cards
        
    Returns:
        Tuple of (result: "win"/"lose"/"push", multiplier: float)
    """
    p_score, p_type = determine_hand_type(player_hand)
    d_score, d_type = determine_hand_type(dealer_hand)
    
    # Rule 1: Player BUST always loses
    if p_type == HandType.BUST:
        return ("lose", 0.0)
    
    # Rule 2: Dealer BUST, Player wins
    if d_type == HandType.BUST:
        return ("win", 2.0)
    
    # Rule 3: Compare types first (higher type wins)
    if p_type.value > d_type.value:
        # Player has stronger hand type
        # Payouts by rarity: XI_BAN 3.0x, NGU_LINH 3.5x, XI_DACH 2.5x
        if p_type == HandType.XI_BAN:
            return ("win", 3.0)  # Two Aces - Very rare
        elif p_type == HandType.XI_DACH:
            return ("win", 2.5)  # Blackjack - Rare
        elif p_type == HandType.NGU_LINH:
            return ("win", 3.5)  # 5 cards ≤21 - Hardest
        return ("win", 2.0)  # Normal - Base
    
    if p_type.value < d_type.value:
        # Dealer has stronger hand type
        return ("lose", 0.0)
    
    # Same hand type - compare scores
    if p_type == HandType.NGU_LINH:
        # NGU_LINH vs NGU_LINH: Lower score wins
        if p_score < d_score:
            return ("win", 3.5)  # Ngu Linh win pays 3.5x
        elif p_score > d_score:
            return ("lose", 0.0)
        else:
            return ("push", 1.0)
    else:
        # NORMAL vs NORMAL: Higher score wins
        if p_score > d_score:
            return ("win", 2.0)
        elif p_score < d_score:
            return ("lose", 0.0)
        else:
            return ("push", 1.0)


def check_phase1_winner(
    player_hand: List["Card"],
    dealer_hand: List["Card"]
) -> Tuple[str, float]:
    """
    Phase 1 comparison (initial 2 cards).
    Only XI_BAN and XI_DACH are relevant here.
    
    Args:
        player_hand: Player's 2 cards
        dealer_hand: Dealer's 2 cards
        
    Returns:
        Tuple of (result, multiplier)
    """
    _, p_type = determine_hand_type(player_hand)
    _, d_type = determine_hand_type(dealer_hand)
    
    # Only compare special hands
    if p_type not in (HandType.XI_BAN, HandType.XI_DACH):
        p_type = HandType.NORMAL
    if d_type not in (HandType.XI_BAN, HandType.XI_DACH):
        d_type = HandType.NORMAL
    
    # Dealer has special hand
    if d_type in (HandType.XI_BAN, HandType.XI_DACH):
        if p_type.value > d_type.value:
            # Player XI_BAN beats Dealer XI_DACH
            return ("win", 3.0 if p_type == HandType.XI_BAN else 2.5)
        elif p_type.value == d_type.value:
            return ("push", 1.0)
        else:
            return ("lose", 0.0)
    
    # Dealer normal, Player special
    if p_type in (HandType.XI_BAN, HandType.XI_DACH):
        return ("win", 3.0 if p_type == HandType.XI_BAN else 2.5)
    
    # Both normal - no Phase 1 resolution
    return ("continue", 0.0)

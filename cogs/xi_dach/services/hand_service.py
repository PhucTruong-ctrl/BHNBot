"""Hand Evaluation Service."""

from typing import List, Tuple
from enum import Enum
from ..core.deck import Card

class HandType(Enum):
    """Special hand types in Xi Dach."""
    XI_DACH = "xidach"      # A + 10/J/Q/K
    XI_BAN = "xiban"        # A + A
    NGU_LINH = "ngulinh"    # 5 cards <= 21
    NORMAL = "normal"
    BUST = "bust"

def calculate_hand_value(cards: List[Card]) -> int:
    """Calculate total value treating Aces optimally."""
    total = 0
    count = len(cards)
    initial_aces_as_10 = 0

    for i, card in enumerate(cards):
        if not card.is_ace:
            total += card.value
        else:
            # Drawn Ace (3rd card+) -> Always 1
            if i >= 2:
                total += 1
                continue
                
            # Initial Ace
            if count == 2:
                total += 11
            elif count == 3:
                total += 10
                initial_aces_as_10 += 1
            else:
                total += 1
                
    # Adjust for Bust where flexible Ace can drop
    # Only Ace from START (idx < 2) can count as 10 or 1.
    # Logic above adds 10 for Aces if count <= 3 and is initial.
    # Standard rule: AA = 2 (or 12/22 but Xi Ban is special).
    # Here we focus on point value.
    while total > 21 and initial_aces_as_10 > 0:
        total -= 9
        initial_aces_as_10 -= 1
        
    return total

def determine_hand_type(cards: List[Card]) -> Tuple[int, HandType]:
    """Determine hand type and value."""
    value = calculate_hand_value(cards)
    
    if len(cards) == 2:
        if all(c.is_ace for c in cards):
            return value, HandType.XI_BAN
        if value == 21:
            has_ace = any(c.is_ace for c in cards)
            has_ten = any(c.is_ten_value for c in cards)
            if has_ace and has_ten:
                return value, HandType.XI_DACH

    if len(cards) == 5 and value <= 21:
        return value, HandType.NGU_LINH

    if value > 21:
        return value, HandType.BUST

    return value, HandType.NORMAL

def get_hand_description(hand_type: HandType) -> str:
    """Get Vietnamese description for hand."""
    descriptions = {
        HandType.XI_DACH: "🎰 **XÌ DÁCH!**",
        HandType.XI_BAN: "🎰 **XÌ BÀN!** (2 Aces)",
        HandType.NGU_LINH: "🐉 **NGŨ LINH!** (5 lá ≤ 21)",
        HandType.BUST: "💥 **QUÁ 21!**",
        HandType.NORMAL: "",
    }
    return descriptions.get(hand_type, "")

def format_hand(cards: List[Card], hide_first: bool = False) -> str:
    """Format hand for display."""
    if not cards:
        return "*(Không có bài)*"
    if hide_first and len(cards) > 1:
        return f"🎴 {cards[1].to_emoji()}"
    return " ".join(c.to_emoji() for c in cards)

def compare_hands(player_cards: List[Card], dealer_cards: List[Card]) -> Tuple[str, float]:
    """Compare player vs dealer."""
    p_value, p_type = determine_hand_type(player_cards)
    d_value, d_type = determine_hand_type(dealer_cards)

    # Player constraint: < 16 is loss
    if p_value < 16 and p_type == HandType.NORMAL:
        return "lose", 0.0

    if p_type == HandType.BUST:
        return "lose", 0.0

    if d_type == HandType.BUST:
        return "win", 2.0

    # Xi Ban heirarchy
    if p_type == HandType.XI_BAN:
        return "push", 1.0 if d_type == HandType.XI_BAN else "win", 4.0
    if d_type == HandType.XI_BAN:
        return "lose", 0.0

    # Ngu Linh heirarchy
    if p_type == HandType.NGU_LINH:
        if d_type == HandType.NGU_LINH:
            if p_value > d_value: return "win", 2.0
            elif p_value < d_value: return "lose", 0.0
            return "push", 1.0
        return "win", 2.0
    if d_type == HandType.NGU_LINH:
        return "lose", 0.0

    # Xi Dach heirarchy
    if p_type == HandType.XI_DACH:
        return "push", 1.0 if d_type == HandType.XI_DACH else "win", 3.0
    if d_type == HandType.XI_DACH:
        return "lose", 0.0

    # Normal comparison
    if p_value > d_value: return "win", 2.0
    if p_value < d_value: return "lose", 0.0
    return "push", 1.0

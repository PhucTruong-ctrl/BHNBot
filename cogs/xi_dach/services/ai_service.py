"""Dealer AI Service."""

from typing import List, Tuple
from ..core.deck import Card
from .hand_service import calculate_hand_value

def get_dealer_decision(dealer_hand: List[Card], players_data: list = None) -> Tuple[str, str]:
    """Decide Dealer's next move based on Standard Soft 17 Rules.
    
    Returns:
        Tuple[str, str]: (action, reason)
    """
    value = calculate_hand_value(dealer_hand)
    hand_size = len(dealer_hand)
    
    # 1. HARD STOP: 5 Cards (Ngũ Linh candidates) or 21 Points
    if hand_size == 5:
        return "stand", "ngu_linh_achieved"
        
    if value >= 21:
        return "stand", "max_point"
        
    # 2. SOFT 17 RULE: Hit if < 16 (Standard VN: 16 is 'du tuoi')
    if value < 16:
        return "hit", "under_16"
        
    if value == 16:
        # "Dằn non" strategy: Stand on 16 to avoid bust (50% chance)
        return "stand", "qualified_16"

    # >= 17 -> Stand
    return "stand", "safe_stand"

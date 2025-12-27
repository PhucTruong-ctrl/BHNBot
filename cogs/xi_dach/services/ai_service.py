"""
Xi Dach AI Service - Smart Dealer Logic.

Implements risk-based decision making:
- Mandatory: Draw until score >= 16
- Smart: Analyze survivors and decide based on risk
"""

import random
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.deck import Card
    from ..core.player import Player

from .hand_service import calculate_hand_value, determine_hand_type, HandType


def get_dealer_decision(
    dealer_hand: List["Card"],
    survivors: List["Player"] = None
) -> Tuple[str, str]:
    """
    Determine dealer's next action.
    
    Smart AI Logic:
    1. MANDATORY: Draw if score < 16
    2. CHECK: If 5 cards (Ngu Linh) -> STAND
    3. SMART: Analyze how many survivors dealer is losing to
    
    Args:
        dealer_hand: Dealer's current cards
        survivors: List of Player objects still in game (not BUST)
        
    Returns:
        Tuple of (action: "hit"/"stand", reason: str)
    """
    score, hand_type = determine_hand_type(dealer_hand)
    card_count = len(dealer_hand)
    
    # Check Ngu Linh first (5 cards <= 21)
    if card_count >= 5:
        if hand_type == HandType.NGU_LINH:
            return ("stand", "Ngũ Linh! Dealer dừng rút.")
        elif hand_type == HandType.BUST:
            return ("stand", "Dealer quắc (5+ lá)!")
    
    # BUST - already lost
    if hand_type == HandType.BUST:
        return ("stand", f"Dealer quắc ({score} điểm)!")
    
    # MANDATORY: Draw until 16
    if score < 16:
        return ("hit", f"Dealer chỉ có {score} điểm, chưa đủ tuổi.")
    
    # SMART DECISION (16 - 21)
    if survivors is None or len(survivors) == 0:
        # No context, play conservatively
        if score >= 17:
            return ("stand", f"Dealer dằn ({score} điểm).")
        else:
            return ("hit", f"Dealer liều rút thêm ({score} điểm).")
    
    # Calculate survivors dealer is losing to
    losing_to = 0
    ngu_linh_exists = False
    
    for player in survivors:
        p_score, p_type = determine_hand_type(player.hand)
        
        # Skip BUST players (already lost)
        if p_type == HandType.BUST:
            continue
        
        # NGU_LINH beats all normal hands
        if p_type == HandType.NGU_LINH:
            ngu_linh_exists = True
            losing_to += 1
            continue
        
        # Compare scores for normal hands
        if p_score > score:
            losing_to += 1
    
    total_active = sum(1 for p in survivors 
                       if determine_hand_type(p.hand)[1] != HandType.BUST)
    
    # Decision Matrix
    if losing_to == 0:
        # Winning or tied with everyone
        return ("stand", f"Dealer đang thắng tất cả! Dằn ({score} điểm).")
    
    if score <= 17:
        # Low score and losing - aggressive draw
        return ("hit", f"Dealer {score} điểm, đang thua {losing_to} người. Liều!")
    
    if score == 18:
        # Border case - draw only if losing to majority
        if total_active > 0 and losing_to > total_active / 2:
            return ("hit", f"Dealer 18 điểm nhưng thua hơn nửa bàn. Liều!")
        return ("stand", f"Dealer 18 điểm, chấp nhận rủi ro. Dằn.")
    
    # 19, 20, 21 - Always stand
    return ("stand", f"Dealer {score} điểm. Dằn an toàn.")


def get_smart_think_time() -> float:
    """
    Get random thinking time for dealer AI.
    Makes the game feel more dynamic.
    
    Returns:
        Sleep duration in seconds (1-5s)
    """
    return random.uniform(1.0, 4.0)

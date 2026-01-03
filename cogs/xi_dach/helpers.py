"""Helper utilities for Xi Dach game."""

import random
from .constants import (
    DEALER_MESSAGES,
    PLAYER_WIN_MESSAGES,
    PLAYER_LOSE_MESSAGES,
    PLAYER_PUSH_MESSAGES,
)
from .services.hand_service import HandType

def format_final_result_text(
    dealer_score: int,
    dealer_type: HandType,
    dealer_hand: list,
    results: list
) -> str:
    """Format final multiplayer blackjack results as fun text.
    
    Args:
        dealer_score: Dealer's final score
        dealer_type: Dealer's hand type (XI_DACH, BUST, NORMAL, etc.)
        dealer_hand: List of dealer's cards (strings)
        results: List of player result dicts
        
    Returns:
        Formatted multi-line string with dealer + all players
    """
    lines = []
    
    # PART 1: Dealer Result
    dealer_msg = _format_dealer_result(dealer_score, dealer_type, dealer_hand)
    lines.append(dealer_msg)
    lines.append("")  # Blank line
    
    # PART 2: Player Results
    for r in results:
        player_msg = _format_player_result(r)
        lines.append(player_msg)
    
    return "\n".join(lines)

def _format_dealer_result(score, hand_type, hand):
    """Format dealer result with random message."""
    # FIX: Helper handles List[Card], must convert to string (emoji)
    cards_str = " ".join([c.to_emoji() for c in hand])
    
    if hand_type == HandType.XI_DACH:
        template = random.choice(DEALER_MESSAGES["blackjack"])
        # Format might not need score if it says Blackjack
        # But consistent display:
        return f"{template}\n🤖 **Nhà Cái:** {cards_str}"
    
    elif hand_type == HandType.BUST:
        template = random.choice(DEALER_MESSAGES["bust"])
        msg = template.format(score=score)
        return f"{msg}\n🤖 **Nhà Cái:** {cards_str} ({score})"
    
    else:  # NORMAL, XI_BAN, NGU_LINH (treated as normal stand for dealer msg purpose)
        template = random.choice(DEALER_MESSAGES["stand"])
        msg = template.format(score=score)
        return f"{msg}\n🤖 **Nhà Cái:** {cards_str} ({score})"

def _format_player_result(result_dict):
    """Format single player result with random message."""
    user = f"<@{result_dict['user_id']}>"
    score = result_dict['score']
    # FIX: Convert List[Card] to emoji strings
    cards = " ".join([c.to_emoji() for c in result_dict['hand']])
    outcome = result_dict['result']
    net = result_dict['net_profit']
    
    # Hand Type Label (for Blackjack/Ngu Linh visualization)
    hand_type_label = ""
    # We don't have hand_type enum in result_dict usually, just strings like 'instant_win'
    # But checking cards length/score can infer special hands if needed
    
    payout = result_dict.get('payout', 0)
    
    # Select message pool
    if outcome == "win" or outcome == "instant_win":
        template = random.choice(PLAYER_WIN_MESSAGES)
        # REQUEST: Show TOTAL PAYOUT (Stake + Profit) -> "Lời 200" style (as per user mindset)
        payout_str = f"**+{payout:,} Hạt**" if payout > 0 else ""
        msg = template.format(user=user, payout_display=payout_str, score=score)
        
    elif outcome == "lose":
        template = random.choice(PLAYER_LOSE_MESSAGES)
        msg = template.format(user=user, score=score, bet=abs(net))
        
    else:  # push
        template = random.choice(PLAYER_PUSH_MESSAGES)
        msg = template.format(user=user, score=score)
    
    # Add cards display
    return f"{msg}\n└ 🃏 {cards} ({score})"

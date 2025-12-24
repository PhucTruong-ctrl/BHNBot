"""Helper utilities for Bau Cua game.

Contains functions for building embeds, formatting text, and displaying results.
"""

import discord
from typing import Dict, List, Tuple

from .constants import ANIMALS, MAX_BET_AMOUNT


def create_betting_embed(end_timestamp: int) -> discord.Embed:
    """Create embed for betting phase with Discord auto-updating countdown.
    
    Uses Discord timestamp format `<t:TIMESTAMP:R>` which auto-updates
    client-side without requiring message edits.
    
    Args:
        end_timestamp: Unix timestamp when betting phase ends
        
    Returns:
        Discord embed ready to display
    """
    embed = discord.Embed(
        title="🎰 BẦU CUA TÔM CÁ GÀ NAI 🎰",
        description=f"⏳ **Hết hạn cược:** <t:{end_timestamp}:R>",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💡 Cách chơi",
        value=(
            f"Bấm vào 1 nút để chọn linh vật, nhập số hạt muốn cược (max {MAX_BET_AMOUNT:,})\n"
            "Ví dụ: Cược 100 thì xuất hiện 1 lần = nhận 200 (lời 100) | "
            "2 lần = nhận 300 (lời 200) | 3 lần = nhận 400 (lời 300)"
        ),
        inline=False
    )
    
    return embed


def create_rolling_text(result1: str, result2: str, result3: str) -> str:
    """Create text display for rolling animation frame.
    
    Shows current dice state during animation.
    
    Args:
        result1: First dice result (animal key)
        result2: Second dice result (animal key)
        result3: Third dice result (animal key)
        
    Returns:
        Formatted string with 3 animal emojis
    """
    emoji1 = ANIMALS[result1]["emoji"]
    emoji2 = ANIMALS[result2]["emoji"]
    emoji3 = ANIMALS[result3]["emoji"]
    
    return f"{emoji1} {emoji2} {emoji3}"


def create_partial_result_text(
    result1: str = None,
    result2: str = None,
    result3: str = None,
    rolling_symbol: str = "🎲"
) -> str:
    """Create text for partial results (some dice stopped, others still rolling).
    
    Used for sequential dice stopping animation for suspense.
    
    Args:
        result1: First dice result (None if still rolling)
        result2: Second dice result (None if still rolling)
        result3: Third dice result (None if still rolling)
        rolling_symbol: Symbol to show for dice still rolling
        
    Returns:
        Formatted string with mix of final emojis and rolling symbols
    """
    emoji1 = ANIMALS[result1]["emoji"] if result1 else rolling_symbol
    emoji2 = ANIMALS[result2]["emoji"] if result2 else rolling_symbol
    emoji3 = ANIMALS[result3]["emoji"] if result3 else rolling_symbol
    
    return f"{emoji1} {emoji2} {emoji3}"


def create_result_display(result1: str, result2: str, result3: str) -> str:
    """Create final result display with large emojis.
    
    Args:
        result1: First dice result (animal key)
        result2: Second dice result (animal key)
        result3: Third dice result (animal key)
        
    Returns:
        Formatted string showing final results
    """
    emoji1 = ANIMALS[result1]["emoji"]
    emoji2 = ANIMALS[result2]["emoji"]
    emoji3 = ANIMALS[result3]["emoji"]
    
    return f"{emoji1} {emoji2} {emoji3}"


def create_summary_text(
    result1: str,
    result2: str,
    result3: str,
    bets_data: Dict[int, List[Tuple[str, int]]]
) -> str:
    """Create detailed summary text of results per user.
    
    Shows each player's bets and their winnings/losses.
    
    Args:
        result1: First dice result
        result2: Second dice result
        result3: Third dice result
        bets_data: Dictionary mapping user_id to list of (animal_key, amount) tuples
        
    Returns:
        Formatted multi-line string with summary for each user
    """
    final_result = [result1, result2, result3]
    summary_lines = []
    
    for user_id, bet_list in bets_data.items():
        # Use user ID mention format (no fetch needed, instant)
        user_mention = f"<@{user_id}>"
        
        # Build detailed bet breakdown
        bet_details = []
        total_winnings = 0
        total_loss = 0
        
        for animal_key, bet_amount in bet_list:
            matches = sum(1 for r in final_result if r == animal_key)
            
            # Add animal name and amount to details
            animal_name = ANIMALS[animal_key]['name']
            bet_details.append(f"{animal_name} {bet_amount}")
            
            if matches > 0:
                # Formula: bet_amount * (matches + 1)
                # cược 10 ăn 1 = 10 * 2 = 20 (lời 10)
                # cược 10 ăn 2 = 10 * 3 = 30 (lời 20)
                # cược 10 ăn 3 = 10 * 4 = 40 (lời 30)
                total_winnings += bet_amount * (matches + 1)
            else:
                total_loss += bet_amount
        
        # Build summary for this user
        bet_str = ", ".join(bet_details)
        
        # Build result string with both wins and losses
        result_parts = []
        if total_winnings > 0:
            result_parts.append(f"thắng {total_winnings}")
        if total_loss > 0:
            result_parts.append(f"thua {total_loss}")
        
        result_str = ", ".join(result_parts) if result_parts else "hoà"
        
        summary = f"{user_mention} đã cược {bet_str} 🌱 và {result_str} 🌱"
        summary_lines.append(summary)
    
    return "\n".join(summary_lines)


def calculate_payout(bet_amount: int, matches: int) -> int:
    """Calculate payout for a single bet.
    
    Formula: bet_amount * (matches + 1)
    - 0 matches = 0 payout (lost bet)
    - 1 match = bet_amount * 2
    - 2 matches = bet_amount * 3
    - 3 matches = bet_amount * 4
    
    Args:
        bet_amount: Amount of seeds bet
        matches: Number of times animal appeared in results (0-3)
        
    Returns:
        Total payout amount
    """
    if matches == 0:
        return 0
    return bet_amount * (matches + 1)


def calculate_net_profit(bet_amount: int, matches: int) -> int:
    """Calculate net profit/loss for a bet.
    
    Args:
        bet_amount: Amount of seeds bet
        matches: Number of matches
        
    Returns:
        Net profit (positive) or loss (negative)
        Loss is represented as negative bet_amount
    """
    payout = calculate_payout(bet_amount, matches)
    return payout - bet_amount

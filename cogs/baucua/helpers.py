"""Helper utilities for Bau Cua game.

Contains functions for building embeds, formatting text, and displaying results.
"""

import discord
from typing import Dict, List, Tuple

from .constants import ANIMALS, MAX_BET_AMOUNT


async def create_betting_embed(user: discord.User, end_timestamp: int) -> discord.Embed:
    """Create embed for betting phase with Discord auto-updating countdown.
    
    Applies VIP styling if user has active subscription.
    
    Uses Discord timestamp format `<t:TIMESTAMP:R>` which auto-updates
    client-side without requiring message edits.
    
    Args:
        user: Discord user (for VIP styling)
        end_timestamp: Unix timestamp when betting phase ends
        
    Returns:
        Discord embed ready to display
    """
    from core.services.vip_service import VIPEngine
    
    title = "🎰 BẦU CUA TÔM CÁ GÀ NAI"  # Keep emoji, factory adds tier prefix
    description = f"⏳ **Hết hạn cược:** <t:{end_timestamp}:R>"
    
    embed = await VIPEngine.create_vip_embed(user, title, description)
    
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
    bets_data: Dict[int, List[Tuple[str, int]]],
    vip_data: Dict[int, int] = None
) -> str:
    """Create detailed summary text of results per user.
    
    Shows each player's bets and their winnings/losses.
    VIPs get special result messages with Instant Cashback info.
    
    Args:
        result1: First dice result
        result2: Second dice result
        result3: Third dice result
        bets_data: Dictionary mapping user_id to list of (animal_key, amount) tuples
        vip_data: Dict mapping user_id to tier (e.g. {123: 1, 456: 3})
        
    Returns:
        Formatted multi-line string with summary for each user
    """
    final_result = [result1, result2, result3]
    summary_lines = []
    
    if vip_data is None:
        vip_data = {}
    
    # Gen Z templates (Regular)
    import random
    
    WIN_MSGS = [
        "{user} đã hốt bạc **{amount}** 🌱. Flex nhẹ cái nhân phẩm!",
        "{user} làm giàu không khó, ẵm trọn **{amount}** 🌱. Mời cả làng đi ăn đi!",
        "Cuộc đời nở hoa! {user} thắng **{amount}** 🌱. Đỉnh nóc, kịch trần, bay phấp phới!",
        "Ao chình server! {user} bú đẫm **{amount}** 🌱. Chia tiền cho bot với!",
        "Tài năng hay may mắn? {user} lụm **{amount}** 🌱. Keo lỳ quá bạn ơi!",
        "{user} nhân phẩm bùng nổ, húp trọn **{amount}** 🌱. Đại gia đây rồi!",
        "Chấn động địa cầu! {user} thắng lớn **{amount}** 🌱. SOS, cứu ví nhà cái!",
        "{user} nay được tổ độ, thắng **{amount}** 🌱. Đừng ai cản bạn tôi!",
        "10 điểm không có nhưng! {user} đem về **{amount}** 🌱.",
        "Mê chữ ê kéo dài! {user} thắng **{amount}** 🌱. Slay quá đi!"
    ]
    
    LOSS_MSGS = [
        "{user} xa bờ rồi, bay màu **{amount}** 🌱. Một phút bốc đồng, cả đời bốc cám.",
        "Đen thôi đỏ quên đi. {user} cúng cho nhà cái **{amount}** 🌱. Hẹn kiếp sau gỡ lại.",
        "{user} lỗ **{amount}** 🌱. Còn cái nịt, còn đúng cái nịt.",
        "{user} đã tạch **{amount}** 🌱. Xu cà na, đi nhảy cầu thôi.",
        "Chia buồn cùng {user}, bay mất **{amount}** 🌱. Tam tai chưa qua, thái tuế đã tới.",
        "{user} âm **{amount}** 🌱. Ra đê mà ở chứ còn gì nữa.",
        "Cuộc sống bế tắc, {user} thua **{amount}** 🌱. Trầm cảm part n.",
        "{user} đã hiến máu nhân đạo **{amount}** 🌱. Bot cảm ơn nhà tài trợ.",
        "Khóc tiếng mán! {user} mất **{amount}** 🌱. Thôi đừng buồn, em ơi đừng khóc...",
        "{user} toang rồi ông giáo ạ, âm **{amount}** 🌱."
    ]
    
    NEUTRAL_MSGS = [
        "{user} hòa vốn. Đời không như là mơ nhưng cũng không như là thơ.",
        "{user} bảo toàn tính mạng. Không thắng không thua, coi như tập thể dục.",
        "{user} vốn liếng y nguyên. Vui vẻ không quạu nha.",
        "{user} huề tiền. Chơi cho vui, tiền bạc phù du.",
        "{user} về bờ an toàn. Hú hồn chim én!"
    ]

    # VIP Messages (Instant Cashback)
    # Tier Names Mapping
    TIER_NAMES = {
        1: "🥈 [BẠC]",
        2: "🥇 [VÀNG]",
        3: "💎 [KIM CƯƠNG]"
    }
    
    VIP_WIN_MSGS = [
        "{tier} {user} đẳng cấp chiến thắng **{amount}** 🌱. Phong độ là nhất thời, VIP là mãi mãi!",
        "{tier} {user} hốt gọn **{amount}** 🌱. Đại gia đi shopping thôi!",
        "{tier} {user} bỏ túi **{amount}** 🌱. Tiền vào như nước sông Đà!",
        "{tier} Chúc mừng {user} thắng lớn **{amount}** 🌱. Thần thái sang chảnh!",
        "{tier} {user} nâng tài sản thêm **{amount}** 🌱. Quá dữ dằn!"
    ]
    
    # Template expects {amount} (loss) and {cashback} (refund)
    VIP_LOSS_MSGS = [
        "{tier} {user} rơi mất **{amount}** 🌱. Nhưng được hoàn **{cashback}** 🌱! 💸",
        "{tier} {user} hơi đen khi mất **{amount}** 🌱. May là VIP, nhận lại **{cashback}** 🌱.",
        "{tier} {user} thua **{amount}** 🌱. Ting ting! +**{cashback}** 🌱 tiền hoàn trả.",
        "{tier} {user} lỗ **{amount}** 🌱. Đừng lo, bot đã back lại **{cashback}** 🌱.",
        "{tier} {user} mất **{amount}** 🌱. Đặc quyền VIP: Hồi máu **{cashback}** 🌱 ngay lập tức!"
    ]
    
    VIP_NEUTRAL_MSGS = [
        "{tier} {user} bảo toàn vốn. Thong dong tự tại.",
        "{tier} {user} hòa tiền. Phong thái điềm tĩnh.",
        "{tier} {user} không thắng không thua. Vẫn cứ là Ok."
    ]

    for user_id, bet_list in bets_data.items():
        user_mention = f"<@{user_id}>"
        tier = vip_data.get(user_id, 0)
        is_vip = tier > 0
        tier_str = TIER_NAMES.get(tier, "")
        
        # Calculate NET profit/loss
        total_payout = 0
        total_bet = 0
        
        for animal_key, bet_amount in bet_list:
            total_bet += bet_amount
            matches = sum(1 for r in final_result if r == animal_key)
            if matches > 0:
                total_payout += bet_amount * (matches + 1)
        
        net_profit = total_payout - total_bet
        
        if net_profit > 0:
            if is_vip:
                msg_template = random.choice(VIP_WIN_MSGS)
                summary = msg_template.format(user=user_mention, amount=f"{net_profit:,}", tier=tier_str)
            else:
                msg_template = random.choice(WIN_MSGS)
                summary = msg_template.format(user=user_mention, amount=f"{net_profit:,}")
                
        elif net_profit < 0:
            loss = abs(net_profit)
            
            if is_vip:
                # Calculate Cashback for display
                rate = 0.02
                if tier == 2: rate = 0.03
                elif tier == 3: rate = 0.05
                
                cashback = int(loss * rate)
                summary = random.choice(VIP_LOSS_MSGS).format(
                    user=user_mention, 
                    amount=f"{loss:,}", 
                    cashback=f"{cashback:,}",
                    tier=tier_str
                )
            else:
                summary = random.choice(LOSS_MSGS).format(
                    user=user_mention, 
                    amount=f"{loss:,}"
                )
        else:
            if is_vip:
                msg_template = random.choice(VIP_NEUTRAL_MSGS)
                summary = msg_template.format(user=user_mention, tier=tier_str)
            else:
                msg_template = random.choice(NEUTRAL_MSGS)
                summary = msg_template.format(user=user_mention)
            
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


async def unified_send(ctx_or_interaction, content: str = None, embed: discord.Embed = None, view: discord.ui.View = None, ephemeral: bool = False):
    """Unified message sender for Context and Interaction.
    
    Arg:
        ctx_or_interaction: commands.Context or discord.Interaction
        content: Text content
        embed: Discord Embed
        view: Discord View
        ephemeral: Only for interaction (hidden message)
        
    Returns:
        The sent Message object
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        interaction = ctx_or_interaction
        if interaction.response.is_done():
            if view is None:
                return await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            return await interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)
        else:
            if view is None:
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=ephemeral)
            return await interaction.original_response()
    else:
        ctx = ctx_or_interaction
        if view is None:
            return await ctx.send(content=content, embed=embed)
        return await ctx.send(content=content, embed=embed, view=view)


def parse_quick_bet_args(args: tuple) -> Tuple[bool, int, str, str]:
    """Parse arguments for Quick Bet command.
    
    Supported formats:
    - -q 50k bau
    - 50000 cua -q (flags anywhere)
    - mode:quick amount:50k choice:tom (handled by slash command parser separately, this is for prefix/raw args)
    
    Args:
        args: Tuple of string arguments
        
    Returns:
        Tuple (success, amount, animal_key, error_message)
    """
    import re
    
    if not args:
        return False, 0, "", "Thiếu tham số! Dùng: `!bc -q <tiền> <con_vật>`"
    
    # Flatten args to string list
    args_list = [str(a).lower() for a in args]
    
    # Check for quick flag (optional if logic calls this specifically for quick bet mode)
    # But strictly, we expect arguments like ["50k", "bau"] here if flag was stripped, or with flag.
    # We'll just look for amount and choice.
    
    amount = 0
    choice = ""
    
    # Animal Aliases
    ALIAS_MAP = {
        'bau': 'bau', 'b': 'bau', 'bầu': 'bau',
        'cua': 'cua', 'c': 'cua',
        'tom': 'tom', 't': 'tom', 'tôm': 'tom',
        'ca': 'ca', 'á': 'ca', 'cá': 'ca', 'fish': 'ca',
        'ga': 'ga', 'g': 'ga', 'gà': 'ga', 'chicken': 'ga',
        'nai': 'nai', 'n': 'nai', 'deer': 'nai'
    }
    
    for arg in args_list:
        if arg in ['-q', '--quick', 'quick']:
            continue
            
        # Check if amount (digits + k/m)
        money_match = re.match(r'^(\d+)([km])?$', arg)
        if money_match:
            try:
                val = int(money_match.group(1))
                suffix = money_match.group(2)
                if suffix == 'k': val *= 1000
                if suffix == 'm': val *= 1000000
                amount = val
                continue
            except Exception:
                pass
        
        # Check if choice
        if arg in ALIAS_MAP:
            choice = ALIAS_MAP[arg]
            continue
            
    if amount <= 0:
        return False, 0, "", "Số tiền không hợp lệ! Ví dụ: 50k, 10000"
        
    if not choice:
        return False, 0, "", "Chưa chọn linh vật! (bau, cua, tom, ca, ga, nai)"
        
    return True, amount, choice, ""


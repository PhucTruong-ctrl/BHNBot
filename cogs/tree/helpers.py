"""Helper functions for tree system display and formatting.

Contains pure functions for creating embeds, progress bars, and text formatting.
"""

import discord
from typing import List, Tuple
from core.logger import setup_logger

from .constants import (
    TREE_IMAGES,
    TREE_NAMES,
    TREE_DESCRIPTIONS,
    PROGRESS_BAR_LENGTH
)
from .models import TreeData, ContributorData
from configs.item_constants import ItemKeys

logger = setup_logger("TreeHelpers", "logs/cogs/tree.log")


def create_progress_bar(progress: int, requirement: int, length: int = PROGRESS_BAR_LENGTH) -> str:
    """Generate visual progress bar.
    
    PERFORMANCE FIX #9: Uses list join for better performance.
    
    Args:
        progress: Current progress value
        requirement: Target value for completion
        length: Length of bar in characters
        
    Returns:
        String with filled and empty squares
    """
    if requirement == 0:
        filled = length
    else:
        percent = min(100, int((progress / requirement) * 100))
        filled = int(percent * length / 100)
    
    # Use list + join (faster than string concatenation)
    bar_parts = ["🟩"] * filled + ["⬜"] * (length - filled)
    return "".join(bar_parts)


async def create_tree_embed(tree_data: TreeData) -> discord.Embed:
    """Create main tree display embed.
    
    Args:
        tree_data: TreeData instance with current state
        
    Returns:
        Discord embed showing tree status
    """
    level_reqs = tree_data.get_level_requirements()
    req = level_reqs.get(tree_data.current_level + 1, level_reqs[6])
    
    # Calculate progress
    if tree_data.current_level >= 6:
        bar = "🟩" * PROGRESS_BAR_LENGTH
        footer_text = f"🍎 Cây đã trĩu quả! Chờ thu hoạch • Tổng: {tree_data.total_contributed} Hạt"
        percent = 100
    else:
        percent = tree_data.calculate_progress_percent()
        bar = create_progress_bar(tree_data.current_progress, req)
        footer_text = (
            f"Mùa {tree_data.season} • Level {tree_data.current_level}/6 • "
            f"{tree_data.current_progress}/{req} Hạt • Tổng: {tree_data.total_contributed}"
        )
    
    embed = discord.Embed(
        title="Cây Bên Hiên Nhà",
        description=TREE_DESCRIPTIONS.get(tree_data.current_level, "..."),
        color=discord.Color.green()
    )
    embed.set_image(url=TREE_IMAGES.get(tree_data.current_level, TREE_IMAGES[1]))
    embed.add_field(
        name=f"Trạng thái: {TREE_NAMES.get(tree_data.current_level, '???')}",
        value=f"```\n{bar}\n```",
        inline=False
    )
    embed.add_field(name="Tiến độ", value=f"**{percent}%**", inline=True)
    embed.add_field(name="Level", value=f"**{tree_data.current_level}/6**", inline=True)
    embed.add_field(
        name="💡 Cách Góp",
        value="Bấm nút dưới đây để góp hạt cho cây!",
        inline=False
    )
    embed.set_footer(text=footer_text)
    
    return embed


def create_contribution_success_embed(
    user: discord.User,
    amount: int,
    new_progress: int,
    requirement: int,
    leveled_up: bool = False,
    new_level: int = None,
    item_name: str = "Hạt",
    quantity: int = None,
    action_title: str = "Góp Hạt Cho Cây!"
) -> discord.Embed:
    """Create success embed after contribution.
    
    Args:
        user: Discord user who contributed
        amount: Total value contributed (EXP)
        new_progress: New progress value
        requirement: Requirement for next level
        leveled_up: Whether tree leveled up
        new_level: New level if leveled up
        item_name: Name of item used (e.g. "Phân Bón", "Hạt")
        quantity: Quantity of items used (e.g. 3)
        action_title: Title of the embed action
        
    Returns:
        Discord embed with success message
    """
    # Defaults
    if quantity is None:
        quantity = amount
        
    # Calculate value per item for breakdown
    if quantity > 0:
        value_per_item = amount // quantity
    else:
        value_per_item = 0

    embed = discord.Embed(
        description=f"**{user.name}** đã xài **{quantity}** {item_name}",
        color=discord.Color.green()
    )
    
    # Title with Icon (mapped from action_title if needed, or just use string)
    if "Phân" in item_name:
        icon = "🌾"
        title = "Bón Phân Cho Cây!"
    else:
        icon = "🌱"
        title = "Góp Hạt Cho Cây!"
        
    embed.set_author(name=f"{icon} {title}")
    
    # Field 1: Total EXP
    embed.add_field(
        name="⚡ Tổng EXP",
        value=f"**{amount} EXP** → +{amount} điểm cho cây",
        inline=False
    )
    
    # Field 2: Detail
    embed.add_field(
        name="📋 Chi tiết",
        value=f"{quantity} × {value_per_item}",
        inline=False
    )
    
    # Field 3: Progress
    percent = int((new_progress / requirement) * 100) if requirement > 0 else 0
    embed.add_field(
        name="📊 Tiến độ",
        value=f"**{percent}%** ({new_progress}/{requirement})",
        inline=False
    )
    
    if leveled_up and new_level:
        embed.add_field(
            name="🎉 CÂY ĐÃ LÊN CẤP!",
            value=f"**{TREE_NAMES.get(new_level, 'Cây Thần')}** - Cấp {new_level}/6",
            inline=False
        )
        embed.color = discord.Color.gold()
    
    return embed


async def create_harvest_announcement_embed(
    season: int,
    top_contributors: List[Tuple[int, int]],
    bot
) -> discord.Embed:
    """Create big harvest event announcement embed.
    
    Args:
        season: Season number that just ended
        top_contributors: List of (user_id, exp) tuples
        bot: Discord bot instance for fetching users
        
    Returns:
        Discord embed for harvest announcement
    """
    from .constants import HARVEST_REWARDS
    
    embed = discord.Embed(
        title=f"🎉 THU HOẠCH THÀNH CÔNG - MÙA {season}! 🎉",
        description=(
            "Cây Đại Thụ đã hiến dâng những trái ngọt nhất cho Bên Hiên Nhà.\n\n"
            "Phước lành rực rỡ nung nấu trên toàn server!"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url=TREE_IMAGES[6])
    
    # Field 1: Global Buff
    embed.add_field(
        name="✨ TOÀN SERVER BỰC LỪA (24 Giờ)",
        value="**X2 Hạt** khi chat/voice\n**X2 Hạt** cho mọi activity",
        inline=False
    )
    
    # Field 2: Contributors Reward
    embed.add_field(
        name="🎁 PHẦN THƯỞNG CHO NGƯỜI ĐÓNG GÓP",
        value=(
            f"• **Top 1**: {HARVEST_REWARDS['top1']:,} Hạt + Quả Ngọt Mùa {season}\n"
            f"• **Top 2**: {HARVEST_REWARDS['top2']:,} Hạt + Quả Ngọt Mùa {season}\n"
            f"• **Top 3**: {HARVEST_REWARDS['top3']:,} Hạt + Quả Ngọt Mùa {season}\n"
            f"• **Những người khác**: {HARVEST_REWARDS['others']:,} Hạt + Quả Ngọt Mùa {season}"
        ),
        inline=False
    )
    
    # Field 3: Top Contributors
    if top_contributors:
        top_text = ""
        for idx, (uid, exp) in enumerate(top_contributors[:3], 1):
            try:
                user = bot.get_user(uid)
                if not user:
                    user = await bot.fetch_user(uid)
                top_text += f"{idx}. **{user.name}** - {exp} Kinh Nghiệm\n"
            except Exception:
                top_text += f"{idx}. **User #{uid}** - {exp} Kinh Nghiệm\n"
        
        embed.add_field(
            name="🏆 Top 3 Người Đóng Góp Nhiều Nhất",
            value=top_text,
            inline=False
        )
    
    # Field 4: Season Reset
    embed.add_field(
        name="MÙA MỚI BẮT ĐẦU",
        value=(
            f"Cây đã tái sinh Level 1\n"
            f"Mùa {season + 1} chính thức khai mạc!\n"
            f"Hãy chuẩn bị cho cuộc đua góp hạt mới"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"Cảm ơn tất cả! 🙏 | Mùa tiếp theo sẽ còn huy hoàng hơn!")
    
    return embed


async def format_contributor_list(
    contributors: List[ContributorData],
    tree_manager,  # Changed from bot to tree_manager
    show_exp: bool = False
) -> str:
    """Format list of contributors for display.
    
    PERFORMANCE FIX #4: Uses tree_manager.get_user_cached() to avoid N+1 queries.
    
    Args:
        contributors: List of ContributorData instances
        tree_manager: TreeManager instance (for cached user fetching)
        show_exp: Whether to show exp or amount
        
    Returns:
        Formatted string with numbered list
    """
    if not contributors:
        return "Chưa có ai đóng góp"
    
    result = ""
    for idx, contributor in enumerate(contributors, 1):
        user = await tree_manager.get_user_cached(contributor.user_id)
        username = user.name if user else f"User #{contributor.user_id}"
        
        value = contributor.contribution_exp if show_exp else contributor.amount
        result += f"{idx}. **{username}** - {value} {'Kinh Nghiệm' if show_exp else 'Hạt'}\n"
    
    return result


async def format_all_time_contributors(
    contributors: List[Tuple[int, int]],
    tree_manager  # Changed from bot to tree_manager
) -> str:
    """Format all-time contributors for display.
    
    PERFORMANCE FIX #4: Uses tree_manager.get_user_cached() to avoid N+1 queries.
    
    Args:
        contributors: List of (user_id, total_exp) tuples
        tree_manager: TreeManager instance (for cached user fetching)
        
    Returns:
        Formatted string with numbered list
    """
    if not contributors:
        return "Chưa có ai đóng góp"
    
    result = ""
    for idx, (user_id, total_exp) in enumerate(contributors, 1):
        user = await tree_manager.get_user_cached(user_id)
        username = user.name if user else f"User #{user_id}"
        
        result += f"{idx}. **{username}** - {total_exp} Kinh Nghiệm\n"
    
    return result


def get_contribution_exp(contribution_type: str, amount: int) -> int:
    """Calculate experience points for contribution.
    
    Args:
        contribution_type: Type of contribution ('seeds' or 'phan_bon')
        amount: Amount contributed
        
    Returns:
        Experience points earned
    """
    if contribution_type == ItemKeys.PHAN_BON:
        # Phan bon: amount is already the exp (50-100)
        return amount
    else:
        # Hạt: 1 seed = 1 exp
        return amount

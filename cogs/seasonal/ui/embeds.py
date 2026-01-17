from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ..core.event_types import EventConfig


def create_event_info_embed(
    event: EventConfig,
    user_currency: int,
    community_progress: int,
    community_goal: int,
) -> discord.Embed:
    percent = (community_progress / community_goal * 100) if community_goal > 0 else 0
    progress_bar = _create_progress_bar(percent)

    embed = discord.Embed(
        title=f"🎉 {event.name.upper()}",
        description=event.description or f"Sự kiện **{event.name}** đang diễn ra!",
        color=event.color,
    )

    if event.banner_image:
        embed.set_image(url=event.banner_image)
    if event.thumbnail:
        embed.set_thumbnail(url=event.thumbnail)

    embed.add_field(
        name=f"💰 {event.currency_name} của bạn",
        value=f"**{user_currency:,}** {event.currency_emoji}",
        inline=True,
    )

    embed.add_field(
        name="📅 Thời gian",
        value=f"{event.registry.start_date.strftime('%d/%m')} - {event.registry.end_date.strftime('%d/%m/%Y')}",
        inline=True,
    )

    goal_desc = event.community_goal_description.format(
        target=f"{community_goal:,}",
        currency=event.currency_emoji,
    )
    embed.add_field(
        name="🎯 Mục tiêu cộng đồng",
        value=f"{goal_desc}\n{community_progress:,} / {community_goal:,} ({percent:.1f}%)\n{progress_bar}",
        inline=False,
    )

    if event.guide:
        embed.add_field(
            name="📖 Hướng dẫn",
            value=event.guide,
            inline=False,
        )

    embed.set_footer(text=f"Kết thúc: {event.registry.end_date.strftime('%d/%m/%Y %H:%M')}")

    return embed


def create_community_goal_embed(
    event: EventConfig,
    progress: int,
    goal: int,
    milestones_reached: list[int],
) -> discord.Embed:
    percent = (progress / goal * 100) if goal > 0 else 0
    progress_bar = _create_progress_bar(percent, width=30)

    embed = discord.Embed(
        title=f"🎯 MỤC TIÊU CỘNG ĐỒNG - {event.name.upper()}",
        color=event.color,
    )

    if event.thumbnail:
        embed.set_thumbnail(url=event.thumbnail)

    goal_desc = event.community_goal_description.format(
        target=f"{goal:,}",
        currency=event.currency_emoji,
    )
    embed.add_field(
        name="📋 Mục tiêu",
        value=goal_desc,
        inline=False,
    )

    embed.add_field(
        name="📊 Tiến độ",
        value=f"**{progress:,}** / {goal:,} ({percent:.1f}%)\n{progress_bar}",
        inline=False,
    )

    milestone_lines = []
    for milestone in event.milestones:
        p = milestone.percent
        if p in milestones_reached:
            status = "✅"
        elif percent >= p:
            status = "✅"
        else:
            status = "⏳"

        reward_text = _get_milestone_reward_text(milestone, event.currency_emoji)
        milestone_lines.append(f"{status} **{p}%** - {reward_text}")

    if milestone_lines:
        embed.add_field(
            name="🏆 Các mốc thưởng",
            value="\n".join(milestone_lines),
            inline=False,
        )

    return embed


def create_leaderboard_embed(
    event: EventConfig,
    leaderboard: list[dict],
    bot: discord.Client,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🏆 BẢNG XẾP HẠNG - {event.name.upper()}",
        color=event.color,
    )

    if event.thumbnail:
        embed.set_thumbnail(url=event.thumbnail)

    if not leaderboard:
        embed.description = "Chưa có ai tham gia sự kiện!"
        return embed

    lines = []
    medals = ["🥇", "🥈", "🥉"]

    for i, entry in enumerate(leaderboard[:10]):
        user_id = entry["user_id"]
        currency = entry["currency"]

        medal = medals[i] if i < 3 else f"`{i + 1}.`"
        user = bot.get_user(user_id)
        name = user.display_name if user else f"User {user_id}"

        lines.append(f"{medal} **{name}** - {currency:,} {event.currency_emoji}")

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"Top 10 người chơi có nhiều {event.currency_name} nhất")
    return embed


def create_event_start_embed(
    event: EventConfig,
    progress: int = 0,
    goal: int | None = None,
    milestones_reached: list[int] | None = None,
) -> discord.Embed:
    if goal is None:
        goal = event.community_goal_target
    if milestones_reached is None:
        milestones_reached = []

    percent = (progress / goal * 100) if goal > 0 else 0
    progress_bar = _create_progress_bar(percent)

    embed = discord.Embed(
        title=f"🎉 {event.name.upper()} BẮT ĐẦU!",
        description=event.description or f"Sự kiện **{event.name}** đã chính thức bắt đầu!",
        color=event.color,
    )

    if event.banner_image:
        embed.set_image(url=event.banner_image)
    if event.thumbnail:
        embed.set_thumbnail(url=event.thumbnail)

    embed.add_field(
        name=f"💰 Tiền tệ sự kiện",
        value=f"{event.currency_emoji} **{event.currency_name}**",
        inline=True,
    )

    embed.add_field(
        name="📅 Thời gian",
        value=f"{event.registry.start_date.strftime('%d/%m')} - {event.registry.end_date.strftime('%d/%m/%Y')}",
        inline=True,
    )

    goal_desc = event.community_goal_description.format(
        target=f"{goal:,}",
        currency=event.currency_emoji,
    )
    embed.add_field(
        name="🎯 Mục tiêu cộng đồng",
        value=f"{goal_desc}\n**{progress:,}** / {goal:,} ({percent:.1f}%)\n{progress_bar}",
        inline=False,
    )

    if event.milestones:
        milestone_lines = []
        for m in event.milestones[:4]:
            if m.percent in milestones_reached or percent >= m.percent:
                status = "✅"
            else:
                status = "⏳"
            reward = _get_milestone_reward_text(m, event.currency_emoji)
            milestone_lines.append(f"{status} **{m.percent}%**: {reward}")
        embed.add_field(
            name="🏆 Các mốc thưởng",
            value="\n".join(milestone_lines),
            inline=False,
        )

    if event.fish:
        fish_list = " ".join(f.emoji for f in event.fish[:6])
        embed.add_field(
            name=f"🐟 Cá sự kiện ({len(event.fish)} loại)",
            value=fish_list,
            inline=True,
        )

    if event.registry.minigames:
        games = [m.name for m in event.registry.minigames]
        embed.add_field(
            name="🎮 Minigames",
            value="\n".join(games),
            inline=True,
        )

    if event.guide:
        embed.add_field(
            name="📖 Hướng dẫn chơi",
            value=event.guide,
            inline=False,
        )

    embed.add_field(
        name="💻 Lệnh sử dụng",
        value=(
            "`/sukien` - Xem thông tin sự kiện\n"
            "`/sukien cuahang` - Cửa hàng sự kiện\n"
            "`/nhiemvu` - Nhiệm vụ (gồm cả nhiệm vụ sự kiện)\n"
            "`/sukien xephang` - Bảng xếp hạng"
        ),
        inline=False,
    )

    embed.set_footer(text=f"Sự kiện kết thúc: {event.registry.end_date.strftime('%d/%m/%Y')}")

    return embed


def create_event_end_embed(
    event: EventConfig,
    final_progress: int,
    goal: int,
    participant_count: int,
) -> discord.Embed:
    percent = (final_progress / goal * 100) if goal > 0 else 0
    completed = percent >= 100

    embed = discord.Embed(
        title=f"{'🎉' if completed else '⏰'} {event.name.upper()} KẾT THÚC!",
        color=event.color,
    )

    if event.banner_image:
        embed.set_image(url=event.banner_image)
    if event.thumbnail:
        embed.set_thumbnail(url=event.thumbnail)

    if completed:
        embed.description = "🎊 **HOÀN THÀNH MỤC TIÊU!** Cảm ơn tất cả đã tham gia!"
    else:
        embed.description = f"Đạt **{percent:.1f}%** mục tiêu. Cảm ơn tất cả đã tham gia! Hẹn gặp lại ở sự kiện sau!"

    embed.add_field(
        name="📊 Kết quả cuối cùng",
        value=f"**{final_progress:,}** / {goal:,} ({percent:.1f}%)",
        inline=True,
    )

    embed.add_field(
        name="👥 Tổng người tham gia",
        value=f"**{participant_count:,}** thành viên",
        inline=True,
    )

    return embed


def _create_progress_bar(percent: float, width: int = 25) -> str:
    filled = int(width * min(percent, 100) / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _get_milestone_reward_text(milestone, currency_emoji: str = "") -> str:
    if milestone.reward_type == "seeds":
        return f"+{milestone.amount} hạt giống"
    elif milestone.reward_type == "title":
        return f'Danh hiệu "{milestone.title_name}"'
    elif milestone.reward_type == "buff":
        buff_names = {
            "fishing_x2": "x2 cá",
            "seeds_x2": "x2 hạt giống",
            "currency_x2": f"x2 {currency_emoji}",
        }
        buff_text = buff_names.get(milestone.buff_type, milestone.buff_type)
        return f"{buff_text} trong {milestone.duration_hours}h"
    elif milestone.reward_type == "role":
        return f"Role đặc biệt: {milestone.role_name}"
    return "Phần thưởng đặc biệt"

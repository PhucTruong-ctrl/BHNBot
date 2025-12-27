"""Embed Builders for Xi Dach."""

import discord
import time
from typing import Optional

from ..services.hand_service import (
    HandType,
    get_hand_description,
    format_hand
)
from ..core.table import Table, TableStatus
from ..core.player import Player, PlayerStatus

def create_solo_game_embed(table: Table, player: Player, hide_dealer: bool = True) -> discord.Embed:
    """Create embed for solo game display."""
    embed = discord.Embed(
        title="🎰 XÌ DÁCH - Chơi Đơn",
        color=discord.Color.gold()
    )

    # Dealer's hand
    dealer_display = format_hand(table.dealer_hand, hide_first=hide_dealer)
    if hide_dealer:
        dealer_value = "?"
    else:
        dealer_value = str(table.dealer_value)
        if table.dealer_type != HandType.NORMAL:
            dealer_value += f" {get_hand_description(table.dealer_type)}"
    
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{dealer_display}\n📊 Điểm: **{dealer_value}**",
        inline=False
    )

    # Player's hand
    player_display = format_hand(player.hand)
    player_value = str(player.hand_value)
    if player.hand_type != HandType.NORMAL:
        player_value += f" {get_hand_description(player.hand_type)}"
    
    embed.add_field(
        name=f"🎴 {player.username}",
        value=f"{player_display}\n📊 Điểm: **{player_value}**\n💰 Cược: **{player.bet:,}** hạt",
        inline=False
    )

    # Status
    if player.status == PlayerStatus.PLAYING:
        embed.set_footer(text="💡 Chọn Rút thêm bài, Dằn để dừng, hoặc Gấp Đôi tiền cược")
    elif player.status == PlayerStatus.BUST:
        embed.set_footer(text="💥 Bạn đã quá 21 điểm!")
        embed.color = discord.Color.red()
    elif player.status == PlayerStatus.BLACKJACK:
        embed.set_footer(text="🎉 Bạn có Xì Dách/Xì Bàn!")
        embed.color = discord.Color.green()

    return embed


def create_result_embed(
    table: Table,
    player: Player,
    result: str,
    payout: int
) -> discord.Embed:
    """Create embed for game result."""
    if result == "win":
        title = "🎉 THẮNG!"
        color = discord.Color.green()
        description = f"Bạn thắng **{payout:,}** hạt!"
    elif result == "lose":
        title = "😢 THUA!"
        color = discord.Color.red()
        description = f"Bạn thua **{player.bet:,}** hạt!"
    else:
        title = "🤝 HÒA!"
        color = discord.Color.blue()
        description = "Bạn được hoàn lại tiền cược!"

    embed = discord.Embed(title=title, description=description, color=color)

    # Show final hands
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{format_hand(table.dealer_hand)}\n📊 Điểm: **{table.dealer_value}** {get_hand_description(table.dealer_type)}",
        inline=True
    )
    embed.add_field(
        name=f"🎴 {player.username}",
        value=f"{format_hand(player.hand)}\n📊 Điểm: **{player.hand_value}** {get_hand_description(player.hand_type)}",
        inline=True
    )

    return embed


def create_lobby_embed(table: Table, time_remaining: Optional[int] = None) -> discord.Embed:
    """Create embed for multiplayer lobby."""
    embed = discord.Embed(
        title="🎰 XÌ DÁCH",
        description="**Sòng nhiều người**",
        color=discord.Color.green()
    )
    
    if time_remaining is not None and time_remaining > 0:
        end_time = int(time.time() + time_remaining)
        embed.add_field(name="⏳ Thời gian", value=f"<t:{end_time}:R>", inline=True)
    else:
        embed.add_field(name="⏳ Thời gian", value="**Đã hết thời gian tham gia**", inline=True)

    # Count stats
    joined_count = sum(1 for p in table.players.values() if p.status == PlayerStatus.WAITING or p.is_ready)
    ready_count = sum(1 for p in table.players.values() if p.is_ready)
    total_bet = sum(p.bet for p in table.players.values())

    embed.add_field(
        name="📊 Thống kê",
        value=f"Tham gia: **{joined_count}** • Sẵn sàng: **{ready_count}** • Tổng cược: **{total_bet:,}**",
        inline=False
    )

    # List players
    players_list = []
    for uid, player in table.players.items():
        if player.is_ready:
            status = "✅"
        elif player.status == PlayerStatus.WAITING:
            status = "⏳"
        else:
            status = "👀"
        
        bet_display = f"{player.bet:,}" if player.bet > 0 else "—"
        players_list.append(f"{status} <@{uid}> • **{bet_display}**")

    if players_list:
        embed.add_field(
            name="👥 Người chơi",
            value="\n".join(players_list),
            inline=False
        )
    else:
        embed.add_field(
            name="👥 Người chơi",
            value="*Chờ người chơi...*",
            inline=False
        )

    embed.set_footer(text="Tham Gia → Đặt cược → Sẵn Sàng")
    return embed


def create_multi_game_embed(table: Table) -> discord.Embed:
    """Create embed for multiplayer game."""
    embed = discord.Embed(
        title="🎰 XÌ DÁCH - Ván Đấu",
        color=discord.Color.gold()
    )

    # Dealer's hand
    hide_dealer = table.status != TableStatus.DEALER_TURN and table.status != TableStatus.FINISHED
    dealer_display = format_hand(table.dealer_hand, hide_first=hide_dealer)
    dealer_value = "?" if hide_dealer else str(table.dealer_value)
    
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{dealer_display}\n📊 Điểm: **{dealer_value}**",
        inline=False
    )

    # All players' hands
    for uid, player in table.players.items():
        if player.bet <= 0:
            continue

        status_emoji = {
            PlayerStatus.PLAYING: "🎮",
            PlayerStatus.WAITING: "⏳",
            PlayerStatus.STAND: "✋",
            PlayerStatus.BUST: "💥",
            PlayerStatus.BLACKJACK: "🎰",
        }.get(player.status, "👤")

        player_display = format_hand(player.hand)
        hand_desc = get_hand_description(player.hand_type) if player.hand_type != HandType.NORMAL else ""
        
        embed.add_field(
            name=f"{status_emoji} {player.username}",
            value=f"{player_display}\n📊 Điểm: **{player.hand_value}** {hand_desc}\n💰 Cược: **{player.bet:,}**",
            inline=True
        )

    if table.current_player:
        embed.set_footer(text=f"🎮 Lượt của: {table.current_player.username}")

    return embed

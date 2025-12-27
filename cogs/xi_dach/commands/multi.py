"""Multiplayer Game Implementation."""

import discord
import time
import asyncio
import io
from typing import TYPE_CHECKING, List, Dict, Optional

from database_manager import db_manager, get_or_create_user, batch_update_seeds
from core.logger import setup_logger

from ..constants import (
    MIN_BET, LOBBY_DURATION, BETTING_DURATION, TURN_TIMEOUT,
    MAX_PLAYERS
)
from ..core.game_manager import game_manager
from ..core.table import Table, TableStatus
from ..core.player import Player, PlayerStatus
from ..core.deck import Deck
from ..services.hand_service import HandType, compare_hands, calculate_hand_value
from ..services.ai_service import get_dealer_decision
from ..ui.embeds import create_lobby_embed, create_multi_game_embed
from ..ui.views import LobbyView, MultiBetView, MultiGameView, BettingEntryView
from ..ui.render import render_game_state

if TYPE_CHECKING:
    from ..cog import XiDachCog

logger = setup_logger("XiDachMulti", "cogs/xidach.log")

async def start_multiplayer(cog: "XiDachCog", interaction: discord.Interaction) -> None:
    """Start a multiplayer lobby."""
    user = interaction.user
    channel_id = interaction.channel.id

    if game_manager.get_table(channel_id):
        await interaction.response.send_message(
            "❌ Đã có sòng bài đang chạy tại kênh này!", ephemeral=True
        )
        return

    # Create Table
    table = game_manager.create_table(channel_id, host_id=user.id, is_multiplayer=True)
    
    # Auto-add host
    # Host needs to join explicitly or auto? Existing logic: Host must join via button or auto-added?
    # Original logic: _start_lobby just showed embed. Players join via button.
    # Let's keep it consistent: Host must click Join too, OR auto-join.
    # Original: `await self._start_lobby(interaction, table)`
    
    await _start_lobby(cog, interaction, table)


async def _start_lobby(cog: "XiDachCog", interaction: discord.Interaction, table: Table) -> None:
    """Run the lobby phase."""
    # await interaction.response.defer() # Might be deferred already?
    
    embed = create_lobby_embed(table, LOBBY_DURATION)
    view = LobbyView(cog, table, timeout=LOBBY_DURATION)
    
    msg = await interaction.response.send_message(embed=embed, view=view)
    table.message_id = msg.id if not isinstance(msg, discord.Interaction) else (await interaction.original_response()).id
    
    # Countdown Loop
    end_time = time.time() + LOBBY_DURATION
    try:
        while time.time() < end_time:
            if table.status != TableStatus.WAITING: 
                break # Force started
            
            # Check if Full
            if len(table.players) >= MAX_PLAYERS:
                break
                
            await asyncio.sleep(2) # Refresh rate (low to avoid ratelimit)
            # We don't need to edit message constantly unless timer is text-based.
            # Timestamp <t:R> handles visual countdown.
            
    except Exception as e:
        logger.error(f"Lobby error: {e}")
        
    # Check players
    if len(table.players) == 0:
        await interaction.channel.send("❌ Không có ai tham gia. Hủy sòng.")
        game_manager.remove_table(table.table_id)
        return

    await _start_betting_phase(cog, interaction.channel, table)


async def player_join_lobby(cog: "XiDachCog", interaction: discord.Interaction, table: Table) -> None:
    """Handle join request."""
    user = interaction.user
    
    async with table.lock:
        if user.id in table.players:
            await interaction.response.send_message("❌ Bạn đã tham gia rồi!", ephemeral=True)
            return
            
        if len(table.players) >= MAX_PLAYERS:
            await interaction.response.send_message("❌ Sòng đã đầy!", ephemeral=True)
            return

        # Check balance
        await get_or_create_user(user.id, user.display_name)
        # Note: We don't deduct money yet. Just check exists.

        player = Player(user_id=user.id, username=user.display_name, status=PlayerStatus.WAITING)
        table.add_player(player)

        # Update Embed
        try:
             elapsed = time.time() - table.created_at
             remaining = max(0, LOBBY_DURATION - int(elapsed))
             embed = create_lobby_embed(table, remaining)
             await interaction.response.edit_message(embed=embed)
        except Exception as e:
             logger.error(f"Join update error: {e}")


async def _start_betting_phase(cog: "XiDachCog", channel, table: Table) -> None:
    """Transition to betting phase."""
    table.status = TableStatus.BETTING
    
    # Send Betting Interface (One msg per player? Or one shared msg?)
    # Original logic: Send a shared Embed saying "Check DM/Ephemeral"? 
    # Actually original sent a View with Bet Buttons in the channel. 
    # But buttons are global. 
    # View was `MultiBetView`. It had buttons +100 etc. but callback checked user_id.
    # The issue: ONE view for ALL players is chaotic if it's ephemeral.
    # Use: Generic View in Channel. When clicked -> Ephemeral Controller or just direct action.
    # Original used `MultiBetView(cog, table, player)` which implies PER PLAYER?
    # "for uid, player in table.players.items(): send ephemeral?"
    # No, usually Discord bots use one public message with buttons that act ephemerally.
    
    # Let's verify `views.py`. `MultiBetView` takes `player`. This suggests Per-Player View.
    # But we can't send per-player View easily in a channel without spamming.
    # The clean way: Send 1 "Master Betting" Embed. Buttons: "Đặt Cược".
    # Click "Đặt Cược" -> Sends Ephemeral `MultiBetView`.
    # BUT `MultiBetView` in my `views.py` has buttons for amounts.
    # Let's assume we send ONE Public Menu, and players click "Open Bet Interface"?
    # OR we send individual DMs? (Bad UX).
    # OR we just loop and ping everyone?
    
    # Wait for ready or timeout
    end_time = time.time() + BETTING_DURATION
    
    # Generic "Open Betting" View just in case? 
    # Actually we just wait. Players click buttons on the PREVIOUS generic message (if we sent one).
    # MultiBetView logic above was tricky.
    
    # Send generic betting dashboard
    # We need a View that allows users to open their betting panel?
    # For now, let's assume we proceed when all ready OR timeout.
    
    start_msg = await channel.send(
        content=f"⏳ **GIAI ĐOẠN ĐẶT CƯỢC** ({BETTING_DURATION}s)\nVui lòng mở Bảng Đặt Cược bên dưới:",
        view=BettingEntryView(cog, table, timeout=BETTING_DURATION)
    )
    # To fix "WIP": We need a public view that spawns personal betting views.
    # But implementing a new View class now might be overkill.
    # Let's rely on the fact that `_start_lobby` had players join.
    # We can ping each player individually with a DM? Or ephemeral?
    # Valid solution: Loop.
    
    while time.time() < end_time:
        await asyncio.sleep(2)
        
        # Check if table killed
        if table.status != TableStatus.BETTING:
            break
            
        # Check if all ready
        # Only count players with bet > 0?
        # Standard: ready_players_count == active_players_count
        if table.ready_players_count > 0 and table.ready_players_count == len(table.players):
             break
             
    # End of loop
    if table.status == TableStatus.BETTING:
        # Auto-start with ready players
        ready_p = [p for p in table.players.values() if p.is_ready and p.bet > 0]
        if not ready_p:
            await channel.send("❌ Hết giờ đặt cược và không ai sẵn sàng. Hủy sòng.")
            game_manager.remove_table(table.table_id)
        else:
            await channel.send("⏳ Hết giờ đặt cược! Bắt đầu với những người đã sẵn sàng...")
            await _start_multi_game(cog, channel, table)


async def process_bet(cog: "XiDachCog", interaction: discord.Interaction, table: Table, user_id: int, amount: int) -> None:
    """Handle bet placement."""
    async with table.lock:
        player = table.players.get(user_id)
        if not player: return

        # Validate
        if amount < MIN_BET:
            await interaction.response.send_message(f"❌ Cược tối thiểu {MIN_BET}!", ephemeral=True)
            return

        # Check Balance (Atomic)
        # We don't deduct yet? Or deduct specific amount?
        # Original: Checked balance, didn't deduct until `player_ready`? Or deduct immediately?
        # Original Audit said "Check-then-Act".
        # Safe way: Deduct on Ready? Or Deduct on Bet?
        # If we support "Change Bet", Deducting immediately is messy (refunds needed).
        # Best: Just validate balance > amount.
        # Deduct ONLY when confirming READY.
        
        # Check if user VALID has enough
        current_bal = await db_manager.get_user_balance(user_id)
        if current_bal < amount:
            await interaction.response.send_message("❌ Không đủ hạt!", ephemeral=True)
            return

        player.bet = amount
        await interaction.response.send_message(f"✅ Đã chọn cược: **{amount:,}**", ephemeral=True)
        # Note: Embed update needed?


async def player_ready(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player) -> None:
    """Commit bet and set ready."""
    async with table.lock:
        if player.bet <= 0:
            await interaction.response.send_message("❌ Vui lòng đặt cược trước!", ephemeral=True)
            return

        # Atomic Deduct
        success = await db_manager.modify(
            "UPDATE users SET seeds = seeds - ? WHERE user_id = ? AND seeds >= ?",
            (player.bet, player.user_id, player.bet)
        )
        if not success:
            await interaction.response.send_message("❌ Giao dịch thất bại! Có người đã nhanh tay hơn (hoặc hết tiền).", ephemeral=True)
            return

        player.is_ready = True
        await interaction.response.send_message(f"✅ **{player.username}** đã sẵn sàng!", ephemeral=False)
        
        # Check if all ready
        if all(p.is_ready for p in table.players.values()):
            # Start Game
            asyncio.create_task(_start_multi_game(cog, interaction.channel, table))


async def _start_multi_game(cog: "XiDachCog", channel, table: Table) -> None:
    """Initialize game loop."""
    table.status = TableStatus.PLAYING
    
    # Deal Cards
    for p in table.players.values():
        p.hand = table.deck.draw(2)
        p.status = PlayerStatus.PLAYING
        p.hand_value = calculate_hand_value(p.hand)
        # Check instant win
        if p.hand_type in (HandType.XI_DACH, HandType.XI_BAN):
             p.status = PlayerStatus.BLACKJACK

    table.dealer_hand = table.deck.draw(2)
    
    # Sort turns (Position based? or Join order?)
    # Using existing dict order.
    table.turn_order = [p for p in table.players.values() if p.status == PlayerStatus.PLAYING] # Exclude failed bets?
    if not table.turn_order:
        await channel.send("❌ Không có người chơi hợp lệ. Hủy.")
        return
        
    table.turn_index = 0
    await _next_turn(cog, channel, table)


async def _next_turn(cog: "XiDachCog", channel, table: Table) -> None:
    """Process next turn."""
    if table.turn_index >= len(table.turn_order):
        await _finish_multi_game(cog, channel, table)
        return
        
    player = table.turn_order[table.turn_index]
    table.current_player = player
    
    # Skip if finished (Blackjack)
    if player.status != PlayerStatus.PLAYING:
        table.turn_index += 1
        await _next_turn(cog, channel, table)
        return

    # Send Generic Game Embed (With buttons enabled for current player)
    # Note: MultiGameView checks `_is_active_and_turn`.
    
    embed = create_multi_game_embed(table)
    
    # Render
    img_bytes = await render_game_state(
        table.dealer_hand, 
        _get_players_data(table), 
        hide_dealer=True
    )
    file = discord.File(io.BytesIO(img_bytes), filename="multi_game.png")
    embed.set_image(url="attachment://multi_game.png")
    
    view = MultiGameView(cog, table, channel=channel, timeout=TURN_TIMEOUT)
    
    msg = await channel.send(
        content=f"👉 Lượt của **<@{player.user_id}>**",
        embed=embed,
        view=view,
        file=file
    )
    table.current_turn_msg = msg
    table.turn_action_timestamp = time.time()
    
    # Timer Task? 
    # relying on view timeout or global loop? 
    # Cog usually has `cleanup_loop`.
    # We leave timeout to View `on_timeout`?
    # View timeout disables buttons only. Need `auto-stand`.
    # View will call `player_stand` on timeout maybe? 
    # In `views.py`, on_timeout just disables.
    # Ideally should auto-stand.


async def player_hit_multi(cog: "XiDachCog", interaction, table: Table, player: Player, view: MultiGameView) -> None:
    """Handle Draw for Multiplayer."""
    async with table.lock:
        await interaction.response.defer()
        
        card = table.deck.draw_one()
        player.add_card(card)
        
        if player.is_bust or len(player.hand) >= 5:
            player.status = PlayerStatus.BUST if player.is_bust else PlayerStatus.STAND
            await _advance_turn(cog, interaction, table)
        else:
            # Update View (Same Turn)
            await _refresh_game_view(interaction, table, view, player.user_id)


async def player_stand_multi(cog: "XiDachCog", interaction, table: Table, player: Player, view: MultiGameView) -> None:
    """Handle Stand for Multiplayer."""
    async with table.lock:
        if interaction:
            await interaction.response.defer()
        player.status = PlayerStatus.STAND
        await _advance_turn(cog, interaction, table)


async def force_stand_multi(cog: "XiDachCog", table: Table, player: Player) -> None:
    """Force stand a player (Timeout)."""
    async with table.lock:
        if player.status != PlayerStatus.PLAYING:
            return
        logger.info(f"[TIMEOUT] Force standing player {player.user_id}")
        player.status = PlayerStatus.STAND
        
        # We need a channel context to advance turn
        channel = cog.bot.get_channel(table.channel_id)
        if not channel: return

        # Need to simulate interaction-like object or refactor `_advance_turn`
        # `_advance_turn` uses `interaction.channel` usually.
        # Let's mock a simple object or refactor `_advance_turn` to accept channel explicitly.
        
        # Refactoring _advance_turn signature first is better.
        await _advance_turn(cog, None, table, channel_override=channel)


async def player_double_multi(cog: "XiDachCog", interaction, table: Table, player: Player, view: MultiGameView) -> None:
    """Handle Double Multi."""
    async with table.lock:
        await interaction.response.defer()

        # Atomic Deduct
        success = await db_manager.modify(
            "UPDATE users SET seeds = seeds - ? WHERE user_id = ? AND seeds >= ?",
            (player.bet, player.user_id, player.bet)
        )
        if not success:
             await interaction.followup.send("❌ Không đủ hạt để X2!", ephemeral=True)
             return
             
        player.bet *= 2
        player.is_doubled = True
        
        card = table.deck.draw_one()
        player.add_card(card)
        
        player.status = PlayerStatus.BUST if player.is_bust else PlayerStatus.STAND
        await _advance_turn(cog, interaction, table)


async def _advance_turn(cog: "XiDachCog", interaction, table: Table, channel_override=None):
    """Move to next player."""
    table.turn_index += 1
    channel = channel_override or (interaction.channel if interaction else None)
    
    # Clean up old message?
    try:
        if table.current_turn_msg:
             # Just try to delete, don't wait/check too much
             asyncio.create_task(table.current_turn_msg.delete())
    except:
        pass
        
    if channel:
        await _next_turn(cog, channel, table)
    else:
        logger.error("[MULTI] No channel found to advance turn!")


async def _refresh_game_view(interaction, table, view, user_id):
    """Refreshes the current turn message with new card state."""
    embed = create_multi_game_embed(table)
    img_bytes = await render_game_state(
        table.dealer_hand, _get_players_data(table), hide_dealer=True
    )
    file = discord.File(io.BytesIO(img_bytes), filename="multi_game.png")
    embed.set_image(url="attachment://multi_game.png")
    
    await interaction.edit_original_response(embed=embed, file=file, view=view)


async def _finish_multi_game(cog: "XiDachCog", channel, table: Table) -> None:
    """Dealer turn and results."""
    table.status = TableStatus.DEALER_TURN
    # Dealer AI Loop
    # (Simplified for brevity, similar to Solo but updating one message)
    
    # Reveal
    msg = await channel.send("🎲 **LƯỢT NHÀ CÁI**")
    
    while True:
        players_data = _get_players_data(table)
        img_bytes = await render_game_state(table.dealer_hand, players_data, hide_dealer=False)
        file = discord.File(io.BytesIO(img_bytes), filename="multi_end.png")
        
        embed = create_multi_game_embed(table)
        embed.set_image(url="attachment://multi_end.png")
        
        await msg.edit(embed=embed, attachments=[file])
        
        await asyncio.sleep(1.5)
        
        action, _ = get_dealer_decision(table.dealer_hand)
        if action == "stand":
            break
            
        table.dealer_hand.append(table.deck.draw_one())
    
    # Calculate Results
    table.status = TableStatus.FINISHED
    stats_data = []
    seed_updates = {}
    
    embed = discord.Embed(title="📊 KẾT QUẢ", color=discord.Color.gold())
    
    for uid, player in table.players.items():
        if player.bet <= 0: continue
        
        result, mul = compare_hands(player.hand, table.dealer_hand)
        payout = int(player.bet * mul)
        
        stats_data.append({
            'user_id': uid, 'result': result, 'payout': payout, 
            'hand_type': player.hand_type, 'is_bust': player.is_bust
        })
        
        if payout > 0:
            seed_updates[uid] = payout
            
        res_emoji = "🏆" if result == "win" else ("💀" if result == "lose" else "🤝")
        net = getattr(player, 'net_change', payout - player.bet) # Simplified
        net_str = f"+{payout - player.bet}" if result == "win" else f"-{player.bet}" if result == "lose" else "0"
        
        embed.add_field(
            name=f"{res_emoji} {player.username}",
            value=f"{get_hand_description(player.hand_type)}\nKL: **{net_str}** hạt",
            inline=True
        )

    # Batch Update DB
    if seed_updates:
        await batch_update_seeds(seed_updates)
        
    # Batch Stats
    await cog.stats.update_game_stats(channel.id, stats_data)
    
    await channel.send(embed=embed)
    game_manager.remove_table(table.table_id)


def _get_players_data(table: Table) -> list:
    """Helper to format player data for renderer."""
    return [{
        'name': p.username, 'cards': p.hand, 'score': p.hand_value, 'bet': p.bet
    } for p in table.players.values()]

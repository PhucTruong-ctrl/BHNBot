"""
Xi Dach Multiplayer Controller.

Handles the complete game flow:
- Phase 0: Lobby (Join/Bet)
- Phase 1: Initial Check (Xi Ban/Xi Dach)
- Phase 2: Player Turns (Draw/Stand)
- Phase 3: Dealer AI
- Phase 4: Results
"""

import asyncio
import io
import time
from typing import TYPE_CHECKING, Optional, List, Dict

import discord
from core.logger import setup_logger
from database_manager import db_manager, get_user_balance, batch_update_seeds, add_seeds

from ..core.game_manager import game_manager
from ..core.table import Table, TableStatus
from ..core.player import Player, PlayerStatus
from ..services.hand_service import (
    HandType,
    calculate_hand_value,
    determine_hand_type,
    is_du_tuoi,
    get_hand_description,
    format_hand,
    compare_hands,
    check_phase1_winner,
)
from ..services.ai_service import get_dealer_decision, get_smart_think_time
from ..ui.views import LobbyView, MultiGameView
from ..ui.embeds import create_lobby_embed, create_multi_game_embed
from ..ui.render import render_game_state, render_player_hand

if TYPE_CHECKING:
    from ..cog import XiDachCog

logger = setup_logger("XiDachMulti", "cogs/xidach_multi.log")

# Constants
LOBBY_DURATION = 30  # seconds (betting time)
TURN_TIMEOUT = 30  # seconds

async def _safe_send(channel, **kwargs):
    """Retries sending a message up to 3 times."""
    retries = 3
    for i in range(retries):
        try:
            return await channel.send(**kwargs)
        except discord.HTTPException as e:
            if i == retries - 1:
                logger.error(f"[SAFE_SEND] Failed after {retries} retries: {e}")
                return None
            logger.warning(f"[SAFE_SEND] Retry {i+1}/{retries} due to error: {e}")
            await asyncio.sleep(1 * (i + 1))
        except Exception as e:
            logger.error(f"[SAFE_SEND] Critical error: {e}")
            return None

async def _safe_edit(message, **kwargs):
    """Retries editing a message up to 3 times."""
    retries = 3
    if not message: return None
    for i in range(retries):
        try:
            return await message.edit(**kwargs)
        except discord.HTTPException as e:
            if i == retries - 1:
                logger.error(f"[SAFE_EDIT] Failed after {retries} retries: {e}")
                return None
            logger.warning(f"[SAFE_EDIT] Retry {i+1}/{retries} due to error: {e}")
            await asyncio.sleep(1 * (i + 1))
        except Exception as e:
            # Message might be deleted
            logger.error(f"[SAFE_EDIT] Critical error (msg likely deleted): {e}")
            return None


# ==================== PHASE 0: LOBBY ====================

async def start_multiplayer(cog: "XiDachCog", ctx_or_interaction, initial_bet: int) -> None:
    """Start or join a multiplayer Xi Dach game."""
    # Normalize ctx/interaction
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        channel_id = ctx_or_interaction.channel_id
    else:
        user = ctx_or_interaction.author
        channel_id = ctx_or_interaction.channel.id

    logger.info(f"[MULTI_START] User: {user.id} | Channel: {channel_id} | Bet: {initial_bet}")

    # Create table
    table = game_manager.create_table(channel_id, user.id, is_solo=False)
    if not table:
        msg = "⚠️ Đang có game diễn ra ở kênh này! Hãy đợi kết thúc hoặc qua kênh khác."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    table.channel_id = channel_id

    # Add host as first player with bet
    balance = await get_user_balance(user.id)
    if balance < initial_bet:
        msg = f"❌ Bạn không đủ hạt! (Cần {initial_bet:,}, có {balance:,})"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        game_manager.remove_table(table.channel_id)
        return

    # Deduct bet immediately
    # Deduct bet immediately
    await add_seeds(user.id, -initial_bet, 'xi_dach_bet', 'minigame')

    host = table.add_player(user.id, user.display_name, initial_bet)
    host.is_ready = True
    logger.info(f"[LOBBY] Host {user.id} joined with bet {initial_bet}")

    await _run_lobby(cog, ctx_or_interaction, table)


async def _run_lobby(cog: "XiDachCog", ctx_or_interaction, table: Table) -> None:
    """Run the lobby countdown and start game when ready."""
    embed = create_lobby_embed(table, LOBBY_DURATION)
    view = LobbyView(cog, table, timeout=LOBBY_DURATION + 5)

    # Send lobby message
    if isinstance(ctx_or_interaction, discord.Interaction):
        if not ctx_or_interaction.response.is_done():
            await ctx_or_interaction.response.send_message(embed=embed, view=view)
            msg = await ctx_or_interaction.original_response()
        else:
            msg = await ctx_or_interaction.followup.send(embed=embed, view=view)
    else:
        msg = await ctx_or_interaction.send(embed=embed, view=view)

    table.message_id = msg.id

    # Countdown loop
    end_time = time.time() + LOBBY_DURATION
    while time.time() < end_time:
        async with table.lock:
            if table.status == TableStatus.PLAYING:
                # Game started by host
                return

        await asyncio.sleep(2)

    # Timeout - auto start if players exist
    async with table.lock:
        if table.status != TableStatus.LOBBY:
            return

        valid_players = [p for p in table.players.values() if p.bet > 0]
        if not valid_players:
            channel = ctx_or_interaction.channel if hasattr(ctx_or_interaction, 'channel') else cog.bot.get_channel(table.channel_id)
            if channel:
                await channel.send("❌ Hết giờ, không có ai tham gia. Hủy sòng.")
            game_manager.remove_table(table.channel_id)
            return

    channel = ctx_or_interaction.channel if hasattr(ctx_or_interaction, 'channel') else cog.bot.get_channel(table.channel_id)
    if channel:
        # Auto-start without button requirement
        await channel.send("⌛ **Hết thời gian chờ! Tự động bắt đầu...**")
        await _start_game(cog, channel, table)


async def process_bet(cog: "XiDachCog", interaction: discord.Interaction, table: Table, user_id: int, amount: int) -> None:
    """Process a bet from a player. Amounts are ADDITIVE."""
    async with table.lock:
        if table.status != TableStatus.LOBBY:
            await interaction.response.send_message("⚠️ Game đã bắt đầu!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        balance = await get_user_balance(user_id)
        current_player = table.players.get(user_id)
        current_bet = current_player.bet if current_player else 0
        
        # ADDITIVE: New total = current + amount clicked
        new_total = current_bet + amount
        additional_needed = amount  # Always add the clicked amount

        if balance < additional_needed:
            await interaction.followup.send(f"❌ Không đủ hạt! (Cần {additional_needed:,}, bạn có {balance:,})", ephemeral=True)
            return

        # Deduct the clicked amount
        # Deduct the clicked amount
        await add_seeds(user_id, -additional_needed, 'xi_dach_bet_add', 'minigame')

        if current_player:
            current_player.bet = new_total  # Additive
            current_player.is_ready = True
        else:
            player = table.add_player(user_id, interaction.user.display_name, amount)
            player.is_ready = True

        logger.info(f"[BET] User {user_id} bet +{amount} (Total: {new_total})")
        await interaction.followup.send(f"✅ Cược thêm **{amount:,}** hạt! Tổng: **{new_total:,}**", ephemeral=True)

    # Update lobby message
    await _update_lobby_message(cog, table)


async def cancel_bet(cog: "XiDachCog", interaction: discord.Interaction, table: Table, user_id: int) -> None:
    """Cancel bet and refund player."""
    async with table.lock:
        if table.status != TableStatus.LOBBY:
            await interaction.response.send_message("⚠️ Game đã bắt đầu!", ephemeral=True)
            return

        player = table.players.get(user_id)
        if not player or player.bet <= 0:
            await interaction.response.send_message("❌ Bạn chưa đặt cược!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Refund the bet
        refund_amount = player.bet
        # Refund the bet
        refund_amount = player.bet
        await add_seeds(user_id, refund_amount, 'xi_dach_refund', 'minigame')

        # Remove player from table
        table.remove_player(user_id)
        logger.info(f"[CANCEL_BET] User {user_id} cancelled bet, refunded {refund_amount}")
        await interaction.followup.send(f"✅ Đã hoàn lại **{refund_amount:,}** hạt!", ephemeral=True)

    # Update lobby message
    await _update_lobby_message(cog, table)

async def request_start_game(cog: "XiDachCog", interaction: discord.Interaction, table: Table) -> None:
    """Host requests to start game immediately."""
    async with table.lock:
        if interaction.user.id != table.host_id:
            await interaction.response.send_message("❌ Chỉ chủ phòng mới được bắt đầu!", ephemeral=True)
            return

        if table.status != TableStatus.LOBBY:
            await interaction.response.send_message("⚠️ Game đã bắt đầu hoặc kết thúc!", ephemeral=True)
            return

        valid_players = [p for p in table.players.values() if p.bet > 0]
        if not valid_players:
            await interaction.response.send_message("❌ Chưa có ai đặt cược!", ephemeral=True)
            return

        await interaction.response.send_message("🎲 **Chủ phòng bắt đầu game!**")

    await _start_game(cog, interaction.channel, table)


async def _update_lobby_message(cog: "XiDachCog", table: Table) -> None:
    """Update the lobby embed with current players."""
    try:
        channel = cog.bot.get_channel(table.channel_id)
        if not channel or not table.message_id:
            return

        msg = await channel.fetch_message(table.message_id)
        embed = create_lobby_embed(table)
        await msg.edit(embed=embed)
    except Exception as e:
        logger.error(f"[UPDATE_LOBBY] Error: {e}")



# ==================== PHASE 1: INITIAL CHECK ====================

async def _start_game(cog: "XiDachCog", channel, table: Table) -> None:
    """Start the game and run Phase 1 checks."""
    async with table.lock:
        if table.status == TableStatus.PLAYING:
            logger.warning(f"[START_GAME] Table {table.table_id} already playing!")
            return

        table.status = TableStatus.PLAYING
        table.deck.reset()
        table.dealer_hand = []

        # Build turn order
        table._turn_order = [uid for uid, p in table.players.items() if p.bet > 0]
        table.current_player_idx = 0

        # Deal 2 cards to everyone
        for uid in table._turn_order:
            player = table.players[uid]
            player.hand = []
            player.status = PlayerStatus.WAITING
            player.add_card(table.deck.draw_one())
            player.add_card(table.deck.draw_one())

        table.dealer_hand = table.deck.draw(2)

    logger.info(f"[PHASE_1] Table {table.table_id} - Dealing cards")

    # Phase 1: Check for instant wins/losses
    _, dealer_type = determine_hand_type(table.dealer_hand)
    phase1_ended = False

    if dealer_type in (HandType.XI_BAN, HandType.XI_DACH):
        # Dealer has special hand - immediate resolution
        logger.info(f"[PHASE_1] Dealer has {dealer_type.name}!")
        phase1_ended = True

        results = []
        seed_updates = {}

        for uid, player in table.players.items():
            if player.bet <= 0:
                continue

            result, mul = check_phase1_winner(player.hand, table.dealer_hand)
            payout = int(player.bet * mul)

            if payout > 0:
                seed_updates[uid] = payout

            _, p_type = determine_hand_type(player.hand)
            results.append({
                "username": player.username,
                "hand_type": p_type.name,
                "result": result,
                "payout": payout - player.bet
            })
            player.status = PlayerStatus.BLACKJACK if p_type in (HandType.XI_BAN, HandType.XI_DACH) else PlayerStatus.STAND

        # Pay winners
        if seed_updates:
            await batch_update_seeds(seed_updates, reason='xi_dach_payout', category='minigame')

        # Send result
        embed = discord.Embed(
            title=f"🎰 NHÀ CÁI CÓ {get_hand_description(dealer_type)}!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="🤖 Nhà Cái",
            value=f"{format_hand(table.dealer_hand)}\n{get_hand_description(dealer_type)}",
            inline=False
        )

        for r in results:
            emoji = "🏆" if r["result"] == "win" else ("🤝" if r["result"] == "push" else "💀")
            net_str = f"+{r['payout']:,}" if r["payout"] >= 0 else f"{r['payout']:,}"
            embed.add_field(
                name=f"{emoji} {r['username']}",
                value=f"{r['hand_type']} | {net_str} Hạt",
                inline=True
            )

        await channel.send(embed=embed)
        game_manager.remove_table(table.channel_id)
        return

    # Check for player instant wins
    for uid, player in list(table.players.items()):
        if player.bet <= 0:
            continue

        _, p_type = determine_hand_type(player.hand)

        if p_type in (HandType.XI_BAN, HandType.XI_DACH):
            # Player instant win
            mul = 2.0 if p_type == HandType.XI_BAN else 1.5
            payout = int(player.bet * mul)
            profit = payout - player.bet

            await batch_update_seeds({uid: payout}, reason='xi_dach_instant_win', category='minigame')
            player.status = PlayerStatus.BLACKJACK
            player.payout = payout  # Store for result embed

            # Remove from turn order
            if uid in table._turn_order:
                table._turn_order.remove(uid)

            type_emoji = "🎰" if p_type == HandType.XI_DACH else "🏆"
            await channel.send(
                f"{type_emoji} **{player.username}** có {get_hand_description(p_type)}! "
                f"Lời **+{profit:,}** hạt, tổng **{payout:,}** về tay! 🎉"
            )
            logger.info(f"[PHASE_1] Player {uid} instant win: {p_type.name}")


    # Continue to Phase 2
    if table._turn_order:
        table.players[table._turn_order[0]].status = PlayerStatus.PLAYING
        await _next_turn(cog, channel, table)
    else:
        # All players won instantly - go to dealer
        await _run_dealer(cog, channel, table)


# ==================== PHASE 2: PLAYER TURNS ====================

async def _next_turn(cog: "XiDachCog", channel, table: Table) -> None:
    """Process the next player's turn."""
    async with table.lock:
        if table.status != TableStatus.PLAYING:
            logger.warning(f"[NEXT_TURN] Table {table.table_id} not playing!")
            return

        current = table.current_player
        if not current:
            # All players done - dealer's turn
            pass
        else:
            # Skip finished players
            while current and current.status != PlayerStatus.PLAYING:
                table.next_turn()
                current = table.current_player

    if not current:
        await _run_dealer(cog, channel, table)
        return

    # Render current player's view
    score, hand_type = determine_hand_type(current.hand)
    tuoi_str = "✅ Đủ tuổi" if is_du_tuoi(current.hand) else "❌ Chưa đủ tuổi"
    type_str = get_hand_description(hand_type)
    
    # Status text with color coding
    if hand_type == HandType.BUST:
        status_str = "❌ ĐÃ QUẮC (>21)"
        embed_color = discord.Color.red()
        title = f"❌ {current.username} ĐÃ QUẮC!"
    elif hand_type in (HandType.XI_BAN, HandType.XI_DACH, HandType.NGU_LINH):
        status_str = f"🏆 {type_str}"
        embed_color = discord.Color.gold()
        title = f"🏆 {current.username} - {type_str}!"
    else:
        status_str = tuoi_str
        embed_color = discord.Color.blue()
        title = f"👤 Lượt của {current.username}"

    embed = discord.Embed(
        title=title,
        color=embed_color
    )
    
    # Trạng thái field
    embed.add_field(
        name="📊 Trạng thái",
        value=status_str,
        inline=False
    )
    
    # Cược và Điểm (inline)
    embed.add_field(
        name="💰 Cược",
        value=f"**{current.bet:,}** hạt",
        inline=True
    )
    embed.add_field(
        name="🎰 Điểm",
        value=f"**{score}**",
        inline=True
    )
    
    # Bài text
    embed.add_field(
        name="🃏 Bài của bạn",
        value=format_hand(current.hand),
        inline=False
    )

    # Render image
    try:
        ts = int(time.time() * 1000)
        img_bytes = await render_player_hand(current.hand, current.username)
        filename = f"hand_{ts}.png"
        file = discord.File(io.BytesIO(img_bytes), filename=filename)
        embed.set_image(url=f"attachment://{filename}")
    except Exception as e:
        logger.error(f"[RENDER] Error: {e}")
        file = None

    view = MultiGameView(cog, table, channel=channel, timeout=TURN_TIMEOUT)

    if file:
        msg = await _safe_send(
            channel,
            content=f"👉 <@{current.user_id}>",
            embed=embed,
            view=view,
            file=file
        )
    else:
        msg = await _safe_send(
            channel,
            content=f"👉 <@{current.user_id}>",
            embed=embed,
            view=view
        )
    
    # If explicit send failed, try text only fallback
    if not msg:
         logger.warning(f"[NEXT_TURN] Send failed (likely image), retrying text only")
         msg = await _safe_send(
            channel,
            content=f"👉 <@{current.user_id}> (Lỗi hiển thị ảnh)",
            embed=embed,
            view=view
         )

    table.current_turn_msg = msg
    table.turn_action_timestamp = time.time()


async def player_hit_multi(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player, view) -> None:
    """Handle player drawing a card."""
    async with table.lock:
        if table.status != TableStatus.PLAYING:
            await interaction.response.send_message("⚠️ Game chưa bắt đầu hoặc đã kết thúc!", ephemeral=True)
            return

        if table.current_player != player:
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

        await interaction.response.defer()

        card = table.deck.draw_one()
        player.add_card(card)
        logger.info(f"[HIT] Player {player.user_id} drew {card}")

        score, hand_type = determine_hand_type(player.hand)

        # Check for end conditions
        if hand_type == HandType.BUST:
            player.status = PlayerStatus.BUST
            logger.info(f"[BUST] Player {player.user_id} busted with {score}")

        elif hand_type == HandType.NGU_LINH:
            player.status = PlayerStatus.STAND  # Ngu Linh auto-stands
            logger.info(f"[NGU_LINH] Player {player.user_id} achieved Ngu Linh!")

    # Update display
    await _refresh_turn_display(cog, interaction.channel, table, player)

    # Check if turn should end
    if player.status in (PlayerStatus.BUST, PlayerStatus.STAND):
        await _advance_to_next(cog, interaction.channel, table)


async def player_stand_multi(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player, view) -> None:
    """Handle player standing."""
    async with table.lock:
        if table.status != TableStatus.PLAYING:
            await interaction.response.send_message("⚠️ Game chưa bắt đầu!", ephemeral=True)
            return

        if table.current_player != player:
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

        # Check "Đủ tuổi" rule
        if not is_du_tuoi(player.hand):
            score = calculate_hand_value(player.hand)
            await interaction.response.send_message(
                f"❌ Bạn chỉ có **{score} điểm** - Chưa đủ tuổi (cần ≥16)! Phải rút thêm.",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        player.status = PlayerStatus.STAND
        logger.info(f"[STAND] Player {player.user_id} stood with {calculate_hand_value(player.hand)}")

    await _advance_to_next(cog, interaction.channel, table)


async def player_double_multi(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player, view) -> None:
    """Handle double down."""
    async with table.lock:
        if not player.can_double:
            await interaction.response.send_message("❌ Không thể gấp đôi lúc này!", ephemeral=True)
            return

        balance = await get_user_balance(player.user_id)
        if balance < player.bet:
            await interaction.response.send_message(f"❌ Không đủ hạt để gấp đôi!", ephemeral=True)
            return

        await interaction.response.defer()

        # Deduct additional bet
        # Deduct additional bet
        await add_seeds(player.user_id, -player.bet, 'xi_dach_double', 'minigame')

        player.bet *= 2
        player.is_doubled = True

        # Draw one card and end turn
        card = table.deck.draw_one()
        player.add_card(card)

        score, hand_type = determine_hand_type(player.hand)
        player.status = PlayerStatus.BUST if hand_type == HandType.BUST else PlayerStatus.STAND

        logger.info(f"[DOUBLE] Player {player.user_id} doubled. New bet: {player.bet}, drew {card}")

    # Update display to show the doubled card
    await _refresh_turn_display(cog, interaction.channel, table, player)
    
    # Double Down = Limit 1 card -> End Turn
    await _advance_to_next(cog, interaction.channel, table)


async def force_stand_multi(cog: "XiDachCog", table: Table, player: Player) -> None:
    """Force stand/bust on timeout based on hand value."""
    async with table.lock:
        if not player or player.status != PlayerStatus.PLAYING:
            return

        # Check if player has enough points
        score, _ = determine_hand_type(player.hand)
        
        if score < 16:
            # Under 16 points = Auto-lose
            logger.info(f"[TIMEOUT] Player {player.user_id} timed out with {score} points - AUTO-BUST")
            player.status = PlayerStatus.BUST
            timeout_msg = f"⏰ **{player.username}** hết thời gian với **{score} điểm** (Chưa đủ tuổi)! Thua luôn. 💀"
        else:
            # 16+ points = Auto-stand
            logger.info(f"[TIMEOUT] Player {player.user_id} timed out with {score} points - AUTO-STAND")
            player.status = PlayerStatus.STAND
            timeout_msg = f"⏰ **{player.username}** hết thời gian! Tự động dằn với **{score} điểm**."

    channel = cog.bot.get_channel(table.channel_id)
    if channel:
        await channel.send(timeout_msg)
        await _advance_to_next(cog, channel, table)


async def _refresh_turn_display(cog: "XiDachCog", channel, table: Table, player: Player) -> None:
    """Refresh the current turn display."""
    score, hand_type = determine_hand_type(player.hand)
    tuoi_str = "✅ Đủ tuổi" if is_du_tuoi(player.hand) else "❌ Chưa đủ tuổi"
    type_str = get_hand_description(hand_type)

    embed = discord.Embed(
        title=f"🎮 Lượt của {player.username}",
        description=f"**Điểm: {score}** {type_str} ({tuoi_str})",
        color=discord.Color.red() if hand_type == HandType.BUST else discord.Color.blue()
    )
    embed.add_field(name="🃏 Bài của bạn", value=format_hand(player.hand), inline=False)
    embed.add_field(name="🤖 Nhà Cái", value=format_hand(table.dealer_hand, hide_first=True), inline=False)

    try:
        ts = int(time.time() * 1000)
        img_bytes = await render_player_hand(player.hand, player.username)
        filename = f"hand_{ts}.png"
        file = discord.File(io.BytesIO(img_bytes), filename=filename)
        embed.set_image(url=f"attachment://{filename}")

        if table.current_turn_msg:
            await _safe_edit(table.current_turn_msg, embed=embed, attachments=[file])
    except Exception as e:
        logger.error(f"[REFRESH] Error: {e}")
        if table.current_turn_msg:
            await _safe_edit(table.current_turn_msg, embed=embed)


async def _advance_to_next(cog: "XiDachCog", channel, table: Table) -> None:
    """Advance to next player."""
    async with table.lock:
        # Keep old message for history (do NOT delete)
        table.current_turn_msg = None
        table.next_turn()

    await _next_turn(cog, channel, table)


# ==================== PHASE 3: DEALER ====================

async def _run_dealer(cog: "XiDachCog", channel, table: Table) -> None:
    """Run dealer's AI turn with visual updates."""
    import random
    
    async with table.lock:
        if table.status in (TableStatus.DEALER_TURN, TableStatus.FINISHED):
            logger.warning(f"[DEALER] Table {table.table_id} already in dealer phase!")
            return

        table.status = TableStatus.DEALER_TURN

    logger.info(f"[PHASE_3] Table {table.table_id} - Dealer's turn")

    # Get survivors (not bust)
    survivors = [p for p in table.players.values() if p.status not in (PlayerStatus.BUST, PlayerStatus.BLACKJACK)]

    # Send initial dealer message with image
    d_score, d_type = determine_hand_type(table.dealer_hand)
    embed = discord.Embed(
        title="🎲 LƯỢT CỦA NHÀ CÁI",
        description=f"**Điểm: {d_score}**",
        color=discord.Color.gold()
    )
    embed.add_field(name="🃏 Bài Nhà Cái", value=format_hand(table.dealer_hand), inline=False)
    
    # Render dealer's hand image
    try:
        ts = int(time.time() * 1000)
        img_bytes = await render_player_hand(table.dealer_hand, "Nhà Cái")
        filename = f"dealer_{ts}.png"
        file = discord.File(io.BytesIO(img_bytes), filename=filename)
        embed.set_image(url=f"attachment://{filename}")
        dealer_msg = await _safe_send(channel, embed=embed, file=file)
    except Exception as e:
        logger.error(f"[DEALER_RENDER] Error: {e}")
        dealer_msg = await _safe_send(channel, embed=embed)

    # Dealer AI loop - each draw with visual update
    while True:
        # Longer thinking time: 2-10 seconds
        think_time = random.uniform(2.0, 10.0)
        await asyncio.sleep(think_time)

        action, reason = get_dealer_decision(table.dealer_hand, survivors)
        logger.info(f"[DEALER_AI] {action}: {reason}")

        if action == "stand":
            break

        # Draw card
        card = table.deck.draw_one()
        table.dealer_hand.append(card)

        d_score, d_type = determine_hand_type(table.dealer_hand)
        
        # Create updated embed with new hand
        embed = discord.Embed(
            title=f"🎲 NHÀ CÁI: {d_score} điểm",
            description=f"🃏 *{reason}*",
            color=discord.Color.red() if d_type == HandType.BUST else discord.Color.gold()
        )
        embed.add_field(name="🃏 Bài", value=format_hand(table.dealer_hand), inline=False)
        
        # Render updated hand - delete old, send new (Discord can't edit attachments properly)
        try:
            ts = int(time.time() * 1000)
            img_bytes = await render_player_hand(table.dealer_hand, "Nhà Cái")
            filename = f"dealer_{ts}.png"
            file = discord.File(io.BytesIO(img_bytes), filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            
            # Delete old message and send new one (to update image)
            try:
                await dealer_msg.delete()
            except:
                pass
            dealer_msg = await _safe_send(channel, embed=embed, file=file)
        except Exception as e:
            logger.error(f"[DEALER_RENDER] Error: {e}")
            # Fallback: just edit embed text
            await _safe_edit(dealer_msg, embed=embed)

        # Check Ngu Linh or Bust
        if len(table.dealer_hand) >= 5 or d_type == HandType.BUST:
            break

    # Final dealer result announcement - richer embed
    d_score, d_type = determine_hand_type(table.dealer_hand)
    logger.info(f"[DEALER_RESULT] Score: {d_score}, Type: {d_type.name}")
    
    d_desc = get_hand_description(d_type)
    
    # Create final dealer embed
    if d_type == HandType.BUST:
        final_embed = discord.Embed(
            title="💥 NHÀ CÁI QUẮC!",
            color=discord.Color.red()
        )
        status_str = "❌ QUẮC (>21)"
    elif d_type == HandType.NGU_LINH:
        final_embed = discord.Embed(
            title="🏆 NHÀ CÁI NGŨ LINH!",
            color=discord.Color.gold()
        )
        status_str = "🏆 NGŨ LINH (5 lá)"
    else:
        final_embed = discord.Embed(
            title="✅ NHÀ CÁI ĐÃ CHỐT BÀI",
            color=discord.Color.green()
        )
        status_str = "✅ CHỐT BÀI"
    
    final_embed.add_field(name="🎰 Điểm", value=f"**{d_score}**", inline=True)
    final_embed.add_field(name="📊 Trạng thái", value=status_str, inline=True)
    
    # Consolidate message: Edit the last dealer message instead of sending new one
    edited = False
    if dealer_msg:
        try:
            # Reuse the image from the existing message
            if dealer_msg.embeds and dealer_msg.embeds[0].image:
                final_embed.set_image(url=dealer_msg.embeds[0].image.url)
            
            # Edit the message
            if await _safe_edit(dealer_msg, embed=final_embed):
                edited = True
        except Exception as e:
            logger.warning(f"[DEALER_FINAL] Edit failed, falling back to send: {e}")

    if not edited:
        # Fallback: Render and Send New (only if edit failed)
        try:
            ts = int(time.time() * 1000)
            img_bytes = await render_player_hand(table.dealer_hand, "Nhà Cái")
            filename = f"dealer_final_{ts}.png"
            file = discord.File(io.BytesIO(img_bytes), filename=filename)
            final_embed.set_image(url=f"attachment://{filename}")
            await _safe_send(channel, embed=final_embed, file=file)
        except Exception as e:
            logger.error(f"[DEALER_FINAL] Render error: {e}")
            await _safe_send(channel, embed=final_embed)

    await _finish_game(cog, channel, table)


# ==================== PHASE 4: RESULTS ====================

async def _finish_game(cog: "XiDachCog", channel, table: Table) -> None:
    """Calculate final results and pay out."""
    import random
    
    async with table.lock:
        table.status = TableStatus.FINISHED

    d_score, d_type = determine_hand_type(table.dealer_hand)
    seed_updates = {}
    results = []

    for uid, player in table.players.items():
        if player.bet <= 0:
            continue

        p_score, p_type = determine_hand_type(player.hand)
        
        # Check if instant winner (already paid in Phase 1)
        if player.status == PlayerStatus.BLACKJACK:
            # Instant winner - use stored payout
            payout = getattr(player, 'payout', int(player.bet * (2.0 if p_type == HandType.XI_BAN else 1.5)))
            net = payout - player.bet
            results.append({
                "user_id": uid,
                "username": player.username,
                "score": p_score,
                "hand": player.hand,
                "hand_type": p_type,
                "result": "instant_win",
                "bet": player.bet,
                "net": net,
                "payout": payout
            })
            logger.info(f"[RESULT] Player {uid}: instant_win ({p_type.name}), net {net:+}")
            continue

        result, mul = compare_hands(player.hand, table.dealer_hand)
        payout = int(player.bet * mul)

        if payout > 0:
            seed_updates[uid] = payout

        net = payout - player.bet
        results.append({
            "user_id": uid,
            "username": player.username,
            "score": p_score,
            "hand": player.hand,
            "hand_type": p_type,
            "result": result,
            "bet": player.bet,
            "net": net,
            "payout": payout
        })

        logger.info(f"[RESULT] Player {uid}: {result}, net {net:+}")


    # Pay winners
    if seed_updates:
        await batch_update_seeds(seed_updates, reason='xi_dach_refund', category='minigame')

    # Flavor texts
    win_flavors = ["Đỉnh cao! 🔥", "Thắng đậm! 💰", "Số hưởng! 🍀", "Ngon! 👏"]
    lose_flavors = ["Gà văiii 🤣", "Đen quá! 😢", "Thua keo này, bày keo khác! 💪", "Chia buồn... 😅"]
    push_flavors = ["Hòa êm! 🤝", "Huề vốn! ⚖️"]

    # Build result embed
    embed = discord.Embed(
        title="🎰🎰🎰 KẾT QUẢ XÌ DÁCH",
        color=discord.Color.gold()
    )

    # Dealer info with cards
    d_desc = get_hand_description(d_type)
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{format_hand(table.dealer_hand)} ({d_score})",
        inline=False
    )

    # Each player result - BIG format
    for r in results:
        # Special emoji for instant winners
        if r["result"] == "instant_win":
            if r["hand_type"] == HandType.XI_BAN:
                p_emoji = "💎"
                type_label = "XÌ BÀN"
            else:
                p_emoji = "�"
                type_label = "XÌ DÁCH"
        elif r["result"] == "win":
            p_emoji = "🏆"
            type_label = None
        elif r["result"] == "lose":
            p_emoji = "😢"
            type_label = None
        else:
            p_emoji = "🤝"
            type_label = None
        
        # Cards line with type label for instant wins
        cards_str = f"{format_hand(r['hand'])} ({r['score']})"
        if type_label:
            cards_str = f"**{type_label}** - {cards_str}"
        
        # Build player result
        embed.add_field(
            name=f"{p_emoji} @{r['username']}",
            value=cards_str,
            inline=False
        )
        
        # Big result text
        if r["result"] == "instant_win":
            result_str = f"**🎉 {type_label}! Lời +{r['net']:,}, tổng {r['payout']:,} HẠT 🎉**"
            flavor = random.choice(win_flavors)
        elif r["result"] == "win":
            result_str = f"**Kết quả: THẮNG | +{r['net']:,} HẠT💰**"
            flavor = random.choice(win_flavors)
        elif r["result"] == "lose":
            result_str = f"**Kết quả: THUA | {r['net']:,} HẠT💸**"
            flavor = random.choice(lose_flavors)
        else:
            result_str = f"**Kết quả: HÒA | ±0 HẠT⚖️**"
            flavor = random.choice(push_flavors)
        
        embed.description = f"{result_str}\n\n*{flavor}*" if len(results) == 1 else None


    # If multiple players, add summary
    if len(results) > 1:
        summary_lines = []
        for r in results:
            if r["result"] == "instant_win":
                emoji = "�" if r["hand_type"] == HandType.XI_DACH else "💎"
            elif r["result"] == "win":
                emoji = "🏆"
            elif r["result"] == "lose":
                emoji = "💀"
            else:
                emoji = "🤝"
            net_str = f"+{r['net']:,}" if r["net"] >= 0 else f"{r['net']:,}"
            summary_lines.append(f"{emoji} **{r['username']}**: {net_str} Hạt")
        embed.add_field(name="📊 Tổng Kết", value="\n".join(summary_lines), inline=False)


    # Send result
    await channel.send(embed=embed)
    game_manager.remove_table(table.channel_id)


# ==================== LOBBY HELPERS ====================

async def player_join_lobby(cog: "XiDachCog", interaction: discord.Interaction, table: Table) -> None:
    """Player joins lobby without betting yet."""
    async with table.lock:
        if table.status != TableStatus.LOBBY:
            await interaction.response.send_message("⚠️ Game đã bắt đầu!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in table.players:
            await interaction.response.send_message("Bạn đã tham gia rồi!", ephemeral=True)
            return

        table.add_player(user_id, interaction.user.display_name, 0)
        logger.info(f"[JOIN] User {user_id} joined lobby")
        await interaction.response.send_message("✅ Đã tham gia! Hãy chọn mức cược.", ephemeral=True)

    await _update_lobby_message(cog, table)


async def player_ready(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player) -> None:
    """Mark player as ready."""
    async with table.lock:
        if player.bet <= 0:
            await interaction.response.send_message("❌ Bạn chưa đặt cược!", ephemeral=True)
            return

        player.is_ready = True
        await interaction.response.send_message("✅ Sẵn sàng!", ephemeral=True)

    await _update_lobby_message(cog, table)

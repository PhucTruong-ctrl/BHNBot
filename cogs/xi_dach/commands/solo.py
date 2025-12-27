"""Solo Game Implementation."""

import discord
import time
import asyncio
import io
import random
from typing import TYPE_CHECKING, Optional

from database_manager import db_manager
from core.logger import setup_logger

from ..constants import SOLO_TIMEOUT
from ..core.game_manager import game_manager
from ..core.table import Table, TableStatus
from ..core.player import Player, PlayerStatus
from ..core.deck import Deck
from ..services.hand_service import HandType, compare_hands, calculate_hand_value
from ..services.ai_service import get_dealer_decision
from ..ui.embeds import create_solo_game_embed, create_result_embed
from ..ui.views import SoloGameView
from ..ui.render import render_game_state, render_player_hand

if TYPE_CHECKING:
    from ..cog import XiDachCog

logger = setup_logger("XiDachSolo", "cogs/xidach.log")

async def start_solo_game(cog: "XiDachCog", ctx_or_interaction, bet_amount: int) -> None:
    """Start a solo game vs Dealer."""
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    
    # Validation
    if bet_amount < 1:
        msg = "❌ Số hạt cược phải lớn hơn 0!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Check Balance (Atomic)
    success = await db_manager.modify(
        "UPDATE users SET seeds = seeds - ? WHERE user_id = ? AND seeds >= ?",
        (bet_amount, user.id, bet_amount)
    )
    
    if not success:
        msg = "❌ Giao dịch thất bại! Bạn không đủ hạt."
        if isinstance(ctx_or_interaction, discord.Interaction):
             await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
             await ctx_or_interaction.send(msg)
        return

    # Create Table
    channel_id = ctx_or_interaction.channel.id
    if game_manager.get_table(channel_id):
        # Refund
        await db_manager.add_seeds(user.id, bet_amount)
        msg = "❌ Đang có ván bài tại kênh này! Vui lòng chờ hoặc sang kênh khác."
        if isinstance(ctx_or_interaction, discord.Interaction):
             await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
             await ctx_or_interaction.send(msg)
        return

    table = game_manager.create_table(channel_id, host_id=user.id)
    
    # Initialize Game State
    player = Player(
        user_id=user.id,
        username=user.display_name,
        bet=bet_amount,
        status=PlayerStatus.PLAYING
    )
    table.add_player(player)

    # Deal Cards
    # 2 for player, 2 for dealer
    player.hand = table.deck.draw(2)
    table.dealer_hand = table.deck.draw(2)
    
    # Initial Checks (Xi Dach/Xi Ban)
    # Check Player
    if player.hand_type in (HandType.XI_DACH, HandType.XI_BAN):
        player.status = PlayerStatus.BLACKJACK
    
    # Check Dealer (Only checked at end normally, but for auto-end logic?)
    # Rules say: If Dealer has Xi Dach, game ends immediately unless Player also has.
    # We will handle "Fast Finish" logic in _finish_solo_game or keep it here?
    # Usually we let player play unless dealer face up card is A/10 and we peek? 
    # VN rule: Dealer checks immediately? 
    # Simplest: Let flow continue to View, but if Player has Blackjack, View updates immediately.

    # Render
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.defer()
        
    try:
        # Initial Render
        players_data = [{
            'name': player.username,
            'cards': player.hand,
            'score': player.hand_value,
            'bet': player.bet
        }]
        img_bytes = await render_game_state(table.dealer_hand, players_data, hide_dealer=True)
        file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
        
        embed = create_solo_game_embed(table, player, hide_dealer=True)
        embed.set_image(url="attachment://solo_game.png")
        
        view = SoloGameView(cog, table, player, timeout=SOLO_TIMEOUT)
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view, file=file)
        else:
            await ctx_or_interaction.send(embed=embed, view=view, file=file)
            
        # If Player has Blackjack immediately -> Finish
        if player.status == PlayerStatus.BLACKJACK:
             await finish_solo_game(cog, ctx_or_interaction, table, player)
             
    except Exception as e:
        logger.error(f"Error starting solo game: {e}", exc_info=True)
        game_manager.remove_table(channel_id)
        await db_manager.add_seeds(user.id, bet_amount) # Refund on crash


async def player_hit(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player) -> None:
    """Handle Hit action."""
    await interaction.response.defer()
    async with table.lock:
        if player.status != PlayerStatus.PLAYING:
            return

        card = table.deck.draw_one()
        player.add_card(card)
        
        # Check Bust or Ngu Linh
        if player.is_bust:
            player.status = PlayerStatus.BUST
            await finish_solo_game(cog, interaction, table, player)
            return
            
        if len(player.hand) >= 5:
            # Ngu Linh? HandType calculation handles value. 
            # If 5 cards and not bust, it is Ngu Linh (or just 5 cards <= 21).
            # Auto Stand.
            player.status = PlayerStatus.STAND
            await finish_solo_game(cog, interaction, table, player)
            return

        # Update View
        await _update_solo_view(interaction, input_cog=cog, table=table, player=player)


async def player_stand(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player) -> None:
    """Handle Stand action."""
    await interaction.response.defer()
    async with table.lock:
        if player.status != PlayerStatus.PLAYING:
            return
        player.status = PlayerStatus.STAND
        await finish_solo_game(cog, interaction, table, player)


async def player_double(cog: "XiDachCog", interaction: discord.Interaction, table: Table, player: Player) -> None:
    """Handle Double Down."""
    await interaction.response.defer()
    async with table.lock:
        if player.is_doubled or player.status != PlayerStatus.PLAYING:
            return

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
        
        if player.is_bust:
            player.status = PlayerStatus.BUST
        else:
            player.status = PlayerStatus.STAND
            
        await finish_solo_game(cog, interaction, table, player)


async def _update_solo_view(interaction: discord.Interaction, input_cog, table: Table, player: Player):
    """Helper to update the game view state."""
    # Render
    players_data = [{
        'name': player.username,
        'cards': player.hand,
        'score': player.hand_value,
        'bet': player.bet
    }]
    img_bytes = await render_game_state(table.dealer_hand, players_data, hide_dealer=True)
    file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
    
    embed = create_solo_game_embed(table, player, hide_dealer=True)
    embed.set_image(url="attachment://solo_game.png")
    
    view = SoloGameView(input_cog, table, player, timeout=SOLO_TIMEOUT)
    await interaction.edit_original_response(embed=embed, view=view, file=file)


async def finish_solo_game(cog: "XiDachCog", interaction, table: Table, player: Player) -> None:
    """End game, Dealer play, Payout."""
    # Dealer Play
    # Logic in Mechanics/DealerAI
    # We need to simulate the dealer loop with animation
    
    # Initial Reveal
    players_data = [{'name': player.username, 'cards': player.hand, 'score': player.hand_value, 'bet': player.bet}]
    
    # Show Dealer First Card
    # (In code we just render hide_dealer=False)
    img_bytes = await render_game_state(table.dealer_hand, players_data, hide_dealer=False)
    file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
    embed = create_solo_game_embed(table, player, hide_dealer=False)
    embed.set_image(url="attachment://solo_game.png")
    embed.set_field_at(1, name="🤖 Nhà Cái", value=f"🔍 Đang lật bài...\n📊 Điểm: **{table.dealer_value}**", inline=False)
    
    if isinstance(interaction, discord.Interaction):
        await interaction.edit_original_response(embed=embed, file=file, view=None)
    else:
        # Context support? Usually finish comes from Interaction (Button)
        pass

    await asyncio.sleep(1.5)

    # Dealer Loop
    while True:
        action, reason = get_dealer_decision(table.dealer_hand)
        if action == "stand":
            break
            
        # Draw
        card = table.deck.draw_one()
        table.dealer_hand.append(card)
        
        # Render
        img_bytes = await render_game_state(table.dealer_hand, players_data, hide_dealer=False)
        file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
        embed.set_image(url="attachment://solo_game.png")
        embed.set_field_at(1, name="🤖 Nhà Cái", value=f"🤖 Đang rút bài...\n📊 Điểm: **{table.dealer_value}**", inline=False)
        
        await interaction.edit_original_response(embed=embed, file=file)
        await asyncio.sleep(1.5)

    # Final Result
    result, multiplier = compare_hands(player.hand, table.dealer_hand)
    payout = int(player.bet * multiplier)
    
    if payout > 0:
        await db_manager.add_seeds(player.user_id, payout)
        
    # Stats
    await cog.stats.update_game_stats(
        interaction.channel.id,
        [{'user_id': player.user_id, 'result': result, 'payout': payout, 
          'hand_type': player.hand_type, 'is_bust': player.is_bust}]
    )
    
    # Final Embed
    # Use create_result_embed
    embed = create_result_embed(table, player, result, payout)
    
    # Final Image
    img_bytes = await render_game_state(table.dealer_hand, players_data, hide_dealer=False)
    file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
    embed.set_image(url="attachment://solo_game.png")
    
    await interaction.edit_original_response(embed=embed, file=file)
    
    # Cleanup
    game_manager.remove_table(table.channel_id)

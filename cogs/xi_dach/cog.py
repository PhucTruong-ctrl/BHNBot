"""
Xi Dach (Vietnamese Blackjack) - Discord Cog

Main cog containing command handlers and game logic orchestration.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
import io
import random
from typing import Optional

from database_manager import (
    db_manager,
    get_user_balance,
    add_seeds,
    get_or_create_user,
    batch_update_seeds,
)
from core.logger import setup_logger

from .game import (
    compare_hands,
    format_hand,
    get_hand_description,
    determine_hand_type,
    render_hand_image,
    render_game_state_image,
    calculate_hand_value,
    HandType,
)
from .models import (
    Table,
    Player,
    PlayerStatus,
    TableStatus,
    game_manager,
)
from .views import (
    SoloGameView,
    LobbyView,
    MultiBetView,
    MultiGameView,
    create_solo_game_embed,
    create_result_embed,
    create_lobby_embed,
    create_multi_game_embed,
)

logger = setup_logger("XiDachCog", "cogs/xidach.log")

# Game constants
MIN_BET = 1
MAX_PLAYERS = 8  # Limit 8 players (excluding dealer)

SOLO_TIMEOUT = 120  # seconds
LOBBY_DURATION = 30  # seconds
BETTING_DURATION = 15  # seconds after first player ready


def _get_lobby_remaining(table: Table) -> int:
    """Calculate remaining lobby time from table creation."""
    elapsed = time.time() - table.created_at
    remaining = max(0, LOBBY_DURATION - int(elapsed))
    return remaining


class XiDachCog(commands.Cog):
    """Cog for Xi Dach (Vietnamese Blackjack) game.
    
    Supports both single-player (1v1 vs bot) and multiplayer modes.
    
    Attributes:
        bot: The Discord bot instance.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_user_seeds(self, user_id: int) -> int:
        """Get user's current seed balance.
        
        Args:
            user_id (int): Discord user ID.
            
        Returns:
            int: User's seed balance.
        """
        return await get_user_balance(user_id)

    async def update_seeds(self, user_id: int, amount: int) -> None:
        """Update user's seeds with logging.
        
        Args:
            user_id (int): Discord user ID.
            amount (int): Amount to add (negative to subtract).
        """
        await get_or_create_user(user_id, f"User#{user_id}")
        balance_before = await get_user_balance(user_id)
        await add_seeds(user_id, amount)
        
        logger.info(
            f"[XIDACH] [SEED_UPDATE] user_id={user_id} change={amount} "
            f"before={balance_before} after={balance_before + amount}"
        )

    async def validate_bet(
        self,
        interaction: discord.Interaction,
        bet_amount: int,
        ephemeral: bool = True
    ) -> bool:
        """Validate bet amount and user balance.
        
        Args:
            interaction: Discord interaction.
            bet_amount: Amount to bet.
            ephemeral: Whether error messages are ephemeral.
            
        Returns:
            bool: True if bet is valid.
        """
        if bet_amount < MIN_BET:
            await interaction.response.send_message(
                f"❌ Tiền cược tối thiểu là **{MIN_BET}** hạt!",
                ephemeral=ephemeral
            )
            return False

        if bet_amount > MAX_BET:
            await interaction.response.send_message(
                f"❌ Tiền cược tối đa là **{MAX_BET:,}** hạt!",
                ephemeral=ephemeral
            )
            return False

        user_balance = await self.get_user_seeds(interaction.user.id)
        if user_balance < bet_amount:
            await interaction.response.send_message(
                f"❌ Bạn không đủ hạt!\nCần: **{bet_amount:,}** | Có: **{user_balance:,}**",
                ephemeral=ephemeral
            )
            return False

        return True

    # ==================== SOLO GAME LOGIC ====================

    async def _start_solo_game(
        self,
        ctx_or_interaction,
        bet_amount: int
    ) -> None:
        """Start a single-player Xi Dach game.
        
        Args:
            ctx_or_interaction: Command context or interaction.
            bet_amount: Amount to bet.
        """
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        table = None  # For cleanup on error
        
        if is_slash:
            interaction = ctx_or_interaction
            channel = interaction.channel
            user = interaction.user
            # CRITICAL: Defer FIRST before any async operations
            await interaction.response.defer()
        else:
            ctx = ctx_or_interaction
            channel = ctx.channel
            user = ctx.author

        try:
            # Validate bet amount
            if bet_amount < MIN_BET:
                msg = f"❌ Tiền cược tối thiểu là **{MIN_BET}** hạt!"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            if bet_amount > MAX_BET:
                msg = f"❌ Tiền cược tối đa là **{MAX_BET:,}** hạt!"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Check user balance
            user_balance = await self.get_user_seeds(user.id)
            if user_balance < bet_amount:
                msg = f"❌ Bạn không đủ hạt!\nCần: **{bet_amount:,}** | Có: **{user_balance:,}**"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Check for existing game in channel
            existing_table = game_manager.get_table(channel.id)
            if existing_table:
                msg = "❌ Kênh này đã có ván đang chơi! Chờ kết thúc trước."
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Create table
            table = game_manager.create_table(channel.id, user.id, is_solo=True)
            if not table:
                msg = "❌ Không thể tạo ván đấu!"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Deduct bet
            await self.update_seeds(user.id, -bet_amount)

            # Add player
            player = table.add_player(user.id, user.display_name, bet_amount)
            player.is_ready = True

            # Start game
            table.start_game()

            logger.info(
                f"[XIDACH] [SOLO_START] user={user.name} user_id={user.id} "
                f"bet={bet_amount} table_id={table.table_id}"
            )

            # Check for instant blackjack (Player OR Dealer)
            if player.status == PlayerStatus.BLACKJACK or table.dealer_type in (HandType.XI_BAN, HandType.XI_DACH):
                await self._handle_solo_blackjack(ctx_or_interaction, table, player, is_slash)
                return

            # Create game view
            view = SoloGameView(self, table, player, timeout=SOLO_TIMEOUT)
            
            # Create image
            players_data = [{
                'name': player.username,
                'cards': player.hand,
                'score': player.hand_value,
                'bet': player.bet
            }]
            img_bytes = await render_game_state_image(
                dealer_cards=table.dealer_hand,
                players_data=players_data,
                hide_dealer=True
            )
            file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
            
            # Create embed
            embed = create_solo_game_embed(table, player, hide_dealer=True)
            embed.set_image(url="attachment://solo_game.png")

            if is_slash:
                message = await interaction.followup.send(embed=embed, file=file, view=view)
            else:
                message = await ctx.send(embed=embed, file=file, view=view)

            table.message_id = message.id

        except Exception as e:
            logger.error(f"[XIDACH] [ERROR] Solo game error: {e}", exc_info=True)
            # Cleanup table on error
            if table and channel:
                game_manager.remove_table(channel.id)
            # Try to notify user
            try:
                msg = f"❌ Đã xảy ra lỗi: {str(e)}"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
            except Exception:
                pass

    async def _handle_solo_blackjack(
        self,
        ctx_or_interaction,
        table: Table,
        player: Player,
        is_slash: bool
    ) -> None:
        """Handle instant blackjack in solo game.
        
        Args:
            ctx_or_interaction: Command context or interaction.
            table: Game table.
            player: The player.
            is_slash: Whether this is a slash command.
        """
        # Reveal dealer's hand
        table.dealer_play()

        # Compare hands
        result, multiplier = compare_hands(player.hand, table.dealer_hand)
        payout = int(player.bet * multiplier)

        # Update seeds
        if payout > 0:
            await self.update_seeds(player.user_id, payout)

        # Create result embed
        embed = create_result_embed(table, player, result, payout)

        # Dealer Xi Dach Taunt
        if table.dealer_type in (HandType.XI_BAN, HandType.XI_DACH):
            if embed.description is None: embed.description = ""
            embed.description += "\n# Úi, lỡ bốc ra Xì Dách mất rồi. Xin lỗi cưng nha 🫦"

        # Render Result Image
        try:
             players_data = [{
                'name': player.username,
                'cards': player.hand,
                'score': player.hand_value,
                'bet': player.bet
            }]
             img_bytes = await render_game_state_image(
                dealer_cards=table.dealer_hand,
                players_data=players_data,
                hide_dealer=False
            )
             file = discord.File(io.BytesIO(img_bytes), filename="solo_result.png")
             embed.set_image(url="attachment://solo_result.png")
             
             if is_slash:
                 await ctx_or_interaction.followup.send(embed=embed, file=file)
             else:
                 await ctx_or_interaction.send(embed=embed, file=file)
        except Exception as e:
             logger.error(f"[XIDACH] Solo blackjack render error: {e}")
             if is_slash:
                 await ctx_or_interaction.followup.send(embed=embed)
             else:
                 await ctx_or_interaction.send(embed=embed)

        logger.info(
            f"[XIDACH] [SOLO_BLACKJACK] user_id={player.user_id} "
            f"result={result} payout={payout}"
        )

        # Cleanup
        game_manager.remove_table(table.channel_id)

    async def _update_solo_display(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player,
        view: "SoloGameView",
        finished: bool = False,
        hide_dealer: bool = True
    ) -> None:
        """Helper to update solo game display with image.
        
        Args:
            interaction: Discord interaction.
            table: Game table.
            player: Player.
            view: Game view.
            finished: Whether game is finished.
            hide_dealer: Whether to hide dealer's first card.
        """
        try:
             # Render image
            players_data = [{
                'name': player.username,
                'cards': player.hand,
                'score': player.hand_value,
                'bet': player.bet
            }]
            
            img_bytes = await render_game_state_image(
                dealer_cards=table.dealer_hand,
                players_data=players_data,
                hide_dealer=hide_dealer
            )
            file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
            
            # Create embed
            embed = create_solo_game_embed(table, player, hide_dealer=hide_dealer, finished=finished)
            embed.set_image(url="attachment://solo_game.png")
            
            # Update response
            if not interaction.response.is_done():
                 # Should not happen if deferred, but for safety
                await interaction.response.send_message(embed=embed, file=file, view=view)
            else:
                await interaction.edit_original_response(embed=embed, file=file, view=view)
                
        except Exception as e:
            logger.error(f"[XIDACH] Failed to update solo display: {e}")
            # Fallback
            embed = create_solo_game_embed(table, player, hide_dealer=hide_dealer, finished=finished)
            await interaction.edit_original_response(embed=embed, view=view)

    async def player_hit(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player
    ) -> None:
        """Handle player hit action.
        
        Args:
            interaction: Discord interaction.
            table: Game table.
            player: The player.
        """
        await interaction.response.defer()

        # Draw card
        card = table.deck.draw_one()
        player.add_card(card)

        logger.info(
            f"[XIDACH] [HIT] user_id={player.user_id} card={card} "
            f"total={player.hand_value}"
        )

        # Check for bust
        if player.is_bust:
            player.status = PlayerStatus.BUST
            await self._finish_solo_game(interaction, table, player)
            return

        # Check for Ngu Linh (5 cards <= 21)
        if len(player.hand) >= 5:
            player.status = PlayerStatus.STAND
            await self._finish_solo_game(interaction, table, player)
            return

        # Update display
        view = SoloGameView(self, table, player)
        await self._update_solo_display(interaction, table, player, view, hide_dealer=True)

    async def player_stand(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player
    ) -> None:
        """Handle player stand action."""
        await interaction.response.defer()
        player.status = PlayerStatus.STAND
        await self._finish_solo_game(interaction, table, player)

    async def player_double(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player
    ) -> None:
        """Handle player double down action."""
        # Check balance for doubling
        user_balance = await self.get_user_seeds(player.user_id)
        if user_balance < player.bet:
            await interaction.response.send_message(
                f"❌ Bạn không đủ hạt để gấp đôi!\nCần: **{player.bet:,}** | Có: **{user_balance:,}**",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Deduct additional bet
        await self.update_seeds(player.user_id, -player.bet)
        player.bet *= 2
        player.is_doubled = True

        # Draw one card and stand
        card = table.deck.draw_one()
        player.add_card(card)
        
        # Determine status
        if player.is_bust:
            player.status = PlayerStatus.BUST
        else:
            player.status = PlayerStatus.STAND
            
        # Finish game
        await self._finish_solo_game(interaction, table, player)

        logger.info(
            f"[XIDACH] [DOUBLE] user_id={player.user_id} new_bet={player.bet} "
            f"card={card} total={player.hand_value}"
        )

        # Auto stand after double
        if not player.is_bust:
            player.status = PlayerStatus.STAND

        await self._finish_solo_game(interaction, table, player)

    # ==================== MULTI-PLAYER ACTION HANDLERS ====================
    # These methods handle actions in multiplayer and resend message with new card image

    async def player_hit_multi(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player,
        view: "MultiGameView"
    ) -> None:
        """Handle player hit in multiplayer - resends message with new card image."""
        await interaction.response.defer()

        # Draw card
        card = table.deck.draw_one()
        player.add_card(card)

        logger.info(
            f"[XIDACH] [HIT] user_id={player.user_id} card={card} "
            f"total={player.hand_value}"
        )

        # Check for bust
        if player.is_bust:
            player.status = PlayerStatus.BUST

        # Check for Ngu Linh (5 cards <= 21)
        if len(player.hand) >= 5 and not player.is_bust:
            player.status = PlayerStatus.STAND

        # ALWAYS resend message to show the new card (even if bust/ngu linh)
        await self._resend_turn_message(interaction, table, player, view)


    async def player_stand_multi(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player,
        view: "MultiGameView"
    ) -> None:
        """Handle player stand in multiplayer."""
        # Validate Minimum Points (16) Rule
        if player.hand_value < 16 and player.hand_type == HandType.NORMAL:
            await interaction.response.send_message(
                "⚠️ **Chưa đủ tuổi!** Bạn cần tối thiểu **16 điểm** để Dằn bài.",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        player.status = PlayerStatus.STAND
        # Message will be updated by the turn loop

    async def player_double_multi(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player,
        view: "MultiGameView"
    ) -> None:
        """Handle player double in multiplayer - resends message with new card image."""
        try:
            # Check balance for doubling
            user_balance = await self.get_user_seeds(player.user_id)
            if user_balance < player.bet:
                await interaction.response.send_message(
                    f"❌ Bạn không đủ hạt để gấp đôi!\nCần: **{player.bet:,}** | Có: **{user_balance:,}**",
                    ephemeral=True
                )
                return

            await interaction.response.defer()

            # Deduct additional bet
            await self.update_seeds(player.user_id, -player.bet)
            player.bet *= 2
            player.is_doubled = True

            # Draw one card and stand
            card = table.deck.draw_one()
            player.add_card(card)

            logger.info(
                f"[XIDACH] [DOUBLE] user_id={player.user_id} new_bet={player.bet} "
                f"card={card} total={player.hand_value}"
            )

            # Auto stand after double (if not bust)
            # Even if bust, we want to finish turn logic.
            # But add_card sets BUST status automatically if > 21.
            # So we only set STAND if playing.
            if player.status == PlayerStatus.PLAYING:
                 player.status = PlayerStatus.STAND

            # Delete old message and send new one with updated card image
            await self._resend_turn_message(interaction, table, player, view)
            
        except Exception as e:
            logger.error(f"[XIDACH] [DOUBLE_ERROR] {e}", exc_info=True)
            try:
                 await interaction.followup.send("❌ Có lỗi xảy ra khi gấp đôi.", ephemeral=True)
            except: pass

    async def _resend_turn_message(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player,
        view: "MultiGameView"
    ) -> None:
        """Helper to delete old turn message and send new one with updated card image."""
        import io
        import time
        
        TURN_TIMEOUT = 30  # Constant for turn duration
        
        logger.info(f"[XIDACH] [RESEND_START] user_id={player.user_id} cards={len(player.hand)}")
        
        # Delete old message (use table's reference)
        old_msg = table.current_turn_msg
        if old_msg:
            try:
                await old_msg.delete()
                logger.info(f"[XIDACH] [RESEND_DELETE_OK] old_msg_id={old_msg.id}")
            except discord.NotFound:
                logger.info("[XIDACH] [RESEND_DELETE] old_msg not found (already deleted)")
            except discord.HTTPException as e:
                logger.warning(f"[XIDACH] [RESEND_DELETE_ERROR] {e}")
        
        try:
            # Render new card image
            logger.info(f"[XIDACH] [RESEND_RENDER_START] Calling render_hand_image for {player.username}")
            try:
                player_hand_img = await render_hand_image(player.hand, player.username)
                logger.info(f"[XIDACH] [RESEND_RENDER_DONE] Got {len(player_hand_img)} bytes")
            except Exception as e:
                logger.error(f"[XIDACH] [RESEND_RENDER_FAIL] Error rendering image: {e}", exc_info=True)
                raise e
                
            hand_file = discord.File(io.BytesIO(player_hand_img), filename="hand.png")
            
            # Check if player is finished (Bust, Stand, Blackjack, etc)
            is_finished = player.status != PlayerStatus.PLAYING
            
            # Determine remaining time
            remaining = TURN_TIMEOUT if not is_finished else 0
            
            # Create new embed (pass finished flag)
            new_embed = self._create_turn_embed(player, remaining, finished=is_finished, is_multiplayer=True)
            new_embed.set_image(url="attachment://hand.png")
            
            # Create NEW view
            new_view = MultiGameView(self, table, channel=interaction.channel)
            
            # If finished, disable buttons and set content
            if is_finished:
                for item in new_view.children:
                    if hasattr(item, "disabled"):
                        item.disabled = True
                        
                if player.status == PlayerStatus.BUST:
                    content_str = f"💥 **<@{player.user_id}>** ĐÃ QUẮC (BÙ)!"
                elif player.hand_type == HandType.NGU_LINH:
                    content_str = f"🐉 **<@{player.user_id}>** ĐÃ ĐẠT NGŨ LINH!"
                elif player.status == PlayerStatus.BLACKJACK:
                    content_str = f"🎰 **<@{player.user_id}>** XÌ DÁCH!"
                elif player.status == PlayerStatus.STAND:
                    content_str = f"✋ **<@{player.user_id}>** ĐÃ DẰN BÀI."
                else:
                    content_str = f"✅ **<@{player.user_id}>** Hoàn thành lượt."
            else:
                content_str = f"🎮 **LƯỢT CỦA** <@{player.user_id}>"
                # Check if can double, if not disable the button
                if not player.can_double:
                    for item in new_view.children:
                        if hasattr(item, "custom_id") and item.custom_id == "btn_double_multi":
                            item.disabled = True
            
            # Send new message with NEW view
            new_msg = await interaction.channel.send(
                content=content_str,
                embed=new_embed,
                view=new_view,
                file=hand_file
            )
            
            logger.info(f"[XIDACH] [RESEND_SENT] new_msg_id={new_msg.id}")
            
            # Update TABLE shared state - countdown loop checks these!
            table.current_turn_msg = new_msg
            table.turn_action_timestamp = time.time()  # Signal to reset timer
            
        except Exception as e:
            logger.error(f"[XIDACH] Failed to resend turn message: {e}", exc_info=True)

    async def _finish_solo_game(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player
    ) -> None:
        """Finish solo game and calculate results with animation."""
        
        # 1. Reveal Dealer's hand
        table.dealer_play() # Update internal status (drawing handled manually below)
        
        # Initial Reveal Animation
        try:
            players_data = [{
                'name': player.username,
                'cards': player.hand,
                'score': player.hand_value,
                'bet': player.bet
            }]
            
            # Render Revealed
            img_bytes = await render_game_state_image(
                dealer_cards=table.dealer_hand,
                players_data=players_data,
                hide_dealer=False
            )
            file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
            
            embed = create_solo_game_embed(table, player, hide_dealer=False, finished=True)
            embed.set_image(url="attachment://solo_game.png")
            embed.set_field_at(1, name="📋 Trạng thái", value="🔍 Nhà cái đang lật bài...", inline=True)
            
            await interaction.edit_original_response(embed=embed, file=file, view=None)
            await asyncio.sleep(2)
            
            # Dealer Smart Loop
            while True:
                # Decide next move
                action, reason = table.get_dealer_decision()
                
                if action == "stand":
                    break

                # Trash Talk Logic
                trash_talk = None
                
                # S1: Check if opponent has Xi Dach (In Solo, opponent is 'player')
                if player.hand_type == HandType.XI_DACH:
                    is_initial_small = len(table.dealer_hand) == 2 and table.dealer_value < 10
                    is_fourth_card = len(table.dealer_hand) >= 4
                    if is_initial_small or is_fourth_card:
                         trash_talk = "Xì dách của cưng chưa chắc to hơn Ngũ Linh của chị đâu 💅"

                # Priority 2: Standard AI Trash Talk
                if not trash_talk:
                    if reason == "desperate_initial":
                         trash_talk = random.choice([
                             "30 chưa phải là Tết đâu. NHÌN!!! 👀",
                             "Tưởng 2 lá là ăn được tao à? Mơ đi cưng! 💤",
                             "Dằn non à? Để anh dạy chú thế nào là bản lĩnh! 💪"
                         ])
                    elif reason == "desperate_drawn":
                         trash_talk = random.choice([
                             "Ái chà! Tụi mày rút căng thế. Buộc tao phải tất tay với chúng mày rồi! 😈",
                             "Thế này thì ép Nhà Cái quá... Thêm lá nữa! 🔥",
                             "Chơi lớn luôn nè! Sợ gì! 💣"
                         ])
                    elif reason == "ngu_linh_attempt":
                         trash_talk = random.choice([
                             "Ngũ Linh hay là Quắc đây... Chơi luôn! 🎲",
                             "Không phục à? Để tao rút thêm lá nữa cho tâm phục khẩu phục! 😤",
                             "4 lá chưa đủ đô, lá thứ 5 phán quyết! 🐉"
                         ])

                if trash_talk:
                     # Update embed with trash talk
                     embed.set_field_at(1, name="📋 Trạng thái", value=f"💬 {trash_talk}", inline=True)
                     await interaction.edit_original_response(embed=embed, view=None)
                     await asyncio.sleep(5.0)

                # Draw card
                new_card = table.deck.draw_one()
                table.dealer_hand.append(new_card)
                
                # Render Drawing State
                img_bytes = await render_game_state_image(
                    dealer_cards=table.dealer_hand,
                    players_data=players_data,
                    hide_dealer=False
                )
                file = discord.File(io.BytesIO(img_bytes), filename="solo_game.png")
                
                embed.set_image(url="attachment://solo_game.png")
                embed.set_field_at(1, name="📋 Trạng thái", value="🤖 Nhà cái đang rút bài...", inline=True)
                
                await interaction.edit_original_response(embed=embed, file=file, view=None)
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"[XIDACH] Dealer animation error: {e}")

        # Final Result
        # Compare hands
        result, multiplier = compare_hands(player.hand, table.dealer_hand)
        payout = int(player.bet * multiplier)

        # Update seeds
        if payout > 0:
            await self.update_seeds(player.user_id, payout)

        # Create result embed
        embed = create_result_embed(table, player, result, payout)
        
        # --- TRASH TALK (RESULTS) ---
        taunt = ""
        if result == "lose" and table.dealer_type not in (HandType.XI_DACH, HandType.XI_BAN):
            # Dealer wins NORMAL hand
            
            # S2: Self-Sabotage Check (Had Xi Dach 21 but hit?)
            had_xi_dach_initially = False
            if len(player.hand) > 2:
                # We already imported calculate_hand_value
                initial_sum = calculate_hand_value(player.hand[:2])
                if initial_sum == 21:
                    had_xi_dach_initially = True
            
            if had_xi_dach_initially:
                 taunt = "\n# Con gà này win thì không chịu, cứ thích phải thua cơ 🐔"
            elif player.hand_value < 16 and player.hand_type == HandType.NORMAL:
                taunt = "\n# Con gà này chưa ĐỦ TUỔI với anh 🐔"
            elif player.hand_value >= 16:
                taunt = random.choice([
                             "Con vợ này gà thế nhờ 🤪",
                             "Hehe ăn may thôi 🤭",
                             "Tưởng thế nào, ra là cũng chỉ có thế 🤡"
                         ])
        elif result == "win" and player.hand_type == HandType.NGU_LINH:
             taunt = random.choice([
                 "\n# Ngũ Linh cơ à? Ghê đấy! 🤐",
                 "\n# Ăn rùa được ván Ngũ Linh thôi, đừng gáy! 🐢",
                 "\n# Trời độ mày ván này đấy! ⛈️",
                 "\n# Hên thôi, lần sau chết với bà! 🔮"
             ])
        
        if taunt:
            if embed.description is None: embed.description = ""
            embed.description += taunt

        # "Ngủ luôn" logic for Dealer
        if table.dealer_value > 21 and len(table.dealer_hand) >= 5:
             if embed.description is None: embed.description = ""
             embed.description += f"\n# 😴 Và thế là **Nhà Cái** đã ngủ luôn!"

        # Render Final Image
        try:
             players_data = [{
                'name': player.username,
                'cards': player.hand,
                'score': player.hand_value,
                'bet': player.bet
            }]
             img_bytes = await render_game_state_image(
                dealer_cards=table.dealer_hand,
                players_data=players_data,
                hide_dealer=False
            )
             file = discord.File(io.BytesIO(img_bytes), filename="solo_game_final.png")
             embed.set_image(url="attachment://solo_game_final.png")
             
             await interaction.edit_original_response(embed=embed, file=file, view=None)
        except Exception as e:
             logger.error(f"[XIDACH] Final render error: {e}")
             await interaction.edit_original_response(embed=embed, view=None)

        logger.info(
            f"[XIDACH] [SOLO_FINISH] user_id={player.user_id} "
            f"result={result} payout={payout} multiplier={multiplier}"
        )

        # Cleanup
        game_manager.remove_table(table.channel_id)

    # ==================== MULTIPLAYER GAME LOGIC ====================

    async def _start_multiplayer(self, ctx_or_interaction) -> None:
        """Start a multiplayer Xi Dach lobby.
        
        Args:
            ctx_or_interaction: Command context or interaction.
        """
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        table = None  # For cleanup on error
        channel = None
        
        if is_slash:
            interaction = ctx_or_interaction
            channel = interaction.channel
            user = interaction.user
            await interaction.response.defer()
        else:
            ctx = ctx_or_interaction
            channel = ctx.channel
            user = ctx.author

        try:
            # Check for existing game
            existing_table = game_manager.get_table(channel.id)
            if existing_table:
                msg = "❌ Kênh này đã có sòng đang mở! Chờ kết thúc trước."
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Create table
            table = game_manager.create_table(channel.id, user.id, is_solo=False)
            if not table:
                msg = "❌ Không thể mở sòng!"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Add host as spectator
            host_player = table.add_player(user.id, user.display_name)
            host_player.status = PlayerStatus.SPECTATING

            logger.info(
                f"[XIDACH] [LOBBY_OPEN] host={user.name} host_id={user.id} "
                f"table_id={table.table_id}"
            )

            # Create lobby view
            view = LobbyView(self, table, timeout=LOBBY_DURATION + 5)
            embed = create_lobby_embed(table, LOBBY_DURATION)

            if is_slash:
                message = await interaction.followup.send(embed=embed, view=view)
            else:
                message = await ctx.send(embed=embed, view=view)

            table.message_id = message.id

            # Countdown loop - update every second (like turn countdown)
            start_time = time.time()
            last_update = LOBBY_DURATION

            while time.time() - start_time < LOBBY_DURATION:
                elapsed = time.time() - start_time
                remaining = LOBBY_DURATION - int(elapsed)

                # Update every second for smooth countdown
                # Silent Countdown (Optimized)
                # Client-local Timestamp handles visual countdown
                # Only check for timeout here.
                await asyncio.sleep(1)
                # Check if game should start early
                if self._should_start_game(table):
                    break

                await asyncio.sleep(0.5)            # LOBBY CLOSED / STARTING
            # Final update to remove timer and show "Starting..."
            # Lock status to prevent race conditions from reviving the timer
            # Lock status to prevent race conditions from reviving the timer
            table.status = TableStatus.BETTING
            
            # AUTO-CLEANUP: Delete all ephemeral betting UIs
            for p in table.players.values():
                if p.interaction:
                    try:
                        await p.interaction.delete_original_response()
                    except:
                        pass
            

            try:
                # Disable buttons
                for item in view.children:
                    item.disabled = True
                    
                embed = create_lobby_embed(table, time_remaining=None)
                await message.edit(embed=embed, view=view)
            except:
                pass

            # AUTO-READY: Mark players who have bet but forgot to press ready
            for player in table.players.values():
                if player.bet > 0 and not player.is_ready:
                    player.is_ready = True
                    logger.info(f"[XIDACH] [AUTO_READY] user_id={player.user_id} bet={player.bet}")

            # Check if enough players to start (only those with bets)
            ready_count = sum(1 for p in table.players.values() if p.is_ready and p.bet > 0)
            if ready_count < 1:
                await channel.send("⚠️ Không có ai đặt cược! Sòng đã đóng.")
                logger.info(f"[XIDACH] [LOBBY_CANCELLED] no_betters table_id={table.table_id}")
                game_manager.remove_table(channel.id)
                return

            # Start the game
            await self._start_multi_game(channel, table)

        except Exception as e:
            logger.error(f"[XIDACH] [ERROR] Multiplayer game error: {e}", exc_info=True)
            # Cleanup table on error
            if channel:
                game_manager.remove_table(channel.id)
            # Try to notify user
            try:
                msg = f"❌ Đã xảy ra lỗi: {str(e)}"
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
            except Exception:
                pass

    def _should_start_game(self, table: Table) -> bool:
        """Check if multiplayer game should start early.
        
        Game starts early ONLY if ALL joined players are ready.
        If any player has joined (WAITING) but not ready, we must wait.
        
        Args:
            table: Game table.
            
        Returns:
            bool: True if game should start.
        """
        ready_count = table.ready_players_count
        
        # Count players who have joined (WAITING) but NOT ready yet
        waiting_not_ready = sum(
            1 for p in table.players.values()
            if p.status == PlayerStatus.WAITING and not p.is_ready
        )
        
        # If any player has joined but not ready, DON'T start yet
        if waiting_not_ready > 0:
            return False
        
        # Need at least 1 ready player to start
        if ready_count < 1:
            return False
        
        # All joined players are ready - can start!
        return True

    async def player_join_lobby(
        self,
        interaction: discord.Interaction,
        table: Table
    ) -> None:
        """Handle player joining the lobby.
        
        Args:
            interaction: Discord interaction.
            table: Game table.
        """
        user_id = interaction.user.id

        # Check if already in table
        if user_id in table.players:
            player = table.players[user_id]
            
                # If player was spectating (host), allow joining
            if player.status == PlayerStatus.SPECTATING:
                # CHECK LIMIT before joining
                current_players = sum(1 for p in table.players.values() if p.status != PlayerStatus.SPECTATING)
                if current_players >= MAX_PLAYERS:
                    await interaction.response.send_message(
                        f"❌ Sòng đã đủ {MAX_PLAYERS} người chơi! Không thể tham gia.",
                        ephemeral=True
                    )
                    return

                player.status = PlayerStatus.WAITING
                player.interaction = interaction  # Save interaction for cleanup
                logger.info(f"[XIDACH] [PLAYER_JOIN] host/spectator joining: user_id={user_id}")
                # Fall through to send betting view...
                
            # If already joined (WAITING/READY), block duplicate view
            else:
                 await interaction.response.send_message(
                    "❌ Bạn đã tham gia rồi! Vui lòng sử dụng bảng cược cũ.",
                    ephemeral=True
                )
                 return

        # Add new player
        # CHECK LIMIT before joining
        current_players = sum(1 for p in table.players.values() if p.status != PlayerStatus.SPECTATING)
        if current_players >= MAX_PLAYERS:
            await interaction.response.send_message(
                f"❌ Sòng đã đủ {MAX_PLAYERS} người chơi! Không thể tham gia.",
                ephemeral=True
            )
            return
        player = table.add_player(user_id, interaction.user.display_name)
        player.status = PlayerStatus.WAITING  # WAITING = Đã tham gia (not SPECTATING)
        player.interaction = interaction  # Save interaction for cleanup
        game_manager.add_user_to_table(user_id, table.channel_id)

        # Show betting view
        view = MultiBetView(self, table, player)
        await interaction.response.send_message(
            f"🎮 Chào mừng đến sòng!\n"
            f"💰 Đặt cược bằng cách nhấn các nút bên dưới.\n"
            f"✅ Nhấn **Sẵn Sàng** khi hoàn tất.",
            view=view,
            ephemeral=True
        )

        logger.info(
            f"[XIDACH] [PLAYER_JOIN] user={interaction.user.name} "
            f"user_id={user_id} table_id={table.table_id}"
        )

        # UPDATE LOBBY EMBED to show new player joined
        try:
            channel = interaction.channel
            if table.message_id and channel:
                lobby_msg = await channel.fetch_message(table.message_id)
                remaining = _get_lobby_remaining(table)
                embed = create_lobby_embed(table, remaining)
                await lobby_msg.edit(embed=embed)
        except discord.NotFound:
            pass
        except Exception as e:
            logger.error(f"[XIDACH] Failed to update lobby after join: {e}")

    async def process_bet(
        self,
        interaction: discord.Interaction,
        table: Table,
        user_id: int,
        amount: int
    ) -> None:
        """Process a bet from a player.
        
        Args:
            interaction: Discord interaction.
            table: Game table.
            user_id: Player's user ID.
            amount: Bet amount to add.
        """
        # Lock check (Robust Liveness Check)
        try:
            current_table = game_manager.get_table(table.channel_id)
            if current_table is not table or table.status != TableStatus.LOBBY:
                 # START_CHANGE: User requested DELETE instead of EDIT
                 try:
                     await interaction.message.delete()
                 except:
                     pass
                 # END_CHANGE
                 await interaction.response.send_message(
                     "❌ Đã hết thời gian cược!", ephemeral=True
                 )
                 return
        except Exception as e:
            logger.error(f"[XIDACH] Lock Check Error: {e}")
            try:
                await interaction.message.delete()
            except:
                pass
            await interaction.response.send_message("❌ Sòng đã đóng!", ephemeral=True)
            return

        player = table.players.get(user_id)
        if not player:
            await interaction.response.send_message(
                "❌ Bạn chưa tham gia sòng!", ephemeral=True
            )
            return

        # Check balance
        user_balance = await self.get_user_seeds(user_id)
        new_total = player.bet + amount

        if new_total > user_balance:
            await interaction.response.send_message(
                f"❌ Không đủ hạt!\n"
                f"Đang cược: {player.bet:,} | Thêm: {amount:,} | Có: {user_balance:,}",
                ephemeral=True
            )
            return



        # Add bet
        player.bet = new_total

        # EDIT the betting message with updated bet amount instead of sending new message
        view = MultiBetView(self, table, player)
        # Use response.edit_message for atomic update
        await interaction.response.edit_message(
            content=f"💰 **Đặt cược:**\n✅ Đã thêm **{amount:,} hạt💰! Hiện tại: **{player.bet:,} hạt💰\n"
                    f"Nhấn các nút để cộng thêm tiền cược.",
            view=view
        )

        logger.info(
            f"[XIDACH] [BET_ADD] user_id={user_id} amount={amount} "
            f"total={player.bet}"
        )

        # UPDATE LOBBY EMBED to reflect "Đã tham gia" status
        try:
            channel = interaction.channel
            if table.message_id and channel:
                lobby_msg = await channel.fetch_message(table.message_id)
                remaining = _get_lobby_remaining(table)
                embed = create_lobby_embed(table, remaining)
                await lobby_msg.edit(embed=embed)
        except discord.NotFound:
            pass
        except Exception as e:
            logger.error(f"[XIDACH] Failed to update lobby embed after bet: {e}")

    async def player_ready(
        self,
        interaction: discord.Interaction,
        table: Table,
        player: Player
    ) -> None:
        """Handle player ready action.
        
        Args:
            interaction: Discord interaction.
            table: Game table.
            player: The player.
        """
        # Lock check (Robust Liveness Check)
        try:
            current_table = game_manager.get_table(table.channel_id)
            if current_table is not table or table.status != TableStatus.LOBBY:
                 # START_CHANGE: User requested DELETE instead of EDIT
                 try:
                     await interaction.message.delete()
                 except:
                     pass
                 # END_CHANGE
                 await interaction.response.send_message(
                     "❌ Không thể sẵn sàng do đã quá thời gian quy định!", ephemeral=True
                 )
                 return
        except Exception as e:
            logger.error(f"[XIDACH] Lock Check Error: {e}")
            try:
                await interaction.message.delete()
            except:
                pass
            await interaction.response.send_message("❌ Sòng đã đóng!", ephemeral=True)
            return

        # Check if already ready
        if player.is_ready:
            await interaction.response.send_message(
                "✅ Bạn đã sẵn sàng rồi!", ephemeral=True
            )
            return

        if player.bet <= 0:
            await interaction.response.send_message(
                "❌ Bạn cần đặt cược trước khi sẵn sàng!",
                ephemeral=True
            )
            return

        # Validate and deduct bet
        user_balance = await self.get_user_seeds(player.user_id)
        if user_balance < player.bet:
            await interaction.response.send_message(
                f"❌ Không đủ hạt! Có: {user_balance:,} | Cược: {player.bet:,}",
                ephemeral=True
            )
            return

        # Deduct bet
        await self.update_seeds(player.user_id, -player.bet)
        player.is_ready = True
        player.status = PlayerStatus.WAITING

        # Confirm readiness - edit message to remove buttons effectively (or show ready state)
        # Actually user might want to un-ready? No, flow is one-way.
        # But for Ready button, we should just reply "Success".
        # Wait, if we use edit_message, we replace the Betting UI with "You are ready"?
        # No, the Betting UI should remain for OTHER actions (if any)? 
        # But this is EPHEMERAL. It is specific to the user.
        # If user is ready, they don't need to bet anymore.
        # So replacing the Betting UI with "✅ Ready" is GOOD UX.
        await interaction.response.edit_message(
            content=f"✅ Bạn đã sẵn sàng với **{player.bet:,}** hạt!\n(Vui lòng chờ người chơi khác)",
            view=None
        )

        logger.info(
            f"[XIDACH] [PLAYER_READY] user_id={player.user_id} "
            f"bet={player.bet} table_id={table.table_id}"
        )

        # UPDATE LOBBY EMBED to reflect new status
        try:
            channel = interaction.channel
            if table.message_id and channel:
                lobby_msg = await channel.fetch_message(table.message_id)
                # Calculate remaining time approximately (use table creation time if available)
                if table.status == TableStatus.LOBBY:
                    remaining = _get_lobby_remaining(table)
                else:
                    remaining = None
                    
                embed = create_lobby_embed(table, remaining)
                await lobby_msg.edit(embed=embed)
        except discord.NotFound:
            pass
        except Exception as e:
            logger.error(f"[XIDACH] Failed to update lobby embed: {e}")

    async def _start_multi_game(
        self,
        channel: discord.TextChannel,
        table: Table
    ) -> None:
        """Start the multiplayer game.
        
        Args:
            channel: Discord channel.
            table: Game table.
        """
        TURN_TIMEOUT = 30  # 30 seconds per turn

        try:
            # Start game
            table.start_game()

            logger.info(
                f"[XIDACH] [MULTI_START] table_id={table.table_id} "
                f"players={len(table._turn_order)}"
            )
            
            # REFUND players who bet but are not in turn order (race condition fix)
            # This happens when player bets at the exact moment lobby closes
            for uid, player in table.players.items():
                if player.bet > 0 and uid not in table._turn_order:
                    # Refund their bet
                    await self.update_seeds(uid, player.bet)
                    logger.warning(
                        f"[XIDACH] [REFUND_RACE_CONDITION] user_id={uid} "
                        f"bet={player.bet} (not in turn order)"
                    )
                    await channel.send(
                        f"⚠️ <@{uid}> đặt cược quá muộn! Đã hoàn **{player.bet:,} HẠT💰** 🌻",
                        delete_after=10
                    )
                    player.bet = 0  # Clear bet to avoid confusion

            # CARD DEALING ANIMATION
            deal_msg = await channel.send("## 🎴 **CHIA BÀI...**") # Increased size
            
            # Animation frames
            frames = [
                "## 🎴 ━━━ **CHIA BÀI** ━━━ 🎴",
                "## 🃏 ━━━ **CHIA BÀI** ━━━ 🃏",
                "## 🎴 ━ Chia cho Nhà Cái... ━ 🎴",
                "## 🃏 ━ Chia cho Người chơi... ━ 🃏"
            ]
            
            for frame in frames:
                await asyncio.sleep(0.4)
                try:
                    await deal_msg.edit(content=frame)
                except discord.NotFound:
                    break
            
            await asyncio.sleep(0.3)
            await deal_msg.delete()

            # Send overview embed with IMAGE
            try:
                # Prepare data for renderer
                players_data = []
                for uid in table._turn_order:
                    p = table.players[uid]
                    players_data.append({
                        'name': p.username,
                        'cards': p.hand,
                        'score': p.hand_value,
                        'bet': p.bet
                    })

                # Render image
                logger.info(f"[XIDACH] [OVERVIEW_RENDER] table_id={table.table_id}")
                img_bytes = await render_game_state_image(
                    dealer_cards=table.dealer_hand,
                    players_data=players_data,
                    hide_dealer=True
                )
                
                # Create file and update embed
                file = discord.File(io.BytesIO(img_bytes), filename="game_state.png")
                overview_embed = self._create_overview_embed(table, hide_dealer=True)
                overview_embed.set_image(url="attachment://game_state.png")
                
                overview_msg = await channel.send(embed=overview_embed, file=file)
            except Exception as e:
                logger.error(f"[XIDACH] [OVERVIEW_FAIL] {e}", exc_info=True)
                # Fallback to text only
                overview_embed = self._create_overview_embed(table, hide_dealer=True)
                overview_msg = await channel.send(embed=overview_embed)

            # CHECK DEALER INSTANT WIN (Xi Ban / Xi Dach)
            # If dealer has Xi Ban or Xi Dach, game ends immediately (unless player also has it, checked in calc)
            if table.dealer_type in [HandType.XI_BAN, HandType.XI_DACH]:
                logger.info(f"[XIDACH] [DEALER_INSTANT_WIN] type={table.dealer_type}")
                await channel.send(
                    f"# 🎰 **NHÀ CÁI CÓ {get_hand_description(table.dealer_type)}**!\n" # Increased to H1
                    f"## Úi, lỡ bốc ra Xì Dách mất rồi. Xin lỗi cưng nha =)) 🫦", # Increased to H2
                )
                # Skip turn loop completely
                table.status = TableStatus.FINISHED
            
            # Process turns ONLY if game not finished (Dealer didn't win instantly)
            if table.status != TableStatus.FINISHED:
                # Process each player's turn with SEPARATE MESSAGES
                while table.current_player:
                    current = table.current_player

                    # Check for instant blackjack - skip turn
                    # Check for instant blackjack (Thắng Trắng) - show hand and skip turn
                    if current.status == PlayerStatus.BLACKJACK:
                        # Render hand for proof
                        player_hand_img = await render_hand_image(current.hand, current.username)
                        hand_file = discord.File(io.BytesIO(player_hand_img), filename="hand.png")
                        
                        desc = get_hand_description(current.hand_type)
                        await channel.send(
                            f"✨ <@{current.user_id}> có **{desc}**! (Thắng trắng)",
                            file=hand_file,
                            delete_after=15
                        )
                        table.next_player()
                        continue


                    # Create TURN-SPECIFIC embed with card image

                    
                    # Render current player's hand as image
                    player_hand_img = await render_hand_image(current.hand, current.username)
                    hand_file = discord.File(io.BytesIO(player_hand_img), filename="hand.png")
                    
                    turn_embed = self._create_turn_embed(current, TURN_TIMEOUT, is_multiplayer=True)
                    turn_embed.set_image(url="attachment://hand.png")
                    
                    # Create view first (without turn_msg)
                    turn_view = MultiGameView(self, table, channel=channel)
                    
                    turn_msg = await channel.send(
                        content=f"🎮 **LƯỢT CỦA** <@{current.user_id}>",
                        embed=turn_embed,
                        view=turn_view,
                        file=hand_file
                    )
                    
                    # Set turn_msg reference in both view AND table (shared state)
                    turn_view.turn_msg = turn_msg
                    table.current_turn_msg = turn_msg
                    table.turn_action_timestamp = time.time()

                    # Countdown loop with per-second updates
                    start_time = time.time()
                    last_countdown = TURN_TIMEOUT
                    last_action_time = table.turn_action_timestamp  # Track via TABLE (shared state)

                    while (
                        current.status == PlayerStatus.PLAYING
                        and time.time() - start_time < TURN_TIMEOUT
                    ):
                        # Check if player took an action (hit) - reset timer via TABLE
                        if table.turn_action_timestamp > last_action_time:
                            start_time = time.time()  # Reset timer
                            last_action_time = table.turn_action_timestamp
                            last_countdown = TURN_TIMEOUT
                            # Update turn_msg reference from TABLE (may have changed after hit)
                            turn_msg = table.current_turn_msg
                        
                        elapsed = time.time() - start_time
                        remaining = TURN_TIMEOUT - int(elapsed)

                        # Silent Timeout Watcher (Optimized)
                        # We do NOT edit the message every second anymore.
                        # The message uses <t:timestamp:R> for client-side countdown.

                        # Only update if remaining changed significantly (e.g. for internal logic)
                        # But actually we just need to check if remaining <= 0
                        
                        last_countdown = remaining
                        
                        await asyncio.sleep(1) # Check every 1s is enough

                        await asyncio.sleep(0.5)

                    # Auto-stand on timeout
                    if current.status == PlayerStatus.PLAYING:
                        current.status = PlayerStatus.STAND
                        await channel.send(
                            f"⏰ **<@{current.user_id}>** hết thời gian! Tự động **Dằn**!"
                        )

                    # Disable turn message buttons
                    for item in turn_view.children:
                        item.disabled = True
                    try:
                        final_turn_embed = self._create_turn_embed(current, 0, finished=True, is_multiplayer=True)
                        await turn_msg.edit(embed=final_turn_embed, view=turn_view)
                    except discord.NotFound:
                        pass

                    # If player finished turn early (Bust/Blackjack/Stand), wait for them to see result
                    if current.status != PlayerStatus.PLAYING:
                        await asyncio.sleep(5)

                    # Cleanup old turn message
                    # User Request: Keep "Bust/Ngủ luôn" messages
                    try:
                        if table.current_turn_msg:
                            if current.status == PlayerStatus.BUST:
                                # Keep message for Bust/Ngủ luôn
                                pass 
                            else:
                                await table.current_turn_msg.delete()
                    except:
                        pass
                    
                    table.next_turn()
                    
                    # Update overview
                    overview_embed = self._create_overview_embed(table, hide_dealer=True)
                    try:
                        await overview_msg.edit(embed=overview_embed)
                    except:
                        pass

                await asyncio.sleep(1)

            # Dealer's turn
            # Dealer's turn - Async Animation
            table.dealer_play() # Sets status
            
            # --- DEALER TURN MESSAGE SETUP ---
            # 1. Reveal Dealer's hidden card message
            try:
                # Render Dealer Hand (Revealed)
                dealer_img = await render_hand_image(table.dealer_hand, "Nhà Cái")
                hand_file = discord.File(io.BytesIO(dealer_img), filename="dealer_hand.png")
                
                # Create Dealer Embed
                embed = discord.Embed(
                    title="🎮 **LƯỢT CỦA NHÀ CÁI**",
                    color=discord.Color.gold()
                )
                embed.set_image(url="attachment://dealer_hand.png")
                embed.add_field(name="📊 Điểm", value=f"**{table.dealer_value}**", inline=True)
                embed.add_field(name="📋 Trạng thái", value="🔍 Đang lật bài...", inline=True)
                
                # Send Dealer Message
                dealer_msg = await channel.send(embed=embed, file=hand_file)
                await asyncio.sleep(2) # Pause for suspense
            except Exception as e:
                logger.error(f"[XIDACH] Failed to send dealer reveal: {e}")
                dealer_msg = None

            # 2. Dealer Smart Loop
            while True:
                # Decide next move
                action, reason = table.get_dealer_decision()
                
                if action == "stand":
                    break

                # Trash Talk Logic
                trash_talk = None
                
                # S1: Check if any opponent has Xi Dach
                opponent_has_xidach = any(
                    p.hand_type == HandType.XI_DACH 
                    for p in table.players.values() 
                    if p.bet > 0
                )
                
                # Priority 1: Taunt Xi Dach Player (4th card or Small Initial)
                # Ensure we only say this once per game effectively (random chance or strict)
                # Condition: Opponent has Xi Dach AND (Dealer hand size >= 4 OR (Initial < 10 and hand size == 2))
                is_initial_small = len(table.dealer_hand) == 2 and table.dealer_value < 10
                is_fourth_card = len(table.dealer_hand) >= 4
                
                if opponent_has_xidach and (is_initial_small or is_fourth_card):
                    trash_talk = "Xì dách của cưng chưa chắc to hơn Ngũ Linh của chị đâu 💅"
                
                # Priority 2: Standard AI Trash Talk (if no specific taunt)
                elif reason == "safe_majority":
                     trash_talk = random.choice([
                         "Ăn được hơn nửa sòng rồi, dằn thôi mấy cưng! �",
                         "Biết dừng đúng lúc là người quân tử. �",
                         "Lấy ít làm lời, tham thì thâm! �"
                     ])
                elif reason == "cut_losses":
                     trash_talk = random.choice([
                         "Thua thì chung, rút nữa là bán nhà đấy! 🏠",
                         "Cây này xương quá... Thôi coi như xui. 🦴",
                         "Dừng ở đây thôi, gỡ gạc ván sau. 🏳️"
                     ])
                elif reason == "desperate_hit":
                     trash_talk = random.choice([
                         "Thế này thì ép Nhà Cái quá... Thêm lá nữa! �",
                         "Không còn gì để mất! Tất tay! �",
                         "Thua keo này ta bày keo khác... RÚT! �"
                     ])
                elif reason == "ngu_linh_achieved":
                     trash_talk = random.choice([
                         "💬 **5 lá** rồi nha! Chia nữa là Quắc đấy đùa à?",
                         "💬 **Ngũ Linh Hương Tỏa Sáng!** Dừng cuộc chơi thôi 😎"
                     ])

                if trash_talk and dealer_msg:
                     embed.set_field_at(1, name="📋 Trạng thái", value=f"💬 {trash_talk}", inline=True)
                     try: 
                        await dealer_msg.edit(embed=embed)
                        await asyncio.sleep(5.0) # Give time to read
                     except: pass

                if dealer_msg:
                    # Update status to drawing
                    embed.set_field_at(1, name="📋 Trạng thái", value="🤖 Đang rút bài...", inline=True)
                    try:
                        await dealer_msg.edit(embed=embed)
                    except: pass
                
                await asyncio.sleep(1) # Delay before draw
                
                # Draw card
                new_card = table.deck.draw_one()
                table.dealer_hand.append(new_card)
                
                # Render update
                if dealer_msg:
                    try:
                        dealer_img = await render_hand_image(table.dealer_hand, "Nhà Cái")
                        hand_file = discord.File(io.BytesIO(dealer_img), filename="dealer_hand.png")
                        
                        embed.color = discord.Color.red() if table.dealer_value > 21 else discord.Color.gold()
                        embed.set_image(url="attachment://dealer_hand.png")
                        embed.set_field_at(0, name="📊 Điểm", value=f"**{table.dealer_value}**", inline=True)
                        
                        # Delete and resend for new image (Discord limit)
                        await dealer_msg.delete()
                        dealer_msg = await channel.send(embed=embed, file=hand_file)
                    except Exception as e:
                        logger.error(f"[XIDACH] Failed to animate dealer draw: {e}")
                
                await asyncio.sleep(2) # 2s delay after draw

            # Final Dealer State
            if dealer_msg:
                try:
                    status_text = "✅ Đã Chốt Bài"
                    if table.dealer_value > 21:
                        embed.color = discord.Color.red()
                        embed.title = "💥 **NHÀ CÁI ĐÃ QUẮC!**"
                        status_text = "💥 NHÀ CÁI ĐÃ QUẮC! ( > 21 )" # Increased size
                        
                        # Dealer "Ngủ luôn" logic
                        if len(table.dealer_hand) >= 5:
                            status_text = "😴 Và thế là **Nhà Cái** đã ngủ luôn!"
                    else:
                        embed.color = discord.Color.green()
                        embed.title = "✅ **NHÀ CÁI ĐÃ CHỐT BÀI**"
                        status_text = "✅ CHỐT BÀI" # Increased size
                    
                    embed.set_field_at(1, name="📋 Trạng thái", value=status_text, inline=True)
                    
                    await dealer_msg.edit(embed=embed)
                    await asyncio.sleep(4) # Show final result for a bit
                    # await dealer_msg.delete() <- Removed deletion to persist result
                except:
                    pass

            # Calculate results for all players
            await self._calculate_multi_results(channel, table)

        except Exception as e:
            logger.error(f"[XIDACH] [ERROR] Multi game error: {e}", exc_info=True)
            await channel.send(f"❌ Đã xảy ra lỗi trong ván đấu: {str(e)}")
        finally:
            # ALWAYS cleanup table
            game_manager.remove_table(channel.id)

    def _get_player_turn_commentary(self, player: Player, finished: bool) -> Optional[str]:
        """Generate funny trash talk for player turn based on state."""
        # 1. Finished State (Stand/Bust/Blackjack)
        if finished:
            if player.status == PlayerStatus.BUST:
                return random.choice([
                    "Chia buồn... Đi bụi rồi ⚰️",
                    "Tham thì thâm... Xu cà na! 🍋",
                    "Thôi xong! Ra đê mà ở 🏠",
                    "Rút cho cố vô... 💥"
                ])
            elif player.status == PlayerStatus.BLACKJACK or player.hand_type == HandType.NGU_LINH:
                return random.choice([
                    "Cao thủ! Cả sòng quỳ xuống! 🙇",
                    "Trời độ! Ai chơi lại nữa! 🌟",
                    "Vô địch thiên hạ! 🏆",
                    "Cái tầm này thì ai đỡ nổi! 😎"
                ])
            elif player.status == PlayerStatus.STAND:
                if player.hand_value < 16 and player.hand_type == HandType.NORMAL:
                    return random.choice([
                        "Non và xanh lắm! Về bú sữa mẹ đi em! 🍼",
                        "Chưa đủ tuổi ra gió rồi cưng ơi! 🌬️",
                        "Yếu thì đừng ra gió! 16 điểm còn chưa có... 😂",
                        "Về học lại luật đi cưng! <16 mà đòi dằn? 📚"
                    ])
                elif player.hand_value <= 15: # Should be unreachable if normal, but keeps checks safe
                    return random.choice([
                        "Yếu đuối... 🐔",
                        "Non gan thế? 🐣",
                        "Sợ chết à? Bốc tiếp đi! 👻",
                        "Dằn non ăn cám nha cưng! 🍚"
                    ])
                elif 16 <= player.hand_value <= 17:
                    return random.choice([
                        "Cũng tạm... Cầu trời khấn phật đi 🙏",
                        "Run tay rồi à? 🥶",
                        "An toàn là bạn... Tai nạn là thường 🚑",
                        "Biết đâu đấy... 🤞"
                    ])
                elif 18 <= player.hand_value <= 20:
                    return random.choice([
                        "Khét đấy! 🔥",
                        "Tự tin ghê... 😏",
                        "Rung đùi chờ tiền thôi! 💰",
                        "Chắc nịch luôn! 🧱"
                    ])
                elif player.hand_value == 21:
                     return "Xong phim Nhà Cái! 🎬"
        
        # 2. Playing State (Thinking/Hit)
        else:
             if player.hand_value <= 10:
                 return random.choice([
                     "Mạnh dạn lên em! 💪",
                     "Sợ gì! Bốc mạnh! 🚀",
                     "Tới luôn bác tài! 🚌",
                     "Thấp quá... Thêm lá nữa! ➕"
                 ])
             elif 11 <= player.hand_value <= 15:
                 return random.choice([
                     "Suy nghĩ kỹ nha... 🤔",
                     "Cơ hội đổi đời... hoặc đi bụi 🌪️",
                     "Run tay à? Bốc đi! 👇",
                     "Lỡ cỡ thế này khó chịu nhỉ... 😬"
                 ])
             elif 16 <= player.hand_value <= 20:
                 return random.choice([
                     "Dằn hay Rút?... Đau đầu quá 🤯",
                     "Liều ăn nhiều? Hay về tay trắng? 💸",
                     "Coi chừng toang nha... 💣",
                     "Hồi hộp vãi tim... 💓"
                 ])
        
        return None

    def _create_turn_embed(
        self, 
        player: Player, 
        time_remaining: int, 
        finished: bool = False,
        is_multiplayer: bool = False
    ) -> discord.Embed:
        """Create embed for player's turn."""
        
        # Status Text & Color
        if finished:
            if player.status == PlayerStatus.BUST:
                status_text = "### 💥 ĐÃ QUẮC (>21)"
                color = discord.Color.red()
            elif player.status == PlayerStatus.STAND:
                if player.hand_type == HandType.NGU_LINH:
                     status_text = "### 🐉 ĐÃ ĐẠT NGŨ LINH"
                     color = discord.Color.gold()
                elif player.hand_value < 16 and player.hand_type == HandType.NORMAL:
                    status_text = "### 🍼 CHƯA ĐỦ TUỔI (<16)"
                    color = discord.Color.orange()
                else:
                    status_text = "### ✋ ĐÃ DẰN BÀI"
                    color = discord.Color.green()
            elif player.status == PlayerStatus.BLACKJACK:
                # Check for Thang Trang type
                hand_type_text = "XÌ DÁCH"
                if player.hand_type == HandType.XI_BAN:
                     hand_type_text = "XÌ BÀN"
                status_text = f"### 🎰 {hand_type_text}!"
                color = discord.Color.gold()
        # Default color/text if not set above
        if not finished:
            status_text = "### ⏳ ĐANG SUY NGHĨ..."
            color = discord.Color.blue()
            
        # Ngu luon check
        if player.is_bust and len(player.hand) >= 5:
             status_text += f"\n### 😴 Và thế là **{player.username}** đã ngủ luôn!"

        embed = discord.Embed(
            title=f"🎲 Lượt của {player.username}",
            description=f"**Trạng thái:**\n{status_text}",
            color=color
        )
        
        # Add Trash Talk (Multiplayer Only)
        if is_multiplayer:
            commentary = self._get_player_turn_commentary(player, finished)
            if commentary:
                # Add to description or footer? Description looks better for "Chat" vibe
                embed.description += f"\n\n> *“{commentary}”*"
        
        embed.add_field(name="💰 Cược", value=f"**{player.bet:,} hạt**", inline=True) # Bold for emphasis
        
        # Point Display Logic
        if player.hand_type == HandType.XI_BAN:
             pass # Don't show Points field
        elif player.hand_type == HandType.XI_DACH:
             # Show 21 explicitly? or just hand_value. 
             # hand_value for Xi Dach is 21. So default is fine.
             embed.add_field(name="📊 Điểm", value=f"**{player.hand_value}**", inline=True)
        else:
             embed.add_field(name="📊 Điểm", value=f"**{player.hand_value}**", inline=True)
        
        if not finished:
            # Use Discord Relative Timestamp
            end_time = int(time.time() + time_remaining)
            embed.add_field(name="⏰ Thời gian", value=f"<t:{end_time}:R>", inline=True)

        if not finished and player.can_double:
            embed.set_footer(text="💎 Bạn có thể NHÂN ĐÔI tiền cược!")

        return embed

    def _create_overview_embed(
        self,
        table: Table,
        hide_dealer: bool = True
    ) -> discord.Embed:
        """Create overview embed showing all players and dealer with clean design.
        
        Args:
            table: Game table.
            hide_dealer: Whether to hide dealer's first card.
            
        Returns:
            discord.Embed: Overview embed.
        """
        embed = discord.Embed(
            title="🎰 XÌ DÁCH",
            description="**Ván đấu nhiều người**",
            color=discord.Color.dark_gold()
        )

        # Dealer's hand - clean format
        dealer_display = format_hand(table.dealer_hand, hide_first=hide_dealer)
        if hide_dealer:
            dealer_value = "?"
        else:
            dealer_value = str(table.dealer_value)
            if table.dealer_value > 21:
                dealer_value = f"💥 {table.dealer_value}"
            if table.dealer_type != HandType.NORMAL:
                dealer_value += f" {get_hand_description(table.dealer_type)}"

        embed.add_field(
            name="🤖 Nhà Cái",
            value=f"{dealer_display}\nĐiểm: **{dealer_value}**",
            inline=False
        )

        # All players - clean format
        for uid, player in table.players.items():
            if player.bet <= 0:
                continue

            # Simple status icons
            if player.status == PlayerStatus.BUST:
                icon = "💥"
            elif player.status == PlayerStatus.BLACKJACK:
                icon = "🎰"
            elif player.status == PlayerStatus.STAND:
                icon = "✋"
            else:
                icon = "🎴"

            # Current player marker
            is_current = table.current_player and table.current_player.user_id == uid
            if is_current:
                name = f"▶ {player.username}"
            else:
                name = f"{icon} {player.username}"

            player_display = format_hand(player.hand)
            hand_desc = get_hand_description(player.hand_type) if player.hand_type != HandType.NORMAL else ""
            
            score = str(player.hand_value)
            
            # Special Display Logic (User Request)
            score_line = f"Điểm: **{score}**"
            
            if player.hand_type == HandType.XI_BAN:
                # Xi Ban: Hide score completely, just show hand description later
                score_line = "" 
            elif player.hand_type == HandType.XI_DACH or (player.status == PlayerStatus.BLACKJACK and player.hand_value == 21):
                # Xi Dach: Show "21" (already set in score)
                pass
            elif player.status == PlayerStatus.BLACKJACK:
                 # Other blackjack cases (rare/impossible if not Xi Ban/Xi Dach)
                 score = "???"
                 score_line = f"Điểm: **{score}**"
            
            elif player.hand_value > 21:
                score = f"💥 {player.hand_value}"
                score_line = f"Điểm: **{score}**"

            # Construct value string
            # If Xi Ban, score_line is empty, so we format accordingly
            val_str = f"{player_display}\n"
            if score_line:
                if hand_desc:
                    val_str += f"{score_line} **{hand_desc}**\n"
                else:
                    val_str += f"{score_line}\n"
            else:
                 # Just show hand desc (e.g. "XÌ BÀN!")
                val_str += f"**{hand_desc}**\n"
                
            val_str += f"Cược: **{player.bet:,}**"

            embed.add_field(
                name=name,
                value=val_str,
                inline=True
            )

        # Footer
        if table.current_player:
            embed.set_footer(text=f"Đang đợi: {table.current_player.username}")
        else:
            embed.set_footer(text="Tất cả người chơi đã hoàn thành!")

        return embed

    async def _calculate_multi_results(
        self,
        channel: discord.TextChannel,
        table: Table
    ) -> None:
        """Calculate and display results for all players.
        
        Args:
            channel: Discord channel.
            table: Game table.
        """
        results = []
        seed_updates = {}

        for uid, player in table.players.items():
            if player.bet <= 0:
                continue

            result, multiplier = compare_hands(player.hand, table.dealer_hand)
            payout = int(player.bet * multiplier)

            if payout > 0:
                seed_updates[uid] = payout

            # Build result line
            if result == "win":
                emoji = "🎉"
                result_text = f"THẮNG | +{payout:,} HẠT💰"
            elif result == "lose":
                emoji = "😢"
                result_text = f"THUA | -{player.bet:,} HẠT💰"
            else:
                emoji = "🤝"
                result_text = "HÒA"

            results.append(
                f"{emoji} <@{uid}>: {format_hand(player.hand)} "
                f"(**{player.hand_value}**) \n# Kết quả: {result_text}" # Reduced from # (H1) to ** (Bold)
            )

            logger.info(
                f"[XIDACH] [MULTI_RESULT] user_id={uid} result={result} "
                f"payout={payout}"
            )

        # Batch update seeds
        if seed_updates:
            await batch_update_seeds(seed_updates)
            logger.info(f"[XIDACH] [BATCH_PAYOUT] {len(seed_updates)} players")

        # Send results
        dealer_display = (
            f"🤖 **Nhà Cái**: {format_hand(table.dealer_hand)} "
            f"(**{table.dealer_value}** {get_hand_description(table.dealer_type)})"
        )
        
        results_text = "\n".join(results)
        embed = discord.Embed(
            title="🎰 KẾT QUẢ XÌ DÁCH",
            description=f"{dealer_display}\n\n{results_text}",
            color=discord.Color.gold()
        )
        
        # 1v1 Trash Talk Logic
        # Only if exactly 1 player played 
        active_players = [p for p in table.players.values() if p.bet > 0]
        if len(active_players) == 1:
            player = active_players[0]
            # Check result from results list string (simplest way without re-calculating)
            # But better to check Logic again briefly
            res, _ = compare_hands(player.hand, table.dealer_hand)
            
            taunt = ""
            if res == "lose" and table.dealer_type not in (HandType.XI_DACH, HandType.XI_BAN):
                # Dealer wins NORMAL hand
                
                # S2: Self-Sabotage Check (Had Xi Dach 21 but hit?)
                # Logic: Initial 2 cards sum to 21, but hand size > 2
                had_xi_dach_initially = False
                if len(player.hand) > 2:
                    initial_sum = calculate_hand_value(player.hand[:2])
                    # Note: calculate_hand_value handles Aces. Ace+Ten = 21. Ace+Ace=12/2/22 (not 21).
                    if initial_sum == 21:
                        had_xi_dach_initially = True
                
                if had_xi_dach_initially:
                     taunt = "\n# Con gà này win thì không chịu, cứ thích phải thua cơ 🐔"
                elif player.hand_value < 16 and player.hand_type == HandType.NORMAL:
                    taunt = "\n# Con gà này chưa Đủ TUỔI với anh 🐔"
                elif player.hand_value >= 16:
                     taunt = random.choice([
                             "\n# Tưởng thế nào 😏",
                             "\n# Gà vãiii 🤣",
                             "\n# Hehe ăn may thôi 🤭"
                         ])
            
            elif res == "win" and player.hand_type == HandType.NGU_LINH:
                 taunt = random.choice([
                     "\n# Ngũ Linh cơ à? Ghê đấy! 🤐",
                     "\n# Ăn rùa được ván Ngũ Linh thôi, đừng gáy! 🐢",
                     "\n# Trời độ mày ván này đấy! ⛈️",
                     "\n# Hên thôi, lần sau chết với bà! 🔮"
                 ])
            
            if taunt:
                embed.description += taunt
        
        try:
            # Render FINAL game state (Dealer revealed)
            players_data = []
            for uid, p in table.players.items():
                if p.bet > 0:
                    players_data.append({
                        'name': p.username,
                        'cards': p.hand,
                        'score': p.hand_value,
                        'bet': p.bet
                    })

            img_bytes = await render_game_state_image(
                dealer_cards=table.dealer_hand,
                players_data=players_data,
                hide_dealer=False  # Reveal dealer
            )
            
            file = discord.File(io.BytesIO(img_bytes), filename="result_state.png")
            embed.set_image(url="attachment://result_state.png")
            
            await channel.send(embed=embed, file=file)
        except Exception as e:
            logger.error(f"[XIDACH] [RESULT_RENDER_FAIL] {e}", exc_info=True)
            await channel.send(embed=embed)

    # ==================== COMMANDS ====================

    @app_commands.command(
        name="xidach",
        description="Chơi Xì Dách - Có số tiền cược: chơi đơn | Không có: mở sòng"
    )
    @app_commands.describe(cuoc="Số hạt muốn cược (bỏ trống để mở sòng nhiều người)")
    async def xidach_slash(
        self,
        interaction: discord.Interaction,
        cuoc: Optional[int] = None
    ) -> None:
        """Start Xi Dach game via slash command.
        
        Args:
            interaction: Discord interaction.
            cuoc: Bet amount (optional).
        """
        if cuoc is not None:
            await self._start_solo_game(interaction, cuoc)
        else:
            await self._start_multiplayer(interaction)

    @commands.command(name="xidach", description="Chơi Xì Dách")
    async def xidach_prefix(self, ctx, cuoc: Optional[int] = None) -> None:
        """Start Xi Dach game via prefix command.
        
        Args:
            ctx: Command context.
            cuoc: Bet amount (optional).
        """
        if cuoc is not None:
            await self._start_solo_game(ctx, cuoc)
        else:
            await self._start_multiplayer(ctx)


async def setup(bot: commands.Bot) -> None:
    """Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance.
    """
    await bot.add_cog(XiDachCog(bot))

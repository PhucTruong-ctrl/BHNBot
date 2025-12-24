"""Bau Cua Cog - Main orchestrator.

Coordinates game logic, statistics, and UI components.
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from core.logger import setup_logger

from .game_logic import GameManager
from .statistics import StatisticsTracker
from .views import BauCuaBetView
from .helpers import (
    create_betting_embed,
    create_result_display,
    create_summary_text
)
from .constants import BETTING_TIME_SECONDS

logger = setup_logger("BauCuaCog", "logs/cogs/baucua.log")


class BauCuaCog(commands.Cog):
    """Cog for Bầu Cua (Vietnamese dice game).
    
    Manages the complete game flow:
    1. Betting phase (45 seconds)
    2. Dice rolling animation
    3. Results calculation
    4. Statistics tracking
    """
    
    def __init__(self, bot):
        """Initialize the Bau Cua cog.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.game_manager = GameManager(bot)
        self.stats_tracker = StatisticsTracker(bot)
        logger.info("[BAUCUA_COG] Cog initialized")
    
    @app_commands.command(name="baucua", description="Chơi game Bầu Cua Tôm Cá Gà Nai")
    async def play_baucua_slash(self, interaction: discord.Interaction):
        """Start Bầu Cua game via slash command."""
        await self._start_game(interaction)
    
    @commands.command(name="baucua", description="Chơi game Bầu Cua Tôm Cá Gà Nai")
    async def play_baucua_prefix(self, ctx):
        """Start Bầu Cua game via prefix command."""
        await self._start_game(ctx)
    
    async def _start_game(self, ctx_or_interaction):
        """Unified game start logic for both slash and prefix commands.
        
        Args:
            ctx_or_interaction: Either discord.Interaction (slash) or commands.Context (prefix)
        """
        try:
            # Determine command type
            is_slash = isinstance(ctx_or_interaction, discord.Interaction)
            
            if is_slash:
                channel = ctx_or_interaction.channel
                await ctx_or_interaction.response.defer(ephemeral=False)
            else:
                channel = ctx_or_interaction.channel
            
            channel_id = channel.id
            
            # Check if game already active in channel
            if self.game_manager.is_game_active(channel_id):
                msg = "❌ Kênh này đã có game đang chơi! Chờ kết thúc trước khi tạo game mới."
                if is_slash:
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg)
                return
            
            # Create game
            game_state = self.game_manager.create_game(channel_id)
            
            # Send betting interface
            import time
            end_timestamp = int(time.time() + BETTING_TIME_SECONDS)
            embed = create_betting_embed(end_timestamp)
            view = BauCuaBetView(self.game_manager, game_state.game_id)
            
            if is_slash:
                game_message = await ctx_or_interaction.followup.send(embed=embed, view=view)
            else:
                game_message = await ctx_or_interaction.send(embed=embed, view=view)
            
            logger.info(
                f"[GAME_START] game_id={game_state.game_id} channel={channel.name}"
            )
            
            # Betting phase - just wait, Discord handles countdown
            await self._run_betting_phase(game_message, view)
            
            # Check if anyone bet
            if not game_state.has_bets():
                await channel.send("⚠️ Không ai cược! Game bị hủy.")
                logger.info(f"[GAME_CANCELLED] game_id={game_state.game_id} reason=no_bets")
                self.game_manager.end_game(channel_id)
                return
            
            logger.info(
                f"[BETTING_END] game_id={game_state.game_id} "
                f"players={game_state.get_total_players()} "
                f"bets={game_state.get_total_bets_count()}"
            )
            
            # Copy bets before cleanup
            bets_data = game_state.bets.copy()
            
            # Roll dice and show results
            results = await self._run_dice_roll(channel)
            
            # Display results and summary
            await self._display_results(channel, results, bets_data)
            
            # Clean up game state
            self.game_manager.end_game(channel_id)
            
            # Update results in background
            asyncio.create_task(
                self._process_game_results(channel_id, results, bets_data)
            )
            
            logger.info(f"[GAME_COMPLETE] game_id={game_state.game_id}")
            
        except Exception as e:
            logger.error(f"Error in game flow: {e}", exc_info=True)
            
            # Clean up on error
            if is_slash:
                try:
                    await ctx_or_interaction.followup.send(f"❌ Lỗi: {str(e)}", ephemeral=True)
                except Exception:
                    pass
            else:
                try:
                    await ctx_or_interaction.send(f"❌ Lỗi: {str(e)}")
                except Exception:
                    pass
            
            # Remove active game
            self.game_manager.end_game(channel.id)
    
    async def _run_betting_phase(self, game_message, view):
        """Run the betting countdown phase.
        
        Uses Discord timestamp for countdown (auto-updates client-side).
        Only edits message once at the end to disable buttons.
        
        Args:
            game_message: Discord message to update
            view: BauCuaBetView instance
        """
        # Wait for betting duration
        # Discord timestamp handles countdown display automatically
        await asyncio.sleep(BETTING_TIME_SECONDS)
        
        # Betting phase ended - disable buttons
        try:
            for item in view.children:
                item.disabled = True
            await game_message.edit(view=view)
            logger.info("[BETTING_PHASE] Betting ended, buttons disabled")
        except Exception as e:
            logger.error(f"Error disabling bet buttons: {e}")
    
    async def _run_dice_roll(self, channel):
        """Roll dice with animation.
        
        Args:
            channel: Discord channel for sending roll message
            
        Returns:
            Tuple of (result1, result2, result3)
        """
        await asyncio.sleep(1)  # Brief pause before rolling
        
        # Initial roll display
        initial_roll = await self.game_manager.roll_dice()
        from .helpers import create_rolling_text
        rolling_text = create_rolling_text(*initial_roll)
        rolling_message = await channel.send(rolling_text)
        
        # Animate
        results = await self.game_manager.animate_roll(rolling_message)
        
        return results
    
    async def _display_results(self, channel, results, bets_data):
        """Display final results and summary.
        
        Args:
            channel: Discord channel
            results: Tuple of (result1, result2, result3)
            bets_data: Dictionary of bets
        """
        result_display = create_result_display(*results)
        summary_text = create_summary_text(*results, bets_data)
        
        # Find and update rolling message, send summary
        async for message in channel.history(limit=5):
            if message.author == self.bot.user and "🎃" in message.content:
                await asyncio.gather(
                    message.edit(content=result_display),
                    channel.send(f"**TỔNG KẾT:**\n{summary_text}")
                )
                break
    
    async def _process_game_results(self, channel_id, results, bets_data):
        """Process game results: update balances and statistics.
        
        Runs in background via asyncio.create_task().
        
        Args:
            channel_id: Discord channel ID
            results: Tuple of dice results
            bets_data: Dictionary of user bets
        """
        try:
            # Calculate payouts
            from .models import GameState
            temp_game = GameState(
                game_id="temp",
                channel_id=channel_id,
                start_time=0,
                bets=bets_data
            )
            payouts = await self.game_manager.calculate_results(temp_game, results)
            
            # Update balances
            await self.game_manager.update_game_results_batch(payouts)
            
            # Update statistics
            await self.stats_tracker.update_game_stats(channel_id, results, bets_data)
            
        except Exception as e:
            logger.error(f"Error processing game results: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    """Load the Bau Cua cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(BauCuaCog(bot))

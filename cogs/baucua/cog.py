import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import datetime
import time
from database_manager import batch_update_seeds, db_manager
from core.services.vip_service import VIPEngine

from .game_logic import GameManager
from .statistics import StatisticsTracker
from .views import BauCuaBetView
from .helpers import (
    create_betting_embed,
    create_result_display,
    create_summary_text
)
from .constants import BETTING_TIME_SECONDS
from core.logging import get_logger

logger = get_logger("BauCuaCog")

# Cooldown constants for gambling commands
BAUCUA_COOLDOWN_RATE = 1  # 1 use
BAUCUA_COOLDOWN_PER = 10  # per 10 seconds


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
        self.active_views = {}  # channel_id -> BauCuaBetView (for cleanup)
        
        # Start cashback task
        self.daily_cashback_task.start()
        logger.info("[BAUCUA_COG] Cog initialized + Cashback Task Started")
        
    def cog_unload(self):
        self.daily_cashback_task.cancel()

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0)) # UTC midnight
    async def daily_cashback_task(self):
        """Process daily cashback for VIP users."""
        await self._process_cashback()

    @commands.command(name="test_cashback")
    @commands.is_owner()
    async def test_cashback_cmd(self, ctx):
        """Force run cashback task (Owner only)."""
        await ctx.send("⏳ Đang chạy cashback...")
        count, total = await self._process_cashback()
        await ctx.send(f"✅ Đã chạy xong! Hoàn tiền cho {count} người. Tổng: {total:,} Hạt.")

    async def _process_cashback(self):
        """Core logic for cashback processing."""
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        
        logger.info(f"[CASHBACK] Starting process for date: {yesterday}")
        
        # 1. Get all stats for yesterday
        rows = await db_manager.fetchall(
            "SELECT user_id, total_lost, total_won FROM baucua_daily_stats WHERE date = ?",
            (yesterday,)
        )
        
        if not rows:
            logger.info("[CASHBACK] No stats found for yesterday.")
            return 0, 0
            
        count = 0
        total_refunded = 0
        
        for row in rows:
            user_id, lost, won = row
            net_loss = lost - won
            
            if net_loss <= 0:
                continue
                
            # Check VIP status
            vip_data = await VIPEngine.get_vip_data(user_id)
            if not vip_data:
                continue
                
            tier = vip_data.get('tier', 0)
            if tier < 1:
                continue
                
            # Calculate Refund (Tier 1: 2%, Tier 2: 3%, Tier 3: 5%)
            rate = 0
            if tier == 1: rate = 0.02
            elif tier == 2: rate = 0.03
            elif tier == 3: rate = 0.05
            
            refund = int(net_loss * rate)
            if refund > 10000:
                refund = 10000 # Cap
                
            if refund <= 0:
                continue
                
            # Process Refund
            try:
                await self.game_manager.update_seeds(user_id, refund)
                total_refunded += refund
                count += 1
                
                # Send DM
                try:
                    user = self.bot.get_user(user_id)
                    if user:
                        await user.send(
                            f"💎 **VIP Cashback:** Bạn nhận được **{refund:,} Hạt** hoàn trả từ số tiền thua hôm qua ({net_loss:,}).\n"
                            f"Tier {tier} Rate: {int(rate*100)}%."
                        )
                except Exception:
                    pass # User blocked DM
                    
            except Exception as e:
                logger.error(f"Error refunding user {user_id}: {e}")
                
        logger.info(f"[CASHBACK] Completed. Users: {count}, Total: {total_refunded}")
        return count, total_refunded

    @app_commands.command(name="baucua", description="Chơi game Bầu Cua Tôm Cá Gà Nai")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    async def play_baucua_slash(self, interaction: discord.Interaction):
        """Start Bầu Cua game via slash command."""
        await self._start_new_game(interaction)
    
    @commands.command(name="baucua", description="Chơi game Bầu Cua Tôm Cá Gà Nai")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def play_baucua_prefix(self, ctx, *args):
        """Start Bầu Cua game via prefix command.
        
        Supports Quick Bet: !bc -q 50k bau
        """
        if args:
            await self._process_quick_bet(ctx, args)
        else:
            await self._start_new_game(ctx)
            
    async def _process_quick_bet(self, ctx_or_interaction, args):
        """Handle Quick Bet logic."""
        from .helpers import parse_quick_bet_args, unified_send
        
        # Parse args
        success, amount, choice, error = parse_quick_bet_args(args)
        if not success:
            await unified_send(ctx_or_interaction, f"❌ {error}", ephemeral=True)
            return
            
        channel_id = ctx_or_interaction.channel.id
        
        # Check active game
        if not self.game_manager.is_game_active(channel_id):
            # Start new game (non-blocking)
            game_state = await self._start_new_game(ctx_or_interaction)
            if not game_state:
                return # Error starting game
            # Wait briefly for game to register
            await asyncio.sleep(0.5)
        else:
            game_state = self.game_manager.get_game(channel_id)
            
        # Place bet
        await self.game_manager.add_bet(
            ctx_or_interaction,
            game_state.game_id,
            choice,
            amount
        )
    
    async def _start_new_game(self, ctx_or_interaction):
        """Initialize game and spawn game loop.
        
        Returns:
            GameState if successful, None if failed
        """
        # Determine context
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            channel = ctx_or_interaction.channel
            # Don't defer if already deferred (handled by caller if needed, or check)
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.defer(ephemeral=False)
        else:
            channel = ctx_or_interaction.channel
            
        channel_id = channel.id
        
        # Check active
        if self.game_manager.is_game_active(channel_id):
            msg = "❌ Kênh này đã có game đang chơi!"
            from .helpers import unified_send
            await unified_send(ctx_or_interaction, msg, ephemeral=True)
            return None
            
        # Create game
        try:
            game_state = self.game_manager.create_game(channel_id)
            
            # Create View & Embed
            import time
            end_timestamp = int(time.time() + BETTING_TIME_SECONDS)
            
            user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
            embed = await create_betting_embed(user, end_timestamp)
            view = BauCuaBetView(self.game_manager, game_state.game_id)
            self.active_views[channel_id] = view
            
            # Send Message
            from .helpers import unified_send
            game_message = await unified_send(ctx_or_interaction, embed=embed, view=view)
            
            logger.info(f"[GAME_START] game_id={game_state.game_id} channel={channel.name}")
            
            # Spawn Game Loop Task
            asyncio.create_task(self._run_game_loop(channel, game_message, view, game_state))
            
            return game_state
            
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            from .helpers import unified_send
            await unified_send(ctx_or_interaction, f"❌ Lỗi: {e}", ephemeral=True)
            return None

    async def _run_game_loop(self, channel, game_message, view, game_state):
        """Main game loop running as background task."""
        try:
            # Betting phase
            await self._run_betting_phase(game_message, view)
            
            # Check bets
            if not game_state.has_bets():
                await channel.send("⚠️ Không ai cược! Game bị hủy.")
                logger.info(f"[GAME_CANCELLED] game_id={game_state.game_id} reason=no_bets")
                self._cleanup_view(channel.id)
                self.game_manager.end_game(channel.id)
                return
                
            logger.info(f"[BETTING_END] game_id={game_state.game_id} bets={game_state.get_total_bets_count()}")
            
            # Copy bets
            bets_data = game_state.bets.copy()
            
            # Roll Dice
            results = await self._run_dice_roll(channel)
            
            # Display Results
            await self._display_results(channel, results, bets_data)
            
            # Cleanup
            self._cleanup_view(channel.id)
            self.game_manager.end_game(channel.id)
            
            # Process Payouts & Stats & Instant Cashback
            asyncio.create_task(self._process_game_results(channel.id, results, bets_data))
            
            logger.info(f"[GAME_COMPLETE] game_id={game_state.game_id}")
            
        except Exception as e:
            logger.error(f"Error in game loop: {e}", exc_info=True)
            self._cleanup_view(channel.id)
            self.game_manager.end_game(channel.id)

    async def _run_betting_phase(self, game_message, view):
        """Run the betting countdown phase."""
        await asyncio.sleep(BETTING_TIME_SECONDS)
        
        try:
            for item in view.children:
                item.disabled = True
            await game_message.edit(view=view)
            logger.info("[BETTING_PHASE] Betting ended, buttons disabled")
        except Exception as e:
            logger.error(f"Error disabling bet buttons: {e}")
    
    async def _run_dice_roll(self, channel):
        """Roll dice with animation."""
        await asyncio.sleep(1)
        initial_roll = await self.game_manager.roll_dice()
        from .helpers import create_rolling_text
        rolling_text = create_rolling_text(*initial_roll)
        rolling_message = await channel.send(rolling_text)
        results = await self.game_manager.animate_roll(rolling_message)
        return results
    
    async def _display_results(self, channel, results, bets_data):
        """Display final results."""
        result_display = create_result_display(*results)
        
        # Get VIP data for special messages
        vip_data = {} # user_id -> tier
        user_ids = list(bets_data.keys())
        
        for uid in user_ids:
            vip = await VIPEngine.get_vip_data(uid)
            if vip and vip['tier'] >= 1:
                vip_data[uid] = vip['tier']
        
        # Helper uses this data to decide message template and calculate cashback amount for display
        summary_text = create_summary_text(*results, bets_data, vip_data=vip_data)
        
        async for message in channel.history(limit=5):
            if message.author == self.bot.user:
                await asyncio.gather(
                    message.edit(content=result_display),
                    channel.send(f"**TỔNG KẾT:**\n{summary_text}")
                )
                break
    
    async def _process_game_results(self, channel_id, results, bets_data):
        """Process game results: payouts, stats, and INSTANT CASHBACK."""
        try:
            from .models import GameState
            temp_game = GameState(
                game_id="temp",
                channel_id=channel_id,
                start_time=0,
                bets=bets_data
            )
            # 1. Standard Payouts
            payouts = await self.game_manager.calculate_results(temp_game, results)
            await self.game_manager.update_game_results_batch(payouts)
            
            # 2. Update Stats
            await self.stats_tracker.update_game_stats(channel_id, results, bets_data)
            
            # 3. Instant Cashback for VIP Losers
            await self._process_instant_cashback(bets_data, payouts)
            
        except Exception as e:
            logger.error(f"Error processing game results: {e}", exc_info=True)

    async def _process_instant_cashback(self, bets_data, payouts):
        """Calculate and apply instant cashback for VIPs who lost."""
        for user_id, bets in bets_data.items():
            total_bet = sum(amount for _, amount in bets)
            payout = payouts.get(user_id, 0)
            net_change = payout - total_bet
            
            if net_change >= 0:
                continue # Only cashback on loss
                
            loss = abs(net_change)
            
            # Check VIP
            vip = await VIPEngine.get_vip_data(user_id)
            if not vip or vip['tier'] < 1:
                continue
                
            tier = vip['tier']
            # Rate: 2%, 3%, 5%
            rate = 0.02
            if tier == 2: rate = 0.03
            elif tier == 3: rate = 0.05
            
            # Instant Cashback (No cap)
            cashback = int(loss * rate)
            
            if cashback > 0:
                try:
                    await self.game_manager.update_seeds(user_id, cashback)
                    logger.info(f"[INSTANT_CASHBACK] User {user_id} (Tier {tier}) lost {loss} -> refunded {cashback}")
                except Exception as e:
                    logger.error(f"[CASHBACK_ERROR] Failed to refund {user_id}: {e}")

    def _cleanup_view(self, channel_id):
        if channel_id in self.active_views:
            self.active_views[channel_id].stop()
            del self.active_views[channel_id]

async def setup(bot: commands.Bot):
    """Load the Bau Cua cog."""
    await bot.add_cog(BauCuaCog(bot))

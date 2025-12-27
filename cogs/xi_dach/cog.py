"""Xi Dach (Vietnamese Blackjack) - Refactored Controller.

This module acts as the entry point and controller for the Xi Dach game.
It delegates business logic to specialized modules in `commands/`, `mechanics/`, and `ui/`.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time

from core.logger import setup_logger
from database_manager import db_manager, get_user_balance

from .constants import MIN_BET, TURN_TIMEOUT
# from .models import game_manager, Table, Player # REMOVED
# Should be:
from .core.game_manager import game_manager
from .core.table import Table
from .core.player import Player
from .statistics import StatisticsTracker

# Import Implementations
# from .commands import solo as solo_cmd  # REMOVED
from .commands import multi as multi_cmd

logger = setup_logger("XiDachCog", "cogs/xidach.log")

class XiDachCog(commands.Cog):
    """Cog for Xi Dach (Vietnamese Blackjack) game."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_task = None
        self.stats = StatisticsTracker(bot)

    async def cog_load(self):
        """Start background tasks."""
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_loop())
        logger.info("[XIDACH] Cleanup task started")

    async def cog_unload(self):
        """Cancel background tasks."""
        if self.cleanup_task:
            self.cleanup_task.cancel()

    async def cleanup_loop(self):
        """Periodically clean up stale tables."""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                count = game_manager.cleanup_old_tables(max_age_seconds=600)
                if count > 0:
                    logger.info(f"[XIDACH] [CLEANUP] Removed {count} stale tables")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[XIDACH] [CLEANUP_ERROR] {e}")

    # ==================== PUBLIC COMMANDS ====================

    @commands.hybrid_command(name="xidach", description="Chơi Xì Dách (Tạo phòng hoặc tham gia)")
    @app_commands.describe(bet="Số hạt muốn cược")
    async def xidach(self, ctx: commands.Context, bet: int = 50):
        """Start or Join Xi Dach Lobby."""
        logger.info(f"[XIDACH] Command triggered by {ctx.author.id} (bet={bet})")
        # Unified Multiplayer Flow
        await multi_cmd.start_multiplayer(self, ctx.interaction if ctx.interaction else ctx, bet)

    # ==================== SOLO CALLBACKS REMOVED ====================

    # ==================== MULTI CALLBACKS (Called by View) ====================

    async def player_join_lobby(self, interaction: discord.Interaction, table: Table):
        await multi_cmd.player_join_lobby(self, interaction, table)
    
    async def process_bet(self, interaction: discord.Interaction, table: Table, user_id: int, amount: int):
        await multi_cmd.process_bet(self, interaction, table, user_id, amount)

    async def player_ready(self, interaction: discord.Interaction, table: Table, player: Player):
        await multi_cmd.player_ready(self, interaction, table, player)

    async def player_hit_multi(self, interaction: discord.Interaction, table: Table, player: Player, view):
        await multi_cmd.player_hit_multi(self, interaction, table, player, view)

    async def player_stand_multi(self, interaction: discord.Interaction, table: Table, player: Player, view):
        await multi_cmd.player_stand_multi(self, interaction, table, player, view)

    async def player_double_multi(self, interaction: discord.Interaction, table: Table, player: Player, view):
        await multi_cmd.player_double_multi(self, interaction, table, player, view)

    async def request_start_game(self, interaction: discord.Interaction, table: Table):
        await multi_cmd.request_start_game(self, interaction, table)

    # ==================== HELPERS ====================
    
    async def get_user_seeds(self, user_id: int) -> int:
        """Helper for views to check balance."""
        return await get_user_balance(user_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(XiDachCog(bot))

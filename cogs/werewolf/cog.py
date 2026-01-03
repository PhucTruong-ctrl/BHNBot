"""Discord cog providing Werewolf game commands."""

from __future__ import annotations

import asyncio
from typing import Set

import discord
from discord.ext import commands
from discord import app_commands

from .engine.game import WerewolfGame
from .engine.manager import WerewolfManager
from .roles.base import Expansion
from database_manager import get_server_config
from core.logger import setup_logger

logger = setup_logger("WerewolfCog", "cogs/werewolf/werewolf.log")

EXPANSION_ALIASES = {
    "newmoon": Expansion.NEW_MOON,
    "new_moon": Expansion.NEW_MOON,
    "nm": Expansion.NEW_MOON,
    "village": Expansion.THE_VILLAGE,
    "thevillage": Expansion.THE_VILLAGE,
    "tv": Expansion.THE_VILLAGE,
}


class WerewolfCog(commands.Cog):
    """Cog that exposes the Werewolf commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.manager = WerewolfManager(bot)

    def cog_unload(self) -> None:
        asyncio.create_task(self.manager.stop_all())
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Auto-restore saved Werewolf games on bot startup and cleanup orphaned permissions"""
        # P1 FIX: Clean up orphaned permissions from crashed games
        try:
            await self.manager.cleanup_orphaned_permissions()
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned permissions: {e}", exc_info=True)
        
        # Game state restoration temporarily disabled for dynamic voice channel support
        # TODO: Implement full game state restoration with voice_channel_id
        pass

    @commands.group(name="masoi", invoke_without_command=True)
    async def werewolf_group(self, ctx: commands.Context) -> None:
        await ctx.send("Các lệnh: !masoi create, !masoi guide")

    @werewolf_group.command(name="create")
    async def create(self, ctx: commands.Context, *expansion_flags: str) -> None:
        """Tạo bàn Ma Sói mới.
        
        All games include dedicated category with voice channel.
        Players can choose to use voice or just chat in threads.
        
        Usage:
            !masoi create
            !masoi create newmoon
            !masoi create newmoon character
        """
        # Check if current channel is set as NoiTu channel
        try:
            noitu_channel_id = await get_server_config(ctx.guild.id, "noitu_channel_id")
            if noitu_channel_id == ctx.channel.id:
                await ctx.send("Kênh này đang được dùng cho Nối Từ. Ko thể tạo Ma Sói ở đây!", delete_after=8)
                return
        except Exception as e:
            logger.error(f"Error checking NoiTu channel: {e}", exc_info=True)
        
        # Check for existing game (temp key during lobby)
        existing = await self.manager.get_game(ctx.guild.id, None) if ctx.guild else None
        if existing and not existing.is_finished:
            await ctx.send("Đang có một bàn Ma Sói khác hoạt động.", delete_after=8)
            return
        
        # Parse expansions
        expansions: Set[Expansion] = set()
        invalid_expansions = []
        for flag in expansion_flags:
            exp = EXPANSION_ALIASES.get(flag.lower())
            if exp:
                expansions.add(exp)
            else:
                invalid_expansions.append(flag)
        
        if invalid_expansions:
            await ctx.send(
                f"⚠️ Expansion không hợp lệ: {', '.join(invalid_expansions)}. "
                f"Dùng: {', '.join(EXPANSION_ALIASES.keys())}", 
                delete_after=10
            )
        
        # Create game with new architecture
        try:
            game = await self.manager.create_game(
                guild=ctx.guild,  # type: ignore[arg-type]
                host=ctx.author,
                expansions=expansions,
                lobby_channel=ctx.channel  # type: ignore[arg-type]
            )
        except RuntimeError as exc:
            await ctx.send(str(exc), delete_after=8)
            return
        
        await game.open_lobby()
        await game.add_player(ctx.author)
        await ctx.send("✅ Đã tạo bàn Ma Sói. Dùng nút để tham gia!", delete_after=10)

    @werewolf_group.command(name="guide")
    async def guide_prefix(self, ctx: commands.Context) -> None:
        """Show werewolf role guide.
        
        Usage:
            !werewolf guide
        """
        guide_cog = self.bot.get_cog("WerewolfGuideCog")
        if not guide_cog:
            await ctx.send("Guide cog không được load!", delete_after=6)
            return

        embed = guide_cog.get_guide_embed()
        view = guide_cog.get_guide_view(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    werewolf_group_app = app_commands.Group(name="masoi", description="Werewolf game commands")

    @werewolf_group_app.command(name="create", description="Tạo bàn chơi Ma Sói")
    @app_commands.describe(
        expansion="Expansion (newmoon, village)"
    )
    async def create_slash(self, interaction: discord.Interaction, expansion: str = "") -> None:
        """Create a werewolf game via slash command.
        
        Usage:
            /masoi create
            /masoi create newmoon
        """
        # Check if current channel is set as NoiTu channel
        try:
            noitu_channel_id = await get_server_config(interaction.guild.id, "noitu_channel_id")
            if noitu_channel_id == interaction.channel.id:
                await interaction.response.send_message("Kênh này đang được dùng cho Nối Từ. Ko thể tạo Ma Sói ở đây!", ephemeral=True)
                return
        except Exception as e:
            logger.error(f"Error checking NoiTu channel: {e}", exc_info=True)
        
        await interaction.response.defer()
        
        existing = await self.manager.get_game(interaction.guild.id, None) if interaction.guild else None
        if existing and not existing.is_finished:
            await interaction.followup.send("Đang có một bàn Ma Sói khác hoạt động.")
            return
        
        expansions: Set[Expansion] = set()
        if expansion:
            exp = EXPANSION_ALIASES.get(expansion.lower())
            if exp:
                expansions.add(exp)
            else:
                await interaction.followup.send(f"⚠️ Expansion '{expansion}' không hợp lệ. Dùng: {', '.join(EXPANSION_ALIASES.keys())}")
        
        try:
            game = await self.manager.create_game(
                guild=interaction.guild,  # type: ignore[arg-type]
                host=interaction.user,
                expansions=expansions,
                lobby_channel=interaction.channel  # type: ignore[arg-type]
            )
        except RuntimeError as exc:
            await interaction.followup.send(str(exc))
            return
        
        await game.open_lobby()
        await game.add_player(interaction.user)
        await interaction.followup.send("✅ Đã tạo bàn Ma Sói. Dùng nút để tham gia!")

    @werewolf_group_app.command(name="guide", description="Xem hướng dẫn chơi Ma Sói")
    async def guide_slash(self, interaction: discord.Interaction) -> None:
        """Show werewolf role guide via slash command.
        
        Usage:
            /werewolf guide
        """
        guide_cog = self.bot.get_cog("WerewolfGuideCog")
        if not guide_cog:
            await interaction.response.send_message("Guide cog không được load!", ephemeral=True)
            return

        embed = guide_cog.get_guide_embed()
        view = guide_cog.get_guide_view(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WerewolfCog(bot))
    # WerewolfGuideCog is loaded separately via guide.py setup()

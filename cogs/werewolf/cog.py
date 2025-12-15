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

    @commands.group(name="werewolf", invoke_without_command=True)
    async def werewolf_group(self, ctx: commands.Context) -> None:
        await ctx.send("Các lệnh: !werewolf create, !werewolf guide")

    @werewolf_group.command(name="create")
    async def create(self, ctx: commands.Context, game_mode: str = "text", *expansion_flags: str) -> None:
        game_mode = game_mode.lower()
        if game_mode not in ("text", "voice"):
            await ctx.send("Mode phải là 'text' hoặc 'voice'", delete_after=6)
            return
        
        # Check if current channel is set as NoiTu channel
        import aiosqlite
        DB_PATH = "./data/database.db"
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT noitu_channel_id FROM server_config WHERE guild_id = ?", 
                    (ctx.guild.id,)
                ) as cursor:
                    row = await cursor.fetchone()
            
            if row and row[0] == ctx.channel.id:
                await ctx.send("Kênh này đang được dùng cho Nối Từ. Ko thể tạo Ma Sói ở đây!", delete_after=8)
                return
        except Exception as e:
            print(f"Error checking NoiTu channel: {e}")
        
        existing = self.manager.get_game(ctx.guild.id) if ctx.guild else None
        if existing and not existing.is_finished:
            await ctx.send("Đang có một bàn Ma Sói khác hoạt động.", delete_after=8)
            return
        expansions: Set[Expansion] = set()
        for flag in expansion_flags:
            exp = EXPANSION_ALIASES.get(flag.lower())
            if exp:
                expansions.add(exp)
        try:
            game = await self.manager.create_game(ctx.guild, ctx.channel, ctx.author, expansions, game_mode=game_mode)  # type: ignore[arg-type]
        except RuntimeError as exc:
            await ctx.send(str(exc), delete_after=8)
            return
        await game.open_lobby()
        await game.add_player(ctx.author)
        mode_text = "Voice" if game_mode == "voice" else "Text"
        await ctx.send(f"Đã tạo bàn Ma Sói [{mode_text}]. Dùng nút để tham gia!", delete_after=10)

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

    werewolf_group_app = app_commands.Group(name="werewolf", description="Werewolf game commands")

    @werewolf_group_app.command(name="start", description="Bắt đầu trò chơi Ma Sói")
    @app_commands.describe(
        game_mode="'text' hoặc 'voice' (mặc định: text)",
        expansion="Expansion (newmoon, village)"
    )
    async def start_slash(self, interaction: discord.Interaction, game_mode: str = "text", expansion: str = "") -> None:
        """Start a werewolf game via slash command.
        
        Usage:
            /werewolf start
            /werewolf start voice newmoon
        """
        game_mode = game_mode.lower()
        if game_mode not in ("text", "voice"):
            await interaction.response.send_message("Mode phải là 'text' hoặc 'voice'", ephemeral=True)
            return
        
        # Check if current channel is set as NoiTu channel
        import aiosqlite
        DB_PATH = "./data/database.db"
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT noitu_channel_id FROM server_config WHERE guild_id = ?", 
                    (interaction.guild.id,)
                ) as cursor:
                    row = await cursor.fetchone()
            
            if row and row[0] == interaction.channel.id:
                await interaction.response.send_message("Kênh này đang được dùng cho Nối Từ. Ko thể tạo Ma Sói ở đây!", ephemeral=True)
                return
        except Exception as e:
            print(f"Error checking NoiTu channel: {e}")
        
        await interaction.response.defer()
        
        existing = self.manager.get_game(interaction.guild.id) if interaction.guild else None
        if existing and not existing.is_finished:
            await interaction.followup.send("Đang có một bàn Ma Sói khác hoạt động.")
            return
        
        expansions: Set[Expansion] = set()
        if expansion:
            exp = EXPANSION_ALIASES.get(expansion.lower())
            if exp:
                expansions.add(exp)
        
        try:
            game = await self.manager.create_game(interaction.guild, interaction.channel, interaction.user, expansions, game_mode=game_mode)  # type: ignore[arg-type]
        except RuntimeError as exc:
            await interaction.followup.send(str(exc))
            return
        
        await game.open_lobby()
        await game.add_player(interaction.user)
        mode_text = "Voice" if game_mode == "voice" else "Text"
        await interaction.followup.send(f"Đã tạo bàn Ma Sói [{mode_text}]. Dùng nút để tham gia!")

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
    # Load the guide cog
    from .guide import WerewolfGuideCog
    await bot.add_cog(WerewolfGuideCog(bot))

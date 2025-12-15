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
        await ctx.send("Các lệnh: !werewolf create, !werewolf cancel, !werewolf guide")

    @werewolf_group.command(name="create")
    async def create(self, ctx: commands.Context, game_mode: str = "text", *expansion_flags: str) -> None:
        game_mode = game_mode.lower()
        if game_mode not in ("text", "voice"):
            await ctx.send("Mode phải là 'text' hoặc 'voice'", delete_after=6)
            return
        
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

    @werewolf_group.command(name="cancel")
    async def cancel(self, ctx: commands.Context) -> None:
        game = self.manager.get_game(ctx.guild.id) if ctx.guild else None
        if not game:
            await ctx.send("Không có bàn nào để huỷ.", delete_after=6)
            return
        if ctx.author.id != game.host.id and not ctx.author.guild_permissions.manage_guild:
            await ctx.send("Chỉ chủ bàn hoặc quản trị viên mới huỷ được.", delete_after=6)
            return
        await self.manager.remove_game(ctx.guild.id)
        await ctx.send("Đã huỷ bàn Ma Sói.", delete_after=6)

    @werewolf_group.command(name="guide")
    async def guide_prefix(self, ctx: commands.Context) -> None:
        """Show werewolf role guide.
        
        Usage:
            !werewolf guide
        """
        guide_cog = self.bot.get_cog("WerewolfGuideCog")
        if not guide_cog:
            await ctx.send("❌ Guide cog không được load!", delete_after=6)
            return

        embed = guide_cog.get_guide_embed()
        view = guide_cog.get_guide_view(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    werewolf_group_app = app_commands.Group(name="werewolf", description="Werewolf game commands")

    @werewolf_group_app.command(name="guide", description="Xem hướng dẫn các role trong trò chơi Ma Sói")
    async def guide_slash(self, interaction: discord.Interaction) -> None:
        """Show werewolf role guide via slash command.
        
        Usage:
            /werewolf guide
        """
        guide_cog = self.bot.get_cog("WerewolfGuideCog")
        if not guide_cog:
            await interaction.response.send_message("❌ Guide cog không được load!", ephemeral=True)
            return

        embed = guide_cog.get_guide_embed()
        view = guide_cog.get_guide_view(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WerewolfCog(bot))
    # Load the guide cog
    from .guide import WerewolfGuideCog
    await bot.add_cog(WerewolfGuideCog(bot))

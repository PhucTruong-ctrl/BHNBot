"""
Analytics Cog - Track command usage across all cogs
"""
from __future__ import annotations

from core.logging import get_logger
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import BHNBot

logger = get_logger("analytics")


class AnalyticsCog(commands.Cog):
    """Track and analyze command usage across the bot."""

    def __init__(self, bot: "BHNBot") -> None:
        self.bot = bot
        self.db = bot.db

    async def cog_load(self) -> None:
        """Ensure command_usage table exists."""
        await self._ensure_tables()
        logger.info("AnalyticsCog loaded - command tracking enabled")

    async def _ensure_tables(self) -> None:
        """Create analytics tables if they don't exist."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS command_usage (
                id SERIAL PRIMARY KEY,
                command_name VARCHAR(100) NOT NULL,
                cog_name VARCHAR(100),
                user_id BIGINT NOT NULL,
                guild_id BIGINT,
                channel_id BIGINT,
                used_at TIMESTAMPTZ DEFAULT NOW(),
                success BOOLEAN DEFAULT TRUE,
                execution_time_ms INTEGER,
                error_type VARCHAR(100)
            )
        """)
        
        # Indexes for fast queries
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_command_usage_command 
            ON command_usage(command_name)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_command_usage_user 
            ON command_usage(user_id)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_command_usage_guild 
            ON command_usage(guild_id)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_command_usage_time 
            ON command_usage(used_at)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_command_usage_cog 
            ON command_usage(cog_name)
        """)
        
        # User activity tracking table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_data JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_user 
            ON user_activity(user_id)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_guild 
            ON user_activity(guild_id)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_time 
            ON user_activity(created_at)
        """)

    async def _log_command(
        self,
        command_name: str,
        cog_name: str | None,
        user_id: int,
        guild_id: int | None,
        channel_id: int | None,
        success: bool = True,
        execution_time_ms: int | None = None,
        error_type: str | None = None,
    ) -> None:
        """Log a command usage to the database."""
        try:
            await self.db.execute(
                """
                INSERT INTO command_usage 
                (command_name, cog_name, user_id, guild_id, channel_id, success, execution_time_ms, error_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                command_name,
                cog_name,
                user_id,
                guild_id,
                channel_id,
                success,
                execution_time_ms,
                error_type,
            )
        except Exception as e:
            logger.error(f"Failed to log command usage: {e}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        """Track prefix command completions."""
        if ctx.author.bot:
            return
            
        cog_name = ctx.cog.qualified_name if ctx.cog else None
        guild_id = ctx.guild.id if ctx.guild else None
        channel_id = ctx.channel.id if ctx.channel else None
        
        await self._log_command(
            command_name=ctx.command.qualified_name if ctx.command else "unknown",
            cog_name=cog_name,
            user_id=ctx.author.id,
            guild_id=guild_id,
            channel_id=channel_id,
            success=True,
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Track prefix command errors."""
        if ctx.author.bot:
            return
        
        # Skip if command not found
        if isinstance(error, commands.CommandNotFound):
            return
            
        cog_name = ctx.cog.qualified_name if ctx.cog else None
        guild_id = ctx.guild.id if ctx.guild else None
        channel_id = ctx.channel.id if ctx.channel else None
        
        await self._log_command(
            command_name=ctx.command.qualified_name if ctx.command else "unknown",
            cog_name=cog_name,
            user_id=ctx.author.id,
            guild_id=guild_id,
            channel_id=channel_id,
            success=False,
            error_type=type(error).__name__,
        )

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, 
        interaction: discord.Interaction, 
        command: app_commands.Command | app_commands.ContextMenu
    ) -> None:
        """Track slash command completions."""
        if interaction.user.bot:
            return
            
        # Get cog name from command binding
        cog_name = None
        if hasattr(command, 'binding') and command.binding:
            if hasattr(command.binding, 'qualified_name'):
                cog_name = command.binding.qualified_name
            elif hasattr(command.binding, '__class__'):
                cog_name = command.binding.__class__.__name__
        
        guild_id = interaction.guild_id
        channel_id = interaction.channel_id
        
        await self._log_command(
            command_name=command.qualified_name,
            cog_name=cog_name,
            user_id=interaction.user.id,
            guild_id=guild_id,
            channel_id=channel_id,
            success=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Track member joins."""
        if member.bot:
            return
        try:
            await self.db.execute(
                """
                INSERT INTO user_activity (user_id, guild_id, event_type, event_data)
                VALUES (?, ?, 'join', '{}')
                """,
                member.id,
                member.guild.id,
            )
        except Exception as e:
            logger.error(f"Failed to log member join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Track member leaves."""
        if member.bot:
            return
        try:
            await self.db.execute(
                """
                INSERT INTO user_activity (user_id, guild_id, event_type, event_data)
                VALUES (?, ?, 'leave', '{}')
                """,
                member.id,
                member.guild.id,
            )
        except Exception as e:
            logger.error(f"Failed to log member leave: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, 
        member: discord.Member, 
        before: discord.VoiceState, 
        after: discord.VoiceState
    ) -> None:
        """Track voice channel join/leave for online hours."""
        if member.bot:
            return
        
        try:
            if before.channel is None and after.channel is not None:
                await self.db.execute(
                    """
                    INSERT INTO user_activity (user_id, guild_id, event_type, event_data)
                    VALUES (?, ?, 'voice_join', ?)
                    """,
                    member.id,
                    member.guild.id,
                    f'{{"channel_id": {after.channel.id}}}',
                )
            elif before.channel is not None and after.channel is None:
                await self.db.execute(
                    """
                    INSERT INTO user_activity (user_id, guild_id, event_type, event_data)
                    VALUES (?, ?, 'voice_leave', ?)
                    """,
                    member.id,
                    member.guild.id,
                    f'{{"channel_id": {before.channel.id}}}',
                )
        except Exception as e:
            logger.error(f"Failed to log voice state: {e}")
            logger.error(f"Failed to log member leave: {e}")


async def setup(bot: "BHNBot") -> None:
    await bot.add_cog(AnalyticsCog(bot))

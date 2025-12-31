import discord
import traceback
import sys
from discord.ext import commands
from core.logger import setup_logger

logger = setup_logger("ErrorHandler", "logs/core_errors.log")

class UserFeedbackError(commands.CommandError):
    """Exception for user-facing errors that should be displayed nicely."""
    def __init__(self, message, *args):
        self.message = message
        super().__init__(message, *args)

class ErrorHandler(commands.Cog):
    """Global Error Handler to catch and process command errors."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """The event triggered when an error is raised while invoking a command."""
        
        # If command has its own error handler, ignore global one
        if hasattr(ctx.command, 'on_error'):
            return

        # Get original error if it exists
        error = getattr(error, 'original', error)

        # 1. IGNORED ERRORS (Normal operation)
        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return # Ignore silently

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f"⚠️ Lệnh `{ctx.command}` đã bị vô hiệu hóa.")
            return

        # 2. USER ERRORS (Feedback needed)
        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = '{}, và {}'.format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = ' và '.join(missing)
            await ctx.send(f"⛔ Bạn thiếu quyền: **{fmt}**")
            return

        if isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = '{}, và {}'.format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = ' và '.join(missing)
            await ctx.send(f"⚠️ Bot thiếu quyền để thực hiện: **{fmt}**")
            return

        if isinstance(error, commands.CheckFailure):
            # Generic check failure (likes @checks.is_admin)
            await ctx.send("⛔ Bạn không có quyền sử dụng lệnh này.")
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Tham số không hợp lệ.\nSử dụng: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Thiếu tham số: `{error.param.name}`\nSử dụng: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Từ từ thôi! Thử lại sau **{error.retry_after:.1f}s**.", delete_after=5)
            return

        if isinstance(error, asyncio.TimeoutError):
            # Move timeout monitoring logic here
            try:
                from core.timeout_monitor import get_monitor
                timeout_monitor = get_monitor()
                timeout_monitor.record_timeout(
                    context="command_execution",
                    user_id=ctx.author.id if ctx.author else None,
                    command=ctx.command.name if ctx.command else "unknown"
                )
                logger.error(f"[TIMEOUT] Command timeout: {ctx.command} by user {ctx.author.id}")
                await ctx.send(f"⚠️ Lệnh `{ctx.command}` đã bị hủy do quá thời gian xử lý (Timeout).", delete_after=10)
            except Exception as e:
                logger.error(f"Error recording timeout: {e}")
            return

        # 3. UNHANDLED SYSTEM ERRORS (Log & Report)
        
        # Log to file
        logger.error(f'Ignoring exception in command {ctx.command}:', exc_info=error)
        
        # Log short version to console
        print(f"[ERROR] Command '{ctx.command}' failed: {error}")

        # Send polite message to user (AVOID SPAM)
        try:
            embed = discord.Embed(
                title="❌ Lỗi Hệ Thống",
                description="Đã xảy ra lỗi không mong muốn. Admin đã được thông báo.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            pass # Cannot send message, ignore

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))

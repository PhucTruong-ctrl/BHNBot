"""Discord command tracing middleware for OpenTelemetry integration."""

import functools
import time
from typing import Any, Callable, Optional, TypeVar, ParamSpec

import discord
from discord.ext import commands
from discord import app_commands
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import structlog

from core.telemetry.config import get_tracer

P = ParamSpec("P")
T = TypeVar("T")


def traced_command(
    name: Optional[str] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add OpenTelemetry tracing to Discord commands.
    
    Creates a span for each command invocation with attributes:
    - command.name: The command name
    - user.id: Discord user ID
    - guild.id: Guild ID (if in guild)
    - channel.id: Channel ID
    - duration_ms: Execution time in milliseconds
    
    Also injects trace_id into structlog context for log correlation.
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        command_name = name or func.__name__
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            interaction: Optional[discord.Interaction] = None
            for arg in args:
                if isinstance(arg, discord.Interaction):
                    interaction = arg
                    break
            
            if interaction is None:
                return await func(*args, **kwargs)
            
            tracer = get_tracer("discord.commands")
            
            with tracer.start_as_current_span(f"command.{command_name}") as span:
                start_time = time.perf_counter()
                
                span.set_attribute("command.name", command_name)
                span.set_attribute("user.id", interaction.user.id)
                span.set_attribute("user.name", str(interaction.user))
                
                if interaction.guild:
                    span.set_attribute("guild.id", interaction.guild.id)
                    span.set_attribute("guild.name", interaction.guild.name)
                
                if interaction.channel:
                    span.set_attribute("channel.id", interaction.channel.id)
                
                trace_id = format(span.get_span_context().trace_id, "032x")
                span_id = format(span.get_span_context().span_id, "016x")
                
                structlog.contextvars.bind_contextvars(
                    trace_id=trace_id,
                    span_id=span_id,
                    command=command_name,
                    user_id=interaction.user.id,
                    guild_id=interaction.guild.id if interaction.guild else None,
                )
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
                    
                finally:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_attribute("duration_ms", duration_ms)
                    structlog.contextvars.clear_contextvars()
        
        return wrapper
    return decorator


class CommandTracingCog(commands.Cog):
    """Mixin cog that adds automatic tracing to all app_commands."""
    
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        span = trace.get_current_span()
        if span.is_recording():
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.record_exception(error)

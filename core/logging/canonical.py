"""Canonical log lines for Discord command completion."""

import time
from typing import Any, Optional

import structlog

from core.logging import get_logger

_log = get_logger("canonical")


def log_command_complete(
    command: str,
    user_id: int,
    guild_id: Optional[int],
    channel_id: Optional[int],
    duration_ms: float,
    success: bool,
    error: Optional[str] = None,
    **extra: Any,
) -> None:
    """Log a single canonical entry for command completion.
    
    This produces exactly ONE log entry per command with all relevant context,
    enabling easy querying and analysis in Loki/Grafana.
    """
    log_method = _log.info if success else _log.error
    
    log_method(
        "command_complete",
        command=command,
        user_id=user_id,
        guild_id=guild_id,
        channel_id=channel_id,
        duration_ms=round(duration_ms, 2),
        success=success,
        error=error,
        **extra,
    )


class CommandTimer:
    """Context manager for timing command execution."""
    
    def __init__(
        self,
        command: str,
        user_id: int,
        guild_id: Optional[int] = None,
        channel_id: Optional[int] = None,
    ):
        self.command = command
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.start_time: float = 0
        self.success: bool = True
        self.error: Optional[str] = None
        self.extra: dict[str, Any] = {}
    
    def __enter__(self) -> "CommandTimer":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        
        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)
        
        log_command_complete(
            command=self.command,
            user_id=self.user_id,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            duration_ms=duration_ms,
            success=self.success,
            error=self.error,
            **self.extra,
        )
    
    def add_context(self, **kwargs: Any) -> None:
        self.extra.update(kwargs)
    
    def mark_failed(self, error: str) -> None:
        self.success = False
        self.error = error

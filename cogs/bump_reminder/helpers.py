"""Utility functions for bump reminder system.

Helper functions for datetime parsing, validation, and embed building.
"""

import discord
from datetime import datetime, timezone
from typing import Optional


def parse_utc_datetime(value):
    """Parse UTC datetime from ISO string or return datetime object directly.
    
    PostgreSQL/asyncpg returns datetime objects natively.
    This function handles both for backward compatibility.
    
    Args:
        value: Either ISO format string (legacy) or datetime object (PostgreSQL)
        
    Returns:
        Timezone-aware datetime in UTC, or None if input is None
    """
    if value is None:
        return None
    
    # PostgreSQL already returns datetime objects
    if isinstance(value, datetime):
        # Ensure timezone-aware
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    
    # Legacy string format (for old SQLite data)
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    
    return None


def validate_text_channel(channel) -> bool:
    """Check if channel is a TextChannel.
    
    Args:
        channel: Discord channel object (any type)
        
    Returns:
        True if channel is TextChannel, False otherwise
    """
    return isinstance(channel, discord.TextChannel)


def build_reminder_embed(elapsed_hours: int, elapsed_minutes: int) -> discord.Embed:
    """Build the bump reminder embed message.
    
    Args:
        elapsed_hours: Hours elapsed since last bump
        elapsed_minutes: Minutes elapsed (after hours)
        
    Returns:
        Configured Discord embed ready to send
    """
    embed = discord.Embed(
        title="⏰ Đến giờ bump server rồi!",
        description=(
            f"Đã qua **{elapsed_hours}h {elapsed_minutes}m** kể từ lần bump cuối.\n"
            f"Sử dụng lệnh `/bump` để đưa server lên top Disboard nhé!\n\n"
            f"**Lợi ích:**\n"
            f"• Tăng khả năng hiển thị server\n"
            f"• Thu hút thêm member mới\n"
            f"• Giúp server phát triển\n"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Reminder tự động mỗi 3 giờ • Cảm ơn bạn!")
    
    return embed


def calculate_time_remaining(total_seconds: float) -> tuple[int, int]:
    """Calculate hours and minutes from total seconds.
    
    Args:
        total_seconds: Total seconds to convert
        
    Returns:
        Tuple of (hours, minutes)
    """
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return hours, minutes

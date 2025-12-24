"""Utility functions for bump reminder system.

Helper functions for datetime parsing, validation, and embed building.
"""

import discord
from datetime import datetime, timezone
from typing import Optional


def parse_utc_datetime(iso_string: Optional[str]) -> Optional[datetime]:
    """Parse ISO format string to timezone-aware UTC datetime.
    
    Args:
        iso_string: ISO format datetime string (may be naive or aware)
        
    Returns:
        Timezone-aware datetime in UTC, or None if input is None
        
    Raises:
        ValueError: If iso_string is invalid format
    """
    if not iso_string:
        return None
    
    dt = datetime.fromisoformat(iso_string)
    
    # Ensure timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt


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

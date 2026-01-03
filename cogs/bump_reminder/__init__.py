"""Bump Reminder Package.

DISBOARD bump reminder system with automatic detection and periodic notifications.

Components:
- detector: Listens for and processes DISBOARD bump confirmations
- task: Runs periodic checks and sends reminders
- models: Data models for bump configurations
- helpers: Utility functions
- constants: Configuration values
"""

from .cog import BumpReminderCog

async def setup(bot):
    """Load the Bump Reminder cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(BumpReminderCog(bot))

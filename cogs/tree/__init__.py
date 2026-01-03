"""Tree growth system for community engagement.

Features:
- 6-level tree progression with seasonal scaling
- Contributor tracking and rankings
- Harvest events with tiered rewards
- 24h server-wide buff system
- Memorabilia items
"""

from .cog import TreeCog

__version__ = "2.0.0"  # Refactored modular version

async def setup(bot):
    """Load the Tree cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(TreeCog(bot))

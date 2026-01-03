"""Bau Cua game package.

Vietnamese dice game (Bầu Cua Tôm Cá Gà Nai) with:
- Interactive betting interface
- Animated dice rolling
- Automatic balance updates
- Achievement tracking
"""

from .cog import BauCuaCog

__version__ = "2.0.0"  # Refactored modular version

async def setup(bot):
    """Load the Bau Cua cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(BauCuaCog(bot))

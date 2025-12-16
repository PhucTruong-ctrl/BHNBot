"""Fishing game package."""

from .cog import FishingCog
from .constants import ALL_FISH, GIFT_ITEMS

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

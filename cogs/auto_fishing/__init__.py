from discord.ext import commands
from .cog import AutoFishingCog


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoFishingCog(bot))

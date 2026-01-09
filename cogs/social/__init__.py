from discord.ext import commands
from .cog import SocialCog


async def setup(bot: commands.Bot):
    await bot.add_cog(SocialCog(bot))

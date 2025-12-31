from .cog import EconomyCog

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

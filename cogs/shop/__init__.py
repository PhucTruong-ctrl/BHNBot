from .cog import ShopCog

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

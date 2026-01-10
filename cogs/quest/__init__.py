from .cog import QuestCog

async def setup(bot):
    await bot.add_cog(QuestCog(bot))

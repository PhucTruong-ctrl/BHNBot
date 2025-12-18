from .cog import RelationshipCog

async def setup(bot):
    await bot.add_cog(RelationshipCog(bot))

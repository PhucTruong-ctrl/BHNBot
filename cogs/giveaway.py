import discord
from discord.ext import commands

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('-> Module Giveaway đã sẵn sàng!')

# Hàm setup bắt buộc phải có
async def setup(bot):
    await bot.add_cog(Giveaway(bot))
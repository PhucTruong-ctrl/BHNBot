import discord
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('-> Module General đã sẵn sàng!')

    @commands.command()
    async def ping(self, ctx):
        """Kiểm tra độ trễ của bot"""
        await ctx.send(f'Pong! Độ trễ: {round(self.bot.latency * 1000)}ms')

# Hàm setup bắt buộc để load Cog
async def setup(bot):
    await bot.add_cog(General(bot))
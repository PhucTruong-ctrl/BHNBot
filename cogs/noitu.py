import discord
from discord.ext import commands

class NoiTu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('-> Module Nối Từ đã sẵn sàng!')

# Hàm setup bắt buộc phải có
async def setup(bot):
    await bot.add_cog(NoiTu(bot))
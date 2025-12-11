import discord
from discord.ext import commands
from discord import app_commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Module General!')

    @commands.command()
    async def ping(self, ctx):
        """Kiểm tra độ trễ của bot"""
        await ctx.send(f'Pong! Độ trễ: {round(self.bot.latency * 1000)}ms')

    @commands.command(name="help")
    async def help_prefix(self, ctx):
        """Hiển thị danh sách lệnh"""
        embed = discord.Embed(
            title="Danh sách lệnh BHNBot",
            color=discord.Color.blue(),
            description="Sử dụng các lệnh dưới đây để tương tác với bot"
        )
        
        # Game commands
        embed.add_field(
            name="Nối Từ",
            value="• `!reset` - Reset game trong kênh\n"
                  "• Nhắn từ trong kênh để nối tiếp",
            inline=False
        )
        
        # Word management
        embed.add_field(
            name="Quản lý từ vựng",
            value="• `!themtu từ1 từ2` - Đề xuất từ mới\n"
                  "• Admin sẽ phê duyệt trước khi thêm",
            inline=False
        )
        # Utility
        embed.add_field(
            name="Tiện ích",
            value="• `!ping` - Kiểm tra độ trễ bot\n"
                  "• `!help` - Hiển thị trợ giúp này",
            inline=False
        )
        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Hiển thị danh sách lệnh")
    async def help_slash(self, interaction: discord.Interaction):
        """Hiển thị danh sách lệnh"""
        embed = discord.Embed(
            title="Danh sách lệnh BHNBot",
            color=discord.Color.blue(),
            description="Sử dụng các lệnh dưới đây để tương tác với bot"
        )
        
        # Game commands
        embed.add_field(
            name="Nối Từ",
            value="• `!reset` - Reset game trong kênh\n"
                  "• Nhắn từ trong kênh để nối tiếp",
            inline=False
        )
        
        # Word management
        embed.add_field(
            name="Quản lý từ vựng",
            value="• `!themtu từ1 từ2` - Đề xuất từ mới\n"
                  "• Admin sẽ phê duyệt trước khi thêm",
            inline=False
        )
        
        # Configuration (Admin only)
        embed.add_field(
            name="Cấu hình",
            value="• `/config set kenh_noitu <channel>` - Đặt kênh chơi nối từ\n"
                  "• `/config set kenh_admin <channel>` - Đặt kênh phê duyệt từ\n"
                  "• `/config set kenh_giveaway <channel>` - Đặt kênh giveaway",
            inline=False
        )
        
        # Utility
        embed.add_field(
            name="🔧 Tiện ích",
            value="• `!ping` - Kiểm tra độ trễ bot\n"
                  "• `!help` / `/help` - Hiển thị trợ giúp này\n"
                  "• `!ntrank` / `/ntrank` - Xem xếp hạng nối từ",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @commands.command(name="ntrank")
    async def ntrank_prefix(self, ctx):
        """Hiển thị xếp hạng nối từ"""
        await self._show_ranking(ctx)

    @app_commands.command(name="ntrank", description="Xem xếp hạng nối từ")
    async def ntrank_slash(self, interaction: discord.Interaction):
        """Hiển thị xếp hạng nối từ"""
        await self._show_ranking(interaction)

    async def _show_ranking(self, ctx_or_interaction):
        """Hiển thị xếp hạng"""
        import aiosqlite
        
        DB_PATH = "./data/database.db"
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT username, wins, correct_words FROM player_stats ORDER BY wins DESC, correct_words DESC LIMIT 10"
                ) as cursor:
                    rows = await cursor.fetchall()
            
            if not rows:
                msg = "Chưa có ai chơi cả 🥺"
                if isinstance(ctx_or_interaction, commands.Context):
                    await ctx_or_interaction.send(msg)
                else:
                    await ctx_or_interaction.response.send_message(msg, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏆 Xếp hạng Nối Từ",
                color=discord.Color.gold(),
                description="Top 10 người chơi"
            )
            
            # Medal emojis
            medals = ["🥇", "🥈", "🥉"]
            
            rank_text = ""
            for idx, (username, wins, correct_words) in enumerate(rows, 1):
                medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                rank_text += f"{medal} **{username}** - {wins} thắng, {correct_words} từ\n"
            
            embed.description = rank_text
            embed.set_footer(text="Xếp hạng dựa trên số thắng và số từ chính xác")
            
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(embed=embed)
            else:
                await ctx_or_interaction.response.send_message(embed=embed)
        
        except Exception as e:
            msg = f"Lỗi khi lấy xếp hạng: {e}"
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(msg)
            else:
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)

# Hàm setup bắt buộc để load Cog
async def setup(bot):
    await bot.add_cog(General(bot))
import discord
from discord.ext import commands
from discord import app_commands

from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
import functools


from core.logger import setup_logger

logger = setup_logger("GeneralCog", "cogs/general.log")

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Module General!')

    @commands.command()
    async def ping(self, ctx):
        """Kiểm tra độ trễ của bot"""
        import time
        
        # Measure REST latency (bot response time)
        start = time.time()
        msg = await ctx.send("Đang đo...")
        rest_latency = (time.time() - start) * 1000
        
        # Gateway latency (WebSocket)
        gateway_latency = self.bot.latency * 1000
        
        # Database latency
        db_start = time.time()
        try:
            from database_manager import db_manager
            await db_manager.fetchone("SELECT 1")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        db_latency = (time.time() - db_start) * 1000
        
        # Create detailed embed
        embed = discord.Embed(
            title="🏓 Ping Details",
            color=discord.Color.blue(),
            description=f"**Discord REST latency:** {rest_latency:.0f}ms\n"
                       f"**Discord Gateway (WS) latency:** {gateway_latency:.0f}ms\n"
                       f"**Database response time:** {db_latency:.2f}ms\n"
                       f"**Bot processing ping:** {(rest_latency - gateway_latency):.0f}ms"
        )
        embed.set_footer(text=f"Mèo Béo | Latency: {round(gateway_latency)}ms")
        
        await msg.edit(content=None, embed=embed)

    @commands.command(name="avatar")
    async def avatar_prefix(self, ctx, user: discord.User = None):
        """Xem avatar của user (hoặc chính mình)"""
        user = user or ctx.author
        embed = discord.Embed(
            title=f"Avatar của {user.name}",
            color=discord.Color.random()
        )
        embed.set_image(url=user.avatar.url if user.avatar else user.default_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name="avatar", description="Xem avatar của user")
    @app_commands.describe(user="User muốn xem avatar (để trống để xem avatar của bạn)")
    async def avatar_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Xem avatar của user"""
        user = user or interaction.user
        embed = discord.Embed(
            title=f"Avatar của {user.name}",
            color=discord.Color.random()
        )
        embed.set_image(url=user.avatar.url if user.avatar else user.default_avatar.url)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="help")
    async def help_prefix(self, ctx):
        """Hiển thị danh sách lệnh"""
        is_admin = ctx.author.guild_permissions.administrator if ctx.guild else False
        await self._send_help(ctx, is_admin)

    @app_commands.command(name="help", description="Hiển thị danh sách lệnh")
    async def help_slash(self, interaction: discord.Interaction):
        """Hiển thị danh sách lệnh"""
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        await self._send_help(interaction, is_admin)

    async def _send_help(self, ctx_or_interaction, is_admin: bool = False):
        """Comprehensive help command with admin filtering.
        
        Shows all available commands categorized by feature.
        Admin-only commands are only displayed to users with Administrator permission.
        
        Args:
            ctx_or_interaction: Discord Context or Interaction
            is_admin: Whether user has admin permissions
        """
        embed = discord.Embed(
            title="📚 Hướng Dẫn Sử Dụng - Bên Hiên Nhà Bot",
            color=discord.Color.blue(),
            description="Danh sách đầy đủ các lệnh có sẵn\n"
                       "_Bot hỗ trợ cả Slash Command `/` và Prefix Command `!`_"
        )
        
        # ==================== ECONOMY ====================
        economy_cmds = [
            "`/chao` - Nhận quà hàng ngày (5h-10h sáng)",
            "`/tuido` `!tuido` - Xem túi đồ và số hạt",
            "`/top` `!top` - Bảng xếp hạng top 10 giàu nhất",
            "`/hoso` `!hoso [user]` - Xem thẻ hồ sơ cá nhân"
        ]
        embed.add_field(
            name="💰 Kinh Tế",
            value="\n".join(economy_cmds),
            inline=False
        )
        
        # ==================== FISHING ====================
        fishing_cmds = [
            "`/cauca` `!cauca` - Câu cá (cooldown 30s)",
            "`/banca` `!banca` - Bán cá kiếm tiền",
            "`/moruong` `!moruong` - Mở rương kho báu",
            "`/nangcap` `!nangcap` - Nâng cấp cần câu",
            "`/bosuutap` `!bosuutap` - Xem bộ sưu tập cá",
            "`/huyenthoai` `!huyenthoai` - Bảng Vàng Huyền Thoại",
            "",
            "**Cá Huyền Thoại:**",
            "`/hiente` `!hiente` - Hiến tế cá (Thuồng Luồng)",
            "`/chetao` `!chetao` - Chế tạo Tinh Cầu",
            "`/dosong` `!dosong` - Dò Cá Voi 52hz",
            "`/ghepbando` `!ghepbando` - Ghép Bản Đồ Cthulhu",
            "`/bonphan` `!bonphan` - Bón phân cho cây",
            "`/taiche` `!taiche` - Tái chế rác (10 rác → 1 phân)"
        ]
        embed.add_field(
            name="🎣 Câu Cá & Khám Phá",
            value="\n".join(fishing_cmds),
            inline=False
        )
        
        # ==================== SHOP ====================
        shop_cmds = [
            "`/mua` `!mua [item] [số_lượng]` - Mua vật phẩm",
            "`/sudung` `!sudung [item]` - Dùng buff câu cá"
        ]
        embed.add_field(
            name="🛍️ Cửa Hàng",
            value="\n".join(shop_cmds),
            inline=False
        )
        
        # ==================== SOCIAL ====================
        social_cmds = [
            "`/tangqua` - Tặng quà tăng thân thiết",
            "`/thanthiet` `!thanthiet [user]` - Xem độ thân thiết",
            "`/kethop` - Mời nuôi thú cưng chung",
            "`/nuoi` - Chăm sóc pet (Cho ăn/Vuốt ve)"
        ]
        embed.add_field(
            name="🤝 Xã Hội",
            value="\n".join(social_cmds),
            inline=False
        )
        
        # ==================== COMMUNITY ====================
        community_cmds = [
            "`/gophat` - Góp hạt nuôi cây server",
            "`/cay` - Xem trạng thái cây server",
            "`/giveaway create` - Tạo giveaway mới",
            "`/giveaway end` - Kết thúc giveaway sớm"
        ]
        embed.add_field(
            name="🌳 Cộng Đồng",
            value="\n".join(community_cmds),
            inline=False
        )
        
        # ==================== GAMES ====================
        games_cmds = [
            "`/baucua` `!baucua` - Bầu Cua Tôm Cá Gà Nai",
            "`/masoi` - Chơi Ma Sói",
            "`/themtu` `!themtu` - Đề xuất từ mới Nối Từ",
            "`/ntrank` `!ntrank` - BXH Nối Từ",
            "`/reset` `!reset` - Reset game trong kênh"
        ]
        embed.add_field(
            name="🎮 Trò Chơi",
            value="\n".join(games_cmds),
            inline=False
        )
        
        # ==================== UTILITY ====================
        utility_cmds = [
            "`/avatar` `!avatar [user]` - Xem avatar",
            "`/help` `!help` - Lệnh này",
            "`!ping` - Kiểm tra độ trễ bot"
        ]
        embed.add_field(
            name="🔧 Tiện Ích",
            value="\n".join(utility_cmds),
            inline=False
        )
        
        # ==================== ADMIN ONLY ====================
        # Only show this section if user is admin
        if is_admin:
            admin_cmds = [
                "**Quản Lý Hệ Thống:**",
                "`/config` `!config` - Cài đặt kênh chức năng",
                "`/exclude add/remove` - Chặn kênh nhận hạt chat",
                "`/exclude_list` - Xem danh sách kênh loại trừ",
                "`/sync` `!sync` - Đồng bộ slash commands",
                "",
                "**Quản Lý Game:**",
                "`/themhat` `!themhat <user> <số>` - Thêm hạt",
                "`/themitem` `!themitem <user> <item>` - Thêm item",
                "`/sukiencauca` `!sukiencauca` - Trigger sự kiện câu cá",
                "`/thuhoach` - Thu hoạch cây server"
            ]
            embed.add_field(
                name="🔒 Admin Only (Chỉ Quản Trị Viên)",
                value="\n".join(admin_cmds),
                inline=False
            )
        
        embed.set_footer(text="Gõ / hoặc ! + tên lệnh để sử dụng • Developed by Bên Hiên Nhà")
        
        # Send message
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            # Slash command - send ephemeral (only user sees it)
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)

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
        from database_manager import get_stat_leaderboard
        
        try:
            # Query user_stats table for noi tu correct words
            rows = await get_stat_leaderboard('noitu', 'correct_words', 10)
            
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
            for idx, (_, username, correct_words) in enumerate(rows, 1):
                medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                rank_text += f"{medal} **{username}** - {correct_words} từ đúng\n"
            
            embed.description = rank_text
            embed.set_footer(text="Xếp hạng dựa trên số từ đúng")
            
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
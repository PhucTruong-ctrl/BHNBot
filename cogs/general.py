import discord
from discord.ext import commands
from discord import app_commands

from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
import functools

from core.logging import get_logger
logger = get_logger("general")


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("module_loaded", module="general")

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
            "`/chao` - Nhận quà hàng ngày (5h-10h sáng) + streak bonus",
            "`/tuido` `!tuido` - Xem túi đồ, số hạt, cần câu",
            "`/top` `!top` - Bảng xếp hạng top 10 giàu nhất",
            "`/mua [item]` - Mua vật phẩm từ shop",
            "`/sudung [item]` - Sử dụng vật phẩm buff"
        ]
        embed.add_field(
            name="💰 Kinh Tế & Cửa Hàng",
            value="\n".join(economy_cmds),
            inline=False
        )
        
        # ==================== FISHING ====================
        fishing_cmds = [
            "`/cauca` - Câu cá (cooldown theo cấp cần)",
            "`/banca` - Bán cá kiếm tiền",
            "`/moruong` - Mở rương kho báu",
            "`/nangcap` - Nâng cấp cần câu",
            "`/bosuutap` - Xem bộ sưu tập cá",
            "`/huyenthoai` - Bảng Vàng Huyền Thoại",
            "`/lichcauca` - Xem lịch sự kiện câu cá",
            "",
            "**Cá Huyền Thoại:**",
            "`/hiente` - Hiến tế (Thuồng Luồng)",
            "`/chetao` - Chế tạo Tinh Cầu (Cá Ngân Hà)",
            "`/dosong` - Máy dò sóng (52Hz)",
            "`/ghepbando` - Ghép bản đồ (Cthulhu)",
            "`/bonphan` - Bón phân cho cây"
        ]
        embed.add_field(
            name="🎣 Câu Cá & Khám Phá",
            value="\n".join(fishing_cmds),
            inline=False
        )
        
        # ==================== AUTO FISHING ====================
        auto_fishing_cmds = [
            "`/autocauca` - Mở dashboard câu cá tự động",
            "• Nâng cấp: Efficiency, Duration, Quality",
            "• Tinh luyện cá thành essence"
        ]
        embed.add_field(
            name="🤖 Câu Cá Tự Động",
            value="\n".join(auto_fishing_cmds),
            inline=False
        )
        
        # ==================== TOURNAMENT ====================
        tournament_cmds = [
            "`/giaidau create [fee]` - Tổ chức giải đấu (VIP 1+)",
            "`/giaidau join [id]` - Tham gia giải đấu",
            "`/giaidau rank` - Xem bảng xếp hạng"
        ]
        embed.add_field(
            name="🏆 Giải Đấu Câu Cá",
            value="\n".join(tournament_cmds),
            inline=False
        )
        
        # ==================== AQUARIUM ====================
        aquarium_cmds = [
            "`/nha khoitao` - Tạo nhà (Thread trong Forum)",
            "`/trangtri cuahang` - Mở shop nội thất",
            "`/trangtri sapxep` - Đặt/gỡ nội thất (5 vị trí)",
            "`/trangtri theme` - Đổi hình nền (VIP 2+)",
            "`/thamnha` - Ghé thăm nhà người khác",
            "`/taiche` - Tái chế rác → Xu Lá + Phân Bón"
        ]
        embed.add_field(
            name="🏠 Hồ Cá & Nhà Cửa",
            value="\n".join(aquarium_cmds),
            inline=False
        )
        
        # ==================== SOCIAL & RELATIONSHIP ====================
        social_cmds = [
            "`/tangqua [user]` - Tặng quà (có thể ẩn danh)",
            "`/qua-thongke` - Xem thống kê quà tặng",
            "`/banthan moi/chapnhan/danhsach` - Hệ thống bạn thân (max 3)",
            "`/tute` - Xem điểm tử tế",
            "`/tutetop` - BXH người tử tế nhất"
        ]
        embed.add_field(
            name="🤝 Xã Hội & Bạn Thân",
            value="\n".join(social_cmds),
            inline=False
        )
        
        # ==================== PROFILE ====================
        profile_cmds = [
            "`/hoso` - Xem thẻ hồ sơ cá nhân",
            "`/theme` - Chọn theme hồ sơ",
            "`/bio [text]` - Đặt bio cá nhân",
            "`/thanhtuu` - Xem thành tựu đã đạt"
        ]
        embed.add_field(
            name="👤 Hồ Sơ Cá Nhân",
            value="\n".join(profile_cmds),
            inline=False
        )
        
        # ==================== COMMUNITY ====================
        community_cmds = [
            "`/cay` - Xem trạng thái cây server",
            "`/gophat [amount]` - Góp hạt nuôi cây",
            "`/tuoi` - Tưới cây (1 lần/ngày, nhận XP + reward)",
            "`/huyhieu` - Xem huy hiệu đóng góp",
            "`/nhiemvu` - Xem nhiệm vụ hàng ngày server"
        ]
        embed.add_field(
            name="🌳 Cộng Đồng & Cây Server",
            value="\n".join(community_cmds),
            inline=False
        )
        
        # ==================== GIVEAWAY ====================
        giveaway_cmds = [
            "`/giveaway create` - Tạo giveaway mới",
            "`/giveaway end` - Kết thúc giveaway sớm"
        ]
        embed.add_field(
            name="🎁 Giveaway",
            value="\n".join(giveaway_cmds),
            inline=False
        )
        
        # ==================== GAMES ====================
        games_cmds = [
            "`/baucua` - Bầu Cua Tôm Cá Gà Nai",
            "`/xidach [bet]` - Xì Dách (Blackjack Việt Nam)",
            "`/masoi create` - Tạo bàn Ma Sói",
            "`/masoi guide` - Hướng dẫn vai trò Ma Sói",
            "",
            "**Nối Từ:** Gõ từ tiếp theo trong kênh",
            "`/themtu` - Đề xuất từ mới",
            "`/ntrank` - BXH Nối Từ",
            "`/resetnoitu` - Reset game (anti-troll 5 phút)"
        ]
        embed.add_field(
            name="🎮 Trò Chơi",
            value="\n".join(games_cmds),
            inline=False
        )
        
        # ==================== MUSIC ====================
        music_cmds = [
            "`/play [query]` - Phát nhạc YouTube/Spotify/SoundCloud",
            "`/skip` `/pause` `/stop` - Điều khiển phát nhạc",
            "`/queue` `/nowplaying` - Xem hàng đợi/bài đang phát",
            "`/volume [0-100]` - Điều chỉnh âm lượng",
            "`/loop [off/track/queue]` - Chế độ lặp",
            "`/shuffle` - Xáo trộn hàng đợi",
            "`/filter [effect]` - Hiệu ứng: lofi, nightcore, bass...",
            "`/247` - Bật/tắt chế độ 24/7",
            "",
            "**Playlist:** `/playlist create/add/play/list/delete`"
        ]
        embed.add_field(
            name="🎵 Nhạc",
            value="\n".join(music_cmds),
            inline=False
        )
        
        # ==================== SEASONAL EVENTS ====================
        seasonal_cmds = [
            "`/sukien info` - Xem event đang diễn ra",
            "`/sukien thamgia` - Tham gia event",
            "`/sukien tiendo` - Xem tiến độ cá nhân",
            "`/sukien cuahang` - Mở shop event",
            "`/sukien diemdanh` - Điểm danh nhận thưởng",
            "`/danhhieu xem/trangbi` - Xem/đeo danh hiệu"
        ]
        embed.add_field(
            name="🎄 Sự Kiện Theo Mùa",
            value="\n".join(seasonal_cmds),
            inline=False
        )
        
        # ==================== VIP ====================
        vip_cmds = [
            "`/thuongluu b` - Mua VIP (Bạc/Vàng/Kim Cương)",
            "`/thuongluu s` - Xem trạng thái VIP",
            "`/thuongluu t` - BXH VIP"
        ]
        embed.add_field(
            name="💎 VIP",
            value="\n".join(vip_cmds),
            inline=False
        )
        
        # ==================== UTILITY ====================
        utility_cmds = [
            "`/avatar [user]` - Xem avatar",
            "`/help` - Lệnh này",
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
                "**Cài Đặt Server:**",
                "`/config set` - Cài đặt kênh chức năng",
                "`/exclude add/remove` - Chặn kênh nhận hạt chat",
                "`/reset` - Reset game trong kênh",
                "",
                "**Quản Lý Tài Nguyên:**",
                "`/themhat <user> <số>` - Thêm hạt",
                "`/themitem <user> <item>` - Thêm item",
                "`/themxu <user> <số>` - Thêm Xu Lá",
                "`/thuhoach` - Thu hoạch cây server",
                "",
                "**Hệ Thống:**",
                "`/sync` - Đồng bộ slash commands",
                "`/healthcheck` - Kiểm tra sức khỏe bot",
                "`!cog load/reload/unload` - Quản lý modules",
                "",
                "**Sự Kiện:**",
                "`/sukien_admin create/end` - Quản lý event",
                "`/sukien_test start/stop` - Test event"
            ]
            embed.add_field(
                name="🔒 Admin Only",
                value="\n".join(admin_cmds),
                inline=False
            )
        
        embed.set_footer(text="Gõ / + tên lệnh để sử dụng • Developed by Bên Hiên Nhà")
        
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
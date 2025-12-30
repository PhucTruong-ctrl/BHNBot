import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
import functools

DB_PATH = "./data/database.db"
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
            from core.database import db_manager
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

    # ==================== PROFILE CARD ====================

    @app_commands.command(name="hoso", description="Xem profile card")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    async def profile_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """View profile card"""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        
        try:
            from database_manager import get_user_balance, get_leaderboard
            
            seeds = await get_user_balance(target_user.id)
            
            # Get rank
            leaderboard = await get_leaderboard(1000)  # Get enough to find rank
            rank = 999
            for i, (uid, uname, seed_count) in enumerate(leaderboard, 1):
                if uid == target_user.id:
                    rank = i
                    break
            
            # Create profile card image
            profile_img = await self._create_profile_card_new(target_user, seeds, rank)
            
            # Send as file
            file = discord.File(profile_img, filename="profile.png")
            await interaction.followup.send(file=file)
        
        except Exception as e:
            await interaction.followup.send(f"Lỗi tạo profile: {e}")
            logger.error(f"[PROFILE] Error: {e}", exc_info=True)

    @commands.command(name="hoso", description="Xem profile card")
    async def profile_prefix(self, ctx, user: discord.User = None):
        """View profile card via prefix"""
        target_user = user or ctx.author
        
        try:
            from database_manager import get_user_balance, get_leaderboard
            
            seeds = await get_user_balance(target_user.id)
            
            # Get rank
            leaderboard = await get_leaderboard(1000)  # Get enough to find rank
            rank = 999
            for i, (uid, uname, seed_count) in enumerate(leaderboard, 1):
                if uid == target_user.id:
                    rank = i
                    break
            
            # Create profile card image
            profile_img = await self._create_profile_card_new(target_user, seeds, rank)
            
            # Send as file
            file = discord.File(profile_img, filename="profile.png")
            await ctx.send(file=file)
        
        except Exception as e:
            await ctx.send(f"Lỗi tạo profile: {e}")
            logger.error(f"[PROFILE] Error: {e}", exc_info=True)

    def _generate_profile_image_sync(self, user_data, avatar_bytes):
        """Synchronous CPU-bound Pillow image generation (runs in executor)"""
        import os
        
        # Unpack user data
        display_name = user_data['display_name']
        seeds = user_data['seeds']
        rank = user_data['rank']
        
        # --- CONFIGURATION ---
        COLOR_BG = (245, 240, 235)
        COLOR_BORDER = (139, 90, 43)
        COLOR_TEXT_MAIN = (74, 59, 42)
        COLOR_TEXT_ACCENT = (92, 138, 69)
        COLOR_BAR_BG = (224, 224, 224)
        COLOR_BAR_FILL = (118, 200, 147)
        COLOR_HEART = (255, 107, 107)
        
        WIDTH, HEIGHT = 900, 300
        
        # Load fonts
        def load_font(name, size, fallback_font="arial.ttf"):
            font_path = f"./assets/{name}"
            try:
                return ImageFont.truetype(font_path, size)
            except Exception as e:
                try:
                    return ImageFont.truetype(fallback_font, size)
                except Exception as e:
                    return ImageFont.load_default()

        font_main = load_font("PatrickHand-Regular.ttf", 45)
        font_rank = load_font("PatrickHand-Regular.ttf", 18)
        font_info = load_font("Nunito-Bold.ttf", 16)
        font_small = load_font("Nunito-Bold.ttf", 14)
        
        # Create base image
        bg_path = "./assets/card_bg_ghibli.png"
        if os.path.exists(bg_path):
            try:
                img = Image.open(bg_path).resize((WIDTH, HEIGHT))
            except Exception as e:
                img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
        else:
            img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
            
        draw = ImageDraw.Draw(img, 'RGBA')
        
        if not os.path.exists(bg_path):
            draw.rectangle((5, 5, WIDTH-5, HEIGHT-5), outline=COLOR_BORDER, width=3)
        
        # --- AVATAR SECTION ---
        avatar_size = 200
        avatar = Image.open(avatar_bytes).convert('RGBA').resize((avatar_size, avatar_size))
        
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        avatar_x, avatar_y = 25, 50
        img.paste(avatar, (avatar_x, avatar_y), mask)
        draw.ellipse((avatar_x-5, avatar_y-5, avatar_x+avatar_size+5, avatar_y+avatar_size+5), 
                     outline=COLOR_BORDER, width=4)
        
        # --- INFO SECTION ---
        info_x = 280
        
        draw.text((info_x, 90), display_name, font=font_main, fill=COLOR_TEXT_MAIN)
        
        rank_title = self._get_rank_title_no_emoji(seeds)
        draw.text((info_x, 145), f"Hạng: {rank_title} (#{rank})", font=font_rank, fill=COLOR_TEXT_ACCENT)
        
        # Progress Bar
        next_milestone = 50
        if seeds >= 5000: next_milestone = 10000
        elif seeds >= 1000: next_milestone = 5000
        elif seeds >= 500: next_milestone = 1000
        elif seeds >= 200: next_milestone = 500
        elif seeds >= 50: next_milestone = 200
            
        progress = min(seeds / next_milestone, 1.0)
        
        bar_x, bar_y = info_x, 175
        bar_w, bar_h = 335, 15
        
        draw.text((info_x + bar_w - 100, 150), f"{seeds}/{next_milestone}", font=font_info, fill=COLOR_TEXT_MAIN)
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=12, fill=COLOR_BAR_BG)
        
        if progress > 0:
            fill_w = int(bar_w * progress)
            draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h)], radius=12, fill=COLOR_BAR_FILL)
            


        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, 'PNG')
        img_bytes.seek(0)
        return img_bytes

    async def _create_profile_card_new(self, user, seeds, rank):
        """Download avatars then generate profile card in executor (non-blocking)"""
        import aiohttp
        
        # Prepare user data
        user_data = {
            'display_name': user.display_name,
            'seeds': seeds,
            'rank': rank
        }
        
        # Download user avatar
        user_avatar_url = str(user.avatar.url if user.avatar else user.default_avatar.url)
        async with aiohttp.ClientSession() as session:
            async with session.get(user_avatar_url) as resp:
                avatar_bytes = io.BytesIO(await resp.read())
        

        
        # Run CPU-bound image generation in executor to avoid blocking
        loop = asyncio.get_running_loop()
        img_bytes = await loop.run_in_executor(
            None,
            self._generate_profile_image_sync,
            user_data,
            avatar_bytes
        )
        
        return img_bytes



    def _get_rank_title_no_emoji(self, seeds: int) -> str:
        """Get rank title based on seeds earned (without emoji)"""
        if seeds < 50:
            return "Người Gieo Hạt"
        elif seeds < 200:
            return "Nảy Mầm"
        elif seeds < 500:
            return "Cây Non"
        elif seeds < 1000:
            return "Trưởng Thành"
        elif seeds < 5000:
            return "Ra Hoa"
        else:
            return "Cây Đại Thụ"

    def _get_rank_title(self, seeds: int) -> str:
        """Get rank title based on seeds earned"""
        if seeds < 50:
            return "🌱 Người Gieo Hạt"
        elif seeds < 200:
            return "🌿 Nảy Mầm"
        elif seeds < 500:
            return "🎋 Cây Non"
        elif seeds < 1000:
            return "🌳 Trưởng Thành"
        elif seeds < 5000:
            return "🌸 Ra Hoa"
        else:
            return "🍎 Cây Đại Thụ"

# Hàm setup bắt buộc để load Cog
async def setup(bot):
    await bot.add_cog(General(bot))
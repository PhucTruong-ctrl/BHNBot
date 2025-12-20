import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
import functools

DB_PATH = "./data/database.db"

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
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("SELECT 1")
        except:
            pass
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
        """Helper to send help embed"""
        embed = discord.Embed(
            title="📖 Danh sách lệnh BHNBot",
            color=discord.Color.blue(),
            description="Bot hỗ trợ cả **Slash Command (/)** và **Prefix Command (!)**.\n_Các lệnh đánh dấu (/) là chỉ dùng Slash._"
        )
        
        # 1. Fishing
        embed.add_field(
            name="🎣 Câu Cá & Khám Phá",
            value="• `/cauca` (!cauca) - Câu cá (cooldown 30s)\n"
                  "• `/banca` (!banca) - Bán cá (VD: `/banca ca_loc`)\n"
                  "• `/moruong` (!moruong) - Mở rương kho báu\n"
                  "• `/hiente` (!hiente) - Hiến tế cá (Gọi Thuồng Luồng)\n"
                  "• `/chetao` (!chetao) - Chế tạo mồi/vật phẩm\n"
                  "• `/dosong` (!dosong) - Dò tìm Cá Voi 52Hz\n"
                  "• `/ghepbando` (!ghepbando) - Ghép bản đồ kho báu\n"
                  "• `/taiche` (!taiche) - Tái chế rác thành phân bón",
            inline=False
        )

        # 2. Economy
        embed.add_field(
            name="💰 Kinh Tế & Túi Đồ",
            value="• `/chao` (Slash only) - Nhận quà sáng (5h-10h)\n"
                  "• `/tuido` (!tuido) - Xem túi đồ và hạt\n"
                  "• `/top` (!top) - Xem BXH đại gia hạt",
            inline=False
        )

        # 3. Shop & Items
        embed.add_field(
            name="🛍️ Cửa Hàng",
            value="• `/mua` (!mua) - Mua quà & vật phẩm từ cửa hàng",
            inline=False
        )

        # 4. Relationship & Pet
        embed.add_field(
            name="🐱 Thú Cưng & Quan Hệ",
            value="• `/tangqua` (Slash only) - Tặng quà tăng thân thiết\n"
                  "• `/thanthiet` (!thanthiet) - Xem điểm thân thiết\n"
                  "• `/kethop` (Slash only) - Mời nuôi pet chung\n"
                  "• `/nuoi` (Slash only) - Chăm sóc pet (cho ăn/vuốt ve)",
            inline=False
        )

        # 5. Games
        embed.add_field(
            name="🎮 Minigames",
            value="• `/baucua` (!baucua) - Chơi Bầu Cua Tôm Cá\n"
                  "• `/masoi` (!masoi) - Chơi Ma Sói\n"
                  "• `/ntrank` (!ntrank) - BXH Nối Từ\n"
                  "• `/themtu` (!themtu) - Đề xuất từ mới cho Nối Từ\n"
                  "• `/reset` (!reset) - Reset game (Nối từ/Ma sói) tại kênh",
            inline=False
        )

        # 6. Utility
        embed.add_field(
            name="🔧 Tiện Ích",
            value="• `/hoso` (!hoso) - Xem thẻ hồ sơ cá nhân đẹp\n"
                  "• `/avatar` (!avatar) - Xem ảnh đại diện\n"
                  "• `!ping` - Kiểm tra mạng bot",
            inline=False
        )
        
        # 7. Giveaway (Host)
        embed.add_field(
            name="🎁 Giveaway",
            value="• `/giveaway create` (Slash only) - Tạo Giveaway mới\n" 
                  "• `/giveaway end` (Slash only) - Kết thúc Giveaway sớm\n",
            inline=False
        )

        # 8. Admin Only (Separate field)
        if is_admin:
            embed.add_field(
                name="⚙️ Admin / Quản Lý (Admin Only)",
                value="• `/config set ...` - Cài đặt kênh (Nối từ, Log, v.v.)\n"
                      "• `/exclude add/remove` - Chặn kênh nhận hạt chat\n"
                      "• `/themhat` (!themhat) - Cộng hạt cho member\n"
                      "• `/sync` (!sync) - Đồng bộ lệnh Slash\n"
                      "• `/thuhoach` - Thu hoạch cây server\n"
                      "• `!cog load/reload` - Quản lý module",
                inline=False
            )

        embed.set_footer(text="Gõ / hoặc ! tên lệnh để bắt đầu")
        
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            await ctx_or_interaction.response.send_message(embed=embed)

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
            for idx, (username, correct_words) in enumerate(rows, 1):
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
            print(f"[PROFILE] Error: {e}")
            import traceback
            traceback.print_exc()

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
            print(f"[PROFILE] Error: {e}")
            import traceback
            traceback.print_exc()

    def _generate_profile_image_sync(self, user_data, avatar_bytes, friend_data=None, friend_avatar_bytes=None):
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
            except:
                try:
                    return ImageFont.truetype(fallback_font, size)
                except:
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
            except:
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
            
        # --- FRIEND SECTION ---
        if friend_data and friend_avatar_bytes:
            f_size = 200
            f_avatar = Image.open(friend_avatar_bytes).convert('RGBA').resize((f_size, f_size))
            
            f_mask = Image.new('L', (f_size, f_size), 0)
            ImageDraw.Draw(f_mask).ellipse((0, 0, f_size, f_size), fill=255)
            
            f_x, f_y = 680, 50
            img.paste(f_avatar, (f_x, f_y), f_mask)
            draw.ellipse((f_x-2, f_y-2, f_x+f_size+2, f_y+f_size+2), outline=COLOR_HEART, width=2)
            
            affinity_title = self._get_affinity_title(friend_data['affinity'])
            draw.text((info_x, 190), f"Đang thân với: {friend_data['name']}", font=font_info, fill=COLOR_HEART)
            draw.text((info_x, 210), f"Mức độ: {affinity_title} ({friend_data['affinity']})", font=font_small, fill=COLOR_TEXT_MAIN)
        else:
            draw.text((info_x, 210), "Chưa có tri kỷ", font=font_info, fill=(150, 150, 150))

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
        
        # Get best friend and download their avatar if exists
        friend_data = None
        friend_avatar_bytes = None
        best_friend_data = await self._get_best_friend(user.id)
        
        if best_friend_data:
            f_id, f_affinity = best_friend_data
            try:
                friend = await self.bot.fetch_user(f_id)
                friend_data = {
                    'name': friend.name,
                    'affinity': f_affinity
                }
                
                f_avatar_url = str(friend.avatar.url if friend.avatar else friend.default_avatar.url)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f_avatar_url) as resp:
                        friend_avatar_bytes = io.BytesIO(await resp.read())
            except Exception as e:
                print(f"Error loading friend: {e}")
        
        # Run CPU-bound image generation in executor to avoid blocking
        loop = asyncio.get_running_loop()
        img_bytes = await loop.run_in_executor(
            None,
            functools.partial(
                self._generate_profile_image_sync,
                user_data,
                avatar_bytes,
                friend_data,
                friend_avatar_bytes
            )
        )
        
        return img_bytes

    async def _get_best_friend(self, user_id):
        from database_manager import get_top_affinity_friends
        
        friends = await get_top_affinity_friends(user_id, 1)
        if friends:
            return friends[0]
        return None

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

    def _get_affinity_title(self, affinity: int) -> str:
        """Get affinity level title"""
        if affinity < 10:
            return "Quen biết"
        elif affinity < 30:
            return "Bạn tốt"
        elif affinity < 60:
            return "Bạn thân"
        elif affinity < 100:
            return "Gia đình"
        else:
            return "Linh hồn song sinh"

    async def _create_profile_card(self, user, seeds, best_friend):
        """Create profile card using Pillow - Legacy version"""
        from urllib.request import urlopen
        
        # Create image
        width, height = 800, 400
        img = Image.new('RGB', (width, height), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        
        # Load avatar
        try:
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            avatar_data = urlopen(avatar_url).read()
            avatar_img = Image.open(io.BytesIO(avatar_data)).convert('RGBA')
            avatar_img = avatar_img.resize((120, 120))
            
            # Add avatar (rounded)
            img.paste(avatar_img, (30, 30), avatar_img)
        except:
            pass
        
        # Get fonts (use default if unavailable)
        try:
            title_font = ImageFont.truetype("arial.ttf", 40)
            stat_font = ImageFont.truetype("arial.ttf", 24)
            label_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        
        # Draw username
        draw.text((170, 40), f"{user.name}", font=title_font, fill=(255, 255, 255))
        
        # Draw stats
        stats_text = f"💰 {seeds} Hạt"
        draw.text((170, 100), stats_text, font=stat_font, fill=(200, 200, 200))
        
        # Draw best friend
        draw.text((30, 180), "👥 Người tri kỷ:", font=label_font, fill=(255, 165, 0))
        draw.text((200, 180), best_friend, font=stat_font, fill=(255, 200, 0))
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes

# Hàm setup bắt buộc để load Cog
async def setup(bot):
    await bot.add_cog(General(bot))
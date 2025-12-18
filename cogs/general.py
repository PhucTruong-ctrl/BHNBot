import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from PIL import Image, ImageDraw, ImageFont
import io

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
        await self._send_help(ctx)

    @app_commands.command(name="help", description="Hiển thị danh sách lệnh")
    async def help_slash(self, interaction: discord.Interaction):
        """Hiển thị danh sách lệnh"""
        await self._send_help(interaction)

    async def _send_help(self, ctx_or_interaction):
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
                  "• `/bal` (Slash only) - Xem số dư hạt\n"
                  "• `/tuido` (!tuido) - Xem túi đồ và hạt\n"
                  "• `/top` (!top) - Xem BXH đại gia hạt",
            inline=False
        )

        # 3. Shop & Items
        embed.add_field(
            name="🛍️ Cửa Hàng",
            value="• `/shop` (Slash only) - Xem menu shop\n"
                  "• `/mua` (!mua) - Mua đồ (VD: `/mua cafe 1`)",
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
            value="• `/gacreate` (Slash only) - Tạo Giveaway mới\n" 
                  "• `/gaend` (Slash only) - Kết thúc Giveaway sớm\n",
            inline=False
        )

        # 8. Admin Only (Separate field)
        embed.add_field(
            name="⚙️ Admin / Quản Lý (Admin Only)",
            value="• `/config set ...` - Cài đặt kênh (Nối từ, Log, v.v.)\n"
                  "• `/exclude add/remove` - Chặn kênh nhận hạt chat\n"
                  "• `/themhat` (!themhat) - Cộng hạt cho member\n"
                  "• `/sync` (!sync) - Đồng bộ lệnh Slash\n"
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
        import aiosqlite
        
        DB_PATH = "./data/database.db"
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Query user_stats table for noi tu wins
                async with db.execute("""
                    SELECT u.username, us.value as wins
                    FROM user_stats us
                    JOIN users u ON us.user_id = u.user_id
                    WHERE us.game_id = 'noitu' AND us.stat_key = 'wins'
                    ORDER BY us.value DESC
                    LIMIT 10
                """) as cursor:
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
            for idx, (username, wins) in enumerate(rows, 1):
                medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                rank_text += f"{medal} **{username}** - {wins} thắng\n"
            
            embed.description = rank_text
            embed.set_footer(text="Xếp hạng dựa trên số thắng")
            
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
            # Get user data from economy and leaderboard
            async with aiosqlite.connect(DB_PATH) as db:
                # Get seeds
                async with db.execute(
                    "SELECT seeds FROM users WHERE user_id = ?",
                    (target_user.id,)
                ) as cursor:
                    economy_row = await cursor.fetchone()
                
                # Get rank
                async with db.execute(
                    "SELECT COUNT(*) FROM users WHERE seeds > (SELECT seeds FROM users WHERE user_id = ?)",
                    (target_user.id,)
                ) as cursor:
                    rank_row = await cursor.fetchone()
                    rank = rank_row[0] + 1 if rank_row else 999
            
            seeds = economy_row[0] if economy_row else 0
            
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
            async with aiosqlite.connect(DB_PATH) as db:
                # Get seeds
                async with db.execute(
                    "SELECT seeds FROM users WHERE user_id = ?",
                    (target_user.id,)
                ) as cursor:
                    economy_row = await cursor.fetchone()
                
                # Get rank
                async with db.execute(
                    "SELECT COUNT(*) FROM users WHERE seeds > (SELECT seeds FROM users WHERE user_id = ?)",
                    (target_user.id,)
                ) as cursor:
                    rank_row = await cursor.fetchone()
                    rank = rank_row[0] + 1 if rank_row else 999
            
            seeds = economy_row[0] if economy_row else 0
            
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

    async def _create_profile_card_new(self, user, seeds, rank):
        """Create profile card using Pillow with 'Resident Card' (Ghibli/Journal) design"""
        import aiohttp
        import os
        
        # --- CONFIGURATION ---
        # Colors (Earth Tones)
        COLOR_BG = (245, 240, 235)      # Warm Beige
        COLOR_BORDER = (139, 90, 43)    # Brown
        COLOR_TEXT_MAIN = (74, 59, 42)  # Dark Brown
        COLOR_TEXT_ACCENT = (92, 138, 69) # Green
        COLOR_BAR_BG = (224, 224, 224)  # Light Grey
        COLOR_BAR_FILL = (118, 200, 147) # Pastel Green
        COLOR_HEART = (255, 107, 107)   # Pastel Red
        
        # Dimensions
        WIDTH, HEIGHT = 900, 300
        
        # --- ASSETS LOADING ---
        # Fonts
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
        
        # Background
        bg_path = "./assets/card_bg_ghibli.png"
        if os.path.exists(bg_path):
            try:
                img = Image.open(bg_path).resize((WIDTH, HEIGHT))
            except:
                img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
        else:
            img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
            
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Draw Border if no background image
        if not os.path.exists(bg_path):
            draw.rectangle((5, 5, WIDTH-5, HEIGHT-5), outline=COLOR_BORDER, width=3)
        
        # --- AVATAR SECTION (LEFT) ---
        # Download avatar
        user_avatar_url = str(user.avatar.url if user.avatar else user.default_avatar.url)
        async with aiohttp.ClientSession() as session:
            async with session.get(user_avatar_url) as resp:
                avatar_bytes = io.BytesIO(await resp.read())
        
        avatar_size = 200
        avatar = Image.open(avatar_bytes).convert('RGBA').resize((avatar_size, avatar_size))
        
        # Create circular mask
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        # Paste avatar
        avatar_x, avatar_y = 25, 50
        img.paste(avatar, (avatar_x, avatar_y), mask)
        
        # Draw decorative ring around avatar
        draw.ellipse((avatar_x-5, avatar_y-5, avatar_x+avatar_size+5, avatar_y+avatar_size+5), 
                     outline=COLOR_BORDER, width=4)
        
        # --- INFO SECTION (MIDDLE) ---
        info_x = 280
        
        # Username
        display_name = user.display_name
        draw.text((info_x, 90), display_name, font=font_main, fill=COLOR_TEXT_MAIN)
        
        # Rank Title
        rank_title = self._get_rank_title_no_emoji(seeds)
        draw.text((info_x, 145), f"Hạng: {rank_title} (#{rank})", font=font_rank, fill=COLOR_TEXT_ACCENT)
        
        # Progress Bar (Branch style)
        # Milestones: 50, 200, 500, 1000, 5000
        next_milestone = 50
        if seeds >= 5000: next_milestone = 10000
        elif seeds >= 1000: next_milestone = 5000
        elif seeds >= 500: next_milestone = 1000
        elif seeds >= 200: next_milestone = 500
        elif seeds >= 50: next_milestone = 200
            
        progress = min(seeds / next_milestone, 1.0)
        
        bar_x, bar_y = info_x, 175
        bar_w, bar_h = 335, 15
        
        # Draw Seeds Text
        draw.text((info_x + bar_w - 100, 150), f"{seeds}/{next_milestone}", font=font_info, fill=COLOR_TEXT_MAIN)

        # Draw Bar Background
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=12, fill=COLOR_BAR_BG)
        
        # Draw Bar Fill
        if progress > 0:
            fill_w = int(bar_w * progress)
            draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h)], radius=12, fill=COLOR_BAR_FILL)
            
        # --- AFFINITY SECTION (RIGHT/BOTTOM) ---
        # Get best friend
        best_friend_data = await self._get_best_friend(user.id)
        
        if best_friend_data:
            f_id, f_affinity = best_friend_data
            try:
                friend = await self.bot.fetch_user(f_id)
                
                # Friend Avatar
                f_avatar_url = str(friend.avatar.url if friend.avatar else friend.default_avatar.url)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f_avatar_url) as resp:
                        f_avatar_bytes = io.BytesIO(await resp.read())
                
                f_size = 200
                f_avatar = Image.open(f_avatar_bytes).convert('RGBA').resize((f_size, f_size))
                
                # Mask
                f_mask = Image.new('L', (f_size, f_size), 0)
                ImageDraw.Draw(f_mask).ellipse((0, 0, f_size, f_size), fill=255)
                
                # Position: Bottom Right of the info section
                f_x, f_y = 680, 50
                
                img.paste(f_avatar, (f_x, f_y), f_mask)
                draw.ellipse((f_x-2, f_y-2, f_x+f_size+2, f_y+f_size+2), outline=COLOR_HEART, width=2)
                
                # Text
                affinity_title = self._get_affinity_title(f_affinity)
                draw.text((info_x, 190), f"Đang thân với: {friend.name}", font=font_info, fill=COLOR_HEART)
                draw.text((info_x, 210), f"Mức độ: {affinity_title} ({f_affinity})", font=font_small, fill=COLOR_TEXT_MAIN)
                
            except Exception as e:
                print(f"Error loading friend: {e}")
                draw.text((info_x, 210), "Chưa có tri kỷ", font=font_info, fill=(150, 150, 150))
        else:
            draw.text((info_x, 210), "Chưa có tri kỷ", font=font_info, fill=(150, 150, 150))

        # Save
        img_bytes = io.BytesIO()
        img.save(img_bytes, 'PNG')
        img_bytes.seek(0)
        return img_bytes

    async def _get_best_friend(self, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                """SELECT user_id_2, affinity FROM relationships 
                   WHERE user_id_1 = ? ORDER BY affinity DESC LIMIT 1""",
                (user_id,)
            ) as cursor:
                r1 = await cursor.fetchone()
            
            async with db.execute(
                """SELECT user_id_1, affinity FROM relationships 
                   WHERE user_id_2 = ? ORDER BY affinity DESC LIMIT 1""",
                (user_id,)
            ) as cursor:
                r2 = await cursor.fetchone()
        
        if r1 and r2:
            return r1 if r1[1] >= r2[1] else r2
        return r1 or r2

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
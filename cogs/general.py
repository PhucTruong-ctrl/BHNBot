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
        await ctx.send(f'Pong! Độ trễ: {round(self.bot.latency * 1000)}ms')

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
        embed = discord.Embed(
            title="📖 Danh sách lệnh Mèo Béo",
            color=discord.Color.blue(),
            description="Sử dụng các lệnh dưới đây để tương tác với bot"
        )
        
        # Game commands
        embed.add_field(
            name="🎮 Nối Từ",
            value="• `!reset` - Reset game trong kênh\n"
                  "• `/reset` - Reset game (slash)\n"
                  "• Nhắn 2 từ để nối tiếp từ",
            inline=False
        )
        
        # Word management
        embed.add_field(
            name="📚 Quản lý từ vựng",
            value="• `!themtu từ1 từ2` - Đề xuất từ mới\n"
                  "• `/themtu từ1 từ2` - Đề xuất từ mới (slash)",
            inline=False
        )
        
        # Economy commands
        embed.add_field(
            name="💰 Kinh tế (Hạt)",
            value="• `/chao` - Chào buổi sáng (5h-10h) nhận 10 hạt\n"
                  "• `/bal` - Xem số hạt hiện tại\n"
                  "• `/tuido` - Alias của /bal\n"
                  "• `/top` - Xem bảng xếp hạng hạt",
            inline=False
        )
        
        # Tree commands
        embed.add_field(
            name="🌳 Trồng Cây",
            value="• `/cay` - Xem trạng thái cây server\n"
                  "• `/gophat` - Góp hạt để nuôi cây\n"
                  "• `/thuhoach` - Thu hoạch cây (Admin only)",
            inline=False
        )
        
        # Shop commands
        embed.add_field(
            name="🛍️ Cửa hàng",
            value="• `/shop` - Xem danh sách quà\n"
                  "• `/buy <item>` - Mua quà\n"
                  "• `/inventory [@user]` - Xem túi đồ",
            inline=False
        )
        
        # Interaction commands
        embed.add_field(
            name="💝 Tương tác",
            value="• `/tangqua <user> <item>` - Tặng quà cho ai đó\n"
                  "• `/affinity [@user]` - Xem mức độ thân thiết",
            inline=False
        )
        
        # Configuration (Admin only)
        embed.add_field(
            name="⚙️ Cấu hình (Admin only)",
            value="• `/config set kenh_noitu <channel>` - Đặt kênh chơi nối từ\n"
                  "• `/config set kenh_cay <channel>` - Đặt kênh trồng cây\n"
                  "• `/config set kenh_giveaway <channel>` - Đặt kênh giveaway\n"
                  "• `/config set kenh_logs <channel>` - Đặt kênh logs\n"
                  "• `/exclude add|remove <channel>` - Loại trừ kênh không nhận seed",
            inline=False
        )
        
        # Utility
        embed.add_field(
            name="🔧 Tiện ích",
            value="• `!ping` - Kiểm tra độ trễ bot\n"
                  "• `/avatar [@user]` - Xem avatar\n"
                  "• `/profile [@user]` - Xem profile card\n"
                  "• `/ntrank` - Xem xếp hạng nối từ",
            inline=False
        )
        
        embed.set_footer(text="Gõ lệnh để bắt đầu • Hỗ trợ cả prefix (!) và slash (/)")
        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Hiển thị danh sách lệnh")
    async def help_slash(self, interaction: discord.Interaction):
        """Hiển thị danh sách lệnh"""
        embed = discord.Embed(
            title="📖 Danh sách lệnh BHNBot",
            color=discord.Color.blue(),
            description="Sử dụng các lệnh dưới đây để tương tác với bot"
        )
        
        # Game commands
        embed.add_field(
            name="🎮 Nối Từ",
            value="• `!reset` - Reset game trong kênh\n"
                  "• `/reset` - Reset game (slash)\n"
                  "• Nhắn 2 từ để nối tiếp từ",
            inline=False
        )
        
        # Word management
        embed.add_field(
            name="📚 Quản lý từ vựng",
            value="• `!themtu từ1 từ2` - Đề xuất từ mới\n"
                  "• `/themtu từ1 từ2` - Đề xuất từ mới (slash)",
            inline=False
        )
        
        # Economy commands
        embed.add_field(
            name="💰 Kinh tế (Hạt)",
            value="• `/chao` - Chào buổi sáng (5h-10h) nhận 10 hạt\n"
                  "• `/bal` - Xem số hạt hiện tại\n"
                  "• `/tuido` - Alias của /bal\n"
                  "• `/top` - Xem bảng xếp hạng hạt",
            inline=False
        )
        
        # Tree commands
        embed.add_field(
            name="🌳 Trồng Cây",
            value="• `/cay` - Xem trạng thái cây server\n"
                  "• `/gophat` - Góp hạt để nuôi cây\n"
                  "• `/thuhoach` - Thu hoạch cây (Admin only)",
            inline=False
        )
        
        # Shop commands
        embed.add_field(
            name="🛍️ Cửa hàng",
            value="• `/shop` - Xem danh sách quà\n"
                  "• `/buy <item>` - Mua quà\n"
                  "• `/inventory [@user]` - Xem túi đồ",
            inline=False
        )
        
        # Interaction commands
        embed.add_field(
            name="💝 Tương tác",
            value="• `/tangqua <user> <item>` - Tặng quà cho ai đó\n"
                  "• `/affinity [@user]` - Xem mức độ thân thiết",
            inline=False
        )
        
        # Configuration (Admin only)
        embed.add_field(
            name="⚙️ Cấu hình (Admin only)",
            value="• `/config set kenh_noitu <channel>` - Đặt kênh chơi nối từ\n"
                  "• `/config set kenh_cay <channel>` - Đặt kênh trồng cây\n"
                  "• `/config set kenh_giveaway <channel>` - Đặt kênh giveaway\n"
                  "• `/config set kenh_logs <channel>` - Đặt kênh logs\n"
                  "• `/exclude add|remove <channel>` - Loại trừ kênh không nhận seed",
            inline=False
        )
        
        # Utility
        embed.add_field(
            name="🔧 Tiện ích",
            value="• `!ping` - Kiểm tra độ trễ bot\n"
                  "• `/avatar [@user]` - Xem avatar\n"
                  "• `/profile [@user]` - Xem profile card\n"
                  "• `/ntrank` - Xem xếp hạng nối từ",
            inline=False
        )
        
        embed.set_footer(text="Gõ lệnh để bắt đầu • Hỗ trợ cả prefix (!) và slash (/)")
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

    # ==================== PROFILE CARD ====================

    @app_commands.command(name="profile", description="Xem profile card")
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
                    "SELECT seeds FROM economy_users WHERE user_id = ?",
                    (target_user.id,)
                ) as cursor:
                    economy_row = await cursor.fetchone()
                
                # Get rank
                async with db.execute(
                    "SELECT COUNT(*) FROM economy_users WHERE seeds > (SELECT seeds FROM economy_users WHERE user_id = ?)",
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

    async def _create_profile_card_new(self, user, seeds, rank):
        """Create profile card using Pillow with new design"""
        import aiohttp
        
        # Download avatar
        user_avatar_url = str(user.avatar.url if user.avatar else user.default_avatar.url)
        async with aiohttp.ClientSession() as session:
            async with session.get(user_avatar_url) as resp:
                avatar_bytes = io.BytesIO(await resp.read())
        
        # Create image (1000x240 like the reference)
        img = Image.new('RGB', (1000, 240), color=(30, 30, 30))
        logo = Image.open(avatar_bytes).convert('RGBA').resize((200, 200))
        
        # Create circular mask for avatar
        bigsize = (logo.size[0] * 3, logo.size[1] * 3)
        mask = Image.new('L', bigsize, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(logo.size, Image.Resampling.LANCZOS)
        logo.putalpha(mask)
        
        # Paste avatar
        img.paste(logo, (20, 20), mask=logo)
        
        # Main drawing
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Status circle (black background)
        draw.ellipse((152, 152, 208, 208), fill='#000000')
        
        # Status color (using user status if available)
        status_color = '#3BA55B'  # Default online green
        try:
            if hasattr(user, 'status'):
                if str(user.status) == "online":
                    status_color = '#3BA55B'
                elif str(user.status) == "idle":
                    status_color = '#F9A61A'
                elif str(user.status) == "dnd":
                    status_color = '#EC4245'
                else:
                    status_color = '#737F8D'
        except:
            pass
        
        # Status indicator circle
        draw.ellipse((155, 155, 205, 205), fill=status_color)
        
        # Load fonts
        try:
            big_font = ImageFont.truetype("arial.ttf", 60)
            medium_font = ImageFont.truetype("arial.ttf", 40)
            small_font = ImageFont.truetype("arial.ttf", 30)
        except:
            try:
                big_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 60)
                medium_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 40)
                small_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 30)
            except:
                big_font = ImageFont.load_default()
                medium_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        
        # Rank and Level display (top right)
        rank_text = f"#{rank}"
        bbox = draw.textbbox((0, 0), rank_text, font=big_font)
        text_width = bbox[2] - bbox[0]
        offset_x = 1000 - 15 - text_width
        offset_y = 5
        draw.text((offset_x, offset_y), rank_text, font=big_font, fill="#FFFFFF")
        
        # "RANK" label
        rank_label_text = "RANK"
        bbox = draw.textbbox((0, 0), rank_label_text, font=small_font)
        label_width = bbox[2] - bbox[0]
        offset_x -= 5 + label_width
        offset_y = 35
        draw.text((offset_x, offset_y), rank_label_text, font=small_font, fill="#FFFFFF")
        
        # Level display
        level_text = "1"  # Fixed level 1 for seeds system
        bbox = draw.textbbox((0, 0), level_text, font=big_font)
        text_width = bbox[2] - bbox[0]
        offset_x -= 15 + text_width
        offset_y = 5
        draw.text((offset_x, offset_y), level_text, font=big_font, fill="#11ebf2")
        
        # "LEVEL" label
        level_label = "LEVEL"
        bbox = draw.textbbox((0, 0), level_label, font=small_font)
        label_width = bbox[2] - bbox[0]
        offset_x -= 5 + label_width
        offset_y = 35
        draw.text((offset_x, offset_y), level_label, font=small_font, fill="#11ebf2")
        
        # Progress bar for seeds
        bar_offset_x = logo.size[0] + 20 + 100
        bar_offset_y = 160
        bar_offset_x_1 = 1000 - 50
        bar_offset_y_1 = 200
        circle_size = bar_offset_y_1 - bar_offset_y
        
        # Background bar (grey)
        draw.rectangle((bar_offset_x, bar_offset_y, bar_offset_x_1, bar_offset_y_1), fill="#727175")
        
        # Left circle background
        draw.ellipse((bar_offset_x - circle_size // 2, bar_offset_y, bar_offset_x + circle_size // 2, bar_offset_y + circle_size), fill="#727175")
        
        # Right circle background
        draw.ellipse((bar_offset_x_1 - circle_size // 2, bar_offset_y, bar_offset_x_1 + circle_size // 2, bar_offset_y_1), fill="#727175")
        
        # Calculate progress (max 10000 seeds for visual representation)
        max_seeds = 10000
        progress = min((seeds / max_seeds) * 100, 100)
        
        bar_length = bar_offset_x_1 - bar_offset_x
        progress_bar_length = round(bar_length * progress / 100)
        pbar_offset_x_1 = bar_offset_x + progress_bar_length
        
        # Draw progress rectangle (cyan)
        if progress_bar_length > 0:
            draw.rectangle((bar_offset_x, bar_offset_y, pbar_offset_x_1, bar_offset_y_1), fill="#11ebf2")
            
            # Left circle progress
            draw.ellipse((bar_offset_x - circle_size // 2, bar_offset_y, bar_offset_x + circle_size // 2, bar_offset_y + circle_size), fill="#11ebf2")
            
            # Right circle progress
            draw.ellipse((pbar_offset_x_1 - circle_size // 2, bar_offset_y, pbar_offset_x_1 + circle_size // 2, bar_offset_y_1), fill="#11ebf2")
        
        # Seeds text
        seeds_text = f"/ 10000 Hạt"
        bbox = draw.textbbox((0, 0), seeds_text, font=small_font)
        text_width = bbox[2] - bbox[0]
        seeds_offset_x = bar_offset_x_1 - text_width
        seeds_offset_y = bar_offset_y - 40
        draw.text((seeds_offset_x, seeds_offset_y), seeds_text, font=small_font, fill="#727175")
        
        seeds_current = f"{seeds} "
        bbox = draw.textbbox((0, 0), seeds_current, font=small_font)
        seeds_width = bbox[2] - bbox[0]
        draw.text((seeds_offset_x - seeds_width, seeds_offset_y), seeds_current, font=small_font, fill="#FFFFFF")
        
        # Username
        username_text = user.display_name if hasattr(user, 'display_name') else user.name
        if len(username_text) >= 15:
            bbox = draw.textbbox((0, 0), username_text, font=small_font)
            text_offset_x = bar_offset_x - 10
            text_offset_y = bar_offset_y - 40
            draw.text((text_offset_x, text_offset_y), username_text, font=small_font, fill="#FFFFFF")
            username_width = bbox[2] - bbox[0]
        else:
            bbox = draw.textbbox((0, 0), username_text, font=medium_font)
            text_offset_x = bar_offset_x - 10
            text_offset_y = bar_offset_y - 40
            draw.text((text_offset_x, text_offset_y), username_text, font=medium_font, fill="#FFFFFF")
            username_width = bbox[2] - bbox[0]
        
        # Discriminator
        if hasattr(user, 'discriminator'):
            discriminator = f"#{user.discriminator}"
            text_offset_x += username_width + 10
            bbox = draw.textbbox((0, 0), discriminator, font=small_font)
            text_offset_y = bar_offset_y - 40
            draw.text((text_offset_x - 10, text_offset_y), discriminator, font=small_font, fill="#727175")
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, 'PNG')
        img_bytes.seek(0)
        
        return img_bytes

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
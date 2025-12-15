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
            # Get user data from economy
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT seeds FROM economy_users WHERE user_id = ?",
                    (target_user.id,)
                ) as cursor:
                    economy_row = await cursor.fetchone()
                
                # Get top friends (affinity)
                async with db.execute(
                    """SELECT user_id_2 as friend_id, affinity FROM relationships 
                       WHERE user_id_1 = ? ORDER BY affinity DESC LIMIT 1""",
                    (target_user.id,)
                ) as cursor:
                    friend_row1 = await cursor.fetchone()
                
                async with db.execute(
                    """SELECT user_id_1 as friend_id, affinity FROM relationships 
                       WHERE user_id_2 = ? ORDER BY affinity DESC LIMIT 1""",
                    (target_user.id,)
                ) as cursor:
                    friend_row2 = await cursor.fetchone()
            
            seeds = economy_row[0] if economy_row else 0
            
            # Determine best friend
            best_friend_id = None
            if friend_row1 and friend_row2:
                best_friend_id = friend_row1[0] if friend_row1[1] >= friend_row2[1] else friend_row2[0]
            elif friend_row1:
                best_friend_id = friend_row1[0]
            elif friend_row2:
                best_friend_id = friend_row2[0]
            
            best_friend_name = "Chưa có"
            if best_friend_id:
                try:
                    best_friend = await self.bot.fetch_user(best_friend_id)
                    best_friend_name = best_friend.name
                except:
                    best_friend_name = "Người lạ"
            
            # Create profile card image
            profile_img = await self._create_profile_card(target_user, seeds, best_friend_name)
            
            # Send as file
            file = discord.File(profile_img, filename="profile.png")
            await interaction.followup.send(file=file)
        
        except Exception as e:
            await interaction.followup.send(f"Lỗi tạo profile: {e}")
            print(f"[PROFILE] Error: {e}")

    async def _create_profile_card(self, user, seeds, best_friend):
        """Create profile card using Pillow"""
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
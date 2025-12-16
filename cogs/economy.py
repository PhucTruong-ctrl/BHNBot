import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, time
import random
import asyncio
from database_manager import (
    db_manager,
    get_user_balance,
    add_seeds,
    get_or_create_user,
    get_leaderboard,
    batch_update_seeds
)

DB_PATH = "./data/database.db"

# Constants
DAILY_BONUS = 10  # Hạt nhận từ /chao
DAILY_WINDOW_START = 5  # 5 AM
DAILY_WINDOW_END = 12  # 12 AM
CHAT_REWARD_MIN = 1
CHAT_REWARD_MAX = 3
CHAT_REWARD_COOLDOWN = 60  # seconds
VOICE_REWARD_INTERVAL = 5  # minutes
VOICE_REWARD = 5  # Hạt mỗi 5 phút trong voice

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_cooldowns = {}  # {user_id: last_reward_time}
        self.reaction_cooldowns = {}  # {user_id: last_reaction_reward_time}
        self.voice_reward_task.start()
        self.voice_affinity_task.start()

    def cog_unload(self):
        self.voice_reward_task.cancel()
        self.voice_affinity_task.cancel()

    # ==================== HELPER FUNCTIONS ====================
    async def get_or_create_user_local(self, user_id: int, username: str):
        """Get or create user in economy_users table"""
        return await get_or_create_user(user_id, username)

    async def is_harvest_buff_active(self, guild_id: int) -> bool:
        """Check if 24h harvest buff is active"""
        try:
            result = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"harvest_buff_{guild_id}",
                cache_ttl=60
            )
            
            if not result or not result[0]:
                return False
            
            buff_until = datetime.fromisoformat(result[0])
            return datetime.now() < buff_until
        except:
            return False

    async def add_seeds_local(self, user_id: int, amount: int):
        """Add seeds to user"""
        await add_seeds(user_id, amount)

    async def get_user_balance_local(self, user_id: int) -> int:
        """Get user balance (seeds only)"""
        return await get_user_balance(user_id)

    async def get_leaderboard_local(self, limit: int = 10) -> list:
        """Get top players by seeds"""
        return await get_leaderboard(limit)

    async def update_last_daily(self, user_id: int):
        """Update last daily reward time"""
        await db_manager.modify(
            "UPDATE economy_users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db_manager.clear_cache_by_prefix(f"user_full_{user_id}")

    async def update_last_chat_reward(self, user_id: int):
        """Update last chat reward time"""
        await db_manager.modify(
            "UPDATE economy_users SET last_chat_reward = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db_manager.clear_cache_by_prefix(f"user_full_{user_id}")

    async def get_last_daily(self, user_id: int) -> datetime:
        """Get last daily reward time"""
        result = await db_manager.fetchone(
            "SELECT last_daily FROM economy_users WHERE user_id = ?",
            (user_id,)
        )
        if result and result[0]:
            return datetime.fromisoformat(result[0])
        return None

    def is_daily_window(self) -> bool:
        """Check if current time is within daily reward window (5 AM - 10 AM)"""
        now = datetime.now()
        return DAILY_WINDOW_START <= now.hour < DAILY_WINDOW_END

    async def get_excluded_channels(self, guild_id: int) -> list:
        """Get list of excluded channels for a guild"""
        try:
            result = await db_manager.fetchone(
                "SELECT logs_channel_id, exclude_chat_channels FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"excluded_channels_{guild_id}",
                cache_ttl=600
            )
            
            excluded = []
            if result:
                if result[0]:  # logs_channel_id
                    excluded.append(result[0])
                
                # Parse exclude_chat_channels (JSON format)
                if result[1]:
                    try:
                        import json
                        parsed = json.loads(result[1])
                        excluded.extend(parsed)
                    except:
                        pass
            
            return excluded
        except:
            return []

    # ==================== COMMANDS ====================

    @app_commands.command(name="chao", description="Chào buổi sáng (5h-10h) để nhận hạt")
    async def daily_bonus(self, interaction: discord.Interaction):
        """Daily bonus reward between 5 AM - 10 AM"""
        await interaction.response.defer(ephemeral=True)
        
        # Check time window
        if not self.is_daily_window():
            now = datetime.now()
            await interaction.followup.send(
                f"❌ Chỉ nhận hạt từ 5h tới 10h sáng!\n"
                f"Giờ hiện tại: {now.strftime('%H:%M')}",
                ephemeral=True
            )
            return
        
        # Get or create user
        user = interaction.user
        await self.get_or_create_user_local(user.id, user.name)
        
        # Check if already claimed today
        last_daily = await self.get_last_daily(user.id)
        if last_daily:
            today = datetime.now().date()
            if last_daily.date() == today:
                await interaction.followup.send(
                    f"❌ Bạn đã nhận hạt hôm nay rồi! Quay lại vào ngày mai.",
                    ephemeral=True
                )
                return
        
        # Award seeds
        await self.add_seeds_local(user.id, DAILY_BONUS)
        await self.update_last_daily(user.id)
        
        # Get new balance
        seeds = await self.get_user_balance_local(user.id)
        
        embed = discord.Embed(
            title="☀️ Chào buổi sáng!",
            description=f"Bạn nhận được **{DAILY_BONUS} hạt**",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Hạt hiện tại", value=f"**{seeds}**", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="bal", description="Xem số hạt hiện tại")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    async def balance(self, interaction: discord.Interaction, user: discord.User = None):
        """Check balance"""
        await interaction.response.defer(ephemeral=True)
        
        target_user = user or interaction.user
        await self.get_or_create_user_local(target_user.id, target_user.name)
        
        seeds = await self.get_user_balance_local(target_user.id)
        
        embed = discord.Embed(
            title=f"💰 Số dư của {target_user.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="🌱 Hạt", value=f"**{seeds}**", inline=False)
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tuido", description="Xem số hạt và túi đồ của bạn")
    @app_commands.describe(user="Người chơi (để trống để xem của bạn)")
    async def balance_alias(self, interaction: discord.Interaction, user: discord.User = None):
        """Check balance and inventory"""
        await interaction.response.defer(ephemeral=False)
        
        target_user = user or interaction.user
        await self.get_or_create_user_local(target_user.id, target_user.name)
        
        seeds = await self.get_user_balance_local(target_user.id)
        
        # Get inventory
        from database_manager import get_inventory
        inventory = await get_inventory(target_user.id)
        
        embed = discord.Embed(
            title=f"💰 Thông tin của {target_user.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="🌱 Hạt", value=f"**{seeds}**", inline=False)
        
        # Display inventory items
        if inventory:
            # Import fish names for display
            from cogs.fishing import ALL_FISH, GIFT_ITEMS
            
            # Fish items
            fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH}
            if fish_items:
                fish_text = "\n".join([f"{ALL_FISH[k]['emoji']} **{ALL_FISH[k]['name']}** x{v}" for k, v in sorted(fish_items.items())])
                # Split into multiple fields if too long (max 1024 chars per field)
                if len(fish_text) > 1024:
                    fish_list = sorted(fish_items.items())
                    mid = len(fish_list) // 2
                    part1 = "\n".join([f"{ALL_FISH[k]['emoji']} **{ALL_FISH[k]['name']}** x{v}" for k, v in fish_list[:mid]])
                    part2 = "\n".join([f"{ALL_FISH[k]['emoji']} **{ALL_FISH[k]['name']}** x{v}" for k, v in fish_list[mid:]])
                    embed.add_field(name="🐟 Cá (1/2)", value=part1, inline=False)
                    embed.add_field(name="🐟 Cá (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="🐟 Cá", value=fish_text, inline=False)
            
            # Gift items
            gift_lookup = {
                "cafe": ("Cà Phê", "☕"),
                "flower": ("Hoa", "🌹"),
                "ring": ("Nhẫn", "💍"),
                "gift": ("Quà", "🎁"),
                "chocolate": ("Sô Cô La", "🍫"),
                "card": ("Thiệp", "💌"),
            }
            gift_items = {k: v for k, v in inventory.items() if k in gift_lookup}
            if gift_items:
                gift_text = "\n".join([f"{gift_lookup[k][1]} **{gift_lookup[k][0]}** x{v}" for k, v in sorted(gift_items.items())])
                if len(gift_text) > 1024:
                    gift_list = sorted(gift_items.items())
                    mid = len(gift_list) // 2
                    part1 = "\n".join([f"{gift_lookup[k][1]} **{gift_lookup[k][0]}** x{v}" for k, v in gift_list[:mid]])
                    part2 = "\n".join([f"{gift_lookup[k][1]} **{gift_lookup[k][0]}** x{v}" for k, v in gift_list[mid:]])
                    embed.add_field(name="💝 Quà Tặng (1/2)", value=part1, inline=False)
                    embed.add_field(name="💝 Quà Tặng (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="💝 Quà Tặng", value=gift_text, inline=False)
            
            # Tool items
            tool_lookup = {
                "treasure_chest": ("Rương Kho Báu", "🎁"),
                "fertilizer": ("Phân Bón", "🌾"),
                "pearl": ("Ngọc Trai", "🔮"),
                "rod_material": ("Vật Liệu Cân", "⚙️"),
                "puzzle_a": ("Mảnh Ghép A", "🧩"),
                "puzzle_b": ("Mảnh Ghép B", "🧩"),
                "puzzle_c": ("Mảnh Ghép C", "🧩"),
                "puzzle_d": ("Mảnh Ghép D", "🧩"),
            }
            tool_items = {k: v for k, v in inventory.items() if k in tool_lookup}
            if tool_items:
                tool_text = "\n".join([f"{tool_lookup[k][1]} **{tool_lookup[k][0]}** x{v}" for k, v in sorted(tool_items.items())])
                if len(tool_text) > 1024:
                    tool_list = sorted(tool_items.items())
                    mid = len(tool_list) // 2
                    part1 = "\n".join([f"{tool_lookup[k][1]} **{tool_lookup[k][0]}** x{v}" for k, v in tool_list[:mid]])
                    part2 = "\n".join([f"{tool_lookup[k][1]} **{tool_lookup[k][0]}** x{v}" for k, v in tool_list[mid:]])
                    embed.add_field(name="🛠️ Công Cụ (1/2)", value=part1, inline=False)
                    embed.add_field(name="🛠️ Công Cụ (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="🛠️ Công Cụ", value=tool_text, inline=False)
            
            # Trash items
            trash_items = {k: v for k, v in inventory.items() if k.startswith("trash_")}
            if trash_items:
                trash_text = "\n".join([f"**{k.replace('trash_', '').replace('_', ' ')}** x{v}" for k, v in sorted(trash_items.items())])
                if len(trash_text) > 1024:
                    trash_list = sorted(trash_items.items())
                    mid = len(trash_list) // 2
                    part1 = "\n".join([f"**{k.replace('trash_', '').replace('_', ' ')}** x{v}" for k, v in trash_list[:mid]])
                    part2 = "\n".join([f"**{k.replace('trash_', '').replace('_', ' ')}** x{v}" for k, v in trash_list[mid:]])
                    embed.add_field(name="🗑️ Rác (1/2)", value=part1, inline=False)
                    embed.add_field(name="🗑️ Rác (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="🗑️ Rác", value=trash_text, inline=False)
        else:
            embed.add_field(name="🎒 Túi Đồ", value="Trống rỗng", inline=False)
        
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=False)

    @commands.command(name="tuido", description="Xem số hạt và túi đồ")
    async def balance_alias_prefix(self, ctx, user: discord.User = None):
        """Check balance and inventory via prefix"""
        target_user = user or ctx.author
        await self.get_or_create_user_local(target_user.id, target_user.name)
        
        seeds = await self.get_user_balance_local(target_user.id)
        
        # Get inventory
        from database_manager import get_inventory
        inventory = await get_inventory(target_user.id)
        
        embed = discord.Embed(
            title=f"💰 Thông tin của {target_user.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="🌱 Hạt", value=f"**{seeds}**", inline=False)
        
        # Display inventory items
        if inventory:
            # Import fish names for display
            from cogs.fishing import ALL_FISH, GIFT_ITEMS
            
            # Fish items
            fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH}
            if fish_items:
                fish_text = "\n".join([f"{ALL_FISH[k]['emoji']} **{ALL_FISH[k]['name']}** x{v}" for k, v in sorted(fish_items.items())])
                # Split into multiple fields if too long (max 1024 chars per field)
                if len(fish_text) > 1024:
                    fish_list = sorted(fish_items.items())
                    mid = len(fish_list) // 2
                    part1 = "\n".join([f"{ALL_FISH[k]['emoji']} **{ALL_FISH[k]['name']}** x{v}" for k, v in fish_list[:mid]])
                    part2 = "\n".join([f"{ALL_FISH[k]['emoji']} **{ALL_FISH[k]['name']}** x{v}" for k, v in fish_list[mid:]])
                    embed.add_field(name="🐟 Cá (1/2)", value=part1, inline=False)
                    embed.add_field(name="🐟 Cá (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="🐟 Cá", value=fish_text, inline=False)
            
            # Gift items
            gift_lookup = {
                "cafe": ("Cà Phê", "☕"),
                "flower": ("Hoa", "🌹"),
                "ring": ("Nhẫn", "💍"),
                "gift": ("Quà", "🎁"),
                "chocolate": ("Sô Cô La", "🍫"),
                "card": ("Thiệp", "💌"),
            }
            gift_items = {k: v for k, v in inventory.items() if k in gift_lookup}
            if gift_items:
                gift_text = "\n".join([f"{gift_lookup[k][1]} **{gift_lookup[k][0]}** x{v}" for k, v in sorted(gift_items.items())])
                if len(gift_text) > 1024:
                    gift_list = sorted(gift_items.items())
                    mid = len(gift_list) // 2
                    part1 = "\n".join([f"{gift_lookup[k][1]} **{gift_lookup[k][0]}** x{v}" for k, v in gift_list[:mid]])
                    part2 = "\n".join([f"{gift_lookup[k][1]} **{gift_lookup[k][0]}** x{v}" for k, v in gift_list[mid:]])
                    embed.add_field(name="💝 Quà Tặng (1/2)", value=part1, inline=False)
                    embed.add_field(name="💝 Quà Tặng (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="💝 Quà Tặng", value=gift_text, inline=False)
            
            # Tool items
            tool_lookup = {
                "treasure_chest": ("Rương Kho Báu", "🎁"),
                "fertilizer": ("Phân Bón", "🌾"),
                "pearl": ("Ngọc Trai", "🔮"),
                "rod_material": ("Vật Liệu Cân", "⚙️"),
                "puzzle_a": ("Mảnh Ghép A", "🧩"),
                "puzzle_b": ("Mảnh Ghép B", "🧩"),
                "puzzle_c": ("Mảnh Ghép C", "🧩"),
                "puzzle_d": ("Mảnh Ghép D", "🧩"),
            }
            tool_items = {k: v for k, v in inventory.items() if k in tool_lookup}
            if tool_items:
                tool_text = "\n".join([f"{tool_lookup[k][1]} **{tool_lookup[k][0]}** x{v}" for k, v in sorted(tool_items.items())])
                if len(tool_text) > 1024:
                    tool_list = sorted(tool_items.items())
                    mid = len(tool_list) // 2
                    part1 = "\n".join([f"{tool_lookup[k][1]} **{tool_lookup[k][0]}** x{v}" for k, v in tool_list[:mid]])
                    part2 = "\n".join([f"{tool_lookup[k][1]} **{tool_lookup[k][0]}** x{v}" for k, v in tool_list[mid:]])
                    embed.add_field(name="🛠️ Công Cụ (1/2)", value=part1, inline=False)
                    embed.add_field(name="🛠️ Công Cụ (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="🛠️ Công Cụ", value=tool_text, inline=False)
            
            # Trash items
            trash_items = {k: v for k, v in inventory.items() if k.startswith("trash_")}
            if trash_items:
                trash_text = "\n".join([f"**{k.replace('trash_', '').replace('_', ' ')}** x{v}" for k, v in sorted(trash_items.items())])
                if len(trash_text) > 1024:
                    trash_list = sorted(trash_items.items())
                    mid = len(trash_list) // 2
                    part1 = "\n".join([f"**{k.replace('trash_', '').replace('_', ' ')}** x{v}" for k, v in trash_list[:mid]])
                    part2 = "\n".join([f"**{k.replace('trash_', '').replace('_', ' ')}** x{v}" for k, v in trash_list[mid:]])
                    embed.add_field(name="🗑️ Rác (1/2)", value=part1, inline=False)
                    embed.add_field(name="🗑️ Rác (2/2)", value=part2, inline=False)
                else:
                    embed.add_field(name="🗑️ Rác", value=trash_text, inline=False)
        else:
            embed.add_field(name="🎒 Túi Đồ", value="Trống rỗng", inline=False)
        
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await ctx.send(embed=embed)
    async def leaderboard(self, interaction: discord.Interaction):
        """Show leaderboard"""
        await interaction.response.defer(ephemeral=True)
        
        top_users = await self.get_leaderboard_local(10)
        
        if not top_users:
            await interaction.followup.send("❌ Chưa có ai trong bảng xếp hạng!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Bảng Xếp Hạng Hạt",
            color=discord.Color.gold()
        )
        
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, username, seeds) in enumerate(top_users, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}."
            ranking_text += f"{medal} **{username}** - {seeds} Hạt\n"
        
        embed.description = ranking_text
        embed.set_footer(text="Cập nhật hàng ngày • Xếp hạng dựa trên tổng hạt")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="top", description="Xem bảng xếp hạng 10 người có nhiều hạt nhất")
    async def top_leaderboard_slash(self, interaction: discord.Interaction):
        """Show top 10 leaderboard (slash command)"""
        await interaction.response.defer(ephemeral=False)
        
        top_users = await self.get_leaderboard_local(10)
        
        if not top_users:
            await interaction.followup.send("❌ Chưa có ai trong bảng xếp hạng!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Bảng Xếp Hạng Top 10 Hạt",
            color=discord.Color.gold()
        )
        
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, username, seeds) in enumerate(top_users, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}️⃣"
            ranking_text += f"{medal} **{username}** - {seeds} 🌱\n"
        
        embed.description = ranking_text
        embed.set_footer(text="Cập nhật hàng ngày • Xếp hạng dựa trên tổng hạt")
        
        await interaction.followup.send(embed=embed, ephemeral=False)

    @commands.command(name="top", description="Xem bảng xếp hạng top 10")
    async def top_leaderboard_prefix(self, ctx):
        """Show top 10 leaderboard (prefix command)"""
        top_users = await self.get_leaderboard_local(10)
        
        if not top_users:
            await ctx.send("❌ Chưa có ai trong bảng xếp hạng!")
            return
        
        embed = discord.Embed(
            title="🏆 Bảng Xếp Hạng Top 10 Hạt",
            color=discord.Color.gold()
        )
        
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, username, seeds) in enumerate(top_users, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}️⃣"
            ranking_text += f"{medal} **{username}** - {seeds} 🌱\n"
        
        embed.description = ranking_text
        embed.set_footer(text="Cập nhật hàng ngày • Xếp hạng dựa trên tổng hạt")
        
        await ctx.send(embed=embed)

    @commands.command(name="themhat", description="Thêm hạt cho user (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_seeds_admin(self, ctx, user: discord.User, amount: int):
        """Add seeds to a user (Admin only)"""
        # Validate amount
        if amount <= 0:
            await ctx.send("❌ Số lượng phải lớn hơn 0!")
            return
        
        # Get or create user
        await self.get_or_create_user_local(user.id, user.name)
        
        # Add seeds
        await self.add_seeds_local(user.id, amount)
        
        # Get new balance
        new_balance = await self.get_user_balance_local(user.id)
        
        embed = discord.Embed(
            title="Thêm Hạt Thành Công",
            color=discord.Color.green()
        )
        embed.add_field(name="Người nhận", value=f"**{user.name}**", inline=False)
        embed.add_field(name="Hạt thêm", value=f"**+{amount}**", inline=True)
        embed.add_field(name="Số dư mới", value=f"**{new_balance}**", inline=True)
        embed.set_footer(text=f"Thực hiện bởi {ctx.author.name}")
        
        await ctx.send(embed=embed)
        print(f"[ADMIN] {ctx.author.name} added {amount} seeds to {user.name}")

    @app_commands.command(name="themhat", description="Thêm hạt cho user (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user="Người nhận hạt",
        amount="Số lượng hạt muốn thêm"
    )
    async def add_seeds_admin_slash(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Add seeds to a user (Admin only) - Slash command"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate amount
        if amount <= 0:
            await interaction.followup.send("❌ Số lượng phải lớn hơn 0!", ephemeral=True)
            return
        
        # Get or create user
        await self.get_or_create_user_local(user.id, user.name)
        
        # Add seeds
        await self.add_seeds_local(user.id, amount)
        
        # Get new balance
        new_balance = await self.get_user_balance_local(user.id)
        
        embed = discord.Embed(
            title="Thêm Hạt Thành Công",
            color=discord.Color.green()
        )
        embed.add_field(name="Người nhận", value=f"**{user.name}**", inline=False)
        embed.add_field(name="Hạt thêm", value=f"**+{amount}**", inline=True)
        embed.add_field(name="Số dư mới", value=f"**{new_balance}**", inline=True)
        embed.set_footer(text=f"Thực hiện bởi {interaction.user.name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"[ADMIN] {interaction.user.name} added {amount} seeds to {user.name}")

    # ==================== EVENTS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Reward seeds for chat activity"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # Get excluded channels
        excluded_channels = await self.get_excluded_channels(message.guild.id)
        
        # Don't reward in excluded channels
        if message.channel.id in excluded_channels:
            return
        
        # Check cooldown
        user_id = message.author.id
        now = datetime.now().timestamp()
        
        if user_id in self.chat_cooldowns:
            last_reward = self.chat_cooldowns[user_id]
            if now - last_reward < CHAT_REWARD_COOLDOWN:
                return
        
        # Get or create user
        await self.get_or_create_user_local(user_id, message.author.name)
        
        # Award random seeds
        reward = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
        
        # Check if harvest buff is active (x2 multiplier)
        is_buff_active = await self.is_harvest_buff_active(message.guild.id)
        if is_buff_active:
            reward = reward * 2
            print(f"[ECONOMY] 🔥 HARVEST BUFF ACTIVE! {message.author.name} earned {reward} seeds from chat")
        else:
            print(f"[ECONOMY] {message.author.name} earned {reward} seeds from chat")
        
        await self.add_seeds_local(user_id, reward)
        await self.update_last_chat_reward(user_id)
        
        # Update cooldown
        self.chat_cooldowns[user_id] = now

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Reward seeds when someone reacts to a message or forum post"""
        # Don't reward bot reactions
        if user.bot:
            return
        
        # Get message author (the one who posted the message/forum post)
        message = reaction.message
        if not message.author:
            return
        
        # Don't reward self-reactions
        if user.id == message.author.id:
            return
        
        # Must be in a guild
        if not message.guild:
            return
        
        # Get excluded channels
        excluded_channels = await self.get_excluded_channels(message.guild.id)
        
        # Check if channel is excluded
        if message.channel.id in excluded_channels:
            return
        
        # Check if it's a forum post or regular message
        # Forum posts are in ThreadChannel
        is_forum_post = isinstance(message.channel, discord.Thread) and message.channel.parent and hasattr(message.channel.parent, 'type') and message.channel.parent.type == discord.ChannelType.forum
        
        # Check cooldown for the message author (not the reactor)
        author_id = message.author.id
        now = datetime.now().timestamp()
        
        cooldown_key = f"{author_id}_reaction"
        if cooldown_key in self.reaction_cooldowns:
            last_reward = self.reaction_cooldowns[cooldown_key]
            # Use longer cooldown for reactions (120 seconds)
            if now - last_reward < 120:
                return
        
        # Get or create user
        await self.get_or_create_user_local(author_id, message.author.name)
        
        # Award seeds - same as chat reward
        reward = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
        
        # Check if harvest buff is active
        is_buff_active = await self.is_harvest_buff_active(message.guild.id)
        if is_buff_active:
            reward = reward * 2
        
        # Log with context
        location = f"forum post" if is_forum_post else "message"
        if is_buff_active:
            print(f"[ECONOMY] 🔥 HARVEST BUFF! {message.author.name} earned {reward} seeds from emoji reaction on {location}")
        else:
            print(f"[ECONOMY] {message.author.name} earned {reward} seeds from emoji reaction on {location}")
        
        await self.add_seeds_local(author_id, reward)
        self.reaction_cooldowns[cooldown_key] = now

    @tasks.loop(minutes=VOICE_REWARD_INTERVAL)
    async def voice_reward_task(self):
        """Check voice channels and reward members every 5 minutes - ONLY if speaking"""
        try:
            for guild in self.bot.guilds:
                is_buff_active = await self.is_harvest_buff_active(guild.id)
                
                for voice_channel in guild.voice_channels:
                    # Get members in voice (exclude bots) who are SPEAKING
                    speaking_members = [m for m in voice_channel.members if not m.bot and m.voice and m.voice.self_mute == False]
                    
                    if not speaking_members:
                        continue
                    
                    # Award seeds to each speaking member
                    for member in speaking_members:
                        await self.get_or_create_user_local(member.id, member.name)
                        
                        reward = VOICE_REWARD
                        if is_buff_active:
                            reward = reward * 2
                            print(f"[ECONOMY] 🔥 HARVEST BUFF! {member.name} earned {reward} seeds from voice (x2)")
                        else:
                            print(f"[ECONOMY] 🎙️ {member.name} earned {reward} seeds from voice (speaking)")
                        
                        await self.add_seeds_local(member.id, reward)
        
        except Exception as e:
            print(f"[ECONOMY] Voice reward error: {e}")

    @tasks.loop(minutes=VOICE_REWARD_INTERVAL)
    async def voice_affinity_task(self):
        """Increase affinity between members speaking in the same voice channel"""
        try:
            interactions_cog = self.bot.get_cog("InteractionsCog")
            if not interactions_cog:
                return
            
            for guild in self.bot.guilds:
                for voice_channel in guild.voice_channels:
                    # Get members in voice (exclude bots) who are SPEAKING
                    speaking_members = [m for m in voice_channel.members if not m.bot and m.voice and m.voice.self_mute == False]
                    
                    # Need at least 2 members to increase affinity
                    if len(speaking_members) < 2:
                        continue
                    
                    # Increase affinity between all pairs of speaking members
                    for i, member1 in enumerate(speaking_members):
                        for member2 in speaking_members[i+1:]:
                            # Add 3 affinity points per person pair in voice
                            await interactions_cog.add_affinity_local(member1.id, member2.id, 3)
                            print(f"[AFFINITY] 🎙️ {member1.name} & {member2.name} +3 affinity (voice chat)")
        
        except Exception as e:
            print(f"[ECONOMY] Voice affinity task error: {e}")
            import traceback
            traceback.print_exc()

    @voice_reward_task.before_loop
    async def before_voice_reward_task(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()

    @voice_affinity_task.before_loop
    async def before_voice_affinity_task(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import asyncio
import time
from datetime import datetime, timedelta
from database_manager import (
    get_inventory,
    add_item,
    remove_item,
    add_seeds,
    get_user_balance,
    get_or_create_user
)

DB_PATH = "./data/database.db"

# ==================== LOOT TABLES ====================

LOOT_TABLE_NORMAL = {
    "trash": 25,         # Rác (ủng rách, lon nước)
    "common_fish": 60,   # Cá thường (cá chép, cá rô)
    "rare_fish": 10,     # Cá hiếm (cá koi, cá hồi)
    "chest": 5           # Rương báu
}

# Khi cây ở level max hoặc nở hoa (Boost)
LOOT_TABLE_BOOST = {
    "trash": 10,         # Giảm rác
    "common_fish": 40,   # Giảm cá thường
    "rare_fish": 35,     # Tăng mạnh cá hiếm
    "chest": 15          # X3 tỉ lệ rương
}

# Cá thường - key format: "ca_chep" (lowercase, no spaces)
COMMON_FISH = [
    {"key": "ca_chep", "name": "Cá Chép", "emoji": "🐠", "sell_price": 10},
    {"key": "ca_ro", "name": "Cá Rô", "emoji": "🐟", "sell_price": 10},
    {"key": "ca_tre", "name": "Cá Trê", "emoji": "🐟", "sell_price": 12},
]

# Cá hiếm
RARE_FISH = [
    {"key": "ca_koi", "name": "Cá Koi", "emoji": "✨🐠", "sell_price": 50},
    {"key": "ca_hoi", "name": "Cá Hồi", "emoji": "✨🐟", "sell_price": 55},
    {"key": "ca_tam", "name": "Cá Tầm", "emoji": "✨🐟", "sell_price": 60},
    {"key": "ca_rong", "name": "Cá Rồng", "emoji": "🐲", "sell_price": 100},
]

# Create lookup dictionaries
ALL_FISH = {fish["key"]: fish for fish in COMMON_FISH + RARE_FISH}
COMMON_FISH_KEYS = [f["key"] for f in COMMON_FISH]
RARE_FISH_KEYS = [f["key"] for f in RARE_FISH]

# Rác tái chế
TRASH_ITEMS = [
    {"name": "Ủng Rách", "emoji": "🥾"},
    {"name": "Lon Nước", "emoji": "🥫"},
    {"name": "Xà Phòng Cũ", "emoji": "🧼"},
    {"name": "Mảnh Kính", "emoji": "🔨"},
]

# Rương báu - các loại vật phẩm có thể ra
CHEST_LOOT = {
    "fertilizer": 30,       # Phân bón
    "puzzle_piece": 20,     # Mảnh ghép
    "coin_pouch": 20,       # Túi hạt
    "gift_random": 30       # Quà tặng ngẫu nhiên
}

# Các loại quà tặng
GIFT_ITEMS = ["cafe", "flower", "ring", "gift", "chocolate", "card"]

# ==================== UI COMPONENTS ====================

class FishSellView(discord.ui.View):
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
    
    @discord.ui.button(label="Bán Cá Vừa Câu", style=discord.ButtonStyle.green)
    async def sell_caught_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sell only the fish just caught"""
        # Only allow the user who caught the fish to sell
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Calculate money
        total_money = 0
        is_boosted = await self.cog.get_tree_boost_status(self.guild_id)
        multiplier = 2 if is_boosted else 1
        
        for fish_key, quantity in self.caught_items.items():
            fish_info = ALL_FISH.get(fish_key)
            if fish_info:
                base_price = fish_info['sell_price']
                total_money += base_price * quantity * multiplier
        
        # Remove items from inventory
        for fish_key, quantity in self.caught_items.items():
            await remove_item(self.user_id, fish_key, quantity)
        
        # Add money
        await add_seeds(self.user_id, total_money)
        
        # Clean up
        if self.user_id in self.cog.caught_items:
            del self.cog.caught_items[self.user_id]
        
        # Send result
        boost_text = " (Giá x2 do Cây Buff!)" if is_boosted else ""
        fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
        embed = discord.Embed(
            title="💰 Bán Cá Thành Công",
            description=f"Bạn đã bán {sum(self.caught_items.values())} con cá:\n{fish_summary}\n\n**Nhận: {total_money} Hạt**{boost_text}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
        # Disable button after sell
        self.disable_all_items()

class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fishing_cooldown = {}  # {user_id: timestamp}
        self.caught_items = {}  # {user_id: {item_key: quantity}} - temporarily store caught items
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def get_tree_boost_status(self, guild_id: int) -> bool:
        """Check if server tree is at max level (nở hoa/kết trái)"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT level FROM server_tree WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] >= 5:  # Level 5+ = boost
                        return True
        except:
            pass
        return False
    
    async def get_loot_table(self, guild_id: int) -> dict:
        """Get loot table based on tree status"""
        is_boosted = await self.get_tree_boost_status(guild_id)
        return LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
    
    async def roll_loot(self, guild_id: int) -> str:
        """Roll kết quả câu cá"""
        table = await self.get_loot_table(guild_id)
        items = list(table.keys())
        weights = list(table.values())
        return random.choices(items, weights=weights, k=1)[0]
    
    async def add_inventory_item(self, user_id: int, item_name: str, item_type: str):
        """Add item to inventory with type tracking"""
        await add_item(user_id, item_name, 1)
        
        # Also update item_type in DB (extension)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE inventory SET type = ? WHERE user_id = ? AND item_name = ?",
                    (item_type, user_id, item_name)
                )
                await db.commit()
        except:
            pass  # Fallback: type column might not exist yet
    
    async def get_fishing_cooldown_remaining(self, user_id: int) -> int:
        """Get remaining cooldown in seconds"""
        if user_id not in self.fishing_cooldown:
            return 0
        
        cooldown_until = self.fishing_cooldown[user_id]
        remaining = max(0, cooldown_until - time.time())
        return int(remaining)
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="cauca", description="Câu cá - cooldown 30s")
    async def fish_slash(self, interaction: discord.Interaction):
        """Fish via slash command"""
        await self._fish_action(interaction)
    
    @commands.command(name="cauca", description="Câu cá - cooldown 30s")
    async def fish_prefix(self, ctx):
        """Fish via prefix command"""
        await self._fish_action(ctx)
    
    async def _fish_action(self, ctx_or_interaction):
        """Main fishing logic - roll loot 1-5 times per cast"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            channel = ctx_or_interaction.channel
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            channel = ctx_or_interaction.channel
            ctx = ctx_or_interaction
        
        # Check cooldown
        remaining = await self.get_fishing_cooldown_remaining(user_id)
        if remaining > 0:
            msg = f"⏱️ Cần chờ {remaining}s nữa mới được câu lại!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Ensure user exists
        username = ctx.author.name if not is_slash else ctx_or_interaction.user.name
        await get_or_create_user(user_id, username)
        
        # Set cooldown
        self.fishing_cooldown[user_id] = time.time() + 30
        
        # Casting animation
        wait_time = random.randint(1, 5)
        casting_msg = await channel.send(
            f"🎣 **{username}** quăng cần... Chờ cá cắn câu... ({wait_time}s)"
        )
        await asyncio.sleep(wait_time)
        
        # Roll loot 1-5 times
        num_catches = random.randint(1, 5)
        results = {}
        for _ in range(num_catches):
            result = await self.roll_loot(channel.guild.id)
            results[result] = results.get(result, 0) + 1
        
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        boost_text = " ✨**(CÂY BUFF!)**✨" if is_boosted else ""
        
        # Track caught items for sell button
        self.caught_items[user_id] = {}
        
        # Build summary display and process all results
        fish_display = []
        fish_only_items = {}
        
        for result_type, count in results.items():
            if result_type == "trash":
                for _ in range(count):
                    trash = random.choice(TRASH_ITEMS)
                    item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                    await self.add_inventory_item(user_id, item_key, "trash")
                    fish_display.append(f"🥾 {trash['name']} x{count}")
            
            elif result_type == "common_fish":
                for _ in range(count):
                    fish = random.choice(COMMON_FISH)
                    await self.add_inventory_item(user_id, fish['key'], "fish")
                    if fish['key'] not in fish_only_items:
                        fish_only_items[fish['key']] = 0
                    fish_only_items[fish['key']] += 1
                
                # Display grouped
                for key, qty in fish_only_items.items():
                    fish = ALL_FISH[key]
                    fish_display.append(f"{fish['emoji']} {fish['name']} x{qty} ({fish['sell_price']} Hạt)")
            
            elif result_type == "rare_fish":
                for _ in range(count):
                    fish = random.choice(RARE_FISH)
                    await self.add_inventory_item(user_id, fish['key'], "fish")
                    if fish['key'] not in fish_only_items:
                        fish_only_items[fish['key']] = 0
                    fish_only_items[fish['key']] += 1
                
                # Display grouped
                for key, qty in fish_only_items.items():
                    if key in RARE_FISH_KEYS:
                        fish = ALL_FISH[key]
                        fish_display.append(f"✨ {fish['name']} x{qty} ({fish['sell_price']} Hạt)")
            
            elif result_type == "chest":
                for _ in range(count):
                    await self.add_inventory_item(user_id, "treasure_chest", "tool")
                fish_display.append(f"🎁 Rương Kho Báu x{count}")
        
        # Store only fish for the sell button
        self.caught_items[user_id] = fish_only_items
        
        # Build embed
        emoji_map = {"trash": "🥾", "common_fish": "🐟", "rare_fish": "✨", "chest": "🎁"}
        result_emojis = [emoji_map.get(r, "") for r in results.keys()]
        
        title = f"🎣 Câu Được {''.join(result_emojis)} x{num_catches}"
        if num_catches > 1:
            title = f"🎣 BIG HAUL! Câu Được {num_catches} Con!"
        
        embed = discord.Embed(
            title=title,
            description="\n".join(fish_display) if fish_display else "Không có gì",
            color=discord.Color.blue() if num_catches == 1 else discord.Color.gold()
        )
        embed.set_footer(text=f"Tổng câu được: {num_catches} con{boost_text}")
        
        # Create view with sell button if there are fish to sell
        view = None
        if fish_only_items:
            view = FishSellView(self, user_id, fish_only_items, channel.guild.id)
        
        await casting_msg.edit(content="", embed=embed, view=view)
    
    @app_commands.command(name="banca", description="Bán cá - dùng /banca cá_rô hoặc /banca cá_rô, cá_chép")
    @app_commands.describe(fish_types="Loại cá (cá_rô, cá_chép, cá_koi) - phân cách bằng dấu phẩy để bán nhiều loại")
    async def sell_fish_slash(self, interaction: discord.Interaction, fish_types: str = None):
        """Sell selected fish via slash command"""
        await self._sell_fish_action(interaction, fish_types)
    
    @commands.command(name="banca", description="Bán cá - dùng !banca cá_rô hoặc !banca cá_rô, cá_chép")
    async def sell_fish_prefix(self, ctx, *, fish_types: str = None):
        """Sell selected fish via prefix command"""
        await self._sell_fish_action(ctx, fish_types)
    
    async def _sell_fish_action(self, ctx_or_interaction, fish_types: str = None):
        """Sell all fish or specific types logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Filter fish items by type
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH}
        
        if not fish_items:
            msg = "❌ Bạn không có cá nào để bán!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Parse fish_types if specified
        selected_fish = None
        if fish_types:
            # Parse comma-separated fish types
            requested = [f.strip().lower().replace(" ", "_") for f in fish_types.split(",")]
            selected_fish = {k: v for k, v in fish_items.items() if k in requested}
            
            if not selected_fish:
                available = ", ".join(fish_items.keys())
                msg = f"❌ Không tìm thấy cá!\nCá bạn có: {available}"
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
        else:
            # Sell all fish
            selected_fish = fish_items
        
        # Calculate total money
        total_money = 0
        is_boosted = await self.get_tree_boost_status(ctx.guild.id if hasattr(ctx, 'guild') else ctx_or_interaction.guild.id)
        multiplier = 2 if is_boosted else 1
        
        # Calculate money from selected fish
        for fish_key, quantity in selected_fish.items():
            fish_info = ALL_FISH.get(fish_key)
            if fish_info:
                base_price = fish_info['sell_price']
                total_money += base_price * quantity * multiplier
        
        # Remove selected fish from inventory
        for fish_key in selected_fish.keys():
            await remove_item(user_id, fish_key, selected_fish[fish_key])
        
        # Add money
        await add_seeds(user_id, total_money)
        
        # Send result
        boost_text = " (Giá x2 do Cây Buff!)" if is_boosted else ""
        fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in selected_fish.items()])
        embed = discord.Embed(
            title="💰 Bán Cá Thành Công",
            description=f"Bạn đã bán {sum(selected_fish.values())} con cá:\n{fish_summary}\n\n**Nhận: {total_money} Hạt**{boost_text}",
            color=discord.Color.green()
        )
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    @app_commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_slash(self, interaction: discord.Interaction):
        """Open chest via slash command"""
        await self._open_chest_action(interaction)
    
    @commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_prefix(self, ctx):
        """Open chest via prefix command"""
        await self._open_chest_action(ctx)
    
    async def _open_chest_action(self, ctx_or_interaction):
        """Open treasure chest logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Check if user has chest
        inventory = await get_inventory(user_id)
        if inventory.get("treasure_chest", 0) <= 0:
            msg = "❌ Bạn không có Rương Kho Báu!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove chest from inventory
        await remove_item(user_id, "treasure_chest", 1)
        
        # Roll loot
        items = list(CHEST_LOOT.keys())
        weights = list(CHEST_LOOT.values())
        loot_type = random.choices(items, weights=weights, k=1)[0]
        
        # Process loot
        if loot_type == "fertilizer":
            await self.add_inventory_item(user_id, "fertilizer", "tool")
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description="**🌾 Phân Bón** (Dùng `/bonphan` để nuôi cây)",
                color=discord.Color.gold()
            )
        
        elif loot_type == "puzzle_piece":
            pieces = ["puzzle_a", "puzzle_b", "puzzle_c", "puzzle_d"]
            piece = random.choice(pieces)
            await self.add_inventory_item(user_id, piece, "tool")
            piece_display = piece.split("_")[1].upper()
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**🧩 Mảnh Ghép {piece_display}** (Gom đủ 4 mảnh A-B-C-D để đổi quà siêu to!)",
                color=discord.Color.blue()
            )
        
        elif loot_type == "coin_pouch":
            coins = random.randint(100, 500)
            await add_seeds(user_id, coins)
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**💰 Túi Hạt** - Bạn nhận được **{coins} Hạt**!",
                color=discord.Color.green()
            )
        
        else:  # gift_random
            gift = random.choice(GIFT_ITEMS)
            await self.add_inventory_item(user_id, gift, "gift")
            gift_names = {"cafe": "☕ Cà Phê", "flower": "🌹 Hoa", "ring": "💍 Nhẫn", 
                         "gift": "🎁 Quà", "chocolate": "🍫 Sô Cô La", "card": "💌 Thiệp"}
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**{gift_names[gift]}** (Dùng `/tangqua` để tặng cho ai đó)",
                color=discord.Color.magenta()
            )
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    @app_commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây (tăng 50-100 điểm)")
    async def use_fertilizer_slash(self, interaction: discord.Interaction):
        """Use fertilizer via slash command"""
        await self._use_fertilizer_action(interaction)
    
    @commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây")
    async def use_fertilizer_prefix(self, ctx):
        """Use fertilizer via prefix command"""
        await self._use_fertilizer_action(ctx)
    
    async def _use_fertilizer_action(self, ctx_or_interaction):
        """Use fertilizer logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        guild_id = ctx_or_interaction.guild.id
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            guild_id = ctx_or_interaction.guild.id
            ctx = ctx_or_interaction
        
        # Check if user has fertilizer
        inventory = await get_inventory(user_id)
        if inventory.get("fertilizer", 0) <= 0:
            msg = "❌ Bạn không có Phân Bón!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove fertilizer
        await remove_item(user_id, "fertilizer", 1)
        
        # Add to tree
        boost_amount = random.randint(50, 100)
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE server_tree SET progress = progress + ? WHERE guild_id = ?",
                    (boost_amount, guild_id)
                )
                await db.commit()
            
            embed = discord.Embed(
                title="🌾 Phân Bón Hiệu Quả!",
                description=f"**+{boost_amount}** điểm cho Cây Server! (Tổng progress tăng)",
                color=discord.Color.green()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi",
                description=f"Không thể cộng điểm: {str(e)}",
                color=discord.Color.red()
            )
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

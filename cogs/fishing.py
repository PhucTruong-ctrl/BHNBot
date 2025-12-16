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
    "trash": 30,         # Rác (ủng rách, lon nước)
    "common_fish": 60,   # Cá thường (cá chép, cá rô) - nguồn thu chính
    "rare_fish": 5,      # Cá hiếm (cá koi, cá hồi) - giảm để rare thực sự rare
    "chest": 5           # Rương báu
}

# Khi cây ở level max hoặc nở hoa (Boost)
# CHÚ Ý: Boost chỉ áp dụng x2 giá bán, KHÔNG tăng tỷ lệ Cá Hiếm (chống lạm phát)
LOOT_TABLE_BOOST = {
    "trash": 15,         # Giảm rác
    "common_fish": 75,   # Tăng cá thường (thay vì tăng cá hiếm)
    "rare_fish": 5,      # GIỮ NGUYÊN 5% - không tăng cá hiếm (chống lạm phát)
    "chest": 5           # Rương tương tự
}

# Không có mồi câu (No Worm) - Câu được cá nhỏ để kiếm vốn, nhưng cực khó ra đồ xịn
# Để giúp newbie dễ kiếm 10 Hạt đầu tiên và không cảm thấy nản
LOOT_TABLE_NO_WORM = {
    "trash": 50,         # Rác (vừa phải - giúp newbie kiếm cá để bán)
    "common_fish": 49,   # Cá thường (tăng cơ hội kiếm vốn)
    "rare_fish": 1,      # Cực hiếm - cho hy vọng bất ngờ (1%)
    "chest": 0           # Không có rương khi không có mồi
}

# Tỉ lệ roll số lượng cá (1-5) - tỉ lệ giảm dần (NERF từ [40,30,20,8,2] -> [70,20,8,2,0])
# 1 cá: 70%, 2 cá: 20%, 3 cá: 8%, 4 cá: 2%, 5 cá: 0%
# Trung bình: ~1.4 con/lần (giảm từ 2.0)
CATCH_COUNT_WEIGHTS = [70, 20, 8, 2, 0]  # Cho random.choices() với k=1

# Cá thường - key format: "ca_chep" (lowercase, no spaces)
# GIÁ ĐÃ GIẢM để chống lạm phát (Original: 10-12)
COMMON_FISH = [
    {"key": "ca_chep", "name": "Cá Chép", "emoji": "🐠", "sell_price": 5},
    {"key": "ca_ro", "name": "Cá Rô", "emoji": "🐟", "sell_price": 6},
    {"key": "ca_tre", "name": "Cá Trê", "emoji": "🐟", "sell_price": 8},
]

# Cá hiếm
# GIÁ ĐÃ GIẢM để chống lạm phát (Original: 50-100)
RARE_FISH = [
    {"key": "ca_koi", "name": "Cá Koi", "emoji": "✨🐠", "sell_price": 30},
    {"key": "ca_hoi", "name": "Cá Hồi", "emoji": "✨🐟", "sell_price": 40},
    {"key": "ca_tam", "name": "Cá Tầm", "emoji": "✨🐟", "sell_price": 50},
    {"key": "ca_rong", "name": "Cá Rồng", "emoji": "🐲", "sell_price": 80}
]

# Ngọc Trai - Item hiếm từ Tiên Cá (bán giá cao)
PEARL_INFO = {"key": "pearl", "name": "Ngọc Trai", "emoji": "🔮", "sell_price": 150}

# Create lookup dictionaries
ALL_FISH = {fish["key"]: fish for fish in COMMON_FISH + RARE_FISH}
ALL_FISH["pearl"] = PEARL_INFO  # Thêm ngọc trai vào danh sách để có thể bán
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

# Mồi câu (Money Sink)
WORM_COST = 5  # Giá mua mồi - chống lạm phát bằng cách tiêu tiền trước khi câu

# ==================== RANDOM EVENTS ====================
# Tổng tỉ lệ event khoảng 8-10% là đẹp

RANDOM_EVENTS = {
    # --- BAD EVENTS ---
    "snapped_line": {"chance": 0.01, "name": "Đứt Cước!"},
    "police_fine": {"chance": 0.01, "name": "Công An Phạt!"},
    "predator": {"chance": 0.01, "name": "Cá sấu cắn!"},
    "equipment_break": {"chance": 0.005, "name": "Gãy Cần!"},
    "flood": {"chance": 0.005, "name": "Sóng Thần!"},
    "pollution": {"chance": 0.01, "name": "Ô Nhiễm!"},  # NEW: Biến cá thành rác

    # --- GOOD EVENTS ---
    "ghost_blessing": {"chance": 0.005, "name": "Ma Ban Phước!"},
    "mermaid_gift": {"chance": 0.005, "name": "Tiên Cá!"},  # NEW: Tặng Ngọc Trai
    "golden_hook": {"chance": 0.01, "name": "Lưỡi Câu Vàng!"},  # NEW: X2 Cá
    "turtle_gift": {"chance": 0.01, "name": "Rùa Thần!"},  # NEW: Tặng Mồi
}

RANDOM_EVENT_MESSAGES = {
    "snapped_line": "Dây câu bị căng quá mạnh và đứt phựt! 😭 (Mất mồi)",
    "police_fine": "O e o e! 🚔 Công an phường bắt phạt vì câu trộm! (Mất 50 Hạt)",
    "predator": "Một bóng đen lớn lao tới đớp trọn mẻ cá của bạn! 😱 (Mất cá + Mồi)",
    "equipment_break": "Rắc! Cần câu gãy đôi rồi. Cần 5 phút để sửa. 🛠️ (Cooldown tăng)",
    "flood": "Sóng lớn đánh úp! Mọi thứ bị cuốn trôi ra biển. 🌊(Mất hết)",
    "pollution": "Nước ở đây ô nhiễm quá! Cá biến dị hết rồi. 🤢 (Cá biến thành Rác)",
    
    "ghost_blessing": "Một linh hồn lang thang mỉm cười với bạn. ✨ (+100 Hạt)",
    "mermaid_gift": "🧜‍♀️ Nàng Tiên Cá ngoi lên và tặng bạn một viên **Ngọc Trai** lấp lánh!",
    "golden_hook": "Lưỡi câu phát sáng! ✨ **X2 SỐ LƯỢNG CÁ** trong lượt này!",
    "turtle_gift": "🐢 Rùa Thần hiện lên: 'Ta trả lại mồi cho con'. (+2 Giun)",
}

# ==================== UI COMPONENTS ====================

class FishSellView(discord.ui.View):
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
    
    @discord.ui.button(label="💰 Bán Cá Vừa Câu", style=discord.ButtonStyle.green)
    async def sell_caught_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sell only the fish just caught"""
        # Only allow the user who caught the fish to sell
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            print(f"[FISHING] User {interaction.user.name} selling caught fish: {self.caught_items}")
            
            # Calculate money (NO boost multiplier anymore)
            total_money = 0
            
            for fish_key, quantity in self.caught_items.items():
                fish_info = ALL_FISH.get(fish_key)
                if fish_info:
                    base_price = fish_info['sell_price']
                    total_money += base_price * quantity
            
            print(f"[FISHING] Total money: {total_money}")
            
            # Remove items from inventory
            for fish_key, quantity in self.caught_items.items():
                await remove_item(self.user_id, fish_key, quantity)
                print(f"[FISHING] Removed {quantity}x {fish_key} from inventory")
            
            # Add money
            await add_seeds(self.user_id, total_money)
            print(f"[FISHING] Added {total_money} seeds to user {self.user_id}")
            
            # Clean up
            if self.user_id in self.cog.caught_items:
                del self.cog.caught_items[self.user_id]
            
            # Send result
            fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
            embed = discord.Embed(
                title=f"**{interaction.user.name}** đã bán {sum(self.caught_items.values())} con cá",
                description=f"\n{fish_summary}\n**Nhận: {total_money} Hạt**",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
            # Disable button after sell
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            print(f"[FISHING] ✅ Sell completed successfully")
            
        except Exception as e:
            print(f"[FISHING] ❌ ERROR selling fish: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)
            except:
                pass

class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fishing_cooldown = {}  # {user_id: timestamp}
        self.caught_items = {}  # {user_id: {item_key: quantity}} - temporarily store caught items
        self.user_titles = {}  # {user_id: title} - cache danh hiệu người dùng
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def track_caught_fish(self, user_id: int, fish_key: str):
        """Track that user caught this fish type for collection book"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if already caught
                async with db.execute(
                    "SELECT id FROM fish_collection WHERE user_id = ? AND fish_key = ?",
                    (user_id, fish_key)
                ) as cursor:
                    exists = await cursor.fetchone()
                
                if not exists:
                    # Add to collection
                    await db.execute(
                        "INSERT INTO fish_collection (user_id, fish_key, caught_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        (user_id, fish_key)
                    )
                    await db.commit()
                    print(f"[COLLECTION] {user_id} added {fish_key} to collection")
                    return True  # Lần đầu bắt loại này
        except Exception as e:
            print(f"[COLLECTION] Error tracking fish: {e}")
            # Create table nếu không tồn tại
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS fish_collection (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            fish_key TEXT NOT NULL,
                            caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, fish_key)
                        )
                    """)
                    await db.commit()
                    # Thử lại
                    return await self.track_caught_fish(user_id, fish_key)
            except Exception as e2:
                print(f"[COLLECTION] Failed to create table: {e2}")
        
        return False
    
    async def get_collection(self, user_id: int) -> dict:
        """Get user's fish collection"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    """SELECT fish_key, caught_at FROM fish_collection 
                       WHERE user_id = ? ORDER BY caught_at""",
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return {row[0]: row[1] for row in rows}
        except:
            return {}
    
    async def check_collection_complete(self, user_id: int) -> bool:
        """Check if user caught all fish types"""
        collection = await self.get_collection(user_id)
        all_fish_keys = set(COMMON_FISH_KEYS + RARE_FISH_KEYS)
        caught_keys = set(collection.keys())
        return all_fish_keys.issubset(caught_keys)
    
    async def add_title(self, user_id: int, guild_id: int, title: str):
        """Add title to user by assigning Discord role"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                print(f"[TITLE] Guild {guild_id} not found")
                return
            
            user = guild.get_member(user_id)
            if not user:
                print(f"[TITLE] User {user_id} not found in guild {guild_id}")
                return
            
            # Get the role (1450409414111658024)
            role_id = 1450409414111658024
            role = guild.get_role(role_id)
            if not role:
                print(f"[TITLE] Role {role_id} not found in guild {guild_id}")
                return
            
            # Add role to user
            await user.add_roles(role)
            self.user_titles[user_id] = title
            print(f"[TITLE] Added role '{role.name}' to user {user_id}")
        except Exception as e:
            print(f"[TITLE] Error adding title: {e}")
    
    async def get_title(self, user_id: int, guild_id: int) -> str:
        """Get user's title by checking if they have the role"""
        if user_id in self.user_titles:
            return self.user_titles[user_id]
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return ""
            
            user = guild.get_member(user_id)
            if not user:
                return ""
            
            # Check if user has the role (1450409414111658024)
            role_id = 1450409414111658024
            role = guild.get_role(role_id)
            if role and role in user.roles:
                title = "👑 Vua Câu Cá 👑"
                self.user_titles[user_id] = title
                return title
        except Exception as e:
            print(f"[TITLE] Error getting title: {e}")
        
        return ""
    
    async def trigger_random_event(self, user_id: int, guild_id: int) -> dict:
        """Trigger random event during fishing - returns event_type and result"""
        # Default result dict
        result = {
            "triggered": False, "type": None, "message": "",
            "lose_worm": False, "lose_catch": False, "lose_money": 0, "gain_money": 0,
            "cooldown_increase": 0,
            "catch_multiplier": 1,  # Mặc định x1
            "convert_to_trash": False,  # Mặc định False
            "gain_items": {}  # Item nhận được thêm
        }
        
        # Roll for random event
        rand = random.random()
        current_chance = 0
        
        for event_type, event_data in RANDOM_EVENTS.items():
            current_chance += event_data["chance"]
            if rand < current_chance:
                # Event triggered!
                print(f"[EVENT] {event_type} triggered for user {user_id}")
                
                # Build result dict with event data
                result["triggered"] = True
                result["type"] = event_type
                result["message"] = f"{event_data['name']} {RANDOM_EVENT_MESSAGES[event_type]}"
                
                # --- BAD EVENTS ---
                if event_type == "snapped_line":
                    result["lose_worm"] = True
                    result["lose_catch"] = True  # Dây đứt = không câu được gì
                elif event_type == "police_fine":
                    result["lose_money"] = 50
                elif event_type == "predator":
                    result["lose_worm"] = True
                    result["lose_catch"] = True
                elif event_type == "equipment_break":
                    result["cooldown_increase"] = 300
                elif event_type == "flood":
                    result["lose_worm"] = True
                    result["lose_catch"] = True
                elif event_type == "pollution":
                    result["convert_to_trash"] = True
                
                # --- GOOD EVENTS ---
                elif event_type == "ghost_blessing":
                    result["gain_money"] = 100
                elif event_type == "mermaid_gift":
                    result["gain_items"] = {"pearl": 1}
                elif event_type == "golden_hook":
                    result["catch_multiplier"] = 2
                elif event_type == "turtle_gift":
                    result["gain_items"] = {"worm": 2}
                
                return result
        
        # No event
        return {"triggered": False}
    
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
        
        # --- LOGIC MỚI: AUTO-BUY MỒI NẾU CÓ ĐỦ TIỀN ---
        inventory = await get_inventory(user_id)
        has_worm = inventory.get("worm", 0) > 0
        auto_bought = False  # Biến check xem có tự mua không

        # Nếu không có mồi, kiểm tra xem có đủ tiền mua không
        if not has_worm:
            balance = await get_user_balance(user_id)
            if balance >= WORM_COST:
                # Tự động trừ tiền coi như mua mồi dùng ngay
                await add_seeds(user_id, -WORM_COST)
                has_worm = True
                auto_bought = True
                print(f"[FISHING] {username} auto-bought worm (-{WORM_COST} seeds)")
            else:
                # Không có mồi, cũng không đủ tiền -> Chấp nhận câu rác
                has_worm = False
        else:
            # Có mồi trong túi -> Trừ mồi
            await remove_item(user_id, "worm", 1)
            print(f"[FISHING] {username} consumed 1 worm from inventory")
        
        # --- KẾT THÚC LOGIC MỚI ---
        
        print(f"[FISHING] {username} started fishing (user_id={user_id}) [has_worm={has_worm}] [auto_bought={auto_bought}]")
        
        # Set cooldown
        self.fishing_cooldown[user_id] = time.time() + 30
        
        # Casting animation
        wait_time = random.randint(1, 5)
        
        # Thêm thông báo nhỏ nếu tự mua mồi hoặc không có mồi
        status_text = ""
        if auto_bought:
            status_text = f"\n💸 *(-{WORM_COST} Hạt mua mồi)*"
        elif not has_worm:
            status_text = "\n⚠️ *Không có mồi (Tỉ lệ rác cao)*"

        casting_msg = await channel.send(
            f"🎣 **{username}** quăng cần... Chờ cá cắn câu... ({wait_time}s){status_text}"
        )
        await asyncio.sleep(wait_time)
        
        # ==================== TRIGGER RANDOM EVENTS ====================
        event_result = await self.trigger_random_event(user_id, channel.guild.id)
        
        if event_result.get("triggered", False):
            # Random event occurred!
            event_message = event_result["message"]
            
            # Process event effects
            if event_result.get("lose_worm", False) and has_worm:
                await remove_item(user_id, "worm", 1)
                event_message += " (Mất 1 Giun)"
            
            if event_result.get("lose_money", 0) > 0:
                await add_seeds(user_id, -event_result["lose_money"])
                event_message += f" (-{event_result['lose_money']} Hạt)"
            
            if event_result.get("gain_money", 0) > 0:
                await add_seeds(user_id, event_result["gain_money"])
                event_message += f" (+{event_result['gain_money']} Hạt)"
            
            # Process gain_items (Mermaid gift pearls, Turtle gift worms)
            if event_result.get("gain_items", {}):
                for item_key, item_count in event_result["gain_items"].items():
                    await add_item(user_id, item_key, item_count)
                    item_name = ALL_FISH.get(item_key, {}).get("name", item_key)
                    event_message += f" (+{item_count} {item_name})"
            
            # Increase cooldown if needed
            if event_result.get("cooldown_increase", 0) > 0:
                self.fishing_cooldown[user_id] = time.time() + 30 + event_result["cooldown_increase"]
            else:
                self.fishing_cooldown[user_id] = time.time() + 30
            
            # If lose_catch, don't process fishing
            if event_result.get("lose_catch", False):
                embed = discord.Embed(
                    title="⚠️ THẢM HỌA!",
                    description=event_message,
                    color=discord.Color.red()
                )
                await casting_msg.edit(content="", embed=embed)
                print(f"[EVENT] {username} triggered {event_result.get('type')} - fishing cancelled")
                return
            
            # Otherwise, display event message and continue fishing
            embed = discord.Embed(
                title="⚠️ SỰ KIỆN!",
                description=event_message,
                color=discord.Color.orange()
            )
            await casting_msg.edit(content="", embed=embed)
            
            # Wait a bit before showing catch
            await asyncio.sleep(1)
            casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
        # ==================== NORMAL FISHING PROCESSING ====================
        
        # Roll số lượng cá (1-5) với tỉ lệ giảm dần
        num_fish = random.choices([1, 2, 3, 4, 5], weights=CATCH_COUNT_WEIGHTS, k=1)[0]
        
        # Apply catch multiplier from events (e.g., Golden Hook)
        multiplier = event_result.get("catch_multiplier", 1)
        original_num_fish = num_fish
        num_fish = num_fish * multiplier
        if multiplier > 1:
            print(f"[EVENT] {username} activated catch_multiplier x{multiplier}: {original_num_fish} → {num_fish} fish")
        
        # Roll trash (độc lập)
        trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
        
        # Roll chest (độc lập, tỉ lệ thấp)
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        chest_weights = [95, 5] if not is_boosted else [90, 10]
        chest_count = random.choices([0, 1], weights=chest_weights, k=1)[0]
        
        results = {"fish": num_fish}
        if trash_count > 0:
            results["trash"] = trash_count
        if chest_count > 0:
            results["chest"] = chest_count
        
        print(f"[FISHING] {username} rolled: {num_fish} fish, {trash_count} trash, {chest_count} chest")
        
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        boost_text = " ✨**(CÂY BUFF!)**✨" if is_boosted else ""
        
        # Track caught items for sell button
        self.caught_items[user_id] = {}
        
        # Build summary display and process all results
        fish_display = []
        fish_only_items = {}
        
        # FIX: Track if rare fish already caught this turn (Max 1 rare per cast)
        caught_rare_this_turn = False
        
        # Chọn loot table dựa trên có worm hay không
        if has_worm:
            # Có mồi = dùng loot table bình thường (có cả cá hiếm)
            loot_table = LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
        else:
            # Không có mồi = dùng loot table giảm cực (chỉ rác và cá thường)
            loot_table = LOOT_TABLE_NO_WORM
        
        # Process fish - roll loại cá cho mỗi con
        # CHÚ Ý: Boost KHÔNG tăng tỷ lệ Cá Hiếm, chỉ tăng tỷ lệ Rương để balance
        for _ in range(num_fish):
            # Roll từ LOOT_TABLE để xác định loại (Rare vs Common)
            # Normalize weights để lấy tỉ lệ common vs rare
            fish_weights_sum = loot_table["common_fish"] + loot_table["rare_fish"]
            
            # Nếu không có mồi, fish_weights_sum = 30 + 0 = 30
            # Lúc này common_ratio = 100%, rare_ratio = 0% (không bao giờ rare)
            if fish_weights_sum == 0:
                # Nếu không có cá nào trong loot table (chỉ có rác/rương)
                common_ratio = 1.0
                rare_ratio = 0.0
            else:
                common_ratio = loot_table["common_fish"] / fish_weights_sum
                rare_ratio = loot_table["rare_fish"] / fish_weights_sum
            
            is_rare = random.choices([False, True], weights=[common_ratio, rare_ratio], k=1)[0]
            
            # Check if convert_to_trash event is active (e.g., Pollution)
            if event_result.get("convert_to_trash", False):
                # Convert fish to trash
                trash = random.choice(TRASH_ITEMS)
                item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                await self.add_inventory_item(user_id, item_key, "trash")
                print(f"[EVENT-POLLUTION] {username} fish converted to trash: {item_key}")
                continue
            
            # FIX: Nếu đã bắt rare rồi hoặc roll ra rare lần này nhưng đã bắt rare trước -> bắt buộc common
            if is_rare and not caught_rare_this_turn:
                fish = random.choice(RARE_FISH)
                caught_rare_this_turn = True  # Đánh dấu đã bắt rare
                print(f"[FISHING] {username} caught RARE fish: {fish['key']} ✨ (Max 1 rare per cast)")
                await self.add_inventory_item(user_id, fish['key'], "fish")
                # Track in collection
                is_new_collection = await self.track_caught_fish(user_id, fish['key'])
                if is_new_collection:
                    print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                if fish['key'] not in fish_only_items:
                    fish_only_items[fish['key']] = 0
                fish_only_items[fish['key']] += 1
            else:
                # Bắt cá thường (hoặc roll rare lần 2+ thì buộc common)
                fish = random.choice(COMMON_FISH)
                print(f"[FISHING] {username} caught common fish: {fish['key']}")
                await self.add_inventory_item(user_id, fish['key'], "fish")
                # Track in collection
                is_new_collection = await self.track_caught_fish(user_id, fish['key'])
                if is_new_collection:
                    print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                if fish['key'] not in fish_only_items:
                    fish_only_items[fish['key']] = 0
                fish_only_items[fish['key']] += 1
        
        # Display fish grouped
        for key, qty in fish_only_items.items():
            fish = ALL_FISH[key]
            emoji = fish['emoji']
            total_price = fish['sell_price'] * qty  # Multiply price by quantity
            fish_display.append(f"{emoji} {fish['name']} x{qty} ({total_price} Hạt)")
        
        # Process trash (độc lập)
        if trash_count > 0:
            trash_items_caught = {}
            for _ in range(trash_count):
                trash = random.choice(TRASH_ITEMS)
                item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                await self.add_inventory_item(user_id, item_key, "trash")
                if item_key not in trash_items_caught:
                    trash_items_caught[item_key] = 0
                trash_items_caught[item_key] += 1
            
            for key, qty in trash_items_caught.items():
                trash_name = key.replace("trash_", "").replace("_", " ").title()
                fish_display.append(f"🥾 {trash_name} x{qty}")
            print(f"[FISHING] {username} caught trash: {trash_items_caught}")
        
        # Process chest (độc lập)
        if chest_count > 0:
            for _ in range(chest_count):
                await self.add_inventory_item(user_id, "treasure_chest", "tool")
            fish_display.append(f"🎁 Rương Kho Báu x{chest_count}")
            print(f"[FISHING] {username} caught {chest_count}x TREASURE CHEST! 🎁")
        
        # Store only fish for the sell button
        self.caught_items[user_id] = fish_only_items
        print(f"[FISHING] {username} final caught items: {fish_only_items}")
        
        # Check if collection is complete and award title if needed
        is_complete = await self.check_collection_complete(user_id)
        title_earned = False
        if is_complete:
            current_title = await self.get_title(user_id, channel.guild.id)
            if not current_title or "Vua" not in current_title:
                await self.add_title(user_id, channel.guild.id, "👑 Vua Câu Cá 👑")
                title_earned = True
                print(f"[TITLE] {username} earned 'Vua Câu Cá' title!")
        
        # Build embed with item summary
        total_catches = num_fish + trash_count + chest_count
        
        # Create summary text for title
        summary_parts = []
        for key, qty in fish_only_items.items():
            fish = ALL_FISH[key]
            summary_parts.append(f"{qty} {fish['name']}")
        if chest_count > 0:
            summary_parts.append(f"{chest_count} Rương")
        
        summary_text = " và ".join(summary_parts) if summary_parts else "Rác"
        title = f"🎣 {username} Câu Được {summary_text}"
        
        if num_fish > 2:
            title = f"🎣 BIG HAUL! {username} Bắt {num_fish} Con Cá! 🎉"
        
        # Add title-earned message if applicable
        if title_earned:
            title = f"🎣 {title}\n👑 **DANH HIỆU: VUA CÂU CÁ ĐƯỢC MỞ KHÓA!** 👑"
        
        embed = discord.Embed(
            title=title,
            description="\n".join(fish_display) if fish_display else "Không có gì",
            color=discord.Color.gold() if title_earned else (discord.Color.blue() if total_catches == 1 else discord.Color.gold())
        )
        
        if title_earned:
            embed.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã bắt được **tất cả các loại cá**!\nChúc mừng bạn trở thành **Vua Câu Cá**! 🎉\nXem `/suutapca` để xác nhận!",
                inline=False
            )
        
        embed.set_footer(text=f"Tổng câu được: {total_catches} cá{boost_text}")
        
        # Create view with sell button if there are fish to sell
        view = None
        if fish_only_items:
            view = FishSellView(self, user_id, fish_only_items, channel.guild.id)
            print(f"[FISHING] Created sell button for {username} with {len(fish_only_items)} fish types")
        else:
            print(f"[FISHING] No fish to sell, button not shown")
        
        await casting_msg.edit(content="", embed=embed, view=view)
        print(f"[FISHING] ✅ Fishing result posted for {username}")
    
    
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
        # FIX: Boost không nhân đôi giá bán (chống lạm phát), giá cố định
        is_boosted = await self.get_tree_boost_status(ctx.guild.id if hasattr(ctx, 'guild') else ctx_or_interaction.guild.id)
        
        # Calculate money from selected fish (NO multiplier on boost anymore)
        for fish_key, quantity in selected_fish.items():
            fish_info = ALL_FISH.get(fish_key)
            if fish_info:
                base_price = fish_info['sell_price']
                total_money += base_price * quantity
        
        # Remove selected fish from inventory
        for fish_key in selected_fish.keys():
            await remove_item(user_id, fish_key, selected_fish[fish_key])
        
        # Add money
        await add_seeds(user_id, total_money)
        
        # Send result
        # Boost không còn x2 giá nữa - chỉ tăng drop rate rương thôi
        fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in selected_fish.items()])
        username = ctx.author.name if hasattr(ctx, 'author') else ctx.user.name
        embed = discord.Embed(
                title=f"**{username}** đã bán {sum(selected_fish.values())} con cá",
                description=f"\n{fish_summary}\n**Nhận: {total_money} Hạt**",
                color=discord.Color.green()
        )
        
        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=True)
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
            coins = random.randint(100, 200)
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
    
    # ==================== CRAFT/RECYCLE ====================
    
    @app_commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    @app_commands.describe(
        action="Để trống để xem thông tin, hoặc 'phan' để tạo phân bón"
    )
    async def recycle_trash_slash(self, interaction: discord.Interaction, action: str = None):
        """Recycle trash via slash command"""
        await self._recycle_trash_action(interaction, action)
    
    @commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    async def recycle_trash_prefix(self, ctx, action: str = None):
        """Recycle trash via prefix command"""
        await self._recycle_trash_action(ctx, action)
    
    async def _recycle_trash_action(self, ctx_or_interaction, action: str = None):
        """Recycle trash logic - auto converts 10 trash → 1 fertilizer"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=True)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Count all trash items
        trash_count = sum(qty for key, qty in inventory.items() if key.startswith("trash_"))
        
        if trash_count == 0:
            msg = "❌ Bạn không có rác nào để tái chế!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Check if user has enough trash
        if trash_count < 10:
            msg = f"❌ Bạn cần 10 rác để tạo phân bón, hiện có {trash_count}"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove 10 trash items
        trash_removed = 0
        for key in list(inventory.keys()):
            if key.startswith("trash_") and trash_removed < 10:
                qty_to_remove = min(inventory[key], 10 - trash_removed)
                await remove_item(user_id, key, qty_to_remove)
                trash_removed += qty_to_remove
        
        # Add 1 fertilizer
        await self.add_inventory_item(user_id, "fertilizer", "tool")
        
        embed = discord.Embed(
            title="✅ Tái Chế Thành Công",
            description="10 Rác → 1 🌱 Phân Bón",
            color=discord.Color.green()
        )
        print(f"[RECYCLE] {ctx.author.name if not is_slash else ctx.user.name} recycled 10 trash → 1 fertilizer")
        
        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=True)
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
                    "UPDATE server_tree SET current_progress = current_progress + ? WHERE guild_id = ?",
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
    
    # ==================== COLLECTION BOOK ====================
    
    @app_commands.command(name="suutapca", description="Xem Bộ Sưu Tập Cá - Câu Đủ Tất Cả Để Thành Vua Câu Cá!")
    async def view_collection_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """View fish collection via slash command"""
        target_user = user or interaction.user
        await self._view_collection_action(interaction, target_user.id, target_user.name)
    
    @commands.command(name="suutapca", description="Xem Bộ Sưu Tập Cá")
    async def view_collection_prefix(self, ctx, user: discord.User = None):
        """View fish collection via prefix command"""
        target_user = user or ctx.author
        await self._view_collection_action(ctx, target_user.id, target_user.name)
    
    async def _view_collection_action(self, ctx_or_interaction, user_id: int, username: str):
        """View collection logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            ctx = ctx_or_interaction
            guild_id = ctx_or_interaction.guild_id
        else:
            ctx = ctx_or_interaction
            guild_id = ctx_or_interaction.guild.id
        
        # Get collection
        collection = await self.get_collection(user_id)
        
        # Separate common and rare
        common_caught = set()
        rare_caught = set()
        
        for fish_key in collection.keys():
            if fish_key in RARE_FISH_KEYS:
                rare_caught.add(fish_key)
            elif fish_key in COMMON_FISH_KEYS:
                common_caught.add(fish_key)
        
        # Get total count
        total_all_fish = len(COMMON_FISH_KEYS + RARE_FISH_KEYS)
        total_caught = len(common_caught) + len(rare_caught)
        completion_percent = int((total_caught / total_all_fish) * 100)
        
        # Check if completed
        is_complete = await self.check_collection_complete(user_id)
        
        # Get current title
        current_title = await self.get_title(user_id, guild_id)
        
        # Build embed
        embed = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_fish}** ({completion_percent}%) ",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        # Add title if has
        if current_title:
            embed.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add common fish section
        common_display = []
        for fish in COMMON_FISH:
            emoji = "✅" if fish['key'] in common_caught else "❌"
            common_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        embed.add_field(
            name=f"🐠 Cá Thường ({len(common_caught)}/{len(COMMON_FISH)})",
            value="\n".join(common_display) if common_display else "Không có",
            inline=False
        )
        
        # Add rare fish section
        rare_display = []
        for fish in RARE_FISH:
            emoji = "✅" if fish['key'] in rare_caught else "❌"
            rare_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        embed.add_field(
            name=f"✨ Cá Hiếm ({len(rare_caught)}/{len(RARE_FISH)})",
            value="\n".join(rare_display) if rare_display else "Không có",
            inline=False
        )
        
        # Add completion message
        if is_complete:
            embed.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã trở thành **👑 VUA CÂU CÁ 👑**!\nCảm ơn sự kiên trì của bạn! 🎉",
                inline=False
            )
        else:
            missing_count = total_all_fish - total_caught
            embed.add_field(
                name="📝 Còn Lại",
                value=f"Bạn còn cần bắt **{missing_count}** loại cá nữa để trở thành Vua Câu Cá! 💪",
                inline=False
            )
        
        embed.set_footer(text="Mỗi lần bắt một loại cá mới, nó sẽ được thêm vào sưu tập của bạn!")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

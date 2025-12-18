import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database_manager import (
    get_user_balance,
    add_seeds,
    get_inventory,
    add_item,
    remove_item
)

DB_PATH = "./data/database.db"

# Shop Items Definition
SHOP_ITEMS = {
    "cafe": {"name": "Cà phê", "cost": 50, "emoji": "☕", "description": "Đồ uống yêu thích của mọi người"},
    "flower": {"name": "Hoa", "cost": 75, "emoji": "🌹", "description": "Bông hoa đẹp xinh để tặng"},
    "ring": {"name": "Nhẫn", "cost": 150, "emoji": "💍", "description": "Nhẫn quý giá, biểu tượng của tình yêu"},
    "gift": {"name": "Quà", "cost": 100, "emoji": "🎁", "description": "Một món quà bất ngờ"},
    "chocolate": {"name": "Sô cô la", "cost": 60, "emoji": "🍫", "description": "Sô cô la ngon ngon, ngọt ngào"},
    "card": {"name": "Thiệp", "cost": 40, "emoji": "💌", "description": "Thiệp chúc mừng lời chúc tốt"},
    "worm": {"name": "Giun (Mồi Câu)", "cost": 10, "emoji": "🪱", "description": "Mồi để câu cá"},
    # Pet Items
    "nuoc": {"name": "Nước Tinh Khiết", "cost": 20, "emoji": "💧", "description": "Nước sạch cho thú cưng"},
    "vitamin": {"name": "Vitamin Tổng Hợp", "cost": 50, "emoji": "💊", "description": "Giúp thú cưng mau lớn"},
    "thuc_an_cao_cap": {"name": "Thức Ăn Cao Cấp", "cost": 100, "emoji": "🍱", "description": "Bữa ăn sang chảnh cho thú cưng"},
    # Consumable buff items (very expensive)
    "nuoc_tang_luc": {"name": "Nước Tăng Lực", "cost": 15000, "emoji": "💪", "description": "Tăng 65% lên 90% thắng 'Dìu Cá' (1 lần)"},
    "gang_tay_xin": {"name": "Găng Tay Câu Cá", "cost": 15000, "emoji": "🥊", "description": "Tăng 65% lên 90% thắng 'Dìu Cá' (1 lần)"},
    "thao_tac_tinh_vi": {"name": "Thao Tác Tinh Vi", "cost": 16000, "emoji": "🎯", "description": "Tăng 65% lên 92% thắng 'Dìu Cá' (1 lần)"},
    "tinh_yeu_ca": {"name": "Tình Yêu Với Cá", "cost": 14500, "emoji": "❤️", "description": "Tăng 65% lên 88% thắng 'Dìu Cá' (1 lần)"},
    # Wave detector for legendary whale
    "may_do_song": {"name": "Máy Dò Sóng", "cost": 20000, "emoji": "📡", "description": "Phát hiện sóng 52Hz của Cá Voi Buồn Bã (1 lần dùng)"},
    # Commemorative items (Season rewards - NOT for sale)
    "qua_ngot_mua_1": {"name": "Quả Ngọt Mùa 1", "cost": None, "emoji": "🍎", "description": "Vật kỉ niệm từ mùa 1 - Chứng tỏ bạn là người lập công xây dựng server!"},
    "qua_ngot_mua_2": {"name": "Quả Ngọt Mùa 2", "cost": None, "emoji": "🍏", "description": "Vật kỉ niệm từ mùa 2 - Tiếp tục lập công xây dựng server!"},
    "qua_ngot_mua_3": {"name": "Quả Ngọt Mùa 3", "cost": None, "emoji": "🍊", "description": "Vật kỉ niệm từ mùa 3 - Cộng đồng mạnh mẽ hơn!"},
    "qua_ngot_mua_4": {"name": "Quả Ngọt Mùa 4", "cost": None, "emoji": "🍋", "description": "Vật kỉ niệm từ mùa 4 - Kiên trì xây dựng!"},
    "qua_ngot_mua_5": {"name": "Quả Ngọt Mùa 5", "cost": None, "emoji": "🍌", "description": "Vật kỉ niệm từ mùa 5 - Hành trình vĩ đại!"},
}

# Reverse mapping: Vietnamese name -> item key
VIETNAMESE_TO_ITEM_KEY = {item_info['name']: key for key, item_info in SHOP_ITEMS.items()}

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_seeds(self, user_id: int) -> int:
        """Get user's current seeds"""
        return await get_user_balance(user_id)

    async def reduce_seeds(self, user_id: int, amount: int):
        """Reduce user's seeds"""
        balance_before = await get_user_balance(user_id)
        await add_seeds(user_id, -amount)
        balance_after = balance_before - amount
        print(
            f"[SHOP] [SEED_UPDATE] user_id={user_id} seed_change=-{amount} "
            f"balance_before={balance_before} balance_after={balance_after}"
        )

    async def add_item_local(self, user_id: int, item_name: str, quantity: int = 1):
        """Add item to user's inventory"""
        await add_item(user_id, item_name, quantity)

    async def remove_item(self, user_id: int, item_name: str, quantity: int = 1) -> bool:
        """Remove item from user's inventory. Return True if successful"""
        return await remove_item(user_id, item_name, quantity)

    async def get_inventory(self, user_id: int) -> dict:
        """Get user's inventory"""
        return await get_inventory(user_id)

    # ==================== COMMANDS ====================

    @app_commands.command(name="shop", description="Xem danh sách quà tặng & vật phẩm trong cửa hàng")
    async def shop(self, interaction: discord.Interaction):
        """Display shop menu"""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🏪 Cửa Hàng Quà Tặng & Vật Phẩm",
            color=discord.Color.purple()
        )
        
        # Regular gifts section
        gifts_text = ""
        consumables_text = ""
        
        for item_key, item_info in SHOP_ITEMS.items():
            if item_key in ["nuoc_tang_luc", "gang_tay_xin", "thao_tac_tinh_vi", "tinh_yeu_ca"]:
                consumables_text += f"{item_info['emoji']} **{item_info['name']}** - {item_info['cost']} hạt\n"
            else:
                gifts_text += f"{item_info['emoji']} **{item_info['name']}** - {item_info['cost']} hạt\n"
        
        if gifts_text:
            embed.add_field(name="💝 Quà Tặng", value=gifts_text, inline=False)
        
        if consumables_text:
            embed.add_field(name="💪 Vật Phẩm Buff", value=consumables_text, inline=False)
        
        embed.add_field(
            name="📖 Cách Mua",
            value="**Lệnh:** `/mua <item_key> [số_lượng]`\n\n**Ví dụ:**\n- `/mua cafe 1` (Cà phê)\n- `/mua nuoc_tang_luc 1` (Nước Tăng Lực)\n- `/mua may_do_song 1` (Máy Dò Sóng)\n\n**Item key:** Dùng tên item viết thường, có gạch dưới",
            inline=False
        )
        embed.add_field(
            name="💪 Buff Items",
            value="🔹 Dùng `/sudung [item_key]` để kích hoạt buff trong một lần câu cá huyền thoại\n"
                  "🔹 Dùng `/tuido` để xem các vật phẩm trong túi",
            inline=False
        )
        embed.set_footer(text="Dùng /tangqua để tặng quà cho người khác")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mua", description="Mua quà & vật phẩm từ cửa hàng")
    @app_commands.describe(
        item="Item key: cafe, flower, ring, gift, chocolate, card, worm hoặc nuoc_tang_luc, gang_tay_xin, thao_tac_tinh_vi, tinh_yeu_ca hoặc may_do_song",
        soluong="Số lượng muốn mua (mặc định: 1)"
    )
    async def buy_slash(self, interaction: discord.Interaction, item: str = None, soluong: int = 1):
        """Buy item from shop"""
        await interaction.response.defer(ephemeral=True)
        
        # If no item specified, show menu
        if item is None:
            await self._show_shop_menu(interaction, is_slash=True)
            return
        
        # Validate quantity
        if soluong < 1:
            await interaction.followup.send(
                f"❌ Số lượng phải >= 1!",
                ephemeral=True
            )
            return
        
        # Try to match Vietnamese name to item key
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            available = ", ".join(VIETNAMESE_TO_ITEM_KEY.keys())
            await interaction.followup.send(
                f"❌ Item không tồn tại!\nCác item có sẵn: {available}",
                ephemeral=True
            )
            return
        
        item_info = SHOP_ITEMS[item_key]
        cost_per_item = item_info['cost']
        total_cost = cost_per_item * soluong
        user_id = interaction.user.id
        
        # Check balance
        seeds = await self.get_seeds(user_id)
        if seeds < total_cost:
            await interaction.followup.send(
                f"❌ Bạn không đủ hạt!\n"
                f"Cần: {total_cost} hạt | Hiện có: {seeds} hạt",
                ephemeral=True
            )
            return
        
        # Process purchase
        await self.reduce_seeds(user_id, total_cost)
        await self.add_item_local(user_id, item_key, soluong)
        
        quantity_text = f" x{soluong}" if soluong > 1 else ""
        embed = discord.Embed(
            title="✅ Mua thành công!",
            description=f"Bạn vừa mua **{item}{quantity_text}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
        embed.add_field(name="💾 Còn lại", value=f"{seeds - total_cost} hạt", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        new_balance = seeds - total_cost
        print(
            f"[SHOP] [PURCHASE] user_id={user_id} username={interaction.user.name} "
            f"item_key={item_key} quantity={soluong} seed_change=-{total_cost} balance_after={new_balance}"
        )

    @commands.command(name="mua", description="Mua quà & vật phẩm - Dùng !mua [item_key] [số_lượng]")
    async def buy_prefix(self, ctx, item: str = None, *, soluong_or_item: str = None):
        """Buy item from shop via prefix - Usage: !mua [item_name] [quantity]"""
        # If no item specified, show menu
        if item is None:
            await self._show_shop_menu(ctx, is_slash=False)
            return
        
        # Handle parameter parsing
        # If soluong_or_item is provided, it could be quantity or second word of item name
        soluong = 1
        if soluong_or_item is not None:
            # Try to parse as number first
            try:
                soluong = int(soluong_or_item)
            except ValueError:
                # If not a number, concatenate back to item name
                item = f"{item} {soluong_or_item}"
        
        # Validate quantity
        if soluong < 1:
            await ctx.send(f"❌ Số lượng phải >= 1!")
            return
        
        # Try to match Vietnamese name to item key
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            available = ", ".join(VIETNAMESE_TO_ITEM_KEY.keys())
            await ctx.send(f"❌ Item không tồn tại!\nCác item có sẵn: {available}")
            return
        
        item_info = SHOP_ITEMS[item_key]
        cost_per_item = item_info['cost']
        total_cost = cost_per_item * soluong
        user_id = ctx.author.id
        
        # Check balance
        seeds = await self.get_seeds(user_id)
        if seeds < total_cost:
            await ctx.send(f"❌ Bạn không đủ hạt!\nCần: {total_cost} hạt | Hiện có: {seeds} hạt")
            return
        
        # Process purchase
        await self.reduce_seeds(user_id, total_cost)
        await self.add_item_local(user_id, item_key, soluong)
        
        quantity_text = f" x{soluong}" if soluong > 1 else ""
        embed = discord.Embed(
            title="✅ Mua thành công!",
            description=f"Bạn vừa mua **{item}{quantity_text}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
        embed.add_field(name="💾 Còn lại", value=f"{seeds - total_cost} hạt", inline=True)
        
        await ctx.send(embed=embed)
        new_balance = seeds - total_cost
        print(
            f"[SHOP] [PURCHASE] user_id={user_id} username={ctx.author.name} "
            f"item_key={item_key} quantity={soluong} seed_change=-{total_cost} balance_after={new_balance}"
        )

    async def _show_shop_menu(self, ctx_or_interaction, is_slash: bool):
        """Show shop menu with all items"""
        embed = discord.Embed(
            title="🏪 MENU MUA ĐỒ",
            color=discord.Color.gold()
        )
        
        # Regular gifts section
        gifts_text = ""
        consumables_text = ""
        
        for item_key, item_info in SHOP_ITEMS.items():
            line = f"{item_info['emoji']} **{item_info['name']}** - {item_info['cost']} hạt\n    💬 {item_info.get('description', 'N/A')}\n"
            if item_key in ["nuoc_tang_luc", "gang_tay_xin", "thao_tac_tinh_vi", "tinh_yeu_ca"]:
                consumables_text += line
            else:
                gifts_text += line
        
        if gifts_text:
            embed.add_field(name="💝 QUÀNG TẶNG", value=gifts_text, inline=False)
        
        if consumables_text:
            embed.add_field(name="💪 VẬT PHẨM BUFF (Siêu Đắt)", value=consumables_text, inline=False)
        
        embed.add_field(
            name="📖 CÁCH MUA",
            value="**Slash Command:** `/mua [Tên Item] [Số Lượng]`\n"
                  "**Prefix Command:** `!mua [Tên Item] [Số Lượng]`\n\n"
                  "**Ví dụ:**\n"
                  "• `/mua Cà phê 5`\n"
                  "• `!mua Nước Tăng Lực 1`",
            inline=False
        )
        embed.set_footer(text="Dùng /shop để xem lại menu này")
        
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

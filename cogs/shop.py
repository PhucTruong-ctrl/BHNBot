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
from .fishing.mechanics.legendary_quest_helper import is_legendary_caught
from .fishing.utils.consumables import CONSUMABLE_ITEMS
from core.logger import setup_logger

logger = setup_logger("ShopCog", "cogs/shop.log")

DB_PATH = "./data/database.db"

# Shop Items Definition
# Maps item keys to their metadata (name, cost, emoji, description)
SHOP_ITEMS = {
    "cafe": {"name": "Cà phê", "cost": 50, "emoji": "☕", "description": "Đồ uống yêu thích của mọi người"},
    "flower": {"name": "Hoa", "cost": 75, "emoji": "🌹", "description": "Bông hoa đẹp xinh để tặng"},
    "ring": {"name": "Nhẫn", "cost": 150, "emoji": "💍", "description": "Nhẫn quý giá, biểu tượng của tình yêu"},
    "gift": {"name": "Quà", "cost": 100, "emoji": "🎁", "description": "Một món quà bất ngờ"},
    "chocolate": {"name": "Sô cô la", "cost": 60, "emoji": "🍫", "description": "Sô cô la ngon ngon, ngọt ngào"},
    "card": {"name": "Thiệp", "cost": 40, "emoji": "💌", "description": "Thiệp chúc mừng lời chúc tốt"},
    "moi": {"name": "Giun (Mồi Câu)", "cost": 10, "emoji": "🪱", "description": "Mồi để câu cá"},
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
    """Cog for managing the shop system, purchases, and currency transactions.

    Handles both slash commands and prefix commands for buying items.
    """
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    async def get_seeds(self, user_id: int) -> int:
        """Retrieves user's current seed balance (currency).

        Args:
            user_id (int): The Discord user ID.

        Returns:
            int: The current balance.
        """
        return await get_user_balance(user_id)

    async def reduce_seeds(self, user_id: int, amount: int):
        """Deducts seeds from user's balance.

        Args:
            user_id (int): The Discord user ID.
            amount (int): The amount to deduct.
        """
        balance_before = await get_user_balance(user_id)
        await add_seeds(user_id, -amount)
        balance_after = balance_before - amount
        logger.info(
            f"[SHOP] [SEED_UPDATE] user_id={user_id} seed_change=-{amount} "
            f"balance_before={balance_before} balance_after={balance_after}"
        )

    async def add_item_local(self, user_id: int, item_id: str, quantity: int = 1):
        """Adds an item to the user's inventory.

        Args:
            user_id (int): The Discord user ID.
            item_id (str): The unique key of the item.
            quantity (int, optional): The amount to add. Defaults to 1.
        """
        await add_item(user_id, item_id, quantity)

    async def remove_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Removes an item from the user's inventory.

        Args:
            user_id (int): The Discord user ID.
            item_id (str): The item key.
            quantity (int): The amount to remove.

        Returns:
            bool: True if successful.
        """
        return await remove_item(user_id, item_id, quantity)

    async def get_inventory(self, user_id: int) -> dict:
        """Retrieves user's inventory data.

        Returns:
            dict: The inventory dictionary {item_id: quantity}.
        """
        return await get_inventory(user_id)

    # ==================== COMMANDS ====================

    @app_commands.command(name="mua", description="Mua quà & vật phẩm từ cửa hàng")
    @app_commands.describe(
        item="Item key: cafe, flower, ring, gift, chocolate, card, worm hoặc nuoc_tang_luc, gang_tay_xin, thao_tac_tinh_vi, tinh_yeu_ca hoặc may_do_song",
        soluong="Số lượng muốn mua (mặc định: 1)"
    )
    async def buy_slash(self, interaction: discord.Interaction, item: str = None, soluong: int = 1):
        """Slash command: Buy items from the shop.

        Args:
            interaction (discord.Interaction): The interaction object.
            item (str, optional): The name of the item to buy.
            soluong (int, optional): The quantity. Defaults to 1.
        """
        await interaction.response.defer(ephemeral=True)
        
        # If no item specified, show menu
        if item is None:
            await self._show_shop_menu(interaction, is_slash=True)
            return
        
        # Validate quantity
        if soluong <= 0:
            await interaction.followup.send(
                f"❌ Số lượng không hợp lệ!",
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
        
        # Check if legendary item already obtained
        if item_key == "may_do_song":
            if await is_legendary_caught(user_id, "ca_voi_52hz"):
                await interaction.followup.send("📡 **TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI**\n\n\"Máy dò sóng chỉ phát ra những tiếng rè tĩnh lặng... Tần số 52Hz cô đơn nhất đại dương không còn lạc lõng nữa, vì nó đã tìm thấy bạn. Không còn tín hiệu nào khác để dò tìm.\"", ephemeral=True)
                return
        
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
        
        logger.info(f"[SHOP] [BUY] user_id={user_id} item={item_key} quantity={soluong} total_cost={total_cost} balance_before={seeds} balance_after={seeds - total_cost}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        new_balance = seeds - total_cost
        logger.info(
            f"[SHOP] [PURCHASE] user_id={user_id} username={interaction.user.name} "
            f"item_key={item_key} quantity={soluong} seed_change=-{total_cost} balance_after={new_balance}"
        )

    @commands.command(name="mua", description="Mua quà & vật phẩm - Dùng !mua [item_key] [số_lượng]")
    async def buy_prefix(self, ctx, item: str = None, *, soluong_or_item: str = None):
        """Prefix command: Buy items from the shop.
        
        Usage: !mua [item_id] [quantity]
        """
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
        if soluong <= 0:
            await ctx.send(f"❌ Số lượng không hợp lệ!")
            return
        
        # Try to match Vietnamese name to item key
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            available = ", ".join(VIETNAMESE_TO_ITEM_KEY.keys())
            await ctx.send(f"❌ Item không tồn tại!\nCác item có sẵn: {available}")
            return
        
        item_info = SHOP_ITEMS[item_key]
        
        # Check if legendary item already obtained
        if item_key == "may_do_song":
            if await is_legendary_caught(user_id, "ca_voi_52hz"):
                await ctx.send("📡 **TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI**\n\n\"Máy dò sóng chỉ phát ra những tiếng rè tĩnh lặng... Tần số 52Hz cô đơn nhất đại dương không còn lạc lõng nữa, vì nó đã tìm thấy bạn. Không còn tín hiệu nào khác để dò tìm.\"")
                return
        
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
        logger.info(
            f"[SHOP] [PURCHASE] user_id={user_id} username={ctx.author.name} "
            f"item_key={item_key} quantity={soluong} seed_change=-{total_cost} balance_after={new_balance}"
        )

    @app_commands.command(name="themitem", description="Thêm item cho user (Admin Only)")
    @app_commands.describe(
        user="User nhận item",
        item_key="Key của item (VD: phan_bon, gift, trash_01)",
        count="Số lượng (mặc định 1)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_item_admin_slash(self, interaction: discord.Interaction, user: discord.User, item_key: str, count: int = 1):
        """Admin command to give items to users"""
        # CRITICAL: Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        admin_id = interaction.user.id
        target_user_id = user.id
        
        # Validate count
        if count <= 0:
            await interaction.followup.send(
                "❌ Số lượng phải lớn hơn 0!",
                ephemeral=True
            )
            return

        try:
            # Use add_item from global scope (already imported)
            await add_item(target_user_id, item_key, count)
            
            # Get item display name
            item_display = SHOP_ITEMS.get(item_key, {}).get("name", item_key)
            
            logger.info(f"[ADMIN] [ADD_ITEM] admin_id={admin_id} target_user_id={target_user_id} item_key={item_key} count={count}")
            
            embed = discord.Embed(
                title="✅ Thêm Item Thành Công",
                description=f"Đã thêm **{count}x {item_display}** cho {user.mention}",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"[SHOP] Error adding item {item_key} to {target_user_id}: {e}")
            await interaction.followup.send(
                f"❌ Lỗi khi thêm item: {e}",
                ephemeral=True
            )

    @commands.command(name="themitem", description="Thêm item cho user (Admin Only) - Dùng !themitem @user item_key [count]")
    @commands.has_permissions(administrator=True)
    async def themitem_prefix(self, ctx, user: discord.User, item_key: str, count: int = 1):
        """Prefix command: Admin tool to add items to a user.
        
        Usage: !themitem @user item_key [count]
        """
        
        # Validate count
        if count <= 0:
            await ctx.send("❌ Số lượng phải lớn hơn 0!")
            return
        
        # Add item to user's inventory
        success = await self.add_item_local(user.id, item_key, count)
        if not success:
            await ctx.send("❌ Có lỗi xảy ra khi thêm item!")
            return
        
        embed = discord.Embed(
            title="✅ Thêm Item Thành Công",
            description=f"Đã thêm **{item_key} x{count}** cho {user.mention}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        logger.info(f"[ADMIN] [ADD_ITEM] admin_id={ctx.author.id} target_user_id={user.id} item_key={item_key} count={count}")

    async def _show_shop_menu(self, ctx_or_interaction, is_slash: bool):
        """Displays the shop menu with categorized items."""
        embed = discord.Embed(
            title="🏪 MENU MUA ĐỒ",
            color=discord.Color.gold()
        )
        
        # Categorize items
        regular_gifts = []
        pet_items = []
        fishing_items = []
        buff_items = []
        special_items = []
        commemorative_items = []
        
        for item_key, item_info in SHOP_ITEMS.items():
            line = f"{item_info['emoji']} **{item_info['name']}** - {item_info['cost']} hạt\n    💬 {item_info.get('description', 'N/A')}\n"
            if item_key in ["cafe", "flower", "ring", "gift", "chocolate", "card"]:
                regular_gifts.append(line)
            elif item_key in ["nuoc", "vitamin", "thuc_an_cao_cap"]:
                pet_items.append(line)
            elif item_key == "moi":
                fishing_items.append(line)
            elif item_key in ["nuoc_tang_luc", "gang_tay_xin", "thao_tac_tinh_vi", "tinh_yeu_ca"]:
                buff_items.append(line)
            elif item_key == "may_do_song":
                special_items.append(line)
            elif item_key.startswith("qua_ngot_mua_"):
                commemorative_items.append(line)
        
        if regular_gifts:
            embed.add_field(name="🎁 Quà Tặng Cơ Bản", value="".join(regular_gifts), inline=False)
        
        if pet_items:
            embed.add_field(name="🐱 Đồ Cho Pet", value="".join(pet_items), inline=False)
        
        if fishing_items:
            embed.add_field(name="🎣 Đồ Câu Cá", value="".join(fishing_items), inline=False)
        
        if buff_items:
            embed.add_field(name="💪 Vật Phẩm Buff (Siêu Đắt)", value="".join(buff_items), inline=False)
        
        if special_items:
            embed.add_field(name="📡 Vật Phẩm Đặc Biệt", value="".join(special_items), inline=False)
        
        if commemorative_items:
            embed.add_field(name="🏆 Vật Phẩm Kỉ Niệm", value="".join(commemorative_items), inline=False)
        
        embed.add_field(
            name="📖 CÁCH MUA",
            value="**Slash Command:** `/mua [Tên Item] [Số Lượng]`\n"
                  "**Prefix Command:** `!mua [Tên Item] [Số Lượng]`\n\n"
                  "**Ví dụ:**\n"
                  "• `/mua Cà phê 5`\n"
                  "• `!mua Nước Tăng Lực 1`",
            inline=False
        )
        embed.set_footer(text="Dùng !mua để xem menu này")
        
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

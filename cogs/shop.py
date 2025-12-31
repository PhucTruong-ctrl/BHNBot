import discord
from discord import app_commands
from discord.ext import commands
from database_manager import (
    db_manager,
    get_user_balance,
    add_seeds
)

from .fishing.mechanics.legendary_quest_helper import is_legendary_caught
from .fishing.utils.consumables import CONSUMABLE_ITEMS
from core.item_system import item_system
from configs.item_constants import ItemKeys
from core.logger import setup_logger

logger = setup_logger("ShopCog", "cogs/shop.log")

DB_PATH = "./data/database.db"

class ShopCog(commands.Cog):
    """Cog for managing the shop system, purchases, and currency transactions.

    Handles both slash commands and prefix commands for buying items.
    """
    def __init__(self, bot):
        self.bot = bot

    def _get_item_map(self):
        """Build Vietnamese name to Item Key mapping dynamically."""
        mapping = {}
        all_items = item_system.get_all_items()
        for key, item_data in all_items.items():
            flags = item_data.get("flags", {})
            if flags.get("buyable", False):
                mapping[item_data["name"]] = key
        return mapping, all_items

    # ==================== HELPER FUNCTIONS ====================

    async def get_seeds(self, user_id: int) -> int:
        """Retrieves user's current seed balance (currency)."""
        return await get_user_balance(user_id)

    async def reduce_seeds(self, user_id: int, amount: int, reason: str, category: str):
        """Deducts seeds from user's balance."""
        balance_before = await get_user_balance(user_id)
        await add_seeds(user_id, -amount, reason, category)
        balance_after = balance_before - amount
        logger.info(
            f"[SHOP] [SEED_UPDATE] user_id={user_id} seed_change=-{amount} "
            f"balance_before={balance_before} balance_after={balance_after}"
        )

    async def add_item_local(self, user_id: int, item_id: str, quantity: int = 1):
        """Adds an item to the user's inventory."""
        # [CACHE] Use bot.inventory.modify
        await self.bot.inventory.modify(user_id, item_id, quantity)

    async def remove_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Removes an item from the user's inventory."""
        # [CACHE] Use bot.inventory.modify
        # Note: modify returns new qty, not bool, but boolean return for remove_item is tricky
        # Usually remove_item returned True/False if success.
        # Strict write-through doesn't check 'if user has item' inside modify (it allows negative?), 
        # wait. My modify implementation in inventory_cache allows negatives?
        # NO. "If new_qty <= 0: pop".
        # It handles subtraction fine.
        # But if user didn't have item, qty becomes -quantity? That's bad.
        # LEGACY BEHAVIOR: remove_item returns False if not enough.
        # I should check first.
        
        current = await self.bot.inventory.get(user_id, item_id)
        if current < quantity:
            return False
            
        await self.bot.inventory.modify(user_id, item_id, -quantity)
        return True

    async def get_inventory(self, user_id: int) -> dict:
        """Retrieves user's inventory data."""
        return await self.bot.inventory.get_all(user_id)

    # ==================== COMMANDS ====================

    @app_commands.command(name="mua", description="Mua quà & vật phẩm từ cửa hàng")
    @app_commands.describe(
        item="Tên vật phẩm muốn mua (VD: Cà phê, Giun...)",
        soluong="Số lượng muốn mua (mặc định: 1)"
    )
    async def buy_slash(self, interaction: discord.Interaction, item: str = None, soluong: int = 1):
        """Slash command: Buy items from the shop."""
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
        
        # Get dynamic mapping
        vietnamese_map, all_items = self._get_item_map()
        
        # Try to match Vietnamese name to item key
        item_key = vietnamese_map.get(item)
        if not item_key:
            # Fallback: check if user passed key directly?
            if item in all_items and all_items[item].get("flags", {}).get("buyable"):
                item_key = item
            else:
                available = ", ".join(sorted(vietnamese_map.keys()))
                # Truncate if too long
                if len(available) > 1000: available = available[:1000] + "..."
                
                await interaction.followup.send(
                    f"❌ Item không tồn tại hoặc không bán!\nCác item có sẵn: {available}",
                    ephemeral=True
                )
                return
        
        item_info = all_items[item_key]
        
        # Check if legendary item already obtained
        if item_key == ItemKeys.MAY_DO_SONG:
            user_id = interaction.user.id # Define user_id early
            if await is_legendary_caught(user_id, "ca_voi_52hz"):
                await interaction.followup.send("📡 **TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI**\n\n\"Máy dò sóng chỉ phát ra những tiếng rè tĩnh lặng... Tần số 52Hz cô đơn nhất đại dương không còn lạc lõng nữa, vì nó đã tìm thấy bạn. Không còn tín hiệu nào khác để dò tìm.\"", ephemeral=True)
                return
        
        cost_per_item = item_info.get("price", {}).get("buy", 0)
        
        # Sanity check: cost > 0
        if cost_per_item <= 0:
             await interaction.followup.send("❌ Vật phẩm này không bán!", ephemeral=True)
             return
 
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
        try:
            async with db_manager.transaction() as conn:
                # 1. Re-check balance inside transaction (lock row via UPDATE or specific SELECT FOR UPDATE if robust, 
                # but simple atomic UPDATE is enough for non-banking critical)
                # We will trust the UPDATE check constraint or just do it atomic.
                
                # Check balance first
                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
                current_seeds = row['seeds'] if row else 0
                
                if current_seeds < total_cost:
                    # Balance changed between check and lock?
                     await interaction.followup.send("❌ Bạn không đủ hạt (Giao dịch bị hủy do số dư thay đổi)!", ephemeral=True)
                     return

                # 2. Deduct Money
                # Returning seeds to confirm valid update if needed, but we checked above.
                await conn.execute(
                    "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                    (total_cost, user_id)
                )
                
                # Log transaction
                await conn.execute(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                    (user_id, -total_cost, f'buy_{item_key}', 'shop')
                )
                
                # 3. Add Item
                # Upsert inventory
                await conn.execute(
                    """INSERT INTO inventory (user_id, item_id, quantity) 
                       VALUES ($1, $2, $3)
                       ON CONFLICT(user_id, item_id) 
                       DO UPDATE SET quantity = inventory.quantity + $3""",
                    (user_id, item_key, soluong)
                )

            # UI Feedback (Outside Transaction)
            quantity_text = f" x{soluong}" if soluong > 1 else ""
            embed = discord.Embed(
                title="✅ Mua thành công!",
                description=f"Bạn vừa mua **{item_info['name']}{quantity_text}**",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
            embed.add_field(name="💾 Còn lại", value=f"{seeds - total_cost} hạt", inline=True)
            
            logger.info(f"[SHOP] [BUY] user_id={user_id} item={item_key} quantity={soluong} total_cost={total_cost}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"[SHOP] Purchase failed: {e}")
            await interaction.followup.send("❌ Giao dịch thất bại do lỗi hệ thống!", ephemeral=True)

    @commands.command(name="mua", description="Mua quà & vật phẩm - Dùng !mua [item_key] [số_lượng]")
    async def buy_prefix(self, ctx, item: str = None, *, soluong_or_item: str = None):
        """Prefix command: Buy items from the shop."""
        # If no item specified, show menu
        if item is None:
            await self._show_shop_menu(ctx, is_slash=False)
            return
        
        # Handle parameter parsing
        soluong = 1
        if soluong_or_item is not None:
            try:
                soluong = int(soluong_or_item)
            except ValueError:
                item = f"{item} {soluong_or_item}"
        
        # Validate quantity
        if soluong <= 0:
            await ctx.send(f"❌ Số lượng không hợp lệ!")
            return
        
        # Get dynamic mapping
        vietnamese_map, all_items = self._get_item_map()
        
        # Try to match Vietnamese name to item key
        item_key = vietnamese_map.get(item)
        if not item_key:
             # Fallback check
            if item in all_items and all_items[item].get("flags", {}).get("buyable"):
                item_key = item
            else:
                available = ", ".join(sorted(vietnamese_map.keys()))
                if len(available) > 1000: available = available[:1000] + "..."
                await ctx.send(f"❌ Item không tồn tại!\nCác item có sẵn: {available}")
                return
        
        item_info = all_items[item_key]
        
        # Check if legendary item already obtained
        user_id = ctx.author.id
        if item_key == ItemKeys.MAY_DO_SONG:
            if await is_legendary_caught(user_id, "ca_voi_52hz"):
                await ctx.send("📡 **TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI**\n\n\"Máy dò sóng chỉ phát ra những tiếng rè tĩnh lặng... Tần số 52Hz cô đơn nhất đại dương không còn lạc lõng nữa, vì nó đã tìm thấy bạn. Không còn tín hiệu nào khác để dò tìm.\"")
                return
        
        cost_per_item = item_info.get("price", {}).get("buy", 0)
        
        if cost_per_item <= 0:
             await ctx.send("❌ Vật phẩm này không bán!")
             return

        # Sanity check: quantity > 0
        if soluong <= 0:
            await ctx.send("❌ Số lượng phải lớn hơn 0!")
            return
 
        total_cost = cost_per_item * soluong
        
        # Check balance
        seeds = await self.get_seeds(user_id)
        if seeds < total_cost:
            await ctx.send(f"❌ Bạn không đủ hạt!\nCần: {total_cost} hạt | Hiện có: {seeds} hạt")
            return
        
        # Process purchase
        try:
            async with db_manager.transaction() as conn:
                # 1. Check & Deduct Money
                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
                current_seeds = row['seeds'] if row else 0
                
                if current_seeds < total_cost:
                     await ctx.send(f"❌ Bạn không đủ hạt! (Cần {total_cost}, có {current_seeds})")
                     return

                await conn.execute(
                    "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                    (total_cost, user_id)
                )
                
                await conn.execute(
                    "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                    (user_id, -total_cost, f'buy_{item_key}', 'shop')
                )
                
                # 2. Add Item
                await conn.execute(
                    """INSERT INTO inventory (user_id, item_id, quantity) 
                       VALUES ($1, $2, $3)
                       ON CONFLICT(user_id, item_id) 
                       DO UPDATE SET quantity = inventory.quantity + $3""",
                    (user_id, item_key, soluong)
                )

            quantity_text = f" x{soluong}" if soluong > 1 else ""
            embed = discord.Embed(
                title="✅ Mua thành công!",
                description=f"Bạn vừa mua **{item_info['name']}{quantity_text}**",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
            embed.add_field(name="💾 Còn lại", value=f"{seeds - total_cost} hạt", inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"[SHOP] [BUY] user_id={user_id} item={item_key} quantity={soluong} total_cost={total_cost}")
            
        except Exception as e:
            logger.error(f"[SHOP] Purchase prefix failed: {e}")
            await ctx.send("❌ Giao dịch thất bại do lỗi hệ thống!")

    @app_commands.command(name="themitem", description="Thêm item cho user (Admin Only)")
    @app_commands.describe(
        user="User nhận item",
        item_key="Key của item (VD: phan_bon, gift, trash_01)",
        count="Số lượng (mặc định 1)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_item_admin_slash(self, interaction: discord.Interaction, user: discord.User, item_key: str, count: int = 1):
        """Admin command to give items to users"""
        await interaction.response.defer(ephemeral=True)
        
        admin_id = interaction.user.id
        target_user_id = user.id
        
        if count <= 0:
            await interaction.followup.send(
                "❌ Số lượng phải lớn hơn 0!",
                ephemeral=True
            )
            return

        try:
            # Verify item exists in our DB
            all_items = item_system.get_all_items()
            if item_key not in all_items:
                 pass

            await self.bot.inventory.modify(target_user_id, item_key, count)
            
            # Get item display name
            item_display = all_items.get(item_key, {}).get("name", item_key)
            
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
        """Prefix command: Admin tool to add items to a user."""
        if count <= 0:
            await ctx.send("❌ Số lượng phải lớn hơn 0!")
            return
        
        success = await self.add_item_local(user.id, item_key, count)
        
        if success is False: # Check explicit False
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
        
        # Categorize items dynamically
        categories = {
            "gift": [],
            "fishing": [],
            "buff": [],
            "special": [],
            "commemorative": []
        }
        
        # Iterate all items to find buyable or shop-listed ones
        all_items = item_system.get_all_items()
        for key, item in all_items.items():
            flags = item.get("flags", {})
            buyable = flags.get("buyable", False)
            category = flags.get("shop_category", "misc")
            
            # Special check for commemorative (not buyable but show up)
            if not buyable and category != "commemorative":
                continue
                
            price = item.get("price", {}).get("buy", 0)
            
            line = f"{item['emoji']} **{item['name']}** (`{key}`) - {price if price else 'N/A' } hạt\n    💬 {item.get('description', 'N/A')}\n"
            
            if category in categories:
                categories[category].append(line)
        
        if categories["gift"]:
            embed.add_field(name="🎁 Quà Tặng Cơ Bản", value="".join(categories["gift"]), inline=False)
        
        if categories["fishing"]:
            embed.add_field(name="🎣 Đồ Câu Cá", value="".join(categories["fishing"]), inline=False)
        
        if categories["buff"]:
            embed.add_field(name="💪 Vật Phẩm Buff", value="".join(categories["buff"]), inline=False)
        
        if categories["special"]:
            embed.add_field(name="📡 Vật Phẩm Đặc Biệt", value="".join(categories["special"]), inline=False)
        
        if categories["commemorative"]:
            embed.add_field(name="🏆 Vật Phẩm Kỉ Niệm", value="".join(categories["commemorative"]), inline=False)
        
        embed.add_field(
            name="📖 CÁCH MUA (Khuyên dùng Key)",
            value="**Slash Command:** `/mua [Tên Item hoặc Key] [Số Lượng]`\n"
                  "**Prefix Command:** `!mua [Tên Item hoặc Key] [Số Lượng]`\n\n"
                  "**Ví dụ (Dùng Key cho chính xác):**\n"
                  "• `!mua tinh_yeu_ca` (Mua 1 Tình Yêu Với Cá)\n"
                  "• `!mua cafe 5` (Mua 5 Cà Phê)",
            inline=False
        )
        embed.set_footer(text="Dùng !mua để xem menu này")
        
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

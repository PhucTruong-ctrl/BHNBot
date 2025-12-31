import discord
from discord import app_commands
from discord.ext import commands
import logging

from .core import logic
from core import checks

logger = logging.getLogger("ShopCog")

class ShopCog(commands.Cog):
    """Cog for managing the shop system."""
    
    def __init__(self, bot):
        self.bot = bot

    # ==================== COMMANDS ====================

    @app_commands.command(name="mua", description="Mua quà & vật phẩm từ cửa hàng")
    async def buy_slash(self, interaction: discord.Interaction, item: str = None, soluong: int = 1):
        await interaction.response.defer(ephemeral=True)
        
        if item is None:
            await self._show_shop_menu(interaction, is_slash=True)
            return

        # Map Name -> Key
        vietnamese_map, all_items = logic.get_buyable_items_map()
        item_key = vietnamese_map.get(item)
        if not item_key:
            # Fallback
            if item in all_items and all_items[item].get("flags", {}).get("buyable"):
                item_key = item
            else:
                available = ", ".join(sorted(vietnamese_map.keys()))
                if len(available) > 1000: available = available[:1000] + "..."
                await interaction.followup.send(f"❌ Item không tồn tại! Có sẵn: {available}", ephemeral=True)
                return

        item_info = all_items[item_key]
        price = item_info.get("price", {}).get("buy", 0)
        total_cost = price * soluong
        
        if price <= 0:
            await interaction.followup.send("❌ Item này không bán.", ephemeral=True)
            return

        # Check conditions
        can_buy, msg = await logic.check_buy_conditions(interaction.user.id, item_key, soluong, total_cost)
        if not can_buy:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        # Execute
        success = await logic.execute_purchase(interaction.user.id, item_key, soluong, total_cost)
        if success:
            # Update cache
            await self.bot.inventory.modify(interaction.user.id, item_key, soluong)
            
            # Retrieve remaining balance for UI
            seeds = await logic.get_user_balance_local(interaction.user.id)
            
            embed = discord.Embed(title="✅ Mua thành công!", color=discord.Color.green())
            embed.description = f"Bạn vừa mua **{item_info['name']} x{soluong}**"
            embed.add_field(name="💰 Trừ", value=f"{total_cost} hạt", inline=True)
            embed.add_field(name="💾 Còn lại", value=f"{seeds} hạt", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"User {interaction.user.id} bought {item_key} x{soluong}")
        else:
             await interaction.followup.send("❌ Giao dịch thất bại (Lỗi hệ thống hoặc số dư thay đổi).", ephemeral=True)

    @commands.command(name="mua")
    async def buy_prefix(self, ctx, item: str = None, *, soluong_or_item: str = None):
        if item is None:
            await self._show_shop_menu(ctx, is_slash=False)
            return
            
        soluong = 1
        if soluong_or_item:
            try: soluong = int(soluong_or_item)
            except: item = f"{item} {soluong_or_item}"
            
        # (Reuse logic mostly, but duplicate for separated handling steps - refactor later to shared method if desirable)
         # Map Name -> Key
        vietnamese_map, all_items = logic.get_buyable_items_map()
        item_key = vietnamese_map.get(item)
        if not item_key:
             if item in all_items and all_items[item].get("flags", {}).get("buyable"): item_key = item
             else:
                 await ctx.send("❌ Item không tìm thấy.")
                 return

        item_info = all_items[item_key]
        price = item_info.get("price", {}).get("buy", 0)
        total_cost = price * soluong
        
        can_buy, msg = await logic.check_buy_conditions(ctx.author.id, item_key, soluong, total_cost)
        if not can_buy:
             await ctx.send(f"❌ {msg}")
             return

        success = await logic.execute_purchase(ctx.author.id, item_key, soluong, total_cost)
        if success:
             await self.bot.inventory.modify(ctx.author.id, item_key, soluong)
             embed = discord.Embed(title="✅ Mua thành công!", color=discord.Color.green())
             embed.description = f"Đã mua **{item_info['name']} x{soluong}**"
             await ctx.send(embed=embed)
        else:
             await ctx.send("❌ Giao dịch thất bại.")

    @app_commands.command(name="themitem", description="Admin Only: Add Item")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_item_slash(self, interaction: discord.Interaction, user: discord.User, item_key: str, count: int = 1):
        # Admin logic - directly using access
        await interaction.response.defer(ephemeral=True)
        try:
             await self.bot.inventory.modify(user.id, item_key, count)
             await interaction.followup.send(f"✅ Đã thêm {count}x {item_key} cho {user.mention}", ephemeral=True)
        except Exception as e:
             await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

    @commands.command(name="themitem")
    @checks.is_admin()
    async def add_item_prefix(self, ctx, user: discord.User, item_key: str, count: int = 1):
         try:
             await self.bot.inventory.modify(user.id, item_key, count)
             await ctx.send(f"✅ Đã thêm {count}x {item_key} cho {user.mention}")
         except Exception as e:
             await ctx.send(f"❌ Lỗi: {e}")

    async def _show_shop_menu(self, ctx_or_int, is_slash):
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
        # Use logic helper to get all items
        _, all_items = logic.get_buyable_items_map()

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
            await ctx_or_int.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_int.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))

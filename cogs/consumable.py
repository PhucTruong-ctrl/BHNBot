"""Consumable items usage system."""

from discord import app_commands
from discord.ext import commands
import discord
import random
from database_manager import get_inventory, remove_item, add_item
from .fishing.consumables import CONSUMABLE_ITEMS, get_consumable_info, is_consumable

class ConsumableCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Lưu các item đang được sử dụng để boost lần câu tiếp theo
        self.active_boosts = {}  # {user_id: {"item_key": str, "effect_type": str, "effect_value": float}}
        # Lưu các user đã phát hiện tín hiệu 52Hz
        self.detected_52hz = {}  # {user_id: True} - trigger 100% whale encounter

    # ==================== COMMANDS ====================

    @app_commands.command(name="sudung", description="Sử dụng vật phẩm tiêu thụ để có buff khi câu cá")
    @app_commands.describe(item="Item key: nuoc_tang_luc, gang_tay_xin, thao_tac_tinh_vi, hoặc tinh_yeu_ca (để trống xem danh sách)")
    async def use_consumable_slash(self, interaction: discord.Interaction, item: str = None):
        """Use a consumable item - slash version"""
        await interaction.response.defer(ephemeral=True)
        await self._use_consumable(interaction, item, is_slash=True)

    @commands.command(name="sudung", description="Sử dụng vật phẩm tiêu thụ - Dùng !sudung [item_key]")
    async def use_consumable_prefix(self, ctx, item: str = None):
        """Use a consumable item - prefix version"""
        await self._use_consumable(ctx, item, is_slash=False)

    async def _use_consumable(self, ctx_or_interaction, item_key: str, is_slash: bool):
        """Core logic to use a consumable item"""
        
        # Show help if no item provided
        if item_key is None:
            embed = discord.Embed(
                title="📖 Cách Sử Dụng Vật Phẩm Tiêu Thụ",
                description="Dùng `/sudung [item_key]` để sử dụng vật phẩm",
                color=discord.Color.blurple()
            )
            
            for key, item_info in CONSUMABLE_ITEMS.items():
                value = f"**{item_info['name']}**\n{item_info['description']}\n\n**Lệnh:** `/sudung {key}` hoặc `!sudung {key}`"
                embed.add_field(name=f"🎫 {key}", value=value, inline=False)
            
            embed.set_footer(text="Mua tại cửa hàng với /mua (nếu cần)")
            
            if is_slash:
                await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Validate item exists
        if not is_consumable(item_key):
            available = ", ".join([f"`{k}`" for k in CONSUMABLE_ITEMS.keys()])
            error_msg = f"❌ Không tìm thấy vật phẩm `{item_key}`!\n\n**Vật phẩm có sẵn:**\n{available}"
            
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
            return
        
        user_id = ctx_or_interaction.user.id if is_slash else ctx_or_interaction.author.id
        item_info = get_consumable_info(item_key)
        
        # Check inventory
        inventory = await get_inventory(user_id)
        quantity = inventory.get(item_key, 0)
        
        if quantity < 1:
            error_msg = f"❌ Bạn không có **{item_info['name']}**!"
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
            return
        
        # Use the item - remove from inventory
        success = await remove_item(user_id, item_key, 1)
        if not success:
            error_msg = "❌ Lỗi khi sử dụng vật phẩm!"
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
            return
        
        # Store active boost for this user
        self.active_boosts[user_id] = {
            "item_key": item_key,
            "effect_type": item_info["effect_type"],
            "effect_value": item_info["effect_value"],
        }
        
        # Send success message
        embed = discord.Embed(
            title=f"✅ Đã Sử Dụng {item_info['name']}",
            description=item_info["mechanism"],
            color=discord.Color.green()
        )
        embed.add_field(name="📖 Mô tả", value=item_info["description"], inline=False)
        embed.add_field(name="📦 Còn lại", value=f"x{quantity - 1}", inline=False)
        embed.add_field(
            name="⏱️ Thời gian hiệu lực",
            value="Có hiệu lực cho lần câu cá huyền thoại tiếp theo",
            inline=False
        )
        
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)



    # ==================== ADMIN COMMANDS ====================

    @commands.command(name="themconsumable", description="Thêm consumable item vào inventory (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_consumable_prefix(self, ctx, item_key: str, quantity: int = 1, user: discord.User = None):
        """Add consumable item to user's inventory"""
        target_user = user or ctx.author
        
        if not is_consumable(item_key):
            available = ", ".join([f"`{k}`" for k in CONSUMABLE_ITEMS.keys()])
            await ctx.send(f"❌ Không tìm thấy item `{item_key}`!\n\n**Items có sẵn:**\n{available}")
            return
        
        item_info = get_consumable_info(item_key)
        await add_item(target_user.id, item_key, quantity)
        
        embed = discord.Embed(
            title="✅ Đã Thêm Consumable Item",
            description=f"User: {target_user.mention}\nItem: {item_info['name']} x{quantity}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    def get_active_boost(self, user_id: int) -> dict | None:
        """Get active boost for user (và xóa sau khi dùng)"""
        return self.active_boosts.pop(user_id, None)

    def has_detected_52hz(self, user_id: int) -> bool:
        """Check if user has detected 52Hz signal"""
        return self.detected_52hz.get(user_id, False)

    def clear_52hz_signal(self, user_id: int):
        """Clear the 52Hz detection flag after spawning whale"""
        self.detected_52hz.pop(user_id, None)

async def setup(bot):
    await bot.add_cog(ConsumableCog(bot))

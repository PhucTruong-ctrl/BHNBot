"""UI views for fishing system."""

import discord
import random
from database_manager import remove_item, add_seeds, get_inventory
from .constants import ALL_FISH, DB_PATH, LEGENDARY_FISH_KEYS
from .mechanics.glitch import apply_display_glitch
from core.logger import setup_logger

logger = setup_logger("FishingViews", "cogs/fishing/fishing.log")

class FishSellView(discord.ui.View):
    """Display-only view for fishing results (sell buttons removed)."""
    
    def __init__(self, cog, user_id, caught_items, guild_id):
        """Initialize FishSellView (Display-only, buttons removed).
        
        NOTE: Sell buttons removed in UX cleanup.
        Users should use /banca command for selling.
        Interactive events (Black Market, Haggle) moved to /banca.
        """
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
        self.sold = False
    
    async def on_timeout(self):
        """Cleans up view when it times out."""
        if self.user_id in self.cog.caught_items:
            try:
                del self.cog.caught_items[self.user_id]
            except Exception as e:
                logger.error(f"Unexpected error: {e}")


class HagglingView(discord.ui.View):
    """A view for the Haggling minigame.

    Allows the user to negotiate the sell price with a risk/reward mechanic.
    """
    def __init__(self, cog, user_id, caught_items, base_total, username):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.base_total = base_total
        self.username = username
        self.completed = False
    
    @discord.ui.button(label="🤝 Chốt Luôn", style=discord.ButtonStyle.green)
    async def accept_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accepts the current offer without further negotiation.

        Safely processes the transaction at the `base_total` price.
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            return
        
        if self.completed:
            return
        
        self.completed = True
        
        try:
            from database_manager import db_manager
            
            # Prepare batch operations
            operations = []
            
            # Remove fish items
            for fish_key, quantity in self.caught_items.items():
                operations.append((
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (quantity, self.user_id, fish_key)
                ))
            
            operations.append((
                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                (self.user_id,)
            ))
            
            # Add seeds
            operations.append((
                "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                (self.base_total, self.user_id)
            ))
            
            # Execute transaction
            await db_manager.batch_modify(operations)
            
            # Clear caches
            db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
            db_manager.clear_cache_by_prefix(f"balance_{self.user_id}")
            db_manager.clear_cache_by_prefix("leaderboard")
            
            embed = discord.Embed(
                title="🤝 **CHỐT XONG!**",
                description=f"💰 Nhận: **{self.base_total} Hạt**\n\n✅ An toàn là trên hết!",
                color=discord.Color.green()
            )
            
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"[HAGGLE_ACCEPT] {self.username} (user_id={self.user_id}) earned {self.base_total} seeds")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)
    
    @discord.ui.button(label="😏 Đòi Thêm", style=discord.ButtonStyle.primary)
    async def demand_more(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Attempts to negotiate a higher price.

        Mechanic:
        - 40% chance of success: Price increases by 30%.
        - 60% chance of failure: Price decreases by 20% (Merchant annoyed).
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            return
        
        if self.completed:
            return
        
        self.completed = True
        success = random.random() < 0.4
        
        if success:
            # Success: +30%
            final_total = int(self.base_total * 1.3)
            message = f"💰 Nhận: **{final_total} Hạt** (+30%)\n\n😎 Thương lái khúc xương! Bạn làm ăn quá khéo!"
            color = discord.Color.gold()
            action = "SUCCESS"
        else:
            # Failure: -20%
            final_total = int(self.base_total * 0.8)
            message = f"💸 Chỉ nhận: **{final_total} Hạt** (-20%)\n\n😤 Thương lái dỗi bỏ đi rồi bán cho người khác với giá rẻ hơn!"
            color = discord.Color.red()
            action = "FAIL"
        
        try:
            from database_manager import db_manager
            
            # Prepare batch operations
            operations = []
            
            # Remove fish items
            for fish_key, quantity in self.caught_items.items():
                operations.append((
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (quantity, self.user_id, fish_key)
                ))
            
            operations.append((
                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                (self.user_id,)
            ))
            
            # Add seeds
            operations.append((
                "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                (final_total, self.user_id)
            ))
            
            # Execute transaction
            await db_manager.batch_modify(operations)
            
            # Clear caches
            db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
            db_manager.clear_cache_by_prefix(f"balance_{self.user_id}")
            db_manager.clear_cache_by_prefix("leaderboard")
            
            embed = discord.Embed(
                title=f"😏 **MẶC CÀ {action}!**",
                description=message,
                color=color
            )
            
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"[HAGGLE_{action}] {self.username} (user_id={self.user_id}) earned {final_total} seeds")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

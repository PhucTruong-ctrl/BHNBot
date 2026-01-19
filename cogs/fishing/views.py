"""UI views for fishing system."""

import discord
import random
from database_manager import add_seeds
from .constants import ALL_FISH, DB_PATH, LEGENDARY_FISH_KEYS
from .mechanics.glitch import apply_display_glitch
from core.logging import setup_logger

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
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(
                    content="⏰ **Hết thời gian!** Phiên hiển thị đã kết thúc.",
                    view=None
                )
        except:
            pass
        
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
            # [CACHE] Use new inventory system
            for fish_key, quantity in self.caught_items.items():
                await self.cog.bot.inventory.modify(self.user_id, fish_key, -quantity)
            
            # Add seeds
            await add_seeds(self.user_id, self.base_total, reason='haggle_accept', category='fishing')
            
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
            # [CACHE] Use new inventory system
            for fish_key, quantity in self.caught_items.items():
                await self.cog.bot.inventory.modify(self.user_id, fish_key, -quantity)
            
            # Add seeds
            await add_seeds(self.user_id, final_total, reason='haggle_result', category='fishing')
            
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

class TournamentLobbyView(discord.ui.View):
    """View for Tournament Lobby (Join/Leave/Start)."""
    def __init__(self, tournament_id: int, host_id: int):
        super().__init__(timeout=900) # 15 mins matching registration time
        self.tournament_id = tournament_id
        self.host_id = host_id
        
    async def update_embed(self, interaction: discord.Interaction):
        """Updates the embed with current participant count."""
        from .tournament import TournamentManager
        from core.database import db_manager # Import here to avoid issues
        
        # Get count
        count_data = await db_manager.fetchrow(
            "SELECT COUNT(*) as c FROM tournament_entries WHERE tournament_id = ?",
            (self.tournament_id,)
        )
        count = count_data['c']
        
        # Get Embed from message
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            # Update footer or field?
            # Existing Embed: "Status: Registering..."
            # Let's append count to description or update it.
            # Simple approach: Update footer or a field.
            embed.set_footer(text=f"ID: {self.tournament_id} | Người tham gia: {count}")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Tham Gia", style=discord.ButtonStyle.green, emoji="🎟️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .tournament import TournamentManager
        manager = TournamentManager.get_instance()
        success, msg = await manager.join_tournament(self.tournament_id, interaction.user.id)
        
        if success:
            await self.update_embed(interaction)
            await interaction.followup.send(f"✅ {interaction.user.mention} đã tham gia!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

    @discord.ui.button(label="Rời Giải", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Implement leave? Plan didn't explicitly ask for Leave, but it's good UX.
        # However, logic for refunding fee is needed.
        # Since 'join' deducts fee immediately.
        # Let's skip 'Leave' for now to avoid 'exploit' (join/leave spam).
        # Or simple: "Cannot leave once joined".
        await interaction.response.send_message("❌ Đã tham gia thì không thể rút lui (Hạt đã đóng vào Quỹ)!", ephemeral=True)

    @discord.ui.button(label="Bắt Đầu", style=discord.ButtonStyle.blurple, emoji="⚔️")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Host only start."""
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("❌ Chỉ Host mới được quyền bắt đầu!", ephemeral=True)
            return
            
        from .tournament import TournamentManager
        manager = TournamentManager.get_instance()
        success = await manager.start_tournament(self.tournament_id)
        
        if success:
             embed = discord.Embed(
                 title="⚔️ GIẢI ĐẤU ĐÃ BẮT ĐẦU!",
                 description="Các cần thủ hãy nhanh chóng câu cá!\nThời gian: **10 phút**.\nTính điểm: **Tổng giá trị cá bán được**.",
                 color=discord.Color.red()
             )
             await interaction.response.edit_message(embed=embed, view=None)
        else:
             await interaction.response.send_message("❌ Cần ít nhất 2 người chơi!", ephemeral=True)

    @discord.ui.button(label="Cập Nhật", style=discord.ButtonStyle.gray, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction)

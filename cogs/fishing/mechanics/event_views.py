"""Event-related views for fishing system.

Contains views for meteor shower wishes and NPC encounters.
"""
import logging
import random
import asyncio
from datetime import datetime
import discord

from database_manager import add_seeds, get_stat, increment_stat
from .legendary_quest_helper import increment_manh_sao_bang

logger = logging.getLogger("fishing")


class MeteorWishView(discord.ui.View):
    """View for wishing on shooting stars during meteor shower events."""
    
    def __init__(self, cog):
        super().__init__(timeout=30)
        self.cog = cog
        self.wished_users = set()
    
    @discord.ui.button(label="🙏 Ước Nguyện", style=discord.ButtonStyle.primary, emoji="💫")
    async def wish_on_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle wish button click."""
        user_id = interaction.user.id
        
        # No Daily Limit (User Request)
        # today_str = datetime.now().strftime('%Y-%m-%d')
        # stat_key = f'meteor_shards_today_{today_str}'
        stat_key = "total_wishes" # Just track total wishes instead

        
        # Prevent double-click
        if user_id in self.wished_users:
            await interaction.response.send_message("Bạn đã ước rồi!", ephemeral=True)
            return
        
        self.wished_users.add(user_id)
        
        # 10% chance for manh_sao_bang (User Request)
        if random.random() < 0.2:
            await increment_manh_sao_bang(user_id, 1)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            
            message = (
                f"🌠 **{interaction.user.name}** chắp tay nguyện cầu khi sao băng vụt qua...\n"
                f"✨ Điều kỳ diệu đã đến! Một mảnh vỡ rực sáng rơi xuống tay bạn! Bạn nhận được **Mảnh Sao Băng**! 🌠✨"
            )
            logger.info(f"[METEOR] User {interaction.user.name} ({user_id}) got SHARD")
        else:
            seeds = random.randint(10, 50)
            await add_seeds(user_id, seeds)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            
            message = (
                f"🌠 **{interaction.user.name}** đã gửi một lời ước đến các vì sao...\n"
                f"🌱 Sao băng đã nghe thấy! Bạn nhận được **{seeds} hạt**! ✨"
            )
            logger.info(f"[METEOR] User {interaction.user.name} ({user_id}) got {seeds} SEEDS")
        
        await interaction.response.send_message(message, ephemeral=False)
        
        # Disable button after 15s
        await asyncio.sleep(15)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            logger.error(f"Error editing meteor view: {e}")


class NPCEncounterView(discord.ui.View):
    """View for NPC encounter interactions during fishing."""
    
    def __init__(self, user_id: int, npc_type: str, npc_data: dict, fish_key: str = None):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.npc_type = npc_type
        self.npc_data = npc_data
        self.fish_key = fish_key
        self.value = None
    
    async def on_timeout(self):
        """View times out if no action taken within 30s - auto decline."""
        self.value = "decline"
        self.stop()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the fisher can interact."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải chuyện của bạn!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="✅ Đồng Ý", style=discord.ButtonStyle.success)
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept NPC offer."""
        self.value = "agree"
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="❌ Từ Chối", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline NPC offer."""
        self.value = "decline"
        await interaction.response.defer()
        self.stop()

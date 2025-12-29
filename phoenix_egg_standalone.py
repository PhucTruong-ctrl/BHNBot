"""
Phoenix Egg Mini-game - Standalone Test Version
Usage: Replace KeepFireView in consumable.py with this code
"""

import discord
import random
from core.logger import setup_logger

logger = setup_logger("Consumable", "cogs/consumable.log")


class PhoenixEggView(discord.ui.View):
    """Ấp Trứng Phượng Hoàng (Push Your Luck)"""
    
    def __init__(self, user_id, bot, channel, user):
        super().__init__(timeout=180)  # 3 minutes
        self.user_id = user_id
        self.bot = bot
        self.channel = channel
        self.user = user
        self.energy = 0
        
        # Buttons
        light = discord.ui.Button(label="🔥 Nạp Nhẹ (5-15%)", style=discord.ButtonStyle.primary)
        light.callback = self.add_light
        self.add_item(light)
        
        heavy = discord.ui.Button(label="💥 Nạp Mạnh (15-30%)", style=discord.ButtonStyle.danger)
        heavy.callback = self.add_heavy
        self.add_item(heavy)
        
        activate = discord.ui.Button(label="✨ Kích Hoạt", style=discord.ButtonStyle.success)
        activate.callback = self.activate
        self.add_item(activate)
    
    def _make_embed(self, last_action=""):
        # Progress bar
        filled = self.energy // 10
        empty = 10 - filled
        if self.energy < 50:
            bar = "🟦" * filled + "⬜" * empty
        elif self.energy < 80:
            bar = "🟨" * filled + "⬜" * empty
        else:
            bar = "🟥" * filled + "⬜" * empty
        
        # Status
        if self.energy < 50:
            status = "✅ An toàn"
            color = discord.Color.blue()
        elif self.energy < 80:
            status = "⚠️ Cẩn thận"
            color = discord.Color.gold()
        elif self.energy < 95:
            status = "🎯 VÙ MỤC TIÊU"
            color = discord.Color.orange()
        else:
            status = "🔥 NGUY HIỂM!"
            color = discord.Color.red()
        
        desc = f"[{bar}] **{self.energy}%**\n\n{status}"
        if last_action:
            desc += f"\n\n💫 {last_action}"
        
        embed = discord.Embed(
            title=f"🥚 {self.user.display_name} - ẤP TRỨNG PHƯỢNG HOÀNG",
            description=desc,
            color=color
        )
        embed.add_field(
            name="📖 Hướng Dẫn",
            value="🔥 Nạp Nhẹ: +5-15% an toàn\n"
                  "💥 Nạp Mạnh: +15-30% mạo hiểm\n"
                  "✨ Kích Hoạt: Nở trứng (80-100%)\n"
                  "• Bust >100% ❌ | Perfect 100% 👑",
            inline=False
        )
        return embed
    
    async def add_light(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        
        gain = random.randint(5, 15)
        self.energy += gain
        
        if self.energy > 100:
            self.stop()
            return await self._bust(interaction)
        
        embed = self._make_embed(f"Nạp nhẹ: +{gain}%")
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def add_heavy(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        
        gain = random.randint(15, 30)
        self.energy += gain
        
        if self.energy > 100:
            self.stop()
            return await self._bust(interaction)
        
        embed = self._make_embed(f"Nạp mạnh: +{gain}%")
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def activate(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        
        self.stop()
        
        if self.energy < 80:
            await self._fail_low(interaction)
        elif self.energy == 100:
            await self._perfect(interaction)
        else:
            await self._success(interaction)
    
    async def on_timeout(self):
        from database_manager import remove_item
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_last_play
        
        try:
            await remove_item(self.user_id, "long_vu_lua", 1)
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title=f"⏰ HẾT THỜI GIAN",
                description=f"Trứng đã nguội lạnh.\n**Năng lượng: {self.energy}%**",
                color=discord.Color.red()
            )
            await self.channel.send(embed=embed)
        except Exception as e:
            logger.error(f"[PHOENIX] Timeout error: {e}")
    
    async def _bust(self, interaction):
        from database_manager import remove_item
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_last_play
        
        try:
            await remove_item(self.user_id, "long_vu_lua", 1)
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="💥 NỔ TUNG!",
                description=f"**{self.energy}%** - Quá tải!\n\nTrứng không chịu nổi áp lực.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} busted at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Bust error: {e}")
    
    async def _fail_low(self, interaction):
        from database_manager import remove_item
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_last_play
        
        try:
            await remove_item(self.user_id, "long_vu_lua", 1)
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="❌ QUÁ YẾU",
                description=f"**{self.energy}%** - Cần tối thiểu 80%!\n\nTrứng vỡ.",
                color=discord.Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} too low at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Fail low error: {e}")
    
    async def _success(self, interaction):
        from database_manager import remove_item
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_buff, set_phoenix_last_play
        
        try:
            await remove_item(self.user_id, "long_vu_lua", 1)
            await set_phoenix_buff(self.user_id, True)
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="🎉 TRỨNG NỞ THÀNH CÔNG!",
                description=f"**{self.energy}%** - Hoàn hảo!\n\n🔥 **Cá Phượng Hoàng** sẽ xuất hiện lần câu tiếp theo!",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} success at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Success error: {e}")
    
    async def _perfect(self, interaction):
        from database_manager import remove_item
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_buff, set_phoenix_last_play
        
        try:
            await remove_item(self.user_id, "long_vu_lua", 1)
            await set_phoenix_buff(self.user_id, True)
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="👑 PERFECT! PHƯỢNG HOÀNG CHÚA!",
                description="**100%** - HOÀN HẢO TUYỆT ĐỐI!\n\n"
                            "💎 Ánh sáng chói lọi!\n"
                            "✨ Guaranteed Legendary + Bonus!",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} PERFECT 100%!")
        except Exception as e:
            logger.error(f"[PHOENIX] Perfect error: {e}")


# Usage in consumable.py (line ~368-397):
# Replace:
#   view = KeepFireView(user_id, self.bot, ctx_or_interaction.channel, user)
# With:
#   view = PhoenixEggView(user_id, self.bot, ctx_or_interaction.channel, user)

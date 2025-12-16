"""Legendary fish system."""

import discord
import random
import aiosqlite
import json
from datetime import datetime
from .constants import DB_PATH, LEGENDARY_FISH, LEGENDARY_FISH_KEYS, ALL_FISH, ROD_LEVELS

class LegendaryBossFightView(discord.ui.View):
    """Interactive boss fight for legendary fish."""
    def __init__(self, cog, user_id, legendary_fish: dict, rod_durability: int, rod_level: int, channel=None, guild_id=None):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.legendary_fish = legendary_fish
        self.rod_durability = rod_durability
        self.rod_level = rod_level
        self.channel = channel
        self.guild_id = guild_id
        self.fought = False
    
    @discord.ui.button(label="🔴 Giật Mạnh", style=discord.ButtonStyle.danger)
    async def jerk_hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        success = random.random() < 0.30
        
        if success:
            result_embed = discord.Embed(
                title="✨ THÀNH CÔNG! ✨",
                description=f"🎉 Bạn đã **bắt được {self.legendary_fish['emoji']} {self.legendary_fish['name']}**!\n\n💪 Một cú giật mạnh hoàn hảo!",
                color=discord.Color.gold()
            )
            result_embed.set_image(url=self.legendary_fish.get('image_url', ''))
            await self.cog.add_legendary_fish_to_user(self.user_id, self.legendary_fish['key'])
        else:
            result_embed = discord.Embed(
                title="💔 THẤT BẠI! 💔",
                description=f"❌ Quá mạnh! Cần câu của bạn đã **GÃY TOÁC**!",
                color=discord.Color.red()
            )
            await self.cog.update_rod_data(self.user_id, 0)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    @discord.ui.button(label="🟡 Dìu Cá (Kỹ Thuật)", style=discord.ButtonStyle.primary)
    async def guide_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        
        if self.rod_level < 5:
            fail_embed = discord.Embed(
                title="❌ KHÔNG ĐỦ LEVEL!",
                description=f"🎣 Cần câu hiện tại chỉ cấp {self.rod_level}/5",
                color=discord.Color.orange()
            )
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=fail_embed, view=self)
            return
        
        success = random.random() < 0.60
        
        if success:
            result_embed = discord.Embed(
                title="✨ THÀNH CÔNG! ✨",
                description=f"🎉 Bạn đã **bắt được {self.legendary_fish['emoji']} {self.legendary_fish['name']}**!",
                color=discord.Color.gold()
            )
            result_embed.set_image(url=self.legendary_fish.get('image_url', ''))
            await self.cog.add_legendary_fish_to_user(self.user_id, self.legendary_fish['key'])
        else:
            new_durability = max(0, self.rod_durability - 30)
            result_embed = discord.Embed(
                title="💔 THẤT BẠI! 💔",
                description=f"❌ Quá mạnh! Bạn mất 30 độ bền!",
                color=discord.Color.red()
            )
            await self.cog.update_rod_data(self.user_id, new_durability)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    @discord.ui.button(label="🔵 Cắt Dây (Bỏ Cuộc)", style=discord.ButtonStyle.secondary)
    async def cut_line(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        result_embed = discord.Embed(
            title="🏃 ĐÃ BỎ CUỘC 🏃",
            description=f"✂️ Bạn cắt dây cá.\n\n{self.legendary_fish['emoji']} **{self.legendary_fish['name']}** thoát khỏi!",
            color=discord.Color.greyple()
        )
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)

async def check_legendary_spawn_conditions(user_id: int, guild_id: int, current_hour: int) -> dict | None:
    """Check if legendary fish should spawn."""
    import json
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT legendary_fish FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                legendary_list = json.loads(row[0] or "[]") if row else []
    except:
        legendary_list = []
    
    if len(legendary_list) > 0:
        return None
    
    for legendary in LEGENDARY_FISH:
        time_restriction = legendary.get("time_restriction")
        if time_restriction is not None:
            start_hour, end_hour = time_restriction
            if not (start_hour <= current_hour < end_hour):
                continue
        
        if random.random() < legendary["spawn_chance"]:
            return legendary
    
    return None

async def add_legendary_fish_to_user(user_id: int, legendary_key: str):
    """Add legendary fish to user's collection."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT legendary_fish, legendary_fish_count FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                legendary_list = json.loads(row[0] or "[]") if row else []
                count = row[1] or 0 if row else 0
            
            legendary_list.append(legendary_key)
            count += 1
            
            await db.execute(
                "UPDATE economy_users SET legendary_fish = ?, legendary_fish_count = ? WHERE user_id = ?",
                (json.dumps(legendary_list), count, user_id)
            )
            await db.commit()
    except Exception as e:
        pass

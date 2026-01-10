"""Legendary fish views."""

import discord
import random
import logging

from database_manager import get_fish_collection, increment_stat, get_stat
from ..constants import LEGENDARY_FISH, LEGENDARY_FISH_KEYS, ALL_FISH, ROD_LEVELS
from ..mechanics.glitch import apply_display_glitch

logger = logging.getLogger("fishing")


class LegendaryBossFightView(discord.ui.View):
    
    def __init__(self, cog, user_id, legendary_fish: dict, rod_durability: int, rod_level: int, channel=None, guild_id=None, user=None):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.legendary_fish = legendary_fish
        self.rod_durability = rod_durability
        self.rod_level = rod_level
        self.channel = channel
        self.guild_id = guild_id
        self.user = user
        self.fought = False
        self.failed = False
        
        jerk_btn = discord.ui.Button(label="🔴 GIẬT MẠNH (10%)", style=discord.ButtonStyle.danger)
        jerk_btn.callback = self.jerk_hard
        self.add_item(jerk_btn)
        
        if self.rod_level >= 5:
            chance = 0.65
            consumable_cog = self.cog.bot.get_cog("ConsumableCog")
            if consumable_cog:
                active_boost = consumable_cog.peek_active_boost(self.user_id)
                if active_boost and active_boost.get("effect_type") == "legendary_fish_boost":
                    chance = active_boost.get("effect_value", 0.65)
            
            guide_btn = discord.ui.Button(label=f"🌊 DÌU CÁ ({int(chance*100)}%)", style=discord.ButtonStyle.primary)
            guide_btn.callback = self.guide_fish
            self.add_item(guide_btn)
        
        cut_btn = discord.ui.Button(label="✂️ CẮT DÂY (An Toàn)", style=discord.ButtonStyle.secondary)
        cut_btn.callback = self.cut_line
        self.add_item(cut_btn)
    
    async def jerk_hard(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        success = random.random() < 0.10
        
        if success:
            username = self.user.display_name if self.user else "Unknown"
            result_embed = discord.Embed(
                title=f"✨ {username} - THÀNH CÔNG! ✨",
                description=f"🎉 Bạn đã **bắt được {self.legendary_fish['emoji']} {apply_display_glitch(self.legendary_fish['name'])}**!\n\n💪 Một cú giật mạnh tuyệt diệu!",
                color=discord.Color.gold()
            )
            result_embed.set_image(url=self.legendary_fish.get('image_url', ''))
            await self.cog.add_legendary_fish_to_user(self.user_id, self.legendary_fish['key'])
            
            from ..helpers import track_caught_fish
            await track_caught_fish(self.user_id, self.legendary_fish['key'])
            
            await self._track_legendary_achievement(self.legendary_fish['key'])
        else:
            self.failed = True
            username = self.user.display_name if self.user else "Unknown"
            result_embed = discord.Embed(
                title=f"💥 {username} - CẦN ĐÃ GÃY! 💥",
                description=f"❌ Quá mạnh! Cần câu của bạn không chịu được lực và **GÃY TOÁC**!\n\n⚠️ Bạn sẽ cần sửa chữa.",
                color=discord.Color.red()
            )
            await self.cog.update_rod_data(self.user_id, 0)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    async def guide_fish(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        
        if self.rod_level < 5:
            username = self.user.display_name if self.user else "Unknown"
            fail_embed = discord.Embed(
                title=f"🔒 {username} - KHÔNG ĐỦ ĐIỀU KIỆN",
                description=f"🎣 Kỹ thuật \"Dìu Cá\" chỉ dành riêng cho **Cần Poseidon (Cấp 5)**!\n\nCần hiện tại: Cấp {self.rod_level}/5",
                color=discord.Color.orange()
            )
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=fail_embed, view=self)
            return
        
        base_chance = 0.65
        boost_message = ""
        
        consumable_cog = interaction.client.get_cog("ConsumableCog")
        if consumable_cog:
            active_boost = consumable_cog.get_active_boost(self.user_id)
            if active_boost and active_boost.get("effect_type") == "legendary_fish_boost":
                base_chance = active_boost.get("effect_value", 0.65)
                boost_item_key = active_boost.get("item_key", "")
                from ..utils.consumables import get_consumable_info
                boost_info = get_consumable_info(boost_item_key)
                if boost_info:
                    boost_message = f"\n✨ **BUFF KÍCH HOẠT:** {boost_info['name']}\n🎯 Tỉ lệ thắng: 65% → {int(base_chance*100)}%"
        
        success = random.random() < base_chance
        
        if success:
            username = self.user.display_name if self.user else "Unknown"
            result_embed = discord.Embed(
                title=f"✨ {username} - THÀNH CÔNG! ✨",
                description=f"🎉 Bạn đã **bắt được {self.legendary_fish['emoji']} {apply_display_glitch(self.legendary_fish['name'])}**!\n\n🌊 Một động tác dìu cá hoàn hảo!{boost_message}",
                color=discord.Color.gold()
            )
            result_embed.set_image(url=self.legendary_fish.get('image_url', ''))
            await self.cog.add_legendary_fish_to_user(self.user_id, self.legendary_fish['key'])
            
            from ..helpers import track_caught_fish
            await track_caught_fish(self.user_id, self.legendary_fish['key'])
            
            await self._track_legendary_achievement(self.legendary_fish['key'])
        else:
            self.failed = True
            username = self.user.display_name if self.user else "Unknown"
            result_embed = discord.Embed(
                title=f"💔 {username} - THẤT BẠI! 💔",
                description=f"❌ Kỹ thuật chưa đủ hoàn hảo... {self.legendary_fish['emoji']} **{self.legendary_fish['name']}** đã thoát!{boost_message}\n\n🎣 Độ bền cần: **-40**",
                color=discord.Color.red()
            )
            new_dur = max(0, self.rod_durability - 40)
            await self.cog.update_rod_data(self.user_id, new_dur)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    async def cut_line(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        username = self.user.display_name if self.user else "Unknown"
        result_embed = discord.Embed(
            title=f"✂️ {username} - CẮT DÂY!",
            description=f"Bạn đã cắt dây câu để thoát thân.\n\n{self.legendary_fish['emoji']} **{self.legendary_fish['name']}** đã bơi đi...\n\n✅ Cần câu an toàn!",
            color=discord.Color.light_grey()
        )
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)

    async def _track_legendary_achievement(self, legendary_key: str):
        legendary_stat_map = {
            "thuong_luong": "thuong_luong_caught",
            "ca_ngan_ha": "ca_ngan_ha_caught",
            "ca_phuong_hoang": "ca_phuong_hoang_caught",
            "cthulhu_con": "cthulhu_con_caught",
            "ca_voi_52hz": "ca_voi_52hz_caught"
        }
        
        if legendary_key in legendary_stat_map:
            stat_key = legendary_stat_map[legendary_key]
            try:
                await increment_stat(self.user_id, "fishing", stat_key, 1)
                current_value = await get_stat(self.user_id, "fishing", stat_key)
                await self.cog.bot.achievement_manager.check_unlock(self.user_id, "fishing", stat_key, current_value, self.channel)
                
                await increment_stat(self.user_id, "fishing", "boss_caught", 1)
                current_boss = await get_stat(self.user_id, "fishing", "boss_caught")
                await self.cog.bot.achievement_manager.check_unlock(self.user_id, "fishing", "boss_caught", current_boss, self.channel)
            except Exception as e:
                logger.error(f"[ACHIEVEMENT] Error tracking {stat_key}: {e}")
        
        await increment_stat(self.user_id, "fishing", "legendary_caught", 1)
        current_legendary = await get_stat(self.user_id, "fishing", "legendary_caught")
        await self.cog.bot.achievement_manager.check_unlock(self.user_id, "fishing", "legendary_caught", current_legendary, self.channel)
        
        from ..mechanics.legendary_quest_helper import get_legendary_caught_list
        legendary_list = await get_legendary_caught_list(self.user_id)
        caught_legendary = [fish for fish in legendary_list if fish in LEGENDARY_FISH_KEYS]
        if len(caught_legendary) >= len(LEGENDARY_FISH_KEYS):
            current_all = await get_stat(self.user_id, "fishing", "all_legendary_caught")
            await self.cog.bot.achievement_manager.check_unlock(self.user_id, "fishing", "all_legendary_caught", current_all, self.channel)
        
        if legendary_key == "cthulhu_con":
            self.cog.dark_map_active[self.user_id] = False
            self.cog.dark_map_casts[self.user_id] = 0
            self.cog.dark_map_cast_count[self.user_id] = 0


class LegendaryHallView(discord.ui.View):
    
    def __init__(self, legendary_list, current_index=0):
        super().__init__(timeout=300)
        self.legendary_list = legendary_list
        self.current_index = current_index
        self.message = None
    
    @discord.ui.button(label="← Cá Trước", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_buttons()
            await self.update_message(interaction)
    
    @discord.ui.button(label="Cá Tiếp →", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index < len(self.legendary_list) - 1:
            self.current_index += 1
            self.update_buttons()
            await self.update_message(interaction)
    
    def update_buttons(self):
        prev_btn = None
        next_btn = None
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label and "← " in child.label:
                    prev_btn = child
                elif child.label and " →" in child.label:
                    next_btn = child
        if prev_btn:
            prev_btn.disabled = self.current_index == 0
        if next_btn:
            next_btn.disabled = self.current_index == len(self.legendary_list) - 1
    
    async def update_message(self, interaction: discord.Interaction):
        fish, catchers = self.legendary_list[self.current_index]
        embed = self.build_embed(fish, catchers)
        await interaction.response.edit_message(embed=embed, view=self)
    
    def build_embed(self, fish, catchers):
        emoji = fish['emoji']
        price = fish.get('sell_price', 0)
        fish_key = fish['key']
        
        conditions = self._get_conditions(fish_key)
        
        if catchers:
            catcher_text = "\n".join([f"⭐ **{c['username']}**" for c in catchers])
            
            embed = discord.Embed(
                title=f"🏆 {emoji} Huyền Thoại #{self.current_index + 1}",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="💎 Giá Bán", value=f"{price} Hạt", inline=True)
            embed.add_field(name="📊 Số Người Bắt", value=f"{len(catchers)}", inline=True)
            embed.add_field(name="📋 Nhiệm Vụ", value=conditions, inline=False)
            embed.add_field(name="🏅 Những Người Chinh Phục", value=catcher_text, inline=False)
            
            fish_image_url = fish.get('image_url')
            if fish_image_url:
                embed.set_image(url=fish_image_url)
        else:
            embed = discord.Embed(
                title=f"❓ ??? Huyền Thoại #{self.current_index + 1}",
                description="Cá huyền thoại bí ẩn chưa được khám phá...",
                color=discord.Color.greyple()
            )
            
            embed.add_field(name="💎 Giá Bán", value="??? Hạt", inline=True)
            embed.add_field(name="📊 Số Người Bắt", value="0", inline=True)
            embed.add_field(name="📋 Nhiệm Vụ", value=conditions, inline=False)
            embed.add_field(name="🏅 Những Người Chinh Phục", value="Chưa có ai bắt được...\n🎯 Bạn có thể là người đầu tiên!", inline=False)
        
        page_num = self.current_index + 1
        total_pages = len(self.legendary_list)
        embed.set_footer(text=f"Trang {page_num}/{total_pages} • 🎣 Hãy hoàn thành nhiệm vụ để gặp huyền thoại!")
        
        return embed
    
    def _get_conditions(self, fish_key: str) -> str:
        conditions_map = {
            "thuong_luong": "🌙 Câu lúc **21:00 - 03:00**\n⏰ Hoàn thành nghi thức 30 phút",
            "ca_ngan_ha": "🌌 Câu lúc **00:00 - 04:00**\n⭐ Thu thập đủ **3 Mảnh Sao Băng**",
            "ca_phuong_hoang": "🔥 Câu lúc **06:00 - 09:00**\n🪶 Thu thập đủ **5 Lông Vũ Phượng Hoàng**",
            "cthulhu_con": "🗺️ Sử dụng **Bản Đồ Bóng Tối**\n🎣 Câu 10 lần trong vùng tối",
            "ca_voi_52hz": "📡 Phát hiện **tín hiệu 52Hz**\n🎵 Sử dụng Máy Phát Sóng"
        }
        return conditions_map.get(fish_key, "❓ Điều kiện bí ẩn...")

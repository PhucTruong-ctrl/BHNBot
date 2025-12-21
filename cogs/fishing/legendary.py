"""Legendary fish system."""

import discord
import random
import json
from datetime import datetime
from .constants import DB_PATH, LEGENDARY_FISH, LEGENDARY_FISH_KEYS, ALL_FISH, ROD_LEVELS
from .glitch import apply_display_glitch
from database_manager import get_fish_collection

class LegendaryBossFightView(discord.ui.View):
    """Interactive boss fight for legendary fish with balanced difficulty."""
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
        
        # Add buttons conditionally
        # Always add "Giật Mạnh" button
        jerk_btn = discord.ui.Button(label="🔴 GIẬT MẠNH (10%)", style=discord.ButtonStyle.danger)
        jerk_btn.callback = self.jerk_hard
        self.add_item(jerk_btn)
        
        # Only add "Dìu Cá" button if rod is level 5
        if self.rod_level >= 5:
            # Check for active boosts to show correct percentage
            chance = 0.65
            consumable_cog = self.cog.bot.get_cog("ConsumableCog")
            if consumable_cog:
                active_boost = consumable_cog.peek_active_boost(self.user_id)
                if active_boost and active_boost.get("effect_type") == "legendary_fish_boost":
                    chance = active_boost.get("effect_value", 0.65)
            
            guide_btn = discord.ui.Button(label=f"🌊 DÌU CÁ ({int(chance*100)}%)", style=discord.ButtonStyle.primary)
            guide_btn.callback = self.guide_fish
            self.add_item(guide_btn)
        
        # Always add "Cắt Dây" button
        cut_btn = discord.ui.Button(label="✂️ CẮT DÂY (An Toàn)", style=discord.ButtonStyle.secondary)
        cut_btn.callback = self.cut_line
        self.add_item(cut_btn)
    
    async def jerk_hard(self, interaction: discord.Interaction):
        """Aggressive method: 10% win rate, breaks rod on failure."""
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
            
            # Track in collection book
            from .helpers import track_caught_fish
            await track_caught_fish(self.user_id, self.legendary_fish['key'])
            
            # Check achievement
            legendary_key = self.legendary_fish['key']
            legendary_stat_map = {
                "thuong_luong": "legendary_caught",
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
                    print(f"[ACHIEVEMENT] Tracked {stat_key} for user {self.user_id} on legendary catch {legendary_key}")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error tracking {stat_key} for {self.user_id}: {e}")
            
            # Clean up dark map if caught Cthulhu non
            if legendary_key == "cthulhu_con":
                self.cog.dark_map_active[self.user_id] = False
                self.cog.dark_map_casts[self.user_id] = 0
                self.cog.dark_map_cast_count[self.user_id] = 0
        else:
            self.failed = True  # Mark as failed
            username = self.user.display_name if self.user else "Unknown"
            result_embed = discord.Embed(
                title=f"💥 {username} - CẦN ĐÃ GÃY! 💥",
                description=f"❌ Quá mạnh! Cần câu của bạn không chịu được lực và **GÃY TOÁC**!\n\n⚠️ Bạn sẽ cần sửa chữa.",
                color=discord.Color.red()
            )
            # Break rod completely (durability = 0)
            await self.cog.update_rod_data(self.user_id, 0)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    async def guide_fish(self, interaction: discord.Interaction):
        """Technique method: 65% win rate, high skill requirement (Lv5 only), -40 durability on failure."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        
        # Check if rod is level 5
        if self.rod_level < 5:
            username = self.user.display_name if self.user else "Unknown"
            fail_embed = discord.Embed(
                title=f"🔒 {username} - KHÔNG ĐỦ ĐIỀU KIỆN",
                description=f"🎣 Kỹ thuật \"Dìu Cá\" chỉ dành riêng cho **Cần Poseidon (Cấp 5)**!\n\nCần hiện tại: Cấp {self.rod_level}/5\n\n💡 Hãy chọn \"Giật Mạnh\" hoặc tiếp tục cày để nâng cấp cần.",
                color=discord.Color.orange()
            )
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=fail_embed, view=self)
            return
        
        # Check for active boosts from consumable items
        base_chance = 0.65
        boost_message = ""
        
        # Get consumable cog to check for active boosts
        consumable_cog = interaction.client.get_cog("ConsumableCog")
        if consumable_cog:
            active_boost = consumable_cog.get_active_boost(self.user_id)
            if active_boost and active_boost.get("effect_type") == "legendary_fish_boost":
                base_chance = active_boost.get("effect_value", 0.65)
                boost_item_key = active_boost.get("item_key", "")
                from .consumables import get_consumable_info
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
            
            # Track in collection book
            from .helpers import track_caught_fish
            await track_caught_fish(self.user_id, self.legendary_fish['key'])
            
            # Track legendary achievement
            legendary_key = self.legendary_fish['key']
            legendary_stat_map = {
                "thuong_luong": "legendary_caught",
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
                    print(f"[ACHIEVEMENT] Tracked {stat_key} for user {self.user_id} on legendary catch {legendary_key}")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error tracking {stat_key} for {self.user_id}: {e}")
            
            # Clean up dark map if caught Cthulhu non
            if legendary_key == "cthulhu_con":
                self.cog.dark_map_active[self.user_id] = False
                self.cog.dark_map_casts[self.user_id] = 0
                self.cog.dark_map_cast_count[self.user_id] = 0
        else:
            self.failed = True  # Mark as failed
            username = self.user.display_name if self.user else "Unknown"
            # Lose 40 durability on failure (not breaking)
            new_durability = max(0, self.rod_durability - 40)
            result_embed = discord.Embed(
                title=f"💔 {username} - THẤT BẠI! 💔",
                description=f"❌ Quá mạnh! Cá chạy thoát!\n\n🛡️ Cần câu mất **-40 Độ Bền** (Còn: {new_durability})",
                color=discord.Color.red()
            )
            await self.cog.update_rod_data(self.user_id, new_durability)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    async def cut_line(self, interaction: discord.Interaction):
        """Safe method: No penalty but no catch."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu được bọn này thôi!", ephemeral=True)
            return
        if self.fought:
            await interaction.response.send_message("❌ Đã quyết định rồi!", ephemeral=True)
            return
        
        self.fought = True
        username = self.user.display_name if self.user else "Unknown"
        result_embed = discord.Embed(
            title=f"🏃 {username} - ĐÃ BỎ CUỘC 🏃",
            description=f"✂️ Bạn cắt dây cá.\n\n{self.legendary_fish['emoji']} **{apply_display_glitch(self.legendary_fish['name'])}** thoát khỏi an toàn!\n\n💡 Ít nhất cần của bạn còn nguyên vẹn.",
            color=discord.Color.greyple()
        )
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=result_embed, view=self)

async def check_legendary_spawn_conditions(user_id: int, guild_id: int, current_hour: int, cog=None) -> dict | None:
    """Check if legendary fish should spawn. Each player can only catch 1 of each legendary fish.
    Checks for special summoning conditions: sacrifice, crafted bait, map, frequency, etc."""
    import json
    from database_manager import get_inventory

    try:
        fish_collection = await get_fish_collection(user_id)
        legendary_list = list(fish_collection.keys())
    except:
        legendary_list = []
    
    if not cog:
        # Fallback to basic spawn check
        for legendary in LEGENDARY_FISH:
            if legendary['key'] in legendary_list:
                continue
            time_restriction = legendary.get("time_restriction")
            if time_restriction is not None:
                start_hour, end_hour = time_restriction
                if not (start_hour <= current_hour < end_hour):
                    continue
            if random.random() < legendary["spawn_chance"]:
                return legendary
        return None
    
    # Fetch inventory once for all checks
    inventory = await get_inventory(user_id)
    
    # Check each legendary fish for summoning conditions
    for legendary in LEGENDARY_FISH:
        legendary_key = legendary['key']
        
        # Check if already caught
        already_caught = legendary_key in legendary_list
        
        # If already caught, check if summoning condition is met anyway (for lore embed)
        if already_caught:
            # Special handling for each legendary
            if legendary_key == "thuong_luong":
                # Thuong Luong has its own check in _hiente_action
                continue
            elif legendary_key == "ca_ngan_ha":
                if user_id in cog.guaranteed_catch_users:
                    return {"already_caught": legendary_key}
                continue
            elif legendary_key == "ca_phuong_hoang":
                if not (12 <= current_hour < 14):
                    continue
                has_buff = cog.phoenix_buff_active.get(user_id, False)
                if has_buff or inventory.get("long_vu_lua", 0) > 0:
                    return {"already_caught": legendary_key}
                continue
            elif legendary_key == "cthulhu_con":
                if cog.dark_map_active.get(user_id, False) and cog.dark_map_casts.get(user_id, 0) > 0:
                    return {"already_caught": legendary_key}
                continue
            elif legendary_key == "ca_voi_52hz":
                consumable_cog = cog.bot.get_cog("ConsumableCog") if hasattr(cog, 'bot') else None
                if consumable_cog and consumable_cog.has_detected_52hz(user_id):
                    return {"already_caught": legendary_key}
                continue
            else:
                continue
        
        # Skip if player already caught this legendary fish
        if legendary['key'] in legendary_list:
            continue
        
        # 1. THUỒNG LUỒNG - Progressive sacrifice chance
        if legendary_key == "thuong_luong":
            sacrifice_count = await cog.get_sacrifice_count(user_id)
            if sacrifice_count >= 3:
                start_time = cog.thuong_luong_timers.get(user_id)
                if not start_time:
                    continue

                import time
                elapsed = time.time() - start_time

                # Check if ritual expired (> 5 minutes)
                if elapsed > 300:
                    await cog.reset_sacrifice_count(user_id)
                    if user_id in cog.thuong_luong_timers:
                        del cog.thuong_luong_timers[user_id]
                    return "thuong_luong_expired"

                # Progressive spawn chance with guaranteed spawn in the last minute
                if elapsed > 240:  # 5th minute: GUARANTEED
                    await cog.reset_sacrifice_count(user_id)
                    if user_id in cog.thuong_luong_timers:
                        del cog.thuong_luong_timers[user_id]
                    return legendary

                chance = 0.0
                if elapsed <= 60:  # Minute 1
                    chance = 0.40
                elif elapsed <= 120:  # Minute 2
                    chance = 0.50
                elif elapsed <= 180:  # Minute 3
                    chance = 0.60
                elif elapsed <= 240:  # Minute 4
                    chance = 0.70
                
                if random.random() < chance:
                    await cog.reset_sacrifice_count(user_id)
                    if user_id in cog.thuong_luong_timers:
                        del cog.thuong_luong_timers[user_id]
                    return legendary
            continue
        
        # 2. CÁ NGÂN HÀ - Guaranteed catch from tinh cau mini-game win
        if legendary_key == "ca_ngan_ha":
            if user_id in cog.guaranteed_catch_users:
                # Remove the buff after use
                del cog.guaranteed_catch_users[user_id]
                return legendary
            continue
        
        # 3. CÁ PHƯỢNG HOÀNG - Server tree level + time + optional item condition
        if legendary_key == "ca_phuong_hoang":
            if not (12 <= current_hour < 14):
                continue
            
            # Check if has Lông Vũ Lửa buff active
            has_buff = cog.phoenix_buff_active.get(user_id, False)
            
            if has_buff or inventory.get("long_vu_lua", 0) > 0:
                if random.random() < legendary["spawn_chance"]:
                    # Use item if not in active buff
                    if not has_buff and inventory.get("long_vu_lua", 0) > 0:
                        from database_manager import remove_item
                        await remove_item(user_id, "long_vu_lua", 1)
                        cog.phoenix_buff_active[user_id] = True  # Buff lasts until next catch
                    return legendary
            continue
        
        # 4. CTHULHU NON - Dark map active (10 casts remaining)
        if legendary_key == "cthulhu_con":
            if cog.dark_map_active.get(user_id, False) and cog.dark_map_casts.get(user_id, 0) > 0:
                # Increment cast count (1-10)
                if user_id not in cog.dark_map_cast_count:
                    cog.dark_map_cast_count[user_id] = 0
                cog.dark_map_cast_count[user_id] += 1
                current_cast = cog.dark_map_cast_count[user_id]
                
                # Decrement remaining casts
                cog.dark_map_casts[user_id] -= 1
                
                if current_cast == 10:
                    # 10th cast - GUARANTEED spawn
                    # Clean up after guaranteeing spawn
                    cog.dark_map_active[user_id] = False
                    cog.dark_map_casts[user_id] = 0
                    cog.dark_map_cast_count[user_id] = 0
                    from database_manager import remove_item
                    await remove_item(user_id, "ban_do_ham_am", 1)
                    return legendary
                elif current_cast < 10:
                    # Casts 1-9: Random spawn chance
                    if random.random() < legendary["spawn_chance"]:
                        # Spawn success - cleanup and return
                        cog.dark_map_active[user_id] = False
                        cog.dark_map_casts[user_id] = 0
                        cog.dark_map_cast_count[user_id] = 0
                        from database_manager import remove_item
                        await remove_item(user_id, "ban_do_ham_am", 1)
                        return legendary
                elif cog.dark_map_casts[user_id] <= 0:
                    # Map expired (should not happen with 10 casts, but safety check)
                    cog.dark_map_active[user_id] = False
                    cog.dark_map_cast_count[user_id] = 0
                    from database_manager import remove_item
                    await remove_item(user_id, "ban_do_ham_am", 1)
            continue
        
        # 5. CÁ VOI 52HZ - Frequency detected flag
        if legendary_key == "ca_voi_52hz":
            consumable_cog = cog.bot.get_cog("ConsumableCog") if hasattr(cog, 'bot') else None
            if consumable_cog and consumable_cog.has_detected_52hz(user_id):
                # 100% spawn and reset flag
                consumable_cog.clear_52hz_signal(user_id)
                return legendary
            continue
        
        # 6. CÁ PHƯỢNG HOÀNG - Guaranteed catch from phoenix buff
        if legendary_key == "ca_phuong_hoang":
            from .legendary_quest_helper import has_phoenix_buff
            if await has_phoenix_buff(user_id):
                # Reset buff after guaranteed catch
                from .legendary_quest_helper import set_phoenix_buff
                await set_phoenix_buff(user_id, False)
                return legendary
            continue
        
        # Fallback: basic spawn check with time restriction
        time_restriction = legendary.get("time_restriction")
        if time_restriction is not None:
            start_hour, end_hour = time_restriction
            if not (start_hour <= current_hour < end_hour):
                continue
        
        if random.random() < legendary["spawn_chance"]:
            return legendary
    
    return None

async def add_legendary_fish_to_user(user_id: int, legendary_key: str):
    """Add legendary fish to user's collection. Returns updated legendary list."""
    try:
        fish_collection = await get_fish_collection(user_id)
        legendary_list = list(fish_collection.keys())
        
        legendary_list.append(legendary_key)
        
        # Store the legendary fish using the insert function
        from database_manager import db_manager
        await db_manager.modify(
            "INSERT OR IGNORE INTO fish_collection (user_id, fish_id, quantity) VALUES (?, ?, ?)",
            (user_id, legendary_key, 1)
        )
        
        # Mark as caught in quest system
        from .legendary_quest_helper import set_legendary_caught
        await set_legendary_caught(user_id, legendary_key, True)
        
        # Track legendary caught for achievements
        from database_manager import increment_stat
        await increment_stat(user_id, "fishing", "legendary_caught", 1)
        
        # Check if all legendary fish caught
        from .constants import LEGENDARY_FISH_KEYS
        caught_legendary = [fish for fish in legendary_list if fish in LEGENDARY_FISH_KEYS]
        if len(caught_legendary) >= len(LEGENDARY_FISH_KEYS):
            try:
                await increment_stat(user_id, "fishing", "all_legendary_caught", 1)
                # Note: This stat should only be 1, but we use increment to ensure it's set
                print(f"[ACHIEVEMENT] User {user_id} has caught all legendary fish!")
            except Exception as e:
                print(f"[ACHIEVEMENT] Error tracking all_legendary_caught for {user_id}: {e}")
            
            return legendary_list
    except Exception as e:
        pass
    return []

"""Main Fishing Cog."""

import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import random
import time

from .constants import *
from .helpers import track_caught_fish, get_collection, check_collection_complete
from .rod_system import get_rod_data, update_rod_data as update_rod_data_module
from .legendary import LegendaryBossFightView, check_legendary_spawn_conditions, add_legendary_fish_to_user as add_legendary_module
from .events import trigger_random_event
from .views import FishSellView
from database_manager import (
    get_inventory, add_item, remove_item, add_seeds, 
    get_user_balance, get_or_create_user
)

class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fishing_cooldown = {}
        self.caught_items = {}
        self.user_titles = {}
        self.user_stats = {}
        self.user_achievements = {}
        self.lucky_buff_users = {}
        self.avoid_event_users = {}
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="cauca", description="Câu cá - thời gian chờ 30s")
    async def fish_slash(self, interaction: discord.Interaction):
        await self._fish_action(interaction)
    
    @commands.command(name="cauca")
    async def fish_prefix(self, ctx):
        await self._fish_action(ctx)
    
    async def _fish_action(self, ctx_or_interaction):
        """Main fishing logic - rút gọn, gọi helpers từ modules khác"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            channel = ctx_or_interaction.channel
            guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            channel = ctx_or_interaction.channel
            guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
            ctx = ctx_or_interaction
        
        # --- GET ROD DATA ---
        rod_lvl, rod_durability = await get_rod_data(user_id)
        rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
        
        # --- CHECK FISH BUCKET LIMIT (BEFORE ANYTHING ELSE) ---
        # Get current fish count
        current_inventory = await get_inventory(user_id)
        fish_count = sum(v for k, v in current_inventory.items() if k in ALL_FISH)
        
        # If bucket is full (15+ fish), block fishing immediately
        if fish_count >= 15:
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            embed = discord.Embed(
                title=f"⚠️ XÔ ĐÃ ĐẦY - {username_display}!",
                description=f"🪣 Xô cá của bạn đã chứa {fish_count} con cá (tối đa 15).\n\nHãy bán cá để có chỗ trống, rồi quay lại câu tiếp!",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Hãy dùng lệnh bán cá để bán bớt nhé.")
            if is_slash:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            print(f"[FISHING] [BLOCKED] {username_display} (user_id={user_id}) bucket_full fish_count={fish_count}/15")
            return
        
        # --- CHECK DURABILITY & AUTO REPAIR ---
        repair_msg = ""
        is_broken_rod = False  # Flag to treat as no-worm when durability is broken
        
        if rod_durability <= 0:
            repair_cost = rod_config["repair"]
            balance = await get_user_balance(user_id)
            
            if balance >= repair_cost:
                # Auto repair
                await add_seeds(user_id, -repair_cost)
                rod_durability = rod_config["durability"]
                await update_rod_data(user_id, rod_durability)
                repair_msg = f"\n🛠️ *Cần gãy! Đã tự động sửa (-{repair_cost} Hạt)*"
                print(f"[FISHING] [AUTO_REPAIR] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} (user_id={user_id}) seed_change=-{repair_cost} new_durability={rod_durability}")
            else:
                # Not enough money to repair - allow fishing but with broken rod penalties
                is_broken_rod = True
                repair_msg = f"\n⚠️ **Cần câu đã gãy!** Phí sửa là {repair_cost} Hạt. Bạn đang câu với cần gãy (chỉ 1% cá hiếm, 1 item/lần, không rương)."
                print(f"[FISHING] [BROKEN_ROD] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} (user_id={user_id}) cannot_afford_repair cost={repair_cost}")
        
        # --- CHECK COOLDOWN (using rod-based cooldown) ---
        remaining = await self.get_fishing_cooldown_remaining(user_id)
        if remaining > 0:
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            msg = f"⏱️ **{username_display}** chờ chút nhen! Cần chờ {remaining}s nữa mới được câu lại!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Ensure user exists
        username = ctx.author.name if not is_slash else ctx_or_interaction.user.name
        await get_or_create_user(user_id, username)
        
        # --- LOGIC MỚI: AUTO-BUY MỒI NẾU CÓ ĐỦ TIỀN ---
        inventory = await get_inventory(user_id)
        has_worm = inventory.get("worm", 0) > 0
        auto_bought = False  # Biến check xem có tự mua không

        # Nếu không có mồi, kiểm tra xem có đủ tiền mua không
        if not has_worm:
            balance = await get_user_balance(user_id)
            if balance >= WORM_COST:
                # Tự động trừ tiền coi như mua mồi dùng ngay
                await add_seeds(user_id, -WORM_COST)
                has_worm = True
                auto_bought = True
                print(f"[FISHING] [AUTO_BUY_WORM] {username} (user_id={user_id}) seed_change=-{WORM_COST} action=purchased_bait")
            else:
                # Không có mồi, cũng không đủ tiền -> Chấp nhận câu rác
                has_worm = False
        else:
            # Có mồi trong túi -> Trừ mồi
            await remove_item(user_id, "worm", 1)
            print(f"[FISHING] [CONSUME_WORM] {username} (user_id={user_id}) inventory_change=-1 action=used_bait")
        
        # --- KẾT THÚC LOGIC MỚI ---
        
        print(f"[FISHING] [START] {username} (user_id={user_id}) rod_level={rod_lvl} rod_durability={rod_durability} has_bait={has_worm}")
        
        # Set cooldown using rod-based cooldown
        self.fishing_cooldown[user_id] = time.time() + rod_config["cd"]
        
        # Casting animation
        wait_time = random.randint(1, 5)
        
        # Thêm thông báo nhỏ nếu tự mua mồi hoặc không có mồi
        status_text = ""
        if auto_bought:
            status_text = f"\n💸 *(-{WORM_COST} Hạt mua mồi)*"
        elif not has_worm:
            status_text = "\n⚠️ *Không có mồi (Tỉ lệ rác cao)*"
        
        rod_status = f"\n🎣 *{rod_config['emoji']} {rod_config['name']} (Thời gian chờ: {rod_config['cd']}s)*"

        casting_msg = await channel.send(
            f"🎣 **{username}** quăng cần... Chờ cá cắn câu... ({wait_time}s){status_text}{rod_status}"
        )
        await asyncio.sleep(wait_time)
        
        # ==================== TRIGGER RANDOM EVENTS ====================
        
        event_result = await trigger_random_event(self, user_id, channel.guild.id, rod_lvl)
        
        # If user avoided a bad event, show what they avoided
        if event_result.get("avoided", False):
            embed = discord.Embed(
                title=f"🛡️ BẢO VỆ - {username}!",
                description=f"✨ **Giác Quan Thứ 6 hoặc Đi Chùa bảo vệ bạn!**\n\n{event_result['message']}\n\n**Bạn an toàn thoát khỏi sự kiện này!**",
                color=discord.Color.gold()
            )
            await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
            await asyncio.sleep(1)
            casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
        # Check if user was protected from bad event
        was_protected = False
        if hasattr(self, "avoid_event_users") and self.avoid_event_users.get(user_id, False):
            was_protected = True
        
        # Initialize durability loss (apply after event check)
        durability_loss = 1  # Default: 1 per cast
        
        if event_result.get("triggered", False):
            # Random event occurred!
            event_message = event_result["message"]
            event_type = event_result.get("type")
            
            # *** DURABILITY LOSS FROM EVENTS ***
            if event_type == "equipment_break":
                # Gãy cần: Trừ hết độ bền
                durability_loss = rod_durability  # Trừ sạch về 0
            elif event_type in ["snapped_line", "plastic_trap", "big_log", "crab_cut", "electric_eel"]:
                # Đứt dây / Vướng rác / Mắc gỗ / Cua kẹp / Lươn Điện: Trừ 5 độ bền
                durability_loss = 5
            elif event_type == "predator":
                # Cá dữ: Trừ 3 độ bền
                durability_loss = 3
            
            # Process event effects
            if event_result.get("lose_worm", False) and has_worm:
                await remove_item(user_id, "worm", 1)
                event_message += " (Mất 1 Giun)"
            
            if event_result.get("lose_money", 0) > 0:
                await add_seeds(user_id, -event_result["lose_money"])
                event_message += f" (-{event_result['lose_money']} Hạt)"
            
            if event_result.get("gain_money", 0) > 0:
                await add_seeds(user_id, event_result["gain_money"])
                event_message += f" (+{event_result['gain_money']} Hạt)"
            
            # Process gain_items (pearls, worms, chests, etc.)
            if event_result.get("gain_items", {}):
                for item_key, item_count in event_result["gain_items"].items():
                    await add_item(user_id, item_key, item_count)
                    item_name = ALL_FISH.get(item_key, {}).get("name", item_key)
                    event_message += f" (+{item_count} {item_name})"
            
            # Handle special effects
            if event_result.get("custom_effect") == "lose_all_bait":
                # sea_sickness: Mất hết mồi
                inventory = await get_inventory(user_id)
                worm_count = inventory.get("worm", 0)
                if worm_count > 0:
                    await remove_item(user_id, "worm", worm_count)
                    event_message += f" (Nôn hết {worm_count} Giun)"
                    print(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=sea_sickness inventory_change=-{worm_count} item=worm")
            
            elif event_result.get("custom_effect") == "cat_steal":
                # Mèo Mun: Cướp con cá to nhất (giá cao nhất)
                # Điều này sẽ xử lý ở phần sau trong catch result
                pass
            
            elif event_result.get("custom_effect") == "snake_bite":
                # Rắn Nước: Trừ 5% tài sản
                balance = await get_user_balance(user_id)
                penalty = max(10, int(balance * 0.05))  # Min 10 Hạt
                await add_seeds(user_id, -penalty)
                event_message += f" (Trừ 5% tài sản: {penalty} Hạt)"
                print(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=snake_bite seed_change=-{penalty} penalty_type=asset_penalty")
            
            elif event_result.get("custom_effect") == "lucky_buff":
                # Cầu Vồng Đôi: Buff may mắn cho lần sau (cá hiếm chắc chắn)
                # Lưu vào cache (tạm thời cho lần tiếp theo)
                if not hasattr(self, "lucky_buff_users"):
                    self.lucky_buff_users = {}
                self.lucky_buff_users[user_id] = True
                event_message += " (Lần câu sau chắc ra Cá Hiếm!)"
                print(f"[EVENT] {username} received lucky buff for next cast")
            
            elif event_result.get("custom_effect") == "sixth_sense":
                # Giác Thứ 6: Tránh xui lần sau (bỏ qua event tiếp theo)
                if not hasattr(self, "avoid_event_users"):
                    self.avoid_event_users = {}
                self.avoid_event_users[user_id] = True
                event_message += " (Lần sau tránh xui!)"
                print(f"[EVENT] {username} will avoid bad event on next cast")
            
            elif event_result.get("custom_effect") == "restore_durability":
                # Hồi độ bền: +20 độ bền (không vượt quá max)
                max_durability = rod_config["durability"]
                rod_durability = min(max_durability, rod_durability + 20)
                await self.update_rod_data(user_id, rod_durability)
                event_message += f" (Độ bền +20: {rod_durability}/{max_durability})"
                print(f"[EVENT] {username} restored rod durability to {rod_durability}")
            
            # Note: global_reset is handled after event embed display below
            
            # Adjust cooldown (golden_turtle có thể là -30 để reset)
            if event_result.get("cooldown_increase", 0) != 0:
                if event_result["cooldown_increase"] < 0:
                    # Reset cooldown (golden_turtle)
                    self.fishing_cooldown[user_id] = time.time()
                    event_message += " (Thời gian chờ xóa sạch!)"
                    print(f"[EVENT] {username} Thời gian chờ reset")
                else:
                    self.fishing_cooldown[user_id] = time.time() + rod_config["cd"] + event_result["cooldown_increase"]
            else:
                self.fishing_cooldown[user_id] = time.time() + rod_config["cd"]
            
            # If lose_catch, don't process fishing
            if event_result.get("lose_catch", False):
                embed = discord.Embed(
                    title=f"⚠️ KIẾP NẠN - {username}!",
                    description=event_message,
                    color=discord.Color.red()
                )
                # Apply durability loss before returning
                rod_durability = max(0, rod_durability - durability_loss)
                await self.update_rod_data(user_id, rod_durability)
                embed.set_footer(text=f"🛡️ Độ bền: {rod_durability}/{rod_config['durability']}")
                await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
                print(f"[EVENT] {username} triggered {event_type} - fishing cancelled, durability loss: {durability_loss}")
                return
            
            # Otherwise, display event message and continue fishing
            event_type_data = RANDOM_EVENTS.get(event_type, {})
            is_good_event = event_type_data.get("type") == "good"
            color = discord.Color.green() if is_good_event else discord.Color.orange()
            event_title = f"🌟 PHƯỚC LÀNH - {username}!" if is_good_event else f"⚠️ KIẾP NẠN - {username}!"
            embed = discord.Embed(
                title=event_title,
                description=event_message,
                color=color
            )
            await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
            
            # Handle global reset events
            if event_result.get("custom_effect") == "global_reset":
                # Clear all fishing cooldowns
                self.fishing_cooldown.clear()
                
                # Send server-wide announcement
                announcement_embed = discord.Embed(
                    title="🌟🌟🌟 SỰ KIỆN TOÀN SERVER! 🌟🌟🌟",
                    description=f"⚡ **{username}** đã kích hoạt **{event_type_data.get('name', event_type)}**!\n\n"
                                f"✨ **TẤT CẢ MỌI NGƯỜI ĐÃ ĐƯỢC HỒI PHỤC COOLDOWN!**\n"
                                f"🚀 Mau vào câu ngay nào các đồng ngư ơi! 🎣🎣🎣",
                    color=discord.Color.magenta()
                )
                await channel.send(embed=announcement_embed)
                print(f"[GLOBAL EVENT] {username} triggered {event_type} - All fishing cooldowns cleared!")
            
            # Wait a bit before showing catch
            await asyncio.sleep(1)
            casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
        # ==================== NORMAL FISHING PROCESSING ====================
        
        # Roll số lượng cá (1-5) với tỉ lệ giảm dần
        # NHƯNG: Nếu không có mồi HOẶC cần gãy -> chỉ được 1 cá hoặc 1 rác (không multiple)
        if has_worm and not is_broken_rod:
            num_fish = random.choices([1, 2, 3, 4, 5], weights=CATCH_COUNT_WEIGHTS, k=1)[0]
        else:
            num_fish = 1  # Không mồi hoặc cần gãy = 1 cá thôi
        
        # Apply catch multiplier from events (e.g., Golden Hook)
        multiplier = event_result.get("catch_multiplier", 1)
        original_num_fish = num_fish
        num_fish = num_fish * multiplier
        if multiplier > 1:
            print(f"[EVENT] {username} activated catch_multiplier x{multiplier}: {original_num_fish} → {num_fish} fish")
        
        # Roll trash (độc lập)
        # NHƯNG: Nếu không có mồi HOẶC cần gãy -> chỉ roll trash hoặc cá, không vừa cá vừa rác vừa rương
        if has_worm and not is_broken_rod:
            trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
        else:
            # Không mồi hoặc cần gãy: Xác suất cao là rác (50/50 rác hoặc cá)
            trash_count = random.choices([0, 1], weights=[50, 50], k=1)[0]
        
        # Roll chest (độc lập, tỉ lệ thấp)
        # NHƯNG: Nếu không có mồi HOẶC cần gãy -> không bao giờ ra rương
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        if has_worm and not is_broken_rod:
            chest_weights = [95, 5] if not is_boosted else [90, 10]
            chest_count = random.choices([0, 1], weights=chest_weights, k=1)[0]
        else:
            chest_count = 0  # Không mồi = không ra rương
        
        results = {"fish": num_fish}
        if trash_count > 0:
            results["trash"] = trash_count
        if chest_count > 0:
            results["chest"] = chest_count
        
        print(f"[FISHING] {username} rolled: {num_fish} fish, {trash_count} trash, {chest_count} chest [has_worm={has_worm}]")
        
        is_boosted = await self.get_tree_boost_status(channel.guild.id)
        boost_text = " ✨**(CÂY BUFF!)**✨" if is_boosted else ""
        
        # Track caught items for sell button
        self.caught_items[user_id] = {}
        
        # Build summary display and process all results
        fish_display = []
        fish_only_items = {}
        
        # FIX: Track if rare fish already caught this turn (Max 1 rare per cast)
        caught_rare_this_turn = False
        
        # Chọn loot table dựa trên có worm hay không, hoặc cần gãy
        if has_worm and not is_broken_rod:
            # Có mồi = dùng loot table bình thường (có cả cá hiếm)
            loot_table = LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
        else:
            # Không có mồi HOẶC cần gãy = dùng loot table giảm cực (chỉ rác và cá thường, 1% hiếm)
            loot_table = LOOT_TABLE_NO_WORM
        
        # Process fish - roll loại cá cho mỗi con
        # CHÚ Ý: Boost KHÔNG tăng tỷ lệ Cá Hiếm, chỉ tăng tỷ lệ Rương để balance
        for _ in range(num_fish):
            # Roll từ LOOT_TABLE để xác định loại (Rare vs Common)
            # Normalize weights để lấy tỉ lệ common vs rare
            fish_weights_sum = loot_table["common_fish"] + loot_table["rare_fish"]
            
            # Nếu không có mồi, fish_weights_sum = 30 + 0 = 30
            # Lúc này common_ratio = 100%, rare_ratio = 0% (không bao giờ rare)
            if fish_weights_sum == 0:
                # Nếu không có cá nào trong loot table (chỉ có rác/rương)
                common_ratio = 1.0
                rare_ratio = 0.0
            else:
                common_ratio = loot_table["common_fish"] / fish_weights_sum
                rare_ratio = loot_table["rare_fish"] / fish_weights_sum
            
            # *** APPLY ROD LUCK BONUS ***
            rare_ratio = min(0.9, rare_ratio + rod_config["luck"])  # Cap at 90% max
            common_ratio = 1.0 - rare_ratio  # Adjust common to maintain 100% total
            
            is_rare = random.choices([False, True], weights=[common_ratio, rare_ratio], k=1)[0]
            
            # Check if convert_to_trash event is active (e.g., Pollution)
            if event_result.get("convert_to_trash", False):
                # Convert fish to trash
                trash = random.choice(TRASH_ITEMS)
                item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                await self.add_inventory_item(user_id, item_key, "trash")
                print(f"[EVENT-POLLUTION] {username} fish converted to trash: {item_key}")
                continue
            
            # FIX: Nếu đã bắt rare rồi hoặc roll ra rare lần này nhưng đã bắt rare trước -> bắt buộc common
            if is_rare and not caught_rare_this_turn:
                fish = random.choice(RARE_FISH)
                caught_rare_this_turn = True  # Đánh dấu đã bắt rare
                print(f"[FISHING] {username} caught RARE fish: {fish['key']} ✨ (Max 1 rare per cast, Rod Luck: +{int(rod_config['luck']*100)}%)")
                await self.add_inventory_item(user_id, fish['key'], "fish")
                
                # Check boss_hunter achievement
                if fish['key'] in ['megalodon', 'thuy_quai_kraken', 'leviathan']:
                    await self.check_achievement(user_id, "boss_hunter", channel, guild_id)
                
                # Track in collection
                is_new_collection = await track_caught_fish(user_id, fish['key'])
                if is_new_collection:
                    print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                if fish['key'] not in fish_only_items:
                    fish_only_items[fish['key']] = 0
                fish_only_items[fish['key']] += 1
            else:
                # Bắt cá thường (hoặc roll rare lần 2+ thì buộc common)
                fish = random.choice(COMMON_FISH)
                print(f"[FISHING] {username} caught common fish: {fish['key']}")
                await self.add_inventory_item(user_id, fish['key'], "fish")
                # Track in collection
                is_new_collection = await track_caught_fish(user_id, fish['key'])
                if is_new_collection:
                    print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                if fish['key'] not in fish_only_items:
                    fish_only_items[fish['key']] = 0
                fish_only_items[fish['key']] += 1
        # Display fish grouped
        for key, qty in fish_only_items.items():
            fish = ALL_FISH[key]
            emoji = fish['emoji']
            total_price = fish['sell_price'] * qty  # Multiply price by quantity
            fish_display.append(f"{emoji} {fish['name']} x{qty} ({total_price} Hạt)")
        
        # Process trash (độc lập)
        if trash_count > 0:
            trash_items_caught = {}
            for _ in range(trash_count):
                trash = random.choice(TRASH_ITEMS)
                item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                await self.add_inventory_item(user_id, item_key, "trash")
                if item_key not in trash_items_caught:
                    trash_items_caught[item_key] = 0
                trash_items_caught[item_key] += 1
            
            for key, qty in trash_items_caught.items():
                trash_name = key.replace("trash_", "").replace("_", " ").title()
                fish_display.append(f"🥾 {trash_name} x{qty}")
            print(f"[FISHING] {username} caught trash: {trash_items_caught}")
        
        # Process chest (độc lập)
        if chest_count > 0:
            for _ in range(chest_count):
                await self.add_inventory_item(user_id, "treasure_chest", "tool")
            fish_display.append(f"🎁 Rương Kho Báu x{chest_count}")
            print(f"[FISHING] {username} caught {chest_count}x TREASURE CHEST! 🎁")
        
        # Store only fish for the sell button
        self.caught_items[user_id] = fish_only_items
        print(f"[FISHING] {username} final caught items: {fish_only_items}")
        
        # Handle cat_steal event: Remove most valuable fish and rebuild display
        if event_result.get("custom_effect") == "cat_steal" and fish_only_items:
            most_valuable_fish = None
            highest_price = -1
            for fish_key, qty in fish_only_items.items():
                fish_info = ALL_FISH.get(fish_key, {})
                price = fish_info.get('sell_price', 0)
                if price > highest_price and qty > 0:
                    highest_price = price
                    most_valuable_fish = fish_key
            
            if most_valuable_fish:
                await remove_item(user_id, most_valuable_fish, 1)
                fish_info = ALL_FISH[most_valuable_fish]
                fish_only_items[most_valuable_fish] -= 1
                if fish_only_items[most_valuable_fish] == 0:
                    del fish_only_items[most_valuable_fish]
                
                # Rebuild fish_display from remaining items to avoid duplicates
                fish_display = []
                for key, qty in fish_only_items.items():
                    if qty > 0:
                        fish = ALL_FISH[key]
                        total_price = fish['sell_price'] * qty
                        fish_display.append(f"{fish['emoji']} {fish['name']} x{qty} ({total_price} Hạt)")
                
                print(f"[EVENT] {username} lost {fish_info['name']} to cat_steal")
                if fish_display:
                    fish_display[0] = fish_display[0] + f"\n(🐈 Mèo cướp mất {fish_info['name']} giá {highest_price} Hạt!)"
        
        # Update caught items for sell button
        self.caught_items[user_id] = fish_only_items
        
        # ==================== CHECK FOR LEGENDARY FISH ====================
        current_hour = datetime.now().hour
        legendary_fish = await check_legendary_spawn_conditions(user_id, channel.guild.id, current_hour)
        
        if legendary_fish:
            # Legendary fish spawned! Show boss fight minigame
            legendary_key = legendary_fish['key']
            print(f"[LEGENDARY] {username} encountered {legendary_key}!")
            
            # Create warning embed
            legendary_embed = discord.Embed(
                title="⚠️ CẢNH BÁO: DÂY CÂU CĂNG CỰC ĐỘ!",
                description=f"🌊 Có một con quái vật đang cắn câu!\n"
                           f"💥 Nó đang kéo bạn xuống nước!\n\n"
                           f"**{legendary_fish['emoji']} {legendary_fish['name']}**\n"
                           f"_{legendary_fish['description']}_",
                color=discord.Color.dark_red()
            )
            legendary_embed.add_field(
                name="⚔️ CHUẨN BỊ ĐẤU BOSS!",
                value=f"Độ bền cần câu: {rod_durability}/{rod_config['durability']}\n"
                     f"Cấp độ cần: {rod_lvl}/5",
                inline=False
            )
            legendary_embed.set_image(url=legendary_fish.get('image_url', ''))
            legendary_embed.set_footer(text="Chọn chiến thuật chinh phục quái vật! ⏱️ 60 giây")
            
            # Create boss fight view
            boss_view = LegendaryBossFightView(self, user_id, legendary_fish, rod_durability, rod_lvl, channel, guild_id)
            
            # Send boss fight message
            boss_msg = await channel.send(f"<@{user_id}>", embed=legendary_embed, view=boss_view)
            
            # Wait for interaction or timeout
            try:
                await asyncio.sleep(60)  # 60 second timeout
            except:
                pass
            
            # Check if battle was fought
            if boss_view.fought:
                print(f"[LEGENDARY] {username} fought the boss!")
                # Continue to show normal fishing results as well
            else:
                print(f"[LEGENDARY] {username} didn't choose - boss escaped!")
        
        # ==================== END LEGENDARY CHECK ====================
        
        # Check if collection is complete and award title if needed
        is_complete = await check_collection_complete(user_id)
        title_earned = False
        if is_complete:
            current_title = await self.get_title(user_id, channel.guild.id)
            if not current_title or "Vua" not in current_title:
                await add_title(user_id, channel.guild.id, "👑 Vua Câu Cá 👑")
                title_earned = True
                print(f"[TITLE] {username} earned 'Vua Câu Cá' title!")
        
        # Build embed with item summary
        total_catches = num_fish + trash_count + chest_count
        
        # Create summary text for title
        summary_parts = []
        for key, qty in fish_only_items.items():
            fish = ALL_FISH[key]
            summary_parts.append(f"{qty} {fish['name']}")
        if chest_count > 0:
            summary_parts.append(f"{chest_count} Rương")
        
        summary_text = " và ".join(summary_parts) if summary_parts else "Rác"
        title = f"🎣 {username} Câu Được {summary_text}"
        
        if num_fish > 2:
            title = f"🎣 THỜI TỚI! {username} Bắt {num_fish} Con Cá! 🎉"
        
        # Add title-earned message if applicable
        if title_earned:
            title = f"🎣 {title}\n👑 **DANH HIỆU: VUA CÂU CÁ ĐƯỢC MỞ KHÓA!** 👑"
        
        # Build description with broken rod warning if needed
        desc_parts = ["\n".join(fish_display) if fish_display else "Không có gì"]
        if is_broken_rod:
            desc_parts.append("\n⚠️ **CẢNH BÁO: Cần câu gãy!** (Chỉ 1% cá hiếm, 1 item/lần, không rương)")
        
        embed = discord.Embed(
            title=title,
            description="".join(desc_parts),
            color=discord.Color.red() if is_broken_rod else (discord.Color.gold() if title_earned else (discord.Color.blue() if total_catches == 1 else discord.Color.gold()))
        )
        
        if title_earned:
            embed.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã bắt được **tất cả các loại cá**!\nChúc mừng bạn trở thành **Vua Câu Cá**! 🎉\nXem `/suutapca` để xác nhận!",
                inline=False
            )
        
        # *** UPDATE DURABILITY AFTER FISHING ***
        rod_durability = max(0, rod_durability - durability_loss)
        await self.update_rod_data(user_id, rod_durability)
        
        durability_status = f"🛡️ Độ bền: {rod_durability}/{rod_config['durability']}"
        embed.set_footer(text=f"Tổng câu được: {total_catches} vật{boost_text} | {durability_status}")
        
        # Create view with sell button if there are fish to sell
        view = None
        if fish_only_items:
            view = FishSellView(self, user_id, fish_only_items, channel.guild.id)
            print(f"[FISHING] Created sell button for {username} with {len(fish_only_items)} fish types")
        else:
            print(f"[FISHING] No fish to sell, button not shown")
        
        await casting_msg.edit(content="", embed=embed, view=view)
        print(f"[FISHING] [RESULT_POST] {username} (user_id={user_id}) action=display_result")
    
    
    @app_commands.command(name="banca", description="Bán cá - dùng /banca cá_rô hoặc /banca cá_rô, cá_chép")
    @app_commands.describe(fish_types="Loại cá (cá_rô, cá_chép, cá_koi) - phân cách bằng dấu phẩy để bán nhiều loại")
    async def sell_fish_slash(self, interaction: discord.Interaction, fish_types: str = None):
        """Sell selected fish via slash command"""
        await self._sell_fish_action(interaction, fish_types)
    
    @commands.command(name="banca", description="Bán cá - dùng !banca cá_rô hoặc !banca cá_rô, cá_chép")
    async def sell_fish_prefix(self, ctx, *, fish_types: str = None):
        """Sell selected fish via prefix command"""
        await self._sell_fish_action(ctx, fish_types)
    
    async def _sell_fish_action(self, ctx_or_interaction, fish_types: str = None):
        """Sell all fish or specific types logic with RANDOM EVENTS"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get username
        username = ctx.user.name if is_slash else ctx.author.name
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Filter fish items by type (exclude rod materials from selling)
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH and k != "rod_material"}
        
        # ==================== CHECK FOR LEGENDARY FISH ====================
        # Remove legendary fish from sellable items
        legendary_fish_in_inventory = {k: v for k, v in fish_items.items() if k in LEGENDARY_FISH_KEYS}
        if legendary_fish_in_inventory:
            # Show warning that legendary fish cannot be sold
            legend_names = ", ".join([ALL_FISH[k]['name'] for k in legendary_fish_in_inventory.keys()])
            msg = f"❌ **CÁ HỮU HẠNG KHÔNG ĐƯỢC BÁN!** 🏆\n\n"
            msg += f"Bạn có: {legend_names}\n\n"
            msg += "Các loại cá huyền thoại này là biểu tượng của danh tiếng của bạn. Chúng không được phép bán!\n\n"
            msg += "💎 Hãy xem `/huyenthoai` để xem Bảng Vàng những con cá huyền thoại!"
            
            if is_slash:
                await ctx.followup.send(msg, ephemeral=False)
            else:
                await ctx.send(msg)
            
            # Remove legendary fish from sellable list
            fish_items = {k: v for k, v in fish_items.items() if k not in LEGENDARY_FISH_KEYS}
            
            if not fish_items:
                return  # No other fish to sell
        
        if not fish_items:
            msg = "❌ Bạn không có cá nào để bán!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Parse fish_types if specified
        selected_fish = None
        if fish_types:
            requested = [f.strip().lower().replace(" ", "_") for f in fish_types.split(",")]
            selected_fish = {k: v for k, v in fish_items.items() if k in requested}
            
            if not selected_fish:
                available = ", ".join(fish_items.keys())
                msg = f"❌ Không tìm thấy cá!\nCá bạn có: {available}"
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
        else:
            selected_fish = fish_items
        
        # 1. Tính tổng tiền gốc
        base_total = 0
        for fish_key, quantity in selected_fish.items():
            fish_info = ALL_FISH.get(fish_key)
            if fish_info:
                base_price = fish_info['sell_price']
                base_total += base_price * quantity
        
        # 2. Xử lý sự kiện bán hàng (Sell Event)
        final_total = base_total
        event_msg = ""
        event_name = ""
        event_color = discord.Color.green()  # Mặc định màu xanh lá
        triggered_event = None
        
        # Roll event
        rand = random.random()
        current_chance = 0
        
        # Debug log
        print(f"[SELL EVENT DEBUG] User: {username}, base_total: {base_total}, random value: {rand:.4f}")
        
        for ev_key, ev_data in SELL_EVENTS.items():
            current_chance += ev_data["chance"]
            print(f"[FISHING] [SELL_EVENT_DEBUG] Checking event={ev_key} chance={ev_data['chance']:.4f} cumulative={current_chance:.4f}")
            if rand < current_chance:
                triggered_event = ev_key
                print(f"[FISHING] [SELL_EVENT_DEBUG] TRIGGERED event={triggered_event}")
                break
        
        if not triggered_event:
            print(f"[FISHING] [SELL_EVENT_DEBUG] NO_EVENT cumulative_chance={current_chance:.4f}")
        
        # Apply event logic
        special_rewards = []
        if triggered_event:
            ev_data = SELL_EVENTS[triggered_event]
            event_name = ev_data["name"]
            
            # Tính toán tiền sau sự kiện
            # Công thức: (Gốc * Multiplier) + Flat Bonus
            final_total = int(base_total * ev_data["mul"]) + ev_data["flat"]
            
            # Cho phép âm tiền nếu sự kiện xấu quá nghiêm trọng
            
            diff = final_total - base_total
            sign = "+" if diff >= 0 else ""
            
            # Xử lý special effects (vật phẩm thưởng)
            if "special" in ev_data:
                special_type = ev_data["special"]
                
                if special_type == "chest":
                    await self.add_inventory_item(user_id, "treasure_chest", "tool")
                    special_rewards.append("🎁 +1 Rương Kho Báu")
                
                elif special_type == "worm":
                    await self.add_inventory_item(user_id, "worm", "bait")
                    special_rewards.append("🪱 +5 Mồi Câu")
                
                elif special_type == "pearl":
                    await self.add_inventory_item(user_id, "pearl", "tool")
                    special_rewards.append("🔮 +1 Ngọc Trai")
                
                elif special_type == "durability":
                    # Thêm độ bền cho cần câu hiện tại
                    user_rod_level, user_rod_durability = await self.get_rod_data(user_id)
                    max_durability = ROD_LEVELS[user_rod_level]["durability"]
                    new_durability = min(max_durability, user_rod_durability + 10)
                    await self.update_rod_data(user_id, new_durability)
                    special_rewards.append("🛠️ +10 Độ Bền Cần Câu")
                
                elif special_type == "rod":
                    await self.add_inventory_item(user_id, "rod_material", "material")
                    special_rewards.append("🎣 +1 Vật Liệu Nâng Cấp Cần")
                
                elif special_type == "lottery":
                    if random.random() < 0.1:  # 10% win chance
                        lottery_reward = 500
                        await add_seeds(user_id, lottery_reward)
                        final_total += lottery_reward
                        special_rewards.append(f"🎉 **TRÚNG SỐ! +{lottery_reward} Hạt!**")
                    else:
                        special_rewards.append("❌ Vé số không trúng")
            
            # Formatting message
            if ev_data["type"] == "good":
                event_color = discord.Color.gold()
                event_msg = f"\n🌟 **SỰ KIỆN: {event_name}**\n_{SELL_MESSAGES[triggered_event]}_\n👉 **Biến động:** {sign}{diff} Hạt"
            else:
                event_color = discord.Color.orange()
                event_msg = f"\n⚠️ **SỰ CỐ: {event_name}**\n_{SELL_MESSAGES[triggered_event]}_\n👉 **Thiệt hại:** {diff} Hạt"
                
            print(f"[FISHING] [SELL_EVENT] {ctx.user.name if is_slash else ctx.author.name} (user_id={ctx.user.id if is_slash else ctx.author.id}) event={triggered_event} seed_change={final_total - base_total} fish_count={len(selected_fish)}")

        # Remove items & Add money
        for fish_key in selected_fish.keys():
            await remove_item(user_id, fish_key, selected_fish[fish_key])
        
        await add_seeds(user_id, final_total)
        
        # 4. Display sell event notification FIRST (if triggered)
        if triggered_event:
            if SELL_EVENTS[triggered_event]["type"] == "good":
                title = f"🌟 PHƯỚC LÀNH - {username}!"
                event_embed_color = discord.Color.gold()
            else:
                title = f"⚠️ KIẾP NẠN - {username}!"
                event_embed_color = discord.Color.orange()
            
            diff = final_total - base_total
            sign = "+" if diff >= 0 else ""
            event_detail = f"{SELL_MESSAGES[triggered_event]}\n\n💰 **{event_name}**"
            
            event_embed = discord.Embed(
                title=title,
                description=event_detail,
                color=event_embed_color
            )
            event_embed.add_field(
                name="📊 Ảnh hưởng giá bán",
                value=f"Gốc: {base_total} Hạt\n{sign}{diff} Hạt\n**= {final_total} Hạt**",
                inline=False
            )
            
            # Add special rewards if any
            if special_rewards:
                event_embed.add_field(
                    name="🎁 Phần Thưởng Đặc Biệt",
                    value="\n".join(special_rewards),
                    inline=False
                )
            
            if is_slash:
                await ctx.followup.send(content=f"<@{user_id}>", embed=event_embed, ephemeral=False)
            else:
                await ctx.send(content=f"<@{user_id}>", embed=event_embed)
        
        # 5. Display main sell result embed
        fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in selected_fish.items()])
        
        embed = discord.Embed(
            title=f"💰 **{username}** bán {sum(selected_fish.values())} con cá",
            description=f"{fish_summary}\n\n💵 **Tổng nhận:** {final_total} Hạt",
            color=discord.Color.green()
        )
        
        # Check achievement "millionaire" (Tích lũy tiền)
        if hasattr(self, "update_user_stat"):
            total_earned = await self.update_user_stat(user_id, "coins_earned", final_total)
            if total_earned >= 100000:
                await self.check_achievement(user_id, "millionaire", ctx.channel, ctx.guild.id if hasattr(ctx, 'guild') else ctx_or_interaction.guild.id)

        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=False)
        else:
            await ctx.send(embed=embed)
    
    @app_commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_slash(self, interaction: discord.Interaction):
        """Open chest via slash command"""
        await self._open_chest_action(interaction)
    
    @commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_prefix(self, ctx):
        """Open chest via prefix command"""
        await self._open_chest_action(ctx)
    
    async def _open_chest_action(self, ctx_or_interaction):
        """Open treasure chest logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            user_name = ctx_or_interaction.user.name
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            user_name = ctx_or_interaction.author.name
            ctx = ctx_or_interaction
        
        # Check if user has chest
        inventory = await get_inventory(user_id)
        if inventory.get("treasure_chest", 0) <= 0:
            msg = "❌ Bạn không có Rương Kho Báu!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove chest from inventory
        await remove_item(user_id, "treasure_chest", 1)
        
        # Roll loot
        items = list(CHEST_LOOT.keys())
        weights = list(CHEST_LOOT.values())
        loot_type = random.choices(items, weights=weights, k=1)[0]
        
        # Process loot
        if loot_type == "fertilizer":
            await self.add_inventory_item(user_id, "fertilizer", "tool")
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description="**🌾 Phân Bón** (Dùng `/bonphan` để nuôi cây)",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"👤 {user_name}")
        
        elif loot_type == "puzzle_piece":
            pieces = ["puzzle_a", "puzzle_b", "puzzle_c", "puzzle_d"]
            piece = random.choice(pieces)
            await self.add_inventory_item(user_id, piece, "tool")
            piece_display = piece.split("_")[1].upper()
            
            # Check if user now has all 4 pieces (A, B, C, D)
            inventory = await get_inventory(user_id)
            has_all_pieces = all(inventory.get(f"puzzle_{p}", 0) > 0 for p in ["a", "b", "c", "d"])
            
            if has_all_pieces:
                # Remove all 4 pieces from inventory
                await remove_item(user_id, "puzzle_a", 1)
                await remove_item(user_id, "puzzle_b", 1)
                await remove_item(user_id, "puzzle_c", 1)
                await remove_item(user_id, "puzzle_d", 1)
                
                # Award random 5000-10000 seeds
                reward = random.randint(5000, 10000)
                await add_seeds(user_id, reward)
                
                embed = discord.Embed(
                    title="🎁 Rương Kho Báu",
                    description=f"**🧩 Mảnh Ghép {piece_display}**\n\n🎉 **ĐỦ 4 MẢNH - TỰ ĐỘNG GHÉP!**\n💰 **Bạn nhận được {reward} Hạt!**",
                    color=discord.Color.gold()
                )
                embed.set_footer(text=f"👤 {user_name}")
            else:
                embed = discord.Embed(
                    title="🎁 Rương Kho Báu",
                    description=f"**🧩 Mảnh Ghép {piece_display}** (Gom đủ 4 mảnh A-B-C-D để đổi quà siêu to!)",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"👤 {user_name}")
        
        elif loot_type == "coin_pouch":
            coins = random.randint(100, 200)
            await add_seeds(user_id, coins)
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**💰 Túi Hạt** - Bạn nhận được **{coins} Hạt**!",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"👤 {user_name}")
        
        else:  # gift_random
            gift = random.choice(GIFT_ITEMS)
            await self.add_inventory_item(user_id, gift, "gift")
            gift_names = {"cafe": "☕ Cà Phê", "flower": "🌹 Hoa", "ring": "💍 Nhẫn", 
                         "gift": "🎁 Quà", "chocolate": "🍫 Sô Cô La", "card": "💌 Thiệp"}
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=f"**{gift_names[gift]}** (Dùng `/tangqua` để tặng cho ai đó)",
                color=discord.Color.magenta()
            )
            embed.set_footer(text=f"👤 {user_name}")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    # ==================== CRAFT/RECYCLE ====================
    
    @app_commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    @app_commands.describe(
        action="Để trống để xem thông tin, hoặc 'phan' để tạo phân bón"
    )
    async def recycle_trash_slash(self, interaction: discord.Interaction, action: str = None):
        """Recycle trash via slash command"""
        await self._recycle_trash_action(interaction, action)
    
    @commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    async def recycle_trash_prefix(self, ctx, action: str = None):
        """Recycle trash via prefix command"""
        await self._recycle_trash_action(ctx, action)
    
    async def _recycle_trash_action(self, ctx_or_interaction, action: str = None):
        """Recycle trash logic - auto converts 10 trash → 1 fertilizer (recycle ALL trash)"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=True)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Count all trash items
        trash_count = sum(qty for key, qty in inventory.items() if key.startswith("trash_"))
        
        if trash_count == 0:
            msg = "❌ Bạn không có rác nào để tái chế!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Check if user has enough trash (at least 10)
        if trash_count < 10:
            msg = f"❌ Bạn cần 10 rác để tạo phân bón, hiện có {trash_count}"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Calculate how many fertilizers can be created
        fertilizer_count = trash_count // 10
        trash_used = fertilizer_count * 10
        trash_remaining = trash_count - trash_used
        
        # Remove all trash items (in groups of 10)
        trash_removed = 0
        for key in list(inventory.keys()):
            if key.startswith("trash_") and trash_removed < trash_used:
                qty_to_remove = min(inventory[key], trash_used - trash_removed)
                await remove_item(user_id, key, qty_to_remove)
                trash_removed += qty_to_remove
        
        # Add fertilizers (multiply the count)
        for _ in range(fertilizer_count):
            await self.add_inventory_item(user_id, "fertilizer", "tool")
        
        embed = discord.Embed(
            title="✅ Tái Chế Thành Công",
            description=f"🗑️ {trash_used} Rác → 🌱 {fertilizer_count} Phân Bón",
            color=discord.Color.green()
        )
        if trash_remaining > 0:
            embed.add_field(name="Rác còn lại", value=f"{trash_remaining} (cần 10 để tạo 1 phân)", inline=False)
        
        username = ctx.user.name if is_slash else ctx.author.name
        print(f"[RECYCLE] {username} recycled {trash_used} trash → {fertilizer_count} fertilizer")
        
        if is_slash:
            await ctx.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    
    # ==================== ROD UPGRADE ====================
    
    @app_commands.command(name="nangcap", description="Nâng cấp cần câu (Giảm hồi chiêu, tăng bền, tăng may mắn)")
    async def upgrade_rod_slash(self, interaction: discord.Interaction):
        """Upgrade rod via slash command"""
        await self._upgrade_rod_action(interaction)
    
    @commands.command(name="nangcap", description="Nâng cấp cần câu")
    async def upgrade_rod_prefix(self, ctx):
        """Upgrade rod via prefix command"""
        await self._upgrade_rod_action(ctx)
    
    async def _upgrade_rod_action(self, ctx_or_interaction):
        """Upgrade rod logic - can use seeds or rod_material"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # Get current rod
        cur_lvl, cur_durability = await get_rod_data(user_id)
        
        if cur_lvl >= 5:
            msg = "🌟 Cần câu của bạn đã đạt cấp tối đa **(Poseidon)**!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        next_lvl = cur_lvl + 1
        rod_info = ROD_LEVELS[next_lvl]
        cost = rod_info["cost"]
        
        # Check if user has rod_material
        inventory = await get_inventory(user_id)
        has_material = inventory.get("rod_material", 0) > 0
        
        if has_material:
            # Use rod_material instead of seeds
            await remove_item(user_id, "rod_material", 1)
            upgrade_method = "Vật Liệu"
            cost_display = "1 Vật Liệu Nâng Cấp Cần"
            use_material = True
        else:
            # Check balance for seeds payment
            balance = await get_user_balance(user_id)
            if balance < cost:
                msg = f"❌ Bạn cần **{cost:,} Hạt** hoặc **1 Vật Liệu Nâng Cấp Cần** để nâng lên **{rod_info['name']}**!\n\nHiện có: **{balance:,} Hạt**"
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
            
            # Deduct seeds
            await add_seeds(user_id, -cost)
            upgrade_method = "Hạt"
            cost_display = f"{cost:,} Hạt"
            use_material = False
        
        # Upgrade rod: restore full durability
        await update_rod_data(user_id, rod_info["durability"], next_lvl)
        
        # Check rod_tycoon achievement if level 5
        if next_lvl == 5:
            guild_id = ctx_or_interaction.guild.id if hasattr(ctx_or_interaction, 'guild') else ctx_or_interaction.guild.id
            await self.check_achievement(user_id, "rod_tycoon", ctx_or_interaction.channel, guild_id)
        
        # Build response embed
        embed = discord.Embed(
            title="✅ Nâng Cấp Cần Câu Thành Công!",
            description=f"**{rod_info['emoji']} {rod_info['name']}** (Cấp {next_lvl}/5)",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚡ Thời Gian Chờ", value=f"**{rod_info['cd']}s** (giảm từ {ROD_LEVELS[cur_lvl]['cd']}s)", inline=True)
        embed.add_field(name="🛡️ Độ Bền", value=f"**{rod_info['durability']}** (tăng từ {ROD_LEVELS[cur_lvl]['durability']})", inline=True)
        embed.add_field(name="🍀 May Mắn", value=f"**+{int(rod_info['luck']*100)}%** Cá Hiếm" if rod_info['luck'] > 0 else "**Không thay đổi**", inline=True)
        embed.add_field(name="💰 Chi Phí", value=f"**{cost_display}** ({upgrade_method})", inline=False)
        embed.set_footer(text="Độ bền đã được hồi phục hoàn toàn!")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
        
        print(f"[ROD] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} upgraded rod to level {next_lvl} using {upgrade_method}")
    
    @app_commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây (tăng 50-100 điểm)")
    async def use_fertilizer_slash(self, interaction: discord.Interaction):
        """Use fertilizer via slash command"""
        await self._use_fertilizer_action(interaction)
    
    @commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây")
    async def use_fertilizer_prefix(self, ctx):
        """Use fertilizer via prefix command"""
        await self._use_fertilizer_action(ctx)
    
    async def _use_fertilizer_action(self, ctx_or_interaction):
        """Use fertilizer logic"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        guild_id = ctx_or_interaction.guild.id
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            guild_id = ctx_or_interaction.guild.id
            ctx = ctx_or_interaction
        
        # Check if user has fertilizer
        inventory = await get_inventory(user_id)
        if inventory.get("fertilizer", 0) <= 0:
            msg = "❌ Bạn không có Phân Bón!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove fertilizer
        await remove_item(user_id, "fertilizer", 1)
        
        # Add to tree
        boost_amount = random.randint(50, 100)
        
        try:
            # Get current tree state
            tree_cog = self.bot.get_cog("CommunityCog")
            if not tree_cog:
                raise Exception("CommunityCog not found!")
            
            # Get current tree data
            lvl, prog, total, season, tree_channel_id, _ = await tree_cog.get_tree_data(guild_id)
            
            # Calculate new progress and potential level-up
            level_reqs = tree_cog.get_level_reqs(season)
            req = level_reqs.get(lvl + 1, level_reqs[6])
            new_progress = prog + boost_amount
            new_total = total + boost_amount
            new_level = lvl
            leveled_up = False
            
            # Handle level ups
            while new_progress >= req and new_level < 6:
                new_level += 1
                new_progress = new_progress - req
                leveled_up = True
                req = level_reqs.get(new_level + 1, level_reqs[6])
            
            # Update tree in database
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE server_tree SET current_level = ?, current_progress = ?, total_contributed = ? WHERE guild_id = ?",
                    (new_level, new_progress, new_total, guild_id)
                )
                await db.commit()
            
            # Build response embed
            embed = discord.Embed(
                title="🌾 Phân Bón Hiệu Quả!",
                description=f"**+{boost_amount}** điểm cho Cây Server!",
                color=discord.Color.green()
            )
            
            # Add level-up notification if applicable
            if leveled_up:
                embed.add_field(
                    name="🌳 CÂY ĐÃ LÊN CẤP!",
                    value=f"**{TREE_NAMES[new_level]}** (Cấp {new_level}/6)",
                    inline=False
                )
                embed.color = discord.Color.gold()
            else:
                embed.add_field(
                    name="Tiến độ",
                    value=f"**{int((new_progress / req) * 100) if req > 0 else 0}%** ({new_progress}/{req})",
                    inline=False
                )
            
            print(f"[FERTILIZER] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} used fertilizer: +{boost_amount} (Tree Level {new_level})")
            
            # Update tree embed in the designated channel
            if tree_channel_id:
                try:
                    print(f"[FERTILIZER] Updating tree message in channel {tree_channel_id}")
                    await tree_cog.update_or_create_pin_message(guild_id, tree_channel_id)
                    print(f"[FERTILIZER] ✅ Tree embed updated successfully")
                    
                    # Send notification embed to tree channel
                    tree_channel = self.bot.get_channel(tree_channel_id)
                    if tree_channel:
                        user_name = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                        notification_embed = discord.Embed(
                            title="🌾 Phân Bón Được Sử Dụng!",
                            description=f"**{user_name}** đã dùng Phân Bón",
                            color=discord.Color.green()
                        )
                        notification_embed.add_field(
                            name="📈 Mức tăng",
                            value=f"**+{boost_amount}** điểm",
                            inline=False
                        )
                        
                        if leveled_up:
                            notification_embed.add_field(
                                name="🎉 Cây đã lên cấp!",
                                value=f"**{TREE_NAMES[new_level]}** (Cấp {new_level}/6)",
                                inline=False
                            )
                            notification_embed.color = discord.Color.gold()
                        else:
                            notification_embed.add_field(
                                name="📊 Tiến độ",
                                value=f"**{int((new_progress / req) * 100) if req > 0 else 0}%** ({new_progress}/{req})",
                                inline=False
                            )
                        
                        await tree_channel.send(embed=notification_embed)
                except Exception as e:
                    print(f"[FERTILIZER] ❌ Failed to update tree embed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[FERTILIZER] ⚠️ No tree channel configured for guild {guild_id}")
        
        except Exception as e:
            print(f"[FERTILIZER] Error: {e}")
            embed = discord.Embed(
                title="❌ Lỗi",
                description=f"Không thể cộng điểm: {e}",
                color=discord.Color.red()
            )
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    # ==================== COLLECTION BOOK ====================
    
    @app_commands.command(name="suutapca", description="Xem Bộ Sưu Tập Cá - Câu Đủ Tất Cả Để Thành Vua Câu Cá!")
    async def view_collection_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """View fish collection via slash command"""
        target_user = user or interaction.user
        await self._view_collection_action(interaction, target_user.id, target_user.name)
    
    @commands.command(name="suutapca", description="Xem Bộ Sưu Tập Cá")
    async def view_collection_prefix(self, ctx, user: discord.User = None):
        """View fish collection via prefix command"""
        target_user = user or ctx.author
        await self._view_collection_action(ctx, target_user.id, target_user.name)
    
    async def _view_collection_action(self, ctx_or_interaction, user_id: int, username: str):
        """View collection logic with pagination"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            ctx = ctx_or_interaction
            guild_id = ctx_or_interaction.guild_id
        else:
            ctx = ctx_or_interaction
            guild_id = ctx_or_interaction.guild.id
        
        # Get collection
        collection = await get_collection(user_id)
        
        # Get legendary fish caught
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT legendary_fish FROM economy_users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        legendary_caught = json.loads(row[0])
                    else:
                        legendary_caught = []
        except:
            legendary_caught = []
        
        # Separate common and rare
        common_caught = set()
        rare_caught = set()
        
        for fish_key in collection.keys():
            if fish_key in RARE_FISH_KEYS:
                rare_caught.add(fish_key)
            elif fish_key in COMMON_FISH_KEYS:
                common_caught.add(fish_key)
        
        # Get total count (including legendary fish)
        total_all_fish = len(COMMON_FISH_KEYS + RARE_FISH_KEYS) + len(LEGENDARY_FISH)
        total_caught = len(common_caught) + len(rare_caught) + len(legendary_caught)
        completion_percent = int((total_caught / total_all_fish) * 100)
        
        # Check if completed (all common + rare + legendary)
        is_complete = await check_collection_complete(user_id) and len(legendary_caught) == len(LEGENDARY_FISH)
        
        # Get current title
        current_title = await self.get_title(user_id, guild_id)
        
        # Build common fish embed (Page 1)
        embed_common = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_fish}** ({completion_percent}%)\n📄 **Trang 1/2 - Cá Thường**",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        if current_title:
            embed_common.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add common fish section (split into multiple fields to avoid length limit)
        common_display = []
        for fish in COMMON_FISH:
            emoji = "✅" if fish['key'] in common_caught else "❌"
            common_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        # Split common fish into 2 columns if too many
        if len(common_display) > 30:
            mid = len(common_display) // 2
            col1 = "\n".join(common_display[:mid])
            col2 = "\n".join(common_display[mid:])
            
            embed_common.add_field(
                name=f"🐠 Cá Thường ({len(common_caught)}/{len(COMMON_FISH)}) - Phần 1",
                value=col1 if col1 else "Không có",
                inline=True
            )
            embed_common.add_field(
                name="Phần 2",
                value=col2 if col2 else "Không có",
                inline=True
            )
        else:
            embed_common.add_field(
                name=f"🐠 Cá Thường ({len(common_caught)}/{len(COMMON_FISH)})",
                value="\n".join(common_display) if common_display else "Không có",
                inline=False
            )
        
        embed_common.set_footer(text="Bấm nút → để xem cá hiếm")
        
        # Build rare fish embed (Page 2)
        embed_rare = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_fish}** ({completion_percent}%)\n📄 **Trang 2/2 - Cá Hiếm & Huyền Thoại**",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        if current_title:
            embed_rare.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add rare fish section (split into multiple fields to avoid length limit)
        rare_display = []
        for fish in RARE_FISH:
            emoji = "✅" if fish['key'] in rare_caught else "❌"
            rare_display.append(f"{emoji} {fish['emoji']} {fish['name']}")
        
        # Split rare fish into 2 columns if too many
        if len(rare_display) > 20:
            mid = len(rare_display) // 2
            col1 = "\n".join(rare_display[:mid])
            col2 = "\n".join(rare_display[mid:])
            
            embed_rare.add_field(
                name=f"✨ Cá Hiếm ({len(rare_caught)}/{len(RARE_FISH)}) - Phần 1",
                value=col1 if col1 else "Không có",
                inline=True
            )
            embed_rare.add_field(
                name="Phần 2",
                value=col2 if col2 else "Không có",
                inline=True
            )
        else:
            embed_rare.add_field(
                name=f"✨ Cá Hiếm ({len(rare_caught)}/{len(RARE_FISH)})",
                value="\n".join(rare_display) if rare_display else "Không có",
                inline=False
            )
        
        # Add legendary fish section (huyền thoại)
        legendary_display = []
        caught_count = 0  # Track caught legendary fish count
        for legendary_fish in LEGENDARY_FISH:
            fish_key = legendary_fish['key']
            if fish_key in legendary_caught:
                # Caught: show name with ✅
                legendary_display.append(f"✅ {legendary_fish['emoji']} {legendary_fish['name']}")
                caught_count += 1
            else:
                # Not caught: only show ???? for first uncaught, hide others
                if caught_count == 0:
                    # No legendary caught yet, show one ????
                    legendary_display.append(f"❓ 🌟 ????")
                    break  # Only show one ????
                else:
                    # Already caught some, don't show remaining uncaught
                    break
        
        embed_rare.add_field(
            name=f"🌟 Cá Huyền Thoại ({len(legendary_caught)}/{len(LEGENDARY_FISH)})",
            value="\n".join(legendary_display) if legendary_display else "❓ 🌟 ????",
            inline=False
        )
        
        # Add completion message
        if is_complete:
            embed_rare.add_field(
                name="🏆 HOÀN THÀNH!",
                value="Bạn đã trở thành **👑 VUA CÂU CÁ 👑**!\nCảm ơn sự kiên trì của bạn! 🎉",
                inline=False
            )
        else:
            missing_count = total_all_fish - total_caught
            embed_rare.add_field(
                name="📝 Còn Lại",
                value=f"Bạn còn cần bắt **{missing_count}** loại cá nữa để trở thành Vua Câu Cá! 💪",
                inline=False
            )
        
        embed_rare.set_footer(text="Bấm nút ← để xem cá thường • Mỗi lần bắt một loại cá mới, nó sẽ được thêm vào sưu tập!")
        
        # Create pagination view
        class CollectionPaginationView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
                self.current_page = 0  # 0 = common, 1 = rare
                self.message = None
            
            @discord.ui.button(label="← Cá Thường", style=discord.ButtonStyle.primary, custom_id="collection_prev")
            async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                """Go to previous page (common fish)"""
                self.current_page = 0
                await self.update_message(interaction)
            
            @discord.ui.button(label="Cá Hiếm →", style=discord.ButtonStyle.primary, custom_id="collection_next")
            async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                """Go to next page (rare fish)"""
                self.current_page = 1
                await self.update_message(interaction)
            
            async def update_message(self, interaction: discord.Interaction):
                """Update the collection message with the current page"""
                if self.message:
                    if self.current_page == 0:
                        await interaction.response.edit_message(embed=embed_common, view=self)
                    else:
                        await interaction.response.edit_message(embed=embed_rare, view=self)
    
        # Send initial embed (common fish)
        view = CollectionPaginationView()
        embed = embed_common
        message = await ctx.channel.send(embed=embed, view=view)
        view.message = message
        
        # Wait for interactions
        await view.wait()
    
    # ==================== LEGENDARY FISH HALL OF FAME ====================
    
    @app_commands.command(name="huyenthoai", description="🏆 Xem Bảng Vàng Huyền Thoại")
    async def legendary_hall_of_fame(self, interaction: discord.Interaction):
        """Show the legendary fish hall of fame with detailed pages."""
        await interaction.response.defer(ephemeral=False)
        await self._legendary_hall_of_fame_action(interaction, is_slash=True)
    
    @commands.command(name="huyenthoai", description="Xem Bảng Vàng Huyền Thoại")
    async def legendary_hall_prefix(self, ctx):
        """Show the legendary fish hall of fame (prefix command)."""
        await self._legendary_hall_of_fame_action(ctx, is_slash=False)
    
    async def _legendary_hall_of_fame_action(self, ctx_or_interaction, is_slash: bool):
        """Hall of fame logic with pagination."""
        import json
        
        channel = ctx_or_interaction.channel
        guild_id = ctx_or_interaction.guild.id
        # Handle both Interaction (slash) and Context (prefix) objects
        client = ctx_or_interaction.client if is_slash else ctx_or_interaction.bot
        
        # Fetch all legendary catches
        legendary_catches = {}
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT user_id, legendary_fish FROM economy_users WHERE legendary_fish_count > 0"
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    for user_id, legendary_json in rows:
                        if legendary_json:
                            try:
                                legendary_list = json.loads(legendary_json)
                                for fish_key in legendary_list:
                                    if fish_key not in legendary_catches:
                                        legendary_catches[fish_key] = []
                                    
                                    try:
                                        user = await client.fetch_user(user_id)
                                        legendary_catches[fish_key].append({
                                            "user_id": user_id,
                                            "username": user.name,
                                            "avatar_url": user.avatar.url if user.avatar else None
                                        })
                                    except:
                                        legendary_catches[fish_key].append({
                                            "user_id": user_id,
                                            "username": f"User {user_id}",
                                            "avatar_url": None
                                        })
                            except:
                                pass
        except Exception as e:
            print(f"[LEGENDARY] Error fetching hall of fame: {e}")
        
        # Filter legendary fish that have been caught
        caught_legendaries = [(fish, legendary_catches[fish['key']]) 
                              for fish in LEGENDARY_FISH 
                              if fish['key'] in legendary_catches]
        
        # If no legendaries caught, show overview with all as "❓"
        if not caught_legendaries:
            embed = discord.Embed(
                title="🏆 BẢNG VÀNG HUYỀN THOẠI 🏆",
                description="🌟 Những người anh hùng đầu tiên chinh phục các cá huyền thoại:\n",
                color=discord.Color.gold()
            )
            
            for legendary_fish in LEGENDARY_FISH:
                emoji = legendary_fish['emoji']
                value = "❓ Chưa ai bắt được...\n🎯 Bạn có thể là người đầu tiên!"
                embed.add_field(name=f"{emoji} ❓", value=value, inline=False)
            
            embed.set_footer(text="🎣 Câu cá và trở thành một phần của lịch sử!")
            
            if is_slash:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Create pagination view for caught legendaries
        class LegendaryHallView(discord.ui.View):
            def __init__(self, caught_list, current_index=0):
                super().__init__(timeout=300)
                self.caught_list = caught_list
                self.current_index = current_index
                self.message = None
                self.update_buttons()
            
            def update_buttons(self):
                self.prev_button.disabled = self.current_index == 0
                self.next_button.disabled = self.current_index == len(self.caught_list) - 1
            
            @discord.ui.button(label="← Cá Trước", style=discord.ButtonStyle.primary)
            async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_index > 0:
                    self.current_index -= 1
                    self.update_buttons()
                    await self.update_message(interaction)
            
            @discord.ui.button(label="Cá Tiếp →", style=discord.ButtonStyle.primary)
            async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_index < len(self.caught_list) - 1:
                    self.current_index += 1
                    self.update_buttons()
                    await self.update_message(interaction)
            
            async def update_message(self, interaction: discord.Interaction):
                fish, catchers = self.caught_list[self.current_index]
                embed = self.build_embed(fish, catchers)
                await interaction.response.edit_message(embed=embed, view=self)
            
            def build_embed(self, fish, catchers):
                emoji = fish['emoji']
                name = fish['name']
                desc = fish.get('description', '')
                price = fish.get('sell_price', 0)
                
                catcher_text = "\n".join([f"⭐ **{c['username']}**" for c in catchers])
                
                embed = discord.Embed(
                    title=f"🏆 {emoji} {name}",
                    description=desc or "Cá huyền thoại bí ẩn",
                    color=discord.Color.gold()
                )
                
                embed.add_field(name="💎 Giá Bán", value=f"{price} Hạt", inline=True)
                embed.add_field(name="📊 Số Người Bắt", value=f"{len(catchers)}", inline=True)
                embed.add_field(name="🏅 Những Người Chinh Phục", value=catcher_text, inline=False)
                
                if fish.get('image_url'):
                    embed.set_image(url=fish['image_url'])
                
                page_num = self.current_index + 1
                total_pages = len(self.caught_list)
                embed.set_footer(text=f"Trang {page_num}/{total_pages} • 🎣 Câu cá và trở thành một phần của lịch sử!")
                
                return embed
        
        # Send first page
        view = LegendaryHallView(caught_legendaries)
        first_fish, first_catchers = caught_legendaries[0]
        embed = view.build_embed(first_fish, first_catchers)
        
        if is_slash:
            message = await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            message = await ctx_or_interaction.send(embed=embed, view=view)
        
        view.message = message
    
    # ==================== DEBUG COMMANDS ====================
    
    @commands.command(name="legendarytrigger", description="TEST: Trigger legendary fish encounter (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def debug_legendary_trigger(self, ctx, fish_key: str = None):
        """Debug command to trigger legendary fish encounter"""
        user_id = ctx.author.id
        channel = ctx.channel
        guild_id = ctx.guild.id
        
        # Select a legendary fish (random or specified)
        if fish_key:
            # Find legendary fish by key
            legendary_fish = None
            for fish in LEGENDARY_FISH:
                if fish['key'].lower() == fish_key.lower():
                    legendary_fish = fish
                    break
            
            if not legendary_fish:
                await ctx.send(f"❌ Cá huyền thoại '{fish_key}' không tồn tại!\n\nDanh sách: {', '.join([f['key'] for f in LEGENDARY_FISH])}")
                return
        else:
            # Random legendary fish
            legendary_fish = random.choice(LEGENDARY_FISH)
        
        # Get rod data
        rod_level, rod_durability = await get_rod_data(user_id)
        rod_config = ROD_LEVELS.get(rod_level, ROD_LEVELS[1])
        
        # Create legendary fish embed (same as normal encounter)
        legendary_embed = discord.Embed(
            title="⚠️ CẢNH BÁO: DÂY CÂU CĂNG CỰC ĐỘ!",
            description=f"🌊 Có một con quái vật đang cắn câu!\n"
                       f"💥 Nó đang kéo bạn xuống nước!\n\n"
                       f"**{legendary_fish['emoji']} {legendary_fish['name']}**\n"
                       f"_{legendary_fish['description']}_",
            color=discord.Color.dark_red()
        )
        legendary_embed.add_field(
            name="⚔️ CHUẨN BỊ ĐẤU BOSS!",
            value=f"Độ bền cần câu: {rod_durability}/{rod_config['durability']}\n"
                 f"Cấp độ cần: {rod_level}/5",
            inline=False
        )
        legendary_embed.add_field(
            name="🧪 DEBUG INFO",
            value=f"Fish Key: `{legendary_fish['key']}`\nSpawn Chance: {legendary_fish['spawn_chance']*100:.2f}%\nAchievement: `{legendary_fish['achievement']}`",
            inline=False
        )
        legendary_embed.set_image(url=legendary_fish.get('image_url', ''))
        legendary_embed.set_footer(text="[DEBUG] Chọn chiến thuật chinh phục quái vật! ⏱️ 60 giây")
        
        # Create boss fight view
        boss_view = LegendaryBossFightView(self, user_id, legendary_fish, rod_durability, rod_level, channel, guild_id)
        
        # Send boss fight message
        boss_msg = await channel.send(f"<@{user_id}> [🧪 DEBUG TEST]", embed=legendary_embed, view=boss_view)
        
        # Log
        print(f"[DEBUG] {ctx.author.name} triggered legendary encounter: {legendary_fish['key']}")
        await ctx.send(f"✅ **DEBUG**: Triggered {legendary_fish['emoji']} {legendary_fish['name']} encounter!")
    
    # ==================== HELPER METHODS ====================
    
    async def get_fishing_cooldown_remaining(self, user_id: int) -> int:
        """Get remaining cooldown in seconds."""
        if user_id not in self.fishing_cooldown:
            return 0
        
        cooldown_until = self.fishing_cooldown[user_id]
        remaining = max(0, cooldown_until - time.time())
        return int(remaining)
    
    async def get_tree_boost_status(self, guild_id: int) -> bool:
        """Check if server tree is at max level (nở hoa/kết trái)."""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT level FROM server_tree WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] >= 5:
                        return True
        except:
            pass
        return False
    
    async def add_inventory_item(self, user_id: int, item_name: str, item_type: str):
        """Add item to inventory."""
        await add_item(user_id, item_name, 1)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE inventory SET type = ? WHERE user_id = ? AND item_name = ?",
                    (item_type, user_id, item_name)
                )
                await db.commit()
        except:
            pass
    
    async def check_achievement(self, user_id: int, achievement_key: str, channel = None, guild_id: int = None):
        """Check and award achievement if conditions are met."""
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = []
        
        # Skip if already earned
        if achievement_key in self.user_achievements[user_id]:
            return False
        
        achievement = ACHIEVEMENTS.get(achievement_key)
        if not achievement:
            return False
        
        # Get user stats from database
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    """SELECT bad_events_encountered, global_reset_triggered, chests_caught,
                       market_boom_sales, robbed_count, god_of_wealth_encountered, 
                       rods_repaired, rod_level, trash_recycled FROM economy_users WHERE user_id = ?""",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return False
                    
                    bad_events, global_reset, chests, market_boom, robbed, god_wealth, rods_rep, rod_lvl, trash_rec = row
        except Exception as e:
            print(f"[ACHIEVEMENT] Error fetching stats: {e}")
            return False
        
        # Check conditions based on achievement type
        condition_met = False
        
        if achievement_key == "survivor" and bad_events >= achievement["target"]:
            condition_met = True
        elif achievement_key == "child_of_sea" and global_reset >= achievement["target"]:
            condition_met = True
        elif achievement_key == "treasure_hunter" and chests >= achievement["target"]:
            condition_met = True
        elif achievement_key == "market_manipulator" and market_boom >= achievement["target"]:
            condition_met = True
        elif achievement_key == "market_unluckiest" and robbed >= achievement["target"]:
            condition_met = True
        elif achievement_key == "god_of_wealth" and god_wealth >= achievement["target"]:
            condition_met = True
        elif achievement_key == "diligent_smith" and rods_rep >= achievement["target"]:
            condition_met = True
        elif achievement_key == "rod_tycoon" and rod_lvl >= achievement["target"]:
            condition_met = True
        elif achievement_key == "master_recycler" and trash_rec >= achievement["target"]:
            condition_met = True
        elif achievement_key == "boss_hunter":
            # Check if user has all 3 boss fish
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute(
                        "SELECT item_name FROM inventory WHERE user_id = ? AND item_name IN ('megalodon', 'thuy_quai_kraken', 'leviathan')",
                        (user_id,)
                    ) as cursor:
                        boss_fish = await cursor.fetchall()
                        if len(boss_fish) >= 3:
                            condition_met = True
            except:
                pass
        elif achievement_key in ["river_lord", "star_walker", "sun_guardian", "void_gazer", "lonely_frequency"]:
            # Check if user has caught this legendary fish
            import json
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute(
                        "SELECT legendary_fish FROM economy_users WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row and row[0]:
                            legendary_list = json.loads(row[0])
                            target_fish = achievement["target"]
                            if target_fish in legendary_list:
                                condition_met = True
            except:
                pass
        elif achievement_key == "legendary_hunter":
            # Check if user has all 5 legendary fish
            import json
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute(
                        "SELECT legendary_fish FROM economy_users WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row and row[0]:
                            legendary_list = json.loads(row[0])
                            required_legendaries = ["thuong_luong", "ca_ngan_ha", "ca_phuong_hoang", "cthulhu_con", "ca_voi_52hz"]
                            if all(fish in legendary_list for fish in required_legendaries):
                                condition_met = True
            except:
                pass
        elif achievement_key == "collection_master":
            condition_met = True  # This is checked separately in _fish_action
        
        if condition_met:
            self.user_achievements[user_id].append(achievement_key)
            
            # Award role if specified
            if achievement.get("role_id") and guild_id:
                try:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        user = guild.get_member(user_id)
                        role = guild.get_role(achievement["role_id"])
                        if user and role:
                            await user.add_roles(role)
                            print(f"[ACHIEVEMENT] {user_id} awarded role '{role.name}' for achievement '{achievement_key}'")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error awarding role for {achievement_key}: {e}")
            
            # Award coins in database
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE economy_users SET seeds = seeds + ? WHERE user_id = ?",
                        (achievement["reward_coins"], user_id)
                    )
                    await db.commit()
            except:
                pass
            
            # Send announcement
            if channel:
                embed = discord.Embed(
                    title=f"🏆 THÀNH TỰU: {achievement['emoji']} {achievement['name']}",
                    description=achievement['description'],
                    color=discord.Color.gold()
                )
                embed.add_field(name="Phần Thưởng", value=f"+{achievement['reward_coins']} Hạt", inline=False)
                if achievement.get("role_id"):
                    embed.add_field(name="🎖️ Role Cấp", value=f"Bạn đã nhận được role thành tựu!", inline=False)
                await channel.send(embed=embed)
            return True
        
        return False
    
    async def get_title(self, user_id: int, guild_id: int) -> str:
        """Get user's title."""
        if user_id in self.user_titles:
            return self.user_titles[user_id]
        
        try:
            guild = self.bot.get_guild(guild_id)
            if guild:
                user = guild.get_member(user_id)
                if user:
                    role_id = 1450409414111658024
                    role = guild.get_role(role_id)
                    if role and role in user.roles:
                        title = "👑 Vua Câu Cá 👑"
                        self.user_titles[user_id] = title
                        return title
        except Exception as e:
            print(f"[TITLE] Error getting title: {e}")
        
        return ""
    
    async def update_rod_data(self, user_id: int, durability: int, level: int = None):
        """Update rod durability (and level if provided)"""
        await update_rod_data_module(user_id, durability, level)
    
    async def add_legendary_fish_to_user(self, user_id: int, legendary_key: str):
        """Add legendary fish to user's collection"""
        await add_legendary_module(user_id, legendary_key)

async def setup(bot):
    """Setup fishing cog."""
    await bot.add_cog(FishingCog(bot))
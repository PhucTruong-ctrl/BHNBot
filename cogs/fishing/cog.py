"""Main Fishing Cog."""

import discord
import aiosqlite
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, time as dt_time
import asyncio
import random
import time
import json
from typing import Optional

from .constants import *
from .helpers import track_caught_fish, get_collection, check_collection_complete
from .rod_system import get_rod_data, update_rod_data as update_rod_data_module
from .legendary import LegendaryBossFightView, check_legendary_spawn_conditions, add_legendary_fish_to_user as add_legendary_module
from .events import trigger_random_event
from .views import FishSellView
from .glitch import apply_display_glitch as global_apply_display_glitch, set_glitch_state
from database_manager import (
    get_inventory, add_item, remove_item, add_seeds, 
    get_user_balance, get_or_create_user, db_manager, get_stat, increment_stat, get_all_stats
)
from .legendary_quest_helper import (
    increment_sacrifice_count, get_sacrifice_count, reset_sacrifice_count,
    set_crafted_bait_status, get_crafted_bait_status,
    set_phoenix_prep_status, get_phoenix_prep_status,
    set_map_pieces_count, get_map_pieces_count, set_quest_completed, is_quest_completed,
    set_frequency_hunt_status, get_frequency_hunt_status,
    is_legendary_caught, set_legendary_caught,
    get_manh_sao_bang_count, set_manh_sao_bang_count, increment_manh_sao_bang,
    has_tinh_cau, set_has_tinh_cau, get_tinh_cau_cooldown, set_tinh_cau_cooldown, craft_tinh_cau
)

# ==================== METEOR SHOWER EVENT ====================

class MeteorWishView(discord.ui.View):
    """View for wishing on shooting stars"""
    def __init__(self, cog):
        super().__init__(timeout=30)
        self.cog = cog
        self.wished_users = set()
    
    @discord.ui.button(label="🙏 Ước Nguyện", style=discord.ButtonStyle.primary, emoji="💫")
    async def wish_on_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        # Check daily limit using user_stats
        today_str = datetime.now().strftime('%Y-%m-%d')
        stat_key = f'meteor_shards_today_{today_str}'
        current_count = await get_stat(user_id, 'fishing', stat_key, 0)
        
        if current_count >= 2:
            await interaction.response.send_message("Bạn đã ước đủ 2 lần hôm nay rồi! Hãy quay lại ngày mai.", ephemeral=True)
            return
        
        # Prevent double-click
        if user_id in self.wished_users:
            await interaction.response.send_message("Bạn đã ước rồi!", ephemeral=True)
            return
        
        self.wished_users.add(user_id)
        
        # 20% chance for manh_sao_bang, else seeds/exp
        if random.random() < 0.2:
            await increment_manh_sao_bang(user_id, 1)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            reward_msg = "Bạn nhận được **Mảnh Sao Băng**! ⭐"
        else:
            seeds = random.randint(10, 50)
            await add_seeds(user_id, seeds)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            reward_msg = f"Bạn nhận được **{seeds} hạt**! 🌱"
        
        await interaction.response.send_message(f"🌟 Ước nguyện thành! {reward_msg}", ephemeral=True)
        
        # Disable button after 15s
        await asyncio.sleep(15)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except:
            pass

# ==================== NPC ENCOUNTER VIEW ====================

class NPCEncounterView(discord.ui.View):
    """View for NPC encounter interactions."""
    def __init__(self, user_id: int, npc_type: str, npc_data: dict, fish_key: str = None):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.npc_type = npc_type
        self.npc_data = npc_data
        self.fish_key = fish_key
        self.value = None
    
    async def on_timeout(self):
        """View times out if no action taken within 30s - auto decline"""
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

# ==================== FISHING COG ====================

class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fishing_cooldown = {}
        self.caught_items = {}
        self.user_titles = {}
        self.user_stats = {}
        self.lucky_buff_users = {}
        self.avoid_event_users = {}
        self.legendary_buff_users = {}  # For ghost NPC buff
        self.sell_processing = {}  # {user_id: timestamp} - Prevent duplicate sell commands
        self.guaranteed_catch_users = {}  # {user_id: True} - Guaranteed legendary catch from tinh cau win
        
        # Emotional state tracking
        self.emotional_states = {}  # {user_id: {type: "suy"|"keo_ly"|"lag", duration: int, start_time: float}}
        
        # Legendary summoning tracking (sacrifice count now persisted in database)
        self.dark_map_active = {}  # {user_id: True/False} - For Cthulhu Non
        self.dark_map_casts = {}  # {user_id: remaining_casts} - Track remaining casts with map
        self.dark_map_cast_count = {}  # {user_id: current_cast} - Track current cast number (1-10) with dark map
        self.phoenix_buff_active = {}  # {user_id: expiry_time} - For Cá Phượng Hoàng lông vũ buff
        self.thuong_luong_timers = {}  # {user_id: timestamp} - For Thuồng Luồng ritual
        # Note: 52Hz detection flag is now handled by ConsumableCog.detected_52hz
        
        # Global Calamity (Disaster) tracking
        self.is_server_frozen = False
        self.freeze_end_time = 0
        self.last_disaster_time = 0  # Timestamp when last disaster ended
        self.global_disaster_cooldown = GLOBAL_DISASTER_COOLDOWN  # Default 3600s (1 hour)
        self.current_disaster = None  # Store current disaster info
        self.disaster_culprit = None  # User who caused the disaster
        self.pending_disaster = {}  # {user_id: disaster_key} - Force trigger disaster on next fishing
        
        self.meteor_wish_count = {}  # {user_id: {'date': date, 'count': int}}
        
        # Start meteor shower task
        self.meteor_shower_event.start()
        
        # Disaster effects tracking (expire when disaster ends)
        self.disaster_catch_rate_penalty = 0.0  # Percentage to reduce catch rate (0.2 = -20%)
        self.disaster_cooldown_penalty = 0  # Extra seconds to add to cooldown
        self.disaster_fine_amount = 0  # Amount to deduct from players
        self.disaster_display_glitch = False  # Whether to show garbled fish names
        self.disaster_effect_end_time = 0  # When current disaster effects expire
        self.disaster_channel = None  # Channel to send disaster end notification
    
    @tasks.loop(time=dt_time(21, 0))
    async def meteor_shower_event(self):
        """Daily meteor shower event at 21:00"""
        try:
            if random.random() < 0.4:  # 40% chance
                # Get all guilds with fishing channels configured
                from database_manager import db_manager
                rows = await db_manager.execute("SELECT guild_id, fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL")
                
                for guild_id, channel_id in rows:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send("🌌 Bầu trời đêm nay quang đãng lạ thường... Có vẻ sắp có mưa sao băng!")
                        
                        # Send 5-10 messages over 30 minutes
                        for _ in range(random.randint(5, 10)):
                            await asyncio.sleep(random.randint(120, 300))  # 2-5 minutes
                            embed = discord.Embed(
                                title="💫 Một ngôi sao vừa vụt qua!",
                                description="Ước mau!",
                                color=discord.Color.blue()
                            )
                            view = MeteorWishView(self)
                            await channel.send(embed=embed, view=view)
        except Exception as e:
            print(f"[METEOR] Error in meteor shower event: {e}")
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="sukien", description="⚡ Force trigger disaster trên user tiếp theo (chỉ Admin)")
    @app_commands.describe(
        user="Discord user sẽ bị trigger disaster",
        disaster_key="Disaster key (xem danh sách trong disaster_events.json)"
    )
    async def trigger_disaster_slash(self, interaction: discord.Interaction, user: discord.User, disaster_key: str):
        await self._trigger_disaster_action(interaction, user.id, disaster_key, is_slash=True)
    
    @commands.command(name="sukien", description="⚡ Force trigger disaster (chỉ Admin)")
    async def trigger_disaster_prefix(self, ctx, user: discord.User, disaster_key: str):
        await self._trigger_disaster_action(ctx, user.id, disaster_key, is_slash=False)
    
    async def _trigger_disaster_action(self, ctx_or_interaction, target_user_id: int, disaster_key: str, is_slash: bool):
        """Force trigger a disaster for next fishing action."""
        # Check if user is bot owner/admin
        if ctx_or_interaction.user.id != self.bot.owner_id:
            if is_slash:
                await ctx_or_interaction.response.send_message("❌ Chỉ Owner mới có quyền sử dụng lệnh này!", ephemeral=True)
            else:
                await ctx_or_interaction.send("❌ Chỉ Owner mới có quyền sử dụng lệnh này!")
            return
        
        # Load disasters data
        import json
        from .constants import DISASTER_EVENTS_PATH
        try:
            with open(DISASTER_EVENTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                disasters = {d["key"]: d for d in data.get("disasters", [])}
        except:
            if is_slash:
                await ctx_or_interaction.response.send_message("❌ Lỗi load disaster events!", ephemeral=True)
            else:
                await ctx_or_interaction.send("❌ Lỗi load disaster events!")
            return
        
        # Verify disaster key exists
        if disaster_key not in disasters:
            disaster_list = ", ".join(disasters.keys())
            if is_slash:
                await ctx_or_interaction.response.send_message(f"❌ Disaster key không tồn tại!\n\nDanh sách: {disaster_list}", ephemeral=True)
            else:
                await ctx_or_interaction.send(f"❌ Disaster key không tồn tại!\n\nDanh sách: {disaster_list}")
            return
        
        # Store pending disaster
        self.pending_disaster[target_user_id] = disaster_key
        
        target_user = self.bot.get_user(target_user_id)
        target_name = target_user.mention if target_user else f"<@{target_user_id}>"
        
        embed = discord.Embed(
            title="⚡ THẢM HỌA ĐƯỢC LÊNH CHỈ",
            description=f"Người chơi {target_name} sẽ bị trigger disaster **{disasters[disaster_key]['name']}** ({disasters[disaster_key]['emoji']}) trong lần câu tiếp theo!",
            color=discord.Color.red()
        )
        
        if is_slash:
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @app_commands.command(name="cauca", description="Câu cá - thời gian chờ 30s")
    async def fish_slash(self, interaction: discord.Interaction):
        await self._fish_action(interaction)
    
    @commands.command(name="cauca")
    async def fish_prefix(self, ctx):
        await self._fish_action(ctx)
    
    async def _fish_action(self, ctx_or_interaction):
        """Main fishing logic - rút gọn, gọi helpers từ modules khác"""
        try:
            is_slash = isinstance(ctx_or_interaction, discord.Interaction)
            
            # Get user_id first (before defer) for lag check
            if is_slash:
                user_id = ctx_or_interaction.user.id
            else:
                user_id = ctx_or_interaction.author.id
            
            # *** CHECK AND APPLY LAG DEBUFF DELAY (applies to EVERY cast) ***
            if self.check_emotional_state(user_id, "lag"):
                await asyncio.sleep(3)
                username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                print(f"[EVENT] {username} experienced lag delay (3s) - start of cast")
            
            if is_slash:
                await ctx_or_interaction.response.defer(ephemeral=False)
                channel = ctx_or_interaction.channel
                guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
                ctx = ctx_or_interaction
            else:
                channel = ctx_or_interaction.channel
                guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
                ctx = ctx_or_interaction
            
            # --- GET USER AND ROD DATA ---
            rod_lvl, rod_durability = await get_rod_data(user_id)
            rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
            inventory = await get_inventory(user_id) # Fetch inventory once
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            print(f"[FISHING] [ROD_DATA] {username_display} (user_id={user_id}) rod_level={rod_lvl} durability={rod_durability}/{rod_config['durability']}")
            
            # --- CHECK FOR SERVER FREEZE (GLOBAL DISASTER) ---
            if self.is_server_frozen:
                remaining_freeze = int(self.freeze_end_time - time.time())
                if remaining_freeze > 0:
                    username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                    
                    # Determine message based on current disaster
                    if self.current_disaster:
                        disaster_emoji = self.current_disaster.get("emoji", "🚨")
                        disaster_name = self.current_disaster.get("name", "Disaster")
                        culprit_text = f" (Tội đồ: {self.disaster_culprit})" if self.disaster_culprit else ""
                        message = f"⛔ **SERVER ĐANG BẢO TRÌ ĐỘT XUẤT!**\n\n{disaster_emoji} **{disaster_name}**{culprit_text}\n\nVui lòng chờ **{remaining_freeze}s** nữa để khôi phục hoạt động!"
                    else:
                        message = f"⛔ Server đang bị khóa. Vui lòng chờ **{remaining_freeze}s** nữa!"
                    
                    print(f"[FISHING] [SERVER_FROZEN] {username_display} (user_id={user_id}) blocked by disaster: {self.current_disaster.get('name', 'unknown') if self.current_disaster else 'unknown'}")
                    if is_slash:
                        await ctx.followup.send(message, ephemeral=True)
                    else:
                        await ctx.send(message)
                    return
                else:
                    # Freeze time expired, reset
                    self.is_server_frozen = False
                    current_disaster_copy = self.current_disaster
                    disaster_channel = self.disaster_channel
                    self.current_disaster = None
                    self.disaster_culprit = None
                    # Clear all disaster effects
                    self.disaster_catch_rate_penalty = 0.0
                    self.disaster_cooldown_penalty = 0
                    self.disaster_fine_amount = 0
                    self.disaster_display_glitch = False
                    self.disaster_effect_end_time = 0
                    self.disaster_channel = None
                    try:
                        set_glitch_state(False, 0)
                    except Exception:
                        pass
                    
                    # Send disaster end notification
                    try:
                        if current_disaster_copy and disaster_channel:
                            end_embed = discord.Embed(
                                title=f"✅ {current_disaster_copy['name'].upper()} ĐÃ KẾT THÚC",
                                description=f"{current_disaster_copy['emoji']} Thảm hoạ toàn server đã qua đi!\n\n💚 **Server đã trở lại bình thường.** Các hoạt động khôi phục hoàn toàn.",
                                color=discord.Color.green()
                            )
                            end_embed.set_footer(text="Cảm ơn vì đã chờ đợi!")
                            await disaster_channel.send(embed=end_embed)
                    except Exception as e:
                        print(f"[DISASTER] Error sending end notification: {e}")

            # --- CHECK FOR NON-FREEZE DISASTER EFFECTS EXPIRING ---
            if self.current_disaster and time.time() >= self.disaster_effect_end_time and not self.is_server_frozen:
                # Non-freeze disaster effects have expired
                try:
                    current_disaster_copy = self.current_disaster
                    disaster_channel = self.disaster_channel
                    self.current_disaster = None
                    self.disaster_culprit = None
                    # Clear all disaster effects
                    self.disaster_catch_rate_penalty = 0.0
                    self.disaster_cooldown_penalty = 0
                    self.disaster_fine_amount = 0
                    self.disaster_display_glitch = False
                    self.disaster_effect_end_time = 0
                    self.disaster_channel = None
                    try:
                        set_glitch_state(False, 0)
                    except Exception:
                        pass
                    
                    # Send disaster end notification
                    if current_disaster_copy and disaster_channel:
                        end_embed = discord.Embed(
                            title=f"✅ {current_disaster_copy['name'].upper()} ĐÃ KẾT THÚC",
                            description=f"{current_disaster_copy['emoji']} Thảm hoạ toàn server đã qua đi!\n\n💚 **Server đã trở lại bình thường.** Các hoạt động khôi phục hoàn toàn.",
                            color=discord.Color.green()
                        )
                        end_embed.set_footer(text="Cảm ơn vì đã chờ đợi!")
                        await disaster_channel.send(embed=end_embed)
                except Exception as e:
                    print(f"[DISASTER] Error handling end of non-freeze disaster: {e}")

            # --- CHECK FISH BUCKET LIMIT (BEFORE ANYTHING ELSE) ---
            # Get current fish count (only real fish, exclude trash and special items)
            fish_count = sum(v for k, v in inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS)
        
            # If bucket is full, block fishing immediately
            if fish_count >= FISH_BUCKET_LIMIT:
                username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                embed = discord.Embed(
                    title=f"⚠️ XÔ ĐÃ ĐẦY - {username_display}!",
                    description=f"🪣 Xô cá của bạn đã chứa {fish_count} con cá (tối đa {FISH_BUCKET_LIMIT}).\n\nHãy bán cá để có chỗ trống, rồi quay lại câu tiếp!",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Hãy dùng lệnh bán cá để bán bớt nhé.")
                if is_slash:
                    await ctx.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx.send(embed=embed)
                print(f"[FISHING] [BLOCKED] {username_display} (user_id={user_id}) bucket_full fish_count={fish_count}/{FISH_BUCKET_LIMIT}")
                return
        
            # --- CHECK DURABILITY & AUTO REPAIR ---
            repair_msg = ""
            is_broken_rod = False  # Flag to treat as no-worm when durability is broken
        
            if rod_durability <= 0:
                repair_cost = rod_config["repair"]
                balance = await get_user_balance(user_id)
                print(f"[FISHING] [ROD_BROKEN] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} (user_id={user_id}) rod_level={rod_lvl} durability={rod_durability} repair_cost={repair_cost} balance={balance}")
            
                if balance >= repair_cost:
                    # Auto repair
                    await add_seeds(user_id, -repair_cost)
                    rod_durability = rod_config["durability"]
                    await self.update_rod_data(user_id, rod_durability, rod_lvl)
                    repair_msg = f"\n🛠️ **Cần câu đã gãy!** Tự động sửa chữa: **-{repair_cost} Hạt** (Độ bền phục hồi: {rod_durability}/{rod_config['durability']})"
                    print(f"[FISHING] [AUTO_REPAIR] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} (user_id={user_id}) seed_change=-{repair_cost} action=rod_repaired new_durability={rod_durability}")
                    # Track rods repaired for achievement
                    try:
                        await increment_stat(user_id, "fishing", "rods_repaired", 1)
                        current_repairs = await get_stat(user_id, "fishing", "rods_repaired")
                        # Check achievement: diligent_smith (100 repairs)
                        await self.bot.achievement_manager.check_unlock(
                            user_id=user_id,
                            game_category="fishing",
                            stat_key="rods_repaired",
                            current_value=current_repairs,
                            channel=channel
                        )
                    except Exception as e:
                        print(f"[ACHIEVEMENT] Error updating rods_repaired for {user_id}: {e}")
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
                print(f"[FISHING] [COOLDOWN] {username_display} (user_id={user_id}) remaining={remaining}s")
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    try:
                        await ctx.send(msg)
                    except Exception as e:
                        print(f"[FISHING] Error sending cooldown message: {e}")
                return
        
            # Ensure user exists
            username = ctx.author.name if not is_slash else ctx_or_interaction.user.name
            await get_or_create_user(user_id, username)
            
            # --- TRIGGER GLOBAL DISASTER (0.05% chance) ---
            disaster_result = await self.trigger_global_disaster(user_id, username, channel)
            if disaster_result.get("triggered"):
                # Disaster was triggered! User's cast is cancelled
                culprit_reward = disaster_result["disaster"]["reward_message"]
                thank_you_msg = f"🎭 {culprit_reward}"
                print(f"[FISHING] [DISASTER_TRIGGERED] {username} (user_id={user_id}) triggered disaster: {disaster_result['disaster']['name']}")
                if is_slash:
                    await ctx.followup.send(thank_you_msg)
                else:
                    await ctx.send(thank_you_msg)
                return
        
            # --- LOGIC MỚI: AUTO-BUY MỒI NẾU CÓ ĐỦ TIỀN ---
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
                    print(f"[FISHING] [AUTO_BUY_WORM] {username} (user_id={user_id}) seed_change=-{WORM_COST} balance_before={balance} balance_after={balance - WORM_COST}")
                else:
                    # Không có mồi, cũng không đủ tiền -> Chấp nhận câu rác
                    has_worm = False
                    print(f"[FISHING] [NO_WORM_NO_MONEY] {username} (user_id={user_id}) has_worm=False balance={balance} < {WORM_COST}")
            else:
                # Có mồi trong túi -> Trừ mồi
                await remove_item(user_id, "worm", 1)
                # Track worms used for achievement
                try:
                    await increment_stat(user_id, "fishing", "worms_used", 1)
                    current_worms = await get_stat(user_id, "fishing", "worms_used")
                    # Check achievement: worm_destroyer (100 worms)
                    await self.bot.achievement_manager.check_unlock(
                        user_id=user_id,
                        game_category="fishing",
                        stat_key="worms_used",
                        current_value=current_worms,
                        channel=channel
                    )
                except:
                    pass
                print(f"[FISHING] [CONSUME_WORM] {username} (user_id={user_id}) inventory_change=-1 action=used_bait")
        
            # --- KẾT THÚC LOGIC MỚI ---
            
            # --- APPLY DISASTER FINE (Police Raid effect) ---
            disaster_fine_msg = ""
            if self.disaster_fine_amount > 0 and time.time() < self.disaster_effect_end_time:
                current_balance = await get_user_balance(user_id)
                if current_balance >= self.disaster_fine_amount:
                    await add_seeds(user_id, -self.disaster_fine_amount)
                    disaster_fine_msg = f"\n💰 **PHẠT HÀNH CHÍNH:** -{ self.disaster_fine_amount} Hạt do {self.current_disaster.get('name', 'sự kiện')}"
                    print(f"[DISASTER_FINE] {username} fined {self.disaster_fine_amount} seeds due to {self.current_disaster.get('key')} balance_before={current_balance} balance_after={current_balance - self.disaster_fine_amount}")
                else:
                    disaster_fine_msg = f"\n⚠️ **PHẠT HÀNH CHÍNH:** Không đủ tiền phạt ({self.disaster_fine_amount} Hạt)"
                    print(f"[DISASTER_FINE] {username} insufficient balance for fine {self.disaster_fine_amount} balance={current_balance}")

        
            print(f"[FISHING] [START] {username} (user_id={user_id}) rod_level={rod_lvl} rod_durability={rod_durability} has_bait={has_worm}")
        
            # Track if this cast triggers global reset (will affect cooldown setting)
            triggers_global_reset = False
            
            # Set cooldown using rod-based cooldown (will be cleared if global_reset triggers)
            cooldown_time = rod_config["cd"]
            
            # *** APPLY DISASTER COOLDOWN PENALTY (Shark Bite Cable effect) ***
            if self.disaster_cooldown_penalty > 0 and time.time() < self.disaster_effect_end_time:
                cooldown_time += self.disaster_cooldown_penalty
                print(f"[DISASTER] {username} cooldown increased by {self.disaster_cooldown_penalty}s due to {self.current_disaster.get('name', 'disaster')}")
            
            self.fishing_cooldown[user_id] = time.time() + cooldown_time
        
            # Casting animation
            wait_time = random.randint(1, 5)
        
            # Thêm thông báo nhỏ nếu tự mua mồi hoặc không có mồi
            status_text = ""
            if auto_bought:
                status_text = f"\n💸 *(-{WORM_COST} Hạt mua mồi)*"
            elif not has_worm:
                status_text = "\n⚠️ *Không có mồi (Tỉ lệ rác cao)*"
        
            rod_status = f"\n🎣 *{rod_config['emoji']} {rod_config['name']} (Thời gian chờ: {rod_config['cd']}s)*"
            durability_status = f"\n🛡️ **Độ bền còn lại: {rod_durability}/{rod_config['durability']}**"
            
            # Apply glitch to all casting text
            casting_text = f"🎣 **{username}** quăng cần... Chờ cá cắn câu... ({wait_time}s){status_text}{rod_status}{repair_msg}{durability_status}"
            casting_text = self.apply_display_glitch(casting_text)

            casting_msg = await channel.send(casting_text)
            await asyncio.sleep(wait_time)
        
            # ==================== TRIGGER RANDOM EVENTS ====================
        
            event_result = await trigger_random_event(self, user_id, channel.guild.id, rod_lvl, channel)
        
            # If user avoided a bad event, show what they avoided
            if event_result.get("avoided", False):
                protection_desc = f"✨ **Giác Quan Thứ 6 hoặc Đi Chùa bảo vệ bạn!**\n\n{event_result['message']}\n\n**Bạn an toàn thoát khỏi sự kiện này!**"
                embed = discord.Embed(
                    title=self.apply_display_glitch(f"🛡️ BẢO VỆ - {username}!"),
                    description=self.apply_display_glitch(protection_desc),
                    color=discord.Color.gold()
                )
                await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
                await asyncio.sleep(1)
                casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
                # Skip event processing since it was avoided - continue to normal fishing
                event_result["triggered"] = False
        
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
            
                # Track if event is good or bad for achievements
                is_event_good = event_result.get("gain_money", 0) > 0 or len(event_result.get("gain_items", {})) > 0 or event_result.get("custom_effect") in ["lucky_buff", "sixth_sense", "restore_durability"]
                if not is_event_good and event_result.get("lose_catch"):
                    is_event_good = False
            
                # Update achievement tracking
                try:
                    if is_event_good:
                        await increment_stat(user_id, "fishing", "good_events_encountered", 1)  # stat update
                        current_good_events = await get_stat(user_id, "fishing", "good_events_encountered")
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "good_events", current_good_events, channel)
                    else:
                        # Track bad events
                        await increment_stat(user_id, "fishing", "bad_events_encountered", 1)  # stat update
                        current_bad_events = await get_stat(user_id, "fishing", "bad_events_encountered")
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "bad_events", current_bad_events, channel)
                except:
                    pass
            
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
                    # SECURITY: Never let balance go negative
                    current_balance = await get_user_balance(user_id)
                    penalty_amount = min(event_result["lose_money"], current_balance)
                    
                    if penalty_amount > 0:
                        await add_seeds(user_id, -penalty_amount)
                        event_message += f" (-{penalty_amount} Hạt)"
                        
                        # Log if penalty was capped
                        if penalty_amount < event_result["lose_money"]:
                            print(f"[FISHING] [EVENT] {username} (user_id={user_id}) Penalty capped: {event_result['lose_money']} → {penalty_amount} (insufficient balance)")
                    else:
                        event_message += f" (Không đủ tiền để bị phạt!)"
            
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
                    penalty = max(10, int(balance * SNAKE_BITE_PENALTY_PERCENT))  # Min 10 Hạt
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
            
                elif event_result.get("custom_effect") == "suy_debuff":
                    # Depression debuff: 50% rare catch reduction for 5 casts
                    self.apply_emotional_state(user_id, "suy", 5)
                    event_message += " (Bạn bị 'suy' 😭 - Giảm 50% tỉ lệ cá hiếm trong 5 lần câu)"
                    print(f"[EVENT] {username} afflicted with suy debuff for 5 casts")
            
                elif event_result.get("custom_effect") == "keo_ly_buff":
                    # Slay buff: 2x sell price for 10 minutes (600 seconds)
                    self.apply_emotional_state(user_id, "keo_ly", 600)
                    event_message += " (Keo Lỳ tái châu! 💅 - x2 tiền bán cá trong 10 phút)"
                    print(f"[EVENT] {username} activated keo_ly buff for 600 seconds")
            
                elif event_result.get("custom_effect") == "lag_debuff":
                    # Lag debuff: 3s delay per cast for 5 minutes (300 seconds)
                    self.apply_emotional_state(user_id, "lag", 300)
                    event_message += " (Mạng lag! 📶 - Bot sẽ phản hồi chậm 3s cho mỗi lần câu trong 5 phút)"
                    print(f"[EVENT] {username} afflicted with lag debuff for 300 seconds")
            
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
                # Note: normal cooldown already set at line 225, only override if special cooldown_increase
            
                # If lose_catch, don't process fishing
                if event_result.get("lose_catch", False):
                    event_display = self.apply_display_glitch(event_message)
                    embed = discord.Embed(
                        title=f"⚠️ KIẾP NẠN - {username}!",
                        description=event_display,
                        color=discord.Color.red()
                    )
                    # Apply durability loss before returning
                    rod_durability = max(0, rod_durability - durability_loss)
                    await self.update_rod_data(user_id, rod_durability)
                    durability_display = self.apply_display_glitch(f"🛡️ Độ bền: {rod_durability}/{rod_config['durability']}")
                    embed.set_footer(text=durability_display)
                    await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
                    print(f"[EVENT] {username} triggered {event_type} - fishing cancelled, durability loss: {durability_loss}")
                    return
            
                # Otherwise, display event message and continue fishing
                event_display = self.apply_display_glitch(event_message)
                event_type_data = RANDOM_EVENTS.get(event_type, {})
                is_good_event = event_type_data.get("type") == "good"
                color = discord.Color.green() if is_good_event else discord.Color.orange()
                event_title = f"🌟 PHƯỚC LÀNH - {username}!" if is_good_event else f"⚠️ KIẾP NẠN - {username}!"
                event_title = self.apply_display_glitch(event_title)
                embed = discord.Embed(
                    title=event_title,
                    description=event_display,
                    color=color
                )
                await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
            
                # Special embed for Isekai event - show legendary fish info
                if event_type == "isekai_truck":
                    # Find the legendary fish data
                    legendary_fish = next((fish for fish in LEGENDARY_FISH_DATA if fish["key"] == "ca_isekai"), None)
                    if legendary_fish:
                        fish_embed = discord.Embed(
                            title=f"🌌 **CÁ HUYỀN THOẠI MỚI!** 🌌",
                            description=f"**{legendary_fish['emoji']} {legendary_fish['name']}**\n\n"
                                       f"{legendary_fish['description']}\n\n"
                                       f"**Giá bán:** {legendary_fish['sell_price']} Hạt (Không thể bán)\n"
                                       f"**Cấp độ:** {legendary_fish['level']}\n"
                                       f"**Thành tựu:** {legendary_fish['achievement']}",
                            color=discord.Color.purple()
                        )
                        if legendary_fish.get("image_url"):
                            fish_embed.set_image(url=legendary_fish["image_url"])
                        await channel.send(embed=fish_embed)
                        await asyncio.sleep(1)  # Brief pause before continuing
            
                # Handle global reset events
                if event_result.get("custom_effect") == "global_reset":
                    triggers_global_reset = True
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
        
            # Apply bonus catch from events (e.g., Bão Cá - câu thêm cá ngẫu nhiên)
            bonus_catch = event_result.get("bonus_catch", 0)
            if bonus_catch > 0:
                original_num_fish = num_fish
                num_fish = num_fish + bonus_catch
                print(f"[EVENT] {username} activated bonus_catch +{bonus_catch}: {original_num_fish} → {num_fish} fish")
        
            # Roll trash (độc lập)
            # NHƯNG: Nếu không có mồi HOẶC cần gãy -> chỉ roll trash hoặc cá, không vừa cá vừa rác vừa rương
            if has_worm and not is_broken_rod:
                trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
            else:
                # Không mồi hoặc cần gãy: Xác suất cao là rác (50/50 rác hoặc cá)
                trash_count = random.choices([0, 1], weights=[50, 50], k=1)[0]
        
            # Roll chest (độc lập, tỉ lệ thấp)
            # NHƯNG: Nếu không có mồi HOẶC cần gãy -> không bao giờ ra rương
            # Check for both tree boost AND lucky buff from NPC
            is_boosted = await self.get_tree_boost_status(channel.guild.id)
            has_lucky_buff = self.lucky_buff_users.get(user_id, False)
            is_boosted = is_boosted or has_lucky_buff
        
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
        
            # Clear lucky buff after this cast
            if has_lucky_buff:
                self.lucky_buff_users[user_id] = False
        
            boost_text = " ✨**(BUFF MAY MẮN!)**✨" if has_lucky_buff else ("✨" if is_boosted else "")
        
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
            
                # *** APPLY EMOTIONAL STATE: SUY DEBUFF (50% rare catch reduction) ***
                if self.check_emotional_state(user_id, "suy"):
                    rare_ratio = rare_ratio * 0.5  # Reduce by 50%
                    self.decrement_suy_cast(user_id)
            
                # *** APPLY LEGENDARY BUFF FROM GHOST NPC ***
                if hasattr(self, "legendary_buff_users") and user_id in self.legendary_buff_users:
                    rare_ratio = min(0.95, rare_ratio + 0.75)  # +75% rare chance
                    print(f"[NPC_BUFF] {username} has legendary buff active! Rare chance boosted to {int(rare_ratio*100)}%")
            
                # *** APPLY DISASTER CATCH RATE PENALTY ***
                current_time = time.time()
                if self.disaster_catch_rate_penalty > 0 and current_time < self.disaster_effect_end_time:
                    # Apply catch rate penalty (e.g., 0.5 = 50% reduction)
                    rare_ratio = rare_ratio * (1.0 - self.disaster_catch_rate_penalty)
                    print(f"[DISASTER] {username} catch rate reduced by {int(self.disaster_catch_rate_penalty*100)}% due to {self.current_disaster.get('name', 'disaster')}")
            
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
                        current_legendary = await get_stat(user_id, "fishing", "legendary_caught") or 0
                        await self.bot.achievement_manager.check_unlock(
                            user_id=user_id,
                            game_category="fishing",
                            stat_key="legendary_caught",
                            current_value=current_legendary + 1,
                            channel=channel
                        )
                
                    # Track in collection
                    is_new_collection = await track_caught_fish(user_id, fish['key'])
                    if is_new_collection:
                        print(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                        # Check first_catch achievement (catch any fish for the first time)
                        # Get current collection count to see if this is the first fish ever
                        collection = await get_collection(user_id)
                        if len(collection) == 1:  # This is the first fish ever caught
                            await increment_stat(user_id, "fishing", "first_catch", 1)
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "first_catch", 1, channel)
                        # Check if collection is complete
                        is_collection_complete = await check_collection_complete(user_id)
                        if is_collection_complete:
                            await self.bot.achievement_manager.check_unlock(
                                user_id=user_id,
                                game_category="fishing",
                                stat_key="collection_complete",
                                current_value=1,
                                channel=channel
                            )
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
                        # Check first_catch achievement (catch any fish for the first time)
                        # Get current collection count to see if this is the first fish ever
                        collection = await get_collection(user_id)
                        if len(collection) == 1:  # This is the first fish ever caught
                            await increment_stat(user_id, "fishing", "first_catch", 1)
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "first_catch", 1, channel)
                        # Check if collection is complete
                        is_collection_complete = await check_collection_complete(user_id)
                        if is_collection_complete:
                            await self.bot.achievement_manager.check_unlock(
                                user_id=user_id,
                                game_category="fishing",
                                stat_key="collection_complete",
                                current_value=1,
                                channel=channel
                            )
                    if fish['key'] not in fish_only_items:
                        fish_only_items[fish['key']] = 0
                    fish_only_items[fish['key']] += 1
        
            # Decrease legendary buff counter
            if hasattr(self, "legendary_buff_users") and user_id in self.legendary_buff_users:
                self.legendary_buff_users[user_id] -= 1
                if self.legendary_buff_users[user_id] <= 0:
                    del self.legendary_buff_users[user_id]
                    print(f"[NPC_BUFF] {username} legendary buff expired")
                else:
                    print(f"[NPC_BUFF] {username} has {self.legendary_buff_users[user_id]} legendary buff uses left")
        
            # Apply duplicate multiplier from events (e.g., Cá Song Sinh - nhân cá giống nhau)
            duplicate_multiplier = event_result.get("duplicate_multiplier", 1)
            if duplicate_multiplier > 1:
                duplicated_items = {}
                for fish_key, qty in fish_only_items.items():
                    new_qty = qty * duplicate_multiplier
                    duplicated_items[fish_key] = new_qty
                    # Add duplicated fish to inventory
                    await add_item(user_id, fish_key, new_qty - qty)
                    print(f"[EVENT] {username} activated duplicate_multiplier x{duplicate_multiplier}: {fish_key} {qty} → {new_qty}")
                fish_only_items = duplicated_items
        
            # Display fish grouped
            for key, qty in fish_only_items.items():
                fish = ALL_FISH[key]
                emoji = fish['emoji']
                total_price = fish['sell_price'] * qty  # Multiply price by quantity
                fish_name = self.apply_display_glitch(fish['name'])
                fish_display.append(f"{emoji} {fish_name} x{qty} ({total_price} Hạt)")
        
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
            
                # Determine if only trash was caught
                only_trash = not fish_only_items and chest_count == 0
            
                for key, qty in trash_items_caught.items():
                    if only_trash:
                        trash_info = ALL_FISH.get(key, {"description": "Unknown trash", "emoji": "🥾"})
                        trash_desc = trash_info.get('description', 'Unknown trash')
                        trash_emoji = trash_info.get('emoji', '🥾')
                        fish_display.append(f"{trash_emoji} {self.apply_display_glitch(trash_desc)}")
                    else:
                        trash_name = key.replace("trash_", "").replace("_", " ").title()
                        fish_display.append(f"🥾 {self.apply_display_glitch(trash_name)} x{qty}")
            
                # Track trash caught for achievement
                try:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                            (trash_count, user_id)
                        )
                        await db.commit()
                    # Track achievement: trash_master
                    try:
                        await increment_stat(user_id, "fishing", "trash_recycled", trash_count)
                        current_trash = await get_stat(user_id, "fishing", "trash_recycled")
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "trash_recycled", current_trash, channel)
                    except Exception as e:
                        print(f"[ACHIEVEMENT] Error tracking trash_recycled for {user_id}: {e}")
                except:
                    pass
                print(f"[FISHING] {username} caught trash: {trash_items_caught}")
        
            # Process chest (độc lập)
            if chest_count > 0:
                for _ in range(chest_count):
                    await self.add_inventory_item(user_id, "treasure_chest", "tool")
                fish_display.append(f"🎁 Rương Kho Báu x{chest_count}")
                print(f"[FISHING] {username} caught {chest_count}x TREASURE CHEST! 🎁")
                # Track chests caught for achievement
                try:
                    await increment_stat(user_id, "fishing", "chests_caught", chest_count)
                    current_chests = await get_stat(user_id, "fishing", "chests_caught")
                    await self.bot.achievement_manager.check_unlock(user_id, "fishing", "chests_caught", current_chests, channel)
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error updating chests_caught for {user_id}: {e}")
        
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
                            fish_name = self.apply_display_glitch(fish['name'])
                            fish_display.append(f"{fish['emoji']} {fish_name} x{qty} ({total_price} Hạt)")
                
                    print(f"[EVENT] {username} lost {fish_info['name']} to cat_steal")
                    # Track robbed count (cat steal counts as being robbed)
                    try:
                        await increment_stat(user_id, "fishing", "robbed_count", 1)  # stat update,
                        current_robbed = await get_stat(user_id, "fishing", "robbed_count")
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "robbed_count", current_robbed, channel)
                    except Exception as e:
                        print(f"[ACHIEVEMENT] Error updating robbed_count for {user_id}: {e}")
                    if fish_display:
                        fish_display[0] = fish_display[0] + f"\n(🐈 Mèo cướp mất {fish_info['name']} giá {highest_price} Hạt!)"
        
            # Update caught items for sell button
            self.caught_items[user_id] = fish_only_items
            
            # Check if bucket is full after fishing, if so, sell all fish instead of just caught
            updated_inventory = await get_inventory(user_id)
            current_fish_count = sum(v for k, v in updated_inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS)
            if current_fish_count >= FISH_BUCKET_LIMIT:
                all_fish_items = {k: v for k, v in updated_inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS}
                self.caught_items[user_id] = all_fish_items
                sell_items = all_fish_items
                print(f"[FISHING] Bucket full ({current_fish_count}/{FISH_BUCKET_LIMIT}), sell button will sell all fish")
            else:
                sell_items = fish_only_items
        
            # ==================== CHECK FOR LEGENDARY FISH ====================
            current_hour = datetime.now().hour
            legendary_fish = await check_legendary_spawn_conditions(user_id, channel.guild.id, current_hour, cog=self)

            if legendary_fish == "thuong_luong_expired":
                user_mention = f"<@{user_id}>"
                embed = discord.Embed(
                    title="🌊 SÓNG YÊN BIỂN LẶNG 🌊",
                    description=f"Nghi lễ hiến tế của {user_mention} đã kết thúc sau 5 phút.\n\n"
                                f"Dòng nước đã trở lại bình thường và sinh vật huyền thoại đã bỏ đi mất do không được câu lên kịp thời!",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Hãy nhanh tay hơn vào lần tới!")
                await channel.send(embed=embed)
                legendary_fish = None
        
            if legendary_fish:
                # Legendary fish spawned! Show boss fight minigame
                legendary_key = legendary_fish['key']
                print(f"[LEGENDARY] {username} encountered {legendary_key}!")
            
                # Create warning embed
                user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
                legendary_embed = discord.Embed(
                    title=f"⚠️ {user.display_name} - CẢNH BÁO: DÂY CÂU CĂNG CỰC ĐỘ!",
                    description=f"🌊 Có một con quái vật đang cắn câu!\n"
                               f"💥 Nó đang kéo bạn xuống nước!\n\n"
                               f"**{legendary_fish['emoji']} {self.apply_display_glitch(legendary_fish['name'])}**\n"
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
                boss_view = LegendaryBossFightView(self, user_id, legendary_fish, rod_durability, rod_lvl, channel, guild_id, user)
            
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
            
            # ==================== PHOENIX FEATHER DROP ====================
            # Drop Lông Vũ Lửa when failing to catch boss or rare fish (5-10% chance)
            if not legendary_fish and (chest_count > 0 or any(fish_key in RARE_FISH_KEYS for fish_key in fish_only_items.keys())):
                # Check if caught rare fish or chest (indicating boss-like encounter)
                drop_chance = random.random()
                if drop_chance < 0.08:  # 8% chance
                    await add_item(user_id, "long_vu_lua", 1)
                    print(f"[PHOENIX] {username} dropped Lông Vũ Lửa!")
                    
                    # Send notification
                    feather_embed = discord.Embed(
                        title="⭐ SAO BĂNG RƠI!",
                        description=f"Con quái vật đã thoát mất, nhưng sức nóng của nó để lại một chiếc **Lông Vũ Lửa** đang rực cháy trên tay bạn!\n\n🔥 **Lông Vũ Lửa** (x1)",
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=feather_embed)
        
            # Check if collection is complete and award title if needed
            is_complete = await check_collection_complete(user_id)
            title_earned = False
            if is_complete:
                current_title = await self.get_title(user_id, channel.guild.id)
                if not current_title or "Vua" not in current_title:
                    # Award "Vua Câu Cá" role
                    try:
                        guild = channel.guild
                        member = guild.get_member(user_id)
                        role_id = 1450409414111658024  # Vua Câu Cá role ID
                        role = guild.get_role(role_id)
                        if member and role and role not in member.roles:
                            await member.add_roles(role)
                            title_earned = True
                            print(f"[TITLE] {username} earned 'Vua Câu Cá' role!")
                    except Exception as e:
                        print(f"[TITLE] Error awarding role: {e}")
        
            # Build embed with item summary
            # FIX: Calculate total fish AFTER duplicate_multiplier is applied
            total_fish = sum(fish_only_items.values())
            total_catches = total_fish + trash_count + chest_count
        
            # Create summary text for title
            summary_parts = []
            for key, qty in fish_only_items.items():
                fish = ALL_FISH[key]
                fish_name = self.apply_display_glitch(fish['name'])
                summary_parts.append(f"{qty} {fish_name}")
            if chest_count > 0:
                summary_parts.append(f"{chest_count} Rương")
            
            summary_text = " và ".join(summary_parts) if summary_parts else "Rác"
            title = f"🎣 {username} Câu Được {summary_text}"
            
            if total_fish > 2:
                title = f"🎣 THỜI TỚI! {username} Bắt {total_fish} Con Cá! 🎉"
            
            # Add title-earned message if applicable
            if title_earned:
                title = f"🎣 {title}\n👑 **DANH HIỆU: VUA CÂU CÁ ĐƯỢC MỞ KHÓA!** 👑"
            
            # *** APPLY GLITCH TO TITLE ***
            title = self.apply_display_glitch(title)
        
            # Build description with broken rod warning if needed
            display_content = "\n".join(fish_display) if fish_display else "Không có gì"
            
            # *** APPLY DISPLAY GLITCH EFFECT ***
            display_content = self.apply_display_glitch(display_content)
            
            desc_parts = [display_content]
            if is_broken_rod:
                desc_parts.append("\n⚠️ **CẢNH BÁO: Cần câu gãy!** (Chỉ 1% cá hiếm, 1 item/lần, không rương)")
                desc_parts[-1] = self.apply_display_glitch(desc_parts[-1])
        
            embed = discord.Embed(
                title=title,
                description="".join(desc_parts),
                color=discord.Color.red() if is_broken_rod else (discord.Color.gold() if title_earned else (discord.Color.blue() if total_catches == 1 else discord.Color.gold()))
            )
        
            if title_earned:
                completion_text = "Bạn đã bắt được **tất cả các loại cá**!\nChúc mừng bạn trở thành **Vua Câu Cá**! 🎉\nXem `/suutapca` để xác nhận!"
                embed.add_field(
                    name="🏆 HOÀN THÀNH!",
                    value=self.apply_display_glitch(completion_text),
                    inline=False
                )
        
            # *** UPDATE DURABILITY AFTER FISHING ***
            old_durability = rod_durability
            rod_durability = max(0, rod_durability - durability_loss)
            await self.update_rod_data(user_id, rod_durability)
            print(f"[FISHING] [DURABILITY_UPDATE] {username} (user_id={user_id}) durability {old_durability} → {rod_durability} (loss: {durability_loss})")
        
            durability_status = f"🛡️ Độ bền còn lại: {rod_durability}/{rod_config['durability']}"
            if rod_durability <= 0:
                durability_status += f" ⚠️ CẦN SỬA ({rod_config['repair']} Hạt)"
            
            # *** APPLY GLITCH TO FOOTER ***
            footer_text = f"Tổng câu được: {total_catches} vật{boost_text} | {durability_status}"
            footer_text = self.apply_display_glitch(footer_text)
            embed.set_footer(text=footer_text)
        
            # Create view with sell button if there are fish to sell
            view = None
            if sell_items:
                view = FishSellView(self, user_id, sell_items, channel.guild.id)
                print(f"[FISHING] Created sell button for {username} with {len(sell_items)} fish types")
            else:
                print(f"[FISHING] No fish to sell, button not shown")
        
            await casting_msg.edit(content="", embed=embed, view=view)
            print(f"[FISHING] [RESULT_POST] {username} (user_id={user_id}) action=display_result")
        
            # ==================== NPC ENCOUNTER ====================
            if random.random() < NPC_ENCOUNTER_CHANCE and fish_only_items:
                await asyncio.sleep(NPC_ENCOUNTER_DELAY)  # Small delay for dramatic effect
            
                # Select random NPC based on weighted chances
                npc_pool = []
                for npc_key, npc_data in NPC_ENCOUNTERS.items():
                    npc_pool.extend([npc_key] * int(npc_data["chance"] * 100))
            
                npc_type = random.choice(npc_pool)
                npc_data = NPC_ENCOUNTERS[npc_type]
            
                # Get the first fish caught
                caught_fish_key = list(fish_only_items.keys())[0]
                caught_fish_info = ALL_FISH[caught_fish_key]
            
                # Build NPC embed
                npc_title = f"⚠️ {npc_data['name']} - {username}!"
                npc_desc = f"{npc_data['description']}\n\n**{username}**, {npc_data['question']}"
                npc_embed = discord.Embed(
                    title=self.apply_display_glitch(npc_title),
                    description=self.apply_display_glitch(npc_desc),
                    color=discord.Color.purple()
                )
            
                if npc_data.get("image_url"):
                    npc_embed.set_image(url=npc_data["image_url"])
            
                # Add cost information
                cost_text = ""
                if npc_data["cost"] == "fish":
                    cost_text = f"💰 **Chi phí:** {caught_fish_info['emoji']} {caught_fish_info['name']}"
                elif isinstance(npc_data["cost"], int):
                    cost_text = f"💰 **Chi phí:** {npc_data['cost']} Hạt"
                elif npc_data["cost"] == "cooldown_5min":
                    cost_text = f"💰 **Chi phí:** Mất lượt câu trong 5 phút"
            
                npc_embed.add_field(name="💸 Giá", value=self.apply_display_glitch(cost_text), inline=False)
            
                # Send NPC message with buttons
                npc_view = NPCEncounterView(user_id, npc_type, npc_data, caught_fish_key)
                
                # Track achievement stats for NPC encounters
                from .constants import NPC_EVENT_STAT_MAPPING
                if npc_type in NPC_EVENT_STAT_MAPPING:
                    stat_key = NPC_EVENT_STAT_MAPPING[npc_type]
                    try:
                        await increment_stat(user_id, "fishing", stat_key, 1)
                        current_value = await get_stat(user_id, "fishing", stat_key)
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, channel)
                        print(f"[ACHIEVEMENT] Tracked {stat_key} for user {user_id} on NPC encounter {npc_type}")
                    except Exception as e:
                        print(f"[ACHIEVEMENT] Error tracking {stat_key} for {user_id}: {e}")
                
                npc_msg = await channel.send(content=f"<@{user_id}>", embed=npc_embed, view=npc_view)
            
                await npc_view.wait()
            
                result_text = ""
                result_color = discord.Color.default()
            
                if npc_view.value == "agree":
                    # Process acceptance
                    result_embed = await self._process_npc_acceptance(user_id, npc_type, npc_data, caught_fish_key, caught_fish_info, username)
                    await npc_msg.edit(content=f"<@{user_id}>", embed=result_embed, view=None)
            
                elif npc_view.value == "decline":
                    # Process decline (includes manual decline and timeout auto-decline)
                    result_text = npc_data["rewards"]["decline"]
                    result_color = discord.Color.light_grey()
                    result_embed = discord.Embed(
                        title=f"{npc_data['name']} - {username} - Từ Chối",
                        description=f"{result_text}",
                        color=result_color
                    )
                    await npc_msg.edit(content=f"<@{user_id}>", embed=result_embed, view=None)
                    print(f"[NPC] {username} declined {npc_type}")
            
            # ==================== FINAL COOLDOWN CHECK ====================
            # If global_reset was triggered, ensure user has no cooldown
            if triggers_global_reset:
                # Clear the user's cooldown that was set earlier
                if user_id in self.fishing_cooldown:
                    del self.fishing_cooldown[user_id]
                print(f"[FISHING] [GLOBAL_RESET] {username} cooldown cleared due to global reset event")
        
        except Exception as e:
            # Catch-all error handler for _fish_action
            print(f"[FISHING] [ERROR] Unexpected error in _fish_action: {e}")
            import traceback
            traceback.print_exc()
            try:
                error_embed = discord.Embed(
                    title="❌ Lỗi Câu Cá",
                    description=f"Xảy ra lỗi không mong muốn: {str(e)[:100]}\n\nVui lòng thử lại sau.",
                    color=discord.Color.red()
                )
                if is_slash:
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
            except:
                pass
    
    
    @app_commands.command(name="banca", description="Bán cá - Dùng /banca [fish_types]")
    @app_commands.describe(fish_types="Fish key phân cách bằng dấu phẩy (ví dụ: ca_ro hoặc ca_chep, ca_koi)")
    async def sell_fish_slash(self, interaction: discord.Interaction, fish_types: str = None):
        """Sell selected fish via slash command"""
        await self._sell_fish_action(interaction, fish_types)
    
    @commands.command(name="banca", description="Bán cá - Dùng !banca [fish_types]")
    async def sell_fish_prefix(self, ctx, *, fish_types: str = None):
        """Sell selected fish via prefix command"""
        await self._sell_fish_action(ctx, fish_types)
    
    async def _sell_fish_action(self, ctx_or_interaction, fish_types: str = None):
        """Sell all fish or specific types logic with RANDOM EVENTS"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            user_id = ctx_or_interaction.user.id
        else:
            user_id = ctx_or_interaction.author.id
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - sell fish")
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            ctx = ctx_or_interaction
        else:
            ctx = ctx_or_interaction
        
        # CRITICAL: Check if sell is already being processed (prevent duplicate execution)
        import time
        current_time = time.time()
        if user_id in self.sell_processing:
            last_sell_time = self.sell_processing[user_id]
            if current_time - last_sell_time < 3:  # 3 second cooldown
                print(f"[FISHING] [SELL_DUPLICATE_BLOCKED] user_id={user_id} time_diff={current_time - last_sell_time:.2f}s")
                msg = "⏳ Đang xử lý lệnh bán cá trước đó..."
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
        
        # Mark as processing
        self.sell_processing[user_id] = current_time
        
        try:
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
                from .glitch import apply_display_glitch as _glitch
                legend_names = ", ".join([_glitch(ALL_FISH[k]['name']) for k in legendary_fish_in_inventory.keys()])
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
            
            # Exclude pearl from auto-sell unless explicitly requested
            if not fish_types:
                fish_items = {k: v for k, v in fish_items.items() if k != "pearl"}
            
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
                # Map ngoc_trai to pearl
                requested_mapped = []
                for req in requested:
                    if req == "ngoc_trai":
                        requested_mapped.append("pearl")
                    else:
                        requested_mapped.append(req)
                selected_fish = {k: v for k, v in fish_items.items() if k in requested_mapped}
                
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
            
            # 1. Tính tổng tiền gốc (trước buff và event)
            base_total = 0
            for fish_key, quantity in selected_fish.items():
                fish_info = ALL_FISH.get(fish_key)
                if fish_info:
                    base_price = fish_info['sell_price']
                    base_total += base_price * quantity
            
            # 2. Xử lý sự kiện bán hàng (Sell Event) - áp dụng trước buff
            event_total = base_total
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
                # Track achievement stats for events
                from .constants import SELL_EVENT_STAT_MAPPING
                if triggered_event in SELL_EVENT_STAT_MAPPING:
                    stat_key = SELL_EVENT_STAT_MAPPING[triggered_event]
                    try:
                        await increment_stat(user_id, "fishing", stat_key, 1)
                        current_value = await get_stat(user_id, "fishing", stat_key)
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, ctx.channel)
                        print(f"[ACHIEVEMENT] Tracked {stat_key} for user {user_id} on sell event {triggered_event}")
                    except Exception as e:
                        print(f"[ACHIEVEMENT] Error tracking {stat_key} for {user_id}: {e}")
                
                ev_data = SELL_EVENTS[triggered_event]
                event_name = ev_data["name"]
                
                # Tính toán tiền sau sự kiện
                # Công thức: (Gốc * Multiplier) + Flat Bonus
                event_total = int(base_total * ev_data["mul"]) + ev_data["flat"]
                
                # Prevent negative balance
                current_balance = await get_user_balance(user_id)
                if event_total < 0 and current_balance + event_total < 0:
                    event_total = -current_balance
                    print(f"[FISHING] [SELL_EVENT] {username} (user_id={user_id}) Penalty capped to prevent negative balance: {event_total}")
                
                # Cho phép âm tiền nếu sự kiện xấu quá nghiêm trọng (but capped above)
                
                diff = event_total - base_total
                sign = "+" if diff >= 0 else ""
                
                # Xử lý special effects (vật phẩm thưởng)
                if "special" in ev_data:
                    special_type = ev_data["special"]
                    
                    if special_type == "chest":
                        await self.add_inventory_item(user_id, "treasure_chest", "tool")
                        special_rewards.append("🎁 +1 Rương Kho Báu")
                        # Track chest gained from sell event
                        try:
                            await increment_stat(user_id, "fishing", "chests_caught", 1)
                            current_chests = await get_stat(user_id, "fishing", "chests_caught")
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "chests_caught", current_chests, ctx.channel)
                        except Exception as e:
                            print(f"[ACHIEVEMENT] Error updating chests_caught (sell special) for {user_id}: {e}")
                    
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
                            event_total += lottery_reward
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
                    
                print(f"[FISHING] [SELL_EVENT] {ctx.user.name if is_slash else ctx.author.name} (user_id={ctx.user.id if is_slash else ctx.author.id}) event={triggered_event} seed_change={event_total - base_total} fish_count={len(selected_fish)}")

            # Apply harvest boost (x2) if active in the server - áp dụng sau sự kiện
            final_total = event_total
            is_harvest_boosted = False
            try:
                guild_id = ctx.guild.id if hasattr(ctx, 'guild') else ctx_or_interaction.guild.id
                if guild_id:
                    result = await db_manager.fetchone(
                        "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                        (guild_id,)
                    )
                    if result and result[0]:
                        buff_until = datetime.fromisoformat(result[0])
                        if datetime.now() < buff_until:
                            # Only apply buff to positive earnings
                            if final_total > 0:
                                final_total = final_total * 2  # Double the event reward
                                is_harvest_boosted = True
                            print(f"[FISHING] [SELL_ACTION] Applied harvest boost x2 for user {user_id}")
            except Exception as e:
                print(f"[FISHING] [SELL_ACTION] Error checking harvest boost: {e}")

            # Remove items & Add money (ATOMIC TRANSACTION - xảy ra cùng lúc)
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    # Start transaction
                    await db.execute("BEGIN TRANSACTION")
                    
                    try:
                        # 1. Remove all fish items
                        for fish_key in selected_fish.keys():
                            await db.execute(
                                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?",
                                (selected_fish[fish_key], user_id, fish_key)
                            )
                        
                        # 1.1. Delete items with quantity <= 0
                        await db.execute(
                            "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                            (user_id,)
                        )
                        
                        # 2. Add seeds to user (with balance tracking)
                        # Get balance before
                        async with db.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,)) as cursor:
                            row = await cursor.fetchone()
                            balance_before = row[0] if row else 0
                        
                        # Update seeds
                        await db.execute(
                            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                            (final_total, user_id)
                        )
                        
                        # Track total money earned for achievements
                        await increment_stat(user_id, "fishing", "total_money_earned", final_total)
                        
                        # Log the balance change
                        balance_after = balance_before + final_total
                        print(f"[FISHING] [SEED_CHANGE] user_id={user_id} amount=+{final_total} balance_before={balance_before} balance_after={balance_after}")

                        # 2.1. Track event-based achievements
                        try:
                            if triggered_event == "market_boom":
                                await increment_stat(user_id, "fishing", "market_boom_sales", 1)  # stat update,
                            elif triggered_event == "god_of_wealth":
                                await increment_stat(user_id, "fishing", "god_of_wealth_encountered", 1)  # stat update,
                            elif triggered_event == "thief_run":
                                await increment_stat(user_id, "fishing", "robbed_count", 1)  # stat update,
                        except Exception as e:
                            print(f"[ACHIEVEMENT] Error updating sell-event counters for {user_id}: {e}")
                        
                        # Commit transaction
                        await db.commit()
                        
                        # Check achievements for sell events
                        if triggered_event == "market_boom":
                            current_market_boom = await get_stat(user_id, "fishing", "market_boom_sales")
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "market_boom_sales", current_market_boom, ctx.channel)
                        elif triggered_event == "god_of_wealth":
                            current_god_wealth = await get_stat(user_id, "fishing", "god_of_wealth_encountered")
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "god_of_wealth_encountered", current_god_wealth, ctx.channel)
                        elif triggered_event == "thief_run":
                            current_robbed = await get_stat(user_id, "fishing", "robbed_count")
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "robbed_count", current_robbed, ctx.channel)
                        
                        # CRITICAL: Invalidate inventory cache after successful transaction
                        db_manager.clear_cache_by_prefix(f"inventory_{user_id}")
                        print(f"[FISHING] [SELL_TRANSACTION] Success: user_id={user_id} total={final_total} fish_count={len(selected_fish)}")
                        
                    except Exception as e:
                        # Rollback on error
                        await db.execute("ROLLBACK")
                        print(f"[FISHING] [SELL_TRANSACTION] Rollback due to error: {e}")
                        raise
            except Exception as e:
                print(f"[FISHING] [SELL_ERROR] Transaction failed: {e}")
                err_msg = f"❌ Lỗi khi bán cá: {str(e)}"
                if is_slash:
                    await ctx.followup.send(err_msg, ephemeral=True)
                else:
                    await ctx.send(err_msg)
                return
            
            # 4. Display sell event notification FIRST (if triggered)
            if triggered_event:
                from .glitch import is_glitch_active, apply_display_glitch as glitch_text
                
                if SELL_EVENTS[triggered_event]["type"] == "good":
                    title = f"🌟 PHƯỚC LÀNH - {username}!"
                    event_embed_color = discord.Color.gold()
                else:
                    title = f"⚠️ KIẾP NẠN - {username}!"
                    event_embed_color = discord.Color.orange()
                
                # Apply glitch if active
                if is_glitch_active():
                    title = glitch_text(title)
                
                diff = event_total - base_total
                sign = "+" if diff >= 0 else ""
                event_detail = f"{SELL_MESSAGES[triggered_event]}\n\n💰 **{event_name}**"
                
                if is_glitch_active():
                    event_detail = glitch_text(event_detail)
                
                event_embed = discord.Embed(
                    title=title,
                    description=event_detail,
                    color=event_embed_color
                )
                
                impact_text = f"Gốc: {base_total} Hạt\n{sign}{diff} Hạt\n**= {event_total} Hạt**"
                if is_glitch_active():
                    impact_text = glitch_text(impact_text)
                
                event_embed.add_field(
                    name="📊 Ảnh hưởng giá bán",
                    value=impact_text,
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
            from .glitch import apply_display_glitch as _glitch, is_glitch_active
            
            if is_glitch_active():
                fish_summary = "\n".join([f"  • {_glitch(ALL_FISH[k]['name'])} x{_glitch(str(v))}" for k, v in selected_fish.items()])
                embed_title = _glitch(f"💰 **{username}** bán {sum(selected_fish.values())} con cá")
                embed_desc = _glitch(f"{fish_summary}")
            else:
                fish_summary = "\n".join([f"  • {_glitch(ALL_FISH[k]['name'])} x{v}" for k, v in selected_fish.items()])
                embed_title = f"💰 **{username}** bán {sum(selected_fish.values())} con cá"
                embed_desc = f"{fish_summary}"
            
            # Add buff information
            if is_harvest_boosted:
                if is_glitch_active():
                    embed_desc += _glitch(f"\n\n🌟 **Buff Từ Cây Server x2!**\n💵 **Gốc:** {_glitch(str(event_total))} Hạt → **Sau buff:** {_glitch(str(final_total))} Hạt")
                else:
                    embed_desc += f"\n\n🌟 **Buff Từ Cây Server x2!**\n💵 **Gốc:** {event_total} Hạt → **Sau buff:** {final_total} Hạt"
            else:
                if is_glitch_active():
                    embed_desc += _glitch(f"\n\n💵 **Tổng nhận:** {_glitch(str(final_total))} Hạt")
                else:
                    embed_desc += f"\n\n💵 **Tổng nhận:** {final_total} Hạt"
            
            embed = discord.Embed(
                title=embed_title,
                description=embed_desc,
                color=discord.Color.green()
            )
            
            # Check achievement "millionaire" after sale
            current_money_earned = await get_stat(user_id, "fishing", "total_money_earned")
            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "total_money_earned", current_money_earned, ctx.channel)

            if is_slash:
                await ctx.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)
        except Exception as e:
            # Handle any exceptions during selling
            print(f"Error in _sell_fish_action: {e}")
            import traceback
            traceback.print_exc()
            msg = "❌ Có lỗi xảy ra khi bán cá. Vui lòng thử lại!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        finally:
            # Clear processing flag after completion or error
            if user_id in self.sell_processing:
                del self.sell_processing[user_id]
    
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
            user_id = ctx_or_interaction.user.id
            user_name = ctx_or_interaction.user.name
        else:
            user_id = ctx_or_interaction.author.id
            user_name = ctx_or_interaction.author.name
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            print(f"[EVENT] {user_name} experienced lag delay (3s) - open chest")
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
            ctx = ctx_or_interaction
        else:
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
        
        # Get rod level for luck calculation
        rod_level, _ = await get_rod_data(user_id)
        
        # Calculate item count based on rod level (luck)
        # Higher rod level = better luck = more items
        # Level 1: 0: 80%, 1: 15%, 2: 4%, 3: 1%
        # Level 2: 0: 70%, 1: 20%, 2: 8%, 3: 2%
        # Level 3: 0: 60%, 1: 25%, 2: 12%, 3: 3%
        # Level 4: 0: 50%, 1: 30%, 2: 16%, 3: 4%
        # Level 5: 0: 40%, 1: 35%, 2: 20%, 3: 5%
        base_zero_chance = 80 - (rod_level - 1) * 10  # Decrease by 10% per level
        zero_chance = max(40, base_zero_chance)  # Min 40%
        one_chance = 15 + (rod_level - 1) * 5  # Increase by 5% per level
        two_chance = 4 + (rod_level - 1) * 4  # Increase by 4% per level
        three_chance = 1 + (rod_level - 1) * 1  # Increase by 1% per level
        
        # Normalize to ensure sum = 100%
        total = zero_chance + one_chance + two_chance + three_chance
        zero_chance = int(zero_chance / total * 100)
        one_chance = int(one_chance / total * 100)
        two_chance = int(two_chance / total * 100)
        three_chance = 100 - zero_chance - one_chance - two_chance  # Ensure sum = 100
        
        item_counts = [0, 1, 2, 3]
        weights = [zero_chance, one_chance, two_chance, three_chance]
        num_items = random.choices(item_counts, weights=weights, k=1)[0]
        
        print(f"[CHEST] {user_name} (rod_level={rod_level}) rolled {num_items} items")
        
        # Roll items
        loot_items = []
        for _ in range(num_items):
            items = list(CHEST_LOOT.keys())
            weights = list(CHEST_LOOT.values())
            loot_type = random.choices(items, weights=weights, k=1)[0]
            loot_items.append(loot_type)
        
        # Process loot and build display
        loot_display = []
        trash_only = all(item in [t.get("key") for t in TRASH_ITEMS] for item in loot_items) and len(loot_items) == 1
        
        for loot_type in loot_items:
            if loot_type == "nothing":
                # Skip nothing items
                continue
            
            elif loot_type == "fertilizer":
                await self.add_inventory_item(user_id, "fertilizer", "tool")
                loot_display.append("🌾 Phân Bón (Dùng `/bonphan` để nuôi cây)")
            
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
                    
                    loot_display.append(f"🧩 Mảnh Ghép {piece_display} → 🎉 **ĐỦ 4 MẢNH - TỰ ĐỘNG GHÉP!** 💰 **{reward} Hạt!**")
                else:
                    loot_display.append(f"🧩 Mảnh Ghép {piece_display} (Gom đủ 4 mảnh A-B-C-D để đổi quà siêu to!)")
            
            elif loot_type == "coin_pouch":
                coins = random.randint(100, 200)
                await add_seeds(user_id, coins)
                loot_display.append(f"💰 Túi Hạt - **{coins} Hạt**")
            
            # Check if it's a trash item
            elif loot_type in [t.get("key") for t in TRASH_ITEMS]:
                trash_item = next((t for t in TRASH_ITEMS if t.get("key") == loot_type), None)
                if trash_item:
                    await self.add_inventory_item(user_id, loot_type, "trash")
                    if trash_only:
                        # Display description for single trash
                        trash_desc = trash_item.get('description', 'Unknown trash')
                        loot_display.append(f"{trash_item['emoji']} {self.apply_display_glitch(trash_desc)}")
                    else:
                        loot_display.append(f"🗑️ {trash_item['name']}")
            
            else:  # gift_random
                gift = random.choice(GIFT_ITEMS)
                await self.add_inventory_item(user_id, gift, "gift")
                gift_names = {"cafe": "☕ Cà Phê", "flower": "🌹 Hoa", "ring": "💍 Nhẫn", 
                             "gift": "🎁 Quà", "chocolate": "🍫 Sô Cô La", "card": "💌 Thiệp"}
                loot_display.append(f"{gift_names[gift]} (Dùng `/tangqua` để tặng cho ai đó)")
        
        # Build embed
        if num_items == 0 or not loot_display:
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description="**❌ Rương trống không - Không có gì cả!**",
                color=discord.Color.greyple()
            )
        else:
            loot_text = "\n".join(loot_display)
            embed = discord.Embed(
                title="🎁 Rương Kho Báu",
                description=loot_text,
                color=discord.Color.gold()
            )
        
        embed.set_footer(text=f"👤 {user_name} | Cấp Cần: {rod_level}")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    # ==================== LEGENDARY SUMMONING ====================
    
    @app_commands.command(name="hiente", description="🌊 Hiến Tế Cá Cho Sông - Chỉ cá có giá > 150 hạt")
    @app_commands.describe(fish_key="Fish key - chỉ cá có giá > 150 hạt (vd: ca_chep_vang, ca_chim)")
    async def hiente_slash(self, interaction: discord.Interaction, fish_key: str):
        await self._hiente_action(interaction, fish_key, is_slash=True)
    
    @commands.command(name="hiente", description="🌊 Hiến Tế Cá - Dùng !hiente [fish_key] (cá > 150 hạt)")
    async def hiente_prefix(self, ctx, fish_key: str = None):
        if not fish_key:
            embed = discord.Embed(
                title="❌ Thiếu tham số",
                description="**Cú pháp:** `!hiente <fish_key>`\n\n**Ví dụ:** `!hiente ca_chep_vang`\n\n**Lưu ý:** Chỉ cá có giá bán > 150 hạt",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        await self._hiente_action(ctx, fish_key, is_slash=False)
    
    async def _hiente_action(self, ctx_or_interaction, fish_key: str, is_slash: bool):
        """Sacrifice fish to Thuồng Luồng"""
        is_slash_cmd = is_slash
        
        if is_slash_cmd:
            user_id = ctx_or_interaction.user.id
            channel = ctx_or_interaction.channel
            guild_id = ctx_or_interaction.guild.id
        else:
            user_id = ctx_or_interaction.author.id
            channel = ctx_or_interaction.channel
            guild_id = ctx_or_interaction.guild.id
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash_cmd else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - sacrifice fish")
        
        if is_slash_cmd:
            await ctx_or_interaction.response.defer()
        
        # Check if user already has Thuồng Luồng
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM fish_collection WHERE user_id = ? AND fish_key = 'thuong_luong'",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] > 0:
                        embed = discord.Embed(
                            title="🌊 DÒNG SÔNG TỪ CHỐI!",
                            description="Mặt nước tĩnh lặng không gợn sóng... Bóng ma dưới đáy sông đã chấp nhận bạn là chủ nhân rồi. Thủy Thần không cần thêm lễ vật nữa, hãy giữ lại những chú cá này đi!",
                            color=discord.Color.gold()
                        )
                        if is_slash_cmd:
                            await ctx_or_interaction.followup.send(embed=embed)
                        else:
                            await ctx_or_interaction.send(embed=embed)
                        return
        except Exception as e:
            print(f"[HIENTE] Error checking thuong_luong ownership: {e}")
        
        # Check if fish_key is valid (common or rare fish only, not legendary)
        if fish_key not in COMMON_FISH_KEYS + RARE_FISH_KEYS:
            embed = discord.Embed(
                title="❌ Loại Cá Không Hợp Lệ",
                description=f"Chỉ có thể hiến tế cá thường hoặc hiếm. Không tìm thấy: `{fish_key}`",
                color=discord.Color.red()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Check if fish sell price is > 150
        fish_sell_price = ALL_FISH[fish_key].get('sell_price', 0)
        if fish_sell_price <= 150:
            embed = discord.Embed(
                title="❌ Cá Không Đủ Tiêu Chuẩn",
                description=f"Chỉ có thể hiến tế cá có giá bán **trên 150 Hạt**!\n\n**{global_apply_display_glitch(ALL_FISH[fish_key]['name'])}** chỉ bán được **{fish_sell_price} Hạt**.",
                color=discord.Color.red()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Check if user has this fish
        inventory = await get_inventory(user_id)
        if inventory.get(fish_key, 0) < 1:
            embed = discord.Embed(
                title="❌ Không Có Cá",
                description=f"Bạn không có {global_apply_display_glitch(ALL_FISH[fish_key]['name'])} để hiến tế",
                color=discord.Color.red()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Check if there's heavy rain (mưa bão event)
        # For now, accept any time (you can add weather check later)
        
        # Remove fish from inventory
        await remove_item(user_id, fish_key, 1)
        
        # Increment sacrifice counter (using database, not RAM)
        current_sacrifices = await self.add_sacrifice_count(user_id, 1)
        
        # Check dragon_slayer achievement (100 sacrifices)
        current_legendary = await get_stat(user_id, "fishing", "legendary_caught")
        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "legendary_caught", current_legendary, channel)
        
        fish_name = global_apply_display_glitch(ALL_FISH[fish_key]['name'])
        fish_emoji = ALL_FISH[fish_key]['emoji']
        
        if current_sacrifices < 3:
            embed = discord.Embed(
                title="🌊 Đã Hiến Tế 🌊",
                description=f"Bạn ném {fish_emoji} **{fish_name}** xuống dòng sông...\n\n⏳ Tiến độ: {current_sacrifices}/3 cá\n\nHiến tế thêm {3 - current_sacrifices} con để hoàn thành lễ!",
                color=discord.Color.blue()
            )
        else:
            # Set the ritual start time
            self.thuong_luong_timers[user_id] = time.time()
            embed = discord.Embed(
                title="⚡ LỄ VẬT HOÀN THÀNH ⚡",
                description=f"Bạn ném {fish_emoji} **{fish_name}** xuống dòng sông lần thứ 3!\n\n🌊 Dòng nước xoáy dữ dội! Trong **5 phút** tới, bạn có cơ hội gặp **THUỒNG LUỒNG**!",
                color=discord.Color.gold()
            )
        
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @app_commands.command(name="chetao", description="✨ Chế Tạo Vật Phẩm - Dùng /chetao item_key")
    @app_commands.describe(item_key="Item key: moi_sao, tinh_cau, etc.")
    async def chetao_slash(self, interaction: discord.Interaction, item_key: str = None):
        await self._chetao_action(interaction, item_key, is_slash=True)
    
    @commands.command(name="chetao", description="✨ Chế Tạo Vật Phẩm - Dùng !chetao [item_key]")
    async def chetao_prefix(self, ctx, item_key: str = None):
        await self._chetao_action(ctx, item_key, is_slash=False)
    
    async def _chetao_action(self, ctx_or_interaction, item_key: str, is_slash: bool):
        """Craft items"""
        is_slash_cmd = is_slash
        
        if is_slash_cmd:
            user_id = ctx_or_interaction.user.id
        else:
            user_id = ctx_or_interaction.author.id
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash_cmd else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - craft item")
        
        if is_slash_cmd:
            await ctx_or_interaction.response.defer()
        
        # Define recipes
        recipes = {
            "moi_sao": {
                "ingredients": {"manh_sao_bang": 1, "worm": 5},
                "result": "manh_sao_bang",
                "description": "Mảnh Sao Băng để thu hút Cá Ngân Hà (legacy)"
            },
            "tinh_cau": {
                "ingredients": {"manh_sao_bang": 5, "pearl": 1},
                "result": "tinh_cau",
                "description": "Tinh Cầu Không Gian để triệu hồi Cá Ngân Hà"
            }
        }
        
        # Show recipes if no item_key specified
        if not item_key:
            embed = discord.Embed(
                title="✨ CÔNG THỨC CHẾ TẠO ✨",
                description="Sử dụng các công thức dưới đây để chế tạo vật phẩm đặc biệt",
                color=discord.Color.purple()
            )
            for key, data in recipes.items():
                ingredients_str = ", ".join([f"{qty} {ALL_FISH.get(ing, {}).get('name', ing)}" for ing, qty in data["ingredients"].items()])
                embed.add_field(
                    name=f"🔧 {key}",
                    value=f"**Nguyên liệu:** {ingredients_str}\n**Kết quả:** {data['description']}",
                    inline=False
                )
            embed.set_footer(text="Sử dụng: !chetao item_key hoặc /chetao item_key")
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Check if item_key exists
        if item_key not in recipes:
            embed = discord.Embed(
                title="❌ Công Thức Không Tồn Tại",
                description=f"Không tìm thấy công thức: `{item_key}`",
                color=discord.Color.red()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        recipe = recipes[item_key]
        inventory = await get_inventory(user_id)
        
        # Check ingredients
        missing = []
        for ing, qty in recipe["ingredients"].items():
            if inventory.get(ing, 0) < qty:
                item_name = ALL_FISH.get(ing, {}).get('name', ing)
                missing.append(f"{qty} {item_name}")
        
        if missing:
            embed = discord.Embed(
                title="❌ Không Đủ Nguyên Liệu",
                description="Cần:\n" + "\n".join(missing),
                color=discord.Color.red()
            )
        else:
            # Craft!
            if item_key == "tinh_cau":
                # Special handling for Tinh Cầu - use quest system
                success = await craft_tinh_cau(user_id)
                if not success:
                    embed = discord.Embed(
                        title="❌ Chế Tạo Thất Bại",
                        description="Không đủ nguyên liệu hoặc lỗi hệ thống.",
                        color=discord.Color.red()
                    )
                else:
                    result_name = "Tinh Cầu Không Gian"
                    embed = discord.Embed(
                        title="✨ CHẾ TẠO THÀNH CÔNG ✨",
                        description=f"Bạn đã chế tạo **{result_name}**!\n\n{recipe['description']}",
                        color=discord.Color.gold()
                    )
            else:
                # Normal crafting
                for ing, qty in recipe["ingredients"].items():
                    await remove_item(user_id, ing, qty)
                await add_item(user_id, recipe["result"], 1)
                
                result_name = ALL_FISH.get(recipe["result"], {}).get('name', recipe["result"])
                embed = discord.Embed(
                    title="✨ CHẾ TẠO THÀNH CÔNG ✨",
                    description=f"Bạn đã chế tạo **{result_name}**!\n\n{recipe['description']}",
                    color=discord.Color.gold()
                )
        
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @app_commands.command(name="dosong", description="📡 Dò Tần Số Cá Voi 52Hz - Mini-game")
    async def dosong_slash(self, interaction: discord.Interaction):
        await self._dosong_action(interaction, is_slash=True)
    
    @commands.command(name="dosong", description="📡 Dò Tần Số Cá Voi 52Hz")
    async def dosong_prefix(self, ctx):
        await self._dosong_action(ctx, is_slash=False)
    
    async def _dosong_action(self, ctx_or_interaction, is_slash: bool):
        """Mini-game to detect whale frequency"""
        is_slash_cmd = is_slash
        
        if is_slash_cmd:
            user_id = ctx_or_interaction.user.id
        else:
            user_id = ctx_or_interaction.author.id
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash_cmd else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - whale detection")
        
        if is_slash_cmd:
            await ctx_or_interaction.response.defer()
        
        # Check if user already has Cá Voi 52Hz
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM fish_collection WHERE user_id = ? AND fish_key = 'ca_voi_52hz'",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] > 0:
                        embed = discord.Embed(
                            title="� TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI",
                            description="Máy dò sóng chỉ phát ra những tiếng rè tĩnh lặng... Tần số 52Hz cô đơn nhất đại dương không còn lạc lõng nữa, vì nó đã tìm thấy bạn. Không còn tín hiệu nào khác để dò tìm.",
                            color=discord.Color.gold()
                        )
                        if is_slash_cmd:
                            await ctx_or_interaction.followup.send(embed=embed)
                        else:
                            await ctx_or_interaction.send(embed=embed)
                        return
        except Exception as e:
            print(f"[DOSONG] Error checking ca_voi_52hz ownership: {e}")
        
        # Check if user has "Máy Dò Sóng"
        inventory = await get_inventory(user_id)
        if inventory.get("may_do_song", 0) < 1:
            embed = discord.Embed(
                title="❌ Không Có Dụng Cụ",
                description="Bạn cần **Máy Dò Sóng** để dò tần số. Mua ở shop với giá 20000 Hạt",
                color=discord.Color.red()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Remove the device (use once)
        await remove_item(user_id, "may_do_song", 1)
        
        # Random frequency 0-100
        detected_freq = random.randint(0, 100)
        
        if detected_freq == 52:
            # SUCCESS! Set flag using ConsumableCog
            consumable_cog = self.bot.get_cog("ConsumableCog")
            if consumable_cog:
                consumable_cog.detected_52hz[user_id] = True
            
            embed = discord.Embed(
                title="📡 ĐÃ BẮT ĐƯỢC TẦN SỐ 📡",
                description=f"🎯 **{detected_freq}Hz** - Đây là tần số cô đơn!\n\n💔 Bạn nghe thấy tiếng kêu buồn bã từ đại dương sâu thẳm...\n\n⚡ Lần quăng cần ngay sau đây **CHẮC CHẮN 100%** sẽ gặp **CÁ VOI 52Hz**!",
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="📡 TẦN SỐ PHÁT HIỆN 📡",
                description=f"🔊 Tần số: **{detected_freq}Hz**\n\n❌ Không phải tần số cô đơn... Hãy thử lại sau!",
                color=discord.Color.greyple()
            )
        
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    @app_commands.command(name="ghepbando", description="🗺️ Ghép 4 Mảnh Bản Đồ → Bản Đồ Hắc Ám")
    async def ghepbando_slash(self, interaction: discord.Interaction):
        await self._ghepbando_action(interaction, is_slash=True)
    
    @commands.command(name="ghepbando", description="🗺️ Ghép Bản Đồ")
    async def ghepbando_prefix(self, ctx):
        await self._ghepbando_action(ctx, is_slash=False)
    
    async def _ghepbando_action(self, ctx_or_interaction, is_slash: bool):
        """Combine 4 map pieces into dark map"""
        is_slash_cmd = is_slash
        
        if is_slash_cmd:
            user_id = ctx_or_interaction.user.id
        else:
            user_id = ctx_or_interaction.author.id
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash_cmd else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - combine map")
        
        if is_slash_cmd:
            await ctx_or_interaction.response.defer()
        
        # Check if user already has Cthulhu Non
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM fish_collection WHERE user_id = ? AND fish_key = 'cthulhu_con'",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] > 0:
                        embed = discord.Embed(
                            title="🐙 Đã Hoàn Thành Nhiệm Vụ",
                            description="Bạn đã sở hữu **Cthulhu Non** rồi! Không thể thực hiện nhiệm vụ này nữa.",
                            color=discord.Color.gold()
                        )
                        if is_slash_cmd:
                            await ctx_or_interaction.followup.send(embed=embed)
                        else:
                            await ctx_or_interaction.send(embed=embed)
                        return
        except Exception as e:
            print(f"[GHEPBANDO] Error checking cthulhu_con ownership: {e}")
        
        # Check if user has all 4 pieces
        inventory = await get_inventory(user_id)
        pieces_needed = ["manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d"]
        missing_pieces = []
        
        for piece in pieces_needed:
            if inventory.get(piece, 0) < 1:
                missing_pieces.append(piece)
        
        if missing_pieces:
            # Build missing pieces display
            piece_display = []
            for item in LEGENDARY_ITEMS:
                if item["key"] in missing_pieces:
                    piece_display.append(f"❌ {item['name']}")
            missing_text = "\n".join(piece_display)
            
            embed = discord.Embed(
                title="❌ Thiếu Mảnh Bản Đồ",
                description=f"Cần tất cả 4 mảnh bản đồ:\n\n{missing_text}",
                color=discord.Color.red()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        # Remove all pieces
        for piece in pieces_needed:
            await remove_item(user_id, piece, 1)
        
        # Give dark map (as a tool)
        await self.add_inventory_item(user_id, "ban_do_ham_am", "tool")
        
        # Set flag
        self.dark_map_active[user_id] = True
        self.dark_map_casts[user_id] = 10  # 10 casts to use the map
        self.dark_map_cast_count[user_id] = 0  # Initialize cast counter
        
        embed = discord.Embed(
            title="🗺️ GHÉP BẢN ĐỒ THÀNH CÔNG 🗺️",
            description="Bạn đã ghép 4 mảnh bản đồ lại với nhau!\n\n📜 **Bản Đồ Hắc Ám** được hoàn thành!\n\n🐙 Bây giờ **Cthulhu Non** sẽ xuất hiện trong **10 lần câu** tiếp theo.\n⚡ Hãy câu ngay trước khi bản đồ tan biến!",
            color=discord.Color.gold()
        )
        
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    # ==================== CRAFT/RECYCLE ====================
    
    @app_commands.command(name="taiche", description="Tái chế rác - 10 rác → 1 phân bón")
    @app_commands.describe(
        action="Để trống để xem thông tin"
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
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
            channel = ctx_or_interaction.channel
            guild_id = ctx_or_interaction.guild_id
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
            channel = ctx_or_interaction.channel
            guild_id = ctx_or_interaction.guild.id
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - recycle trash")
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=True)
        
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

        # Track recycled trash for achievement (counts units recycled)
        try:
            await increment_stat(user_id, "fishing", "trash_recycled", trash_used)
            current_trash_recycled = await get_stat(user_id, "fishing", "trash_recycled")
            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "trash_recycled", current_trash_recycled, channel)
        except Exception as e:
            print(f"[ACHIEVEMENT] Error updating trash_recycled for {user_id}: {e}")
        
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
        """Upgrade rod logic - requires correct amount of rod_material AND seeds
        1->2: 1 mat | 2->3: 2 mat | 3->4: 3 mat | 4->5: 4 mat
        Plus seeds cost from ROD_LEVELS[next_lvl]['cost']
        """
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_slash:
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - upgrade rod")
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
        
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
        
        # Material requirements based on current level
        # 1->2: 1 | 2->3: 2 | 3->4: 3 | 4->5: 4
        materials_needed = cur_lvl
        cost_in_seeds = rod_info["cost"]
        
        # Check if user has enough rod_material AND seeds
        inventory = await get_inventory(user_id)
        has_material = inventory.get("rod_material", 0)
        user_balance = await get_user_balance(user_id)
        
        if has_material < materials_needed:
            embed = discord.Embed(
                title="❌ Không Đủ Vật Liệu",
                description=f"Để nâng **{ROD_LEVELS[cur_lvl]['name']}** lên **{rod_info['name']}** cần **{materials_needed} Vật Liệu Nâng Cấp Cần**!\n\nBạn có: **{has_material}/{materials_needed} Vật Liệu**",
                color=discord.Color.red()
            )
            if is_slash:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            return
        
        if user_balance < cost_in_seeds:
            embed = discord.Embed(
                title="❌ Không Đủ Hạt",
                description=f"Để nâng **{ROD_LEVELS[cur_lvl]['name']}** lên **{rod_info['name']}** cần **{cost_in_seeds} Hạt**!\n\nBạn có: **{user_balance}/{cost_in_seeds} Hạt**",
                color=discord.Color.red()
            )
            if is_slash:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            return
        
        # ATOMIC TRANSACTION: Deduct materials AND seeds
        try:
            # Deduct materials
            await remove_item(user_id, "rod_material", materials_needed)
            
            # Deduct seeds
            await add_seeds(user_id, -cost_in_seeds)
            
            # Upgrade rod: restore full durability
            await update_rod_data_module(user_id, rod_info["durability"], next_lvl)
            
            # Track rod upgrades for achievement
            await increment_stat(user_id, "fishing", "rod_upgrades", 1)
            current_upgrades = await get_stat(user_id, "fishing", "rod_upgrades")
            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "rod_upgrades", current_upgrades, ctx_or_interaction.channel)
            
            # Track max rod level achievement
            if next_lvl >= 5:
                try:
                    await increment_stat(user_id, "fishing", "rod_level_max", next_lvl)
                    current_max = await get_stat(user_id, "fishing", "rod_level_max")
                    await self.bot.achievement_manager.check_unlock(user_id, "fishing", "rod_level_max", current_max, ctx_or_interaction.channel)
                    print(f"[ACHIEVEMENT] User {user_id} reached max rod level {next_lvl}")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error tracking rod_level_max for {user_id}: {e}")
        except Exception as e:
            # Rollback on error
            embed = discord.Embed(
                title="❌ Lỗi Nâng Cấp",
                description=f"Có lỗi xảy ra: {str(e)}",
                color=discord.Color.red()
            )
            if is_slash:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            return
        
        # Achievement check is now handled above with rod_upgrades stat
        
        # Build response embed
        embed = discord.Embed(
            title="✅ Nâng Cấp Cần Câu Thành Công!",
            description=f"**{rod_info['emoji']} {rod_info['name']}** (Cấp {next_lvl}/5)",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚡ Thời Gian Chờ", value=f"**{rod_info['cd']}s** (giảm từ {ROD_LEVELS[cur_lvl]['cd']}s)", inline=True)
        embed.add_field(name="🛡️ Độ Bền", value=f"**{rod_info['durability']}** (tăng từ {ROD_LEVELS[cur_lvl]['durability']})", inline=True)
        embed.add_field(name="🍀 May Mắn", value=f"**+{int(rod_info['luck']*100)}%** Cá Hiếm" if rod_info['luck'] > 0 else "**Không thay đổi**", inline=True)
        embed.add_field(name="💰 Chi Phí", value=f"**{materials_needed}** Vật Liệu + **{cost_in_seeds}** Hạt", inline=False)
        embed.set_footer(text="Độ bền đã được hồi phục hoàn toàn!")
        
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
        
        print(f"[ROD] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} upgraded rod to level {next_lvl} using {materials_needed} rod_material + {cost_in_seeds} seeds")
    
    @app_commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây (tăng 50-100 điểm)")
    async def use_fertilizer_slash(self, interaction: discord.Interaction):
        """Use fertilizer via slash command"""
        await self._use_fertilizer_action(interaction)
    
    @commands.command(name="bonphan", description="Dùng Phân Bón để nuôi cây")
    async def use_fertilizer_prefix(self, ctx):
        """Use fertilizer via prefix command"""
        await self._use_fertilizer_action(ctx)
    
    async def _use_fertilizer_action(self, ctx_or_interaction):
        """Use all fertilizer logic - automatically consumes ALL fertilizer"""
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        guild_id = ctx_or_interaction.guild.id
        
        if is_slash:
            user_id = ctx_or_interaction.user.id
            ctx = ctx_or_interaction
        else:
            user_id = ctx_or_interaction.author.id
            ctx = ctx_or_interaction
        
        # *** CHECK AND APPLY LAG DEBUFF DELAY ***
        if self.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            print(f"[EVENT] {username} experienced lag delay (3s) - use fertilizer")
        
        if is_slash:
            await ctx_or_interaction.response.defer(ephemeral=False)
        
        # Check if user has fertilizer
        inventory = await get_inventory(user_id)
        fertilizer_count = inventory.get("fertilizer", 0)
        
        if fertilizer_count <= 0:
            msg = "❌ Bạn không có Phân Bón!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Remove ALL fertilizer at once
        await remove_item(user_id, "fertilizer", fertilizer_count)
        
        # Add to tree - EXP per fertilizer is 75 (same as /bophan)
        exp_per_fertilizer = 75
        total_exp = fertilizer_count * exp_per_fertilizer
        
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
            new_progress = prog + total_exp
            new_total = total + total_exp
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
            
            # Add contributor entry for fertilizer
            await tree_cog.add_contributor(user_id, guild_id, total_exp, contribution_type="fertilizer")
            
            # Build response embed - show breakdown of all fertilizer used
            embed = discord.Embed(
                title="🌾 Bón Phân Thành Công!",
                description=f"**Tự động sài hết tất cả Phân Bón**",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📦 Số Lượng Phân Bón",
                value=f"**{fertilizer_count}** cái",
                inline=False
            )
            
            embed.add_field(
                name="⚡ EXP/cái",
                value=f"{exp_per_fertilizer} EXP",
                inline=True
            )
            
            embed.add_field(
                name="📊 Tổng EXP",
                value=f"**{total_exp}** EXP",
                inline=True
            )
            
            embed.add_field(
                name="🌳 Cây được cộng",
                value=f"**+{total_exp}** điểm",
                inline=False
            )
            
            # Add level-up notification if applicable
            if leveled_up:
                embed.add_field(
                    name="🎉 CÂY ĐÃ LÊN CẤP!",
                    value=f"**{TREE_NAMES[new_level]}** (Cấp {new_level}/6)",
                    inline=False
                )
                embed.color = discord.Color.gold()
            else:
                embed.add_field(
                    name="📈 Tiến độ",
                    value=f"**{int((new_progress / req) * 100) if req > 0 else 0}%** ({new_progress}/{req})",
                    inline=False
                )
            
            print(f"[FERTILIZER] {ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name} used {fertilizer_count} fertilizer: +{total_exp} EXP (Tree Level {new_level})")
            
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
                            title="🌾 Bón Phân Cho Cây!",
                            description=f"**{user_name}** đã sài **{fertilizer_count}** Phân Bón",
                            color=discord.Color.green()
                        )
                        notification_embed.add_field(
                            name="⚡ Tổng EXP",
                            value=f"**{total_exp}** EXP → **+{total_exp}** điểm cho cây",
                            inline=False
                        )
                        notification_embed.add_field(
                            name="📋 Chi tiết",
                            value=f"{fertilizer_count} × {exp_per_fertilizer}",
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
        
        # Get legendary fish caught - check both sources (legacy and new)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Get legendary fish from new fish_collection table
                async with db.execute(
                    "SELECT COUNT(*) as count FROM fish_collection WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    legendary_caught = []
                    if row and row[0] > 0:
                        async with db.execute(
                            "SELECT fish_id FROM fish_collection WHERE user_id = ?",
                            (user_id,)
                        ) as cursor2:
                            rows = await cursor2.fetchall()
                            legendary_caught = [r[0] for r in rows]
                    else:
                        legendary_caught = []
        except:
            legendary_caught = []
        
        # Also check fish_collection for legendary fish (new system)
        legendary_caught_from_collection = set()
        for fish_key in collection.keys():
            if fish_key in LEGENDARY_FISH_KEYS:
                legendary_caught_from_collection.add(fish_key)
        
        # Merge both sources - new system takes priority
        if legendary_caught_from_collection:
            legendary_caught = list(legendary_caught_from_collection)
        
        # Separate common and rare
        common_caught = set()
        rare_caught = set()
        
        for fish_key in collection.keys():
            if fish_key in RARE_FISH_KEYS:
                rare_caught.add(fish_key)
            elif fish_key in COMMON_FISH_KEYS:
                common_caught.add(fish_key)
        
        # Check if user has Isekai fish (hidden legendary)
        has_isekai = "ca_isekai" in legendary_caught
        
        # Display total: 5 normally, 6 if has Isekai
        total_display = 6 if has_isekai else 5
        
        # Get total count (including legendary fish)
        total_all_fish = len(COMMON_FISH_KEYS + RARE_FISH_KEYS) + len(LEGENDARY_FISH)
        total_caught = len(common_caught) + len(rare_caught) + len(legendary_caught)
        completion_percent = int((total_caught / total_all_fish) * 100)
        
        # Display total for progress: adjust for hidden Isekai
        total_all_display = len(COMMON_FISH_KEYS + RARE_FISH_KEYS) + total_display
        
        # Check if completed (all common + rare + legendary)
        is_complete = await check_collection_complete(user_id) and len(legendary_caught) == len(LEGENDARY_FISH)
        
        # Get current title
        current_title = await self.get_title(user_id, guild_id)
        
        # Build common fish embed (Page 1)
        embed_common = discord.Embed(
            title=f"📖 Bộ Sưu Tập Cá của {username}",
            description=f"**Tiến Độ: {total_caught}/{total_all_display}** ({completion_percent}%)\n📄 **Trang 1/2 - Cá Thường**",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        if current_title:
            embed_common.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add common fish section (split into multiple fields to avoid length limit)
        common_display = []
        for fish in COMMON_FISH:
            emoji = "✅" if fish['key'] in common_caught else "❌"
            fish_name = self.apply_display_glitch(fish['name'])
            common_display.append(f"{emoji} {fish['emoji']} {fish_name}")
        
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
            description=f"**Tiến Độ: {total_caught}/{total_all_display}** ({completion_percent}%)\n📄 **Trang 2/2 - Cá Hiếm & Huyền Thoại**",
            color=discord.Color.gold() if is_complete else discord.Color.blue()
        )
        
        if current_title:
            embed_rare.description += f"\n👑 **Danh Hiệu: {current_title}**"
        
        # Add rare fish section (split into multiple fields to avoid length limit)
        rare_display = []
        for fish in RARE_FISH:
            emoji = "✅" if fish['key'] in rare_caught else "❌"
            fish_name = self.apply_display_glitch(fish['name'])
            rare_display.append(f"{emoji} {fish['emoji']} {fish_name}")
        
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
        for legendary_fish in LEGENDARY_FISH:
            fish_key = legendary_fish['key']
            # Skip ca_isekai unless caught
            if fish_key == 'ca_isekai' and not has_isekai:
                continue
            if fish_key in legendary_caught:
                # Caught: show name with ✅
                fish_name = self.apply_display_glitch(legendary_fish['name'])
                legendary_display.append(f"✅ {legendary_fish['emoji']} {fish_name}")
            else:
                # Not caught: show ????
                legendary_display.append(f"❓ {legendary_fish['emoji']} ????")
        
        embed_rare.add_field(
            name=f"🌟 Cá Huyền Thoại ({len(legendary_caught)}/{total_display})",
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
        """Hall of fame logic with pagination - one fish per page, show tasks & conditions."""
        import json
        
        channel = ctx_or_interaction.channel
        guild_id = ctx_or_interaction.guild.id
        # Handle both Interaction (slash) and Context (prefix) objects
        client = ctx_or_interaction.client if is_slash else ctx_or_interaction.bot
        
        # Fetch all legendary catches
        legendary_catches = {}
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Query all legendary fish caught by users
                async with db.execute(
                    "SELECT user_id, fish_key FROM fish_collection WHERE fish_key IN (?, ?, ?, ?, ?)",
                    ('thuong_luong', 'ca_ngan_ha', 'ca_phuong_hoang', 'cthulhu_con', 'ca_voi_52hz')
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    for user_id, fish_key in rows:
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
        except Exception as e:
            print(f"[LEGENDARY] Error fetching hall of fame: {e}")
        
        # Create list of ALL legendary fish with their catchers (or empty list if uncaught)
        # Exclude ca_isekai from hall of fame as it's event-only
        visible_legendaries = [fish for fish in LEGENDARY_FISH if fish['key'] != 'ca_isekai']
        all_legendaries = [(fish, legendary_catches.get(fish['key'], []))
                           for fish in visible_legendaries]
        
        # Create pagination view for all legendaries
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
                fish_key = fish['key']
                price = fish.get('sell_price', 0)
                
                # Determine conditions for each legendary fish
                conditions = self._get_conditions(fish_key)
                
                if catchers:
                    # Fish has been caught - show full info with conditions
                    catcher_text = "\n".join([f"⭐ **{c['username']}**" for c in catchers])
                    
                    embed = discord.Embed(
                        title=f"🏆 {emoji} Huyền Thoại #{self.current_index + 1}",
                        color=discord.Color.gold()
                    )
                    
                    embed.add_field(name="💎 Giá Bán", value=f"{price} Hạt", inline=True)
                    embed.add_field(name="📊 Số Người Bắt", value=f"{len(catchers)}", inline=True)
                    embed.add_field(name="📋 Nhiệm Vụ", value=conditions, inline=False)
                    embed.add_field(name="🏅 Những Người Chinh Phục", value=catcher_text, inline=False)
                    # Set image for caught legendary fish
                    fish_image_url = fish.get('image_url')
                    if fish_image_url:
                        embed.set_image(url=fish_image_url)
                else:
                    # Fish not caught yet - show ??? with hidden info
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
                """Get condition/task description for each legendary fish."""
                conditions_map = {
                    "thuong_luong": "🌊 **Nghi Thức Hiến Tế**\n📌 Dùng `/hiente` để hiến tế 3 sinh vật to lớn (> 150 hạt)\n📌 Nhận bùa chú để dẫn dụ \"Bóng Ma Dưới Đáy Sông\" xuất hiện",
                    "ca_ngan_ha": "🌌 **Kết Nối Tinh Tú**\n📌 Săn Mảnh Sao Băng từ sự kiện lúc 21:00 hằng ngày\n📌 Chế tạo **Tinh Cầu Không Gian** (5 Mảnh + 1 Ngọc Trai)\n📌 Sử dụng Tinh Cầu để giải mã tín hiệu vũ trụ bí ẩn",
                    "ca_phuong_hoang": "🔥 **Thử Thách Giữ Lửa**\n📌 Tìm **Lông Vũ Lửa** (Tỉ lệ rớt khi câu hụt Boss)\n📌 Sử dụng Lông Vũ để bắt đầu nghi lễ hồi sinh\n📌 Canh nhiệt độ chuẩn xác để đánh thức \"Thần Thú Bất Tử\"",
                    "cthulhu_con": "🗺️ **Bản Đồ Hắc Ám**\n📌 Thu thập 4 Mảnh Bản Đồ rách nát từ rương kho báu\n📌 Ghép lại thành Bản Đồ hoàn chỉnh\n📌 Kích hoạt để tìm hang ổ của \"Cổ Thần Say Ngủ\" (Hiệu lực 10 lần câu)",
                    "ca_voi_52hz": "📡 **Tần Số Cô Đơn**\n📌 Sở hữu **Máy Dò Sóng** chuyên dụng\n📌 Dùng lệnh `/dosong` để quét tín hiệu đại dương\n📌 Tìm ra tần số **52Hz** để kết nối với sinh vật cô độc nhất thế giới",
                }
                return conditions_map.get(fish_key, "❌ Chưa xác định điều kiện")
        
        # Send first page
        view = LegendaryHallView(all_legendaries)
        view.update_buttons()
        first_fish, first_catchers = all_legendaries[0]
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
        user = ctx.author
        legendary_embed = discord.Embed(
            title=f"⚠️ {user.display_name} - CẢNH BÁO: DÂY CÂU CĂNG CỰC ĐỘ!",
            description=f"🌊 Có một con quái vật đang cắn câu!\n"
                       f"💥 Nó đang kéo bạn xuống nước!\n\n"
                       f"**{legendary_fish['emoji']} {self.apply_display_glitch(legendary_fish['name'])}**\n"
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
        boss_view = LegendaryBossFightView(self, user_id, legendary_fish, rod_durability, rod_level, channel, guild_id, user)
        
        # Send boss fight message
        boss_msg = await channel.send(f"<@{user_id}> [🧪 DEBUG TEST]", embed=legendary_embed, view=boss_view)
        
        # Log
        print(f"[DEBUG] {ctx.author.name} triggered legendary encounter: {legendary_fish['key']}")
        debug_msg = f"✅ **DEBUG**: Triggered {legendary_fish['emoji']} {self.apply_display_glitch(legendary_fish['name'])} encounter!"
        await ctx.send(debug_msg)
    
    # ==================== HELPER METHODS ====================
    
    async def get_fishing_cooldown_remaining(self, user_id: int) -> int:
        """Get remaining cooldown in seconds.
        
        Check from RAM first (for users in current session).
        If not found, return 0 (assume cooldown expired on last restart).
        """
        if user_id not in self.fishing_cooldown:
            # Cooldown was not set (user restart bot or first fishing)
            return 0
        
        cooldown_until = self.fishing_cooldown[user_id]
        remaining = max(0, cooldown_until - time.time())
        
        # If remaining time passed, clean up
        if remaining <= 0:
            del self.fishing_cooldown[user_id]
            return 0
        
        return int(remaining)
    
    async def get_tree_boost_status(self, guild_id: int) -> bool:
        """Check if server has tree harvest boost active (from level 6 harvest or if tree at level 5+)."""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Check harvest buff timer first (primary source - set when harvest level 6)
                async with db.execute(
                    "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        from datetime import datetime
                        buff_until = datetime.fromisoformat(row[0])
                        if datetime.now() < buff_until:
                            return True  # Harvest buff is active
                
                # Fallback: Check if tree is at level 5+ (persistent bonus)
                async with db.execute(
                    "SELECT current_level FROM server_tree WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    tree_row = await cursor.fetchone()
                    if tree_row and tree_row[0] >= 5:
                        return True
        except Exception as e:
            print(f"[FISHING] Error checking tree boost: {e}")
        return False
    
    async def trigger_global_disaster(self, user_id: int, username: str, channel) -> dict:
        """
        Trigger a server-wide disaster event.
        Returns: {triggered: bool, disaster: dict or None}
        """
        current_time = time.time()
        
        # CHECK FOR FORCED PENDING DISASTER FIRST
        if user_id in self.pending_disaster:
            disaster_key = self.pending_disaster.pop(user_id)
            # Load disaster data
            import json
            from .constants import DISASTER_EVENTS_PATH
            try:
                with open(DISASTER_EVENTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    disasters_by_key = {d["key"]: d for d in data.get("disasters", [])}
                    if disaster_key in disasters_by_key:
                        disaster = disasters_by_key[disaster_key]
                    else:
                        print(f"[DISASTER] Pending disaster key {disaster_key} not found, skipping")
                        return {"triggered": False, "reason": "pending_disaster_key_invalid"}
            except Exception as e:
                print(f"[DISASTER] Error loading pending disaster: {e}")
                return {"triggered": False, "reason": "pending_disaster_load_error"}
        else:
            # Check if server is in global cooldown period
            if current_time - self.last_disaster_time < self.global_disaster_cooldown:
                return {"triggered": False, "reason": "global_cooldown"}
            
            # Roll for disaster (0.05% chance)
            if random.random() >= 0.0005:
                return {"triggered": False, "reason": "no_trigger"}
            
            # DISASTER TRIGGERED!
            disaster = random.choice(DISASTER_EVENTS)
        
        disaster_duration = disaster.get("duration", 300)
        
        # Extract and store disaster effects
        effects = disaster.get("effects", {})
        
        # ONLY freeze server if disaster explicitly has freeze_server = true
        if effects.get("freeze_server"):
            self.is_server_frozen = True
            self.freeze_end_time = current_time + effects.get("freeze_duration", disaster_duration)
        else:
            self.is_server_frozen = False
            self.freeze_end_time = 0
        
        self.last_disaster_time = current_time + disaster_duration
        self.current_disaster = disaster
        self.disaster_culprit = username
        self.disaster_effect_end_time = current_time + disaster_duration
        self.disaster_channel = channel  # Store channel for end notification
        
        self.disaster_catch_rate_penalty = effects.get("catch_rate_penalty", 0.0)
        self.disaster_cooldown_penalty = effects.get("cooldown_penalty", 0)
        self.disaster_fine_amount = effects.get("fine_amount", 0)
        self.disaster_display_glitch = effects.get("display_glitch", False)
        # Share glitch state globally for other modules (economy, views, legendary)
        try:
            set_glitch_state(self.disaster_display_glitch, self.disaster_effect_end_time)
        except Exception as e:
            print(f"[DISASTER] Failed to set global glitch state: {e}")
        
        # Format announcement message
        announcement = disaster["effects"]["message_template"].format(player=username)
        
        # Create embed for announcement
        embed = discord.Embed(
            title=f"{disaster['emoji']} {disaster['name'].upper()}",
            description=announcement,
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"Thời gian phục hồi: {disaster_duration}s")
        
        # Send announcement
        try:
            await channel.send(embed=embed)
            print(f"[DISASTER] {disaster['key']} triggered by {username}. Duration: {disaster_duration}s")
            
            # Track achievement stats for disaster trigger
            from .constants import DISASTER_STAT_MAPPING
            if disaster['key'] in DISASTER_STAT_MAPPING:
                stat_key = DISASTER_STAT_MAPPING[disaster['key']]
                try:
                    await increment_stat(user_id, "fishing", stat_key, 1)
                    current_value = await get_stat(user_id, "fishing", stat_key)
                    await self.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, channel)
                    print(f"[ACHIEVEMENT] Tracked {stat_key} for user {user_id} on disaster {disaster['key']}")
                except Exception as e:
                    print(f"[ACHIEVEMENT] Error tracking {stat_key} for {user_id}: {e}")
                    
        except Exception as e:
            print(f"[DISASTER] Error sending announcement: {e}")
        
        # Apply specific effects based on disaster type
        if disaster["effects"].get("freeze_server"):
            # Server is frozen, no additional action needed (is_server_frozen already set)
            pass
        
        if disaster["effects"].get("fine_applies_to") == "all_online":
            # Apply fine to all online users
            fine_amount = disaster["effects"].get("fine_amount", 0)
            if fine_amount > 0:
                # This will be applied when users try to fish
                print(f"[DISASTER] Fine of {fine_amount} seeds will be applied to all online users")
        
        return {
            "triggered": True,
            "disaster": disaster,
            "culprit": username,
            "duration": disaster_duration
        }
    
    def apply_display_glitch(self, text: str) -> str:
        """Apply display glitch effect to text - glitches ALL text during hacker attack."""
        if not self.disaster_display_glitch or time.time() >= self.disaster_effect_end_time:
            return text
        
        # Import the aggressive glitch function
        from .glitch import apply_glitch_aggressive
        return apply_glitch_aggressive(text)
    
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

    async def _process_npc_acceptance(self, user_id: int, npc_type: str, npc_data: dict, 
                                      fish_key: str, fish_info: dict, username: str):
        """Process NPC acceptance and rewards. Returns result embed. Includes username in title."""
        result_text = ""
        result_color = discord.Color.green()
        
        # Pay the cost first
        cost = npc_data["cost"]
        
        if cost == "fish":
            # Remove the fish
            await remove_item(user_id, fish_key, 1)
            print(f"[NPC] User {user_id} gave {fish_key} to {npc_type}")
        
        elif isinstance(cost, int):
            # Check if user has enough money
            balance = await get_user_balance(user_id)
            if balance < cost:
                result_text = f"❌ Bạn không đủ {cost} Hạt!\n\n{npc_data['rewards']['decline']}"
                result_color = discord.Color.red()
                result_embed = discord.Embed(
                    title=f"{npc_data['name']} - Thất Bại",
                    description=result_text,
                    color=result_color
                )
                return result_embed
            
            await add_seeds(user_id, -cost)
            print(f"[NPC] User {user_id} paid {cost} seeds to {npc_type}")
        
        elif cost == "cooldown_5min":
            # Add cooldown
            self.fishing_cooldown[user_id] = time.time() + 300
            print(f"[NPC] User {user_id} got 5min cooldown from {npc_type}")
        
        elif cost == "cooldown_3min":
            # Add 3-minute cooldown
            self.fishing_cooldown[user_id] = time.time() + 180
            print(f"[NPC] User {user_id} got 3min cooldown from {npc_type}")
        
        # Roll for reward
        rewards_list = npc_data["rewards"]["accept"]
        
        # Build weighted selection
        reward_pool = []
        for reward in rewards_list:
            weight = int(reward["chance"] * 100)
            reward_pool.extend([reward] * weight)
        
        selected_reward = random.choice(reward_pool)
        
        # Process reward
        reward_type = selected_reward["type"]
        
        if reward_type == "worm":
            amount = selected_reward.get("amount", 5)
            await add_item(user_id, "worm", amount)
            result_text = selected_reward["message"]
            print(f"[NPC] User {user_id} received {amount} worms from {npc_type}")
        
        elif reward_type == "lucky_buff":
            if not hasattr(self, "lucky_buff_users"):
                self.lucky_buff_users = {}
            self.lucky_buff_users[user_id] = True
            result_text = selected_reward["message"]
            print(f"[NPC] User {user_id} received lucky buff from {npc_type}")
        
        elif reward_type == "chest":
            amount = selected_reward.get("amount", 1)
            await add_item(user_id, "treasure_chest", amount)
            result_text = selected_reward["message"]
            print(f"[NPC] User {user_id} received {amount} chest(s) from {npc_type}")
        
        elif reward_type == "rod_durability":
            amount = selected_reward.get("amount", 999)
            if amount == 999:
                # Full restore
                rod_lvl, _ = await get_rod_data(user_id)
                rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
                await self.update_rod_data(user_id, rod_config["durability"])
            else:
                rod_lvl, current_durability = await get_rod_data(user_id)
                rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
                new_durability = min(rod_config["durability"], current_durability + amount)
                await self.update_rod_data(user_id, new_durability)
            result_text = selected_reward["message"]
            print(f"[NPC] User {user_id} received durability from {npc_type}")
        
        elif reward_type == "money":
            amount = selected_reward.get("amount", 150)
            await add_seeds(user_id, amount)
            result_text = selected_reward["message"]
            # Add amount to message if not already included
            if "{amount}" in result_text:
                result_text = result_text.replace("{amount}", f"**{amount} Hạt**")
            elif "Hạt" not in result_text:
                result_text += f" (**+{amount} Hạt**)"
            print(f"[NPC] User {user_id} received {amount} seeds from {npc_type}")
        
        elif reward_type == "pearl":
            amount = selected_reward.get("amount", 1)
            await add_item(user_id, "pearl", amount)
            result_text = selected_reward["message"]
            print(f"[NPC] User {user_id} received {amount} pearl(s) from {npc_type}")
        
        elif reward_type == "rod_material":
            amount = selected_reward.get("amount", 2)
            await add_item(user_id, "rod_material", amount)
            result_text = selected_reward["message"]
            print(f"[NPC] User {user_id} received {amount} rod material(s) from {npc_type}")
        
        elif reward_type == "rock":
            result_text = selected_reward["message"]
            result_color = discord.Color.orange()
            print(f"[NPC] User {user_id} got scammed by {npc_type}")
        
        elif reward_type == "nothing":
            result_text = selected_reward["message"]
            result_color = discord.Color.light_grey()
            print(f"[NPC] User {user_id} got nothing from {npc_type}")
        
        elif reward_type == "triple_money":
            # Calculate 3x fish price
            price = fish_info["sell_price"] * 3
            await add_seeds(user_id, price)
            # Replace placeholder in message with actual amount
            result_text = selected_reward["message"]
            if "{amount}" in result_text:
                result_text = result_text.replace("{amount}", f"**{price} Hạt**")
            elif "tiền gấp 3" in result_text:
                result_text = result_text.replace("tiền gấp 3", f"**{price} Hạt**")
            else:
                # If no placeholder, append the amount to the message
                result_text += f" (**+{price} Hạt**)"
            print(f"[NPC] User {user_id} received {price} seeds (3x) from {npc_type}")
        
        elif reward_type == "legendary_buff":
            # Grant legendary buff
            duration = selected_reward.get("duration", 10)
            if not hasattr(self, "legendary_buff_users"):
                self.legendary_buff_users = {}
            self.legendary_buff_users[user_id] = duration
            result_text = selected_reward["message"]
            result_color = discord.Color.gold()
            print(f"[NPC] User {user_id} received legendary buff ({duration} uses) from {npc_type}")
        
        elif reward_type == "cursed":
            # Curse - lose durability (default 20, or custom amount)
            durability_loss = selected_reward.get("amount", 20)
            rod_lvl, current_durability = await get_rod_data(user_id)
            new_durability = max(0, current_durability - durability_loss)
            await self.update_rod_data(user_id, new_durability)
            result_text = selected_reward["message"]
            result_color = discord.Color.dark_red()
            print(f"[NPC] User {user_id} cursed by {npc_type}, lost {durability_loss} durability")
        
        # Return result embed
        result_embed = discord.Embed(
            title=f"{npc_data['name']} - {username} - Kết Quả",
            description=result_text,
            color=result_color
        )
        
        return result_embed
    
    # ==================== SACRIFICE SYSTEM (Database Persisted) ====================
    
    async def get_sacrifice_count(self, user_id: int) -> int:
        """Get current sacrifice count from database (persisted in legendary_quests)."""
        return await get_sacrifice_count(user_id, "thuong_luong")
    
    async def add_sacrifice_count(self, user_id: int, amount: int = 1) -> int:
        """Increment sacrifice count for Thuồng Luồng quest"""
        return await increment_sacrifice_count(user_id, amount, "thuong_luong")
    
    async def reset_sacrifice_count(self, user_id: int) -> None:
        """Reset sacrifice count to 0 in database (after completing quest)."""
        await reset_sacrifice_count(user_id, "thuong_luong")

    # ==================== EMOTIONAL STATE SYSTEM ====================
    
    def apply_emotional_state(self, user_id: int, state_type: str, duration: int) -> None:
        """Apply emotional state (debuff/buff) to user.
        
        state_type: "suy" (50% rare reduction for 5 casts), "keo_ly" (2x sell for 10 min), "lag" (3s delay for 5 min)
        duration: In casts for "suy", in seconds for "keo_ly" and "lag"
        """
        import time
        self.emotional_states[user_id] = {
            "type": state_type,
            "duration": duration,
            "start_time": time.time(),
            "remaining": duration  # For suy, this is remaining casts
        }
    
    def check_emotional_state(self, user_id: int, state_type: str) -> bool:
        """Check if user has active emotional state of type."""
        if user_id not in self.emotional_states:
            return False
        
        state = self.emotional_states[user_id]
        if state["type"] != state_type:
            return False
        
        import time
        elapsed = time.time() - state["start_time"]
        
        if state_type == "suy":
            # For suy, check remaining casts
            return state["remaining"] > 0
        else:
            # For keo_ly and lag, check time duration
            return elapsed < state["duration"]
    
    def get_emotional_state(self, user_id: int) -> dict | None:
        """Get current emotional state or None if expired."""
        if user_id not in self.emotional_states:
            return None
        
        state = self.emotional_states[user_id]
        import time
        elapsed = time.time() - state["start_time"]
        
        if state["type"] == "suy":
            if state["remaining"] <= 0:
                del self.emotional_states[user_id]
                return None
        else:
            if elapsed >= state["duration"]:
                del self.emotional_states[user_id]
                return None
        
        return state
    
    def decrement_suy_cast(self, user_id: int) -> int:
        """Decrement suy debuff cast count. Returns remaining casts."""
        if user_id in self.emotional_states and self.emotional_states[user_id]["type"] == "suy":
            self.emotional_states[user_id]["remaining"] -= 1
            remaining = self.emotional_states[user_id]["remaining"]
            if remaining <= 0:
                del self.emotional_states[user_id]
            return remaining
        return 0

async def setup(bot):
    """Setup fishing cog."""
    await bot.add_cog(FishingCog(bot))
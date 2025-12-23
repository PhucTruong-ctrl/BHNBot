"""Main Fishing Cog."""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, time as dt_time
import asyncio
import random
import time
import json
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("FishingCog", "cogs/fishing/fishing.log")

from .constants import *
from .helpers import track_caught_fish, get_collection, check_collection_complete
from .mechanics.rod_system import get_rod_data, update_rod_data as update_rod_data_module
from .mechanics.legendary import LegendaryBossFightView, check_legendary_spawn_conditions, add_legendary_fish_to_user as add_legendary_module
from .mechanics.events import trigger_random_event
from .views import FishSellView
from .mechanics.glitch import apply_display_glitch as global_apply_display_glitch, set_glitch_state

# Import new modular mechanics
from .mechanics.disasters import trigger_global_disaster as _trigger_disaster_impl
from .mechanics.buffs import EmotionalStateManager
from .commands.sell import sell_fish_action as _sell_fish_impl
from .commands.bucket import (
    open_chest_action as _open_chest_impl,
    recycle_trash_action as _recycle_trash_impl,
    use_phan_bon_action as _use_phan_bon_impl,
    view_collection_action as _view_collection_impl
)
from .commands.craft import (
    hiente_action as _hiente_impl,
    chetao_action as _chetao_impl,
    dosong_action as _dosong_impl,
    ghepbando_action as _ghepbando_impl
)
from .commands.rod import nangcap_action as _nangcap_impl
from .commands.legendary import legendary_hall_of_fame_action as _legendary_hall_of_fame_impl
from .commands.admin import trigger_event_action as _trigger_event_impl

from database_manager import (
    get_inventory, add_item, remove_item, add_seeds, 
    get_user_balance, get_or_create_user, db_manager, get_stat, increment_stat, get_all_stats, get_fish_count, get_fish_collection,
    save_user_buff, get_user_buffs, remove_user_buff
)
from .mechanics.legendary_quest_helper import (
    increment_sacrifice_count, get_sacrifice_count, reset_sacrifice_count,
    set_crafted_bait_status, get_crafted_bait_status,
    set_phoenix_prep_status, get_phoenix_prep_status,
    set_map_pieces_count, get_map_pieces_count, set_quest_completed, is_quest_completed,
    set_frequency_hunt_status, get_frequency_hunt_status,
    is_legendary_caught, set_legendary_caught,
    get_manh_sao_bang_count, set_manh_sao_bang_count, increment_manh_sao_bang,
    has_tinh_cau, set_has_tinh_cau, get_tinh_cau_cooldown, set_tinh_cau_cooldown, craft_tinh_cau
)

# Import event views from mechanics module
from .mechanics.event_views import MeteorWishView, NPCEncounterView


# ==================== FISHING COG ====================

class FishingCog(commands.Cog):
    """The central cog handling all fishing mechanics, inventory management, and random events.

    Attributes:
        bot (commands.Bot): The Discord bot instance.
        fishing_cooldown (dict): Tracks user timestamps for cooldown management.
        caught_items (dict): Temporary storage for caught items per user (for sell interactions).
        user_locks (dict): Asyncio locks to prevent race conditions during DB updates.
    """
    def __init__(self, bot):
        self.bot = bot
        self.fishing_cooldown = {}
        self.caught_items = {}
        self.user_titles = {}
        self.user_stats = {}
        # self.lucky_buff_users = {} -> Migrated to DB
        self.avoid_event_users = {} # Keep as RAM (session based?) or migrate? For now keep.
        # self.legendary_buff_users = {}  -> Migrated to DB
        self.sell_processing = {}  # {user_id: timestamp} - Prevent duplicate sell commands
        self.guaranteed_catch_users = {}  # {user_id: True} - Keep RAM for now (tinh cau win)
        
        # User locks to prevent concurrent fishing operations
        self.user_locks = {}  # {user_id: asyncio.Lock}
        
        # Emotional state tracking (delegated to EmotionalStateManager)
        # Manager is now stateless/DB-backed
        self.emotional_state_manager = EmotionalStateManager()
        # self.emotional_states = ... REMOVED
        
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
        self.pending_fishing_event = {}  # {user_id: event_key} - Force trigger fishing event on next cast
        self.pending_sell_event = {}  # {user_id: event_key} - Force trigger sell event on next sell
        self.pending_npc_event = {}  # {user_id: npc_key} - Force trigger NPC on next cast
        self.pending_meteor_shower = set()  # set of user_ids - Force meteor shower tonight at 21:00
        
        self.meteor_wish_count = {}  # {user_id: {'date': date, 'count': int}}
        
        # Disaster effects tracking (expire when disaster ends)
        self.disaster_catch_rate_penalty = 0.0  # Percentage to reduce catch rate (0.2 = -20%)
        self.disaster_cooldown_penalty = 0  # Extra seconds to add to cooldown
        self.disaster_fine_amount = 0  # Amount to deduct from players
        self.disaster_display_glitch = False  # Whether to show garbled fish names
        self.disaster_effect_end_time = 0  # When current disaster effects expire
        self.disaster_channel = None  # Channel to send disaster end notification
        
        # Start meteor shower task
        self.meteor_shower_event.start()
        
        # Start state cleanup task (prevents memory leaks)
        self.cleanup_stale_state.start()
        
    async def get_user_total_luck(self, user_id: int) -> float:
        """Calculate total user luck from all sources (Rod, Buffs, etc).
        
        Returns:
            float: Total luck value (e.g. 0.05 for 5%)
        """
        luck = 0.0
        
        # 1. Rod Luck
        rod_lvl, _ = await get_rod_data(user_id)
        rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
        luck += rod_config.get("luck", 0.0)
        
        # 2. Emotional States / Buffs (From DB)
        buffs = await get_user_buffs(user_id)
        
        if "lucky_buff" in buffs:
            # "lucky_buff" from events (Double Rainbow, etc)
            luck += 0.5  # Huge +50% luck (Guarantees rare if base is decent)
            
        if "suy" in buffs:
            # "suy" state reduces luck (check handled by get_user_buffs cleanup)
            luck -= 0.2  # -20% luck
            
        if "legendary_buff" in buffs:
            # Ghost NPC buff
            luck += 0.3 # +30% luck
            
        # Ensure luck doesn't go below -1.0 (though logic handles negatives)
        return max(-0.9, luck)
    
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.meteor_shower_event.cancel()
        self.cleanup_stale_state.cancel()
    
    @tasks.loop(hours=1)
    async def cleanup_stale_state(self):
        """Periodic cleanup of expired state to prevent memory leaks.
        
        Runs every hour to clean:
        - Expired cooldowns
        - Stale buff/debuff entries
        - Old pending events
        - Inactive user locks
        """
        try:
            current_time = time.time()
            cleaned_count = 0
            
            # Clean expired cooldowns (already passed)
            expired_cooldowns = [uid for uid, t in list(self.fishing_cooldown.items()) if t < current_time]
            for uid in expired_cooldowns:
                del self.fishing_cooldown[uid]
                cleaned_count += 1
            
            # Clean old caught_items (older than 30 minutes)
            # Note: caught_items should be cleaned after sell, but cleanup any orphans
            if hasattr(self, '_caught_items_timestamps'):
                old_catches = [uid for uid, t in list(self._caught_items_timestamps.items()) 
                              if current_time - t > 1800]  # 30 min
                for uid in old_catches:
                    if uid in self.caught_items:
                        del self.caught_items[uid]
                    del self._caught_items_timestamps[uid]
                    cleaned_count += 1
            
            # Clean expired phoenix buff
            expired_phoenix = [uid for uid, t in list(self.phoenix_buff_active.items()) if t < current_time]
            for uid in expired_phoenix:
                del self.phoenix_buff_active[uid]
                cleaned_count += 1
            
            # Clean expired thuong_luong timers (10 min max ritual time)
            expired_ritual = [uid for uid, t in list(self.thuong_luong_timers.items()) 
                             if current_time - t > 600]
            for uid in expired_ritual:
                del self.thuong_luong_timers[uid]
                cleaned_count += 1
            
            # Clean stale dark_map tracking (after 1 hour inactive)
            stale_dark_map = [uid for uid in list(self.dark_map_active.keys()) 
                             if not self.dark_map_active.get(uid)]
            for uid in stale_dark_map:
                if uid in self.dark_map_active:
                    del self.dark_map_active[uid]
                if uid in self.dark_map_casts:
                    del self.dark_map_casts[uid]
                if uid in self.dark_map_cast_count:
                    del self.dark_map_cast_count[uid]
                cleaned_count += 1
            
            # Clean old pending events (older than 24 hours)
            # These should trigger on next action, but clean orphans
            one_day_ago = current_time - 86400
            
            # Note: We don't track timestamps for pending events, so we clear them
            # after the hourly cleanup runs 24 times (approximately daily)
            # For now, clear any pending events that exist (they're one-shot)
            # Actually, pending events are meant to trigger on next action
            # We'll clear them if the dict gets too large (>100 entries = likely orphans)
            if len(self.pending_disaster) > 100:
                self.pending_disaster.clear()
                logger.info("[CLEANUP] Cleared oversized pending_disaster dict")
            if len(self.pending_fishing_event) > 100:
                self.pending_fishing_event.clear()
                logger.info("[CLEANUP] Cleared oversized pending_fishing_event dict")
            if len(self.pending_sell_event) > 100:
                self.pending_sell_event.clear()
                logger.info("[CLEANUP] Cleared oversized pending_sell_event dict")
            if len(self.pending_npc_event) > 100:
                self.pending_npc_event.clear()
                logger.info("[CLEANUP] Cleared oversized pending_npc_event dict")
            if len(self.pending_meteor_shower) > 100:
                self.pending_meteor_shower.clear()
                logger.info("[CLEANUP] Cleared oversized pending_meteor_shower set")
            
            # Clean lucky_buff_users - Migrated to DB, no cleanup needed here
            pass
            
            # Clean avoid_event_users that are False
            stale_avoid = [uid for uid, v in list(self.avoid_event_users.items()) if not v]
            for uid in stale_avoid:
                del self.avoid_event_users[uid]
                cleaned_count += 1
            
            # Clean guaranteed_catch_users that are False
            stale_guaranteed = [uid for uid, v in list(self.guaranteed_catch_users.items()) if not v]
            for uid in stale_guaranteed:
                del self.guaranteed_catch_users[uid]
                cleaned_count += 1
            
            # Clean expired legendary buff - Migrated to DB, no cleanup needed here
            pass
            
            # Clean old sell_processing entries (older than 5 minutes)
            old_sell = [uid for uid, t in list(self.sell_processing.items()) 
                       if current_time - t > 300]
            for uid in old_sell:
                del self.sell_processing[uid]
                cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"[CLEANUP] Cleaned {cleaned_count} stale state entries")
                
        except Exception as e:
            logger.error(f"[CLEANUP] Error during state cleanup: {e}")
    
    @cleanup_stale_state.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before starting cleanup task."""
        await self.bot.wait_until_ready()
    
    @tasks.loop(time=dt_time(21, 0))
    async def meteor_shower_event(self):
        """Daily meteor shower event at 21:00"""
        try:
            # Check for pending meteor showers first
            pending_users = list(self.pending_meteor_shower) if hasattr(self, "pending_meteor_shower") else []
            self.pending_meteor_shower.clear()
            
            # Get all guilds with fishing channels configured
            from database_manager import db_manager
            rows = await db_manager.execute("SELECT guild_id, fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL")
            
            for guild_id, channel_id in rows:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    # Force meteor shower for pending users
                    if pending_users:
                        await channel.send("🌌 Bầu trời đêm nay quang đãng lạ thường... Có vẻ sắp có mưa sao băng!")
                        logger.info(f"[METEOR] Force triggering meteor shower for pending users: {pending_users}")
                        
                        # Send meteor for each pending user
                        for user_id in pending_users:
                            embed = discord.Embed(
                                title="💫 Một ngôi sao vừa vụt qua!",
                                description="Ước mau!",
                                color=discord.Color.blue()
                            )
                            view = MeteorWishView(self)
                            await channel.send(embed=embed, view=view)
                            await asyncio.sleep(1)  # Small delay between messages
                    
                    # Regular random meteor shower (skip if we already sent for pending users to avoid double)
                    elif random.random() < 0.4:  # 40% chance
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
            logger.error(f"[METEOR] Error in meteor shower event: {e}")
    
    async def _force_meteor_shower(self, user_id: int, channel):
        """Force trigger meteor shower for a specific user"""
        try:
            embed = discord.Embed(
                title="💫 Một ngôi sao vừa vụt qua!",
                description="Ước mau!",
                color=discord.Color.blue()
            )
            view = MeteorWishView(self)
            await channel.send(embed=embed, view=view)
            logger.info(f"[METEOR] Force triggered meteor shower for user {user_id}")
        except Exception as e:
            logger.error(f"[METEOR] Error in force meteor shower: {e}")
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="sukiencauca", description="⚡ Force trigger event câu cá (chỉ Admin)")
    @app_commands.describe(
        user="Discord user sẽ bị trigger event",
        event_type="Loại event: disaster, fishing_event, sell_event, npc_event, meteor_shower",
        event_key="Event key (xem danh sách trong file tương ứng)"
    )
    async def trigger_event_slash(self, interaction: discord.Interaction, user: discord.User, event_type: str, event_key: str):
        await self._trigger_event_action(interaction, user.id, event_type, event_key, is_slash=True)
    
    @commands.command(name="sukiencauca", description="⚡ Force trigger event câu cá (chỉ Admin)")
    async def trigger_event_prefix(self, ctx, user: discord.User, event_type: str, event_key: str):
        await self._trigger_event_action(ctx, user.id, event_type, event_key, is_slash=False)
    
    async def _trigger_event_action(self, ctx_or_interaction, target_user_id: int, event_type: str, event_key: str, is_slash: bool):
        """Force trigger an event. Delegate to admin module."""
        return await _trigger_event_impl(self, ctx_or_interaction, target_user_id, event_type, event_key, is_slash)

    @app_commands.command(name="cauca", description="🎣 Câu cá - Dùng /cauca để bắt đầu")
    async def fish_slash(self, interaction: discord.Interaction):
        await self._fish_action(interaction)
    
    @commands.command(name="cauca")
    async def fish_prefix(self, ctx):
        await self._fish_action(ctx)
    
    async def _fish_action(self, ctx_or_interaction):
        """Executes the core fishing logic, delegating to helper functions.

        Handles command context (Prefix/Slash), cooldowns, random events, casting, and catch results.

        Args:
            ctx_or_interaction: The context or interaction object triggering the command.
        """
        start_time = time.time()  # Performance monitoring
        try:
            is_slash = isinstance(ctx_or_interaction, discord.Interaction)
            
            # Get user_id first (before defer) for lag check
            if is_slash:
                user_id = ctx_or_interaction.user.id
            else:
                user_id = ctx_or_interaction.author.id
            
            if is_slash:
                await ctx_or_interaction.response.defer(ephemeral=False)
                channel = ctx_or_interaction.channel
                guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
                ctx = ctx_or_interaction
            else:
                channel = ctx_or_interaction.channel
                guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
                ctx = ctx_or_interaction
            
            # *** CHECK AND APPLY LAG DEBUFF DELAY (applies to EVERY cast) ***
            if await self.check_emotional_state(user_id, "lag"):
                await asyncio.sleep(3)
                username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                logger.info(f"[EVENT] {username} experienced lag delay (3s) - start of cast")
            
            # --- GET USER AND ROD DATA ---
            rod_lvl, rod_durability = await get_rod_data(user_id)
            rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
            inventory = await get_inventory(user_id) # Fetch inventory once
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            logger.info(f"[FISHING] [ROD_DATA] {username_display} (user_id={user_id}) rod_level={rod_lvl} durability={rod_durability}/{rod_config['durability']}")
            
            # --- CHECK FOR SERVER FREEZE (GLOBAL DISASTER) ---
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            if await self._check_server_freeze(user_id, username_display, is_slash, ctx):
                return



            # --- CHECK FOR NON-FREEZE DISASTER EFFECTS EXPIRING ---
            await self._clear_expired_disaster()

            # --- CHECK FISH BUCKET LIMIT (BEFORE ANYTHING ELSE) ---
            username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            if await self._check_bucket_limit(user_id, inventory, username_display, is_slash, ctx):
                return
        
            # --- CHECK DURABILITY & AUTO REPAIR ---
            rod_durability, repair_msg, is_broken_rod = await self._check_and_repair_rod(
                user_id, rod_lvl, rod_durability, rod_config, channel, username_display
            )

        
            # Ensure user exists
            username = ctx.author.name if not is_slash else ctx_or_interaction.user.name
            await get_or_create_user(user_id, username)

            # ==================== FIX: COOLDOWN BYPASS & RACE CONDITIONS ====================
            # Initialize lock if not exists
            if user_id not in self.user_locks:
                self.user_locks[user_id] = asyncio.Lock()
            
            # ACQUIRE LOCK BEFORE CHECKING COOLDOWN
            # This ensures only ONE execution per user passes through at a time
            async with self.user_locks[user_id]:
            
                # --- CHECK COOLDOWN (Inside Lock) ---
                remaining = await self.get_fishing_cooldown_remaining(user_id)
                if remaining > 0:
                    username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                    
                    # Calculate cooldown end time for Discord timestamp
                    cooldown_end = int(time.time() + remaining)
                    
                    # Use Discord timestamp format for dynamic countdown
                    msg = f"⏱️ **{username_display}** chờ chút nhen! Câu lại vào <t:{cooldown_end}:R>!"
                    logger.info(f"[FISHING] [COOLDOWN] {username_display} (user_id={user_id}) remaining={remaining}s")
                    if is_slash:
                        await ctx.followup.send(msg, ephemeral=True)
                    else:
                        try:
                            # Auto-delete cooldown message after 10 seconds
                            await ctx.reply(msg, delete_after=10)
                        except Exception as e:
                            logger.error(f"[FISHING] Error sending cooldown message: {e}")
                    return
                
                # --- APPLY DISASTER COOLDOWN PENALTY (Check early) ---
                # We need to know the cooldown time to set it later, but we set a temporary "processing" cooldown
                # to prevent other commands from entering while this one processes (though the lock handles it mostly,
                # setting it in DB/memory provides double safety for distributed systems if ever expanded)
                
                # --- TRIGGER GLOBAL DISASTER (0.05% chance) ---
                disaster_result = await self.trigger_global_disaster(user_id, username, channel)
                if disaster_result.get("triggered"):
                    # Disaster was triggered! User's cast is cancelled
                    culprit_reward = disaster_result["disaster"]["reward_message"]
                    thank_you_msg = f"🎭 {culprit_reward}"
                    logger.info(f"[FISHING] [DISASTER_TRIGGERED] {username} (user_id={user_id}) triggered disaster: {disaster_result['disaster']['name']}")
                    if is_slash:
                        await ctx.followup.send(thank_you_msg)
                    else:
                        await ctx.reply(thank_you_msg)
                    return
        
                # --- LOGIC MỚI: AUTO-BUY MỒI NẾU CÓ ĐỦ TIỀN ---
                has_worm = inventory.get("moi", 0) > 0
                auto_bought = False  # Biến check xem có tự mua không

                # Nếu không có mồi, kiểm tra xem có đủ tiền mua không
                if not has_worm:
                    balance = await get_user_balance(user_id)
                    if balance >= WORM_COST:
                        # Tự động trừ tiền coi như mua mồi dùng ngay
                        await add_seeds(user_id, -WORM_COST)
                        has_worm = True
                        auto_bought = True
                        logger.info(f"[FISHING] [AUTO_BUY_WORM] {username} (user_id={user_id}) seed_change=-{WORM_COST} balance_before={balance} balance_after={balance - WORM_COST}")
                    else:
                        # Không có mồi, cũng không đủ tiền -> Chấp nhận câu rác
                        has_worm = False
                        logger.info(f"[FISHING] [NO_WORM_NO_MONEY] {username} (user_id={user_id}) has_worm=False balance={balance} < {WORM_COST}")
                else:
                    # ==================== PASSIVE: NO BAIT LOSS (Level 7 - Chrono Rod) ====================
                    skip_worm_consumption = False
                    if rod_lvl ==7:
                        passive_chance = rod_config.get("passive_chance", 0.10)
                        if random.random() < passive_chance:
                            skip_worm_consumption = True
                            logger.info(f"[FISHING] [PASSIVE] ⏳ Chrono Rod preserved bait for {username}")
                    
                    if not skip_worm_consumption:
                        # Có mồi trong túi -> Trừ mồi
                        await remove_item(user_id, "moi", 1)
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
                        except Exception as e:
                            logger.error(f"Unexpected error: {e}")
                    logger.info(f"[FISHING] [CONSUME_WORM] {username} (user_id={user_id}) inventory_change=-1 action=used_bait")
        
                # --- KẾT THÚC LOGIC MỚI ---
            
                # --- APPLY DISASTER FINE (Police Raid effect) ---
                disaster_fine_msg = ""
                if self.disaster_fine_amount > 0 and time.time() < self.disaster_effect_end_time:
                    current_balance = await get_user_balance(user_id)
                    if current_balance >= self.disaster_fine_amount:
                        await add_seeds(user_id, -self.disaster_fine_amount)
                        disaster_fine_msg = f"\n💰 **PHẠT HÀNH CHÍNH:** -{ self.disaster_fine_amount} Hạt do {self.current_disaster.get('name', 'sự kiện')}"
                        logger.info(f"[DISASTER_FINE] {username} fined {self.disaster_fine_amount} seeds due to {self.current_disaster.get('key')} balance_before={current_balance} balance_after={current_balance - self.disaster_fine_amount}")
                    else:
                        disaster_fine_msg = f"\n⚠️ **PHẠT HÀNH CHÍNH:** Không đủ tiền phạt ({self.disaster_fine_amount} Hạt)"
                        logger.info(f"[DISASTER_FINE] {username} insufficient balance for fine {self.disaster_fine_amount} balance={current_balance}")

        
                logger.info(f"[FISHING] [START] {username} (user_id={user_id}) rod_level={rod_lvl} rod_durability={rod_durability} has_bait={has_worm}")
        
                # Track if this cast triggers global reset (will affect cooldown setting)
                triggers_global_reset = False
            
                # Set cooldown using rod-based cooldown (will be cleared if global_reset triggers)
                cooldown_time = rod_config["cd"]
            
                # *** APPLY DISASTER COOLDOWN PENALTY (Shark Bite Cable effect) ***
                if self.disaster_cooldown_penalty > 0 and time.time() < self.disaster_effect_end_time:
                    cooldown_time += self.disaster_cooldown_penalty
                    logger.info(f"[DISASTER] {username} cooldown increased by {self.disaster_cooldown_penalty}s due to {self.current_disaster.get('name', 'disaster')}")
            
                self.fishing_cooldown[user_id] = time.time() + cooldown_time
        
                # Casting animation
                wait_time = random.randint(1, 5)
        
                # ==================== REDESIGNED CASTING EMBED ====================
                embed = discord.Embed(
                    title=f"🎣 {username} - Đang Câu Cá",
                    description=f"⏳ **Chờ cá cắn câu trong {wait_time}s...**",
                    color=discord.Color.blue()
                )
                
                # ROD INFO (HIGHLIGHTED)
                rod_name = rod_config.get('name', 'Unknown')
                max_durability = rod_config.get('durability', 10)
                cd_time = rod_config.get('cd', 0)
                
                # Create visual durability bar (same as result embed)
                durability_percent = int((rod_durability / max_durability) * 100) if max_durability > 0 else 0
                filled_blocks = int((rod_durability / max_durability) * 10) if max_durability > 0 else 0
                empty_blocks = 10 - filled_blocks
                durability_bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}] {durability_percent}%"
                
                rod_value = f"**{rod_name}** (Lv. {rod_lvl})\n"
                rod_value += f"Độ bền: {durability_bar}\n"
                rod_value += f"└ {rod_durability}/{max_durability}\n"
                rod_value += f"⏱️ Cooldown: {cd_time}s"
                
                embed.add_field(
                    name="🎣 Cần Câu",
                    value=rod_value,
                    inline=False
                )
                
                # BAIT STATUS
                if auto_bought:
                    bait_value = f"✅ **Tự Động Mua**\n└ Phí: {WORM_COST} Hạt"
                    bait_icon = "💸"
                elif not has_worm:
                    bait_value = f"❌ **Không Có Mồi**\n└ Tỉ lệ rác cao!"
                    bait_icon = "⚠️"
                else:
                    bait_value = f"✅ **Đã Sử Dụng**\n└ Tăng khả năng bắt cá"
                    bait_icon = "🐛"
                
                embed.add_field(
                    name=f"{bait_icon} Mồi Câu",
                    value=bait_value,
                    inline=True
                )
                
                # Add footer if rod was repaired
                if repair_msg:
                    embed.set_footer(text=repair_msg.replace("\n", " • "))
                
                casting_msg = await channel.send(embed=embed)

                await asyncio.sleep(wait_time)
        
                # ==================== TRIGGER RANDOM EVENTS ====================
                
                # Calculate Luck just before event trigger to get latest state
                user_luck = await self.get_user_total_luck(user_id)
                logger.info(f"[FISHING] {username} Luck: {user_luck*100:.1f}%")
        
                event_result = await trigger_random_event(self, user_id, channel.guild.id, rod_lvl, channel, luck=user_luck)
        
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
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
            
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
                        await remove_item(user_id, "moi", 1)
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
                                logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) Penalty capped: {event_result['lose_money']} → {penalty_amount} (insufficient balance)")
                        else:
                            event_message += f" (Không đủ tiền để bị phạt!)"
            
                    if event_result.get("gain_money", 0) > 0:
                        await add_seeds(user_id, event_result["gain_money"])
                        event_message += f" (+{event_result['gain_money']} Hạt)"
            
                    # Process gain_items (ngoc_trais, worms, chests, etc.)
                    if event_result.get("gain_items", {}):
                        for item_key, item_count in event_result["gain_items"].items():
                            # Special check for ca_isekai: don't gain if already have
                            if item_key == "ca_isekai":
                                inventory = await get_inventory(user_id)
                                if inventory.get("ca_isekai", 0) > 0:
                                    continue  # Skip adding ca_isekai if already have
                            await add_item(user_id, item_key, item_count)
                            item_id = ALL_FISH.get(item_key, {}).get("name", item_key)
                            event_message += f" (+{item_count} {item_id})"
            
                    # Handle special effects
                    if event_result.get("custom_effect") == "lose_all_bait":
                        # sea_sickness: Lose all bait (worm)
                        worm_count = inventory.get("moi", 0)
                        if worm_count > 0:
                            await remove_item(user_id, "moi", worm_count)
                            event_message += f" (Nôn hết {worm_count} Giun)"
                            logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=sea_sickness inventory_change=-{worm_count} item=worm")
            
                    elif event_result.get("custom_effect") == "cat_steal":
                        # Black Cat: Steals the biggest fish (handle later in catch result)
                        # Logic deferred to line 1301
                        pass
            
                    elif event_result.get("custom_effect") == "snake_bite":
                        # Water Snake: Minus 5% assets
                        balance = await get_user_balance(user_id)
                        penalty = max(10, int(balance * SNAKE_BITE_PENALTY_PERCENT))  # Min 10 Seeds
                        await add_seeds(user_id, -penalty)
                        event_message += f" (Trừ 5% tài sản: {penalty} Hạt)"
                        logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=snake_bite seed_change=-{penalty} penalty_type=asset_penalty")
            
                    elif event_result.get("custom_effect") == "lucky_buff":
                        # Double Rainbow: Next catch guaranteed rare
                        # Store in temporary cache
                        if not hasattr(self, "lucky_buff_users"):
                            self.lucky_buff_users = {}
                        self.lucky_buff_users[user_id] = True
                        event_message += " (Lần câu sau chắc ra Cá Hiếm!)"
                        logger.info(f"[EVENT] {username} received lucky buff for next cast")
            
                    elif event_result.get("custom_effect") == "sixth_sense":
                        # Sixth Sense: Avoid next bad event
                        if not hasattr(self, "avoid_event_users"):
                            self.avoid_event_users = {}
                        self.avoid_event_users[user_id] = True
                        event_message += " (Lần sau tránh xui!)"
                        logger.info(f"[EVENT] {username} will avoid bad event on next cast")
            
                    elif event_result.get("custom_effect") == "suy_debuff":
                        # Depression debuff: 50% rare catch reduction for 5 casts
                        await self.apply_emotional_state(user_id, "suy", 5)
                        event_message += " (Bạn bị 'suy' 😭 - Giảm 50% tỉ lệ cá hiếm trong 5 lần câu)"
                        logger.info(f"[EVENT] {username} afflicted with suy debuff for 5 casts")
            
                    elif event_result.get("custom_effect") == "keo_ly_buff":
                        # Slay buff: 2x sell price for 10 minutes (600 seconds)
                        await self.apply_emotional_state(user_id, "keo_ly", 600)
                        event_message += " (Keo Lỳ tái châu! 💅 - x2 tiền bán cá trong 10 phút)"
                        logger.info(f"[EVENT] {username} activated keo_ly buff for 600 seconds")
            
                    elif event_result.get("custom_effect") == "lag_debuff":
                        # Lag debuff: 3s delay per cast for 5 minutes (300 seconds)
                        await self.apply_emotional_state(user_id, "lag", 300)
                        event_message += " (Mạng lag! 📶 - Bot sẽ phản hồi chậm 3s cho mỗi lần câu trong 5 phút)"
                        logger.info(f"[EVENT] {username} afflicted with lag debuff for 300 seconds")
            
                    elif event_result.get("custom_effect") == "restore_durability":
                        # Restore Durability: +20 (Max capped)
                        max_durability = rod_config["durability"]
                        rod_durability = min(max_durability, rod_durability + 20)
                        await self.update_rod_data(user_id, rod_durability)
                        event_message += f" (Độ bền +20: {rod_durability}/{max_durability})"
                        logger.info(f"[EVENT] {username} restored rod durability to {rod_durability}")
            
                    # Note: global_reset is handled after event embed display below
            
                    # Adjust cooldown (golden_turtle có thể là -30 để reset)
                    if event_result.get("cooldown_increase", 0) != 0:
                        if event_result["cooldown_increase"] < 0:
                            # Reset cooldown (golden_turtle)
                            self.fishing_cooldown[user_id] = time.time()
                            event_message += " (Thời gian chờ xóa sạch!)"
                            logger.info(f"[EVENT] {username} Thời gian chờ reset")
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
                        logger.info(f"[EVENT] {username} triggered {event_type} - fishing cancelled, durability loss: {durability_loss}")
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
            
                    # Special embed for Isekai event - show legendary fish info or rejection
                    if event_type == "isekai_truck":
                        inventory = await get_inventory(user_id)
                        has_isekai = inventory.get("ca_isekai", 0) > 0
                        if has_isekai:
                            embed = discord.Embed(
                                title="🚚 CÚ HÚC... VÔ NGHĨA!",
                                description="Rầm! Truck-kun húc bạn bay sang dị giới. Bạn hào hứng mở mắt ra, chuẩn bị đón nhận dàn Harem và sức mạnh bá đạo...\n\nNhưng chớp mắt một cái, bạn thấy mình vẫn đang ngồi đần mặt cầm cần câu ở cái hồ này. Hóa ra Nữ Thần Dị Giới đã **từ chối cấp Visa** cho bạn. \n\n*'Về đi, cứu thế giới một lần là đủ rồi!'* - Chẳng có gì xảy ra cả, quê thật sự.",
                                color=discord.Color.purple()
                            )
                            await channel.send(embed=embed)
                        else:
                            # Find the legendary fish data
                            legendary_fish = next((fish for fish in LEGENDARY_FISH_DATA if fish["key"] == "ca_isekai"), None)
                            if legendary_fish:
                                fish_embed = discord.Embed(
                                    title=f"🌌 {username} - CÁ HUYỀN THOẠI MỚI! 🌌",
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
                        logger.info(f"[GLOBAL EVENT] {username} triggered {event_type} - All fishing cooldowns cleared!")
            
                    # Wait a bit before showing catch
                    await asyncio.sleep(1)
                    casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
        
                # ==================== NORMAL FISHING PROCESSING ====================
            
                # NOTE: Race condition protection - user locks enabled for critical database operations
                # Due to code complexity, locks are applied per operation rather than entire block
        
                # Roll number of fish (1-5) with weighted probability
                # BUT: If no bait OR broken rod -> only 1 fish or 1 trash (no multiples)
                if has_worm and not is_broken_rod:
                    num_fish = random.choices([1, 2, 3, 4, 5], weights=CATCH_COUNT_WEIGHTS, k=1)[0]
                else:
                    num_fish = 1  # No bait / broken rod = 1 fish only
        
                # Apply bonus catch from events (e.g., Bão Cá - câu thêm cá ngẫu nhiên)
                bonus_catch = event_result.get("bonus_catch", 0)
                if bonus_catch > 0:
                    original_num_fish = num_fish
                    num_fish = num_fish + bonus_catch
                    logger.info(f"[EVENT] {username} activated bonus_catch +{bonus_catch}: {original_num_fish} → {num_fish} fish")
        
                # Roll trash (independent)
                # BUT: If no bait OR broken rod -> only roll trash OR fish, not both
                if has_worm and not is_broken_rod:
                    trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
                else:
                    # No bait / broken rod: High chance of trash (50/50)
                    trash_count = random.choices([0, 1], weights=[50, 50], k=1)[0]
        
                # Roll chest (independent, low chance)
                # BUT: If no bait OR broken rod -> never roll chest
                # Check for both tree boost AND lucky buff from NPC
                is_boosted = await self.get_tree_boost_status(channel.guild.id)
                has_lucky_buff = await self.check_emotional_state(user_id, "lucky_buff")
                is_boosted = is_boosted or has_lucky_buff
        
                if has_worm and not is_broken_rod:
                    chest_weights = [95, 5] if not is_boosted else [90, 10]
                    chest_count = random.choices([0, 1], weights=chest_weights, k=1)[0]
                else:
                    chest_count = 0  # No bait = no chest
        
                results = {"fish": num_fish}
                if trash_count > 0:
                    results["trash"] = trash_count
                if chest_count > 0:
                    results["chest"] = chest_count
        
                logger.info(f"[FISHING] {username} rolled: {num_fish} fish, {trash_count} trash, {chest_count} chest [has_worm={has_worm}]")
        
                # Clear lucky buff after this cast
                if has_lucky_buff:
                    await self.emotional_state_manager.decrement_counter(user_id, "lucky_buff")
        
                boost_text = " ✨**(BUFF MAY MẮN!)**✨" if has_lucky_buff else ("✨" if is_boosted else "")
        
                # Track caught items for sell button
                self.caught_items[user_id] = {}
        
                # Build summary display and process all results
                fish_display = []
                fish_only_items = {}
                trash_items = {}  # Track specific trash items
        
                # FIX: Track if rare fish already caught this turn (Max 1 rare per cast)
                caught_rare_this_turn = False
        
                # Select loot table based on bait availability or rod status
                if has_worm and not is_broken_rod:
                    # Has bait = use normal loot table (includes rare fish)
                    loot_table = LOOT_TABLE_BOOST if is_boosted else LOOT_TABLE_NORMAL
                else:
                    # No bait / broken rod = use worst loot table (trash & common only, 1% rare)
                    loot_table = LOOT_TABLE_NO_WORM
        
                # Process fish - roll type for each fish
                # NOTE: Boost does NOT increase Rare Fish rate, only Chest rate to balance economy
                for _ in range(num_fish):
                    # Roll from LOOT_TABLE to determine type (Rare vs Common)
                    # Normalize weights
                    fish_weights_sum = loot_table["common_fish"] + loot_table["rare_fish"]
            
                    # If no bait, fish_weights_sum = 30 + 0 = 30
                    # Thus common_ratio = 100%, rare_ratio = 0%
                    if fish_weights_sum == 0:
                        # If table has no fish (only trash/chest)
                        common_ratio = 1.0
                        rare_ratio = 0.0
                    else:
                        common_ratio = loot_table["common_fish"] / fish_weights_sum
                        rare_ratio = loot_table["rare_fish"] / fish_weights_sum
            
                    # *** APPLY TOTAL USER LUCK (Centralized) ***
                    rare_ratio = min(0.9, rare_ratio + user_luck)  # Cap at 90% max
                    
                    # Handle "suy" decrement (luck penalty is -0.2 in total luck)
                    # Handle "suy" decrement (luck penalty is -0.2 in total luck)
                    if await self.check_emotional_state(user_id, "suy"):
                        await self.decrement_suy_cast(user_id)
                        
                    # Log Ghost NPC usage (luck bonus is +0.3 in total luck)
                    # Log Ghost NPC usage (luck bonus is +0.3 in total luck)
                    if await self.check_emotional_state(user_id, "legendary_buff"):
                        logger.info(f"[NPC_BUFF] {username} used legendary buff charge (Luck included in total)")
            
                    # *** APPLY DISASTER CATCH RATE PENALTY ***
                    current_time = time.time()
                    trash_rate = 0.0
                    if self.disaster_catch_rate_penalty > 0 and current_time < self.disaster_effect_end_time:
                        # Calculate trash rate from penalty
                        trash_rate = self.disaster_catch_rate_penalty
                        # Reduce fish rates proportionally
                        total_fish_rate = rare_ratio + common_ratio
                        if total_fish_rate > 0:
                            fish_rate_after_penalty = total_fish_rate * (1.0 - self.disaster_catch_rate_penalty)
                            rare_ratio = (rare_ratio / total_fish_rate) * fish_rate_after_penalty
                            common_ratio = (common_ratio / total_fish_rate) * fish_rate_after_penalty
                        else:
                            trash_rate = 0  # No fish to replace
                        logger.info(f"[DISASTER] {username} fish rate reduced by {int(self.disaster_catch_rate_penalty*100)}%, trash rate: {int(trash_rate*100)}% due to {self.current_disaster.get('name', 'disaster')}")
                
                    # Now roll: common, rare, or trash
                    total_weights = [common_ratio, rare_ratio, trash_rate]
                    choices = ["common", "rare", "trash"]
                    catch_type = random.choices(choices, weights=total_weights, k=1)[0]
                
                    if catch_type == "trash":
                        # Catch trash instead of fish
                        trash = random.choice(TRASH_ITEMS)
                        item_key = trash.get("key", f"trash_{hash(str(trash)) % 1000}")
                        try:
                            await self.add_inventory_item(user_id, item_key, "trash")
                            if item_key not in trash_items: trash_items[item_key] = 0
                            trash_items[item_key] += 1
                            logger.info(f"[DISASTER_TRASH] {username} caught trash: {item_key} due to {self.current_disaster.get('name', 'disaster')}")
                        except Exception as e:
                            logger.info(f"[FISHING] [ERROR] Failed to add trash item {item_key} for {username}: {e}")
                        continue  # Skip fish catching logic
            
                    # Check if convert_to_trash event is active (e.g., Pollution)
                    if event_result.get("convert_to_trash", False):
                        # Convert fish to trash
                        trash = random.choice(TRASH_ITEMS)
                        item_key = f"trash_{trash['name'].lower().replace(' ', '_')}"
                        await self.add_inventory_item(user_id, item_key, "trash")
                        if item_key not in trash_items: trash_items[item_key] = 0
                        trash_items[item_key] += 1
                        logger.info(f"[EVENT-POLLUTION] {username} fish converted to trash: {item_key}")
                        continue
            
                    if catch_type == "rare" and not caught_rare_this_turn:
                        fish = random.choice(RARE_FISH)
                        caught_rare_this_turn = True  # Mark rare as caught to enforce limit
                        logger.info(f"[FISHING] {username} caught RARE fish: {fish['key']} ✨ (Max 1 rare per cast, Rod Luck: +{int(rod_config['luck']*100)}%)")
                        try:
                            await self.add_inventory_item(user_id, fish['key'], "fish")
                        except Exception as e:
                            logger.info(f"[FISHING] [ERROR] Failed to add rare fish {fish['key']} for {username}: {e}")
                            continue  # Skip achievement tracking if add failed
                
                        # Check boss_hunter achievement
                        if fish['key'] in ['megalodon', 'thuy_quai_kraken', 'leviathan']:
                            await increment_stat(user_id, "fishing", "boss_caught", 1)
                            current_boss = await get_stat(user_id, "fishing", "boss_caught")
                            await self.bot.achievement_manager.check_unlock(
                                user_id=user_id,
                                game_category="fishing",
                                stat_key="boss_caught",
                                current_value=current_boss,
                                channel=channel
                            )
                
                        # Track in collection
                        is_new_collection = await track_caught_fish(user_id, fish['key'])
                        if is_new_collection:
                            logger.info(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                            # Check first_catch achievement (catch any fish for the first time)
                            # Get current collection count BEFORE adding this fish
                            collection = await get_collection(user_id)
                            was_empty = len(collection) == 0  # Check if collection was empty before this catch
                            if was_empty:  # This is the first fish ever caught
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
                        
                        # ==================== PASSIVE: DOUBLE CATCH (Level 6 - Void Rod) ====================
                        if rod_lvl == 6:
                            passive_chance = rod_config.get("passive_chance", 0.05)
                            if random.random() < passive_chance:
                                # Duplicate the rare fish!
                                await self.add_inventory_item(user_id, fish['key'], "fish")
                                fish_only_items[fish['key']] += 1  # Add to display count
                                logger.info(f"[FISHING] [PASSIVE] 🌌 Void Rod double catch triggered for {username} - RARE {fish['key']}")
                                # Store for special message display later
                                if not hasattr(self, '_void_rod_double_catch'):
                                    self._void_rod_double_catch = {}
                                self._void_rod_double_catch[user_id] = fish
                    elif catch_type == "common":
                        # Catch common fish (or fallback if rare limit reached)
                        fish = random.choice(COMMON_FISH)
                        logger.info(f"[FISHING] {username} caught common fish: {fish['key']}")
                        try:
                            await self.add_inventory_item(user_id, fish['key'], "fish")
                        except Exception as e:
                            logger.info(f"[FISHING] [ERROR] Failed to add common fish {fish['key']} for {username}: {e}")
                            continue  # Skip achievement tracking if add failed
                        # Track in collection
                        is_new_collection = await track_caught_fish(user_id, fish['key'])
                        if is_new_collection:
                            logger.info(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                            # Check first_catch achievement (catch any fish for the first time)
                            # Get current collection count BEFORE adding this fish
                            collection = await get_collection(user_id)
                            was_empty = len(collection) == 0  # Check if collection was empty before this catch
                            if was_empty:  # This is the first fish ever caught
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
                        
                        # ==================== PASSIVE: DOUBLE CATCH (Level 6 - Void Rod) ====================
                        if rod_lvl == 6:
                            passive_chance = rod_config.get("passive_chance", 0.05)
                            if random.random() < passive_chance:
                                # Duplicate the fish!
                                await self.add_inventory_item(user_id, fish['key'], "fish")
                                fish_only_items[fish['key']] += 1  # Add to display count
                                logger.info(f"[FISHING] [PASSIVE] 🌌 Void Rod double catch triggered for {username} - {fish['key']}")
                                # Store for special message display later
                                if not hasattr(self, '_void_rod_double_catch'):
                                    self._void_rod_double_catch = {}
                                self._void_rod_double_catch[user_id] = fish
        
                # Decrease legendary buff counter
                if await self.check_emotional_state(user_id, "legendary_buff"):
                    remaining = await self.emotional_state_manager.decrement_counter(user_id, "legendary_buff")
                    if remaining <= 0:
                        logger.info(f"[NPC_BUFF] {username} legendary buff expired")
                    else:
                        logger.info(f"[NPC_BUFF] {username} has {remaining} legendary buff uses left")
        
                # Apply duplicate multiplier from events (e.g., Twin Fish - double similar fish)
                duplicate_multiplier = event_result.get("duplicate_multiplier", 1)
                if duplicate_multiplier > 1:
                    duplicated_items = {}
                    for fish_key, qty in fish_only_items.items():
                        new_qty = qty * duplicate_multiplier
                        duplicated_items[fish_key] = new_qty
                        # Add duplicated fish to inventory
                        await add_item(user_id, fish_key, new_qty - qty)
                        logger.info(f"[EVENT] {username} activated duplicate_multiplier x{duplicate_multiplier}: {fish_key} {qty} → {new_qty}")
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
                            trash_info = ALL_FISH.get(key, {"description": "Unknown trash", "emoji": "🥾", "name": "Unknown trash"})
                            trash_desc = trash_info.get('description', 'Unknown trash')
                            trash_emoji = trash_info.get('emoji', '🥾')
                            trash_name = trash_info.get('name', 'Unknown trash')
                            fish_display.append(f"{trash_emoji} {self.apply_display_glitch(trash_name)} - {self.apply_display_glitch(trash_desc)}")
                        else:
                            # Get proper trash name from ALL_ITEMS_DATA
                            from .constants import ALL_ITEMS_DATA
                            trash_data = ALL_ITEMS_DATA.get(key, {})
                            trash_name = trash_data.get('name', key.replace("trash_", "").replace("_", " ").title())
                            fish_display.append(f"🗑️ {self.apply_display_glitch(trash_name)} x{qty}")
            
                    # Track trash caught for achievement
                    try:
                        await add_seeds(user_id, trash_count)
                        # Track achievement: trash_master
                        try:
                            await increment_stat(user_id, "fishing", "trash_recycled", trash_count)
                            current_trash = await get_stat(user_id, "fishing", "trash_recycled")
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "trash_recycled", current_trash, channel)
                        except Exception as e:
                            logger.error(f"[ACHIEVEMENT] Error tracking trash_recycled for {user_id}: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
                    logger.info(f"[FISHING] {username} caught trash: {trash_items_caught}")
        
                # Process chest (độc lập)
                if chest_count > 0:
                    for _ in range(chest_count):
                        await self.add_inventory_item(user_id, "ruong_kho_bau", "tool")
                    fish_display.append(f"🎁 Rương Kho Báu x{chest_count}")
                    logger.info(f"[FISHING] {username} caught {chest_count}x TREASURE CHEST! 🎁")
                    # Track chests caught for achievement
                    try:
                        await increment_stat(user_id, "fishing", "chests_caught", chest_count)
                        current_chests = await get_stat(user_id, "fishing", "chests_caught")
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "chests_caught", current_chests, channel)
                    except Exception as e:
                        logger.error(f"[ACHIEVEMENT] Error updating chests_caught for {user_id}: {e}")
        
                # Store only fish for the sell button
                self.caught_items[user_id] = fish_only_items
                logger.info(f"[FISHING] {username} final caught items: {fish_only_items}")
        
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
                
                        logger.info(f"[EVENT] {username} lost {fish_info['name']} to cat_steal")
                        # Track robbed count (cat steal counts as being robbed)
                        try:
                            await increment_stat(user_id, "fishing", "robbed_count", 1)  # stat update,
                            current_robbed = await get_stat(user_id, "fishing", "robbed_count")
                            await self.bot.achievement_manager.check_unlock(user_id, "fishing", "robbed_count", current_robbed, channel)
                        except Exception as e:
                            logger.error(f"[ACHIEVEMENT] Error updating robbed_count for {user_id}: {e}")
                        if fish_display:
                            fish_display[0] = fish_display[0] + f"\n(🐈 Mèo cướp mất {fish_info['name']} giá {highest_price} Hạt!)"
        
                # Update caught items for sell button
                self.caught_items[user_id] = {k: v for k, v in fish_only_items.items() if k != "ca_isekai"}
            
                # Check if bucket is full after fishing, if so, sell all fish instead of just caught
                updated_inventory = await get_inventory(user_id)
                current_fish_count = sum(v for k, v in updated_inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS)
                if current_fish_count >= FISH_BUCKET_LIMIT:
                    all_fish_items = {k: v for k, v in updated_inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS}
                    # Exclude ca_isekai from sellable items
                    all_fish_items = {k: v for k, v in all_fish_items.items() if k != "ca_isekai"}
                    self.caught_items[user_id] = all_fish_items
                    sell_items = all_fish_items
                    logger.info(f"[FISHING] Bucket full ({current_fish_count}/{FISH_BUCKET_LIMIT}), sell button will sell all fish")
                else:
                    # Exclude ca_isekai from sellable items
                    sell_items = {k: v for k, v in fish_only_items.items() if k != "ca_isekai"}
        
                # ==================== CHECK FOR LEGENDARY FISH ====================
                current_hour = datetime.now().hour
                legendary_fish = await check_legendary_spawn_conditions(user_id, channel.guild.id, current_hour, cog=self)
                legendary_failed = False  # Track if legendary boss fight failed

                if isinstance(legendary_fish, dict) and "already_caught" in legendary_fish:
                    legendary_key = legendary_fish["already_caught"]
                    if legendary_key == "ca_ngan_ha":
                        embed = discord.Embed(
                            title="🌌 VŨ TRỤ LẮC ĐẦU!",
                            description="Bầu trời đêm bỗng trở nên tĩnh mịch lạ thường. Các vì sao thì thầm rằng bạn đã nắm giữ cả dải ngân hà trong tay rồi. Đừng quấy rầy giấc ngủ của vũ trụ thêm nữa.",
                            color=discord.Color.dark_magenta()
                        )
                    elif legendary_key == "cthulhu_con":
                        embed = discord.Embed(
                            title="🐙 VỰC THẲM KHƯỚC TỪ!",
                            description="Tiếng thì thầm điên dại trong đầu bạn bỗng im bặt. Cổ Thần đang say ngủ và ánh mắt của nó đã khắc ghi hình bóng bạn. Đừng đánh thức nỗi kinh hoàng nguyên thủy thêm một lần nào nữa!",
                            color=discord.Color.dark_teal()
                        )
                    elif legendary_key == "ca_phuong_hoang":
                        embed = discord.Embed(
                            title="🔥 NGỌN LỬA NGỦ YÊN!",
                            description="Mặt nước không còn sôi sục, hơi nóng đã dịu lại. Ngọn lửa tái sinh đã chọn bạn làm chủ nhân vĩnh hằng. Không cần thêm tro tàn để thắp lại sự sống, hãy để hào quang ấy rực cháy trong tim bạn.",
                            color=discord.Color.orange()
                        )
                    elif legendary_key == "ca_voi_52hz":
                        embed = discord.Embed(
                            title="🐋 TẦN SỐ ĐÃ ĐƯỢC HỒI ĐÁP!",
                            description="Tiếng hát cô đơn nhất thế giới đã tìm được tri kỷ. Tần số 52Hz không còn lạc lõng giữa đại dương bao la nữa. Nó đã ngừng cất tiếng gọi, vì giờ đây nó đã có bạn bên cạnh.",
                            color=discord.Color.dark_blue()
                        )
                    await channel.send(embed=embed)
                    legendary_fish = None

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
                    logger.info(f"[LEGENDARY] {username} encountered {legendary_key}!")
            
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
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
            
                    # Check if battle was fought
                    if boss_view.fought:
                        logger.info(f"[LEGENDARY] {username} fought the boss!")
                        if boss_view.failed:
                            logger.info(f"[LEGENDARY] {username} failed the boss fight!")
                            legendary_failed = True
                        # Continue to show normal fishing results as well
                    else:
                        logger.info(f"[LEGENDARY] {username} didn't choose - boss escaped!")
                        # No phoenix drop for timeout - only for actual fight failures
        
                # ==================== END LEGENDARY CHECK ====================
            
                # ==================== PHOENIX FEATHER DROP ====================
                # Drop Lông Vũ Lửa when actually failing legendary boss fight (not timeout/cut line) (8% chance)
                if legendary_failed:
                    drop_chance = random.random()
                    if drop_chance < 0.08:  # 8% chance
                        await add_item(user_id, "long_vu_lua", 1)
                        logger.info(f"[PHOENIX] {username} dropped Lông Vũ Lửa from failed legendary boss fight!")
                    
                        # Send notification
                        feather_embed = discord.Embed(
                            title=f"🔥 TÀN DƯ PHƯỢNG HOÀNG - {username}",
                            description=f"Mặt nước bỗng sôi sục! Một bóng đỏ rực vừa vụt qua tầm mắt...\n"
                                        f"Dù sinh vật huyền thoại đã biến mất, nhưng nó đã đánh rơi một bảo vật linh thiêng.\n\n"
                                        f"🪶 **Bạn nhận được:** **Lông Vũ Lửa** (x1)",
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
                                logger.info(f"[TITLE] {username} earned 'Vua Câu Cá' role!")
                        except Exception as e:
                            logger.error(f"[TITLE] Error awarding role: {e}")
        
                # Build embed with item summary
                # FIX: Calculate total fish AFTER duplicate_multiplier is applied
                total_fish = sum(fish_only_items.values())
                total_catches = total_fish + trash_count + chest_count
        
                # ==================== NEW EMBED DESIGN ====================
                # Short, clean title
                title = f"🎣 {username} - Kết Quả Câu Cá"
                
                # Add achievement notification to title if earned
                if title_earned:
                    title = f"👑 {username} - VUA CÂU CÁ! 👑"
                
                # Apply glitch effect
                title = self.apply_display_glitch(title)
                
                # Consistent blue theme (fishing aesthetic)
                embed_color = discord.Color.red() if is_broken_rod else (discord.Color.gold() if title_earned else discord.Color.blue())
                
                embed = discord.Embed(
                    title=title,
                    color=embed_color
                )
                
                # ==================== FIELD 1: ROD INFO (HIGHLIGHTED) ====================
                rod_name = rod_config.get('name', 'Unknown')
                max_durability = rod_config.get('durability', 10)
                
                # Create visual durability bar
                durability_percent = int((rod_durability / max_durability) * 100) if max_durability > 0 else 0
                filled_blocks = int((rod_durability / max_durability) * 10) if max_durability > 0 else 0
                empty_blocks = 10 - filled_blocks
                durability_bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}] {durability_percent}%"
                
                rod_field_value = f"**{rod_name}** (Lv. {rod_lvl})\n"
                rod_field_value += f"Độ bền: {durability_bar}\n"
                rod_field_value += f"└ {rod_durability}/{max_durability}"
                
                if rod_durability <= 0:
                    rod_field_value += f"\n⚠️ **CẦN SỬA: {rod_config['repair']} Hạt**"
                
                embed.add_field(
                    name="🎣 Cần Câu",
                    value=self.apply_display_glitch(rod_field_value),
                    inline=False
                )
                
                # ==================== FIELD 2: CAUGHT ITEMS ====================
                items_value = ""
                
                # Group fish
                if fish_only_items:
                    for key, qty in fish_only_items.items():
                        fish = ALL_FISH[key]
                        fish_name = self.apply_display_glitch(fish['name'])
                        fish_emoji = fish.get('emoji', '🐟')
                        items_value += f"{fish_emoji} **{fish_name}** x{qty}\n"
                
                # Group chests
                if chest_count > 0:
                    items_value += f"🎁 **Rương Kho Báu** x{chest_count}\n"
                
                # Group trash
                # Ungrouped trash display
                if trash_items:
                    for trash_key, qty in trash_items.items():
                        trash_info = ALL_ITEMS_DATA.get(trash_key, {})
                        trash_name = trash_info.get("name", "Rác")
                        trash_name = self.apply_display_glitch(trash_name)
                        items_value += f"🗑️ **{trash_name}** x{qty}\n"
                elif trash_count > 0: # Fallback
                     trash_name = self.apply_display_glitch("Rác")
                     items_value += f"🗑️ **{trash_name}** x{trash_count}\n"
                
                # If nothing caught
                if not items_value:
                    items_value = "_(Không có gì)_"
                
                # Add separator and total
                items_value += f"\n{'─' * 15}\n"
                items_value += f"📊 **Tổng:** {total_catches} items"
                
                embed.add_field(
                    name="🐟 Đã Bắt Được",
                    value=items_value,
                    inline=False
                )
                
                # ==================== SPECIAL NOTIFICATIONS ====================
                # Achievement completion message
                if title_earned:
                    completion_text = "Bạn đã bắt được **tất cả các loại cá**!\n"
                    completion_text += "Chúc mừng bạn trở thành **Vua Câu Cá**! 🎉"
                    embed.add_field(
                        name="🏆 HOÀN THÀNH BỘ SƯU TẬP!",
                        value=self.apply_display_glitch(completion_text),
                        inline=False
                    )
                
                # Broken rod warning
                if is_broken_rod:
                    warning_text = "⚠️ **CẢNH BÁO: Cần câu gãy!**\n"
                    warning_text += "• Chỉ bắt được 1% cá hiếm\n"
                    warning_text += "• Giới hạn 1 item/lần\n"
                    warning_text += "• Không bắt được rương"
                    embed.add_field(
                        name="🚨 Trạng Thái",
                        value=self.apply_display_glitch(warning_text),
                        inline=False
                    )
        
                # *** UPDATE DURABILITY AFTER FISHING ***
                old_durability = rod_durability
                new_durability = max(0, rod_durability - durability_loss)
                try:
                    await self.update_rod_data(user_id, new_durability)
                    rod_durability = new_durability  # Update local variable only if successful
                    logger.info(f"[FISHING] [DURABILITY_UPDATE] {username} (user_id={user_id}) durability {old_durability} → {rod_durability} (loss: {durability_loss})")
                except Exception as e:
                    logger.info(f"[FISHING] [DURABILITY_ERROR] Failed to update durability for {username}: {e}")
                    # Don't update local variable, keep old value for display
            
                # *** APPLY GLITCH TO FOOTER ***
                # The durability_status variable is no longer used directly in the footer,
                # as the rod info is now in a dedicated field.
                footer_text = f"Tổng câu được: {total_catches} vật{boost_text}"
                footer_text = self.apply_display_glitch(footer_text)
                embed.set_footer(text=footer_text)
        
                # Create view with sell button if there are fish to sell
                view = None
                if sell_items:
                    view = FishSellView(self, user_id, sell_items, channel.guild.id)
                    logger.info(f"[FISHING] Created sell button for {username} with {len(sell_items)} fish types")
                else:
                    logger.info(f"[FISHING] No fish to sell, button not shown")
        
                # Track total fish caught for achievement
                if num_fish > 0:
                    try:
                        await increment_stat(user_id, "fishing", "total_fish_caught", num_fish)
                        current_total = await get_stat(user_id, "fishing", "total_fish_caught")
                        await self.bot.achievement_manager.check_unlock(user_id, "fishing", "total_fish_caught", current_total, channel)
                    except Exception as e:
                        logger.error(f"[ACHIEVEMENT] Error updating total_fish_caught for {user_id}: {e}")
            
                await casting_msg.edit(content="", embed=embed, view=view)
                logger.info(f"[FISHING] [RESULT_POST] {username} (user_id={user_id}) action=display_result")
        
                # ==================== NPC ENCOUNTER ====================
                npc_triggered = False
                if hasattr(self, "pending_npc_event") and user_id in self.pending_npc_event:
                    npc_type = self.pending_npc_event.pop(user_id)
                    npc_triggered = True
                    logger.info(f"[NPC] Triggering pending NPC event: {npc_type} for user {user_id}")
                elif random.random() < NPC_ENCOUNTER_CHANCE and (fish_only_items or trash_count > 0 or chest_count > 0):
                    npc_triggered = True
            
                if npc_triggered:
                    if not hasattr(self, "pending_npc_event") or user_id not in self.pending_npc_event:
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
                            logger.info(f"[ACHIEVEMENT] Tracked {stat_key} for user {user_id} on NPC encounter {npc_type}")
                        except Exception as e:
                            logger.error(f"[ACHIEVEMENT] Error tracking {stat_key} for {user_id}: {e}")
                
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
                        logger.info(f"[NPC] {username} declined {npc_type}")
            
                # ==================== FINAL COOLDOWN CHECK ====================
                # If global_reset was triggered, ensure user has no cooldown
                if triggers_global_reset:
                    # Clear the user's cooldown that was set earlier
                    if user_id in self.fishing_cooldown:
                        del self.fishing_cooldown[user_id]
                    logger.info(f"[FISHING] [GLOBAL_RESET] {username} cooldown cleared due to global reset event")
            
                # Performance monitoring
                duration = time.time() - start_time
                logger.info(f"[FISHING] [PERF] Cast completed in {duration:.2f}s for {username}")
        
        except Exception as e:
            # Catch-all error handler for _fish_action
            duration = time.time() - start_time
            logger.info(f"[FISHING] [ERROR] [PERF] Unexpected error in _fish_action after {duration:.2f}s: {e}")
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
                    await ctx.reply(embed=error_embed)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
    
    
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
        """Sell all fish or specific types logic. Delegate to commands module."""
        return await _sell_fish_impl(self, ctx_or_interaction, fish_types)
    
    @app_commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_slash(self, interaction: discord.Interaction):
        """Open chest via slash command"""
        await self._open_chest_action(interaction)
    
    @commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_prefix(self, ctx):
        """Open chest via prefix command"""
        await self._open_chest_action(ctx)
    
    async def _open_chest_action(self, ctx_or_interaction):
        """Open treasure chest logic. Delegate to bucket module."""
        return await _open_chest_impl(self, ctx_or_interaction)
    
    # ==================== LEGENDARY SUMMONING ====================
    
    @app_commands.command(name="hiente", description="🌊 Hiến tế cá cho Thuồng Luồng")
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
            await ctx.reply(embed=embed)
            return
        await self._hiente_action(ctx, fish_key, is_slash=False)
    
    async def _hiente_action(self, ctx_or_interaction, fish_key: str, is_slash: bool):
        """Sacrifice fish to Thuồng Luồng. Delegate to craft module."""
        return await _hiente_impl(self, ctx_or_interaction, fish_key, is_slash)

    @app_commands.command(name="chetao", description="🔧 Chế tạo Tinh Cầu Không Gian")
    @app_commands.describe(item_key="Item key: tinh_cau")
    async def chetao_slash(self, interaction: discord.Interaction, item_key: str):
        await self._chetao_action(interaction, item_key, is_slash=True)
    
    @commands.command(name="chetao", description="🔧 Chế tạo Tinh Cầu Không Gian")
    async def chetao_prefix(self, ctx, item_key: str = None):
        if not item_key:
            await ctx.reply("**Cú pháp:** `!chetao tinh_cau`")
            return
        await self._chetao_action(ctx, item_key, is_slash=False)
    
    async def _chetao_action(self, ctx_or_interaction, item_key: str, is_slash: bool):
        """Craft legendary items. Delegate to craft module."""
        return await _chetao_impl(self, ctx_or_interaction, item_key, is_slash)

    @app_commands.command(name="dosong", description="📡 Sử dụng Máy Dò Sóng tìm Cá Voi 52Hz")
    async def dosong_slash(self, interaction: discord.Interaction):
        await self._dosong_action(interaction, is_slash=True)
    
    @commands.command(name="dosong", description="📡 Sử dụng Máy Dò Sóng")
    async def dosong_prefix(self, ctx):
        await self._dosong_action(ctx, is_slash=False)
    
    async def _dosong_action(self, ctx_or_interaction, is_slash: bool):
        """Use frequency detector. Delegate to craft module."""
        return await _dosong_impl(self, ctx_or_interaction, is_slash)

    # --- NANGCAP (Rod Upgrade) ---
    @app_commands.command(name="nangcap", description="Nâng cấp cần câu của bạn")
    async def nangcap_slash(self, interaction: discord.Interaction):
        await self._nangcap_action(interaction)

    @commands.command(name="nangcap", aliases=["upgrade", "nc"])
    async def nangcap_prefix(self, ctx):
        await _nangcap_impl(ctx)

    async def _nangcap_action(self, ctx_or_interaction):
        """Rod upgrade logic. Delegate to rod module."""
        await _nangcap_impl(ctx_or_interaction)

    @app_commands.command(name="ghepbando", description="🗺️ Ghép Bản Đồ Hầm Ám triệu hồi Cthulhu Non")
    async def ghepbando_slash(self, interaction: discord.Interaction):
        await self._ghepbando_action(interaction, is_slash=True)
    
    @commands.command(name="ghepbando", description="🗺️ Ghép Bản Đồ Hầm Ám")
    async def ghepbando_prefix(self, ctx):
        await self._ghepbando_action(ctx, is_slash=False)
    
    async def _ghepbando_action(self, ctx_or_interaction, is_slash: bool):
        """Combine map pieces. Delegate to craft module."""
        return await _ghepbando_impl(self, ctx_or_interaction, is_slash)

    @app_commands.command(name="bonphan", description="🌾 Bón phân cho cây server")
    async def bonphan_slash(self, interaction: discord.Interaction):
        await self._use_phan_bon_action(interaction)
    
    @commands.command(name="bonphan", description="🌾 Bón phân cho cây server")
    async def bonphan_prefix(self, ctx):
        await self._use_phan_bon_action(ctx)
    
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
        """Recycle trash logic. Delegate to bucket module."""
        return await _recycle_trash_impl(self, ctx_or_interaction, action)

    async def _use_phan_bon_action(self, ctx_or_interaction):
        """Use phan_bon logic. Delegate to bucket module."""
        return await _use_phan_bon_impl(self, ctx_or_interaction)

    async def _view_collection_action(self, ctx_or_interaction, user_id: int, username: str):
        """View collection logic. Delegate to bucket module."""
        return await _view_collection_impl(self, ctx_or_interaction, user_id, username)
    
    @app_commands.command(name="bosuutap", description="📚 Xem bộ sưu tập cá của bạn")
    async def collection_slash(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        await self._view_collection_action(interaction, target.id, target.name)
    
    @commands.command(name="bosuutap", description="Xem bộ sưu tập cá")
    async def collection_prefix(self, ctx, user: discord.User = None):
        target = user or ctx.author
        await self._view_collection_action(ctx, target.id, target.name)
    
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
        """Hall of fame logic. Delegate to legendary module."""
        return await _legendary_hall_of_fame_impl(self, ctx_or_interaction, is_slash)
    
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
                await ctx.reply(f"❌ Cá huyền thoại '{fish_key}' không tồn tại!\n\nDanh sách: {', '.join([f['key'] for f in LEGENDARY_FISH])}")
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
        logger.info(f"[DEBUG] {ctx.author.name} triggered legendary encounter: {legendary_fish['key']}")
        debug_msg = f"✅ **DEBUG**: Triggered {legendary_fish['emoji']} {self.apply_display_glitch(legendary_fish['name'])} encounter!"
        await ctx.reply(debug_msg)
    
    # ==================== HELPER METHODS ====================
    
    async def _clear_expired_disaster(self):
        """Clear expired non-freeze disaster effects and send notification.
        
        Returns:
            bool: True if disaster was cleared, False if no action needed
        """
        if not (self.current_disaster and time.time() >= self.disaster_effect_end_time and not self.is_server_frozen):
            return False
            
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
            return True
        except Exception as e:
            logger.error(f"[DISASTER] Error handling end of non-freeze disaster: {e}")
            return False
    
    async def _check_server_freeze(self, user_id: int, username: str, is_slash: bool, ctx) -> bool:
        """Check if server is frozen due to disaster and handle state reset.
        
        Args:
            user_id: User ID
            username: Username for display
            is_slash: Whether this is a slash command
            ctx: Command context or interaction
            
        Returns:
            bool: True if server is frozen (fishing blocked), False if can proceed
        """
        if not self.is_server_frozen:
            return False
            
        remaining_freeze = int(self.freeze_end_time - time.time())
        if remaining_freeze > 0:
            # Still frozen
            if self.current_disaster:
                disaster_emoji = self.current_disaster.get("emoji", "🚨")
                disaster_name = self.current_disaster.get("name", "Disaster")
                culprit_text = f" (Tội đồ: {self.disaster_culprit})" if self.disaster_culprit else ""
                message = f"⛔ **SERVER ĐANG BẢO TRÌ ĐỘT XUẤT!**\n\n{disaster_emoji} **{disaster_name}**{culprit_text}\n\nVui lòng chờ **{remaining_freeze}s** nữa để khôi phục hoạt động!"
            else:
                message = f"⛔ Server đang bị khóa. Vui lòng chờ **{remaining_freeze}s** nữa!"
            
            logger.info(f"[FISHING] [SERVER_FROZEN] {username} (user_id={user_id}) blocked by disaster: {self.current_disaster.get('name', 'unknown') if self.current_disaster else 'unknown'}")
            if is_slash:
                await ctx.followup.send(message, ephemeral=True)
            else:
                await ctx.reply(message)
            return True
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
                logger.error(f"[DISASTER] Error sending end notification: {e}")
            return False
    
    async def _check_bucket_limit(self, user_id: int, inventory: dict, username: str, is_slash: bool, ctx) -> bool:
        """Check if user's fish bucket is full.
        
        Args:
            user_id: User ID to check
            inventory: User's current inventory
            username: Username for display
            is_slash: Whether this is a slash command
            ctx: Command context or interaction
            
        Returns:
            bool: True if bucket is full (fishing blocked), False if can fish
        """
        fish_count = sum(v for k, v in inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS)
        
        if fish_count >= FISH_BUCKET_LIMIT:
            embed = discord.Embed(
                title=f"⚠️ XÔ ĐÃ ĐẦY - {username}!",
                description=f"🪣 Xô cá của bạn đã chứa {fish_count} con cá (tối đa {FISH_BUCKET_LIMIT}).\n\nHãy bán cá để có chỗ trống, rồi quay lại câu tiếp!",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Hãy dùng lệnh bán cá để bán bớt nhé.")
            if is_slash:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.reply(embed=embed)
            logger.info(f"[FISHING] [BLOCKED] {username} (user_id={user_id}) bucket_full fish_count={fish_count}/{FISH_BUCKET_LIMIT}")
            return True
        return False
    
    async def _check_and_repair_rod(self, user_id: int, rod_lvl: int, rod_durability: int, 
                                     rod_config: dict, channel, username: str) -> tuple:
        """Check rod durability and auto-repair if possible.
        
        Args:
            user_id: User ID
            rod_lvl: Current rod level
            rod_durability: Current rod durability
            rod_config: Rod configuration
            channel: Discord channel for achievement notifications
            username: Username for logging
            
        Returns:
            tuple: (new_durability, repair_msg, is_broken_rod)
        """
        repair_msg = ""
        is_broken_rod = False
        
        if rod_durability <= 0:
            repair_cost = rod_config["repair"]
            balance = await get_user_balance(user_id)
            logger.info(f"[FISHING] [ROD_BROKEN] {username} (user_id={user_id}) rod_level={rod_lvl} durability={rod_durability} repair_cost={repair_cost} balance={balance}")
            
            if balance >= repair_cost:
                # Auto repair
                await add_seeds(user_id, -repair_cost)
                rod_durability = rod_config["durability"]
                await self.update_rod_data(user_id, rod_durability, rod_lvl)
                repair_msg = f"\n🛠️ **Cần câu đã gãy!** Tự động sửa chữa: **-{repair_cost} Hạt** (Độ bền phục hồi: {rod_durability}/{rod_config['durability']})"
                logger.info(f"[FISHING] [AUTO_REPAIR] {username} (user_id={user_id}) seed_change=-{repair_cost} action=rod_repaired new_durability={rod_durability}")
                
                # Track rods repaired for achievement
                try:
                    await increment_stat(user_id, "fishing", "rods_repaired", 1)
                    current_repairs = await get_stat(user_id, "fishing", "rods_repaired")
                    await self.bot.achievement_manager.check_unlock(
                        user_id=user_id,
                        game_category="fishing",
                        stat_key="rods_repaired",
                        current_value=current_repairs,
                        channel=channel
                    )
                except Exception as e:
                    logger.error(f"[ACHIEVEMENT] Error updating rods_repaired for {user_id}: {e}")
            else:
                # Not enough money - broken rod penalties
                is_broken_rod = True
                repair_msg = f"\n⚠️ **Cần câu đã gãy!** Phí sửa là {repair_cost} Hạt. Bạn đang câu với cần gãy (chỉ 1% cá hiếm, 1 item/lần, không rương)."
                logger.info(f"[FISHING] [BROKEN_ROD] {username} (user_id={user_id}) cannot_afford_repair cost={repair_cost}")
        
        return rod_durability, repair_msg, is_broken_rod
    
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
            # Check harvest buff timer first (primary source - set when harvest level 6)
            row = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,)
            )
            if row and row[0]:
                from datetime import datetime
                buff_until = datetime.fromisoformat(row[0])
                if datetime.now() < buff_until:
                    return True  # Harvest buff is active
            
            # Fallback: Check if tree is at level 5+ (persistent bonus)
            tree_row = await db_manager.fetchone(
                "SELECT current_level FROM server_tree WHERE guild_id = ?",
                (guild_id,)
            )
            if tree_row and tree_row[0] >= 5:
                return True
        except Exception as e:
            logger.error(f"[FISHING] Error checking tree boost: {e}")
        return False
    
    async def trigger_global_disaster(self, user_id: int, username: str, channel) -> dict:
        """Trigger a server-wide disaster event. Delegate to mechanics module."""
        return await _trigger_disaster_impl(self, user_id, username, channel)

    
    def apply_display_glitch(self, text: str) -> str:
        """Apply display glitch effect to text - glitches ALL text during hacker attack."""
        if not self.disaster_display_glitch or time.time() >= self.disaster_effect_end_time:
            return text
        
        # Import the aggressive glitch function
        from .glitch import apply_glitch_aggressive
        return apply_glitch_aggressive(text)
    
    async def add_inventory_item(self, user_id: int, item_id: str, item_type: str):
        """Add item to inventory."""
        await add_item(user_id, item_id, 1)
        try:
            await db_manager.modify(
                "UPDATE inventory SET item_type = ? WHERE user_id = ? AND item_id = ?",
                (item_type, user_id, item_id)
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
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
            logger.error(f"[TITLE] Error getting title: {e}")
        
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
            logger.info(f"[NPC] User {user_id} gave {fish_key} to {npc_type}")
        
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
            logger.info(f"[NPC] User {user_id} paid {cost} seeds to {npc_type}")
        
        elif cost == "cooldown_5min":
            # Add cooldown
            self.fishing_cooldown[user_id] = time.time() + 300
            logger.info(f"[NPC] User {user_id} got 5min cooldown from {npc_type}")
        
        elif cost == "cooldown_3min":
            # Add 3-minute cooldown
            self.fishing_cooldown[user_id] = time.time() + 180
            logger.info(f"[NPC] User {user_id} got 3min cooldown from {npc_type}")
        
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
        
        if reward_type == "moi":
            amount = selected_reward.get("amount", 5)
            await add_item(user_id, "moi", amount)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received {amount} worms from {npc_type}")
        
        elif reward_type == "lucky_buff":
            await self.emotional_state_manager.apply_emotional_state(user_id, "lucky_buff", 1)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received lucky buff from {npc_type}")
        
        elif reward_type == "chest":
            amount = selected_reward.get("amount", 1)
            await add_item(user_id, "ruong_kho_bau", amount)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received {amount} chest(s) from {npc_type}")
        
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
            logger.info(f"[NPC] User {user_id} received durability from {npc_type}")
        
        elif reward_type == "money":
            amount = selected_reward.get("amount", 150)
            await add_seeds(user_id, amount)
            result_text = selected_reward["message"]
            # Add amount to message if not already included
            if "{amount}" in result_text:
                result_text = result_text.replace("{amount}", f"**{amount} Hạt**")
            elif "Hạt" not in result_text:
                result_text += f" (**+{amount} Hạt**)"
            logger.info(f"[NPC] User {user_id} received {amount} seeds from {npc_type}")
        
        elif reward_type == "ngoc_trai":
            amount = selected_reward.get("amount", 1)
            await add_item(user_id, "ngoc_trai", amount)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received {amount} ngoc_trai(s) from {npc_type}")
        
        elif reward_type == "vat_lieu_nang_cap":
            amount = selected_reward.get("amount", 2)
            await add_item(user_id, "vat_lieu_nang_cap", amount)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received {amount} rod material(s) from {npc_type}")
        
        elif reward_type == "rock":
            result_text = selected_reward["message"]
            result_color = discord.Color.orange()
            logger.info(f"[NPC] User {user_id} got scammed by {npc_type}")
        
        elif reward_type == "nothing":
            result_text = selected_reward["message"]
            result_color = discord.Color.light_grey()
            logger.info(f"[NPC] User {user_id} got nothing from {npc_type}")
        
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
            logger.info(f"[NPC] User {user_id} received {price} seeds (3x) from {npc_type}")
        
        elif reward_type == "legendary_buff":
            # Grant legendary buff
            duration = selected_reward.get("duration", 10)
            await self.emotional_state_manager.apply_emotional_state(user_id, "legendary_buff", duration)
            result_text = selected_reward["message"]
            result_color = discord.Color.gold()
            logger.info(f"[NPC] User {user_id} received legendary buff ({duration} uses) from {npc_type}")
        
        elif reward_type == "cursed":
            # Curse - lose durability (default 20, or custom amount)
            durability_loss = selected_reward.get("amount", 20)
            rod_lvl, current_durability = await get_rod_data(user_id)
            new_durability = max(0, current_durability - durability_loss)
            await self.update_rod_data(user_id, new_durability)
            result_text = selected_reward["message"]
            result_color = discord.Color.dark_red()
            logger.info(f"[NPC] User {user_id} cursed by {npc_type}, lost {durability_loss} durability")
        
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
    
    async def apply_emotional_state(self, user_id: int, state_type: str, duration: int) -> None:
        """Apply emotional state (debuff/buff) to user. Delegate to manager."""
        await self.emotional_state_manager.apply_emotional_state(user_id, state_type, duration)
    
    async def check_emotional_state(self, user_id: int, state_type: str) -> bool:
        """Check if user has active emotional state of type. Delegate to manager."""
        return await self.emotional_state_manager.check_emotional_state(user_id, state_type)
    
    async def get_emotional_state(self, user_id: int) -> dict | None:
        """Get current emotional state or None if expired. Delegate to manager."""
        return await self.emotional_state_manager.get_emotional_state(user_id)
    
    async def decrement_suy_cast(self, user_id: int) -> int:
        """Decrement suy debuff cast count. Delegate to manager."""
        return await self.emotional_state_manager.decrement_suy_cast(user_id)


async def setup(bot):
    """Setup fishing cog."""
    await bot.add_cog(FishingCog(bot))
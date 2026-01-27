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
from core.logging import get_logger

logger = get_logger("FishingCog")

from .constants import *
from configs.item_constants import ItemKeys, ItemType
from .helpers import track_caught_fish, get_collection, check_collection_complete
from .mechanics.rod_system import get_rod_data, update_rod_data, check_and_repair_rod as _check_and_repair_rod_impl
from .mechanics.legendary import check_legendary_spawn_conditions, add_legendary_fish_to_user as add_legendary_module
from .mechanics.events import trigger_random_event

# FORCE RELOAD collection module to pick up changes
import importlib
from .commands import collection as collection_module
importlib.reload(collection_module)
from .commands.collection import _view_collection_impl_v2


from .ui import FishSellView, LegendaryBossFightView, InteractiveNPCView, MeteorWishView
from core.services.vip_service import VIPEngine
from .mechanics.glitch import apply_display_glitch as global_apply_display_glitch, set_glitch_state

# Import new modular mechanics
from .mechanics.disasters import (
    trigger_global_disaster as _trigger_disaster_impl,
    check_server_freeze as _check_server_freeze_impl,
    clear_expired_disaster as _clear_expired_disaster_impl
)
from .core.state_manager import FishingStateManager
from .mechanics.buffs import EmotionalStateManager
from .commands.sell import sell_fish_action as _sell_fish_impl
from .commands.fish import fish_action_impl as _fish_action_impl
from .services.luck_service import calculate_base_luck, calculate_buff_luck
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
    add_seeds, 
    get_user_balance, get_or_create_user, db_manager, get_stat, increment_stat, get_all_stats, get_fish_count, get_fish_collection,
    save_user_buff, get_user_buffs, remove_user_buff, get_server_config
)
from .mechanics.legendary_quest_helper import (
    increment_sacrifice_count, get_sacrifice_count, reset_sacrifice_count,
    set_frequency_hunt_status, get_frequency_hunt_status,
    is_legendary_caught, set_legendary_caught,
    increment_manh_sao_bang
)

from .commands.tournament import (
    tournament_create_action as _tournament_create_impl,
    tournament_join_action as _tournament_join_impl,
    tournament_rank_action as _tournament_rank_impl
)

# Import event views from mechanics module
# from .mechanics.interactive_sell_views import FishSellView -> Removed

from .utils.global_event_manager import GlobalEventManager
from .tournament import TournamentManager


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
        
        # Centralized state manager (replaces 25+ individual dicts)
        self.state = FishingStateManager()
        
        # Backward-compatible aliases (delegate to state manager)
        self.fishing_cooldown = self.state.fishing_cooldown
        self.caught_items = self.state.caught_items
        self._caught_items_timestamps = self.state._caught_items_timestamps
        self.user_titles = self.state.user_titles
        self.user_stats = self.state.user_stats
        self.avoid_event_users = self.state.avoid_event_users
        self.user_locks = self.state.user_locks
        self.sell_processing = self.state.sell_processing
        self.guaranteed_catch_users = self.state.guaranteed_catch_users
        self.phoenix_buff_active = self.state.phoenix_buff_active
        self.thuong_luong_timers = self.state.thuong_luong_timers
        
        # Dark map aliases (flat dict style for backward compat)
        self.dark_map_active = self.state.dark_map.active
        self.dark_map_casts = self.state.dark_map.remaining_casts
        self.dark_map_cast_count = self.state.dark_map.current_cast
        
        # Pending events aliases
        self.pending_disaster = self.state.pending.disaster
        self.pending_fishing_event = self.state.pending.fishing_event
        self.pending_sell_event = self.state.pending.sell_event
        self.pending_npc_event = self.state.pending.npc_event
        self.pending_meteor_shower = self.state.pending.meteor_shower
        
        self.meteor_wish_count = self.state.meteor_wish_count
        
        # Disaster state aliases (sync primitives via method)
        self._init_disaster_aliases()
        
        # Initialize Inventory Cache System
        from core.inventory_cache import InventoryCache
        if not hasattr(self.bot, 'inventory'):
             self.bot.inventory = InventoryCache(db_manager)
        self.inventory = self.bot.inventory
        
        # Initialize Emotional State Manager
        self.emotional_state_manager = EmotionalStateManager()
        
        # Initialize Global Event Manager
        self.global_event_manager = GlobalEventManager(self.bot)
        
        # Start Global Event Manager
        self.global_event_manager.start()

        
        # Start state cleanup task (prevents memory leaks)
        # Start state cleanup task (prevents memory leaks)
        self.cleanup_stale_state.start()
        
        # Start Tournament Watchdog (1 min)
        self.tournament_watchdog.start()
    
    def _init_disaster_aliases(self) -> None:
        """Initialize backward-compatible disaster state aliases.
        
        Maps primitive disaster attributes from state.disaster to self for
        backward compatibility with existing code that accesses self.is_server_frozen, etc.
        """
        # These are primitives, so we create aliases via properties would be cleaner
        # but for minimal refactor, we just sync once at init and let code update both
        self.is_server_frozen = self.state.disaster.is_frozen
        self.freeze_end_time = self.state.disaster.freeze_end_time
        self.last_disaster_time = self.state.disaster.last_disaster_time
        self.global_disaster_cooldown = self.state.disaster.cooldown_seconds
        self.current_disaster = self.state.disaster.current_disaster
        self.disaster_culprit = self.state.disaster.culprit_id
        self.disaster_catch_rate_penalty = self.state.disaster.catch_rate_penalty
        self.disaster_cooldown_penalty = self.state.disaster.cooldown_penalty
        self.disaster_fine_amount = self.state.disaster.fine_amount
        self.disaster_display_glitch = self.state.disaster.display_glitch
        self.disaster_effect_end_time = self.state.disaster.effect_end_time
        self.disaster_channel = self.state.disaster.channel
        
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

        # Global Event Luck Bonus
        luck += self.global_event_manager.get_public_effect("luck_bonus", 0.0)
            
        # Ensure luck doesn't go below -1.0 (though logic handles negatives)
        return luck

    def get_fish_display_name(self, fish_key: str, fish_name: str) -> str:
        """Get display name for fish with VIP tier badge if applicable.
        
        Args:
            fish_key: Fish key to check
            fish_name: Base fish name
            
        Returns:
            Fish name with tier badge if VIP fish, otherwise unchanged
        """
        from .constants import VIP_FISH_DATA
        
        # Check if this is a VIP fish
        for vip_fish in VIP_FISH_DATA:
            if vip_fish['key'] == fish_key:
                tier = vip_fish['tier_required']
                badge = {1: "🥈", 2: "🥇", 3: "💎"}.get(tier, "")
                return f"{badge} {fish_name}"
        
        return fish_name
    
    async def cog_load(self):
        """Called when cog is loaded. Initialize async tasks."""
        # Restore active tournament state from DB
        try:
            manager = TournamentManager.get_instance()
            manager.set_bot(self.bot)
            await manager.restore_active_tournaments()
        except Exception as e:
            logger.error(f"[FISHING] Failed to restore tournaments: {e}")

    async def cog_unload(self):
        """Cleanup when cog is unloaded."""
        # self.meteor_shower_event.cancel()
        self.global_event_manager.unload()
        self.cleanup_stale_state.cancel()
        self.tournament_watchdog.cancel()
    
    @tasks.loop(minutes=1)
    async def tournament_watchdog(self):
        """Checks for tournament timeouts/auto-starts."""
        try:
             await TournamentManager.get_instance().check_registration_timeouts()
             await TournamentManager.get_instance().check_active_timeouts()
        except Exception as e:
             logger.error(f"[TOURNAMENT] Watchdog error: {e}")

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
            
            # Cleanup cooldowns
            expired_users = [
                uid for uid, timestamp in self.fishing_cooldown.items() # Changed to fishing_cooldown based on original code
                if current_time - timestamp > 3600  # Clean up if older than 1 hour
            ]
            for uid in expired_users:
                del self.fishing_cooldown[uid] # Changed to fishing_cooldown based on original code
                
            if expired_users:
                logger.debug(f"[CLEANUP] Removed {len(expired_users)} expired cooldown entries")

        except Exception as e:
            logger.error(f"[CLEANUP] Error during state cleanup: {e}")
    
    @tournament_watchdog.before_loop
    async def before_watchdog(self):
        await self.bot.wait_until_ready()
        # Restore active tournament cache
        from .tournament import TournamentManager
        await TournamentManager.get_instance().restore_active_tournaments()

    @cleanup_stale_state.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before starting cleanup task."""
        await self.bot.wait_until_ready()


    
    async def _force_meteor_shower(self, user_id: int, channel):
        """Force trigger meteor shower for a specific user"""
        try:
            embed = discord.Embed(
                title="🌟 Một ngôi sao vừa vụt qua!",
                description="Ước mau!",
                color=discord.Color.blue()
            )
            # Use View from Global Event Manager or re-instantiate?
            # Ideally delegated to Manager, but keeping force method for now or removing?
            # The force method uses MeteorWishView.
            # Let's keep it but update to use manager if possible or leave as is if view exists.
            # Wait, MeteorWishView was imported.
            view = MeteorWishView(self.global_event_manager) # Pass manager instead of self?
            # MeteorWishView standard init takes 'cog'. GlobalEventManager expects 'bot' but maybe view needs it.
            # Let's see MeteorWishView implementation later.
            # For now, just removing the loop is key.
            await channel.send(embed=embed, view=view)
            logger.info(f"[METEOR] Force triggered meteor shower for user {user_id}")
        except Exception as e:
            logger.error(f"[METEOR] Error in force meteor shower: {e}")
    
    # ==================== COMMANDS ====================
    
    # --- TOURNAMENT GROUP ---
    giaidau_group = app_commands.Group(name="giaidau", description="🏆 Giải đấu câu cá VIP")

    @giaidau_group.command(name="create", description="Tổ chức giải đấu (VIP Tier 1+)")
    @app_commands.describe(fee="Phí tham gia (Tối thiểu 1000 Hạt)")
    async def tournament_create(self, interaction: discord.Interaction, fee: int):
        await _tournament_create_impl(interaction, fee)

    @giaidau_group.command(name="join", description="Tham gia giải đấu đang mở")
    @app_commands.describe(tournament_id="ID giải đấu")
    async def tournament_join(self, interaction: discord.Interaction, tournament_id: int):
        await _tournament_join_impl(interaction, tournament_id)

    @giaidau_group.command(name="rank", description="Xem bảng xếp hạng giải đấu hiện tại của bạn")
    async def tournament_rank(self, interaction: discord.Interaction):
        await _tournament_rank_impl(interaction)
    
    @app_commands.command(name="sukiencauca", description="⚡ Force trigger event câu cá (chỉ Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user="Discord user sẽ bị trigger event",
        event_type="Loại event: disaster, fishing_event, sell_event, npc_event, meteor_shower",
        event_key="Event key (xem danh sách trong file tương ứng)"
    )
    async def trigger_event_slash(self, interaction: discord.Interaction, user: discord.User, event_type: str, event_key: str):
        await self._trigger_event_action(interaction, user.id, event_type, event_key, is_slash=True)
    
    @commands.command(name="sukiencauca", description="⚡ Force trigger event câu cá (chỉ Admin)")
    @commands.has_permissions(administrator=True)
    async def trigger_event_prefix(self, ctx, user: discord.User, event_type: str, event_key: str):
        await self._trigger_event_action(ctx, user.id, event_type, event_key, is_slash=False)
    
    async def _trigger_event_action(self, ctx_or_interaction, target_user_id: int, event_type: str, event_key: str, is_slash: bool):
        """Force trigger an event. Delegate to admin module."""
        return await _trigger_event_impl(self, ctx_or_interaction, target_user_id, event_type, event_key, is_slash)

    @app_commands.command(name="cauca", description="🎣 Câu cá - Dùng /cauca để bắt đầu")
    async def fish_slash(self, interaction: discord.Interaction):
        await self._fish_action(interaction)
    

    @app_commands.command(name="lichcauca", description="📅 Xem lịch sự kiện (Global Events)")
    async def event_schedule(self, interaction: discord.Interaction):
        """Displays schedule of global events."""
        manager = self.global_event_manager
        
        # 1. Current Active Event
        current_event = manager.current_event
        active_text = "*Không có sự kiện nào đang diễn ra.*"
        
        if current_event:
            name = current_event["data"].get("name", "Unknown")
            end_time = current_event["end_time"]
            remaining = int(end_time - time.time())
            minutes = remaining // 60
            active_text = f"🔥 **{name}** đang diễn ra! (Còn {minutes} phút)"
            
        # 2. Upcoming Events
        embed = discord.Embed(title="📅 Lịch Trình Sự Kiện Toàn Cầu", color=discord.Color.blue())
        embed.add_field(name="🟢 Đang Diễn Ra", value=active_text, inline=False)
        
        events_cfg = manager.config.get("events", {})
        schedule_text = ""
        
        sorted_events = sorted(events_cfg.items(), key=lambda x: x[1].get("priority", 0), reverse=True)
        
        map_days = {0:"T2", 1:"T3", 2:"T4", 3:"T5", 4:"T6", 5:"T7", 6:"CN"}
        
        for key, data in sorted_events:
            # Skip hidden/test events if needed (priority 0?)
            # if data.get("priority", 0) <= 0: continue 
            
            name = data.get("name", key)
            schedule = data.get("schedule", {})
            days = schedule.get("days", []) 
            times = schedule.get("time_ranges", []) 
            chance = schedule.get("frequency_chance", 0)
            
            # Format Days
            if not days:
                days_str = "Hàng ngày"
            else:
                days_str = "-".join([map_days.get(d, str(d)) for d in days])
                
            # Format Times
            times_str = ", ".join(times)
            
            # Format Chance
            chance_str = f"{chance*100:.0f}%" if chance < 1.0 else "100%"
            
            schedule_text += f"**{name}**\n🕒 `{times_str}` ({days_str}) | 🎲 {chance_str}\n\n"
            
        if not schedule_text:
            schedule_text = "Không có dữ liệu sự kiện."
            
        embed.add_field(name="📅 Lịch Cố Định", value=schedule_text, inline=False)
        embed.set_footer(text="Giờ Server: " + datetime.now().strftime("%H:%M:%S"))
        
        await interaction.response.send_message(embed=embed)
        
    @commands.command(name="cauca")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fish_prefix(self, ctx):
        await self._fish_action(ctx)
    
    async def _get_adaptive_npc_data(self, user_id: int, npc_type: str) -> dict:
        """Get NPC data adapted to user's affinity level.
        
        Args:
            user_id: Discord User ID
            npc_type: Key of the NPC (e.g., 'river_pirates')
            
        Returns:
            dict: NPC data with overrides applied (copy of original)
        """
        import copy
        
        # 1. Get Base Data
        base_data = NPC_ENCOUNTERS.get(npc_type)
        if not base_data:
            logger.warning(f"[NPC_ADAPT] Unknown NPC type: {npc_type}")
            return {}
            
        # Create a deep copy to avoid modifying the constant
        adaptive_data = copy.deepcopy(base_data)
        
        # 2. Get User Affinity
        from database_manager import get_stat
        current_affinity = await get_stat(user_id, "npc_affinity", npc_type)
        
        # 3. Check Tiers
        tiers = base_data.get("affinity_tiers", [])
        
        # Sort tiers by min_affinity descending to find highest match first
        sorted_tiers = sorted(tiers, key=lambda x: x.get("min_affinity", 0), reverse=True)
        
        active_tier = None
        for tier in sorted_tiers:
            if current_affinity >= tier.get("min_affinity", 0):
                active_tier = tier
                break
        
        if active_tier:
            overrides = active_tier.get("overrides", {})
            # Apple overrides
            for key, value in overrides.items():
                adaptive_data[key] = value
                
            logger.info(f"[NPC_ADAPT] User {user_id} matched tier for {npc_type} (Affinity: {current_affinity})")
            
        return adaptive_data


    async def _fish_action(self, ctx_or_interaction):
        """Executes the core fishing logic.
        
        Delegates to the extracted implementation in commands/fish.py.
        """
        await _fish_action_impl(self, ctx_or_interaction)
    
    @app_commands.command(name="banca", description="Bán cá - Dùng /banca [fish_types]")
    @app_commands.describe(
        fish_types="Fish key phân cách bằng dấu phẩy (ví dụ: ca_ro hoặc ca_chep, ca_koi)",
        mode="Chế độ bán (vip = giữ cá VIP - Tier 3 only)"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Bán tất cả", value="all"),
        app_commands.Choice(name="💎 Giữ cá VIP (Tier 3)", value="vip")
    ])
    async def sell_fish_slash(self, interaction: discord.Interaction, fish_types: str = None, mode: str = "all"):
        """Sell selected fish via slash command"""
        await interaction.response.defer()
        await self._sell_fish_action(interaction, fish_types, mode)
    
    @commands.command(name="banca", description="Bán cá - Dùng !banca [fish_types]")
    async def sell_fish_prefix(self, ctx, mode: str = "all", *, fish_types: str = None):
        """Sell selected fish via prefix command"""
        logger.info(f"[DEBUG] !banca invoked by {ctx.author} (fish_types={fish_types}, mode={mode})")
        await self._sell_fish_action(ctx, fish_types, mode)
    
    async def _sell_fish_action(self, ctx_or_interaction, fish_types: str = None, mode: str = "all"):
        """Sell all fish or specific types logic. Delegate to commands module."""
        logger.info(f"[DEBUG] Delegating to _sell_fish_impl (mode={mode})")
        return await _sell_fish_impl(self, ctx_or_interaction, fish_types, mode)
    
    @app_commands.command(name="moruong", description="Mở Rương Kho Báu")
    @app_commands.describe(amount="Số lượng rương muốn mở (mặc định 1)")
    async def open_chest_slash(self, interaction: discord.Interaction, amount: int = 1):
        """Open chest via slash command"""
        await interaction.response.defer()
        await self._open_chest_action(interaction, amount)
    
    @commands.command(name="moruong", description="Mở Rương Kho Báu")
    async def open_chest_prefix(self, ctx, amount: int = 1):
        """Open chest via prefix command"""
        await self._open_chest_action(ctx, amount)
    
    async def _open_chest_action(self, ctx_or_interaction, amount: int = 1):
        """Open treasure chest logic. Delegate to bucket module."""
        return await _open_chest_impl(self, ctx_or_interaction, amount)
    
    # ==================== LEGENDARY SUMMONING ====================
    
    @app_commands.command(name="hiente", description="🌊 Hiến tế cá cho Thuồng Luồng")
    @app_commands.describe(fish_key="Fish key - chỉ cá có giá > 150 hạt (vd: ca_chep_vang, ca_chim)")
    async def hiente_slash(self, interaction: discord.Interaction, fish_key: str):
        await interaction.response.defer()
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
        await interaction.response.defer()
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
        await interaction.response.defer()
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
        await interaction.response.defer()
        await self._ghepbando_action(interaction, is_slash=True)
    
    @commands.command(name="ghepbando", description="🗺️ Ghép Bản Đồ Hầm Ám")
    async def ghepbando_prefix(self, ctx):
        await self._ghepbando_action(ctx, is_slash=False)
    
    async def _ghepbando_action(self, ctx_or_interaction, is_slash: bool):
        """Combine map pieces. Delegate to craft module."""
        return await _ghepbando_impl(self, ctx_or_interaction, is_slash)

    @app_commands.command(name="bonphan", description="🌾 Bón phân cho cây server")
    async def bonphan_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._use_phan_bon_action(interaction)
    
    @commands.command(name="bonphan", description="🌾 Bón phân cho cây server")
    async def bonphan_prefix(self, ctx):
        await self._use_phan_bon_action(ctx)
    
    # Legacy taiche removed - Moved to cogs.aquarium
    # @app_commands.command(name="taiche") ... removed

    async def _use_phan_bon_action(self, ctx_or_interaction):
        """Use phan_bon logic. Delegate to bucket module."""
        return await _use_phan_bon_impl(self, ctx_or_interaction)

    async def _view_collection_action(self, ctx_or_interaction, user_id: int, username: str):
        """View fishing collection (Delegate to implementation)"""
        logger.info(f"[COLLECTION] User {username} ({user_id}) requested collection view")
        try:
             await _view_collection_impl_v2(self, ctx_or_interaction, user_id, username)
        except Exception as e:
            logger.error(f"[COLLECTION] Error in _view_collection_action for {username}: {e}")
            # Could provide fallback embed here if needed
    
    @app_commands.command(name="suutapca", description="📚 Xem bộ sưu tập cá của bạn")
    async def collection_slash(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        await self._view_collection_action(interaction, target.id, target.name)
    
    @commands.command(name="suutapca", aliases=["bosuutap"], description="Xem bộ sưu tập cá")
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
    # Note: _clear_expired_disaster and _check_server_freeze moved to mechanics/disasters.py
    
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
        fish_count = sum(v for k, v in inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS and k != ItemKeys.CA_ISEKAI)
        
        if fish_count >= FISH_BUCKET_LIMIT:
            # CHECK VIP FOR AUTO-SELL (Tier 2/3 see task.md - user said Tier 3 gets benefit of Tier 2, implying Tier 2 might have it? User said "when vip user ... tier 3 must get tier 2 benefit")
            # VIP Logic.py usually has tiers. Let's assume Tier 2+ has auto-sell, or specifically Tier 3 as per user request context "Auto bán khi đầy túi".
            # Checking `vip.py` logic or just checking Tier >= 2.
            # User phrase: "cái cơ chế auto bán khi đầy túi tức là khi user vip sài !cauca khi túi đầy thì phải tự bán"
            # It implies ALL VIPs or specific tier.
            # Safe bet: Tier 2 (Platinum) usually has convenience perks.
            # Let's check VIPEngine.
            from core.services.vip_service import VIPEngine
            vip_data = await VIPEngine.get_vip_data(user_id)
            vip_tier = vip_data['tier'] if vip_data else 0
            
            if vip_tier >= 2: # Assuming Tier 2+ gets Auto Sell
                logger.info(f"[FISHING] [VIP] {username} (Tier {vip_tier}) bucket full -> Auto Selling")
                
                # Import dynamically to avoid circular import at top level if possible, or just standard import
                # Since sell.py is in commands, and cog.py is core, better to import inside or check structure.
                # `sell_fish_action` is in `cogs.fishing.commands.sell`
                from .commands.sell import sell_fish_action
                
                # Execute Sell
                # Note: sell_fish_action sends its own embed response (Invoice)
                await sell_fish_action(self, ctx)
                
                # IMPORTANT: Return False so fishing can CONTINUE
                # But we must ensure sell_fish_action actually cleared space.
                # Since we await it, and it's transactional, it should be done.
                # However, we should re-check inventory or assume it worked?
                # Best to trust generic validation in sell_fish_action.
                
                # Wait, if sell fails (e.g. no sellable fish?), we shouldn't infinite loop.
                # `sell_fish_action` checks for sellable fish.
                # If only legendary fish (unsellable) fill the bucket, sell will fail/do nothing.
                # Then we return False? No, if we return False, they fish again -> bucket full -> loop?
                # Actually, `process_fishing_cast` calls this. If we return False, it proceeds to cast.
                # Then it catches fish.
                # Wait, does catching fish fail if bucket is full?
                # Logic at line 1526: "Check if bucket is full after fishing".
                # So `process_fishing_cast` checks limit at START (via this function) and END.
                # If we bypass START check, they fish.
                # If bucket is truly full of UNSELLABLE items, they catch +1.
                # If it exceeds limit at END, it might warn or just stack.
                # BUT, if they have only unsellable fish, `sell_fish_action` will say "No fish to sell".
                # And we proceed to fish.
                # This breaks the "hard limit" for VIPs if they hoard legendaries.
                # Risks: Infinite fish glitch?
                # Solution: Check if space was cleared?
                # For now, implementing as requested: "tự bán và câu mới luôn".
                # I will add a small re-check or just proceed.
                # If sell returns, we proceed.
                return False
            
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
    
    # Note: _check_and_repair_rod moved to mechanics/rod_system.py as check_and_repair_rod()
    
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
        from datetime import datetime
        
        try:
            # Check harvest buff timer first (primary source - set when harvest level 6)
            row = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = $1",
                (int(guild_id),)
            )
            if row and row[0]:
                buff_until = row[0]
                # PostgreSQL returns datetime, legacy SQLite returns string
                if isinstance(buff_until, str):
                    buff_until = datetime.fromisoformat(buff_until)
                if datetime.now() < buff_until:
                    return True  # Harvest buff is active
            
            # Fallback: Check if tree is at level 5+ (persistent bonus)
            tree_row = await db_manager.fetchone(
                "SELECT current_level FROM server_tree WHERE guild_id = $1",
                (int(guild_id),)
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
        from .mechanics.glitch import apply_glitch_aggressive
        return apply_glitch_aggressive(text)
    
    async def add_inventory_item(self, user_id: int, item_id: str, item_type: str):
        """Add item to inventory."""
        await self.bot.inventory.modify(user_id, item_id, 1)
        try:
            await db_manager.modify(
                "UPDATE inventory SET item_type = $1 WHERE user_id = $2 AND item_id = $3",
                (item_type, user_id, item_id)
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
    async def get_title(self, user_id: int, guild_id: int) -> str:
        """Get user's title."""
        if user_id in self.user_titles:
            return self.user_titles[user_id]
        # Get Tree Cog from bot
        Tree = self.bot.get_cog("Tree")
        if not Tree:
            return "" # Or handle error appropriately
        
        try:
            guild = self.bot.get_guild(guild_id)
            if guild:
                user = guild.get_member(user_id)
                if user:
                    role_id = await get_server_config(guild.id, "role_vua_cau_ca")
                    role = guild.get_role(int(role_id)) if role_id else None
                    if role and role in user.roles:
                        title = "👑 Vua Câu Cá 👑"
                        self.user_titles[user_id] = title
                        return title
        except Exception as e:
            logger.error(f"[TITLE] Error getting title: {e}")
        
        return ""
    
    async def update_rod_data(self, user_id: int, durability: int, level: int | None = None):
        """Update rod durability (and level if provided)"""
        await update_rod_data(user_id, durability, level)
    
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
            await self.bot.inventory.modify(user_id, fish_key, -1)
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
            
            await add_seeds(user_id, -cost, 'npc_interaction_cost', 'fishing')
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
        
        if reward_type == ItemKeys.MOI:
            amount = selected_reward.get("amount", 5)
            await self.bot.inventory.modify(user_id, ItemKeys.MOI, amount)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received {amount} worms from {npc_type}")
        
        elif reward_type == "lucky_buff":
            await self.emotional_state_manager.apply_emotional_state(user_id, "lucky_buff", 1)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received lucky buff from {npc_type}")
        
        elif reward_type == "chest":
            amount = selected_reward.get("amount", 1)
            await self.bot.inventory.modify(user_id, ItemKeys.RUONG_KHO_BAU, amount)
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
            await add_seeds(user_id, amount, 'npc_reward_money', 'fishing')
            result_text = selected_reward["message"]
            # Add amount to message if not already included
            if "{amount}" in result_text:
                result_text = result_text.replace("{amount}", f"**{amount} Hạt**")
            elif "Hạt" not in result_text:
                result_text += f" (**+{amount} Hạt**)"
            logger.info(f"[NPC] User {user_id} received {amount} seeds from {npc_type}")
        
        elif reward_type == "ngoc_trai":
            amount = selected_reward.get("amount", 1)
            await self.bot.inventory.modify(user_id, ItemKeys.NGOC_TRAI, amount)
            result_text = selected_reward["message"]
            logger.info(f"[NPC] User {user_id} received {amount} ngoc_trai(s) from {npc_type}")
        
        elif reward_type == "vat_lieu_nang_cap":
            amount = selected_reward.get("amount", 2)
            await self.bot.inventory.modify(user_id, ItemKeys.VAT_LIEU_NANGCAP, amount)
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
            await add_seeds(user_id, price, 'npc_reward_triple_money', 'fishing')
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
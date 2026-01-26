"""Fish command implementation - Core fishing action logic.

This module contains the main fishing logic extracted from FishingCog._fish_action.
The function receives the cog instance to access bot, state, and helper methods.
"""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..cog import FishingCog

import discord

from core.logging import get_logger
# Import constants from parent package
from ..constants import (
    ALL_FISH, ALL_ITEMS_DATA, CATCH_COUNT_WEIGHTS,
    COMMON_FISH, COMMON_FISH_KEYS, CRYPTO_LOSS_CAP,
    FISH_BUCKET_LIMIT, LEGENDARY_FISH_DATA, LEGENDARY_FISH_KEYS,
    LOOT_TABLE_BOOST, LOOT_TABLE_NORMAL, LOOT_TABLE_NO_WORM,
    NPC_ENCOUNTERS, NPC_ENCOUNTER_CHANCE, NPC_ENCOUNTER_DELAY,
    RANDOM_EVENTS, RARE_FISH, RARE_FISH_KEYS, ROD_LEVELS,
    SNAKE_BITE_PENALTY_PERCENT, TRASH_ITEMS, WORM_COST
)
from configs.item_constants import ItemKeys, ItemType

# Import mechanics
from ..mechanics.rod_system import get_rod_data, check_and_repair_rod as _check_and_repair_rod_impl
from ..ui import LegendaryBossFightView, InteractiveNPCView
from ..mechanics.legendary import check_legendary_spawn_conditions
from ..mechanics.events import trigger_random_event
from ..mechanics.disasters import (
    check_server_freeze as _check_server_freeze_impl,
    clear_expired_disaster as _clear_expired_disaster_impl
)


# Import helpers
from ..helpers import track_caught_fish, get_collection, check_collection_complete

# Import database functions
from database_manager import (
    add_seeds, get_user_balance, get_or_create_user, db_manager,
    get_stat, increment_stat, get_server_config, deduct_seeds_if_sufficient
)

# Import tournament
from ..tournament import TournamentManager

# Import seasonal event fish hook
from cogs.seasonal.event_fish_hook import try_catch_event_fish

logger = get_logger("fishing_commands_fish")

async def fish_action_impl(cog: "FishingCog", ctx_or_interaction: Any) -> None:
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
        if await cog.check_emotional_state(user_id, "lag"):
            await asyncio.sleep(3)
            username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
            logger.info(f"[EVENT] {username} experienced lag delay (3s) - start of cast")
        
        # --- GET USER AND ROD DATA ---
        rod_lvl, rod_durability = await get_rod_data(user_id)
        rod_config = ROD_LEVELS.get(rod_lvl, ROD_LEVELS[1])
        # [CACHE] Use bot.inventory instead of direct DB call
        inventory = await cog.bot.inventory.get_all(user_id)
        username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
        logger.info(f"[FISHING] [ROD_DATA] {username_display} (user_id={user_id}) rod_level={rod_lvl} durability={rod_durability}/{rod_config['durability']}")
        
        # [DEBUG] Trace execution
        logger.info(f"[FISHING] [DEBUG] Checking server freeze for {user_id}")
        
        # --- CHECK FOR SERVER FREEZE (GLOBAL DISASTER) ---
        username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
        if await _check_server_freeze_impl(cog, user_id, username_display, is_slash, ctx):
            return


        # --- CHECK FOR NON-FREEZE DISASTER EFFECTS EXPIRING ---
        await _clear_expired_disaster_impl(cog)

        # [DEBUG] Trace execution
        logger.info(f"[FISHING] [DEBUG] Checking bucket limit for {user_id}")

        # --- CHECK FISH BUCKET LIMIT (BEFORE ANYTHING ELSE) ---
        username_display = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
        if await cog._check_bucket_limit(user_id, inventory, username_display, is_slash, ctx):
            return
    
        # [DEBUG] Trace execution
        logger.info(f"[FISHING] [DEBUG] Checking repair for {user_id}")

        # --- CHECK DURABILITY & AUTO REPAIR ---
        async def _achievement_callback(uid: int, stat_key: str, current_value: int):
            await cog.bot.achievement_manager.check_unlock(
                user_id=uid,
                game_category="fishing",
                stat_key=stat_key,
                current_value=current_value,
                channel=channel
            )
        
        rod_durability, repair_msg, is_broken_rod = await _check_and_repair_rod_impl(
            user_id, rod_lvl, rod_durability, rod_config, username_display, _achievement_callback
        )

    
        # Ensure user exists
        username = ctx.author.name if not is_slash else ctx_or_interaction.user.name
        
        # [DEBUG] Trace execution
        logger.info(f"[FISHING] [DEBUG] Getting/Creating user {user_id}")
        
        await get_or_create_user(user_id, username)

        # ==================== FIX: COOLDOWN BYPASS & RACE CONDITIONS ====================
        # Initialize lock if not exists - REMOVED

        # START DATABASE TRANSACTION
        # Replaces legacy asyncio.Lock to handle concurrency via DB serialization
        async with db_manager.transaction() as conn:
            logger.info(f"[FISHING] [DEBUG] Transaction started for {user_id}")
            
            try:
                # --- CHECK COOLDOWN (Inside Lock) ---
                remaining = await cog.get_fishing_cooldown_remaining(user_id)
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
                            # Auto-delete cooldown message when cooldown expires
                            # Use actual remaining time instead of hardcoded 10 seconds
                            await ctx.reply(msg, delete_after=remaining)
                        except Exception as e:
                            logger.error(f"[FISHING] Error sending cooldown message: {e}")
                    return
            
                # --- APPLY DISASTER COOLDOWN PENALTY (Check early) ---
                # We need to know the cooldown time to set it later, but we set a temporary "processing" cooldown
                # to prevent other commands from entering while this one processes (though the lock handles it mostly,
                # setting it in DB/memory provides double safety for distributed systems if ever expanded)
            
                # --- TRIGGER GLOBAL DISASTER (0.05% chance) ---
                # Use timeout to prevent hang due to I/O blocking
                try:
                    logger.info(f"[FISHING] [DEBUG] Checking global disaster for {user_id}")
                    disaster_result = await asyncio.wait_for(
                        cog.trigger_global_disaster(user_id, username, channel),
                        timeout=5.0
                    )
                    logger.info(f"[FISHING] [DEBUG] Disaster check done for {user_id}, triggered={disaster_result.get('triggered')}")
                except asyncio.TimeoutError:
                    logger.error(f"[FISHING] [CRITICAL] Disaster check timed out for {user_id} - skipping")
                    disaster_result = {"triggered": False}
                except Exception as e:
                    logger.error(f"[FISHING] Error in disaster trigger: {e}")
                    disaster_result = {"triggered": False}
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
                # [WATCHDOG] Wrap Auto-Buy logic with timeout to prevent DB hangs
                try:
                    async with asyncio.timeout(5.0):
                        has_worm = inventory.get(ItemKeys.MOI, 0) > 0
                        auto_bought = False  # Biến check xem có tự mua không
    
                        # Nếu không có mồi, kiểm tra xem có đủ tiền mua không
                        if not has_worm:
                            success, balance = await deduct_seeds_if_sufficient(
                                user_id, WORM_COST, 'auto_buy_worm', 'fishing'
                            )
                            if success:
                                has_worm = True
                                auto_bought = True
                                logger.info(f"[FISHING] [AUTO_BUY_WORM] {username} (user_id={user_id}) seed_change=-{WORM_COST} balance_after={balance}")
                            else:
                                has_worm = False
                                logger.info(f"[FISHING] [NO_WORM_NO_MONEY] {username} (user_id={user_id}) has_worm=False balance={balance} < {WORM_COST}")
                except asyncio.TimeoutError:
                     logger.error(f"[FISHING] [CRITICAL] Auto-buy check timed out for {user_id} - assuming no worm")
                     has_worm = False
                     auto_bought = False
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
                        # [CACHE] Use bot.inventory.modify
                        await cog.bot.inventory.modify(user_id, ItemKeys.MOI, -1)
                        # Track worms used for achievement
                        try:
                            await increment_stat(user_id, "fishing", "worms_used", 1)
                            current_worms = await get_stat(user_id, "fishing", "worms_used")
                            # Check achievement: worm_destroyer (100 worms)
                            await cog.bot.achievement_manager.check_unlock(
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
                if cog.disaster_fine_amount > 0 and time.time() < cog.disaster_effect_end_time:
                    success, current_balance = await deduct_seeds_if_sufficient(
                        user_id, cog.disaster_fine_amount, 'disaster_fine', 'fishing'
                    )
                    if success:
                        disaster_fine_msg = f"\n💰 **PHẠT HÀNH CHÍNH:** -{ cog.disaster_fine_amount} Hạt do {cog.current_disaster.get('name', 'sự kiện')}"
                        logger.info(f"[DISASTER_FINE] {username} fined {cog.disaster_fine_amount} seeds due to {cog.current_disaster.get('key')} balance_after={current_balance}")
                    else:
                        disaster_fine_msg = f"\n⚠️ **PHẠT HÀNH CHÍNH:** Không đủ tiền phạt ({cog.disaster_fine_amount} Hạt)"
                        logger.info(f"[DISASTER_FINE] {username} insufficient balance for fine {cog.disaster_fine_amount} balance={current_balance}")

    
                logger.info(f"[FISHING] [START] {username} (user_id={user_id}) rod_level={rod_lvl} rod_durability={rod_durability} has_bait={has_worm}")
    
                # Track if this cast triggers global reset (will affect cooldown setting)
                triggers_global_reset = False
        
                # Set cooldown using rod-based cooldown (will be cleared if global_reset triggers)
                cooldown_time = rod_config["cd"]

                # Apply Global Event Cooldown Multiplier
                cd_mul = cog.global_event_manager.get_public_effect("cooldown_multiplier", 1.0)
                if cd_mul != 1.0:
                    cooldown_time *= cd_mul
                    # Ensure at least 1 second if multiplier is extremely low but not 0
                    if cooldown_time < 1: cooldown_time = 1
        
                # *** APPLY DISASTER COOLDOWN PENALTY (Shark Bite Cable effect) ***
                if cog.disaster_cooldown_penalty > 0 and time.time() < cog.disaster_effect_end_time:
                    cooldown_time += cog.disaster_cooldown_penalty
                    logger.info(f"[DISASTER] {username} cooldown increased by {cog.disaster_cooldown_penalty}s due to {cog.current_disaster.get('name', 'disaster')}")
        
                cog.fishing_cooldown[user_id] = time.time() + cooldown_time
    
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
                user_luck = await cog.get_user_total_luck(user_id)
                logger.info(f"[FISHING] {username} Luck: {user_luck*100:.1f}%")
    
                event_result = await trigger_random_event(cog, user_id, channel.guild.id, rod_lvl, channel, luck=user_luck)
    
                # If user avoided a bad event, show what they avoided
                if event_result.get("avoided", False):
                    protection_desc = f"✨ **Giác Quan Thứ 6 hoặc Đi Chùa bảo vệ bạn!**\n\n{event_result['message']}\n\n**Bạn an toàn thoát khỏi sự kiện này!**"
                    embed = discord.Embed(
                        title=cog.apply_display_glitch(f"🛡️ BẢO VỆ - {username}!"),
                        description=cog.apply_display_glitch(protection_desc),
                        color=discord.Color.gold()
                    )
                    await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
                    await asyncio.sleep(1)
                    casting_msg = await channel.send(f"🎣 **{username}** câu tiếp...")
                    # Skip event processing since it was avoided - continue to normal fishing
                    event_result["triggered"] = False
    
                # Check if user was protected from bad event
                was_protected = False
                if hasattr(cog, "avoid_event_users") and cog.avoid_event_users.get(user_id, False):
                    was_protected = True
    
                # *** INITIALIZE DURABILITY LOSS ***
                # Extract event durability penalty FIRST before setting default
                event_durability_penalty = abs(event_result.get("durability_loss", 0))
            
                if event_durability_penalty > 0:
                    # Event specified durability loss (e.g., flexing = 20)
                    durability_loss = event_durability_penalty
                    logger.info(f"[EVENT] {username} event durability penalty: {durability_loss}")
                else:
                    # Default durability loss per cast
                    durability_loss = 1
        
                # Apply Global Event Durability Multiplier
                dur_mul = cog.global_event_manager.get_public_effect("durability_multiplier", 1.0)
                if dur_mul != 1.0:
                    durability_loss = int(durability_loss * dur_mul)
                    # Ensure at least 1 if multiplier is > 0
                    if durability_loss < 1: durability_loss = 1
    
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
                            await increment_stat(user_id, "fishing", "good_events_encountered", 1)
                            current_good_events = await get_stat(user_id, "fishing", "good_events_encountered")
                            await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "good_events", current_good_events, channel)
                        else:
                            # Track bad events
                            await increment_stat(user_id, "fishing", "bad_events_encountered", 1)
                            current_bad_events = await get_stat(user_id, "fishing", "bad_events_encountered")
                            await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "bad_events", current_bad_events, channel)
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
        
                    # *** SPECIAL DURABILITY OVERRIDES FOR SPECIFIC EVENTS ***
                    # These override event penalty for special cases
                    if event_type == "equipment_break":
                        # Gãy cần: Trừ hết độ bền
                        durability_loss = rod_durability
                    elif event_type in ["snapped_line", "plastic_trap", "big_log", "crab_cut", "electric_eel"] and event_durability_penalty == 0:
                        # ONLY override if event didn't specify penalty
                        durability_loss = 5
                    elif event_type == "predator" and event_durability_penalty == 0:
                        # Cá dữ: Trừ 3 độ bền
                        durability_loss = 3

        

                    # *** SIXTH SENSE PROTECTION LOGIC ***
                    if was_protected:
                        # Check if event is negative
                        is_bad_event = (
                            event_result.get("lose_money", 0) > 0 or 
                            event_result.get("lose_worm", False) or 
                            event_result.get("lose_catch", False) or 
                            event_result.get("custom_effect") in ["snake_bite", "crypto_loss"] or
                            event_durability_penalty > 0
                        )
                    
                        if is_bad_event:
                            # Suppress all negative effects
                            event_result["lose_money"] = 0
                            event_result["lose_worm"] = False
                            event_result["lose_catch"] = False
                        
                            if event_result.get("custom_effect") in ["snake_bite", "crypto_loss"]:
                                event_result["custom_effect"] = None
                        
                            # Reset durability penalty
                            if event_durability_penalty > 0:
                                durability_loss = 1  # Reset to default
                        
                            event_message += "\n🛡️ **Giác Quan Thứ 6** đã chặn đứng xui xẻo!"
                            logger.info(f"[EVENT] {username} consumed Sixth Sense to avoid bad event.")
                        
                            # Consume Buff
                            if hasattr(cog, "avoid_event_users") and user_id in cog.avoid_event_users:
                                del cog.avoid_event_users[user_id]

                    # Process event effects
                    if event_result.get("lose_worm", False) and has_worm:
                        await cog.bot.inventory.modify(user_id, ItemKeys.MOI, -1)
                        event_message += " (Mất 1 Giun)"
        
                    if event_result.get("lose_money", 0) > 0:
                        # SECURITY: Never let balance go negative
                        current_balance = await get_user_balance(user_id)
                        penalty_amount = min(event_result["lose_money"], current_balance)
                
                        if penalty_amount > 0:
                            await add_seeds(user_id, -penalty_amount, 'fishing_event_penalty', 'fishing')
                            event_message += f" (-{penalty_amount} Hạt)"
                    
                            # Log if penalty was capped
                            if penalty_amount < event_result["lose_money"]:
                                logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) Penalty capped: {event_result['lose_money']} → {penalty_amount} (insufficient balance)")
                        else:
                            event_message += f" (Không đủ tiền để bị phạt!)"
        
                    if event_result.get("gain_money", 0) > 0:
                        await add_seeds(user_id, event_result["gain_money"], 'fishing_event_money', 'fishing')
                        event_message += f" (+{event_result['gain_money']} Hạt)"
        
                    # Process gain_items (ngoc_trais, worms, chests, etc.)
                    if event_result.get("gain_items", {}):
                        for item_key, item_count in event_result["gain_items"].items():
                            # Special check for ca_isekai: don't gain if already have
                            if item_key == ItemKeys.CA_ISEKAI:
                                inventory = await cog.bot.inventory.get_all(user_id)
                                if inventory.get(ItemKeys.CA_ISEKAI, 0) > 0:
                                    continue  # Skip adding ca_isekai if already have
                            await cog.bot.inventory.modify(user_id, item_key, item_count)
                            item_id = ALL_FISH.get(item_key, {}).get("name", item_key)
                            event_message += f" (+{item_count} {item_id})"
        
                    # Handle special effects
                    if event_result.get("custom_effect") == "lose_all_bait":
                        # sea_sickness: Lose all bait (worm)
                        worm_count = inventory.get(ItemKeys.MOI, 0)
                        if worm_count > 0:
                            await cog.bot.inventory.modify(user_id, ItemKeys.MOI, -worm_count)
                            event_message += f" (Nôn hết {worm_count} Giun)"
                            logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=sea_sickness inventory_change=-{worm_count} item=worm")
        
                    elif event_result.get("custom_effect") == "cat_steal":
                        # Black Cat: Steals the biggest fish (handle later in catch result)
                        # Logic deferred to line 1301
                        pass
        
                    elif event_result.get("custom_effect") == "snake_bite":
                        # Water Snake: Minus 5% assets
                        balance = await get_user_balance(user_id)
                        penalty = max(10, int(balance * SNAKE_BITE_PENALTY_PERCENT))
                        # Cap at crypto loss cap (5000) for consistency
                        if penalty > CRYPTO_LOSS_CAP:
                            penalty = CRYPTO_LOSS_CAP
                        await add_seeds(user_id, -penalty, 'fishing_event_penalty', 'fishing')
                        event_message += f" (Trừ 5% tài sản: {penalty} Hạt)"
                        logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=snake_bite seed_change=-{penalty} penalty_type=asset_penalty")
        
                    elif event_result.get("custom_effect") == "gain_money_percent":
                        # Crypto Pump: Gain 5% assets
                        from ..constants import GAIN_PERCENT_CAP
                        balance = await get_user_balance(user_id)
                        gain = max(100, int(balance * 0.05))
                        # Cap at 30k (defined in settings)
                        if gain > GAIN_PERCENT_CAP:
                            gain = GAIN_PERCENT_CAP
                        await add_seeds(user_id, gain, 'fishing_event_bonus', 'fishing')
                        event_message += f" (Tăng 5% tài sản: +{gain} Hạt)"
                        logger.info(f"[FISHING] [EVENT] {username} (user_id={user_id}) event=crypto_pump seed_change=+{gain} bonus_type=asset_bonus")
        
                    elif event_result.get("custom_effect") == "lucky_buff":
                        # Double Rainbow: Next catch guaranteed rare
                        # Store in temporary cache
                        if not hasattr(cog, "lucky_buff_users"):
                            cog.lucky_buff_users = {}
                        cog.lucky_buff_users[user_id] = True
                        event_message += " (Lần câu sau chắc ra Cá Hiếm!)"
                        logger.info(f"[EVENT] {username} received lucky buff for next cast")
        
                    elif event_result.get("custom_effect") == "sixth_sense":
                        # Sixth Sense: Avoid next bad event
                        if not hasattr(cog, "avoid_event_users"):
                            cog.avoid_event_users = {}
                        cog.avoid_event_users[user_id] = True
                        event_message += " (Lần sau tránh xui!)"
                        logger.info(f"[EVENT] {username} will avoid bad event on next cast")
        
                    elif event_result.get("custom_effect") == "suy_debuff":
                        # Depression debuff: 50% rare catch reduction for 5 casts
                        await cog.apply_emotional_state(user_id, "suy", 5)
                        event_message += " (Bạn bị 'suy' 😭 - Giảm 50% tỉ lệ cá hiếm trong 5 lần câu)"
                        logger.info(f"[EVENT] {username} afflicted with suy debuff for 5 casts")
        
                    elif event_result.get("custom_effect") == "keo_ly_buff":
                        # Slay buff: 2x sell price for 10 minutes (600 seconds)
                        await cog.apply_emotional_state(user_id, "keo_ly", 600)
                        event_message += " (Keo Lỳ tái châu! 💅 - x2 tiền bán cá trong 10 phút)"
                        logger.info(f"[EVENT] {username} activated keo_ly buff for 600 seconds")
        
                    elif event_result.get("custom_effect") == "lag_debuff":
                        # Lag debuff: 3s delay per cast for 5 minutes (300 seconds)
                        await cog.apply_emotional_state(user_id, "lag", 300)
                        event_message += " (Mạng lag! 📶 - Bot sẽ phản hồi chậm 3s cho mỗi lần câu trong 5 phút)"
                        logger.info(f"[EVENT] {username} afflicted with lag debuff for 300 seconds")
        
                    elif event_result.get("custom_effect") == "restore_durability":
                        # Restore Durability: +20 (Max capped)
                        max_durability = rod_config["durability"]
                        rod_durability = min(max_durability, rod_durability + 20)
                        await cog.update_rod_data(user_id, rod_durability)
                        event_message += f" (Độ bền +20: {rod_durability}/{max_durability})"
                        logger.info(f"[EVENT] {username} restored rod durability to {rod_durability}")
        
                    # Note: global_reset is handled after event embed display below
        
                    # Adjust cooldown (golden_turtle có thể là -30 để reset)
                    if event_result.get("cooldown_increase", 0) != 0:
                        if event_result["cooldown_increase"] < 0:
                            # Reset cooldown (golden_turtle)
                            cog.fishing_cooldown[user_id] = time.time()
                            event_message += " (Thời gian chờ xóa sạch!)"
                            logger.info(f"[EVENT] {username} Thời gian chờ reset")
                        else:
                            cog.fishing_cooldown[user_id] = time.time() + rod_config["cd"] + event_result["cooldown_increase"]
                    # Note: normal cooldown already set at line 225, only override if special cooldown_increase
        
                    # If lose_catch, don't process fishing
                    if event_result.get("lose_catch", False):
                        event_display = cog.apply_display_glitch(event_message)
                        embed = discord.Embed(
                            title=f"⚠️ KIẾP NẠN - {username}!",
                            description=event_display,
                            color=discord.Color.red()
                        )
                        # Apply durability loss before returning
                        rod_durability = max(0, rod_durability - durability_loss)
                        await cog.update_rod_data(user_id, rod_durability)
                        durability_display = cog.apply_display_glitch(f"🛡️ Độ bền: {rod_durability}/{rod_config['durability']}")
                        embed.set_footer(text=durability_display)
                        await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
                        logger.info(f"[EVENT] {username} triggered {event_type} - fishing cancelled, durability loss: {durability_loss}")
                        return
        
                    # Otherwise, display event message and continue fishing
                    event_display = cog.apply_display_glitch(event_message)
                    event_type_data = RANDOM_EVENTS.get(event_type, {})
                    is_good_event = event_type_data.get("type") == "good"
                    color = discord.Color.green() if is_good_event else discord.Color.orange()
                    event_title = f"🌟 PHƯỚC LÀNH - {username}!" if is_good_event else f"⚠️ KIẾP NẠN - {username}!"
                    event_title = cog.apply_display_glitch(event_title)
                    embed = discord.Embed(
                        title=event_title,
                        description=event_display,
                        color=color
                    )
                    await casting_msg.edit(content=f"<@{user_id}>", embed=embed)
        
                    # Special embed for Isekai event - show legendary fish info or rejection
                    if event_type == "isekai_truck":
                        inventory = await cog.bot.inventory.get_all(user_id)
                        has_isekai = inventory.get(ItemKeys.CA_ISEKAI, 0) > 0
                    
                        if has_isekai:
                            # User ALREADY has the fish -> FAIL (Meaningless Bump)
                            # Update the Main Event Embed to reflect Failure/Neutrality instead of "Blessing"
                            failed_title = cog.apply_display_glitch("⚠️ CÚ HÚC VÔ NGHĨA - " + username)
                            # Remove "PHƯỚC LÀNH" from description if present
                            failed_desc = event_display.replace("PHƯỚC LÀNH", "CÚ HÚC")
                        
                            failed_embed = discord.Embed(
                                title=failed_title,
                                description=failed_desc,
                                color=discord.Color.light_grey()
                            )
                            await casting_msg.edit(content=f"<@{user_id}>", embed=failed_embed)

                            embed = discord.Embed(
                                title="🚚 CÚ HÚC... VÔ NGHĨA!",
                                description="Rầm! Truck-kun húc bạn bay sang dị giới. Bạn hào hứng mở mắt ra, chuẩn bị đón nhận dàn Harem và sức mạnh bá đạo...\n\nNhưng chớp mắt một cái, bạn thấy mình vẫn đang ngồi đần mặt cầm cần câu ở cái hồ này. Hóa ra Nữ Thần Dị Giới đã **từ chối cấp Visa** cho bạn.\n\n*(Bạn đã sở hữu Cá Isekai rồi!)*\n\n*'Về đi, cứu thế giới một lần là đủ rồi!'* - Chẳng có gì xảy ra cả, quê thật sự.",
                                color=discord.Color.default()
                            )
                            await channel.send(embed=embed)
                        else:
                            # User does NOT have fish -> SUCCESS -> Grant Item Manually
                            # This block replaces the generic gain_items logic we removed
                            await cog.bot.inventory.modify(user_id, ItemKeys.CA_ISEKAI, 1)
                            logger.info(f"[EVENT] {username} received ca_isekai from isekai_truck event")
                        
                            # Find the legendary fish data
                            legendary_fish = next((fish for fish in LEGENDARY_FISH_DATA if fish["key"] == ItemKeys.CA_ISEKAI), None)
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
                        cog.fishing_cooldown.clear()
            
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
                    # HOOK: Global Event Trash Multiplier
                    # Default multiplier is 1.0 (normal). If 0.0 -> No trash.
                    trash_mul = cog.global_event_manager.get_public_effect("trash_chance_multiplier", 1.0)
                
                    if trash_mul <= 0.0:
                         trash_count = 0 
                    else:
                        trash_count = random.choices([0, 1, 2], weights=[70, 25, 5], k=1)[0]
                        # Apply naive multiplier to count chance? Or re-roll?
                        # For simplicity, if mul > 1.0, we just increase trash count slightly
                        if trash_mul > 1.0 and trash_count > 0:
                            trash_count = int(trash_count * trash_mul)
                else:
                    # No bait / broken rod: High chance of trash (50/50)
                    trash_count = random.choices([0, 1], weights=[50, 50], k=1)[0]
    
                # Roll chest (independent, low chance)
                # BUT: If no bait OR broken rod -> never roll chest
                # Check for both tree boost AND lucky buff from NPC
                is_boosted = await cog.get_tree_boost_status(channel.guild.id)
                has_lucky_buff = await cog.check_emotional_state(user_id, "lucky_buff")
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
                    await cog.emotional_state_manager.decrement_counter(user_id, "lucky_buff")
    
                boost_text = " ✨**(BUFF MAY MẮN!)**✨" if has_lucky_buff else ("✨" if is_boosted else "")
    
                # Track caught items for sell button
                cog.caught_items[user_id] = {}
    
                # Build summary display and process all results
                fish_display = []
                fish_only_items = {}
                trash_items = {}  # Track specific trash items
                new_caught_fishes = set() # Track new catches for display
    
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
                # ==================== PREMIUM BUFF: MULTI CATCH ====================
                # Check if user has active multi_catch buff from Chấm Long Dịch
                premium_multi_catch = 1  # Default 1 fish
                if hasattr(cog, 'premium_buffs') and user_id in cog.premium_buffs:
                    buff = cog.premium_buffs[user_id]
                    if buff['type'] == 'multi_catch':  # No expiration - persists until consumed
                        premium_multi_catch = buff['count']
                        del cog.premium_buffs[user_id]  # Consume buff
                        logger.info(f"[PREMIUM_BUFF] {username} using multi_catch: {premium_multi_catch} fish")
                
                # Modify num_fish if premium buff active
                if premium_multi_catch > 1:
                    num_fish = premium_multi_catch
                
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
                    
                        # HOOK: Global Event Rare Fish Multiplier
                        rare_mul = cog.global_event_manager.get_public_effect("rare_chance_multiplier", 1.0)
                        if rare_mul != 1.0:
                            rare_ratio *= rare_mul
                            # Recalculate common to keep sum = 1.0 (approximately) inside choices logic
                            # But here we are setting weights for random.choices below.
                            # We just boost rare_ratio. Ideally we should normalize again but for game balance,
                            # adding raw probability is often more "feel good".
                            # Let's use the multiplier as direct boost if ratio is small, or multiplier if ratio is meaningful.
                            pass # rare_ratio is modified directly
                        
                        # HOOK: Aquarium Set Bonuses (rare_chance_bonus, catch_rate_bonus)
                        try:
                            from cogs.aquarium.logic.effect_manager import get_effect_manager
                            effect_manager = get_effect_manager()
                            
                            # Apply rare_chance_bonus (percentage bonus to rare fish chance)
                            rare_chance_mul = await effect_manager.get_multiplier(user_id, "rare_chance_bonus")
                            if rare_chance_mul > 1.0:
                                rare_ratio *= rare_chance_mul
                                logger.debug(f"[AQUARIUM] User {user_id} rare_chance_bonus x{rare_chance_mul:.2f}")
                            
                            # Apply catch_rate_bonus (increases overall fish catch vs trash)
                            catch_rate_mul = await effect_manager.get_multiplier(user_id, "catch_rate_bonus")
                            if catch_rate_mul > 1.0:
                                # Boost both common and rare proportionally, reduce trash chance
                                boost_factor = catch_rate_mul - 1.0  # e.g. 0.05 for 5% bonus
                                common_ratio = min(0.95, common_ratio * (1 + boost_factor))
                                rare_ratio = min(0.90, rare_ratio * (1 + boost_factor * 0.5))  # Half effect on rare
                                logger.debug(f"[AQUARIUM] User {user_id} catch_rate_bonus x{catch_rate_mul:.2f}")
                        except Exception as e:
                            logger.warning(f"[AQUARIUM] Failed to apply fishing bonuses for {user_id}: {e}")
        
                    # *** APPLY TOTAL USER LUCK (Centralized) ***
                    rare_ratio = min(0.9, rare_ratio + user_luck)  # Cap at 90% max
                
                    # Handle "suy" decrement (luck penalty is -0.2 in total luck)
                    # Handle "suy" decrement (luck penalty is -0.2 in total luck)
                    if await cog.check_emotional_state(user_id, "suy"):
                        await cog.decrement_suy_cast(user_id)
                    
                    # Log Ghost NPC usage (luck bonus is +0.3 in total luck)
                    # Log Ghost NPC usage (luck bonus is +0.3 in total luck)
                    if await cog.check_emotional_state(user_id, "legendary_buff"):
                        logger.info(f"[NPC_BUFF] {username} used legendary buff charge (Luck included in total)")
        
                    # *** APPLY DISASTER CATCH RATE PENALTY ***
                    current_time = time.time()
                    trash_rate = 0.0
                    if cog.disaster_catch_rate_penalty > 0 and current_time < cog.disaster_effect_end_time:
                        # Calculate trash rate from penalty
                        trash_rate = cog.disaster_catch_rate_penalty
                        # Reduce fish rates proportionally
                        total_fish_rate = rare_ratio + common_ratio
                        if total_fish_rate > 0:
                            fish_rate_after_penalty = total_fish_rate * (1.0 - cog.disaster_catch_rate_penalty)
                            rare_ratio = (rare_ratio / total_fish_rate) * fish_rate_after_penalty
                            common_ratio = (common_ratio / total_fish_rate) * fish_rate_after_penalty
                        else:
                            trash_rate = 0  # No fish to replace
                        logger.info(f"[DISASTER] {username} fish rate reduced by {int(cog.disaster_catch_rate_penalty*100)}%, trash rate: {int(trash_rate*100)}% due to {cog.current_disaster.get('name', 'disaster')}")
            
                    # Now roll: common, rare, or trash
                    total_weights = [common_ratio, rare_ratio, trash_rate]
                    choices = [ItemType.COMMON, ItemType.RARE, ItemType.TRASH]
                    catch_type = random.choices(choices, weights=total_weights, k=1)[0]
            
                    if catch_type == ItemType.TRASH:
                        # Catch trash instead of fish
                        if not TRASH_ITEMS:
                            logger.error("[FISHING] TRASH_ITEMS is empty! Cannot catch trash.")
                            continue

                        trash = random.choice(TRASH_ITEMS)
                        item_key = trash.get("key", f"trash_{hash(str(trash)) % 1000}")
                        try:
                            await cog.add_inventory_item(user_id, item_key, ItemType.TRASH)
                            if item_key not in trash_items: trash_items[item_key] = 0
                            trash_items[item_key] += 1
                            logger.info(f"[DISASTER_TRASH] {username} caught trash: {item_key} due to {cog.current_disaster.get('name', 'disaster')}")
                        except Exception as e:
                            logger.info(f"[FISHING] [ERROR] Failed to add trash item {item_key} for {username}: {e}")
                        continue  # Skip fish catching logic
        
                    # Check if convert_to_trash event is active (e.g., Pollution)
                    if event_result.get("convert_to_trash", False):
                        # Convert fish to trash
                        if not TRASH_ITEMS:
                            logger.error("[FISHING] TRASH_ITEMS is empty during pollution! Skipping.")
                            continue # Skip bad event logic if no trash items

                        trash = random.choice(TRASH_ITEMS)
                        item_key = trash.get("key", f"trash_{trash['name'].lower().replace(' ', '_')}")
                        await cog.add_inventory_item(user_id, item_key, ItemType.TRASH)
                        # Track for embed
                        if item_key not in trash_items: trash_items[item_key] = 0
                        trash_items[item_key] += 1
                    
                        logger.info(f"[EVENT-POLLUTION] {username} fish converted to trash: {item_key}")
                        continue
        
                    if catch_type == ItemType.RARE and not caught_rare_this_turn:
                        if not RARE_FISH:
                             logger.warning("[FISHING] RARE_FISH is empty! Falling back to common.")
                             catch_type = ItemType.COMMON # Fallback
                        else:
                            # Check VIP tier and add VIP fish to rare pool
                            from core.services.vip_service import VIPEngine
                            vip_data = await VIPEngine.get_vip_data(user_id)
                            vip_tier = vip_data['tier'] if vip_data else 0
                            
                            rare_pool = RARE_FISH.copy()
                            if vip_tier > 0:
                                from ..constants import get_vip_fish_for_tier, VIP_FISH_DATA
                                vip_fish_keys = get_vip_fish_for_tier(vip_tier)
                                for vip_fish in VIP_FISH_DATA:
                                    if vip_fish['key'] in vip_fish_keys:
                                        rare_pool.append(vip_fish)
                            
                            fish = random.choice(rare_pool)
                        caught_rare_this_turn = True  # Mark rare as caught to enforce limit
                        logger.info(f"[FISHING] {username} caught RARE fish: {fish['key']} ✨ (Max 1 rare per cast, Rod Luck: +{int(rod_config['luck']*100)}%)")
                        try:
                            await cog.add_inventory_item(user_id, fish['key'], ItemType.FISH)
                        except Exception as e:
                            logger.info(f"[FISHING] [ERROR] Failed to add rare fish {fish['key']} for {username}: {e}")
                            continue  # Skip achievement tracking if add failed
            
                        # Check boss_hunter achievement
                        if fish['key'] in ['megalodon', 'thuy_quai_kraken', 'leviathan']:
                            await increment_stat(user_id, "fishing", "boss_caught", 1)
                            current_boss = await get_stat(user_id, "fishing", "boss_caught")
                            await cog.bot.achievement_manager.check_unlock(
                                user_id=user_id,
                                game_category="fishing",
                                stat_key="boss_caught",
                                current_value=current_boss,
                                channel=channel
                            )
            
                        # Track in collection
                        is_new_collection = await track_caught_fish(user_id, fish['key'])
                        if is_new_collection:
                            new_caught_fishes.add(fish['key'])
                            logger.info(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                            # Check first_catch achievement (catch any fish for the first time)
                            # Get current collection count BEFORE adding this fish
                            collection = await get_collection(user_id)
                            was_empty = len(collection) <= 1  # Check if this was the first fish (size 1 after add)
                            if was_empty:  # This is the first fish ever caught
                                await increment_stat(user_id, "fishing", "first_catch", 1)
                                await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "first_catch", 1, channel)
                            # Check if collection is complete
                            is_collection_complete = await check_collection_complete(user_id)
                            if is_collection_complete:
                                await cog.bot.achievement_manager.check_unlock(
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
                                await cog.add_inventory_item(user_id, fish['key'], ItemType.FISH)
                                fish_only_items[fish['key']] += 1  # Add to display count
                                logger.info(f"[FISHING] [PASSIVE] 🌌 Void Rod double catch triggered for {username} - RARE {fish['key']}")
                                # Store for special message display later
                                if not hasattr(cog, '_void_rod_double_catch'):
                                    cog._void_rod_double_catch = {}
                                cog._void_rod_double_catch[user_id] = fish
                    elif catch_type == ItemType.COMMON:
                        # Catch common fish (or fallback if rare limit reached)
                        if not COMMON_FISH:
                            logger.error("[FISHING] COMMON_FISH is empty! Cannot catch fish.")
                            continue

                        fish = random.choice(COMMON_FISH)
                        logger.info(f"[FISHING] {username} caught common fish: {fish['key']}")
                        try:
                            await cog.add_inventory_item(user_id, fish['key'], ItemType.FISH)
                        except Exception as e:
                            logger.info(f"[FISHING] [ERROR] Failed to add common fish {fish['key']} for {username}: {e}")
                            continue  # Skip achievement tracking if add failed
                        # Track in collection
                        is_new_collection = await track_caught_fish(user_id, fish['key'])
                        if is_new_collection:
                            new_caught_fishes.add(fish['key'])
                            logger.info(f"[COLLECTION] {username} unlocked new fish: {fish['key']}")
                            # Check first_catch achievement (catch any fish for the first time)
                            # Get current collection count BEFORE adding this fish
                            collection = await get_collection(user_id)
                            was_empty = len(collection) == 0  # Check if collection was empty before this catch
                            if was_empty:  # This is the first fish ever caught
                                await increment_stat(user_id, "fishing", "first_catch", 1)
                                await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "first_catch", 1, channel)
                            # Check if collection is complete
                            is_collection_complete = await check_collection_complete(user_id)
                            if is_collection_complete:
                                await cog.bot.achievement_manager.check_unlock(
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
                                await cog.add_inventory_item(user_id, fish['key'], ItemType.FISH)
                                fish_only_items[fish['key']] += 1  # Add to display count
                                logger.info(f"[FISHING] [PASSIVE] 🌌 Void Rod double catch triggered for {username} - {fish['key']}")
                                # Store for special message display later
                                if not hasattr(cog, '_void_rod_double_catch'):
                                    cog._void_rod_double_catch = {}
                                cog._void_rod_double_catch[user_id] = fish
    
                # Decrease legendary buff counter
                if await cog.check_emotional_state(user_id, "legendary_buff"):
                    remaining = await cog.emotional_state_manager.decrement_counter(user_id, "legendary_buff")
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
                        await cog.bot.inventory.modify(user_id, fish_key, new_qty - qty)
                        logger.info(f"[EVENT] {username} activated duplicate_multiplier x{duplicate_multiplier}: {fish_key} {qty} → {new_qty}")
                    fish_only_items = duplicated_items
    
                # Display fish grouped
                tournament_score = 0 # Track score for active tournaments
                for key, qty in fish_only_items.items():
                    fish = ALL_FISH[key]
                    emoji = fish['emoji']
                    total_price = fish['sell_price'] * qty  # Multiply price by quantity
                    fish_name = cog.apply_display_glitch(fish['name'])
                    fish_display.append(f"{emoji} {fish_name} x{qty} ({total_price} Hạt)")
                    
                    # HOOK: Tournament Score (Base Sell Price * Qty)
                    # We use Base Price to ensure fairness (ignore market multipliers)
                    tournament_score += fish['sell_price'] * qty
    
                # Process trash (independent)
                if trash_count > 0:
                    # CHECK VIP TIER 3 FOR AUTO-RECYCLE
                    # This avoids filling inventory with trash
                    from core.services.vip_service import VIPEngine
                    from cogs.aquarium.logic.market import MarketEngine
                    vip_data = await VIPEngine.get_vip_data(user_id)
                    vip_tier = vip_data['tier'] if vip_data else 0
                    
                    if vip_tier >= 3:
                        recycle_reward = trash_count * 1
                        success = await MarketEngine.add_leaf_coins(user_id, recycle_reward, reason="vip_auto_recycle_trash")
                        
                        if success:
                            logger.info(f"[FISHING] [VIP] {username} (Tier {vip_tier}) auto-recycled {trash_count} trash -> {recycle_reward} Leaf Coin")
                            fish_display.append(f"♻️ **Đã tự động tái chế {trash_count} Rác** (+{recycle_reward} 🍃)")
                            
                            try:
                                await increment_stat(user_id, "fishing", "trash_recycled", trash_count)
                                current_trash = await get_stat(user_id, "fishing", "trash_recycled")
                                await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "trash_recycled", current_trash, channel)
                            except Exception as e:
                                logger.error(f"[ACHIEVEMENT] Error tracking trash_recycled for {user_id}: {e}")
                        else:
                            logger.error(f"[FISHING] [VIP] Failed to add leaf coins for {username} - falling back to trash")
                            for _ in range(trash_count):
                                trash = random.choice(TRASH_ITEMS)
                                item_key = trash.get("key", f"trash_{trash['name'].lower().replace(' ', '_')}")
                                await cog.add_inventory_item(user_id, item_key, ItemType.TRASH)
                        
                    else:
                        # Standard Trash Logic
                        for _ in range(trash_count):
                            trash = random.choice(TRASH_ITEMS)
                            item_key = trash.get("key", f"trash_{trash['name'].lower().replace(' ', '_')}")
                            await cog.add_inventory_item(user_id, item_key, ItemType.TRASH)
                        
                            # Populate main trash_items dict for central embed generation
                            if item_key not in trash_items:
                                trash_items[item_key] = 0
                            trash_items[item_key] += 1
            
                        # Track trash caught for achievement (Legacy seed method removed or kept?)
                        # Kept as per original code
                        try:
                            await add_seeds(user_id, trash_count, 'recycle_trash', 'fishing')
                            # Track achievement: trash_master
                            try:
                                await increment_stat(user_id, "fishing", "trash_recycled", trash_count)
                                current_trash = await get_stat(user_id, "fishing", "trash_recycled")
                                await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "trash_recycled", current_trash, channel)
                            except Exception as e:
                                logger.error(f"[ACHIEVEMENT] Error tracking trash_recycled for {user_id}: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error: {e}")
                        logger.info(f"[FISHING] {username} caught trash (independent): {trash_count}")
    
                # HOOK: Update Tournament Score if applicable
                if tournament_score > 0:
                    try:
                        # Pass 'conn' to ensure ACID compliance within this transaction
                        await TournamentManager.get_instance().on_fish_catch(user_id, tournament_score, conn=conn)
                    except Exception as e:
                        logger.error(f"[TOURNAMENT] Error updating score for {username}: {e}")

                # Process chest (độc lập)
                if chest_count > 0:
                    for _ in range(chest_count):
                        await cog.add_inventory_item(user_id, ItemKeys.RUONG_KHO_BAU, "tool")
                    fish_display.append(f"🎁 Rương Kho Báu x{chest_count}")
                    logger.info(f"[FISHING] {username} caught {chest_count}x TREASURE CHEST! 🎁")
                    # Track chests caught for achievement
                    try:
                        await increment_stat(user_id, "fishing", "chests_caught", chest_count)
                        current_chests = await get_stat(user_id, "fishing", "chests_caught")
                        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "chests_caught", current_chests, channel)
                    except Exception as e:
                        logger.error(f"[ACHIEVEMENT] Error updating chests_caught for {user_id}: {e}")
    
                # Store only fish for the sell button
                cog.caught_items[user_id] = fish_only_items
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
                        await cog.bot.inventory.modify(user_id, most_valuable_fish, -1)
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
                                fish_name = cog.apply_display_glitch(cog.get_fish_display_name(fish['key'], fish['name']))
                                fish_display.append(f"{fish['emoji']} {fish_name} x{qty} ({total_price} Hạt)")
            
                        logger.info(f"[EVENT] {username} lost {fish_info['name']} to cat_steal")
                        # Track robbed count (cat steal counts as being robbed)
                        try:
                            await increment_stat(user_id, "fishing", "robbed_count", 1)  # stat update,
                            current_robbed = await get_stat(user_id, "fishing", "robbed_count")
                            await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "robbed_count", current_robbed, channel)
                        except Exception as e:
                            logger.error(f"[ACHIEVEMENT] Error updating robbed_count for {user_id}: {e}")
                        if fish_display:
                            fish_display[0] = fish_display[0] + f"\n(🐈 Mèo cướp mất {fish_info['name']} giá {highest_price} Hạt!)"
    
                # Update caught items for sell button
                cog.caught_items[user_id] = {k: v for k, v in fish_only_items.items() if k != ItemKeys.CA_ISEKAI}
        
                # Check if bucket is full after fishing, if so, sell all fish instead of just caught
                updated_inventory = await cog.bot.inventory.get_all(user_id)
                current_fish_count = sum(v for k, v in updated_inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS and k != ItemKeys.CA_ISEKAI)
                if current_fish_count >= FISH_BUCKET_LIMIT:
                    all_fish_items = {k: v for k, v in updated_inventory.items() if k in COMMON_FISH_KEYS + RARE_FISH_KEYS + LEGENDARY_FISH_KEYS}
                    # Exclude ca_isekai from sellable items
                    all_fish_items = {k: v for k, v in all_fish_items.items() if k != ItemKeys.CA_ISEKAI}
                    cog.caught_items[user_id] = all_fish_items
                    sell_items = all_fish_items
                    logger.info(f"[FISHING] Bucket full ({current_fish_count}/{FISH_BUCKET_LIMIT}), sell button will sell all fish")
                else:
                    # Exclude ca_isekai from sellable items
                    sell_items = {k: v for k, v in fish_only_items.items() if k != ItemKeys.CA_ISEKAI}
    
                # ==================== EVENT FISH BONUS CATCH ====================
                event_fish_result = None
                try:
                    event_fish_result = await try_catch_event_fish(cog.bot, user_id, guild_id)
                    if event_fish_result:
                        logger.info(f"[EVENT_FISH] {username} caught event fish: {event_fish_result.fish.name}")
                except Exception as e:
                    logger.error(f"[EVENT_FISH] Hook failed: {e}")

                # ==================== CHECK FOR LEGENDARY FISH ====================
                current_hour = datetime.now().hour
                legendary_fish = await check_legendary_spawn_conditions(user_id, channel.guild.id, current_hour, cog=cog)
                legendary_failed = False  # Track if legendary boss fight failed

                # Check for Phoenix spawn RNG failure
                if isinstance(legendary_fish, dict) and "spawn_failed" in legendary_fish:
                    from ..mechanics.legendary_quest_helper import consume_phoenix_buff
                
                    legendary_key = legendary_fish["spawn_failed"]
                    energy = legendary_fish["energy"]
                    roll = legendary_fish["roll"]
                
                    # Consume buff (used up)
                    await consume_phoenix_buff(user_id)
                
                    # Public fail message
                    username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
                    fail_embed = discord.Embed(
                        title=f"💔 {username} - NGỌN LỬA ĐÃ TẮT!",
                        description=f"Bạn cố triệu hồi **Cá Phượng Hoàng** với **{energy}%** năng lượng...\n\n"
                                    f"🎲 Phép thuật thất bại! (Cần ≤{energy}, rolled **{roll}**)\n\n"
                                    f"🔥 Lông Vũ Lửa đã cháy kiệt. Hãy thử lại!",
                        color=discord.Color.dark_red()
                    )
                    await channel.send(embed=fail_embed)
                
                    logger.info(f"[PHOENIX] {username} spawn FAILED: {energy}% chance, rolled {roll}")
                
                    # Clear legendary_fish to continue normal fishing
                    legendary_fish = None
            
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
                                   f"**{legendary_fish['emoji']} {cog.apply_display_glitch(legendary_fish['name'])}**\n"
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
                    boss_view = LegendaryBossFightView(cog, user_id, legendary_fish, rod_durability, rod_lvl, channel, guild_id, user)
        
                    # Send boss fight message
                    boss_msg = await channel.send(f"<@{user_id}>", embed=legendary_embed, view=boss_view)
        
                    # Wait for interaction or timeout
                    try:
                    
                        # PERFORMANCE FIX: Progress updates instead of silent 60s wait
                        # Improves UX by showing battle is in progress
                        for i in range(12):  # 12 × 5s = 60s total
                            await asyncio.sleep(5)
                        
                            # Send progress update every 15 seconds (every 3 iterations)
                            if i % 3 == 0 and i > 0:  # Skip first iteration (0)
                                remaining = 60 - (i * 5)
                                progress_msg = f"⚔️ **Trận chiến với {legendary_fish['name']} đang diễn ra...**\\n⏱️ Còn {remaining}s"
                                try:
                                    await channel.send(progress_msg)
                                    logger.debug(f"[LEGENDARY] Battle progress: {60 - remaining}s/{60}s")
                                except Exception as e:
                                    logger.warning(f"[LEGENDARY] Could not send progress update: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error in legendary battle progress: {e}")
        
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
                        await cog.bot.inventory.modify(user_id, "long_vu_lua", 1)
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
                    current_title = await cog.get_title(user_id, channel.guild.id)
                    if not current_title or "Vua" not in current_title:
                        # Award "Vua Câu Cá" role
                        try:
                            guild = channel.guild
                            member = guild.get_member(user_id)
                            role_id = await get_server_config(guild.id, "role_vua_cau_ca")
                            if not role_id:
                                return
                            role = guild.get_role(int(role_id))
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
                title = cog.apply_display_glitch(title)
            
                # Consistent blue theme (fishing aesthetic)
                embed_color = discord.Color.red() if is_broken_rod else (discord.Color.gold() if title_earned else discord.Color.blue())
            
                # ==================== RESULT CONTENT PREPARATION ====================
                
                # 1. ROD INFO STRING
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

                # 2. CAUGHT ITEMS STRING
                items_value = ""
            
                # Group fish
                if fish_only_items:
                    for key, qty in fish_only_items.items():
                        fish = ALL_FISH[key]
                        fish_name = cog.apply_display_glitch(fish['name'])
                        fish_emoji = fish.get('emoji', '🐟')
                    
                        new_tag = " ✨🆕" if key in new_caught_fishes else ""
                        items_value += f"{fish_emoji} **{fish_name}** x{qty}{new_tag}\n"
            
                # Group chests
                if chest_count > 0:
                    items_value += f"🎁 **Rương Kho Báu** x{chest_count}\n"
            
                # Group trash
                if trash_items:
                    for trash_key, qty in trash_items.items():
                        # Try getting from ALL_ITEMS_DATA first
                        trash_info = ALL_ITEMS_DATA.get(trash_key)
                    
                        # If not found, try searching TRASH_ITEMS list
                        if not trash_info:
                            trash_info = next((t for t in TRASH_ITEMS if t.get("key") == trash_key), {})
                    
                        # Fallback to key formatting if still no name
                        trash_name = trash_info.get("name", trash_key.replace("trash_", "").replace("_", " ").title())
                        trash_name = cog.apply_display_glitch(trash_name)
                        items_value += f"🗑️ **{trash_name}** x{qty}\n"
                elif trash_count > 0: # Fallback
                     trash_name = cog.apply_display_glitch("Rác")
                     items_value += f"🗑️ **{trash_name}** x{trash_count}\n"

                # Event fish bonus (from seasonal events)
                if event_fish_result:
                    fish_info = event_fish_result.fish
                    new_tag = " ✨🆕" if event_fish_result.is_new_collection else ""
                    items_value += f"\n🎊 **SỰ KIỆN:** {fish_info.emoji} **{fish_info.name}** x1{new_tag}\n"

                # If nothing caught
                if not items_value:
                    items_value = "_(Không có gì)_"
            
                # Add separator and total
                items_value += f"\n{'─' * 15}\n"
                items_value += f"📊 **Tổng:** {total_catches} vật"

                # ==================== EMBED CREATION (VIP / STANDARD) ====================
                # Import VIP Engine
                from core.services.vip_service import VIPEngine
                
                # Get User Object (for avatar/id)
                user_obj = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
                
                # Check VIP
                vip_data = await VIPEngine.get_vip_data(user_id)
                
                # Generate Title
                title = f"🎣 {username} - Kết Quả Câu Cá"
                if title_earned:
                    title = f"👑 {username} - VUA CÂU CÁ! 👑"
                title = cog.apply_display_glitch(title)

                if vip_data:
                    # --- VIP STYLE ---
                    # Use Factory for base (title, color, footer)
                    # Empty description, use fields for content (same layout as standard)
                    embed = await VIPEngine.create_vip_embed(user_obj, title, "", vip_data)
                    
                    # Field 1: Rod Info (Top)
                    embed.add_field(
                        name="🎣 Cần Câu",
                        value=cog.apply_display_glitch(rod_field_value),
                        inline=False
                    )
                    
                    # Field 2: Caught Items (Bottom)
                    embed.add_field(
                        name="🐟 Đã Câu Được",
                        value=items_value,
                        inline=False
                    )
                else:
                    # --- STANDARD STYLE ---
                    # Standard Colors
                    embed_color = discord.Color.red() if is_broken_rod else (discord.Color.gold() if title_earned else discord.Color.blue())
                    
                    embed = discord.Embed(
                        title=title,
                        color=embed_color
                    )
                    
                    # Field 1: Rod Info (Top)
                    embed.add_field(
                        name="🎣 Cần Câu",
                        value=cog.apply_display_glitch(rod_field_value),
                        inline=False
                    )
                    
                    # Field 2: Caught Items
                    embed.add_field(
                        name="🐟 Đã Câu Được",
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
                        value=cog.apply_display_glitch(completion_text),
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
                        value=cog.apply_display_glitch(warning_text),
                        inline=False
                    )
    
                # *** UPDATE DURABILITY AFTER FISHING ***
                old_durability = rod_durability
                new_durability = max(0, rod_durability - durability_loss)
                try:
                    await cog.update_rod_data(user_id, new_durability)
                    rod_durability = new_durability  # Update local variable only if successful
                    logger.info(f"[FISHING] [DURABILITY_UPDATE] {username} (user_id={user_id}) durability {old_durability} → {rod_durability} (loss: {durability_loss})")
                except Exception as e:
                    logger.info(f"[FISHING] [DURABILITY_ERROR] Failed to update durability for {username}: {e}")
                    # Don't update local variable, keep old value for display
        
                # *** APPLY GLITCH TO FOOTER ***
                # The durability_status variable is no longer used directly in the footer,
                # as the rod info is now in a dedicated field.
                # IMPORTANT: Don't overwrite VIP footer (which has random quotes)
                if not vip_data:
                    footer_text = f"Tổng câu được: {total_catches} vật{boost_text}"
                    footer_text = cog.apply_display_glitch(footer_text)
                    embed.set_footer(text=footer_text)
    
                # Create view with sell button if there are fish to sell
                view = None
                # Sell button removed for UX cleanup
                if sell_items:
                    logger.info(f"[FISHING] Sell button suppressed (UX Cleanup) for {username} with {len(sell_items)} fish types")
                else:
                    logger.info(f"[FISHING] No fish to sell")

    
                # Track total fish caught for achievement
                if num_fish > 0:
                    try:
                        await increment_stat(user_id, "fishing", "total_fish_caught", num_fish)
                        current_total = await get_stat(user_id, "fishing", "total_fish_caught")
                        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "total_fish_caught", current_total, channel)
                        from ..mechanics.events import check_conditional_unlocks
                        await check_conditional_unlocks(user_id, "total_fish_caught", current_total, channel)
                    except Exception as e:
                        logger.error(f"[ACHIEVEMENT] Error updating total_fish_caught for {user_id}: {e}")
                    
                    try:
                        from cogs.quest.services.quest_service import QuestService
                        from cogs.quest.core.quest_types import QuestType
                        result = await QuestService.add_contribution(guild_id, user_id, QuestType.FISH_TOTAL, num_fish)
                        logger.info(f"[QUEST] Fish contribution: guild={guild_id}, user={user_id}, fish={num_fish}, result={result}")
                    except Exception as e:
                        logger.error(f"[QUEST] Error adding fish contribution for {user_id}: {e}")
    


                await casting_msg.edit(content="", embed=embed, view=view)
                logger.info(f"[FISHING] [RESULT_POST] {username} (user_id={user_id}) action=display_result")

                # ==================== NPC ENCOUNTER (PREPARE DATA ONLY) ====================
                # CRITICAL: Prepare NPC data inside lock but SEND outside to avoid deadlock
                npc_data_to_send = None
                npc_triggered = False
                npc_type = None
                
                # Check forced pending trigger
                if hasattr(cog, "pending_npc_event") and user_id in cog.pending_npc_event:
                    npc_type = cog.pending_npc_event.pop(user_id)
                    npc_triggered = True
                    logger.info(f"[NPC] Triggering pending NPC event: {npc_type} for user {user_id}")
            
                # Check random trigger (Chance 6%)
                elif random.random() < NPC_ENCOUNTER_CHANCE and num_fish > 0:
                     npc_triggered = True
    
                if npc_triggered:
                    # If npc_type is NOT set (i.e. Random Trigger), roll for it now
                    if not npc_type:
                        await asyncio.sleep(NPC_ENCOUNTER_DELAY)
            
                        # Select random NPC based on weighted chances
                        npc_pool = []
                        for npc_key, npc_data_config in NPC_ENCOUNTERS.items():
                            npc_pool.extend([npc_key] * int(npc_data_config.get("chance", 0.1) * 100))
                    
                        if not npc_pool:
                             npc_pool = list(NPC_ENCOUNTERS.keys())

                        npc_type = random.choice(npc_pool)
            
                    # Use Adaptive Data based on Affinity
                    npc_data = await cog._get_adaptive_npc_data(user_id, npc_type)

                    # Get caught fish context
                    # We need the key and info of the fish on hook
                    # fish_only_items is {fish_key: count}
                    caught_fish_key = list(fish_only_items.keys())[0] if fish_only_items else list(ALL_FISH.keys())[0]
                    # Fallback if no fish caught but NPC triggered (rare edge case?)
                    # Usually "num_fish > 0" condition prevents this.
                    # But ensuring no crash.
                
                    if caught_fish_key in ALL_FISH:
                        caught_fish_info = ALL_FISH[caught_fish_key]
                    else:
                        caught_fish_info = {"name": "Cá", "emoji": "🐟", "sell_price": 0}
                    
                    caught_fish_ctx = {caught_fish_key: caught_fish_info}

                    # Track stats (inside lock is OK - just DB writes)
                    await increment_stat(user_id, "fishing", "npc_events_triggered", 1)
                    await increment_stat(user_id, "fishing", f"{npc_type}_encounter", 1)
                    
                    # STORE data to send AFTER lock release
                    npc_data_to_send = {
                        "npc_type": npc_type,
                        "npc_data": npc_data,
                        "caught_fish_ctx": caught_fish_ctx,
                        "caught_fish_info": caught_fish_info,
                        "username": username,
                        "user_id": user_id,
                        "channel": channel
                    }
                    logger.info(f"[NPC] Prepared NPC data for {npc_type}, will send after lock release")
    
                # ==================== FINAL COOLDOWN CHECK ====================
                # If global_reset was triggered, ensure user has no cooldown
                if triggers_global_reset:
                    # Clear the user's cooldown that was set earlier
                    if user_id in cog.fishing_cooldown:
                        del cog.fishing_cooldown[user_id]
                    logger.info(f"[FISHING] [GLOBAL_RESET] {username} cooldown cleared due to global reset event")
        
                    # Performance monitoring
                    duration = time.time() - start_time
                    logger.info(f"[FISHING] [PERF] Cast completed in {duration:.2f}s for {username}")
            
            except Exception as inner_ex:
                # CRITICAL: Catch ANY exception inside lock to prevent deadlock
                logger.error(
                    f"[FISHING] [CRITICAL] Exception inside lock for {user_id}: {inner_ex}",
                    exc_info=True
                )
                # Re-raise to be handled by outer except
                raise
            finally:
                logger.info(f"[FISHING] [DEBUG] Lock released for {user_id}")
        
        # ==================== SEND NPC VIEW (OUTSIDE LOCK) ====================
        # CRITICAL: NPC View sent AFTER lock release to prevent deadlock
        if 'npc_data_to_send' in locals() and npc_data_to_send:
            try:
                npc_type = npc_data_to_send["npc_type"]
                npc_data = npc_data_to_send["npc_data"]
                caught_fish_ctx = npc_data_to_send["caught_fish_ctx"]
                caught_fish_info = npc_data_to_send["caught_fish_info"]
                username = npc_data_to_send["username"]
                user_id = npc_data_to_send["user_id"]
                channel = npc_data_to_send["channel"]
                
                # Build NPC embed
                npc_title = f"⚠️ {npc_data['name']} - {username}!"
                npc_desc = f"{npc_data['description']}\n\n**{username}**, {npc_data['question']}"
                npc_embed = discord.Embed(
                    title=cog.apply_display_glitch(npc_title),
                    description=cog.apply_display_glitch(npc_desc),
                    color=discord.Color.gold()
                )

                if npc_data.get("image_url"):
                    npc_embed.set_image(url=npc_data["image_url"])

                # Add cost information
                cost_text = ""
                cost_val = npc_data.get("cost")
                if cost_val == "fish":
                    cost_text = f"💰 **Chi phí:** {caught_fish_info['emoji']} {caught_fish_info['name']}"
                elif isinstance(cost_val, int):
                    cost_text = f"💰 **Chi phí:** {cost_val} Hạt"
                elif cost_val == "cooldown_5min":
                    cost_text = f"💰 **Chi phí:** Mất lượt câu trong 5 phút"

                if cost_text:
                    npc_embed.add_field(name="💸 Yêu Cầu", value=cog.apply_display_glitch(cost_text), inline=False)

                # Create and send NPC View
                npc_view = InteractiveNPCView(
                    cog, 
                    user_id, 
                    npc_type, 
                    npc_data, 
                    caught_fish_ctx, 
                    channel
                )

                # CRITICAL FIX: Skip NPC if user is selling to prevent race condition
                if user_id in cog.sell_processing:
                    logger.info(f"[NPC] Skipped NPC {npc_type} for user {user_id} (currently selling)")
                    return

                npc_msg = await channel.send(content=f"<@{user_id}> 🔥 **SỰ KIỆN NPC!**", embed=npc_embed, view=npc_view)
                npc_view.message = npc_msg
                logger.info(f"[NPC] Sent NPC View for {npc_type} to user {user_id} (OUTSIDE lock)")
                
            except Exception as npc_error:
                logger.error(f"[NPC] Error sending NPC View: {npc_error}", exc_info=True)
    
    except asyncio.TimeoutError as e:
        total_time = time.time() - start_time
        # Track timeout for monitoring
        from core.timeout_monitor import record_timeout
        record_timeout(
            context="fishing.channel.send",
            user_id=user_id,
            command="cauca",
            duration=total_time
        )
        logger.error(f"[FISHING] [TIMEOUT] Discord send timeout after {total_time:.2f}s for user {user_id}", exc_info=True)
        # Try to notify user if possible
        try:
            if is_slash and not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message("❌ Mạng yếu! Thử lại sau.", ephemeral=True)
            elif is_slash:
                await ctx_or_interaction.followup.send("❌ Mạng yếu! Thử lại sau.", ephemeral=True)
            else:
                await ctx_or_interaction.reply("❌ Mạng yếu! Thử lại sau.")
        except Exception:
            pass  # Can't notify, just log
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[FISHING] [ERROR] [PERF] Unexpected error in _fish_action after {total_time:.2f}s: {e}", exc_info=True)
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


"""Helper utility functions for fishing system.

Extracted from fishing/cog.py to improve maintainability.
"""
import logging
import time
from typing import Optional, Dict, Any, Union
import discord

from database_manager import db_manager, get_server_config
from configs.item_constants import ItemKeys
from ..mechanics.rod_system import ROD_LEVELS
from ..mechanics.glitch import apply_glitch_lite, apply_glitch_moderate, apply_glitch_aggressive, DISPLAY_GLITCH_ACTIVE

logger = logging.getLogger("fishing")


# ==================== RESPONSE HELPERS ====================

def get_user_info(ctx_or_interaction, is_slash: bool) -> tuple[int, str]:
    """Get user ID and name from context or interaction.
    
    Args:
        ctx_or_interaction: Command context or interaction
        is_slash: Whether this is a slash command
        
    Returns:
        tuple: (user_id, username)
    """
    if is_slash:
        return ctx_or_interaction.user.id, ctx_or_interaction.user.name
    else:
        return ctx_or_interaction.author.id, ctx_or_interaction.author.name


async def send_response(ctx_or_interaction, content: str = None, 
                        embed: discord.Embed = None, is_slash: bool = True,
                        ephemeral: bool = False, view: discord.ui.View = None):
    """Send a response that works for both slash and prefix commands.
    
    Args:
        ctx_or_interaction: Command context or interaction
        content: Text content to send
        embed: Embed to send
        is_slash: Whether this is a slash command
        ephemeral: Whether message should be ephemeral (slash only)
        view: View to attach to message
    """
    kwargs = {}
    if content:
        kwargs["content"] = content
    if embed:
        kwargs["embed"] = embed
    if view:
        kwargs["view"] = view
        
    if is_slash:
        kwargs["ephemeral"] = ephemeral
        await ctx_or_interaction.response.send_message(**kwargs)
    else:
        await ctx_or_interaction.reply(**kwargs)


async def send_followup(ctx_or_interaction, content: str = None,
                        embed: discord.Embed = None, is_slash: bool = True,
                        ephemeral: bool = False, view: discord.ui.View = None):
    """Send a followup message (after defer) for both slash and prefix commands.
    
    Args:
        ctx_or_interaction: Command context or interaction
        content: Text content to send
        embed: Embed to send
        is_slash: Whether this is a slash command
        ephemeral: Whether message should be ephemeral (slash only)
        view: View to attach to message
    """
    kwargs = {}
    if content:
        kwargs["content"] = content
    if embed:
        kwargs["embed"] = embed
    if view:
        kwargs["view"] = view
        
    if is_slash:
        kwargs["ephemeral"] = ephemeral
        await ctx_or_interaction.followup.send(**kwargs)
    else:
        await ctx_or_interaction.reply(**kwargs)


# ==================== EMBED BUILDERS ====================

def create_fishing_embed(title: str, description: str = None, 
                         color_type: str = "info", 
                         thumbnail_url: str = None) -> discord.Embed:
    """Create a standardized fishing embed.
    
    Args:
        title: Embed title
        description: Embed description
        color_type: Color type (info, success, error, warning, gold, purple, blue)
        thumbnail_url: Optional thumbnail URL
        
    Returns:
        discord.Embed: Configured embed
    """
    colors = {
        "info": discord.Color.blue(),
        "success": discord.Color.green(),
        "error": discord.Color.red(),
        "warning": discord.Color.orange(),
        "gold": discord.Color.gold(),
        "purple": discord.Color.purple(),
        "dark_blue": discord.Color.dark_blue(),
        "dark_purple": discord.Color.dark_purple(),
        "greyple": discord.Color.greyple()
    }
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=colors.get(color_type, discord.Color.blue())
    )
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    return embed


def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed with red color.
    
    Args:
        title: Error title
        description: Error description
        
    Returns:
        discord.Embed: Configured error embed
    """
    return create_fishing_embed(title, description, "error")


def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed with green color.
    
    Args:
        title: Success title
        description: Success description
        
    Returns:
        discord.Embed: Configured success embed
    """
    return create_fishing_embed(title, description, "success")


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
    """
    Trigger a server-wide disaster event.
    Returns: {triggered: bool, disaster: dict or None}
    """
    current_time = time.time()
    
    if user_id in self.pending_disaster:
        disaster_key = self.pending_disaster.pop(user_id)
        from core.data_cache import data_cache
        try:
            data = data_cache.get_disaster_events()
            if not data:
                import json
                from .constants import DISASTER_EVENTS_PATH
                with open(DISASTER_EVENTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            disasters_by_key = {d["key"]: d for d in data.get("disasters", [])}
            if disaster_key in disasters_by_key:
                disaster = disasters_by_key[disaster_key]
            else:
                logger.info(f"[DISASTER] Pending disaster key {disaster_key} not found, skipping")
                return {"triggered": False, "reason": "pending_disaster_key_invalid"}
        except Exception as e:
            logger.error(f"[DISASTER] Error loading pending disaster: {e}")
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
        logger.info(f"[DISASTER] Failed to set global glitch state: {e}")
    
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
        logger.info(f"[DISASTER] {disaster['key']} triggered by {username}. Duration: {disaster_duration}s")
        
        # Track achievement stats for disaster trigger
        from .constants import DISASTER_STAT_MAPPING
        if disaster['key'] in DISASTER_STAT_MAPPING:
            stat_key = DISASTER_STAT_MAPPING[disaster['key']]
            try:
                await increment_stat(user_id, "fishing", stat_key, 1)
                current_value = await get_stat(user_id, "fishing", stat_key)
                await self.bot.achievement_manager.check_unlock(user_id, "fishing", stat_key, current_value, channel)
                logger.info(f"[ACHIEVEMENT] Tracked {stat_key} for user {user_id} on disaster {disaster['key']}")
            except Exception as e:
                logger.error(f"[ACHIEVEMENT] Error tracking {stat_key} for {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"[DISASTER] Error sending announcement: {e}")
    
    # Apply specific effects based on disaster type
    if disaster["effects"].get("freeze_server"):
        # Server is frozen, no additional action needed (is_server_frozen already set)
        pass
    
    if disaster["effects"].get("fine_applies_to") == "all_online":
        # Apply fine to all online users
        fine_amount = disaster["effects"].get("fine_amount", 0)
        if fine_amount > 0:
            # This will be applied when users try to fish
            logger.info(f"[DISASTER] Fine of {fine_amount} seeds will be applied to all online users")
    
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

async def add_inventory_item(self, user_id: int, item_id: str, item_type: str):
    """Add item to inventory."""
    # [CACHE] Use bot.inventory.modify
    await self.bot.inventory.modify(user_id, item_id, 1)
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
                role_id = await get_server_config(guild_id, "role_vua_cau_ca")
                role = guild.get_role(int(role_id)) if role_id else None
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
        # [CACHE] Use bot.inventory.modify
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
        
        await add_seeds(user_id, -cost, reason='npc_payment', category='fishing')
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
        # [CACHE] Use bot.inventory.modify
        await self.bot.inventory.modify(user_id, ItemKeys.MOI, amount)
        result_text = selected_reward["message"]
        logger.info(f"[NPC] User {user_id} received {amount} worms from {npc_type}")
    
    elif reward_type == "lucky_buff":
        # Use centralized persistent manager
        await self.emotional_state_manager.apply_emotional_state(user_id, "lucky_buff", 1)
        result_text = selected_reward["message"]
        logger.info(f"[NPC] User {user_id} received lucky buff from {npc_type}")
    
    elif reward_type == "chest":
        amount = selected_reward.get("amount", 1)
        # [CACHE] Use bot.inventory.modify
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
        await add_seeds(user_id, amount, reason='npc_reward_money', category='fishing')
        result_text = selected_reward["message"]
        # Add amount to message if not already included
        if "{amount}" in result_text:
            result_text = result_text.replace("{amount}", f"**{amount} Hạt**")
        elif "Hạt" not in result_text:
            result_text += f" (**+{amount} Hạt**)"
        logger.info(f"[NPC] User {user_id} received {amount} seeds from {npc_type}")
    
    elif reward_type == "ngoc_trai":
        amount = selected_reward.get("amount", 1)
        # [CACHE] Use bot.inventory.modify
        await self.bot.inventory.modify(user_id, "ngoc_trai", amount)
        result_text = selected_reward["message"]
        logger.info(f"[NPC] User {user_id} received {amount} ngoc_trai(s) from {npc_type}")
    
    elif reward_type == "vat_lieu_nang_cap":
        amount = selected_reward.get("amount", 2)
        # [CACHE] Use bot.inventory.modify
        await self.bot.inventory.modify(user_id, "vat_lieu_nang_cap", amount)
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
        price = (fish_info.get('price', {}).get('sell') or fish_info.get('sell_price', 0)) * 3
        await add_seeds(user_id, price, reason='npc_reward_triple_money', category='fishing')
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
        # Use centralized persistent manager
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





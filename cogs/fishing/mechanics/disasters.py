"""Disaster mechanics for fishing system.

Handles global server-wide disaster events.
"""
import logging
import random
import time
import discord

from database_manager import increment_stat, get_stat
from .glitch import set_glitch_state
from ..constants import DISASTER_EVENTS, DISASTER_STAT_MAPPING

logger = logging.getLogger("fishing")


async def trigger_global_disaster(cog, user_id: int, username: str, channel) -> dict:
    """Trigger a server-wide disaster event.
    
    Args:
        cog: The FishingCog instance
        user_id: User who triggered the disaster
        username: User's display name
        channel: Discord channel for announcements
        
    Returns:
        dict: {triggered: bool, disaster: dict or None, reason: str}
    """
    current_time = time.time()
    
    # CHECK FOR FORCED PENDING DISASTER FIRST
    if user_id in cog.pending_disaster:
        disaster_key = cog.pending_disaster.pop(user_id)
        # Load disaster data
        # Use cached data from constants instead of re-reading file
        from ..constants import DISASTER_EVENTS
        
        # Convert list to dict for fast lookup (could be optimized to global var if needed)
        disasters_by_key = {d["key"]: d for d in DISASTER_EVENTS}
        
        if disaster_key in disasters_by_key:
            disaster = disasters_by_key[disaster_key]
        else:
            logger.info(f"[DISASTER] Pending disaster key {disaster_key} not found in cached config, skipping")
            return {"triggered": False, "reason": "pending_disaster_key_invalid"}
    else:
        # Check if server is in global cooldown period
        if current_time - cog.last_disaster_time < cog.global_disaster_cooldown:
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
        cog.is_server_frozen = True
        cog.freeze_end_time = current_time + effects.get("freeze_duration", disaster_duration)
    else:
        cog.is_server_frozen = False
        cog.freeze_end_time = 0
    
    cog.last_disaster_time = current_time + disaster_duration
    cog.current_disaster = disaster
    cog.disaster_culprit = username
    cog.disaster_effect_end_time = current_time + disaster_duration
    cog.disaster_channel = channel  # Store channel for end notification
    
    cog.disaster_catch_rate_penalty = effects.get("catch_rate_penalty", 0.0)
    cog.disaster_cooldown_penalty = effects.get("cooldown_penalty", 0)
    cog.disaster_fine_amount = effects.get("fine_amount", 0)
    cog.disaster_display_glitch = effects.get("display_glitch", False)
    
    # Share glitch state globally for other modules (economy, views, legendary)
    try:
        set_glitch_state(cog.disaster_display_glitch, cog.disaster_effect_end_time)
    except Exception as e:
        logger.error(f"[DISASTER] Failed to set global glitch state: {e}")
    
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
        if disaster['key'] in DISASTER_STAT_MAPPING:
            stat_key = DISASTER_STAT_MAPPING[disaster['key']]
            try:
                await increment_stat(user_id, "fishing", stat_key, 1)
                current_value = await get_stat(user_id, "fishing", stat_key)
                await cog.bot.achievement_manager.check_unlock(
                    user_id=user_id,
                    game_category="fishing",
                    stat_key=stat_key,
                    current_value=current_value,
                    channel=channel
                )
            except Exception as e:
                logger.error(f"[DISASTER] Error checking achievement: {e}")
    except Exception as e:
        logger.error(f"[DISASTER] Error sending announcement: {e}")
    
    # Return disaster info with rewards for culprit
    return {
        "triggered": True,
        "disaster": disaster
    }

"""Admin commands for fishing system.

Contains commands for manually triggering events (owner only).
"""
import json
import logging
from datetime import datetime
import discord

from ..constants import DISASTER_EVENTS_PATH, FISHING_EVENTS_PATH, SELL_EVENTS_PATH, NPC_EVENTS_PATH

logger = logging.getLogger("fishing")


async def trigger_event_action(cog, ctx_or_interaction, target_user_id: int, 
                                event_type: str, event_key: str, is_slash: bool):
    """Force trigger an event for next appropriate action.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        target_user_id: Target user ID to trigger event for
        event_type: Type of event (disaster, fishing_event, sell_event, npc_event, meteor_shower)
        event_key: Specific event key
        is_slash: Whether this is a slash command
    """
    # Check if user is bot owner/admin
    user_id = ctx_or_interaction.user.id if is_slash else ctx_or_interaction.author.id
    if user_id != cog.bot.owner_id:
        msg = "❌ Chỉ Owner mới có quyền sử dụng lệnh này!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    valid_event_types = ["disaster", "fishing_event", "sell_event", "npc_event", "meteor_shower"]
    if event_type not in valid_event_types:
        type_list = ", ".join(valid_event_types)
        msg = f"❌ Event type không hợp lệ!\n\nDanh sách: {type_list}"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    event_data = None
    event_name = ""
    event_emoji = ""
    
    try:
        if event_type == "disaster":
            with open(DISASTER_EVENTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                disasters = {d["key"]: d for d in data.get("disasters", [])}
                if event_key in disasters:
                    event_data = disasters[event_key]
                    event_name = event_data["name"]
                    event_emoji = event_data["emoji"]
                else:
                    disaster_list = ", ".join(disasters.keys())
                    msg = f"❌ Disaster key không tồn tại!\n\nDanh sách: {disaster_list}"
                    if is_slash:
                        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx_or_interaction.reply(msg)
                    return
                    
        elif event_type == "fishing_event":
            with open(FISHING_EVENTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                events = data.get("events", {})
                if event_key in events:
                    event_data = events[event_key]
                    event_name = event_data.get("name", event_key)
                    event_emoji = "🎣"
                else:
                    event_list = ", ".join(events.keys())
                    msg = f"❌ Fishing event key không tồn tại!\n\nDanh sách: {event_list}"
                    if is_slash:
                        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx_or_interaction.reply(msg)
                    return
                    
        elif event_type == "sell_event":
            with open(SELL_EVENTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                events = data.get("events", {})
                if event_key in events:
                    event_data = events[event_key]
                    event_name = event_data.get("name", event_key)
                    event_emoji = "💰"
                else:
                    event_list = ", ".join(events.keys())
                    msg = f"❌ Sell event key không tồn tại!\n\nDanh sách: {event_list}"
                    if is_slash:
                        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx_or_interaction.reply(msg)
                    return
                    
        elif event_type == "npc_event":
            with open(NPC_EVENTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                npcs = data
                if event_key in npcs:
                    event_data = npcs[event_key]
                    event_name = event_data.get("name", event_key)
                    event_emoji = event_name.split()[0]  # First emoji
                else:
                    npc_list = ", ".join(npcs.keys())
                    msg = f"❌ NPC event key không tồn tại!\n\nDanh sách: {npc_list}"
                    if is_slash:
                        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx_or_interaction.reply(msg)
                    return
                    
        elif event_type == "meteor_shower":
            # Special case: force meteor shower tonight
            if event_key != "force":
                msg = "❌ Cho meteor_shower, event_key phải là 'force'"
                if is_slash:
                    await ctx_or_interaction.response.send_message(msg, ephemeral=True)
                else:
                    await ctx_or_interaction.reply(msg)
                return
            event_name = "Sao Băng Rơi"
            event_emoji = "🌟"
    
    except Exception as e:
        logger.error(f"[TRIGGER_EVENT] Error loading {event_type} data: {e}")
        msg = f"❌ Lỗi load {event_type} events!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    # Store pending event
    if event_type == "disaster":
        cog.pending_disaster[target_user_id] = event_key
    elif event_type == "fishing_event":
        cog.pending_fishing_event[target_user_id] = event_key
    elif event_type == "sell_event":
        cog.pending_sell_event[target_user_id] = event_key
    elif event_type == "npc_event":
        cog.pending_npc_event[target_user_id] = event_key
    elif event_type == "meteor_shower":
        cog.pending_meteor_shower.add(target_user_id)
        # Force trigger meteor shower immediately if it's between 21:00-21:05
        now = datetime.now()
        if now.hour == 21 and now.minute <= 5:
            await cog._force_meteor_shower(target_user_id, ctx_or_interaction.channel)
    
    target_user = cog.bot.get_user(target_user_id)
    target_name = target_user.mention if target_user else f"<@{target_user_id}>"
    
    action_desc = {
        "disaster": "trong lần câu tiếp theo",
        "fishing_event": "trong lần câu tiếp theo", 
        "sell_event": "trong lần bán tiếp theo",
        "npc_event": "trong lần câu tiếp theo",
        "meteor_shower": "vào tối nay lúc 21:00"
    }[event_type]
    
    embed = discord.Embed(
        title="⚡ THẢM HỌA ĐƯỢC LÊNH CHỈ",
        description=f"Người chơi {target_name} sẽ bị trigger **{event_name}** {event_emoji} {action_desc}!",
        color=discord.Color.red()
    )
    
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.reply(embed=embed)
    
    logger.info(f"[TRIGGER_EVENT] Admin triggered {event_type}/{event_key} for user {target_user_id}")

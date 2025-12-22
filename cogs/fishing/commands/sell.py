"""Sell command logic for fishing system.

Handles selling fish with random events and emotional states.
"""
import logging
import random
import time
import asyncio
import discord

from database_manager import get_inventory, add_seeds, db_manager, get_stat, increment_stat
from ..constants import ALL_FISH, LEGENDARY_FISH_KEYS, COMMON_FISH_KEYS, RARE_FISH_KEYS
from ..mechanics.glitch import apply_display_glitch as _glitch
from ..mechanics.events import trigger_random_event

logger = logging.getLogger("fishing")


async def sell_fish_action(cog, ctx_or_interaction, fish_types: str = None):
    """Sell all fish or specific types logic with RANDOM EVENTS
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context (prefix) or interaction (slash)
        fish_types: Optional comma-separated fish types to sell
        
    Returns:
        None (sends messages to Discord)
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        user_id = ctx_or_interaction.user.id
    else:
        user_id = ctx_or_interaction.author.id
    
    # *** CHECK AND APPLY LAG DEBUFF DELAY ***
    if cog.check_emotional_state(user_id, "lag"):
        await asyncio.sleep(3)
        username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
        logger.info(f"[EVENT] {username} experienced lag delay (3s) - sell fish")
    
    if is_slash:
        await ctx_or_interaction.response.defer(ephemeral=False)
        ctx = ctx_or_interaction
    else:
        ctx = ctx_or_interaction
    
    # CRITICAL: Check if sell is already being processed (prevent duplicate execution)
    current_time = time.time()
    if user_id in cog.sell_processing:
        last_sell_time = cog.sell_processing[user_id]
        if current_time - last_sell_time < 3:  # 3 second cooldown
            logger.info(f"[FISHING] [SELL_DUPLICATE_BLOCKED] user_id={user_id} time_diff={current_time - last_sell_time:.2f}s")
            msg = "⏳ Đang xử lý lệnh bán cá trước đó..."
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.reply(msg)
            return
    
    # Mark as processing
    cog.sell_processing[user_id] = current_time
    
    try:
        # Get username
        username = ctx.user.name if is_slash else ctx.author.name
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # Filter fish items by type (exclude rod materials from selling)
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH and k != "rod_material"}
        
        # ==================== CHECK FOR LEGENDARY FISH ====================
        # Remove legendary fish from sellable items (exclude ca_isekai as it's from consumables)
        legendary_fish_in_inventory = {k: v for k, v in fish_items.items() if k in LEGENDARY_FISH_KEYS and k != "ca_isekai"}
        if legendary_fish_in_inventory:
            # Show warning that legendary fish cannot be sold
            legend_names = ", ".join([_glitch(ALL_FISH[k]['name']) for k in legendary_fish_in_inventory.keys()])
            msg = f"❌ **CÁ HỮU HẠNG KHÔNG ĐƯỢC BÁN!** 🏆\n\n"
            msg += f"Bạn có: {legend_names}\n\n"
            msg += "Những con cá này vô giá! Tao sẽ giữ chúng trong túi đồ vĩnh viễn. 🎭"
            # Remove legendary fish from sellable items
            for legend_key in legendary_fish_in_inventory.keys():
                del fish_items[legend_key]
        
        # If fish_types specified, filter to only those types
        if fish_types:
            # Parse fish_types (  comma-separated like "ca_vang,megalodon")
            requested_types = [t.strip().lower() for t in fish_types.split(",")]
            fish_items = {k: v for k, v in fish_items.items() if k in requested_types}
            
            if not fish_items:
                msg = f"❌ Bạn không có cá loại **{fish_types}** để bán!"
                if is_slash:
                    await ctx.followup.send(msg, ephemeral=True)
                else:
                    await ctx.reply(msg)
                return
        
        if not fish_items:
            msg = "🪣 Bạn không có cá nào để bán!"
            if is_slash:
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.reply(msg)
            return
        
        # ==================== TRIGGER SELL RANDOM EVENT ====================
        # Check for pending sell event first
        event_result = {}
        if user_id in cog.pending_sell_event:
            event_key = cog.pending_sell_event.pop(user_id)
            # Load event data
            import json
            from ..constants import SELL_EVENTS_PATH
            try:
                with open(SELL_EVENTS_PATH, "r", encoding="utf-8") as f:
                    sell_events = json.load(f).get("sell_events", [])
                    event_data = next((e for e in sell_events if e["key"] == event_key), None)
                    if event_data:
                        event_result = {"triggered": True, "type": event_key, "message": event_data["message"]}
                        event_result.update(event_data.get("effects", {}))
                        logger.info(f"[SELL] Forced event {event_key} for {username}")
            except Exception as e:
                logger.error(f"[SELL] Error loading forced sell event: {e}")
        
        # If no forced event, roll for random event
        if not event_result:
            # Roll for sell event (5% chance)
            if random.random() < 0.05:
                import json
                from ..constants import SELL_EVENTS_PATH
                try:
                    with open(SELL_EVENTS_PATH, "r", encoding="utf-8") as f:
                        sell_events = json.load(f).get("sell_events", [])
                        if sell_events:
                            event = random.choice(sell_events)
                            event_result = {"triggered": True, "type": event["key"], "message": event["message"]}
                            event_result.update(event.get("effects", {}))
                            logger.info(f"[SELL] Random event {event['key']} triggered for {username}")
                except Exception as e:
                    logger.error(f"[SELL] Error loading sell events: {e}")
        
        # Calculate total sell value
        total_value = 0
        fish_sold = {}
        
        for fish_key, quantity in fish_items.items():
            if fish_key in ALL_FISH:
                fish_data = ALL_FISH[fish_key]
                sell_price = fish_data.get("sell_price", 0)
                total_value += sell_price * quantity
                fish_sold[fish_key] = {"quantity": quantity, "unit_price": sell_price, "total": sell_price * quantity}
        
        # Apply Keo Ly buff (2x sell price for 10 minutes)
        price_multiplier = 1.0
        if cog.check_emotional_state(user_id, "keo_ly"):
            price_multiplier = 2.0
            logger.info(f"[SELL] {username} has keo_ly buff active! 2x sell price")
        
        # Apply sell event modifiers
        if event_result.get("triggered"):
            if "price_bonus" in event_result:
                price_multiplier *= event_result["price_bonus"]
                logger.info(f"[SELL] Event {event_result['type']} bonus: {event_result['price_bonus']}x")
        
        final_value = int(total_value * price_multiplier)
        
        # Build sell message
        if len(fish_sold) <= 5:
            # Show individual fish details
            fish_details = []
            for fish_key, details in fish_sold.items():
                fish_name = _glitch(ALL_FISH[fish_key]["name"])
                emoji = ALL_FISH[fish_key].get("emoji", "")
                fish_details.append(f"{emoji} **{fish_name}** x{details['quantity']} = {details['total']} Hạt")
            fish_list = "\n".join(fish_details)
        else:
            # Too many types, show summary
            fish_list = f"**Tổng {len(fish_sold)} loại cá**"
        
        # Apply event effects BEFORE selling
        event_message = ""
        if event_result.get("triggered"):
            event_message = f"\n\n🎲 **SỰ KIỆN:** {event_result['message']}\n"
            if price_multiplier != 1.0:
                event_message += f"💰 Giá bán: {price_multiplier}x\n"
        
        # Build embed
        embed = discord.Embed(
            title=f"💰 {username} Bán Cá",
            description=f"{fish_list}\n\n**Tổng tiền:** {final_value} Hạt{event_message}",
            color=discord.Color.green()
        )
        
        # Actually remove fish from inventory and add money
        for fish_key in fish_items.keys():
            from cogs.fishing.helpers import remove_item
            await remove_item(user_id, fish_key, fish_items[fish_key])
        
        await add_seeds(user_id, final_value)
        
        # Track stats
        try:
            total_fish_sold = sum(fish_items.values())
            await increment_stat(user_id, "fishing", "fish_sold", total_fish_sold)
            await increment_stat(user_id, "fishing", "money_earned", final_value)
            
            # Check merchant achievement
            current_money = await get_stat(user_id, "fishing", "money_earned")
            await cog.bot.achievement_manager.check_unlock(
                user_id=user_id,
                game_category="fishing",
                stat_key="money_earned",
                current_value=current_money,
                channel=ctx.channel
            )
        except Exception as e:
            logger.error(f"[SELL] Error updating stats: {e}")
        
        # Send result
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.reply(embed=embed)
        
        logger.info(f"[SELL] {username} sold {len(fish_sold)} types, {sum(fish_items.values())} fish for {final_value} seeds")
    
    finally:
        # Always cleanup sell processing lock
        if user_id in cog.sell_processing:
            del cog.sell_processing[user_id]

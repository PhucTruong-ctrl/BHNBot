"""Sell command logic for fishing system.

Handles selling fish with random events and emotional states.
"""
import logging
import random
import time
import asyncio
import discord
from datetime import datetime

from database_manager import get_inventory, add_seeds, db_manager, get_stat, increment_stat, remove_item
from ..constants import ALL_FISH, LEGENDARY_FISH_KEYS, COMMON_FISH_KEYS, RARE_FISH_KEYS
from ..mechanics.glitch import apply_display_glitch as _glitch
from ..mechanics.events import trigger_random_event

logger = logging.getLogger("fishing")


async def _should_auto_sell_item(user_id: int, item_key: str) -> bool:
    """Determine if item should be auto-sold based on player achievements.
    
    Protected items (chests, materials, commemorative, consumables) are never auto-sold.
    Some items can be sold conditionally after achieving specific milestones.
    
    Args:
        user_id (int): Discord user ID
        item_key (str): Item key to check
        
    Returns:
        bool: True if item can be auto-sold, False if protected
    """
    from database_manager import get_rod_data, get_stat
    
    # COMPREHENSIVE protected items list
    # Import would be ideal but avoiding circular dependency
    PROTECTED_ITEMS = {
        # === CHESTS (CRITICAL - User reported bug) ===
        "ruong_kho_bau",  # Main treasure chest from fishing events
        "ruong_go", "ruong_bac", "ruong_vang", "ruong_kim_cuong",
        
        # === GIFTS (For trading/giving) ===
        "cafe", "flower", "ring", "gift", "chocolate", "card",
        
        # === CONSUMABLES (Bait & Buffs) ===
        "moi",  # Worm (bait)
        "co_bon_la",  # Four-leaf clover
        "phan_bon",  # Fertilizer (for tree)
        "nuoc_tang_luc", "gang_tay_xin", "thao_tac_tinh_vi", "tinh_yeu_ca", "tinh_cau",
        
        # === LEGENDARY COMPONENTS (Rare crafting) ===
        "long_vu_lua",  # Phoenix feather
        
        # === PUZZLE PIECES (Quest items) ===
        "manh_ghep_a", "manh_ghep_b", "manh_ghep_c", "manh_ghep_d",
        
        # === COMMEMORATIVE (Season rewards - never sellable) ===
        "qua_ngot_mua_1", "qua_ngot_mua_2", "qua_ngot_mua_3", "qua_ngot_mua_4", "qua_ngot_mua_5",
        
        # === SPECIAL (Manual sell only via /banca ngoc_trai) ===
        "ngoc_trai",  # Pearl
    }
    
    # Always forbid protected items
    if item_key in PROTECTED_ITEMS:
        return False
    
    # === Conditional Items (can sell after achievements) ===
    
    # Upgrade materials: Only sell if rod is max level (7)
    if item_key == "vat_lieu_nang_cap":
        rod_level, _ = await get_rod_data(user_id)
        return rod_level >= 7
    
    # Map fragments & dark map: Only sell after catching Cthulhu
    if item_key in ["manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d", "ban_do_ham_am"]:
        cthulhu_caught = await get_stat(user_id, "fishing", "cthulhu_con_caught")
        return cthulhu_caught and cthulhu_caught > 0
    
    # Meteor fragments: Only sell after catching Galaxy Fish AND max rod level
    if item_key == "manh_sao_bang":
        galaxy_caught = await get_stat(user_id, "fishing", "ca_ngan_ha_caught")
        rod_level, _ = await get_rod_data(user_id)
        return (galaxy_caught and galaxy_caught > 0) and rod_level >= 7
    
    # Sonic detector: Only sell after catching 52 Hz Whale
    if item_key == "may_do_song":
        whale_caught = await get_stat(user_id, "fishing", "ca_voi_52hz_caught")
        return whale_caught and whale_caught > 0
    
    # Phoenix feather: Only sell after catching Phoenix
    if item_key == "long_vu_lua":
        phoenix_caught = await get_stat(user_id, "fishing", "ca_phuong_hoang_caught")
        return phoenix_caught and phoenix_caught > 0
    
    # Default: allow selling (regular fish items)
    return True


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
    if await cog.check_emotional_state(user_id, "lag"):
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
        
        # ENTRY LOG
        logger.info(f"[SELL] Processing sell command for {username} (user_id={user_id})")
        
        # Get inventory
        inventory = await get_inventory(user_id)
        
        # ==================== FILTER SELLABLE ITEMS ====================
        # Start with items that are in ALL_FISH (fish + special items from fishing)
        fish_items = {k: v for k, v in inventory.items() if k in ALL_FISH}
        
        # Apply achievement-based filter for protected/conditional items
        # This excludes: chests, materials, commemorative items, consumables
        # And conditionally allows: upgrade materials (rod lv7), map fragments (after Cthulhu), etc.
        sellable_items = {}
        for item_key, quantity in fish_items.items():
            if await _should_auto_sell_item(user_id, item_key):
                sellable_items[item_key] = quantity
        
        fish_items = sellable_items
        
        # ==================== CHECK FOR LEGENDARY FISH ====================
        # Remove legendary fish from sellable items
        legendary_fish_in_inventory = {k: v for k, v in fish_items.items() if k in LEGENDARY_FISH_KEYS}
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
        
        # 1. TRIGGER INTERACTIVE EVENT (Priority)
        # Check for interactive events (Black Market, Haggle, etc.)
        # If triggered, we stop here and let the View handle the rest.
        try:
            from ..mechanics.interactive_sell_events import (
                check_interactive_event, 
                create_interactive_view, 
                create_interactive_embed
            )
            # Load sell events data
            import json
            from ..constants import SELL_EVENTS_PATH
            with open(SELL_EVENTS_PATH, "r", encoding="utf-8") as f:
                sell_events_data = json.load(f)
            
            # Check if interactive event triggers
            # Calculate base value for condition checking
            temp_base_value = 0
            for fish_key, quantity in fish_items.items():
                if fish_key in ALL_FISH:
                    temp_base_value += ALL_FISH[fish_key].get("sell_price", 0) * quantity
                    
            interactive_event = await check_interactive_event(
                user_id, fish_items, temp_base_value, sell_events_data
            )
            
            # Force trigger from pending_sell_event if set (for testing/admin)
            if user_id in cog.pending_sell_event:
                forced_key = cog.pending_sell_event.pop(user_id)
                events_map = sell_events_data.get('events', {})
                if forced_key in events_map and events_map[forced_key].get('type') == 'interactive':
                    interactive_event = events_map[forced_key]
                    interactive_event['key'] = forced_key
                    logger.info(f"[SELL] Forced interactive event {forced_key} for {username}")

            if interactive_event:
                # Create View and Embed
                view = create_interactive_view(
                    interactive_event, cog, user_id, fish_items, temp_base_value, ctx
                )
                embed = create_interactive_embed(
                    interactive_event, temp_base_value, fish_items
                )
                
                # Send interactive message
                if is_slash:
                    await ctx.followup.send(embed=embed, view=view)
                else:
                    await ctx.reply(embed=embed, view=view)
                
                logger.info(f"[SELL] Interactive event {interactive_event.get('key')} started for {username}")
                return # STOP execution here, View handles the rest
                
        except Exception as e:
            logger.error(f"[SELL] Error checking interactive events: {e}", exc_info=True)

        # 2. TRIGGER PASSIVE EVENT (Legacy/Standard)
        # Check for pending sell event first (Legacy support or passive events)
        event_result = {}
        total_value = 0
        fish_sold = {}
        
        for fish_key, quantity in fish_items.items():
            if fish_key in ALL_FISH:
                fish_data = ALL_FISH[fish_key]
                sell_price = fish_data.get("sell_price", 0)
                total_value += sell_price * quantity
                fish_sold[fish_key] = {"quantity": quantity, "unit_price": sell_price, "total": sell_price * quantity}
        
        # ... (Previous code remains up to fish_sold calculation)
        
        # Apply Keo Ly buff (2x sell price for 10 minutes)
        # Note: Keo Ly is essentially a personal event buff
        price_multiplier = 1.0
        if await cog.check_emotional_state(user_id, "keo_ly"):
            price_multiplier = 2.0
            logger.info(f"[SELL] {username} has keo_ly buff active! 2x sell price")
        elif await cog.check_emotional_state(user_id, "charity_buff"):
            price_multiplier = 1.5
            logger.info(f"[SELL] {username} has charity_buff active! 1.5x sell price")
        
        # HOOK: Global Event Sell Multiplier
        # This replaces manually triggering events inside sell.py
        # The manager handles the event state, we just ask for the multiplier.
        global_sell_mul = cog.global_event_manager.get_public_effect("sell_multiplier", 1.0)
        if global_sell_mul != 1.0:
            price_multiplier *= global_sell_mul
            logger.info(f"[SELL] {username} Global Event Sell Multiplier: x{global_sell_mul}")
        
        # Apply sell event modifiers
        flat_bonus = 0
        special_reward = None
        event_info_text = ""
        
        if event_result.get("triggered"):
            # Multiplier
            if "mul" in event_result:
                price_multiplier *= float(event_result["mul"])
            
            # Flat bonus/penalty (Applied AFTER multiplier to unit price or Total? User said: (Base * Event) * Boost)
            # Usually flat is added to total.
            if "flat" in event_result:
                flat_bonus = int(event_result["flat"])
                
            # Special Items logic (already implemented previously, keeping passing pass or specific logic)
            # We will handle item giving at the end
            
            # Log
            logger.info(f"[SELL] Event {event_result['type']}: Mul={event_result.get('mul', 1)}, Flat={flat_bonus}")
        
        # CALCULATE PRE-BOOST TOTAL
        # Base Total is calculated earlier as `total_value`
        
        # Adjusted Total (Before Boost) = (Base * Multiplier) + Flat
        adjusted_total = int(total_value * price_multiplier) + flat_bonus
        if adjusted_total < 0: adjusted_total = 0
        
        # CHECK SERVER BOOST
        server_boost_mul = 1.0
        is_boosted = False
        if ctx.guild:
            try:
                from ..utils.helpers import get_tree_boost_status
                is_boosted = await get_tree_boost_status(cog, ctx.guild.id)
                if is_boosted:
                    server_boost_mul = 2.0
            except Exception as e:
                logger.error(f"[SELL] Error checking boost: {e}")
        
        # FINAL TOTAL
        final_value = int(adjusted_total * server_boost_mul)
        
        # ==================== BUILD EMBED ====================
        # ==================== BUILD EMBED (REDESIGN) ====================
        # Receipt Style Design
        embed = discord.Embed(
            title=f"🏪 SẠP CÁ {username.upper()} - HÓA ĐƠN",
            description=f"📍 **Địa điểm:** Chợ Cá Bên Hiên Nhà\n⏰ **Thời gian:** {datetime.now().strftime('%H:%M %d/%m/%Y')}",
            color=discord.Color.gold()
        )
        
        # 1. DETAILED FISH LIST
        # Format: 🐟 Cá Chép x5 = 500 Hạt
        fish_lines = []
        if len(fish_sold) <= 20:
            for fish_key, details in fish_sold.items():
                fish_name = _glitch(ALL_FISH[fish_key]["name"])
                emoji = ALL_FISH[fish_key].get("emoji", "🐟")
                qty = details['quantity']
                # Calculate line total (Base Price * Qty)
                # Note: This is BASE price. Modifiers are applied to the total sum later.
                # To be clear, we show Base Total here.
                line_total = details['unit_price'] * qty
                
                fish_lines.append(f"{emoji} **{fish_name}** x{qty} = `{line_total:,} Hạt`")
        else:
            fish_lines.append(f"📦 **Tổng {len(fish_sold)} loại cá** (Danh sách quá dài...)")
            
        # Join lines
        items_content = "\n".join(fish_lines)
        if len(items_content) > 1000: # Safety truncation
             items_content = items_content[:900] + "\n... (danh sách quá dài)"
             
        embed.add_field(name="📋 Chi Tiết Đơn Hàng", value=items_content, inline=False)
        
        # 2. CALCULATION BREAKDOWN
        # Show clearer math: Base -> Event/Buff -> Boost -> Final
        breakdown_lines = []
        breakdown_lines.append(f"💵 **Tổng Gốc:** `{total_value:,} Hạt`")
        
        # Buffs/Events
        if price_multiplier != 1.0 or flat_bonus != 0:
            buff_text = []
            if price_multiplier > 1.0: buff_text.append(f"x{price_multiplier:.1f} (Event/Buff)")
            if price_multiplier < 1.0: buff_text.append(f"x{price_multiplier:.1f} (Giá Giảm)")
            if flat_bonus != 0: 
                sign = "+" if flat_bonus > 0 else ""
                buff_text.append(f"{sign}{flat_bonus} Hạt")
            
            breakdown_lines.append(f"� **Biến Động:** {' | '.join(buff_text)}")
            if event_result.get("triggered"):
                 breakdown_lines.append(f"   _(Sự kiện: {event_result.get('message', 'Unknown')})_")
        
        # Server Boost
        if is_boosted:
            breakdown_lines.append(f"🌳 **Cây Server:** x{server_boost_mul:.1f} (Buff Toàn Server)")
            
        embed.add_field(name="📊 Tổng Kết", value="\n".join(breakdown_lines), inline=False)
        
        # 3. FINAL TOTAL (Big & Bold)
        embed.add_field(
            name="� TỔNG NHẬN",
            value=f"# +{final_value:,} Hạt",
            inline=False
        )
        
        embed.set_footer(text="Cảm ơn quý khách đã ủng hộ sạp cá! 🐟💸")
        if is_boosted:
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1253945310690934835/1265842340535308369/tree_buff.png") # Optional visual flair
        
        # Handle Special Item rewards
        reward_msg = ""
        if "special" in event_result:
            from database_manager import add_item # Import here to be safe
            special_type = event_result["special"]
            
            if special_type == "chest":
                await add_item(user_id, "ruong_kho_bau", 1)
                reward_msg = "🎁 **Nhận thêm:** 1 Rương Kho Báu"
            elif special_type == "moi":
                await add_item(user_id, "moi", 5)
                reward_msg = "🪱 **Nhận thêm:** 5 Mồi Câu"
            elif special_type == "ngoc_trai":
                await add_item(user_id, "ngoc_trai", 1)
                reward_msg = "🔮 **Nhận thêm:** 1 Ngọc Trai"
            elif special_type == "vat_lieu_nang_cap":
                amt = random.randint(2, 5)
                await add_item(user_id, "vat_lieu_nang_cap", amt)
                reward_msg = f"🛠️ **Nhận thêm:** {amt} Vật Liệu Cần Câu"
            
            if reward_msg:
                embed.add_field(name="🎁 Quà Tặng Sự Kiện", value=reward_msg, inline=False)

        # Actually remove fish from inventory and add money
        for fish_key in fish_items.keys():
            await remove_item(user_id, fish_key, fish_items[fish_key])
            
        # HOOK: Cthulhu Raid Hijack
        if hasattr(cog, "global_event_manager") and cog.global_event_manager.current_event:
             evt = cog.global_event_manager.current_event
             evt_data = evt.get("data", {})
             event_type = evt_data.get("type")
             logger.info(f"[SELL] Check Hijack: Event={evt.get('key')} Type={event_type}")
             
             if event_type == "raid_boss":
                 # Convert Money to Damage
                 damage = final_value
                 # Perform contribution
                 await cog.global_event_manager.process_raid_contribution(user_id, damage)
                 logger.info(f"[SELL] HIJACKED! User {user_id} dealt {damage} damage instead of earning money.")
                 
                 final_value = 0 # No money
                 
                 # UPDATE EMBED
                 embed.title = f"⚔️ ĐÃ ĐÓNG GÓP CHO {evt.get('key').upper().replace('_', ' ')}!"
                 embed.color = discord.Color.dark_red()
                 
                 for i, field in enumerate(embed.fields):
                     if "TỔNG NHẬN" in field.name or "Sát Thương" in field.name in field.name:
                         embed.remove_field(i)
                         break
                         
                 # Generic Label: Contribution Points
                 embed.add_field(name="✨ Điểm Đóng Góp", value=f"# {damage:,} Điểm", inline=False)
                 embed.set_footer(text="Cảm ơn bạn đã chung tay bảo vệ server!")
             elif event_type == "fish_quest_raid":
                 # Dragon Quest contribution
                 contribution_qty, fish_value_deducted = await cog.global_event_manager.process_dragon_contribution(
                     user_id, fish_items
                 )
                 
                 if contribution_qty > 0:
                     # Deduct fish value from final payout
                     final_value -= fish_value_deducted
                     if final_value < 0:
                         final_value = 0
                     
                     # Log contribution
                     dragon_name = cog.global_event_manager.dragon_state.get("requested_fish_name", "cá")
                     logger.info(f"[SELL] Dragon Quest contribution! User {user_id} contributed {contribution_qty} {dragon_name}, value deducted: {fish_value_deducted}")
                     
                     # Update Embed
                     embed.add_field(
                         name="🐲 Đóng Góp Long Thần",
                         value=f"Bạn đã đóng góp **{contribution_qty} {dragon_name}** cho Long Thần!\\n_(Cá đóng góp không tính tiền: -{fish_value_deducted:,} Hạt)_",
                         inline=False
                     )
             else:
                 logger.info(f"[SELL] Hijack skipped: Type {evt.get('type')} != raid_boss/fish_quest_raid")
        
        await add_seeds(user_id, final_value, 'sell_fish', 'fishing')
        
        # Track stats
        logger.info(f"[SELL] ========== BEFORE STATS TRACKING for user {user_id} ==========")
        try:
            logger.info(f"[SELL] ========== INSIDE TRY BLOCK ==========")
            total_fish_sold = sum(fish_items.values())
            await increment_stat(user_id, "fishing", "fish_sold", total_fish_sold)
            await increment_stat(user_id, "fishing", "total_money_earned", final_value)
            await increment_stat(user_id, "fishing", "sell_count", 1)
            logger.info(f"[SELL] Incremented sell_count for user {user_id}")
            
            # Check unlock notifications
            # Use local check_sell_conditional_unlocks function
            current_sell_count = await get_stat(user_id, "fishing", "sell_count")
            logger.info(f"[SELL] Checking conditional unlocks: sell_count={current_sell_count}")
            
            # Check sell_count achievement
            await cog.bot.achievement_manager.check_unlock(
                user_id, "fishing", "sell_count", current_sell_count, ctx.channel
            )
            
            # Check achievements
            current_money = await get_stat(user_id, "fishing", "total_money_earned")
            await cog.bot.achievement_manager.check_unlock(
                user_id, "fishing", "total_money_earned", current_money, ctx.channel
            )
            
            # Check fish_sold achievement  
            current_fish_sold = await get_stat(user_id, "fishing", "fish_sold")
            await cog.bot.achievement_manager.check_unlock(
                user_id, "fishing", "fish_sold", current_fish_sold, ctx.channel
            )
            
            # Check rare_fish_sold achievement
            current_rare = await get_stat(user_id, "fishing", "rare_fish_sold")
            await cog.bot.achievement_manager.check_unlock(
                user_id, "fishing", "rare_fish_sold", current_rare, ctx.channel
            )
        except Exception as e:
            logger.error(f"[SELL] Error updating stats: {e}")
        
        # Send result
        if is_slash:
            await ctx.followup.send(embed=embed)
        else:
            await ctx.reply(embed=embed)
        
        logger.info(f"[SELL] {username} sold {len(fish_items)} types, {sum(fish_items.values())} fish for {final_value} seeds (Boost: {server_boost_mul})")
    
    finally:
        # Always cleanup sell processing lock
        if user_id in cog.sell_processing:
            del cog.sell_processing[user_id]

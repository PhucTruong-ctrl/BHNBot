"""Bucket-related commands for fishing system.

Handles chest opening, trash recycling, phan_bon usage, and collection viewing.
"""
import logging
import random
import asyncio
import discord

from database_manager import (
    get_inventory, add_item, remove_item, add_seeds,
    get_stat, increment_stat
)
from ..constants import (
    ALL_FISH, TRASH_ITEMS, CHEST_LOOT, GIFT_ITEMS,
    ALL_ITEMS_DATA, LEGENDARY_FISH_KEYS, COMMON_FISH_KEYS, RARE_FISH_KEYS,
    COMMON_FISH, RARE_FISH, phan_bon_EFFECTS
)
from ..mechanics.rod_system import get_rod_data
from ..mechanics.glitch import apply_display_glitch

logger = logging.getLogger("fishing")


async def open_chest_action(cog, ctx_or_interaction, quantity: int = 1):
    """Open treasure chest logic (Bulk supported).
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        quantity: Number of chests to open (default 1)
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        # Check if deferred already
        if not ctx_or_interaction.response.is_done():
            await ctx_or_interaction.response.defer(ephemeral=False)
        ctx = ctx_or_interaction
        user = ctx_or_interaction.user
        channel = ctx_or_interaction.channel
    else:
        ctx = ctx_or_interaction
        user = ctx.author
        channel = ctx.channel
    
    user_id = user.id
    user_name = user.name
    
    # 1. Validate Quantity
    if quantity < 1:
        msg = "❌ Số lượng phải lớn hơn 0!"
        if is_slash: await ctx.followup.send(msg, ephemeral=True)
        else: await ctx.reply(msg)
        return

    # *** CHECK AND APPLY LAG DEBUFF DELAY ***
    if await cog.check_emotional_state(user_id, "lag"):
        await asyncio.sleep(3)
        logger.info(f"[EVENT] {user_name} experienced lag delay (3s) - open chest")
    
    # 2. Check Inventory & Deduct Chests
    inventory = await get_inventory(user_id)
    current_chests = inventory.get("ruong_kho_bau", 0)
    
    if current_chests < quantity:
        msg = f"❌ Bạn chỉ có **{current_chests}** Rương Kho Báu! (Muốn mở: {quantity})"
        if is_slash: await ctx.followup.send(msg, ephemeral=True)
        else: await ctx.reply(msg)
        return
    
    # Deduct chests immediately
    await remove_item(user_id, "ruong_kho_bau", quantity)
    
    # 3. Track Stats
    try:
        await increment_stat(user_id, "fishing", "chests_opened", quantity)
        current_opened = await get_stat(user_id, "fishing", "chests_opened")
        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "chests_opened", current_opened, channel)
    except Exception as e:
        logger.error(f"[ACHIEVEMENT] Error updating chests_opened for {user_id}: {e}")
    
    # 4. Prepare RNG Factors
    rod_level, _ = await get_rod_data(user_id)
    user_luck = await cog.get_user_total_luck(user_id)
    
    # Base item count weights: 0, 1, 2, 3 items per chest
    base_weights = [30, 45, 20, 5]
    rod_bonus = (rod_level - 1) * 5
    base_weights[0] = max(5, base_weights[0] - rod_bonus)
    base_weights[2] += rod_bonus
    
    luck_factor = max(0, user_luck)
    base_weights[2] = int(base_weights[2] * (1 + luck_factor))
    base_weights[3] = int(base_weights[3] * (1 + luck_factor * 2))
    
    # Loot Keys & Weights
    loot_keys = list(CHEST_LOOT.keys())
    loot_weights = []
    trash_key_list = [t.get("key") for t in TRASH_ITEMS]
    
    for item in loot_keys:
        base_weight = CHEST_LOOT[item]
        if "manh_" in item or "gift" in item or "tui_tien" in item:
            multiplier = 1.0 + max(0, user_luck * 1.5)
            loot_weights.append(base_weight * multiplier)
        elif "trash" in item or item in trash_key_list:
            multiplier = max(0.1, 1.0 - max(0, user_luck))
            loot_weights.append(base_weight * multiplier)
        else:
            loot_weights.append(base_weight)
            
    # 5. Bulk Roll Logic (Loop)
    aggregated_loot = {} # {item_key: count}
    total_seeds = 0
    total_items_count = 0
    
    for _ in range(quantity):
        # Roll item count for this chest
        num_items = random.choices([0, 1, 2, 3], weights=base_weights, k=1)[0]
        total_items_count += num_items
        
        if num_items > 0:
            # Roll looting items
            items_rolled = random.choices(loot_keys, weights=loot_weights, k=num_items)
            for item in items_rolled:
                if item == "nothing": continue
                
                if item == "tui_tien":
                    coins = random.randint(100, 200)
                    total_seeds += coins
                else:
                    aggregated_loot[item] = aggregated_loot.get(item, 0) + 1

    logger.info(f"[CHEST] {user_name} opened {quantity} chests, got {total_items_count} items, {total_seeds} seeds")

    # 6. Process Rewards & Batch DB Update
    loot_messages = []
    
    # A. Add Seeds
    if total_seeds > 0:
        await add_seeds(user_id, total_seeds)
        loot_messages.append(f"💰 **+{total_seeds:,} Hạt**")
        
    # B. Add Items (Batch Optimization)
    # We iterate aggregated_loot and call add_inventory_item (which handles INSERT/UPDATE)
    # Ideally, we should have a batch_add_items function in DB manager, but currently looping add_inventory_item is okay-ish for async sqlite
    # Optimization: Sort items to group DB writes logically if needed, but not strictly required.
    
    puzzle_pieces_got = []
    
    for item_key, count in aggregated_loot.items():
        if item_key == "phan_bon":
            await cog.add_inventory_item(user_id, "phan_bon", count)
            loot_messages.append(f"🌾 **Phân Bón** x{count}")
            
        elif item_key == "manh_ghep":
            # Randomize puzzle pieces
            pieces = ["puzzle_a", "puzzle_b", "puzzle_c", "puzzle_d"]
            for _ in range(count):
                p = random.choice(pieces)
                puzzle_pieces_got.append(p)
                await cog.add_inventory_item(user_id, p, 1) # Add one by one to randomize types
            
            # Since we added individually, we just summarize
            loot_messages.append(f"🧩 **Mảnh Ghép** x{count} (Ngẫu nhiên)")
            
        elif item_key in ["manh_sao_bang", "manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d"]:
            await cog.add_inventory_item(user_id, item_key, count)
            item_data = ALL_ITEMS_DATA.get(item_key, {})
            name = item_data.get("name", item_key)
            emoji = item_data.get("emoji", "❓")
            loot_messages.append(f"{emoji} **{name}** x{count}")
            
        elif item_key in trash_key_list:
            await cog.add_inventory_item(user_id, item_key, count)
            trash_data = next((t for t in TRASH_ITEMS if t["key"] == item_key), {})
            name = trash_data.get("name", item_key)
            emoji = trash_data.get("emoji", "🗑️")
            loot_messages.append(f"{emoji} **{name}** x{count}")
            
        else: # Gifts or generic Items
            await cog.add_inventory_item(user_id, item_key, count)
            # Try to find name in GIFT_ITEMS logic or ALL_ITEMS_DATA
            gift_names = {"cafe": "☕ Cà Phê", "flower": "🌹 Hoa", "ring": "💍 Nhẫn", 
                         "gift": "🎁 Quà", "chocolate": "🍫 Sô Cô La", "card": "💌 Thiệp"}
            name = gift_names.get(item_key, item_key.title())
            loot_messages.append(f"🎁 **{name}** x{count}")

    # 7. Post-Process Special Logics (Puzzle Check)
    if puzzle_pieces_got:
        # Check full set logic again? 
        # For bulk opening, maybe just warn them to check inventory or auto-claim?
        # The original code auto-claimed. Let's do a quick check.
        inv_check = await get_inventory(user_id)
        if all(inv_check.get(f"puzzle_{p}", 0) > 0 for p in ["a", "b", "c", "d"]):
            # Auto claim ONE set if they have full set? 
            # Or many sets?
            # Complexity: Checking how many FULL SETS they have.
            # set_count = min(inv_check["puzzle_a"], inv_check["puzzle_b"]...)
            # For simplicity and UX, let's just trigger one claim notification if they have at least one set.
            # Actual claiming usually happens in a separate event or re-check.
            # Original code did: remove 1 set -> give 5000-10000 seeds.
            # We will keep it simple: if valid set found, auto-exchange 1 set and notify.
            
            # Logic: greedy exchange all sets?
            a, b, c, d = [inv_check.get(f"puzzle_{x}", 0) for x in "abcd"]
            sets_can_make = min(a, b, c, d)
            
            if sets_can_make > 0:
                reward_total = 0
                for _ in range(sets_can_make):
                    reward_total += random.randint(5000, 10000)
                
                await remove_item(user_id, "puzzle_a", sets_can_make)
                await remove_item(user_id, "puzzle_b", sets_can_make)
                await remove_item(user_id, "puzzle_c", sets_can_make)
                await remove_item(user_id, "puzzle_d", sets_can_make)
                await add_seeds(user_id, reward_total)
                
                loot_messages.append(f"🎉 **ĐỦ {sets_can_make} BỘ MẢNH GHÉP!** Tự động đổi: +{reward_total:,} Hạt!")

    # 8. Build Premium Embed
    if not loot_messages:
        description = "**❌ Rương trống không!** (Xui quá đen thôi...)"
        color = discord.Color.dark_grey()
    else:
        # Sort loot messages slightly?
        # Actually random order is fine, or group by type.
        # We constructed them by type order above.
        description = "\n".join(loot_messages)
        color = discord.Color.gold()
        
    embed = discord.Embed(
        title=f"🎁 {user_name} Mở {quantity} Rương!",
        description=description,
        color=color
    )
    
    # Footer Stats
    stats_text = f"Cấp Cần: {rod_level} | Tổng Item: {total_items_count}"
    if total_seeds > 0: stats_text += f" | +{total_seeds} Hạt"
    embed.set_footer(text=stats_text)
    
    if is_slash:
        await ctx.followup.send(embed=embed)
    else:
        await ctx.reply(embed=embed)


async def recycle_trash_action(cog, ctx_or_interaction, action: str = None):
    """Recycle trash into seeds.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        action: Optional action type
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        user_id = ctx_or_interaction.user.id
        user_name = ctx_or_interaction.user.name
        await ctx_or_interaction.response.defer(ephemeral=False)
        ctx = ctx_or_interaction
    else:
        user_id = ctx_or_interaction.author.id
        user_name = ctx_or_interaction.author.name
        ctx = ctx_or_interaction
    
    # Get inventory
    inventory = await get_inventory(user_id)
    
    # Find all trash items (stored as "trash_01", "trash_02", etc.)
    # OLD BUG: trash_keys = [t.get("key") for t in TRASH_ITEMS]  # This was WRONG!
    # FIXED: Use startswith pattern matching like tuido command does
    user_trash = {k: v for k, v in inventory.items() if k.startswith("trash_") and v > 0}
    
    if not user_trash:
        msg = "🪣 Bạn không có rác nào để tái chế!"
        if is_slash:
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    
    # Calculate recycle value (1 phan_bon per 10 trash)
    total_trash = sum(user_trash.values())
    phan_bon_amount = total_trash // 10
    
    if phan_bon_amount == 0:
        msg = "🪣 Bạn cần ít nhất 10 rác để tái chế thành 1 phân bón!"
        if is_slash:
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    
    # Remove all trash
    for trash_key, quantity in user_trash.items():
        await remove_item(user_id, trash_key, quantity)
    
    # Add phan_bon (not seeds!)
    await cog.add_inventory_item(user_id, "phan_bon", phan_bon_amount)
    
    # Track recycling stats
    try:
        await increment_stat(user_id, "fishing", "trash_recycled", total_trash)
        current_recycled = await get_stat(user_id, "fishing", "trash_recycled")
        channel = ctx.channel if not is_slash else ctx_or_interaction.channel
        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "trash_recycled", current_recycled, channel)
    except Exception as e:
        logger.error(f"[ACHIEVEMENT] Error updating trash_recycled: {e}")
    
    # Build embed
    embed = discord.Embed(
        title="♻️ Tái Chế Rác",
        description=f"**Đã tái chế {total_trash} món rác!**\n\n🌱 Nhận được: **{phan_bon_amount} Phân Bón**",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"👤 {user_name}")
    
    if is_slash:
        await ctx.followup.send(embed=embed)
    else:
        await ctx.reply(embed=embed)
    
    logger.info(f"[RECYCLE] {user_name} recycled {total_trash} trash for {phan_bon_amount} phan_bon")


async def use_phan_bon_action(cog, ctx_or_interaction):
    """Use ALL phan_bon (fertilizers) to contribute to server tree.
    
    Each fertilizer gives 50-100 random EXP to the tree.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        user_id = ctx_or_interaction.user.id
        username = ctx_or_interaction.user.display_name
        guild_id = ctx_or_interaction.guild.id
        await ctx_or_interaction.response.defer(ephemeral=False)
        ctx = ctx_or_interaction
    else:
        user_id = ctx_or_interaction.author.id
        username = ctx_or_interaction.author.display_name
        guild_id = ctx_or_interaction.guild.id
        ctx = ctx_or_interaction
    
    # Get inventory
    inventory = await get_inventory(user_id)
    fertilizer_count = inventory.get("phan_bon", 0)
    
    # Check if user has fertilizers
    if fertilizer_count == 0:
        msg = "❌ Bạn không có phân bón nào để bón cho cây!"
        if is_slash:
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    
    # Calculate random EXP for each fertilizer (50-100 each)
    total_exp = sum(random.randint(50, 100) for _ in range(fertilizer_count))
    
    # Remove all fertilizers from inventory
    await remove_item(user_id, "phan_bon", fertilizer_count)
    logger.info(f"[BONPHAN] {username} used {fertilizer_count} fertilizers for {total_exp} EXP")
    
    # Use tree cog's API to add contribution
    tree_cog = cog.bot.get_cog("CommunityCog")
    if tree_cog:
        try:
            # Add contribution with phan_bon type
            await tree_cog.add_contributor(user_id, guild_id, total_exp, contribution_type="phan_bon")
            
            # Get tree data for progress display
            tree_level, tree_prog, tree_total, season, _, _ = await tree_cog.get_tree_data(guild_id)
            percentage = int((tree_prog / tree_total) * 100) if tree_total > 0 else 0
            
            # Update tree message
            await tree_cog.update_or_create_pin_message(guild_id, ctx.channel.id)
        except Exception as e:
            logger.error(f"[BONPHAN] Error with tree contribution: {e}", exc_info=True)
            tree_prog = 0
            tree_total = 1
            percentage = 0
    else:
        logger.warning("[BONPHAN] Tree cog not found")
        tree_prog = 0
        tree_total = 1
        percentage = 0
    
    # Create result embed
    embed = discord.Embed(
        title="🌾 Bón Phân Cho Cây!",
        description=f"**{username}** đã sài **{fertilizer_count} Phân Bón**",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="⚡ Tổng EXP",
        value=f"**{total_exp} EXP** → +{total_exp} điểm cho cây",
        inline=False
    )
    
    embed.add_field(
        name="📋 Chi tiết",
        value=f"{fertilizer_count} × (50-100 EXP mỗi cái)",
        inline=False
    )
    
    embed.add_field(
        name="� Tiến độ Cây",
        value=f"**{percentage}%** ({tree_prog:,}/{tree_total:,} EXP)",
        inline=False
    )
    
    # Send result
    if is_slash:
        await ctx.followup.send(embed=embed)
    else:
        await ctx.reply(embed=embed)


async def view_collection_action(cog, ctx_or_interaction, user_id: int, username: str):
    """View fish collection.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        user_id: User ID to view collection for
        username: Username for display
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        await ctx_or_interaction.response.defer(ephemeral=False)
        ctx = ctx_or_interaction
    else:
        ctx = ctx_or_interaction
    
    # Get user's collection
    from ..helpers import get_collection
    collection = await get_collection(user_id)
    
    # Build collection display
    common_caught = []
    rare_caught = []
    legendary_caught = []
    
    for fish_key in collection.keys():
        if fish_key in COMMON_FISH_KEYS:
            fish_data = next((f for f in COMMON_FISH if f["key"] == fish_key), None)
            if fish_data:
                common_caught.append(f"{fish_data.get('emoji', '🐟')} {fish_data['name']}")
        elif fish_key in RARE_FISH_KEYS:
            fish_data = next((f for f in RARE_FISH if f["key"] == fish_key), None)
            if fish_data:
                rare_caught.append(f"{fish_data.get('emoji', '🐠')} {fish_data['name']}")
        elif fish_key in LEGENDARY_FISH_KEYS:
            fish_data = ALL_FISH.get(fish_key, {})
            legendary_caught.append(f"{fish_data.get('emoji', '🐋')} {fish_data.get('name', fish_key)}")
    
    # Calculate progress
    total_common = len(COMMON_FISH_KEYS)
    total_rare = len(RARE_FISH_KEYS)
    total_legendary = len(LEGENDARY_FISH_KEYS)
    total_fish = total_common + total_rare + total_legendary
    
    caught_count = len(common_caught) + len(rare_caught) + len(legendary_caught)
    progress_percent = int(caught_count / total_fish * 100) if total_fish > 0 else 0
    
    # Build embed
    embed = discord.Embed(
        title=f"📚 Bộ Sưu Tập Cá - {username}",
        description=f"**Tiến Độ:** {caught_count}/{total_fish} ({progress_percent}%)",
        color=discord.Color.blue()
    )
    
    # Common fish section
    common_text = ", ".join(common_caught) if common_caught else "Chưa có cá nào"
    embed.add_field(
        name=f"🐟 Cá Thường ({len(common_caught)}/{total_common})",
        value=common_text[:1024],  # Discord field limit
        inline=False
    )
    
    # Rare fish section
    rare_text = ", ".join(rare_caught) if rare_caught else "Chưa có cá hiếm nào"
    embed.add_field(
        name=f"🐠 Cá Hiếm ({len(rare_caught)}/{total_rare})",
        value=rare_text[:1024],
        inline=False
    )
    
    # Legendary fish section
    legendary_text = ", ".join(legendary_caught) if legendary_caught else "Chưa có cá huyền thoại nào"
    embed.add_field(
        name=f"🐋 Cá Huyền Thoại ({len(legendary_caught)}/{total_legendary})",
        value=legendary_text[:1024],
        inline=False
    )
    
    if is_slash:
        await ctx.followup.send(embed=embed)
    else:
        await ctx.reply(embed=embed)
    
    logger.info(f"[COLLECTION] Viewed collection for {username}: {caught_count}/{total_fish}")

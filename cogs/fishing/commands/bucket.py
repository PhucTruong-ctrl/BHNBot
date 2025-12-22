"""Bucket-related commands for fishing system.

Handles chest opening, trash recycling, fertilizer usage, and collection viewing.
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
    COMMON_FISH, RARE_FISH, FERTILIZER_EFFECTS
)
from ..mechanics.rod_system import get_rod_data
from ..mechanics.glitch import apply_display_glitch

logger = logging.getLogger("fishing")


async def open_chest_action(cog, ctx_or_interaction):
    """Open treasure chest logic.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        user_id = ctx_or_interaction.user.id
        user_name = ctx_or_interaction.user.name
    else:
        user_id = ctx_or_interaction.author.id
        user_name = ctx_or_interaction.author.name
    
    # *** CHECK AND APPLY LAG DEBUFF DELAY ***
    if cog.check_emotional_state(user_id, "lag"):
        await asyncio.sleep(3)
        logger.info(f"[EVENT] {user_name} experienced lag delay (3s) - open chest")
    
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
            await ctx.reply(msg)
        return
    
    # Remove chest from inventory
    await remove_item(user_id, "treasure_chest", 1)
    
    # Track chests opened for achievement
    try:
        await increment_stat(user_id, "fishing", "chests_opened", 1)
        current_opened = await get_stat(user_id, "fishing", "chests_opened")
        channel = ctx.channel if not is_slash else ctx_or_interaction.channel
        await cog.bot.achievement_manager.check_unlock(user_id, "fishing", "chests_opened", current_opened, channel)
    except Exception as e:
        logger.error(f"[ACHIEVEMENT] Error updating chests_opened for {user_id}: {e}")
    
    # Get rod level for luck calculation
    rod_level, _ = await get_rod_data(user_id)
    
    # Calculate item count based on rod level
    zero_chance = 0  # No more empty chests!
    one_chance = 60 - (rod_level - 1) * 5
    two_chance = 30 + (rod_level - 1) * 5
    three_chance = 10
    
    # Normalize to ensure sum = 100%
    total = zero_chance + one_chance + two_chance + three_chance
    if total > 0:
        zero_chance = int(zero_chance / total * 100)
        one_chance = int(one_chance / total * 100)
        two_chance = int(two_chance / total * 100)
        three_chance = 100 - zero_chance - one_chance - two_chance
    
    item_counts = [0, 1, 2, 3]
    weights = [zero_chance, one_chance, two_chance, three_chance]
    num_items = random.choices(item_counts, weights=weights, k=1)[0]
    
    logger.info(f"[CHEST] {user_name} (rod_level={rod_level}) rolled {num_items} items")
    
    # Roll items
    loot_items = []
    for _ in range(num_items):
        items = list(CHEST_LOOT.keys())
        loot_weights = list(CHEST_LOOT.values())
        loot_type = random.choices(items, weights=loot_weights, k=1)[0]
        loot_items.append(loot_type)
    
    # Process loot and build display
    loot_display = []
    trash_only = all(item in [t.get("key") for t in TRASH_ITEMS] for item in loot_items) and len(loot_items) == 1
    
    for loot_type in loot_items:
        if loot_type == "nothing":
            continue
        
        elif loot_type == "fertilizer":
            await cog.add_inventory_item(user_id, "fertilizer", "tool")
            loot_display.append("🌾 Phân Bón (Dùng `/bonphan` để nuôi cây)")
        
        elif loot_type == "puzzle_piece":
            pieces = ["puzzle_a", "puzzle_b", "puzzle_c", "puzzle_d"]
            piece = random.choice(pieces)
            await cog.add_inventory_item(user_id, piece, "tool")
            piece_display = piece.split("_")[1].upper()
            
            # Check if user now has all 4 pieces
            inventory = await get_inventory(user_id)
            has_all_pieces = all(inventory.get(f"puzzle_{p}", 0) > 0 for p in ["a", "b", "c", "d"])
            
            if has_all_pieces:
                await remove_item(user_id, "puzzle_a", 1)
                await remove_item(user_id, "puzzle_b", 1)
                await remove_item(user_id, "puzzle_c", 1)
                await remove_item(user_id, "puzzle_d", 1)
                
                reward = random.randint(5000, 10000)
                await add_seeds(user_id, reward)
                
                loot_display.append(f"🧩 Mảnh Ghép {piece_display} → 🎉 **ĐỦ 4 MẢNH - TỰ ĐỘNG GHÉP!** 💰 **{reward} Hạt!**")
            else:
                loot_display.append(f"🧩 Mảnh Ghép {piece_display} (Gom đủ 4 mảnh A-B-C-D để đổi quà siêu to!)")
        
        elif loot_type == "coin_pouch":
            coins = random.randint(100, 200)
            await add_seeds(user_id, coins)
            loot_display.append(f"💰 Túi Hạt - **{coins} Hạt**")
        
        elif loot_type in ["manh_sao_bang", "manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d"]:
            await cog.add_inventory_item(user_id, loot_type, "legendary_component")
            item_data = ALL_ITEMS_DATA.get(loot_type, {})
            item_id = item_data.get("name", loot_type)
            item_emoji = item_data.get("emoji", "❓")
            loot_display.append(f"{item_emoji} {item_id}")
        
        elif loot_type in [t.get("key") for t in TRASH_ITEMS]:
            trash_item = next((t for t in TRASH_ITEMS if t.get("key") == loot_type), None)
            if trash_item:
                await cog.add_inventory_item(user_id, loot_type, "trash")
                if trash_only:
                    trash_desc = trash_item.get('description', 'Unknown trash')
                    loot_display.append(f"{trash_item['emoji']} {apply_display_glitch(trash_item['name'])} - {apply_display_glitch(trash_desc)}")
                else:
                    loot_display.append(f"🗑️ {trash_item['name']}")
        
        else:  # gift_random
            gift = random.choice(GIFT_ITEMS)
            await cog.add_inventory_item(user_id, gift, "gift")
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
    
    # Find all trash items
    trash_keys = [t.get("key") for t in TRASH_ITEMS]
    user_trash = {k: v for k, v in inventory.items() if k in trash_keys and v > 0}
    
    if not user_trash:
        msg = "🪣 Bạn không có rác nào để tái chế!"
        if is_slash:
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    
    # Calculate recycle value (5 seeds per trash)
    total_trash = sum(user_trash.values())
    recycle_value = total_trash * 5
    
    # Remove all trash
    for trash_key, quantity in user_trash.items():
        await remove_item(user_id, trash_key, quantity)
    
    # Add seeds
    await add_seeds(user_id, recycle_value)
    
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
        description=f"**Đã tái chế {total_trash} món rác!**\n\n💰 Nhận được: **{recycle_value} Hạt**",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"👤 {user_name}")
    
    if is_slash:
        await ctx.followup.send(embed=embed)
    else:
        await ctx.reply(embed=embed)
    
    logger.info(f"[RECYCLE] {user_name} recycled {total_trash} trash for {recycle_value} seeds")


async def use_fertilizer_action(cog, ctx_or_interaction):
    """Use fertilizer on server tree.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_slash:
        user_id = ctx_or_interaction.user.id
        user_name = ctx_or_interaction.user.name
        guild_id = ctx_or_interaction.guild.id
        await ctx_or_interaction.response.defer(ephemeral=False)
        ctx = ctx_or_interaction
    else:
        user_id = ctx_or_interaction.author.id
        user_name = ctx_or_interaction.author.name
        guild_id = ctx_or_interaction.guild.id
        ctx = ctx_or_interaction
    
    # Check if user has fertilizer
    inventory = await get_inventory(user_id)
    if inventory.get("fertilizer", 0) <= 0:
        msg = "❌ Bạn không có Phân Bón! Mở rương để có cơ hội nhận được."
        if is_slash:
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    
    # Remove fertilizer
    await remove_item(user_id, "fertilizer", 1)
    
    # Apply random effect
    effect = random.choice(FERTILIZER_EFFECTS)
    effect_type = effect["type"]
    effect_value = effect.get("value", 0)
    effect_message = effect["message"]
    
    # Process effect
    if effect_type == "xp_boost":
        # Give tree XP boost (delegate to tree cog)
        tree_cog = cog.bot.get_cog("TreeCog")
        if tree_cog:
            try:
                await tree_cog.add_tree_xp(guild_id, effect_value)
                logger.info(f"[FERTILIZER] {user_name} gave {effect_value} XP to server tree")
            except Exception as e:
                logger.error(f"[FERTILIZER] Error adding tree XP: {e}")
    
    elif effect_type == "seeds":
        await add_seeds(user_id, effect_value)
        logger.info(f"[FERTILIZER] {user_name} received {effect_value} seeds")
    
    elif effect_type == "worm":
        await add_item(user_id, "worm", effect_value)
        logger.info(f"[FERTILIZER] {user_name} received {effect_value} worms")
    
    # Build embed
    embed = discord.Embed(
        title="🌾 Bón Phân",
        description=effect_message,
        color=discord.Color.green()
    )
    embed.set_footer(text=f"👤 {user_name}")
    
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

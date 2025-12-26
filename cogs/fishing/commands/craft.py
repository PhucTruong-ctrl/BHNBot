"""Crafting commands for legendary fish summoning.

Handles sacrifice (hiente), crafting (chetao), frequency detection (dosong),
and map assembly (ghepbando) for legendary fish quests.
"""
import logging
import asyncio
import random
import time
import discord

from database_manager import (
    get_inventory, add_item, remove_item, add_seeds,
    get_fish_count, get_stat, increment_stat
)
from ..constants import (
    COMMON_FISH_KEYS, RARE_FISH_KEYS, ALL_FISH,
    LEGENDARY_FISH_KEYS, ALL_ITEMS_DATA
)
from ..mechanics.legendary_quest_helper import (
    increment_sacrifice_count, get_sacrifice_count, reset_sacrifice_count,
    set_crafted_bait_status, get_crafted_bait_status,
    get_manh_sao_bang_count, set_manh_sao_bang_count,
    get_map_pieces_count, set_map_pieces_count
)
from ..utils.helpers import (
    get_user_info, send_followup, 
    create_fishing_embed, create_error_embed, create_success_embed
)

logger = logging.getLogger("fishing")


async def hiente_action(cog, ctx_or_interaction, fish_key: str, is_slash: bool):
    """Sacrifice fish to Thuồng Luồng.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        fish_key: Key of fish to sacrifice
        is_slash: Whether this is a slash command
    """
    is_slash_cmd = is_slash
    user_id, username = get_user_info(ctx_or_interaction, is_slash)
    channel = ctx_or_interaction.channel
    guild_id = ctx_or_interaction.guild.id
    
    # Check lag debuff
    if await cog.check_emotional_state(user_id, "lag"):
        await asyncio.sleep(3)
        username = ctx_or_interaction.user.name if is_slash_cmd else ctx_or_interaction.author.name
        logger.info(f"[EVENT] {username} experienced lag delay (3s) - sacrifice fish")
    
    if is_slash_cmd:
        await ctx_or_interaction.response.defer()
    
    # Check if user already has Thuồng Luồng
    try:
        count = await get_fish_count(user_id, 'thuong_luong')
        if count > 0:
            embed = discord.Embed(
                title="🌊 DÒNG SÔNG TỪ CHỐI!",
                description="Mặt nước tĩnh lặng... Bóng ma dưới đáy sông đã chấp nhận bạn là chủ nhân rồi.",
                color=discord.Color.gold()
            )
            if is_slash_cmd:
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.reply(embed=embed)
            return
    except Exception as e:
        logger.error(f"[HIENTE] Error checking thuong_luong ownership: {e}")
    
    # Check if fish_key is valid
    if fish_key not in COMMON_FISH_KEYS + RARE_FISH_KEYS:
        embed = discord.Embed(
            title="❌ Loại Cá Không Hợp Lệ",
            description=f"Chỉ có thể hiến tế cá thường hoặc hiếm. Không tìm thấy: `{fish_key}`",
            color=discord.Color.red()
        )
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)
        return
    
    # Check inventory
    inventory = await get_inventory(user_id)
    if inventory.get(fish_key, 0) <= 0:
        fish_name = ALL_FISH.get(fish_key, {}).get("name", fish_key)
        embed = discord.Embed(
            title="❌ Không Đủ Cá",
            description=f"Bạn không có **{fish_name}** để hiến tế!",
            color=discord.Color.red()
        )
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)
        return
    
    # Remove fish and add sacrifice count
    await remove_item(user_id, fish_key, 1)
    current_count = await increment_sacrifice_count(user_id, 1, "thuong_luong")
    
    # Start timer if first sacrifice
    if current_count == 1:
        cog.thuong_luong_timers[user_id] = time.time()
    
    fish_name = ALL_FISH.get(fish_key, {}).get("name", fish_key)
    fish_emoji = ALL_FISH.get(fish_key, {}).get("emoji", "🐟")
    
    if current_count >= 3:
        # Ready to spawn!
        embed = discord.Embed(
            title="🌊 LỄ HIẾN TẾ HOÀN TẤT!",
            description=f"Bạn đã hiến tế **{current_count}/3** cá.\n\n🌊 Mặt nước bắt đầu sủi bọt... Thuồng Luồng đang lắng nghe!\n\n**Hãy câu cá liên tục trong 5 phút để triệu hồi Thuồng Luồng!**",
            color=discord.Color.dark_blue()
        )
    else:
        embed = discord.Embed(
            title=f"{fish_emoji} Hiến Tế Thành Công!",
            description=f"Đã thả **{fish_name}** xuống dòng sông đen.\n\n📊 Tiến độ: **{current_count}/3** cá",
            color=discord.Color.blue()
        )
    
    if is_slash_cmd:
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.reply(embed=embed)
    
    logger.info(f"[HIENTE] {user_id} sacrificed {fish_key}, count: {current_count}/3")


async def chetao_action(cog, ctx_or_interaction, item_key: str, is_slash: bool):
    """Craft legendary items.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        item_key: Key of item to craft
        is_slash: Whether this is a slash command
    """
    is_slash_cmd = is_slash
    
    if is_slash_cmd:
        user_id = ctx_or_interaction.user.id
        await ctx_or_interaction.response.defer()
    else:
        user_id = ctx_or_interaction.author.id
    
    # Check lag debuff
    if cog.check_emotional_state(user_id, "lag"):
        await asyncio.sleep(3)
        logger.info(f"[CRAFT] {user_id} experienced lag delay (3s)")
    
    # Get inventory
    inventory = await get_inventory(user_id)
    
    # Define craftable items
    craftable_items = {
        "tinh_cau": {
            "name": "Tinh Cầu",
            "requires": {"manh_sao_bang": 5, "ngoc_trai": 1},
            "description": "Thả xuống nước để triệu hồi Cá Ngân Hà"
        },
        "long_vu_lua": {
            "name": "Lông Vũ Lửa",
            "requires": {"long_phuong_hoang": 3},
            "description": "Dùng để triệu hồi Cá Phượng Hoàng"
        },
        "ban_do_ham_am": {
            "name": "Bản Đồ Hầm Ám",
            "requires": {"manh_ban_do_a": 1, "manh_ban_do_b": 1, "manh_ban_do_c": 1, "manh_ban_do_d": 1},
            "description": "Mở cổng tới vực sâu Cthulhu"
        }
    }
    
    if item_key not in craftable_items:
        items_list = "\n".join([f"• `{k}`: {v['name']}" for k, v in craftable_items.items()])
        embed = discord.Embed(
            title="❌ Vật Phẩm Không Hợp Lệ",
            description=f"Các vật phẩm có thể chế tạo:\n{items_list}",
            color=discord.Color.red()
        )
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)
        return
    
    craft_info = craftable_items[item_key]
    
    # Check requirements
    missing = []
    for req_item, req_count in craft_info["requires"].items():
        if inventory.get(req_item, 0) < req_count:
            item_name = ALL_ITEMS_DATA.get(req_item, {}).get("name", req_item)
            missing.append(f"• {item_name}: {inventory.get(req_item, 0)}/{req_count}")
    
    if missing:
        missing_text = "\n".join(missing)
        embed = discord.Embed(
            title=f"❌ Thiếu Nguyên Liệu",
            description=f"Để chế tạo **{craft_info['name']}**, bạn cần:\n{missing_text}",
            color=discord.Color.red()
        )
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)
        return
    
    # Craft the item
    for req_item, req_count in craft_info["requires"].items():
        await remove_item(user_id, req_item, req_count)
    
    await add_item(user_id, item_key, 1)
    
    embed = discord.Embed(
        title="✨ Chế Tạo Thành Công!",
        description=f"Bạn đã chế tạo được **{craft_info['name']}**!\n\n{craft_info['description']}",
        color=discord.Color.gold()
    )
    
    if is_slash_cmd:
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.reply(embed=embed)
    
    logger.info(f"[CRAFT] {user_id} crafted {item_key}")


async def dosong_action(cog, ctx_or_interaction, is_slash: bool):
    """Use frequency detector to find Ca Voi 52Hz.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        is_slash: Whether this is a slash command
    """
    is_slash_cmd = is_slash
    
    if is_slash_cmd:
        user_id = ctx_or_interaction.user.id
        await ctx_or_interaction.response.defer()
    else:
        user_id = ctx_or_interaction.author.id
    
    # Check if user has frequency detector
    inventory = await get_inventory(user_id)
    if inventory.get("may_do_song", 0) <= 0:
        embed = discord.Embed(
            title="❌ Không Có Máy Dò Sóng",
            description="Bạn cần **Máy Dò Sóng 52Hz** để sử dụng tính năng này!",
            color=discord.Color.red()
        )
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)
        return
    
    # Use the detector
    await remove_item(user_id, "may_do_song", 1)
    
    # Set detection flag via consumable cog
    consumable_cog = cog.bot.get_cog("ConsumableCog")
    if consumable_cog:
        consumable_cog.set_52hz_signal(user_id)
    
    embed = discord.Embed(
        title="📻 Máy Dò Sóng Kích Hoạt!",
        description="🔊 *Bíp... bíp... bíp...*\n\n🐋 Tín hiệu 52Hz đã được phát hiện!\n\n**Hãy câu cá ngay để bắt Cá Voi 52Hz!**",
        color=discord.Color.blue()
    )
    
    if is_slash_cmd:
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.reply(embed=embed)
    
    logger.info(f"[DOSONG] {user_id} activated 52Hz detector")


async def ghepbando_action(cog, ctx_or_interaction, is_slash: bool):
    """Assemble map pieces for Cthulhu summoning.
    
    Args:
        cog: The FishingCog instance
        ctx_or_interaction: Command context or interaction
        is_slash: Whether this is a slash command
    """
    is_slash_cmd = is_slash
    
    if is_slash_cmd:
        user_id = ctx_or_interaction.user.id
        await ctx_or_interaction.response.defer()
    else:
        user_id = ctx_or_interaction.author.id
    
    # Check inventory for map pieces
    inventory = await get_inventory(user_id)
    
    pieces = ["manh_ban_do_a", "manh_ban_do_b", "manh_ban_do_c", "manh_ban_do_d"]
    has_all = all(inventory.get(p, 0) > 0 for p in pieces)
    
    if not has_all:
        missing = [p for p in pieces if inventory.get(p, 0) <= 0]
        missing_names = [ALL_ITEMS_DATA.get(p, {}).get("name", p) for p in missing]
        embed = discord.Embed(
            title="❌ Thiếu Mảnh Bản Đồ",
            description=f"Bạn cần đủ 4 mảnh bản đồ A-B-C-D.\n\nCòn thiếu: {', '.join(missing_names)}",
            color=discord.Color.red()
        )
        if is_slash_cmd:
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)
        return
    
    # Remove pieces and create map
    for piece in pieces:
        await remove_item(user_id, piece, 1)
    
    await add_item(user_id, "ban_do_ham_am", 1)
    
    # Activate dark map for 10 casts (with lock protection to prevent race condition)
    # Initialize lock if not exists
    if user_id not in cog.user_locks:
        cog.user_locks[user_id] = asyncio.Lock()
    
    async with cog.user_locks[user_id]:
        cog.dark_map_active[user_id] = True
        cog.dark_map_casts[user_id] = 10
        cog.dark_map_cast_count[user_id] = 0
    
    embed = discord.Embed(
        title="🗺️ BẢN ĐỒ HẦM ÁM HOÀN THÀNH!",
        description="Bốn mảnh bản đồ ghép lại... Một cổng tối mở ra!\n\n🦑 **Cthulhu Non đang chờ đợi...**\n\n⏳ Bạn có **10 lần câu** để bắt nó!",
        color=discord.Color.dark_purple()
    )
    
    if is_slash_cmd:
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.reply(embed=embed)
    
    logger.info(f"[MAP] {user_id} assembled dark map, 10 casts to catch Cthulhu")

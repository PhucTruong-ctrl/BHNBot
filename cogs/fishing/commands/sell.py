"""
NUCLEAR REWRITE: Sell Fish Command
Strict ACID Transaction - Zero Tolerance for Ghost Items
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from core.logger import setup_logger
from database_manager import db_manager

logger = setup_logger("SellCommand", "cogs/fishing/fishing.log")


async def sell_fish_action(cog, ctx_or_interaction, fish_types: Optional[str] = None):
    """
    Sell fish with STRICT ACID transaction.
    
    Flow:
    1. Validate input
    2. START TRANSACTION
    3. DEDUCT FISH (CRITICAL - must succeed or rollback ALL)
    4. ADD MONEY (only if step 3 succeeds)
    5. COMMIT
    6. Update cache
    7. Send invoice UI
    
    Args:
        cog: FishingCog instance
        ctx_or_interaction: Command context or interaction
        fish_types: Optional comma-separated fish types to sell
    """
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user_id = ctx_or_interaction.user.id if is_slash else ctx_or_interaction.author.id
    username = ctx_or_interaction.user.name if is_slash else ctx_or_interaction.author.name
    
    logger.info(f"[SELL] [ENTRY] User {username} ({user_id}) selling fish_types={fish_types}")
    
    # ===== STEP 1: VALIDATION =====
    # Get all fish from inventory
    try:
        logger.info(f"[SELL] Fetching inventory for user {user_id}")
        rows = await db_manager.fetchall(
            "SELECT item_id, quantity FROM inventory WHERE user_id = $1 AND item_type = 'fish' AND quantity > 0",
            (user_id,)
        )
        logger.info(f"[SELL] Found {len(rows) if rows else 0} fish items in inventory")
    except Exception as e:
        logger.error(f"[SELL] DB error fetching inventory: {e}", exc_info=True)
        msg = "❌ Lỗi hệ thống khi kiểm tra túi đồ!"
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    if not rows:
        msg = "🪣 Bạn không có cá nào để bán!"
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    # Build fish inventory dict
    logger.info(f"[SELL] Building inventory dict from {len(rows)} rows")
    try:
        fish_inventory = {}
        for row in rows:
            # asyncpg returns Record objects - access by index or dict conversion
            item_id = row[0] if isinstance(row, (list, tuple)) else row['item_id']
            quantity = row[1] if isinstance(row, (list, tuple)) else row['quantity']
            fish_inventory[item_id] = quantity
            logger.info(f"[SELL] Added {item_id}: {quantity}")
        logger.info(f"[SELL] Fish inventory: {list(fish_inventory.keys())}")
    except Exception as e:
        logger.error(f"[SELL] Error building inventory dict: {e}", exc_info=True)
        msg = "❌ Lỗi khi xử lý dữ liệu túi đồ!"
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    # Load fish data (prices) - DIRECT from JSON file
    try:
        import json
        import os
        logger.info(f"[SELL] Loading fish data from JSON file")
        
        # Try multiple possible paths
        possible_paths = [
            "/home/phuctruong/BHNBot/data/fishing_data.json",
            "/home/phuctruong/BHNBot/cogs/fishing/data/fishing_data.json",
            os.path.join(os.path.dirname(__file__), "../data/fishing_data.json"),
        ]
        
        fish_data = {}
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
                # Parse nested structure: {"fishing_data": {"fish": [...]}}
                if "fishing_data" in raw_data and "fish" in raw_data["fishing_data"]:
                    fish_list = raw_data["fishing_data"]["fish"]
                    # Convert array to dict keyed by fish 'key'
                    fish_data = {fish['key']: fish for fish in fish_list if 'key' in fish}
                    logger.info(f"[SELL] Loaded {len(fish_data)} fish from {path}")
                else:
                    logger.error(f"[SELL] Invalid JSON structure in {path}")
                break
        
        if not fish_data:
            raise FileNotFoundError("Could not find or parse fishing_data.json")
            
    except Exception as e:
        logger.error(f"[SELL] Failed to load fish data: {e}", exc_info=True)
        msg = "❌ Lỗi hệ thống khi load dữ liệu cá!"
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    # Filter sellable fish (exclude legendary)
    legendary_types = ['legendary', 'mythic']
    fish_to_sell = {}
    
    for fish_id, qty in fish_inventory.items():
        fish_info = fish_data.get(fish_id, {})
        if fish_info.get('rarity') in legendary_types:
            continue  # Skip legendary fish
        
        sell_price = fish_info.get('sell_price', 0)
        if sell_price <= 0:
            continue  # Skip unsellable items
        
        fish_to_sell[fish_id] = {
            'quantity': qty,
            'price': sell_price,
            'name': fish_info.get('name', fish_id)
        }
    
    # Filter by requested types if specified
    if fish_types:
        requested = [t.strip().lower() for t in fish_types.split(',')]
        fish_to_sell = {k: v for k, v in fish_to_sell.items() if k in requested}
        
        if not fish_to_sell:
            msg = f"❌ Bạn không có cá loại **{fish_types}** để bán!"
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.reply(msg)
            return
    
    if not fish_to_sell:
        msg = "🪣 Bạn không có cá nào để bán!"
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    # Calculate total value
    total_value = sum(item['quantity'] * item['price'] for item in fish_to_sell.values())
    
    logger.info(f"[SELL] User {user_id} selling {len(fish_to_sell)} fish types for {total_value} seeds")
    
    # ===== STEP 2-5: ATOMIC TRANSACTION =====
    try:
        async with db_manager.transaction() as conn:
            # STEP 3: DEDUCT FISH (CRITICAL)
            for fish_id, item_data in fish_to_sell.items():
                qty_to_sell = item_data['quantity']
                
                # Try to deduct - MUST return a row or transaction fails
                result = await conn.fetchrow(
                    """
                    UPDATE inventory
                    SET quantity = quantity - $1
                    WHERE user_id = $2 AND item_id = $3 AND quantity >= $1
                    RETURNING quantity
                    """,
                    (qty_to_sell, user_id, fish_id)
                )
                
                if result is None:
                    # CRITICAL FAILURE: Item not found or insufficient quantity
                    raise ValueError(f"Không đủ cá {fish_id}! (Cần {qty_to_sell}, database không tìm thấy)")
                
                logger.info(f"[SELL] Deducted {qty_to_sell}x {fish_id} from user {user_id}, remaining={result['quantity']}")
                
                # Auto-delete if quantity reached 0
                if result['quantity'] <= 0:
                    await conn.execute(
                        "DELETE FROM inventory WHERE user_id = $1 AND item_id = $2",
                        (user_id, fish_id)
                    )
                    logger.info(f"[SELL] Deleted depleted item {fish_id} for user {user_id}")
            
            # STEP 4: ADD MONEY (only if step 3 succeeded)
            await conn.execute(
                "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                (total_value, user_id)
            )
            
            # Transaction log
            await conn.execute(
                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                (user_id, total_value, 'sell_fish', 'fishing')
            )
            
            logger.info(f"[SELL] Added {total_value} seeds to user {user_id}")
        
        # STEP 5: Transaction auto-commits here
        logger.info(f"[SELL] [SUCCESS] Transaction committed for user {user_id}")
        
    except ValueError as ve:
        # User-friendly error (insufficient items)
        logger.warning(f"[SELL] [ROLLBACK] {ve}")
        msg = f"❌ **Giao dịch thất bại!**\n{ve}\n\n_Có thể bạn đã bán số cá này ở lệnh khác._"
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
        
    except Exception as e:
        # System error
        logger.error(f"[SELL] [ROLLBACK] System error: {e}", exc_info=True)
        msg = "❌ Lỗi hệ thống! Transaction đã được rollback để bảo vệ dữ liệu."
        if is_slash:
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    # ===== STEP 6: INVALIDATE CACHE =====
    # Clear cache to ensure next read gets fresh data
    try:
        if hasattr(cog.bot, 'inventory'):
            await cog.bot.inventory.invalidate(user_id)
            logger.info(f"[SELL] Invalidated inventory cache for {user_id}")
    except Exception as e:
        logger.warning(f"[SELL] Failed to invalidate cache: {e}")
    
    # ===== STEP 7: SEND INVOICE UI =====
    # Build invoice embed
    embed = discord.Embed(
        title=f"🏪 SẠP CÁ {username.upper()} - HÓA ĐƠN",
        description=f"📍 **Địa điểm:** Chợ Cá Bên Hiên Nhà\n⏰ **Thời gian:** <t:{int(discord.utils.utcnow().timestamp())}:f>",
        color=discord.Color.green()
    )
    
    # Item details
    details = ""
    for fish_id, item_data in fish_to_sell.items():
        emoji = fish_data.get(fish_id, {}).get('emoji', '🐟')
        name = item_data['name']
        qty = item_data['quantity']
        price = item_data['price']
        line_total = qty * price
        details += f"{emoji} **{name}** x{qty} = {line_total} Hạt\n"
    
    embed.add_field(name="📋 Chi Tiết Đơn Hàng", value=details, inline=False)
    embed.add_field(name="📊 Tổng Kết", value=f"💵 **Tổng Gốc:** {total_value} Hạt", inline=False)
    embed.add_field(name="🏁 TỔNG NHẬN", value=f"# +{total_value} Hạt", inline=False)
    embed.set_footer(text="Cảm ơn quý khách đã ủng hộ sạp cá! 🐟💸")
    
    if is_slash:
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.reply(embed=embed)
    
    logger.info(f"[SELL] [COMPLETE] Invoice sent to user {user_id}")


# Export for use in cog
_sell_fish_impl = sell_fish_action  # Alias for backward compatibility

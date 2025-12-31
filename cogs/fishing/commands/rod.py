
import logging
import discord
from database_manager import db_manager, get_user_balance, add_seeds, increment_stat, get_stat
from ..constants import ROD_LEVELS
from ..mechanics.rod_system import get_rod_data, update_rod_data
from core.utils import format_currency

logger = logging.getLogger("FishingCog")


async def nangcap_action(ctx_or_interaction):
    """Handles the rod upgrade command."""
    
    # Identify user and context
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        reply = ctx_or_interaction.response.send_message
    else:
        user = ctx_or_interaction.author
        reply = ctx_or_interaction.reply

    user_id = user.id
    # Get bot instance
    bot = ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot
    logger.info(f"[ROD] User {user.name} ({user_id}) initiated upgrade.")

    try:
        # Get current rod status (READ-ONLY PRE-CHECK)
        current_level, current_durability = await get_rod_data(user_id)
        
        # Check if max level
        next_level = current_level + 1
        if next_level not in ROD_LEVELS:
            msg = f"🎣 **{user.name}**, cần câu của bạn đã đạt cấp tối đa (**{ROD_LEVELS[current_level]['name']}**)!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await reply(msg, ephemeral=True)
            else:
                await reply(msg)
            return

        # Get upgrade cost
        next_rod_info = ROD_LEVELS[next_level]
        cost = next_rod_info['cost']
        material_cost = next_rod_info.get('material', 0)
        special_materials = next_rod_info.get('special_materials', {})
        special_requirement = next_rod_info.get('special_requirement', None)
        
        # ==================== SPECIAL REQUIREMENT CHECK (Level 7 - Chrono Rod) ====================
        if special_requirement:
            # Check if user has caught the legendary fish
            quest_row = await db_manager.fetchrow(
                "SELECT legendary_caught FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
                (user_id, special_requirement)
            )
            
            if not quest_row or not quest_row['legendary_caught']:
                # Show special requirement message
                fish_name_map = {
                    "ca_ngan_ha": "Cá Ngân Hà 🌌"
                }
                fish_name = fish_name_map.get(special_requirement, special_requirement)
                
                lore = next_rod_info.get('lore', '')
                embed = discord.Embed(
                    title="⏳ Yêu Cầu Đặc Biệt",
                    description=f"Để nâng lên **{next_rod_info['name']}** {next_rod_info['emoji']}, bạn phải từng bắt được **{fish_name}**!\n\n"
                               f"*{lore}*",
                    color=discord.Color.purple()
                )
                
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await reply(embed=embed, ephemeral=True)
                else:
                    await reply(embed=embed)
                return
        
        # ==================== ACID TRANSACTION ====================
        try:
            async with db_manager.transaction() as conn:
                # 1. Check Balance in DB (Atomically)
                cursor = await conn.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                balance = row[0] if row else 0
                
                if balance < cost:
                    raise ValueError(f"Không đủ tiền! Cần **{format_currency(cost)}**, có **{format_currency(balance)}**")

                # 2. Check & Deduct Materials
                if material_cost > 0:
                    mat_row = await conn.fetchrow("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, "vat_lieu_nang_cap"))
                    curr_mat = mat_row[0] if mat_row else 0 # Index 0 for fetchrow returning tuple
                    
                    if curr_mat < material_cost:
                        raise ValueError(f"Thiếu vật liệu nâng cấp! Cần **{material_cost}**, có **{curr_mat}**")
                    
                    # Deduct
                    await conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?", (material_cost, user_id, "vat_lieu_nang_cap"))
                    await conn.execute("DELETE FROM inventory WHERE user_id = ? AND collection_qty <= 0", (user_id,)) # Cleanup if needed, but 'quantity' is the col in inventory table? 
                    # WAIT: The table is 'inventory'. Column is 'quantity'.
                    await conn.execute("DELETE FROM inventory WHERE user_id = ? AND quantity <= 0 AND item_id = ?", (user_id, "vat_lieu_nang_cap"))

                # 3. Check & Deduct Special Materials
                if special_materials:
                    for mat_key, mat_req in special_materials.items():
                        sm_row = await conn.fetchrow("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, mat_key))
                        curr_sm = sm_row[0] if sm_row else 0
                        
                        if curr_sm < mat_req:
                             mat_name = {"manh_sao_bang": "Mảnh Sao Băng ✨"}.get(mat_key, mat_key)
                             raise ValueError(f"Thiếu **{mat_name}**! Cần **{mat_req}**, có **{curr_sm}**")
                        
                        await conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?", (mat_req, user_id, mat_key))
                        await conn.execute("DELETE FROM inventory WHERE user_id = ? AND quantity <= 0 AND item_id = ?", (user_id, mat_key))

                # 4. Deduct Money
                await conn.execute("UPDATE users SET seeds = seeds - ? WHERE user_id = ?", (cost, user_id))
                
                # 5. Update Rod
                new_durability = next_rod_info['durability'] # Reset durable
                await conn.execute("UPDATE fishing_profiles SET rod_level = ?, rod_durability = ? WHERE user_id = ?", (next_level, new_durability, user_id))
                
                # 6. Log Transaction
                await conn.execute("INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)", (user_id, -cost, f"upgrade_rod_{next_level}", "maintenance"))
                
                # Transaction Auto-Commits here
        
        except ValueError as ve:
             # User error (not enough materials/money)
             if isinstance(ctx_or_interaction, discord.Interaction):
                 await reply(f"⚠️ {ve}", ephemeral=True)
             else:
                 await reply(f"⚠️ {ve}")
             return
             
        except Exception as e:
            # System error
            logger.error(f"[ROD] Upgrade Transaction Failed: {e}", exc_info=True)
            msg = "❌ Lỗi hệ thống khi nâng cấp! Giao dịch đã được hủy."
            if isinstance(ctx_or_interaction, discord.Interaction):
                 await reply(msg, ephemeral=True)
            else:
                 await reply(msg)
            return

        # ==================== POST-TRANSACTION (Updates & UI) ====================
        
        # Invalidate inventory cache
        try:
             if hasattr(bot, 'inventory'):
                 await bot.inventory.invalidate(user_id)
        except Exception:
             pass

        # Update stats
        await increment_stat(user_id, "fishing", "rod_upgrades", 1)
        
        if next_level in [5, 7]:
            await increment_stat(user_id, "fishing", "rod_level_max", next_level)
            
        # ==================== SPECIAL LORE MESSAGE (Level 7 - Chrono Rod) ====================
        if next_level == 7:
            lore_embed = discord.Embed(
                title="⏳ Nghi Thức Thời Gian",
                description="Cá Ngân Hà xuất hiện từ hư không, ánh sáng thiên hà bao phủ cần câu của bạn...\n\n"
                           f"*Cần câu rung chuyển, thời gian như ngưng trệ...*\n\n"
                           f"✨ **{next_rod_info['name']}** đã được kích hoạt!",
                color=discord.Color.from_rgb(138, 43, 226)
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await reply(embed=lore_embed)
            else:
                await reply(embed=lore_embed)
            
            # Wait before showing success message
            import asyncio
            await asyncio.sleep(2)
        
        # Success Message
        material_text = f"\n⚙️ Vật liệu: **{material_cost}**" if material_cost > 0 else ""
        special_text = ""
        if special_materials:
            for mat_key, mat_count in special_materials.items():
                mat_name = {
                    "manh_sao_bang": "Mảnh Sao Băng ✨"
                }.get(mat_key, mat_key)
                special_text += f"\n{mat_name}: **{mat_count}**"
        
        msg = (f"🎉 **CHÚC MỪNG!** {user.mention} đã nâng cấp thành công!\n"
               f"🎣 **{ROD_LEVELS[current_level]['name']}** ➔ **{next_rod_info['name']}** {next_rod_info['emoji']}\n"
               f"💸 Chi phí: **{format_currency(cost)}**{material_text}{special_text}\n"
               f"⚡ Độ bền mới: **{new_durability}/{new_durability}**")
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg) if ctx_or_interaction.response.is_done() else await reply(msg)
        else:
            await reply(msg)
        
        logger.info(f"[ROD] {user.name} (ID: {user_id}) upgraded rod to level {next_level} (Cost: {cost}, Materials: {material_cost})")
            
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        logger.error(f"[ROD] Rod Upgrade failed for {user_id}: {e}\n{traceback_str}")
        error_msg = f"❌ Có lỗi xảy ra trong quá trình nâng cấp: {e}"
        try:
            if isinstance(ctx_or_interaction, discord.Interaction):
                await reply(error_msg, ephemeral=True)
            else:
                await reply(error_msg)
        except:
            pass

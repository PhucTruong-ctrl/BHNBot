
import logging
import logging
import discord
from database_manager import db_manager, get_user_balance, add_seeds, get_inventory, remove_item
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
    logger.info(f"[ROD] User {user.name} ({user_id}) initiated upgrade.")

    try:
        # Get current rod status
        current_level, current_durability = await get_rod_data(user_id)
        logger.info(f"[ROD] {user.name} - Level: {current_level}, Durability: {current_durability}")
        
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
        logger.info(f"[ROD] {user.name} - Next Level: {next_level}, Cost: {cost}, Material: {material_cost}, Special: {special_materials}")
        
        # ==================== SPECIAL REQUIREMENT CHECK (Level 7 - Chrono Rod) ====================
        if special_requirement:
            # Check if user has caught the legendary fish
            legendary_quest = await db_manager.execute(
                "SELECT legendary_caught FROM legendary_quests WHERE user_id = ? AND fish_key = ?",
                (user_id, special_requirement)
            )
            
            if not legendary_quest or not legendary_quest[0][0]:
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
        
        # Fetch data for validation
        balance = await get_user_balance(user_id)
        current_materials = 0
        if material_cost > 0:
            inventory = await get_inventory(user_id)
            current_materials = inventory.get("vat_lieu_nang_cap", 0)
        
        # Check special materials (Level 6 - Void Rod)
        special_material_ok = True
        special_material_msg = ""
        if special_materials:
            inventory = await get_inventory(user_id)
            for mat_key, mat_count in special_materials.items():
                user_mat = inventory.get(mat_key, 0)
                if user_mat < mat_count:
                    special_material_ok = False
                    mat_name = {
                        "manh_sao_bang": "Mảnh Sao Băng ✨"
                    }.get(mat_key, mat_key)
                    special_material_msg += f"❌ **{mat_name}**: {user_mat} / {mat_count}\n"
                else:
                    mat_name = {
                        "manh_sao_bang": "Mảnh Sao Băng ✨"
                    }.get(mat_key, mat_key)
                    special_material_msg += f"✅ **{mat_name}**: {user_mat} / {mat_count}\n"
            
        logger.info(f"[ROD] {user.name} - Balance: {balance}, Materials: {current_materials}, Special Materials OK: {special_material_ok}")

        # Check sufficiency
        is_money_enough = balance >= cost
        is_material_enough = current_materials >= material_cost
        
        if not is_money_enough or not is_material_enough or not special_material_ok:
            money_icon = "✅" if is_money_enough else "❌"
            material_icon = "✅" if is_material_enough else "❌"
            
            msg = (f"⚠️ **{user.name}**, bạn chưa đủ điều kiện nâng cấp!\n"
                   f"{money_icon} **Tiền**: {format_currency(balance)} / {format_currency(cost)}\n")
            
            if material_cost > 0:
                msg += f"{material_icon} **Vật liệu**: {current_materials} / {material_cost} ⚙️\n"
            
            if special_materials:
                msg += special_material_msg
            
            # Send error message with auto-delete
            if isinstance(ctx_or_interaction, discord.Interaction):
                await reply(msg, ephemeral=True)
            else:
                await reply(msg, delete_after=15)
            return

        # Process Upgrade (Transaction)
        # 1. Deduct Money
        await add_seeds(user_id, -cost)
        
        # 2. Deduct Materials (if required)
        if material_cost > 0:
            await remove_item(user_id, "vat_lieu_nang_cap", material_cost)
        
        # 3. Deduct Special Materials (Level 6 - Void Rod)
        if special_materials:
            for mat_key, mat_count in special_materials.items():
                await remove_item(user_id, mat_key, mat_count)
                logger.info(f"[ROD] {user.name} used {mat_count}x {mat_key} for upgrade")
        
        # 4. Update Rod
        # Reset durability to max of new level
        new_durability = next_rod_info['durability']
        await update_rod_data(user_id, new_durability, next_level)
        
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
            await reply(msg)
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

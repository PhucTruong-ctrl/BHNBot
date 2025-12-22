
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
        logger.info(f"[ROD] {user.name} - Next Level: {next_level}, Cost: {cost}, Material: {material_cost}")
        
        # Fetch data for validation
        balance = await get_user_balance(user_id)
        current_materials = 0
        if material_cost > 0:
            inventory = await get_inventory(user_id)
            current_materials = inventory.get("rod_material", 0)
            
        logger.info(f"[ROD] {user.name} - Balance: {balance}, Materials: {current_materials}")

        # Check sufficiency
        is_money_enough = balance >= cost
        is_material_enough = current_materials >= material_cost
        
        if not is_money_enough or not is_material_enough:
            money_icon = "✅" if is_money_enough else "❌"
            material_icon = "✅" if is_material_enough else "❌"
            
            msg = (f"⚠️ **{user.name}**, bạn chưa đủ điều kiện nâng cấp!\n"
                   f"{money_icon} **Tiền**: {format_currency(balance)} / {format_currency(cost)}\n")
            
            if material_cost > 0:
                msg += f"{material_icon} **Vật liệu**: {current_materials} / {material_cost} ⚙️\n"
            
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
            await remove_item(user_id, "rod_material", material_cost)
        
        # 3. Update Rod
        # Reset durability to max of new level
        new_durability = next_rod_info['durability']
        await update_rod_data(user_id, new_durability, next_level)
        
        # Success Message
        material_text = f"\n⚙️ Vật liệu: **{material_cost}**" if material_cost > 0 else ""
        msg = (f"🎉 **CHÚC MỪNG!** {user.mention} đã nâng cấp thành công!\n"
               f"🎣 **{ROD_LEVELS[current_level]['name']}** ➔ **{next_rod_info['name']}** {next_rod_info['emoji']}\n"
               f"💸 Chi phí: **{format_currency(cost)}**{material_text}\n"
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

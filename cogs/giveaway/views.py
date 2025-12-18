import discord
import json
from database_manager import db_manager, add_seeds
from .helpers import check_requirements
from .constants import *

class GiveawayJoinView(discord.ui.View):
    def __init__(self, giveaway_id: int, requirements: str):
        super().__init__(timeout=None) # Persistent view
        self.giveaway_id = giveaway_id
        self.reqs = json.loads(requirements) if isinstance(requirements, str) else requirements
        
        # Update custom_id to be unique per giveaway
        # Assuming the button is the first item (index 0)
        self.children[0].custom_id = f"ga_join:{giveaway_id}"

    @discord.ui.button(label="🎉 Tham Gia", style=discord.ButtonStyle.primary, custom_id="ga_join_btn") # custom_id here is placeholder
    async def join_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        
        # 1. Check if already joined
        existing = await db_manager.fetchone(
            "SELECT 1 FROM giveaway_participants WHERE giveaway_id = ? AND user_id = ?",
            (self.giveaway_id, user.id)
        )
        if existing:
            return await interaction.response.send_message("❌ Bạn đã tham gia rồi!", ephemeral=True)

        # 2. Check Requirements
        passed, reason = await check_requirements(user, self.reqs)
        if not passed:
            return await interaction.response.send_message(f"❌ {reason}", ephemeral=True)

        # 3. Handle Cost (Deduct Seeds)
        cost = self.reqs.get("cost", 0)
        if cost > 0:
            # We already checked balance in check_requirements, but let's be safe and deduct now
            # Actually double check balance just in case
            from database_manager import get_user_balance
            bal = await get_user_balance(user.id)
            if bal < cost:
                 return await interaction.response.send_message("❌ Không đủ tiền mua vé!", ephemeral=True)
            
            await add_seeds(user.id, -cost)
            msg_suffix = f" (-{cost} Hạt)"
        else:
            msg_suffix = ""

        # 4. Add to Database
        try:
            await db_manager.modify(
                "INSERT INTO giveaway_participants (giveaway_id, user_id, entries) VALUES (?, ?, ?)",
                (self.giveaway_id, user.id, 1)
            )
            await interaction.response.send_message(f"✅ Đã tham gia thành công!{msg_suffix}", ephemeral=True)
        except Exception as e:
            print(f"Error joining giveaway: {e}")
            await interaction.response.send_message("❌ Có lỗi xảy ra, vui lòng thử lại sau.", ephemeral=True)

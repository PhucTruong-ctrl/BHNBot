import discord
import json
from database_manager import db_manager, add_seeds, get_user_balance
from .helpers import check_requirements, end_giveaway
from .constants import *

class GiveawayEndSelectView(discord.ui.View):
    """View for selecting and ending a giveaway."""
    def __init__(self, bot, options):
        super().__init__(timeout=300)
        self.bot = bot
        
        # Create select menu with giveaway options
        select = discord.ui.Select(
            placeholder="Chọn Giveaway để kết thúc...",
            options=options,
            custom_id="ga_end_select"
        )
        select.callback = self.end_giveaway_callback
        self.add_item(select)
    
    async def end_giveaway_callback(self, interaction: discord.Interaction):
        """Handle giveaway selection and end it."""
        try:
            # Get selected message_id
            message_id = int(interaction.data["values"][0])
            
            # Disable the select menu
            for item in self.children:
                item.disabled = True
            
            await interaction.response.defer()
            await interaction.edit_original_response(view=self)
            
            # End the giveaway
            await end_giveaway(message_id, self.bot)
            
            embed = discord.Embed(
                title="✅ Giveaway Đã Kết Thúc",
                description=f"Giveaway ID `{message_id}` đã được kết thúc và chọn người thắng!",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"[Giveaway] Error ending giveaway: {e}")
            embed = discord.Embed(
                title="❌ Lỗi",
                description=f"Có lỗi xảy ra: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

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
        
        # 1. Check Requirements
        passed, reason = await check_requirements(user, self.reqs)
        if not passed:
            return await interaction.response.send_message(f"❌ {reason}", ephemeral=True)

        # 2. Check Cost (Balance Check)
        cost = self.reqs.get("cost", 0)
        if cost > 0:
            bal = await get_user_balance(user.id)
            if bal < cost:
                 return await interaction.response.send_message("❌ Không đủ tiền mua vé!", ephemeral=True)

        # 3. Add to Database (Handle Race Condition via Unique Constraint)
        try:
            await db_manager.modify(
                "INSERT INTO giveaway_participants (giveaway_id, user_id, entries) VALUES (?, ?, ?)",
                (self.giveaway_id, user.id, 1)
            )
        except Exception as e:
            # Likely sqlite3.IntegrityError due to UNIQUE constraint
            # We can assume user already joined
            return await interaction.response.send_message("❌ Bạn đã tham gia rồi!", ephemeral=True)

        # 4. Deduct Cost
        if cost > 0:
            await add_seeds(user.id, -cost)
            msg_suffix = f" (-{cost} Hạt)"
        else:
            msg_suffix = ""

        await interaction.response.send_message(f"✅ Đã tham gia thành công!{msg_suffix}", ephemeral=True)

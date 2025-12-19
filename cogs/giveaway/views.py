import discord
import json
import random
from database_manager import db_manager, add_seeds, get_user_balance
from .helpers import check_requirements, end_giveaway
from .constants import *
from .models import Giveaway

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
        
        # 0. Check if giveaway is still active
        giveaway_row = await db_manager.fetchone(
            "SELECT status FROM giveaways WHERE message_id = ?", 
            (self.giveaway_id,)
        )
        if not giveaway_row or giveaway_row[0] != 'active':
            return await interaction.response.send_message("❌ Giveaway này đã kết thúc hoặc không còn tồn tại!", ephemeral=True)
        
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

class GiveawayResultView(discord.ui.View):
    """View for giveaway results with reroll and end options (Admin only)"""
    def __init__(self, giveaway_id: int, current_winners: list, bot):
        super().__init__(timeout=None)  # Persistent view
        self.giveaway_id = giveaway_id
        self.current_winners = current_winners
        self.bot = bot

    @discord.ui.button(label="🔄 Reroll", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ admin mới có thể reroll giveaway!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # Get giveaway data
            row = await db_manager.fetchone("SELECT * FROM giveaways WHERE message_id = ?", (self.giveaway_id,))
            if not row:
                await interaction.followup.send("❌ Giveaway không tồn tại!", ephemeral=True)
                return

            ga = Giveaway.from_db(row)
            if ga.status != 'ended':
                await interaction.followup.send("❌ Giveaway chưa kết thúc!", ephemeral=True)
                return

            # Get all participants
            participants = await db_manager.execute(
                "SELECT user_id, entries FROM giveaway_participants WHERE giveaway_id = ?",
                (self.giveaway_id,)
            )

            # Create pool excluding current winners
            pool = []
            for user_id, entries in participants:
                if user_id not in self.current_winners:  # Exclude current winners
                    pool.extend([user_id] * entries)

            if not pool:
                await interaction.followup.send("❌ Không còn người tham gia nào để reroll!", ephemeral=True)
                return

            # Pick new winners
            new_winners_ids = []
            count = min(len(set(pool)), ga.winners_count)
            random.shuffle(pool)
            seen = set()
            for uid in pool:
                if uid not in seen:
                    new_winners_ids.append(uid)
                    seen.add(uid)
                if len(new_winners_ids) >= count:
                    break

            if new_winners_ids:
                new_winners_text = ", ".join([f"<@{uid}>" for uid in new_winners_ids])
                result_text = f"🎉 **REROLL KẾT QUẢ!**\nXin chúc mừng {new_winners_text} đã thắng **{ga.prize}**! {EMOJI_WINNER}"
                
                # Update current winners for next reroll
                self.current_winners = new_winners_ids
                
                # Edit the result message
                embed = discord.Embed(
                    title="🎉 GIVEAWAY KẾT QUẢ (ĐÃ REROLL)",
                    description=result_text,
                    color=COLOR_GIVEAWAY
                )
                embed.set_footer(text=f"Giveaway ID: {self.giveaway_id}")
                
                await interaction.message.edit(embed=embed, view=self)
                
                await interaction.followup.send(f"✅ Đã reroll giveaway! Người thắng mới: {new_winners_text}", ephemeral=True)
            else:
                await interaction.followup.send("❌ Không thể chọn người thắng mới!", ephemeral=True)

        except Exception as e:
            print(f"[Giveaway] Error rerolling giveaway {self.giveaway_id}: {e}")
            await interaction.followup.send("❌ Có lỗi xảy ra khi reroll!", ephemeral=True)

    @discord.ui.button(label="🏁 Kết Thúc", style=discord.ButtonStyle.danger, emoji="🏁")
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ admin mới có thể kết thúc giveaway!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # Update giveaway status to 'completed' (different from 'ended')
            await db_manager.modify(
                "UPDATE giveaways SET status = 'completed' WHERE message_id = ?",
                (self.giveaway_id,)
            )

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            # Update the message
            embed = interaction.message.embeds[0]
            embed.title = "🎉 GIVEAWAY HOÀN TẤT"
            embed.set_footer(text=f"Giveaway ID: {self.giveaway_id} - Đã kết thúc hoàn toàn")

            await interaction.message.edit(embed=embed, view=self)

            await interaction.followup.send("✅ Đã kết thúc giveaway hoàn toàn!", ephemeral=True)
            print(f"[Giveaway] Giveaway {self.giveaway_id} completed by admin")

        except Exception as e:
            print(f"[Giveaway] Error completing giveaway {self.giveaway_id}: {e}")
            await interaction.followup.send("❌ Có lỗi xảy ra khi kết thúc!", ephemeral=True)

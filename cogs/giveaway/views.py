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
            
            print(f"[Giveaway] Admin {interaction.user} ({interaction.user.id}) manually ended giveaway ID {message_id}")
            
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
    def __init__(self, giveaway_id: int, requirements: str, cog=None):
        super().__init__(timeout=None) # Persistent view
        self.giveaway_id = giveaway_id
        self.reqs = json.loads(requirements) if isinstance(requirements, str) else requirements
        self.cog = cog
        
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
        
        # Fetch current requirements from DB (in case they were updated)
        req_row = await db_manager.fetchone(
            "SELECT requirements FROM giveaways WHERE message_id = ?",
            (self.giveaway_id,)
        )
        if not req_row:
            return await interaction.response.send_message("❌ Giveaway không tồn tại!", ephemeral=True)
        
        current_reqs = json.loads(req_row[0]) if req_row[0] else {}
        
        # 1. Check Requirements
        passed, reason = await check_requirements(user, current_reqs)
        if not passed:
            return await interaction.response.send_message(f"❌ {reason}", ephemeral=True)

        # 2. Secure Transaction for Cost & Join
        # This wrapper handles atomic balance check, deduction, and insertion
        from .helpers import join_giveaway_transaction
        
        cost = current_reqs.get("cost", 0)
        success, message = await join_giveaway_transaction(self.giveaway_id, user.id, cost)
        
        if not success:
            return await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            
        msg_suffix = f" (-{cost} Hạt)" if cost > 0 else ""

        await interaction.response.send_message(f"✅ Đã tham gia thành công!{msg_suffix}", ephemeral=True)
        
        # Schedule embed update with 5 second delay
        if self.cog:
            self.cog.schedule_embed_update(self.giveaway_id)

class GiveawayResultView(discord.ui.View):
    """View for giveaway results with reroll and end options (Admin only)"""
    def __init__(self, giveaway_id: int, current_winners: list, bot):
        super().__init__(timeout=None)  # Persistent view
        self.giveaway_id = giveaway_id
        self.current_winners = current_winners
        self.bot = bot
        
        # Set custom_id for persistence
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "🔄 Reroll":
                    item.custom_id = f"ga_reroll:{giveaway_id}"
                elif item.label == "🏁 Kết Thúc":
                    item.custom_id = f"ga_end:{giveaway_id}"

    @discord.ui.button(label="🔄 Reroll", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Chỉ admin mới có thể reroll giveaway!", ephemeral=True)
            return

        # Open modal to input reroll count
        modal = RerollModal(self.giveaway_id, self.current_winners, self.bot)
        await interaction.response.send_modal(modal)

class RerollModal(discord.ui.Modal, title="Reroll Giveaway"):
    def __init__(self, giveaway_id: int, current_winners: list, bot):
        super().__init__()
        self.giveaway_id = giveaway_id
        self.current_winners = current_winners
        self.bot = bot

    reroll_count = discord.ui.TextInput(
        label="Số lượng người thắng cần reroll",
        placeholder="Nhập số lượng (mặc định 1)",
        default="1",
        max_length=2,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse reroll count
            count = int(self.reroll_count.value)
            if count <= 0:
                await interaction.response.send_message("❌ Số lượng phải lớn hơn 0!", ephemeral=True)
                return

            await interaction.response.defer()

            # Get giveaway data
            row = await db_manager.fetchone("SELECT * FROM giveaways WHERE message_id = ?", (self.giveaway_id,))
            if not row:
                await interaction.followup.send("❌ Giveaway không tồn tại!", ephemeral=True)
                return

            ga = Giveaway.from_db(row)
            if ga.status != 'ended':
                await interaction.followup.send("❌ Giveaway chưa kết thúc!", ephemeral=True)
                return

            # Get all participants (each has 1 entry)
            participants = await db_manager.execute(
                "SELECT user_id FROM giveaway_participants WHERE giveaway_id = ?",
                (self.giveaway_id,)
            )

            # Extract user IDs excluding current winners
            available_users = [row[0] for row in participants if row[0] not in self.current_winners]

            if not available_users:
                await interaction.followup.send("❌ Không còn người tham gia nào để reroll!", ephemeral=True)
                return

            # Pick new winners
            available_count = len(available_users)
            if available_count < count:
                await interaction.followup.send(f"⚠️ Chỉ còn {available_count} người có thể reroll! Sẽ chọn {available_count} người.", ephemeral=True)
                count = available_count

            new_winners_ids = random.sample(available_users, count)

            if new_winners_ids:
                # Add new winners to current winners (ensure no duplicates)
                for winner in new_winners_ids:
                    if winner not in self.current_winners:
                        self.current_winners.append(winner)
                
                # Create mentions
                new_winners_text = ", ".join([f"<@{uid}>" for uid in new_winners_ids])
                
                # Get unique list of all winners for display
                unique_winners = list(dict.fromkeys(self.current_winners))  # Preserve order, remove dupes
                all_winners_text = ", ".join([f"<@{uid}>" for uid in unique_winners])
                
                result_text = f"👑 **Người thắng mới:** {new_winners_text}"
                
                print(f"[Giveaway] Rerolled giveaway ID {self.giveaway_id} by admin {interaction.user} ({interaction.user.id}) - New winners: {new_winners_ids}, Total unique: {len(unique_winners)}, All: {unique_winners}")
                
                # Edit the result message
                embed = discord.Embed(
                    title="🎉 GIVEAWAY KẾT QUẢ (ĐÃ REROLL)",
                    description=result_text,
                    color=COLOR_GIVEAWAY
                )
                embed.set_footer(text=f"Giveaway ID: {self.giveaway_id} | Reroll count: {len(new_winners_ids)}")
                
                # Update the view's current_winners to the unique list
                self.current_winners = unique_winners
                
                # Update Persistent Winners in DB
                import json
                await db_manager.modify(
                    "UPDATE giveaways SET winners = ? WHERE message_id = ?",
                    (json.dumps(self.current_winners), self.giveaway_id)
                )

                # Re-instantiate the view to update it
                view = GiveawayResultView(self.giveaway_id, self.current_winners, self.bot)
                await interaction.message.edit(embed=embed, view=view)
                
                await interaction.followup.send(f"✅ Đã reroll {len(new_winners_ids)} người thắng mới: {new_winners_text}", ephemeral=True)
            else:
                await interaction.followup.send("❌ Không thể chọn người thắng mới!", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("❌ Số lượng không hợp lệ!", ephemeral=True)
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

            print(f"[Giveaway] Giveaway ID {self.giveaway_id} completed by admin {interaction.user} ({interaction.user.id})")

            await interaction.followup.send("✅ Đã kết thúc giveaway hoàn toàn!", ephemeral=True)
            print(f"[Giveaway] Giveaway {self.giveaway_id} completed by admin")

        except Exception as e:
            print(f"[Giveaway] Error completing giveaway {self.giveaway_id}: {e}")
            await interaction.followup.send("❌ Có lỗi xảy ra khi kết thúc!", ephemeral=True)

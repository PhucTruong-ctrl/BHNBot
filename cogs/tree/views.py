"""Discord UI components for tree system.

Contains Modal and View for seed contribution.
"""

import discord
from core.logger import setup_logger

logger = setup_logger("TreeViews", "logs/cogs/tree.log")


class ContributeModal(discord.ui.Modal):
    """Modal for custom seed contribution input.
    
    Prompts user to enter the number of seeds they want to contribute.
    
    Attributes:
        tree_manager: Reference to TreeManager instance
    """
    
    def __init__(self, tree_manager):
        """Initialize the contribution modal.
        
        Args:
            tree_manager: TreeManager instance for processing contribution
        """
        super().__init__(title="Góp Hạt Cho Cây")
        self.tree_manager = tree_manager
        
        self.amount_input = discord.ui.TextInput(
            label="Số hạt muốn góp",
            placeholder="Nhập số từ 1 trở lên",
            min_length=1,
            max_length=6
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process contribution when user submits modal.
        
        Validates input and delegates to tree_manager.process_contribution().
        
        Args:
            interaction: Discord interaction from modal submission
        """
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
            
            # Parse and validate amount
            try:
                amount = int(self.amount_input.value)
            except ValueError:
                await interaction.followup.send(
                    "❌ Vui lòng nhập số nguyên hợp lệ!",
                    ephemeral=True
                )
                return
            
            # SECURITY FIX #5: Validate range
            from .constants import MAX_CONTRIBUTION
            
            if amount <= 0:
                await interaction.followup.send(
                    "❌ Số lượng phải lớn hơn 0!",
                    ephemeral=True
                )
                return
            
            if amount > MAX_CONTRIBUTION:
                await interaction.followup.send(
                    f"❌ Số lượng quá lớn! Tối đa: {MAX_CONTRIBUTION:,} hạt",
                    ephemeral=True
                )
                return
            
            # Process contribution
            await self.tree_manager.process_contribution(interaction, amount)
            
        except Exception as e:
            logger.error(f"Error in modal submission: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"❌ Có lỗi xảy ra: {str(e)}",
                    ephemeral=True
                )
            except Exception:
                pass  # Interaction may have expired


class TreeContributeView(discord.ui.View):
    """View with quick contribute buttons.
    
    Displays 3 buttons for quick contributions: 10, 100, and custom amount.
    
    Attributes:
        tree_manager: Reference to TreeManager instance
    """
    
    def __init__(self, tree_manager):
        """Initialize the contribution button view.
        
        Args:
            tree_manager: TreeManager instance
        """
        super().__init__(timeout=None)
        self.tree_manager = tree_manager
    
    @discord.ui.button(
        label="🌱 10 Hạt",
        style=discord.ButtonStyle.green,
        custom_id="tree_10"
    )
    async def contribute_10(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle 10 seeds contribution button."""
        try:
            await interaction.response.defer(ephemeral=False)
        except Exception as e:
            logger.error(f"Error deferring response: {e}", exc_info=True)
            return
        
        await self.tree_manager.process_contribution(interaction, 10)
    
    @discord.ui.button(
        label="🌿 100 Hạt",
        style=discord.ButtonStyle.blurple,
        custom_id="tree_100"
    )
    async def contribute_100(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle 100 seeds contribution button."""
        try:
            await interaction.response.defer(ephemeral=False)
        except Exception as e:
            logger.error(f"Error deferring response: {e}", exc_info=True)
            return
        
        await self.tree_manager.process_contribution(interaction, 100)
    
    @discord.ui.button(
        label="✏️ Tuỳ ý",
        style=discord.ButtonStyle.secondary,
        custom_id="tree_custom"
    )
    async def contribute_custom(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle custom amount contribution button - opens modal."""
        modal = ContributeModal(self.tree_manager)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="💧 Tưới Free",
        style=discord.ButtonStyle.success,
        custom_id="tree_water_free"
    )
    async def water_free(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle free daily watering - gives XP to tree and random reward to user."""
        import random
        from datetime import datetime, date
        from database_manager import db_manager, add_seeds
        
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        today = date.today().isoformat()
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Check if user already watered today
            row = await db_manager.fetchone(
                "SELECT last_water_date FROM tree_water_log WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            
            if row and row[0] == today:
                await interaction.followup.send(
                    "💧 Bạn đã tưới cây hôm nay rồi! Quay lại vào ngày mai nhé~",
                    ephemeral=True
                )
                return
            
            # Update or insert water log
            await db_manager.modify(
                """INSERT INTO tree_water_log (user_id, guild_id, last_water_date)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, guild_id) DO UPDATE SET last_water_date = ?""",
                (user_id, guild_id, today, today)
            )
            
            # Add XP to tree DIRECTLY (FREE - no seed deduction)
            from .models import TreeData
            tree_data = await TreeData.load(guild_id)
            
            if tree_data.current_level < 6:
                # Add 10 XP to tree progress
                new_progress = tree_data.current_progress + 10
                new_total = tree_data.total_contributed + 10
                
                # Check for level up
                level_reqs = tree_data.get_level_requirements()
                req = level_reqs.get(tree_data.current_level + 1, level_reqs[6])
                new_level = tree_data.current_level
                leveled_up = False
                
                while new_progress >= req and new_level < 6:
                    new_level += 1
                    new_progress = new_progress - req
                    leveled_up = True
                    req = level_reqs.get(new_level + 1, level_reqs[6])
                
                # Save tree data
                await db_manager.modify(
                    """UPDATE server_tree 
                       SET current_progress = ?, total_contributed = ?, current_level = ?
                       WHERE guild_id = ?""",
                    (new_progress, new_total, new_level, guild_id)
                )
                
                level_up_msg = "\n🎉 **CÂY TĂNG CẤP!**" if leveled_up else ""
            else:
                level_up_msg = "\n🍎 Cây đã chín! Đợi Admin thu hoạch nhé~"
            
            # Random reward for user
            reward = random.choice([5, 10, 15, 20, 30, 50])
            await add_seeds(user_id, reward)
            
            await interaction.followup.send(
                f"💧 **Tưới cây thành công!** Cây nhận +10 XP.{level_up_msg}\n"
                f"🌱 Cây cảm ơn và thưởng bạn **{reward}** Hạt!",
                ephemeral=True
            )
            
            logger.info(f"[WATER_FREE] User {user_id} watered tree, got {reward} seeds")
            
        except Exception as e:
            logger.error(f"Error in water_free: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"❌ Có lỗi xảy ra: {str(e)}",
                    ephemeral=True
                )
            except Exception:
                pass

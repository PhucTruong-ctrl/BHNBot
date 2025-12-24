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

"""Discord UI components for Bau Cua game.

Contains Modal and View classes for betting interface.
"""

import discord
from core.logging import setup_logger

from .constants import ANIMALS

logger = setup_logger("BauCuaViews", "logs/cogs/baucua.log")


class BauCuaBetModal(discord.ui.Modal):
    """Modal dialog for entering bet amount.
    
    Prompts user to input the number of seeds they want to bet
    on the selected animal.
    
    Attributes:
        game_cog: Reference to BauCuaCog instance
        game_id: Unique identifier for the active game
        animal_key: Key of animal being bet on (e.g., 'bau')
    """
    
    def __init__(self, game_cog, game_id: str, animal_key: str):
        """Initialize the bet input modal.
        
        Args:
            game_cog: BauCuaCog instance for processing bet
            game_id: Current game session ID
            animal_key: Animal being bet on
        """
        animal_name = ANIMALS[animal_key]['name']
        super().__init__(title=f"Cược {animal_name}")
        self.game_cog = game_cog
        self.game_id = game_id
        self.animal_key = animal_key
        
        # Create text input for bet amount
        self.amount_input = discord.ui.TextInput(
            label="Số hạt muốn cược",
            placeholder="Nhập số từ 1 trở lên",
            min_length=1,
            max_length=6
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process bet when user submits the modal.
        
        Validates input and delegates to game_cog.add_bet().
        
        Args:
            interaction: Discord interaction from modal submission
        """
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Parse bet amount
            try:
                amount = int(self.amount_input.value)
            except ValueError:
                await interaction.followup.send(
                    "❌ Vui lòng nhập số nguyên hợp lệ!",
                    ephemeral=True
                )
                return
            
            # Validate positive amount
            if amount <= 0:
                await interaction.followup.send(
                    "❌ Số lượng không hợp lệ!",
                    ephemeral=True
                )
                return
            
            # Process the bet through game cog
            await self.game_cog.add_bet(
                interaction,
                self.game_id,
                self.animal_key,
                amount
            )
            
        except Exception as e:
            logger.error(
                f"Error processing bet modal submission: {e}",
                exc_info=True
            )
            try:
                await interaction.followup.send(
                    "❌ Lỗi khi xử lý cược!",
                    ephemeral=True
                )
            except Exception:
                pass  # Interaction may have expired


class BauCuaBetView(discord.ui.View):
    """View with 6 animal bet buttons arranged in 3x2 grid.
    
    Displays buttons for all 6 animals. When clicked, opens BauCuaBetModal
    for the user to enter their bet amount.
    
    Attributes:
        game_cog: Reference to BauCuaCog instance
        game_id: Unique identifier for the active game
    """
    
    def __init__(self, game_cog, game_id: str):
        """Initialize the betting button view.
        
        Args:
            game_cog: BauCuaCog instance
            game_id: Current game session ID
        """
        super().__init__(timeout=600)  # 10 minutes max per game (prevents memory leak)
        self.game_cog = game_cog
        self.game_id = game_id
    
    # Row 0: Bầu, Cua, Tôm
    @discord.ui.button(
        label="🎃 Bầu",
        style=discord.ButtonStyle.primary,
        custom_id="baucua_bau",
        row=0
    )
    async def bet_bau(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle Bầu (Gourd) bet button click."""
        modal = BauCuaBetModal(self.game_cog, self.game_id, "bau")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🦀 Cua",
        style=discord.ButtonStyle.primary,
        custom_id="baucua_cua",
        row=0
    )
    async def bet_cua(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle Cua (Crab) bet button click."""
        modal = BauCuaBetModal(self.game_cog, self.game_id, "cua")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🦐 Tôm",
        style=discord.ButtonStyle.primary,
        custom_id="baucua_tom",
        row=0
    )
    async def bet_tom(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle Tôm (Shrimp) bet button click."""
        modal = BauCuaBetModal(self.game_cog, self.game_id, "tom")
        await interaction.response.send_modal(modal)
    
    # Row 1: Cá, Gà, Nai
    @discord.ui.button(
        label="🐟 Cá",
        style=discord.ButtonStyle.primary,
        custom_id="baucua_ca",
        row=1
    )
    async def bet_ca(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle Cá (Fish) bet button click."""
        modal = BauCuaBetModal(self.game_cog, self.game_id, "ca")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🐔 Gà",
        style=discord.ButtonStyle.primary,
        custom_id="baucua_ga",
        row=1
    )
    async def bet_ga(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle Gà (Chicken) bet button click."""
        modal = BauCuaBetModal(self.game_cog, self.game_id, "ga")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🦌 Nai",
        style=discord.ButtonStyle.primary,
        custom_id="baucua_nai",
        row=1
    )
    async def bet_nai(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Handle Nai (Deer) bet button click."""
        modal = BauCuaBetModal(self.game_cog, self.game_id, "nai")
        await interaction.response.send_modal(modal)

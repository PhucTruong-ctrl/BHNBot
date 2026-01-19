"""Interactive Views (Buttons & Modals) for Xi Dach."""

import discord
import time
import asyncio
from discord import ui
from typing import TYPE_CHECKING, Optional

from ..services.hand_service import HandType
from ..core.table import Table, TableStatus
from ..core.player import Player, PlayerStatus
from .embeds import create_lobby_embed

from core.logging import get_logger
logger = get_logger("xi_dach_views")

if TYPE_CHECKING:
    from ..cog import XiDachCog

class BetAmountModal(ui.Modal, title="Nhập Số Hạt Cược"):
    """Modal for inputting custom bet amount."""
    
    amount_input = ui.TextInput(
        label="Số hạt muốn cược",
        placeholder="Nhập số từ 1 trở lên",
        min_length=1,
        max_length=10,
        required=True
    )

    def __init__(self, cog: "XiDachCog", table: Table, user_id: int):
        super().__init__()
        self.cog = cog
        self.table = table
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            amount = int(self.amount_input.value)
            await self.cog.process_bet(interaction, self.table, self.user_id, amount)
        except ValueError:
            await interaction.response.send_message(
                "❌ Vui lòng nhập số nguyên hợp lệ!", ephemeral=True
            )

class SoloGameView(ui.View):
    """View for single-player Xi Dach game."""

    def __init__(
        self,
        cog: "XiDachCog",
        table: Table,
        player: Player,
        timeout: float = 120.0
    ):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table
        self.player = player
        self._update_buttons()

    def _update_buttons(self) -> None:
        is_playing = self.player.status == PlayerStatus.PLAYING
        
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = not is_playing
                if item.custom_id == "btn_double":
                    item.disabled = not is_playing or not self.player.can_double

    @ui.button(label="🃏 Rút", style=discord.ButtonStyle.primary, custom_id="btn_hit")
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Đây không phải lượt của bạn!", ephemeral=True)
            return

        await self.cog.player_hit(interaction, self.table, self.player)
        self._update_buttons()

    @ui.button(label="✋ Dằn", style=discord.ButtonStyle.secondary, custom_id="btn_stand")
    async def stand_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Đây không phải lượt của bạn!", ephemeral=True)
            return

        await self.cog.player_stand(interaction, self.table, self.player)

    @ui.button(label="💰 Gấp Đôi", style=discord.ButtonStyle.success, custom_id="btn_double")
    async def double_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Đây không phải lượt của bạn!", ephemeral=True)
            return

        await self.cog.player_double(interaction, self.table, self.player)

    async def on_timeout(self) -> None:
        if self.player.status == PlayerStatus.PLAYING:
            self.player.status = PlayerStatus.STAND

class LobbyView(ui.View):
    """View for multiplayer lobby with integrated betting."""
    
    BET_AMOUNTS = [50, 100, 500, 1000, 5000]

    def __init__(self, cog: "XiDachCog", table: Table, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table
        self._setup_buttons()

    def _setup_buttons(self):
        # Bet Buttons (Row 0 & 1)
        for amount in self.BET_AMOUNTS:
            btn = ui.Button(
                label=f"{amount:,}", 
                style=discord.ButtonStyle.secondary, 
                custom_id=f"btn_bet_{amount}",
                row=0 if amount < 1000 else 1
            )
            btn.callback = self._make_bet_callback(amount)
            self.add_item(btn)
            
        # Custom Bet
        custom_btn = ui.Button(label="✏️ Khác", style=discord.ButtonStyle.secondary, custom_id="btn_bet_custom", row=1)
        custom_btn.callback = self._custom_bet_callback
        self.add_item(custom_btn)
        
        # All-In Button (Row 1)
        allin_btn = ui.Button(label="💰 ALL IN", style=discord.ButtonStyle.danger, custom_id="btn_allin", row=1)
        allin_btn.callback = self._allin_callback
        self.add_item(allin_btn)
        
        # Cancel Bet Button (Row 2)
        cancel_btn = ui.Button(label="❌ Bỏ Cược", style=discord.ButtonStyle.secondary, custom_id="btn_cancel_bet", row=2)
        cancel_btn.callback = self._cancel_bet_callback
        self.add_item(cancel_btn)
        
        # Start Game (Host Only) (Row 2)
        start_btn = ui.Button(label="🎲 Bắt Đầu", style=discord.ButtonStyle.success, custom_id="btn_start_game", row=2)
        start_btn.callback = self._start_game_callback
        self.add_item(start_btn)

    def _make_bet_callback(self, amount: int):
        async def callback(interaction: discord.Interaction) -> None:
            await self.cog.process_bet(interaction, self.table, interaction.user.id, amount)
        return callback

    async def _custom_bet_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(BetAmountModal(self.cog, self.table, interaction.user.id))

    async def _allin_callback(self, interaction: discord.Interaction) -> None:
        """Bet entire balance."""
        from database_manager import get_user_balance
        balance = await get_user_balance(interaction.user.id)
        if balance <= 0:
            await interaction.response.send_message("❌ Bạn không có hạt để All-In!", ephemeral=True)
            return
        await self.cog.process_bet(interaction, self.table, interaction.user.id, balance)

    async def _cancel_bet_callback(self, interaction: discord.Interaction) -> None:
        """Cancel bet and get refund."""
        from ..commands.multi import cancel_bet
        await cancel_bet(self.cog, interaction, self.table, interaction.user.id)

    async def _start_game_callback(self, interaction: discord.Interaction) -> None:
        await self.cog.request_start_game(interaction, self.table)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True

class MultiGameView(ui.View):
    """View for multiplayer game."""

    def __init__(
        self,
        cog: "XiDachCog",
        table: Table,
        turn_msg: discord.Message = None,
        channel: discord.TextChannel = None,
        timeout: float = 180.0
    ):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table
        self.turn_msg = turn_msg
        self.channel = channel
        self.action_timestamp = 0.0

    def _is_active_and_turn(self, interaction: discord.Interaction) -> bool:
        if self.table.status != TableStatus.PLAYING:
            logger.debug("not_playing._status:_", self.table.status=self.table.status)
            return False
            
        current = self.table.current_player
        if not current:
            logger.debug("no_current_player._index:_,_or", self.table.current_player_idx=self.table.current_player_idx)
            return False
            
        if current.user_id != interaction.user.id:
            logger.debug("wrong_turn._expected:_,_got:_{", current.user_id=current.user_id)
            return False
            
        return True

    @ui.button(label="🃏 Rút", style=discord.ButtonStyle.primary, custom_id="btn_hit_multi")
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_active_and_turn(interaction):
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog.player_hit_multi(interaction, self.table, self.table.current_player, self)

    @ui.button(label="✋ Dằn", style=discord.ButtonStyle.secondary, custom_id="btn_stand_multi")
    async def stand_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_active_and_turn(interaction):
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog.player_stand_multi(interaction, self.table, self.table.current_player, self)

    @ui.button(label="💰 Gấp Đôi", style=discord.ButtonStyle.success, custom_id="btn_double_multi")
    async def double_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_active_and_turn(interaction):
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

        player = self.table.current_player
        if not player.can_double:
             await interaction.response.send_message("❌ Không thể Gấp đôi!", ephemeral=True)
             return

        try:
            await interaction.response.defer()
            await self.cog.player_double_multi(interaction, self.table, player, self)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error("double_button_failed:_", e=e)
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

    async def on_timeout(self) -> None:
        for item in self.children:
             if isinstance(item, ui.Button): item.disabled = True
        
        # Avoid circular import
        from ..commands.multi import force_stand_multi
        asyncio.create_task(force_stand_multi(self.cog, self.table, self.table.current_player))

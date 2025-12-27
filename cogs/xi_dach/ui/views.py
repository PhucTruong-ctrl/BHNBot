"""Interactive Views (Buttons & Modals) for Xi Dach."""

import discord
import time
from discord import ui
from typing import TYPE_CHECKING, Optional

from ..services.hand_service import HandType
from ..core.table import Table, TableStatus
from ..core.player import Player, PlayerStatus
from .embeds import create_lobby_embed

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
    """View for multiplayer lobby."""

    def __init__(self, cog: "XiDachCog", table: Table, timeout: float = 35.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table

    @ui.button(label="🎮 Tham Gia", style=discord.ButtonStyle.success, custom_id="btn_join_lobby")
    async def join_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self.cog.player_join_lobby(interaction, self.table)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True

class MultiBetView(ui.View):
    """View for multiplayer betting phase."""

    BET_AMOUNTS = [50, 100, 500, 1000, 10000]

    def __init__(
        self,
        cog: "XiDachCog",
        table: Table,
        player: Player,
        timeout: float = 300.0
    ):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table
        self.player = player
        self._create_bet_buttons()

    def _create_bet_buttons(self) -> None:
        uid = self.player.user_id
        
        # Presets
        for amount in self.BET_AMOUNTS:
            button = ui.Button(label=f"+{amount:,}", style=discord.ButtonStyle.primary, custom_id=f"btn_bet_{amount}_{uid}", row=0)
            button.callback = self._make_bet_callback(amount)
            self.add_item(button)

        # Actions
        clear_btn = ui.Button(label="🔄 Xoá Cược", style=discord.ButtonStyle.secondary, custom_id=f"btn_bet_clear_{uid}", row=1)
        clear_btn.callback = self._clear_bet_callback
        self.add_item(clear_btn)

        custom_btn = ui.Button(label="✏️ Nhập Số", style=discord.ButtonStyle.secondary, custom_id=f"btn_bet_custom_{uid}", row=1)
        custom_btn.callback = self._custom_bet_callback
        self.add_item(custom_btn)

        all_in_btn = ui.Button(label="🔥 Tất Tay", style=discord.ButtonStyle.danger, custom_id=f"btn_bet_allin_{uid}", row=1)
        all_in_btn.callback = self._all_in_callback
        self.add_item(all_in_btn)

        # Ready
        ready_btn = ui.Button(label="✅ Sẵn Sàng", style=discord.ButtonStyle.success, custom_id=f"btn_ready_{uid}", row=2)
        ready_btn.callback = self._ready_callback
        self.add_item(ready_btn)

    def _make_bet_callback(self, amount: int):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.player.user_id:
                await interaction.response.send_message("❌ Sai giao diện!", ephemeral=True)
                return
            await self.cog.process_bet(interaction, self.table, self.player.user_id, amount)
        return callback

    async def _custom_bet_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Sai giao diện!", ephemeral=True)
            return
        await interaction.response.send_modal(BetAmountModal(self.cog, self.table, self.player.user_id))

    async def _all_in_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Sai giao diện!", ephemeral=True)
            return
        
        try:
            balance = await self.cog.get_user_seeds(self.player.user_id)
            if balance <= 0:
                await interaction.response.send_message("❌ Hết hạt rồi!", ephemeral=True)
                return
            await self.cog.process_bet(interaction, self.table, self.player.user_id, balance)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

    async def _clear_bet_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Sai giao diện!", ephemeral=True)
            return

        self.player.bet = 0
        view = MultiBetView(self.cog, self.table, self.player)
        await interaction.response.edit_message(content=f"💰 **Đặt cược:**\n✅ Đã xoá cược!", view=view)

        try:
             elapsed = time.time() - self.table.created_at
             remaining = max(0, 30 - int(elapsed))
             if self.table.message_id and interaction.channel:
                 lobby_msg = await interaction.channel.fetch_message(self.table.message_id)
                 embed = create_lobby_embed(self.table, remaining)
                 await lobby_msg.edit(embed=embed)
        except:
             pass

    async def _ready_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("❌ Sai giao diện!", ephemeral=True)
            return
        await self.cog.player_ready(interaction, self.table, self.player)

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
        if self.table.status != TableStatus.PLAYING or not self.table.current_player:
            return False
        return self.table.current_player.user_id == interaction.user.id

    @ui.button(label="🃏 Rút", style=discord.ButtonStyle.primary, custom_id="btn_hit_multi")
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_active_and_turn(interaction):
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

        await self.cog.player_hit_multi(interaction, self.table, self.table.current_player, self)

    @ui.button(label="✋ Dằn", style=discord.ButtonStyle.secondary, custom_id="btn_stand_multi")
    async def stand_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_active_and_turn(interaction):
            await interaction.response.send_message("❌ Không phải lượt của bạn!", ephemeral=True)
            return

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

        await self.cog.player_double_multi(interaction, self.table, player, self)

    async def on_timeout(self) -> None:
        for item in self.children:
             if isinstance(item, ui.Button): item.disabled = True
        
        # Avoid circular import
        from ..commands.multi import force_stand_multi
        asyncio.create_task(force_stand_multi(self.cog, self.table, self.table.current_player))
class BettingEntryView(ui.View):
    """View to enter betting phase (Public)."""
    def __init__(self, cog: "XiDachCog", table: Table, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table

    @ui.button(label="💸 Đặt Cược", style=discord.ButtonStyle.primary, custom_id="btn_open_bet")
    async def open_bet_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id not in self.table.players:
            await interaction.response.send_message("❌ Bạn chưa tham gia bàn chơi!", ephemeral=True)
            return
            
        # Send Ephemeral Betting Dashboard
        player = self.table.players[interaction.user.id]
        view = MultiBetView(self.cog, self.table, player)
        await interaction.response.send_message("💰 **BẢNG ĐẶT CƯỢC**", view=view, ephemeral=True)

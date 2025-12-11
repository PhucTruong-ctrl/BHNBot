"""
Werewolf Game Discord UI Components
Views, Buttons, Selects cho game
"""
import discord
from discord.ui import View, Button, Select, button, select
from discord.interactions import Interaction
from typing import Optional, Callable
from .models import GameWerewolf, GamePlayer, Role, Faction


class GameLobbyView(View):
    """View cho lobby game (join + admin controls)"""
    
    def __init__(self, on_join: Callable, on_start: Callable, on_cancel: Callable, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.on_join = on_join
        self.on_start = on_start
        self.on_cancel = on_cancel
    
    @button(label="Tham gia", style=discord.ButtonStyle.green, emoji="🎮")
    async def join_button(self, interaction: Interaction, button: Button):
        await self.on_join(interaction)
    
    @button(label="Bắt đầu Game", style=discord.ButtonStyle.blurple, emoji="▶️")
    async def start_button(self, interaction: Interaction, button: Button):
        await self.on_start(interaction)
    
    @button(label="Hủy Game", style=discord.ButtonStyle.red, emoji="⏹️")
    async def cancel_button(self, interaction: Interaction, button: Button):
        await self.on_cancel(interaction)


class JoinButtonView(View):
    """View cho nút Join lobby"""
    
    def __init__(self, on_join: Callable, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.on_join = on_join
    
    @button(label="Tham gia", style=discord.ButtonStyle.green, emoji="🎮")
    async def join_button(self, interaction: Interaction, button: Button):
        await self.on_join(interaction)


class RoleSelectView(View):
    """View cho chọn vai trò (cho Soi, Tiên Tri, v.v. action ban đêm)"""
    
    def __init__(
        self,
        game: GameWerewolf,
        player: GamePlayer,
        candidates: list[GamePlayer],
        action_type: str,  # "kill", "heal", "check", etc
        on_select: Callable,
        timeout: int = 20
    ):
        super().__init__(timeout=timeout)
        self.game = game
        self.player = player
        self.candidates = candidates
        self.action_type = action_type
        self.on_select = on_select
        
        # Tạo select menu với candidates
        self._build_select()
    
    def _build_select(self):
        """Tạo select menu"""
        options = [
            discord.SelectOption(
                label=f"{c.username}",
                value=str(c.user_id),
                description=f"ID: {c.user_id}"
            )
            for c in self.candidates if c.is_alive
        ]
        
        if not options:
            # Nếu không có ai sống sót
            self.add_item(
                Select(
                    placeholder="Không có mục tiêu",
                    options=[
                        discord.SelectOption(label="Bỏ qua", value="skip")
                    ],
                    disabled=True
                )
            )
        else:
            select_menu = Select(
                placeholder=f"Chọn mục tiêu ({self.action_type})",
                options=options,
                min_values=1,
                max_values=1
            )
            select_menu.callback = self._on_select
            self.add_item(select_menu)
    
    async def _on_select(self, interaction: Interaction):
        """Callback khi select"""
        selected_id = int(interaction.data["values"][0])
        await self.on_select(interaction, self.player, selected_id, self.action_type)


class VoteSelectView(View):
    """View cho bỏ phiếu ban ngày"""
    
    def __init__(
        self,
        game: GameWerewolf,
        voter: Optional[GamePlayer],
        on_vote: Callable,
        timeout: int = 60
    ):
        super().__init__(timeout=timeout)
        self.game = game
        self.voter = voter  # None for group voting
        self.on_vote = on_vote
        
        # Tạo select menu với người chơi sống sót
        self._build_select()
    
    def _build_select(self):
        """Tạo select menu - chỉ cho sống sót, không được chọn chính mình"""
        alive_players = self.game.get_alive_players()
        
        # Filter: chỉ người sống sót
        valid_players = [p for p in alive_players if p.is_alive]
        
        # Nếu có voter cụ thể (individual voting), loại bỏ chính họ
        if self.voter is not None:
            valid_players = [p for p in valid_players if p.user_id != self.voter.user_id]
        # Nếu group voting (voter=None), không loại bỏ ai
        
        options = [
            discord.SelectOption(
                label=f"{p.username}",
                value=str(p.user_id)
            )
            for p in valid_players
        ]
        
        if not options:
            return
        
        select_menu = Select(
            placeholder="Chọn người để treo cổ",
            options=options,
            min_values=1,
            max_values=1
        )
        select_menu.callback = self._on_vote
        self.add_item(select_menu)
    
    async def _on_vote(self, interaction: Interaction):
        """Callback khi vote"""
        voted_id = int(interaction.data["values"][0])
        voter_id = interaction.user.id
        
        if self.voter is None:
            # Group voting - pass voter_id directly
            await self.on_vote(interaction, voter_id, voted_id)
        else:
            # Individual voting - pass voter object
            await self.on_vote(interaction, self.voter, voted_id)


class SkipActionButton(View):
    """View cho nút skip action ban đêm"""
    
    def __init__(self, on_skip: Callable, timeout: int = 45):
        super().__init__(timeout=timeout)
        self.on_skip = on_skip
    
    @button(label="Bỏ qua", style=discord.ButtonStyle.gray, emoji="⏭️")
    async def skip_button(self, interaction: Interaction, button: Button):
        await self.on_skip(interaction)


class ConfirmView(View):
    """View cho confirm/cancel"""
    
    def __init__(self, on_confirm: Callable, on_cancel: Callable, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
    
    @button(label="Xác nhận", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_button(self, interaction: Interaction, button: Button):
        await self.on_confirm(interaction)
    
    @button(label="Hủy", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_button(self, interaction: Interaction, button: Button):
        await self.on_cancel(interaction)


class DebugRoleSelectView(View):
    """View cho chọn vai trò debug (tạm dùng)"""
    
    def __init__(self, game: GameWerewolf, on_role_select: Callable, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.game = game
        self.on_role_select = on_role_select
        
        # Tạo select menu với vai trò
        self._build_select()
    
    def _build_select(self):
        """Tạo select menu với tất cả vai trò"""
        alive_players = self.game.get_alive_players()
        
        # Tạo options cho người chơi
        player_options = [
            discord.SelectOption(
                label=f"{p.username}",
                value=f"player_{p.user_id}",
                description=f"ID: {p.user_id}"
            )
            for p in alive_players
        ]
        
        if player_options:
            player_select = Select(
                placeholder="Chọn người chơi",
                options=player_options,
                min_values=1,
                max_values=1
            )
            player_select.callback = self._on_player_select
            self.add_item(player_select)
    
    async def _on_player_select(self, interaction: Interaction):
        """Callback khi chọn người chơi"""
        player_value = interaction.data["values"][0]
        player_id = int(player_value.replace("player_", ""))
        
        # Tạo select menu cho vai trò
        role_options = [
            discord.SelectOption(
                label=role.value,
                value=role.name,
                description=f"{ROLE_METADATA[role].faction.value}"
            )
            for role in Role
            if role != Role.VILLAGER  # Loại bỏ placeholder
        ]
        
        role_select = Select(
            placeholder="Chọn vai trò",
            options=role_options,
            min_values=1,
            max_values=1
        )
        
        async def role_callback(role_interaction: Interaction):
            role_name = role_interaction.data["values"][0]
            role = Role[role_name]
            await self.on_role_select(role_interaction, player_id, role)
        
        role_select.callback = role_callback
        
        # Tạo view mới với role select
        view = View()
        view.add_item(role_select)
        
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Chọn vai trò:", view=view, ephemeral=True)


class GameControlView(View):
    """View cho điều khiển game (start, end, etc)"""
    
    def __init__(self, on_start: Callable, on_cancel: Callable, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.on_start = on_start
        self.on_cancel = on_cancel
    
    @button(label="Bắt đầu Game", style=discord.ButtonStyle.blurple, emoji="▶️")
    async def start_button(self, interaction: Interaction, button: Button):
        await self.on_start(interaction)
    
    @button(label="Hủy Game", style=discord.ButtonStyle.red, emoji="⏹️")
    async def cancel_button(self, interaction: Interaction, button: Button):
        await self.on_cancel(interaction)

"""
Xi Dach (Vietnamese Blackjack) - Discord UI Views

Contains all Discord UI components: buttons, modals, and views.
"""
import discord
import time
from discord import ui
from typing import TYPE_CHECKING, Optional

from .game import format_hand, get_hand_description, compare_hands, HandType
from .models import Table, Player, PlayerStatus, TableStatus, game_manager

if TYPE_CHECKING:
    from .cog import XiDachCog


# ==================== BET AMOUNT MODAL ====================

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
        """Handle bet amount submission."""
        try:
            amount = int(self.amount_input.value)
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Số lượng không hợp lệ!", ephemeral=True
                )
                return

            await self.cog.process_bet(interaction, self.table, self.user_id, amount)
        except ValueError:
            await interaction.response.send_message(
                "❌ Vui lòng nhập số nguyên hợp lệ!", ephemeral=True
            )


# ==================== SOLO GAME VIEW ====================

class SoloGameView(ui.View):
    """View for single-player Xi Dach game with Hit/Stand/Double buttons."""

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
        """Update button states based on player status."""
        # Disable all if not player's turn or game over
        is_playing = self.player.status == PlayerStatus.PLAYING
        
        for item in self.children:
            if isinstance(item, ui.Button):
                # Disable all buttons if not playing
                item.disabled = not is_playing
                
                # Double button only available on first turn (2 cards)
                if item.custom_id == "btn_double":
                    item.disabled = not is_playing or not self.player.can_double

    @ui.button(label="🃏 Rút", style=discord.ButtonStyle.primary, custom_id="btn_hit")
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle Hit button - draw a card."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải lượt của bạn!", ephemeral=True
            )
            return

        await self.cog.player_hit(interaction, self.table, self.player)
        self._update_buttons()

    @ui.button(label="✋ Dằn", style=discord.ButtonStyle.secondary, custom_id="btn_stand")
    async def stand_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle Stand button - end turn."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải lượt của bạn!", ephemeral=True
            )
            return

        await self.cog.player_stand(interaction, self.table, self.player)

    @ui.button(label="💰 Gấp Đôi", style=discord.ButtonStyle.success, custom_id="btn_double")
    async def double_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle Double Down button - double bet and draw one card."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải lượt của bạn!", ephemeral=True
            )
            return

        await self.cog.player_double(interaction, self.table, self.player)

    async def on_timeout(self) -> None:
        """Handle view timeout - auto stand."""
        if self.player.status == PlayerStatus.PLAYING:
            self.player.status = PlayerStatus.STAND


# ==================== MULTIPLAYER LOBBY VIEW ====================

class LobbyView(ui.View):
    """View for multiplayer lobby with Join button."""

    def __init__(self, cog: "XiDachCog", table: Table, timeout: float = 35.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.table = table

    @ui.button(
        label="🎮 Tham Gia",
        style=discord.ButtonStyle.success,
        custom_id="btn_join_lobby"
    )
    async def join_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle join button click."""
        await self.cog.player_join_lobby(interaction, self.table)

    async def on_timeout(self) -> None:
        """Disable button on timeout."""
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True


# ==================== MULTIPLAYER BETTING VIEW ====================

class MultiBetView(ui.View):
    """View for multiplayer betting phase with preset and custom bet options."""

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
        """Create preset bet buttons with unique IDs per player.
        
        Layout Strategy:
        Row 0: Presets [50, 100, 500, 1k, 10k] (5 buttons)
        Row 1: Actions [Clear, Custom, All-in] (3 buttons)
        Row 2: Ready [Ready] (1 button)
        """
        uid = self.player.user_id
        
        # ROW 0: Presets
        for i, amount in enumerate(self.BET_AMOUNTS):
            button = ui.Button(
                label=f"+{amount:,}",
                style=discord.ButtonStyle.primary,
                custom_id=f"btn_bet_{amount}_{uid}",
                row=0
            )
            button.callback = self._make_bet_callback(amount)
            self.add_item(button)

        # ROW 1: Actions (Clear, Custom, All-in)
        # Clear Button
        clear_btn = ui.Button(
            label="🔄 Xoá Cược",
            style=discord.ButtonStyle.secondary,
            custom_id=f"btn_bet_clear_{uid}",
            row=1
        )
        clear_btn.callback = self._clear_bet_callback
        self.add_item(clear_btn)

        # Custom Bet
        custom_btn = ui.Button(
            label="✏️ Nhập Số",
            style=discord.ButtonStyle.secondary,
            custom_id=f"btn_bet_custom_{uid}",
            row=1
        )
        custom_btn.callback = self._custom_bet_callback
        self.add_item(custom_btn)

        # All-in
        all_in_btn = ui.Button(
            label="🔥 Tất Tay",
            style=discord.ButtonStyle.danger,
            custom_id=f"btn_bet_allin_{uid}",
            row=1
        )
        all_in_btn.callback = self._all_in_callback
        self.add_item(all_in_btn)

        # ROW 2: Ready
        ready_btn = ui.Button(
            label="✅ Sẵn Sàng",
            style=discord.ButtonStyle.success,
            custom_id=f"btn_ready_{uid}",
            row=2
        )
        ready_btn.callback = self._ready_callback
        self.add_item(ready_btn)

    def _make_bet_callback(self, amount: int):
        """Create callback for preset bet button."""
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.player.user_id:
                await interaction.response.send_message(
                    "❌ Đây không phải giao diện cược của bạn!", ephemeral=True
                )
                return
            
            await self.cog.process_bet(interaction, self.table, self.player.user_id, amount)
        return callback

    async def _custom_bet_callback(self, interaction: discord.Interaction) -> None:
        """Show custom bet modal."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải giao diện cược của bạn!", ephemeral=True
            )
            return
        modal = BetAmountModal(self.cog, self.table, self.player.user_id)
        await interaction.response.send_modal(modal)

    async def _all_in_callback(self, interaction: discord.Interaction) -> None:
        """Handle All-in button."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải giao diện cược của bạn!", ephemeral=True
            )
            return
        
        # Calculate max balance
        try:
            balance = await self.cog.get_user_seeds(self.player.user_id)
            if balance <= 0:
                await interaction.response.send_message(
                    "❌ Bạn không còn hạt nào để Tất Tay!", ephemeral=True
                )
                return
            
            await self.cog.process_bet(interaction, self.table, self.player.user_id, balance)
        except Exception as e:
            await self.cog.process_bet(interaction, self.table, self.player.user_id, balance)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Lỗi khi lấy số dư: {e}", ephemeral=True
            )

    async def _clear_bet_callback(self, interaction: discord.Interaction) -> None:
        """Handle Clear Bet button."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải giao diện cược của bạn!", ephemeral=True
            )
            return

        # Reset local bet counter
        self.player.bet = 0
        
        # Update view
        view = MultiBetView(self.cog, self.table, self.player)
        await interaction.response.edit_message(
            content=f"💰 **Đặt cược:**\n✅ Đã xoá cược! Hãy chọn mức cược mới.",
            view=view
        )

        # UPDATE LOBBY EMBED (Public) to reflect 0 bet
        try:
             # Replicate logic from cog.py to calculate remaining time
             # Assuming 30s lobby duration (hardcoded safe fallback or approximated)
             elapsed = time.time() - self.table.created_at
             remaining = max(0, 30 - int(elapsed)) 
             
             if self.table.message_id and interaction.channel:
                 lobby_msg = await interaction.channel.fetch_message(self.table.message_id)
                 embed = create_lobby_embed(self.table, remaining)
                 await lobby_msg.edit(embed=embed)
        except discord.NotFound:
             pass
        except Exception as e:
             # Log but don't crash user interaction (logger might not be available in view scope?)
             # self.cog.logger is available? No, cog logger is 'logger'.
             # Just suppress
             pass

    async def _ready_callback(self, interaction: discord.Interaction) -> None:
        """Handle ready button."""
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải giao diện cược của bạn!", ephemeral=True
            )
            return

        await self.cog.player_ready(interaction, self.table, self.player)

    async def on_timeout(self) -> None:
        """Disable all buttons on timeout."""
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True


# ==================== MULTIPLAYER GAME VIEW ====================

class MultiGameView(ui.View):
    """View for multiplayer game with Hit/Stand/Double buttons."""

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
        self.turn_msg = turn_msg  # Reference to current turn message
        self.channel = channel    # Channel to send new messages
        self.action_timestamp: float = 0.0  # Timestamp of last player action (for timer reset)

    def _is_game_active(self) -> bool:
        """Check if game is still active."""
        return self.table.status == TableStatus.PLAYING and self.table.current_player is not None

    def _is_current_player(self, user_id: int) -> bool:
        """Check if user is the current player."""
        current = self.table.current_player
        return current is not None and current.user_id == user_id

    @ui.button(label="🃏 Rút", style=discord.ButtonStyle.primary, custom_id="btn_hit_multi")
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle Hit button - resends message with new card image."""
        if not self._is_game_active():
            await interaction.response.send_message(
                "❌ Ván đấu đã kết thúc!", ephemeral=True
            )
            return
            
        if not self._is_current_player(interaction.user.id):
            await interaction.response.send_message(
                "❌ Chưa đến lượt của bạn!", ephemeral=True
            )
            return

        player = self.table.current_player
        await self.cog.player_hit_multi(interaction, self.table, player, self)

    @ui.button(label="✋ Dằn", style=discord.ButtonStyle.secondary, custom_id="btn_stand_multi")
    async def stand_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle Stand button."""
        if not self._is_game_active():
            await interaction.response.send_message(
                "❌ Ván đấu đã kết thúc!", ephemeral=True
            )
            return
            
        if not self._is_current_player(interaction.user.id):
            await interaction.response.send_message(
                "❌ Chưa đến lượt của bạn!", ephemeral=True
            )
            return

        player = self.table.current_player
        await self.cog.player_stand_multi(interaction, self.table, player, self)

    @ui.button(label="💰 Gấp Đôi", style=discord.ButtonStyle.success, custom_id="btn_double_multi")
    async def double_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """Handle Double Down button."""
        if not self._is_game_active():
            await interaction.response.send_message(
                "❌ Ván đấu đã kết thúc!", ephemeral=True
            )
            return
            
        if not self._is_current_player(interaction.user.id):
            await interaction.response.send_message(
                "❌ Chưa đến lượt của bạn!", ephemeral=True
            )
            return

        player = self.table.current_player
        if not player.can_double:
            await interaction.response.send_message(
                "❌ Bạn không thể gấp đôi lúc này!", ephemeral=True
            )
            return

        await self.cog.player_double_multi(interaction, self.table, player, self)

    async def on_timeout(self) -> None:
        """Disable all buttons on timeout."""
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True


# ==================== EMBED BUILDERS ====================

def create_solo_game_embed(table: Table, player: Player, hide_dealer: bool = True) -> discord.Embed:
    """Create embed for solo game display.
    
    Args:
        table (Table): Game table.
        player (Player): The player.
        hide_dealer (bool): Whether to hide dealer's first card.
        
    Returns:
        discord.Embed: The game embed.
    """
    embed = discord.Embed(
        title="🎰 XÌ DÁCH - Chơi Đơn",
        color=discord.Color.gold()
    )

    # Dealer's hand
    dealer_display = format_hand(table.dealer_hand, hide_first=hide_dealer)
    if hide_dealer:
        dealer_value = "?"
    else:
        dealer_value = str(table.dealer_value)
        if table.dealer_type != HandType.NORMAL:
            dealer_value += f" {get_hand_description(table.dealer_type)}"
    
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{dealer_display}\n📊 Điểm: **{dealer_value}**",
        inline=False
    )

    # Player's hand
    player_display = format_hand(player.hand)
    player_value = str(player.hand_value)
    if player.hand_type != HandType.NORMAL:
        player_value += f" {get_hand_description(player.hand_type)}"
    
    embed.add_field(
        name=f"🎴 {player.username}",
        value=f"{player_display}\n📊 Điểm: **{player_value}**\n💰 Cược: **{player.bet:,}** hạt",
        inline=False
    )

    # Status
    if player.status == PlayerStatus.PLAYING:
        embed.set_footer(text="💡 Chọn Rút thêm bài, Dằn để dừng, hoặc Gấp Đôi tiền cược")
    elif player.status == PlayerStatus.BUST:
        embed.set_footer(text="💥 Bạn đã quá 21 điểm!")
        embed.color = discord.Color.red()
    elif player.status == PlayerStatus.BLACKJACK:
        embed.set_footer(text="🎉 Bạn có Xì Dách/Xì Bàn!")
        embed.color = discord.Color.green()

    return embed


def create_result_embed(
    table: Table,
    player: Player,
    result: str,
    payout: int
) -> discord.Embed:
    """Create embed for game result.
    
    Args:
        table (Table): Game table.
        player (Player): The player.
        result (str): 'win', 'lose', or 'push'.
        payout (int): Amount won/lost.
        
    Returns:
        discord.Embed: Result embed.
    """
    if result == "win":
        title = "🎉 THẮNG!"
        color = discord.Color.green()
        description = f"Bạn thắng **{payout:,}** hạt!"
    elif result == "lose":
        title = "😢 THUA!"
        color = discord.Color.red()
        description = f"Bạn thua **{player.bet:,}** hạt!"
    else:
        title = "🤝 HÒA!"
        color = discord.Color.blue()
        description = "Bạn được hoàn lại tiền cược!"

    embed = discord.Embed(title=title, description=description, color=color)

    # Show final hands
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{format_hand(table.dealer_hand)}\n📊 Điểm: **{table.dealer_value}** {get_hand_description(table.dealer_type)}",
        inline=True
    )
    embed.add_field(
        name=f"🎴 {player.username}",
        value=f"{format_hand(player.hand)}\n📊 Điểm: **{player.hand_value}** {get_hand_description(player.hand_type)}",
        inline=True
    )

    return embed


def create_lobby_embed(table: Table, time_remaining: Optional[int] = None) -> discord.Embed:
    """Create embed for multiplayer lobby with clean design.
    
    Args:
        table (Table): Game table.
        time_remaining (int, optional): Seconds remaining. None to hide timer.
        
    Returns:
        discord.Embed: Lobby embed.
    """
    
    embed = discord.Embed(
        title="🎰 XÌ DÁCH",
        description="**Sòng nhiều người**",
        color=discord.Color.green()
    )
    
    if time_remaining is not None and time_remaining > 0:
        end_time = int(time.time() + time_remaining)
        embed.add_field(name="⏳ Thời gian", value=f"<t:{end_time}:R>", inline=True)
    else:
        embed.add_field(name="⏳ Thời gian", value="**Đã hết thời gian tham gia**", inline=True)

    # Count stats
    joined_count = sum(1 for p in table.players.values() if p.status == PlayerStatus.WAITING or p.is_ready)
    ready_count = sum(1 for p in table.players.values() if p.is_ready)
    total_bet = sum(p.bet for p in table.players.values())

    # Stats (simplified)
    embed.add_field(
        name="📊 Thống kê",
        value=f"Tham gia: **{joined_count}** • Sẵn sàng: **{ready_count}** • Tổng cược: **{total_bet:,}**",
        inline=False
    )

    # List players - clean format
    players_list = []
    for uid, player in table.players.items():
        if player.is_ready:
            status = "✅"
        elif player.status == PlayerStatus.WAITING:
            status = "⏳"
        else:
            status = "👀"
        
        bet_display = f"{player.bet:,}" if player.bet > 0 else "—"
        players_list.append(f"{status} <@{uid}> • **{bet_display}**")

    if players_list:
        embed.add_field(
            name="👥 Người chơi",
            value="\n".join(players_list),
            inline=False
        )
    else:
        embed.add_field(
            name="👥 Người chơi",
            value="*Chờ người chơi...*",
            inline=False
        )

    embed.set_footer(text="Tham Gia → Đặt cược → Sẵn Sàng")

    return embed


def create_multi_game_embed(table: Table) -> discord.Embed:
    """Create embed for multiplayer game.
    
    Args:
        table (Table): Game table.
        
    Returns:
        discord.Embed: Game embed.
    """
    embed = discord.Embed(
        title="🎰 XÌ DÁCH - Ván Đấu",
        color=discord.Color.gold()
    )

    # Dealer's hand
    hide_dealer = table.status != TableStatus.DEALER_TURN and table.status != TableStatus.FINISHED
    dealer_display = format_hand(table.dealer_hand, hide_first=hide_dealer)
    dealer_value = "?" if hide_dealer else str(table.dealer_value)
    
    embed.add_field(
        name="🤖 Nhà Cái",
        value=f"{dealer_display}\n📊 Điểm: **{dealer_value}**",
        inline=False
    )

    # All players' hands
    for uid, player in table.players.items():
        if player.bet <= 0:
            continue  # Skip spectators

        status_emoji = {
            PlayerStatus.PLAYING: "🎮",
            PlayerStatus.WAITING: "⏳",
            PlayerStatus.STAND: "✋",
            PlayerStatus.BUST: "💥",
            PlayerStatus.BLACKJACK: "🎰",
        }.get(player.status, "👤")

        player_display = format_hand(player.hand)
        hand_desc = get_hand_description(player.hand_type) if player.hand_type != HandType.NORMAL else ""
        
        embed.add_field(
            name=f"{status_emoji} {player.username}",
            value=f"{player_display}\n📊 Điểm: **{player.hand_value}** {hand_desc}\n💰 Cược: **{player.bet:,}**",
            inline=True
        )

    # Current player indicator
    if table.current_player:
        embed.set_footer(text=f"🎮 Lượt của: {table.current_player.username}")

    return embed
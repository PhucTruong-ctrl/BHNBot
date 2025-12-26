"""
Xi Dach (Vietnamese Blackjack) - Data Models

Contains Player, Table, and GameManager data structures for managing game state.
"""
import random
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import discord

from .game import Card, Deck, calculate_hand_value, determine_hand_type, HandType


class PlayerStatus(Enum):
    """Player status in a Xi Dach game."""
    WAITING = "waiting"       # Waiting for turn
    PLAYING = "playing"       # Currently playing their turn
    STAND = "stand"           # Stood (finished)
    BUST = "bust"             # Busted (over 21)
    BLACKJACK = "blackjack"   # Got Xi Dach/Xi Ban
    SPECTATING = "spectating" # Just watching (multiplayer)


class TableStatus(Enum):
    """Table/Game status."""
    LOBBY = "lobby"           # Waiting for players
    BETTING = "betting"       # Players placing bets
    PLAYING = "playing"       # Game in progress
    DEALER_TURN = "dealer"    # Dealer's turn
    FINISHED = "finished"     # Game ended


@dataclass
class Player:
    """Represents a player in Xi Dach game.
    
    Attributes:
        user_id (int): Discord user ID.
        username (str): Display name.
        bet (int): Current bet amount.
        hand (List[Card]): Cards in hand.
        status (PlayerStatus): Current status.
        is_doubled (bool): Whether player doubled down.
    """
    user_id: int
    username: str
    bet: int = 0
    hand: List[Card] = field(default_factory=list)
    status: PlayerStatus = PlayerStatus.WAITING
    is_doubled: bool = False
    is_ready: bool = False
    interaction: Optional[discord.Interaction] = None

    @property
    def hand_value(self) -> int:
        """Get current hand value."""
        return calculate_hand_value(self.hand)

    @property
    def hand_type(self) -> HandType:
        """Get current hand type."""
        _, hand_type = determine_hand_type(self.hand)
        return hand_type

    @property
    def is_bust(self) -> bool:
        """Check if player busted."""
        return self.hand_value > 21

    @property
    def can_double(self) -> bool:
        """Check if player can double down (only on first turn with 2 cards)."""
        return len(self.hand) == 2 and not self.is_doubled

    def add_card(self, card: Card) -> None:
        """Add a card to player's hand.
        
        Args:
            card (Card): Card to add.
        """
        self.hand.append(card)
        
        # Auto-update status on bust
        if self.hand_value > 21:
            self.status = PlayerStatus.BUST
        # Check for Xi Ban ONLY (2 Aces = instant win)
        # Xi Dach (A + 10-value) does NOT auto-win - player can choose to hit/stand
        elif len(self.hand) == 2:
            _, hand_type = determine_hand_type(self.hand)
            if hand_type == HandType.XI_BAN:  # Only AA = auto win
                self.status = PlayerStatus.BLACKJACK

    def reset(self) -> None:
        """Reset player for new game."""
        self.bet = 0
        self.hand = []
        self.status = PlayerStatus.WAITING
        self.is_doubled = False
        self.is_ready = False


@dataclass
class Table:
    """Represents a Xi Dach game table.
    
    Attributes:
        table_id (str): Unique table identifier.
        channel_id (int): Discord channel ID.
        host_id (int): User ID of table host.
        message_id (Optional[int]): Discord message ID for the game.
        players (Dict[int, Player]): Active players by user_id.
        spectators (Set[int]): User IDs of spectators.
        dealer_hand (List[Card]): Dealer's cards.
        deck (Deck): Card deck.
        status (TableStatus): Current table status.
        current_player_idx (int): Index of current player in turn order.
        created_at (float): Timestamp of table creation.
        is_solo (bool): True if single-player game.
    """
    table_id: str
    channel_id: int
    host_id: int
    message_id: Optional[int] = None
    players: Dict[int, Player] = field(default_factory=dict)
    spectators: Set[int] = field(default_factory=set)
    dealer_hand: List[Card] = field(default_factory=list)
    deck: Deck = field(default_factory=Deck)
    status: TableStatus = TableStatus.LOBBY
    current_player_idx: int = 0
    created_at: float = field(default_factory=time.time)
    is_solo: bool = False
    _turn_order: List[int] = field(default_factory=list)
    # Shared state for turn management (used by countdown loop and views)
    turn_action_timestamp: float = 0.0  # Timestamp of last player action
    current_turn_msg: Optional[object] = None  # Reference to current turn message

    @property
    def dealer_value(self) -> int:
        """Get dealer's hand value."""
        return calculate_hand_value(self.dealer_hand)

    @property
    def dealer_type(self) -> HandType:
        """Get dealer's hand type."""
        _, hand_type = determine_hand_type(self.dealer_hand)
        return hand_type

    @property
    def current_player(self) -> Optional[Player]:
        """Get the current player whose turn it is."""
        if not self._turn_order:
            return None
        if self.current_player_idx >= len(self._turn_order):
            return None
        user_id = self._turn_order[self.current_player_idx]
        return self.players.get(user_id)

    @property
    def active_players_count(self) -> int:
        """Count of players who are playing or ready (not spectating)."""
        return sum(1 for p in self.players.values() if p.status != PlayerStatus.SPECTATING)

    @property
    def ready_players_count(self) -> int:
        """Count of players who are ready."""
        return sum(1 for p in self.players.values() if p.is_ready)

    @property
    def time_elapsed(self) -> float:
        """Seconds since table was created."""
        return time.time() - self.created_at

    def add_player(self, user_id: int, username: str, bet: int = 0) -> Player:
        """Add a player to the table.
        
        Args:
            user_id (int): Discord user ID.
            username (str): Display name.
            bet (int): Initial bet amount.
            
        Returns:
            Player: The created player.
        """
        player = Player(user_id=user_id, username=username, bet=bet)
        self.players[user_id] = player
        return player

    def remove_player(self, user_id: int) -> None:
        """Remove a player from the table.
        
        Args:
            user_id (int): Discord user ID.
        """
        if user_id in self.players:
            del self.players[user_id]
        if user_id in self._turn_order:
            self._turn_order.remove(user_id)

    def start_game(self) -> None:
        """Initialize game: deal cards to all players and dealer."""
        self.status = TableStatus.PLAYING
        self.deck.reset()
        self.dealer_hand = []
        
        # Build turn order from ready players
        self._turn_order = [
            uid for uid, p in self.players.items() 
            if p.is_ready and p.bet > 0
        ]
        # Randomize turn order
        random.shuffle(self._turn_order)
        self.current_player_idx = 0

        # Deal 2 cards to each player
        for uid in self._turn_order:
            player = self.players[uid]
            player.hand = []
            player.status = PlayerStatus.WAITING
            player.add_card(self.deck.draw_one())
            player.add_card(self.deck.draw_one())
            
            # Check for Instant Win (Xi Dach/Xi Ban)
            if player.hand_type in (HandType.XI_DACH, HandType.XI_BAN):
                player.status = PlayerStatus.BLACKJACK

        # Deal 2 cards to dealer
        self.dealer_hand = self.deck.draw(2)

        # Set first player as active
        if self._turn_order:
            first_player = self.players[self._turn_order[0]]
            first_player.status = PlayerStatus.PLAYING

    def next_turn(self) -> Optional[Player]:
        """Move to next player's turn.
        
        Returns:
            Optional[Player]: Next player, or None if all done.
        """
        # Mark current player as stood if still playing
        if self.current_player and self.current_player.status == PlayerStatus.PLAYING:
            self.current_player.status = PlayerStatus.STAND

        self.current_player_idx += 1

        if self.current_player_idx >= len(self._turn_order):
            return None  # All players done, dealer's turn

        next_player = self.current_player
        if next_player:
            next_player.status = PlayerStatus.PLAYING
        return next_player

    def dealer_play(self) -> None:
        """Set status to dealer turn (drawing handled by Cog for animation)."""
        self.status = TableStatus.DEALER_TURN

    def is_game_over(self) -> bool:
        """Check if all players have finished their turns."""
        return all(
            p.status in (PlayerStatus.STAND, PlayerStatus.BUST, PlayerStatus.BLACKJACK)
            for p in self.players.values()
            if p.bet > 0
        )

    def get_dealer_decision(self) -> tuple[str, str]:
        """Decide Dealer's next move based on competitive logic.
        
        Returns:
            tuple[str, str]: (action, reason)
                action: 'hit' or 'stand'
                reason: string key for trash talk or logging
        """
        value = self.dealer_value
        hand_size = len(self.dealer_hand)

        # 0. HARD STOP: 5 Cards (Ngũ Linh) or 21 Points
        # If we have 5 cards and are not busted, we MUST stand. It's the highest hand type (usually).
        if hand_size == 5 and value <= 21:
            return "stand", "ngu_linh_achieved"
        
        # 0.5 HARD STOP: >= 21 Points (Normal)
        if value >= 21:
             return "stand", "max_point"

        # 1. BASE RULE: Under 16 MUST hit
        if value < 16:
            return "hit", "under_16"

        # 2. ANALYZE BOARD
        winning_count = 0
        losing_count = 0
        push_count = 0
        
        active_players = [
            p for p in self.players.values() 
            if p.bet > 0 and p.status in (PlayerStatus.STAND, PlayerStatus.BLACKJACK, PlayerStatus.PLAYING)
        ]
        
        if not active_players:
            return "stand", "safe"

        for p in active_players:
            # Player Bust/Low (<16) = Dealer Wins automatically
            if p.status == PlayerStatus.BUST or (p.hand_value < 16 and p.hand_type == HandType.NORMAL):
                winning_count += 1
                continue
                
            p_val = p.hand_value
            # Special hands
            if p.hand_type in (HandType.XI_BAN, HandType.XI_DACH):
                losing_count += 1
            elif p.hand_type == HandType.NGU_LINH:
                if self.dealer_type == HandType.NGU_LINH:
                    if value > p_val: winning_count += 1
                    elif value < p_val: losing_count += 1
                    else: push_count += 1
                else: 
                    losing_count += 1
            else:
                # Normal vs Normal
                if value > p_val:
                    winning_count += 1
                elif value < p_val:
                    losing_count += 1
                else:
                    push_count += 1
        
        # 3. MAJORITY RULE LOGIC (User Request)
        # "If we beat >= 50% of players, STAND. Else, HIT (unless too risky)."
        total_opponents = winning_count + losing_count + push_count
        
        if total_opponents > 0:
            # If we are winning/pushing against at least half the table -> PLAY SAFE
            if (winning_count + push_count) >= (total_opponents / 2.0):
                return "stand", "safe_majority"
                
            # If we are losing to the majority -> CONSIDER RISK
            else:
                # User Rule: "If losing, risk it... UNLESS risk is too high."
                # Risk Assessment: 
                # If Score >= 18: Risk of busting is very high. 
                # User guidance: "If opponent has 21, don't try to beat them if risky."
                if value >= 18:
                     return "stand", "cut_losses"
                
                # Check Ngu Linh Potential (Specific commentary)
                # Min points needed to stay under 21
                cards_needed = 5 - hand_size
                min_points_needed = cards_needed * 1
                is_ngu_linh_possible = (value + min_points_needed) <= 21

                if hand_size == 4 and is_ngu_linh_possible:
                     return "hit", "ngu_linh_attempt"
                
                # Desperation Hit (Since we are losing and score < 18)
                return "hit", "desperate_hit"

        # Default fallback
        return "stand", "safe"


class GameManager:
    """Singleton manager for all active Xi Dach tables.
    
    Manages table creation, lookup, and cleanup.
    """
    _instance: Optional["GameManager"] = None

    def __new__(cls) -> "GameManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tables: Dict[int, Table] = {}  # channel_id -> Table
            cls._instance._user_tables: Dict[int, int] = {}  # user_id -> channel_id
        return cls._instance

    @property
    def tables(self) -> Dict[int, Table]:
        """Get all active tables."""
        return self._tables

    def create_table(
        self,
        channel_id: int,
        host_id: int,
        is_solo: bool = False
    ) -> Optional[Table]:
        """Create a new table in a channel.
        
        Args:
            channel_id (int): Discord channel ID.
            host_id (int): User ID of table creator.
            is_solo (bool): Whether this is a solo game.
            
        Returns:
            Optional[Table]: The created table, or None if channel already has a table.
        """
        if channel_id in self._tables:
            return None  # Channel already has active table

        table_id = f"xd_{channel_id}_{int(time.time() * 1000)}"
        table = Table(
            table_id=table_id,
            channel_id=channel_id,
            host_id=host_id,
            is_solo=is_solo
        )
        self._tables[channel_id] = table
        self._user_tables[host_id] = channel_id
        return table

    def get_table(self, channel_id: int) -> Optional[Table]:
        """Get table by channel ID.
        
        Args:
            channel_id (int): Discord channel ID.
            
        Returns:
            Optional[Table]: The table, or None if not found.
        """
        return self._tables.get(channel_id)

    def get_user_table(self, user_id: int) -> Optional[Table]:
        """Get table that a user is in.
        
        Args:
            user_id (int): Discord user ID.
            
        Returns:
            Optional[Table]: The table, or None if user not in any table.
        """
        channel_id = self._user_tables.get(user_id)
        if channel_id:
            return self._tables.get(channel_id)
        return None

    def remove_table(self, channel_id: int) -> None:
        """Remove a table.
        
        Args:
            channel_id (int): Discord channel ID.
        """
        table = self._tables.pop(channel_id, None)
        if table:
            # Clean up user mappings
            for user_id in table.players:
                self._user_tables.pop(user_id, None)

    def add_user_to_table(self, user_id: int, channel_id: int) -> None:
        """Track that a user has joined a table.
        
        Args:
            user_id (int): Discord user ID.
            channel_id (int): Discord channel ID.
        """
        self._user_tables[user_id] = channel_id

    def cleanup_old_tables(self, max_age_seconds: int = 600) -> int:
        """Remove tables older than max_age_seconds.
        
        Args:
            max_age_seconds (int): Maximum table age in seconds.
            
        Returns:
            int: Number of tables cleaned up.
        """
        now = time.time()
        to_remove = [
            cid for cid, table in self._tables.items()
            if now - table.created_at > max_age_seconds
        ]
        for cid in to_remove:
            self.remove_table(cid)
        return len(to_remove)


# Global singleton instance
game_manager = GameManager()

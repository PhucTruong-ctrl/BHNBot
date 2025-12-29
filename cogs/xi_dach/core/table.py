"""Table domain model."""

import asyncio
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

from .deck import Card, Deck
from .player import Player, PlayerStatus

class TableStatus(Enum):
    """Table/Game status."""
    LOBBY = "lobby"           # Waiting for players
    BETTING = "betting"       # Players placing bets
    PLAYING = "playing"       # Game in progress
    DEALER_TURN = "dealer"    # Dealer's turn
    FINISHED = "finished"     # Game ended

@dataclass
class Table:
    """Represents a Xi Dach game table."""
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
    # Shared state
    turn_action_timestamp: float = 0.0
    current_turn_msg: Optional[object] = None
    current_view: Optional[object] = None  # MultiGameView for cleanup
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def dealer_value(self) -> int:
        from ..services.hand_service import calculate_hand_value
        return calculate_hand_value(self.dealer_hand)

    @property
    def dealer_type(self):
        from ..services.hand_service import determine_hand_type
        _, hand_type = determine_hand_type(self.dealer_hand)
        return hand_type

    @property
    def current_player(self) -> Optional[Player]:
        if not self._turn_order:
            return None
        if self.current_player_idx >= len(self._turn_order):
            return None
        user_id = self._turn_order[self.current_player_idx]
        return self.players.get(user_id)

    @property
    def active_players_count(self) -> int:
        return sum(1 for p in self.players.values() if p.status != PlayerStatus.SPECTATING)

    @property
    def ready_players_count(self) -> int:
        return sum(1 for p in self.players.values() if p.is_ready)

    @property
    def time_elapsed(self) -> float:
        return time.time() - self.created_at

    def add_player(self, user_id: int, username: str, bet: int = 0) -> Player:
        player = Player(user_id=user_id, username=username, bet=bet)
        self.players[user_id] = player
        return player

    def remove_player(self, user_id: int) -> None:
        if user_id in self.players:
            del self.players[user_id]
        if user_id in self._turn_order:
            self._turn_order.remove(user_id)

    def start_game(self) -> None:
        from ..services.hand_service import HandType, determine_hand_type

        self.status = TableStatus.PLAYING
        self.deck.reset()
        self.dealer_hand = []
        
        self._turn_order = [
            uid for uid, p in self.players.items() 
            if p.bet > 0
        ]
        random.shuffle(self._turn_order)
        self.current_player_idx = 0

        # Deal
        for uid in self._turn_order:
            player = self.players[uid]
            player.hand = []
            player.status = PlayerStatus.WAITING
            player.add_card(self.deck.draw_one())
            player.add_card(self.deck.draw_one())
            
            # Instant Win Check
            _, p_type = determine_hand_type(player.hand)
            if p_type in (HandType.XI_DACH, HandType.XI_BAN):
                player.status = PlayerStatus.BLACKJACK

        self.dealer_hand = self.deck.draw(2)

        if self._turn_order:
            first_player = self.players[self._turn_order[0]]
            first_player.status = PlayerStatus.PLAYING

    def next_turn(self) -> Optional[Player]:
        if self.current_player and self.current_player.status == PlayerStatus.PLAYING:
            self.current_player.status = PlayerStatus.STAND

        self.current_player_idx += 1

        if self.current_player_idx >= len(self._turn_order):
            return None

        next_player = self.current_player
        if next_player:
            next_player.status = PlayerStatus.PLAYING
        return next_player

    def dealer_play(self) -> None:
        self.status = TableStatus.DEALER_TURN

    def is_game_over(self) -> bool:
        return all(
            p.status in (PlayerStatus.STAND, PlayerStatus.BUST, PlayerStatus.BLACKJACK)
            for p in self.players.values()
            if p.bet > 0
        )

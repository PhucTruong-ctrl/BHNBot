"""Data models for Bau Cua game state management.

Contains dataclasses for managing game state, bets, and results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import time


@dataclass
class BetData:
    """Represents a single bet placed by a user.
    
    Attributes:
        user_id: Discord user ID who placed the bet
        animal_key: Key of the animal bet on (e.g., 'bau', 'cua')
        amount: Number of seeds bet
    """
    user_id: int
    animal_key: str
    amount: int


@dataclass
class GameState:
    """Active game state for a channel.
    
    Tracks all game information including game ID, timing, and placed bets.
    Uses in-memory storage for active games only.
    
    Attributes:
        game_id: Unique identifier for this game session
        channel_id: Discord channel ID where game is running
        start_time: Unix timestamp when game started
        bets: Dictionary mapping user_id to list of (animal_key, amount) tuples
    """
    game_id: str
    channel_id: int
    start_time: float
    bets: Dict[int, List[Tuple[str, int]]] = field(default_factory=dict)
    
    @classmethod
    def create_new(cls, channel_id: int) -> 'GameState':
        """Create a new game instance for the given channel.
        
        Generates a unique game_id using channel_id and current timestamp.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            New GameState instance with empty bets
        """
        game_id = f"{channel_id}_{int(time.time() * 1000)}"
        return cls(
            game_id=game_id,
            channel_id=channel_id,
            start_time=time.time(),
            bets={}
        )
    
    def add_bet(self, user_id: int, animal_key: str, amount: int) -> None:
        """Add a bet for the specified user.
        
        If user has no prior bets, creates new entry in bets dict.
        Allows multiple bets per user on different animals.
        
        Args:
            user_id: Discord user ID
            animal_key: Animal to bet on
            amount: Number of seeds to bet
        """
        if user_id not in self.bets:
            self.bets[user_id] = []
        self.bets[user_id].append((animal_key, amount))
    
    def get_user_bets(self, user_id: int) -> List[Tuple[str, int]]:
        """Retrieve all bets placed by a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of (animal_key, amount) tuples, empty list if no bets
        """
        return self.bets.get(user_id, [])
    
    def get_total_bet_amount(self, user_id: int) -> int:
        """Calculate total seeds bet by a user across all their bets.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Sum of all bet amounts for user
        """
        return sum(amount for _, amount in self.get_user_bets(user_id))
    
    def has_bets(self) -> bool:
        """Check if any bets have been placed in this game.
        
        Returns:
            True if at least one bet exists
        """
        return len(self.bets) > 0
    
    def get_total_players(self) -> int:
        """Get count of unique players who placed bets.
        
        Returns:
            Number of unique user IDs in bets dict
        """
        return len(self.bets)
    
    def get_total_bets_count(self) -> int:
        """Get total number of individual bets placed.
        
        Returns:
            Sum of all bet counts across all users
        """
        return sum(len(user_bets) for user_bets in self.bets.values())


@dataclass
class GameResult:
    """Results data for a completed game.
    
    Stores the dice roll results and calculated payouts.
    
    Attributes:
        result1: First dice result (animal key)
        result2: Second dice result (animal key)  
        result3: Third dice result (animal key)
        payouts: Dictionary mapping user_id to total payout amount
    """
    result1: str
    result2: str
    result3: str
    payouts: Dict[int, int] = field(default_factory=dict)
    
    def get_results_tuple(self) -> Tuple[str, str, str]:
        """Get dice results as a tuple.
        
        Returns:
            Tuple of (result1, result2, result3)
        """
        return (self.result1, self.result2, self.result3)
    
    def count_matches(self, animal_key: str) -> int:
        """Count how many times an animal appeared in the results.
        
        Args:
            animal_key: Animal to count
            
        Returns:
            Number of matches (0-3)
        """
        results = [self.result1, self.result2, self.result3]
        return sum(1 for r in results if r == animal_key)

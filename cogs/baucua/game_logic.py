"""Core game logic and mechanics for Bau Cua.

Manages game state, betting, dice rolling, and results calculation.
"""

import discord
import random
import asyncio
import time
from typing import Dict, Optional
from core.logging import setup_logger
from core.logging import setup_logger
from database_manager import get_user_balance, add_seeds, get_or_create_user, batch_update_seeds

from .constants import (
    ANIMAL_LIST,
    BETTING_TIME_SECONDS,
    ROLL_ANIMATION_DURATION,
    ROLL_ANIMATION_INTERVAL,
    MAX_BET_AMOUNT,
    MIN_TIME_BEFORE_CUTOFF
)
from .models import GameState
from .helpers import create_rolling_text, create_result_display, calculate_payout

logger = setup_logger("BauCuaGame", "logs/cogs/baucua.log")


class GameManager:
    """Manages Bau Cua game flow and state.
    
    Handles:
    - Game creation and lifecycle
    - Bet processing and validation
    - Dice rolling animation
    - Results calculation
    - Seed balance updates
    
    Attributes:
        bot: Discord bot instance
        active_games: Dict mapping channel_id to GameState
    """
    
    def __init__(self, bot):
        """Initialize game manager.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.active_games: Dict[int, GameState] = {}
    
    def is_game_active(self, channel_id: int) -> bool:
        """Check if a game is currently active in the channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if active game exists
        """
        return channel_id in self.active_games
    
    def create_game(self, channel_id: int) -> GameState:
        """Create and register a new game for the channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            New GameState instance
            
        Raises:
            RuntimeError: If game already exists in channel
        """
        if self.is_game_active(channel_id):
            raise RuntimeError(f"Game already active in channel {channel_id}")
        
        game_state = GameState.create_new(channel_id)
        self.active_games[channel_id] = game_state
        
        logger.info(
            f"[GAME_CREATE] game_id={game_state.game_id} channel_id={channel_id}"
        )
        
        return game_state
    
    def get_game(self, channel_id: int) -> Optional[GameState]:
        """Retrieve active game for channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            GameState if exists, None otherwise
        """
        return self.active_games.get(channel_id)
    
    def end_game(self, channel_id: int) -> None:
        """Remove game from active games.
        
        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.active_games:
            game_id = self.active_games[channel_id].game_id
            del self.active_games[channel_id]
            logger.info(f"[GAME_END] game_id={game_id} channel_id={channel_id}")
    
    async def get_user_seeds(self, user_id: int) -> int:
        """Get user's current seed balance.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Current seed balance
        """
        return await get_user_balance(user_id)
    
    async def update_seeds(self, user_id: int, amount: int) -> None:
        """Update user's seed balance (can be negative).
        
        Ensures user exists before updating and logs the transaction.
        
        Args:
            user_id: Discord user ID
            amount: Hạt to add (negative to deduct)
        """
        # Ensure user exists
        await get_or_create_user(user_id, f"User#{user_id}")
        
        # Track balance before/after
        balance_before = await get_user_balance(user_id)
        reason = 'baucua_bet' if amount < 0 else 'baucua_win'
        await add_seeds(user_id, amount, reason, 'baucua')
        balance_after = balance_before + amount
        
        logger.info(
            f"[SEED_UPDATE] user_id={user_id} change={amount:+d} "
            f"before={balance_before} after={balance_after}"
        )
    
    async def add_bet(
        self,
        ctx_or_interaction,
        game_id: str,
        animal_key: str,
        bet_amount: int
    ) -> None:
        """Process a bet from a user.
        
        Supports both Slash Command (Interaction) and Prefix Command (Context).
        
        Validates:
        - Game is still active
        - Sufficient time remaining
        - Bet amount within limits
        - User has enough seeds
        
        If valid, deducts seeds and adds bet to game state.
        
        Args:
            ctx_or_interaction: Context or Interaction
            game_id: Game session ID
            animal_key: Animal being bet on
            bet_amount: Number of seeds to bet
        """
        from .helpers import unified_send
        
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        channel = ctx_or_interaction.channel
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        
        channel_id = channel.id
        user_id = user.id
        
        # Check if game still active
        game_state = self.get_game(channel_id)
        if not game_state or game_state.game_id != game_id:
            await unified_send(ctx_or_interaction, "❌ Game đã kết thúc!", ephemeral=True)
            return
        
        # Check betting time remaining (must have at least MIN_TIME_BEFORE_CUTOFF seconds left)
        time_remaining = BETTING_TIME_SECONDS - int(time.time() - game_state.start_time)
        if time_remaining < MIN_TIME_BEFORE_CUTOFF:
            await unified_send(
                ctx_or_interaction,
                f"⏰ Hết thời gian cược rồi! (Còn dưới {MIN_TIME_BEFORE_CUTOFF} giây)",
                ephemeral=True
            )
            return
        
        # Validate bet amount (max limit)
        if bet_amount > MAX_BET_AMOUNT:
            await unified_send(
                ctx_or_interaction,
                f"❌ Số tiền cược quá lớn!\nTối đa: {MAX_BET_AMOUNT:,} | Bạn cược: {bet_amount:,}",
                ephemeral=True
            )
            return
        
        if bet_amount <= 0:
            await unified_send(ctx_or_interaction, "❌ Số tiền cược không hợp lệ!", ephemeral=True)
            return
        
        # Check if user has enough seeds
        user_seeds = await self.get_user_seeds(user_id)
        if user_seeds < bet_amount:
            await unified_send(
                ctx_or_interaction,
                f"❌ Bạn không đủ hạt!\nCần: {bet_amount:,} | Hiện có: {user_seeds:,}",
                ephemeral=True
            )
            return
        
        # Deduct seeds FIRST
        await self.update_seeds(user_id, -bet_amount)
        
        # THEN add to bets dictionary with safety check
        try:
            # Verify game still exists (race condition check)
            if channel_id in self.active_games:
                game_state.add_bet(user_id, animal_key, bet_amount)
            else:
                # Game was deleted, refund the user
                await self.update_seeds(user_id, bet_amount)
                await unified_send(
                    ctx_or_interaction,
                    "❌ Game đã kết thúc khi bạn cược! Tiền đã hoàn lại.",
                    ephemeral=True
                )
                return
                
        except Exception as e:
            # If adding bet fails, refund the user
            await self.update_seeds(user_id, bet_amount)
            logger.error(f"Error adding bet: {e}", exc_info=True)
            await unified_send(
                ctx_or_interaction,
                "❌ Lỗi khi xử lý cược! Tiền đã hoàn lại.",
                ephemeral=True
            )
            return
        
        # Show bet confirmation
        from .constants import ANIMALS
        await unified_send(
            ctx_or_interaction,
            f"✅ Bạn đã cược **{bet_amount:,} hạt** vào "
            f"**{ANIMALS[animal_key]['name']}** {ANIMALS[animal_key]['emoji']}",
            ephemeral=True
        )
        
        logger.info(
            f"[BET_PLACED] user={user.name} (id={user_id}) "
            f"amount={bet_amount} animal={animal_key} game_id={game_id}"
        )
    
    async def roll_dice(self) -> tuple:
        """Roll three dice and return results.
        
        Returns:
            Tuple of (result1, result2, result3) with animal keys
        """
        return tuple(random.choices(ANIMAL_LIST, k=3))
    
    async def animate_roll(
        self,
        message: discord.Message,
        duration: float = ROLL_ANIMATION_DURATION
    ) -> tuple:
        """Animate dice rolling with sequential stopping for dramatic effect.
        
        Animation phases:
        1. All 3 dice roll together (first 50% of duration)
        2. Dice 1 stops, 2 & 3 continue (pause 1s)
        3. Dice 2 stops, only 3 continues (pause 1s)
        4. Dice 3 stops (final result)
        
        Display: Always shows exactly 3 emojis (no extra symbols)
        
        Args:
            message: Discord message to edit
            duration: Animation duration in seconds
            
        Returns:
            Final dice results as tuple (result1, result2, result3)
        """
        from .constants import DICE_STOP_INTERVAL
        from .helpers import create_partial_result_text
        
        # Phase 1: All dice rolling (first half of duration)
        phase1_duration = duration * 0.5
        start_time = time.time()
        
        while time.time() - start_time < phase1_duration:
            r1, r2, r3 = await self.roll_dice()
            rolling_text = create_rolling_text(r1, r2, r3)
            
            try:
                await message.edit(content=rolling_text, embed=None)
            except discord.HTTPException as e:
                logger.error(f"Error updating roll animation: {e}")
            
            await asyncio.sleep(ROLL_ANIMATION_INTERVAL)
        
        # Determine final results
        final_result1, final_result2, final_result3 = await self.roll_dice()
        
        # Phase 2: Stop dice 1, continue 2 & 3
        partial_text = create_partial_result_text(
            result1=final_result1,
            result2=None,
            result3=None
        )
        try:
            await message.edit(content=partial_text, embed=None)
        except discord.HTTPException as e:
            logger.error(f"Error showing dice 1 stop: {e}")
        
        # Brief animation with dice 2 & 3 still rolling
        dice_2_3_start = time.time()
        while time.time() - dice_2_3_start < DICE_STOP_INTERVAL:
            r2, r3 = random.choices(ANIMAL_LIST, k=2)
            partial_text = create_partial_result_text(
                result1=final_result1,
                result2=r2,
                result3=r3
            )
            try:
                await message.edit(content=partial_text, embed=None)
            except discord.HTTPException:
                pass
            await asyncio.sleep(ROLL_ANIMATION_INTERVAL)
        
        # Phase 3: Stop dice 2, continue dice 3
        partial_text = create_partial_result_text(
            result1=final_result1,
            result2=final_result2,
            result3=None
        )
        try:
            await message.edit(content=partial_text, embed=None)
        except discord.HTTPException as e:
            logger.error(f"Error showing dice 2 stop: {e}")
        
        # Brief animation with only dice 3 rolling
        dice_3_start = time.time()
        while time.time() - dice_3_start < DICE_STOP_INTERVAL:
            r3 = random.choice(ANIMAL_LIST)
            partial_text = create_partial_result_text(
                result1=final_result1,
                result2=final_result2,
                result3=r3
            )
            try:
                await message.edit(content=partial_text, embed=None)
            except discord.HTTPException:
                pass
            await asyncio.sleep(ROLL_ANIMATION_INTERVAL)
        
        # Phase 4: All dice stopped - show final result (only 3 emojis)
        final_text = create_result_display(final_result1, final_result2, final_result3)
        try:
            await message.edit(content=final_text, embed=None)
        except discord.HTTPException as e:
            logger.error(f"Error showing final result: {e}")
        
        logger.info(
            f"[DICE_ROLL] Sequential animation complete: "
            f"{final_result1}, {final_result2}, {final_result3}"
        )
        
        return (final_result1, final_result2, final_result3)
    
    async def calculate_results(
        self,
        game_state: GameState,
        results: tuple
    ) -> Dict[int, int]:
        """Calculate payouts for all bets based on results.
        
        Formula: payout = bet_amount * (matches + 1)
        - 0 matches = 0 payout (loss)
        - 1 match = bet_amount * 2
        - 2 matches = bet_amount * 3
        - 3 matches = bet_amount * 4
        
        Args:
            game_state: Active game state with bets
            results: Tuple of (result1, result2, result3)
            
        Returns:
            Dictionary mapping user_id to total payout amount
        """
        result1, result2, result3 = results
        final_result = [result1, result2, result3]
        payouts = {}
        
        for user_id, bet_list in game_state.bets.items():
            total_payout = 0
            
            for animal_key, bet_amount in bet_list:
                matches = sum(1 for r in final_result if r == animal_key)
                payout = calculate_payout(bet_amount, matches)
                total_payout += payout
            
            if total_payout > 0:
                payouts[user_id] = total_payout
        
        return payouts
    
    async def update_game_results_batch(
        self,
        payouts: Dict[int, int]
    ) -> None:
        """Update seed balances for all winners in a single batch operation.
        
        Uses optimized batch_update_seeds for performance.
        
        Args:
            payouts: Dictionary mapping user_id to payout amount
        """
        if not payouts:
            logger.debug("[RESULTS] No payouts to process")
            return
        
        try:
            await batch_update_seeds(payouts)
            logger.info(f"[RESULTS] Batch updated seeds for {len(payouts)} users")
        except Exception as e:
            logger.error(f"Error batch updating seeds: {e}", exc_info=True)

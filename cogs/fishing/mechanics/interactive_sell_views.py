"""Interactive View classes for sell events.

Provides base and specific View classes for choice-based sell events.
"""
import discord
import random
import asyncio
from typing import Dict, Any, Optional
from database_manager import db_manager, increment_stat, get_stat
from core.logger import setup_logger

logger = setup_logger("InteractiveSellViews", "cogs/fishing/fishing.log")


class InteractiveSellEventView(discord.ui.View):
    """Base class for interactive sell events.
    
    Provides common functionality:
    - User validation
    - Completion flag (prevent double-click)
    - Outcome rolling with weighted probabilities
    - Transaction execution
    - Timeout handling
    """
    
    def __init__(
        self, 
        cog, 
        user_id: int, 
        fish_items: Dict[str, int],
        base_value: int,
        event_data: Dict[str, Any],
        ctx_or_interaction
    ):
        """Initialize interactive sell event View.
        
        Args:
            cog: FishingCog instance
            user_id: Discord user ID
            fish_items: Dict of fish_key -> quantity being sold
            base_value: Calculated base sell value (before multipliers)
            event_data: Event configuration from sell_events.json
            ctx_or_interaction: Command context (for sending messages)
        """
        timeout = event_data.get('interactive', {}).get('timeout', 30)
        super().__init__(timeout=timeout)
        
        self.cog = cog
        self.user_id = user_id
        self.fish_items = fish_items
        self.base_value = base_value
        self.event_data = event_data
        self.ctx = ctx_or_interaction
        self.completed = False
        
        # Dynamically add buttons from event_data
        self._add_choice_buttons()
    
    def _add_choice_buttons(self):
        """Dynamically create buttons from event choices."""
        choices = self.event_data.get('interactive', {}).get('choices', [])
        
        for choice in choices:
            # Map style string to ButtonStyle enum
            style_map = {
                'green': discord.ButtonStyle.green,
                'primary': discord.ButtonStyle.primary,
                'secondary': discord.ButtonStyle.secondary,
                'danger': discord.ButtonStyle.danger,
                'red': discord.ButtonStyle.red,
                'gray': discord.ButtonStyle.gray,
                'grey': discord.ButtonStyle.gray
            }
            
            style = style_map.get(choice.get('style', 'secondary'), discord.ButtonStyle.secondary)
            
            button = discord.ui.Button(
                label=choice['label'],
                style=style,
                custom_id=choice['id']
            )
            button.callback = self._create_callback(choice)
            self.add_item(button)
    
    def _create_callback(self, choice: Dict):
        """Create callback function for a choice button.
        
        Args:
            choice: Choice configuration dict
            
        Returns:
            Async callback function
        """
        async def callback(interaction: discord.Interaction):
            # Validation: Only original user can click
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    "❌ Không phải cá của bạn!", 
                    ephemeral=True
                )
                return
            
            # Prevent double-click
            if self.completed:
                await interaction.response.send_message(
                    "❌ Đã chọn rồi!", 
                    ephemeral=True
                )
                return
            
            # Mark completed immediately
            self.completed = True
            
            # Disable all buttons
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            
            await interaction.response.edit_message(view=self)
            
            # Roll outcome
            outcome = self._roll_outcome(choice['outcomes'])
            
            # Calculate final value
            multiplier = outcome.get('mul', 1.0)
            flat_bonus = outcome.get('flat', 0)
            final_value = int(self.base_value * multiplier) + flat_bonus
            # REMOVED max(0, final_value) to allow investment losses/penalties
            
            # Execute sell transaction
            await self._execute_sell(
                interaction, 
                final_value, 
                outcome.get('message', ''),
                choice['id'],
                selected_outcome=outcome # Pass for side effects
            )
        
        return callback
    
    def _roll_outcome(self, outcomes: list) -> Dict:
        """Roll weighted outcome from list of possibilities.
        
        Args:
            outcomes: List of outcome dicts with 'weight' field
            
        Returns:
            Selected outcome dict
        """
        if len(outcomes) == 1:
            return outcomes[0]
        
        weights = [o.get('weight', 1.0) for o in outcomes]
        return random.choices(outcomes, weights=weights)[0]
    
    async def _execute_sell(
        self, 
        interaction: discord.Interaction, 
        final_value: int, 
        message: str,
        choice_id: str,
        selected_outcome: Dict = None
    ):
        """Execute the sell transaction atomically.
        
        Args:
            interaction: Discord interaction
            final_value: Final seeds to give user (can be negative)
            message: Result message to display
            choice_id: Which choice was selected (for stats tracking)
            selected_outcome: The full outcome dict (for side effects)
        """
        try:
            # Prepare batch operations for atomic transaction
            consume_items = True
            
            # Lookup strategy: outcome > choice > event > default
            choices = self.event_data.get('interactive', {}).get('choices', [])
            selected_choice = next((c for c in choices if c['id'] == choice_id), None)
            
            if selected_outcome and 'consume_items' in selected_outcome:
                consume_items = selected_outcome['consume_items']
            elif selected_choice and 'consume_items' in selected_choice:
                consume_items = selected_choice['consume_items']
            else:
                consume_items = self.event_data.get('interactive', {}).get('consume_items', True)
            
            # ACID TRANSACTION - Use safe transaction() context
            # [TIMEOUT ADDED] Prevent deadlock
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        # 1. VERIFY & DEDUCT ITEMS
                        if consume_items:
                            for fish_key, quantity in self.fish_items.items():
                                # Check availability
                                row = await conn.fetchrow(
                                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                                    (self.user_id, fish_key)
                                )
                                
                                if not row or row['quantity'] < quantity:
                                    raise ValueError(f"Không đủ cá {fish_key}! (Cần {quantity}, Có {row['quantity'] if row else 0})")
                                
                                # Deduct
                                await conn.execute(
                                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                                    (quantity, self.user_id, fish_key)
                                )
                            
                            # Cleanup empty
                            await conn.execute(
                                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0", 
                                (self.user_id,)
                            )
                        
                        # 2. UPDATE SEEDS
                        if final_value != 0:
                            await conn.execute(
                                "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                                (final_value, self.user_id)
                            )
                            # Manual Log for ACID Transaction
                            event_key = self.event_data.get('key', 'unknown')
                            await conn.execute(
                                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)",
                                (self.user_id, final_value, f"interactive_sell_{event_key}", "fishing")
                            )
                        
                        # Transaction auto-commits on success
            except asyncio.TimeoutError:
                await interaction.followup.send("⚠️ Giao dịch bị hủy do hệ thống bận (DB Locked). Vui lòng thử lại!", ephemeral=True)
                return
            
            # Caches auto-managed by InventoryCache - no manual clearing needed
            # CRITICAL FIX: Invalidate cache after sell (data already in DB)
            # Option 1: Use modify() with delta=0 which reads from DB
            # Option 2: Direct invalidate - simpler since transaction already committed
            # We choose direct invalidate - next !tuido will re-fetch from DB
            try:
                 if hasattr(self.cog.bot, 'inventory'):
                     await self.cog.bot.inventory.invalidate(self.user_id)
            except Exception:
                 pass

            # --- RAID BOSS CONTRIBUTION ---
            # Any money earned from sell events damages the boss
            if final_value > 0:
                 await self.cog.global_event_manager.process_raid_contribution(self.user_id, final_value)

            # --- HANDLE SIDE EFFECTS (Non-Transactional or Separate) ---
            
            # 1. Durability Change
            if selected_outcome and 'durability_change' in selected_outcome:
                change = selected_outcome['durability_change']
                # Get current rod data
                from ..mechanics.rod_system import get_rod_data, update_rod_data
                rod_level, current_durability = await get_rod_data(self.user_id)
                # Apply change (min 0)
                new_durability = max(0, current_durability + change)
                await update_rod_data(self.user_id, new_durability)
                logger.info(f"[INTERACTIVE_SELL] Updated durability for {self.user_id}: {change} -> {new_durability}")
                
            # 2. Apply Buffs
            if selected_outcome and 'buff' in selected_outcome:
                buff_data = selected_outcome['buff']
                buff_type = buff_data.get('type')
                duration = buff_data.get('duration', 0)
                if buff_type:
                    await self.cog.emotional_state_manager.apply_emotional_state(
                        self.user_id, buff_type, duration
                    )
                    logger.info(f"[INTERACTIVE_SELL] Applied buff {buff_type} ({duration}) to {self.user_id}")
            
            # Caches auto-managed by InventoryCache - no manual clearing needed
            # CRITICAL FIX: Invalidate cache after sell (data already in DB)
            # Option 1: Use modify() with delta=0 which reads from DB
            # Option 2: Direct invalidate - simpler since transaction already committed
            # We choose direct invalidate - next !tuido will re-fetch from DB
            
            # Track stats (event-specific)
            event_key = self.event_data.get('key', 'unknown')
            await self._track_stats(event_key, choice_id, final_value > self.base_value, final_value)
            
            # Build result embed
            embed = self._build_result_embed(final_value, message, interaction.user.name)
            
            await interaction.followup.send(embed=embed, ephemeral=False)
            
            logger.info(
                f"[INTERACTIVE_SELL] {interaction.user.name} (user_id={self.user_id}) "
                f"sold via {event_key} choice={choice_id} value={final_value} items_consumed={consume_items}"
            )
            
        except ValueError as ve:
             # Friendly error message for Race Conditions (user sold items elsewhere)
             msg = f"❌ **Giao dịch thất bại!**\n{str(ve)}\n\n_Có thể bạn đã bán số cá này ở lệnh khác hoặc số lượng trong kho đã thay đổi._"
             
             try:
                 await interaction.followup.send(msg, ephemeral=True)
                 
                 # Disable view to prevent further spam
                 for item in self.children:
                     item.disabled = True
                 await interaction.message.edit(view=self)
                 self.stop()
             except Exception:
                 pass # Ignore UI update errors
                 
             logger.warning(f"[INTERACTIVE_SELL_FAIL] Transaction blocked: {ve}")
             # Do not reset completed flag, stop view explicitly
             self.completed = True
             
        except Exception as e:
            await interaction.followup.send(
                f"❌ Lỗi hệ thống: {e}", 
                ephemeral=True
            )
            self.completed = False # Critical err, allow retry? Or maybe keep locked to be safe.
            logger.error(f"[INTERACTIVE_SELL_ERROR] {e}", exc_info=True)
    
    # Stat Mappings: (event_key, choice_id) -> global_stat_key
    STAT_MAPPINGS = {
        # Black Market
        ('black_market', 'accept'): 'risky_choices_made',
        ('black_market', 'decline'): 'safe_choices_made',
        # Haggle Master
        ('haggle_master', 'haggle'): 'haggle_attempts',
        ('haggle_master', 'accept'): 'safe_choices_made',
        # Mystery Buyer (risky_buyer)
        ('risky_buyer', 'accept'): 'risky_choices_made',
        ('risky_buyer', 'decline'): 'safe_choices_made',
        # Auction House
        ('auction_house', 'enter_auction'): 'risky_choices_made',
        ('auction_house', 'skip'): 'safe_choices_made',
        # Double or Nothing
        ('double_or_nothing', 'all_in'): 'risky_choices_made',
        ('double_or_nothing', 'play_safe'): 'safe_choices_made',
        # Quality Inspector
        ('quality_inspector', 'reroll'): 'risky_choices_made',
        ('quality_inspector', 'keep'): 'safe_choices_made',
        # Charity Donation
        ('charity_donation', 'donate'): 'charity_donations',
        # Express Sale
        ('express_sale', 'express'): 'risky_choices_made',
        ('express_sale', 'normal'): 'safe_choices_made', 
        # Investment Offer
        ('investment_offer', 'invest'): 'risky_choices_made',
        ('investment_offer', 'decline'): 'safe_choices_made',
        # Fish Contest (Win is tracked separately, this is just participation choice)
        ('fish_contest', 'enter_contest'): 'risky_choices_made',
        ('fish_contest', 'sell_normal'): 'safe_choices_made',
    }


    async def _track_stats(self, event_key: str, choice_id: str, is_win: bool, final_value: int = 0):
        """Track stats for achievements.
        
        Args:
            event_key: Event identifier
            choice_id: Choice selected
            is_win: Whether outcome was better than base
            final_value: Final money amount earned
        """
        try:
            # 1. Generic stat: total interactive events
            await increment_stat(self.user_id, "fishing", "interactive_events_triggered", 1)
            
            # 2. Detailed Event-specific stat: {event_key}_{choice_id}
            # e.g., black_market_accept, black_market_decline
            stat_key = f"{event_key}_{choice_id}"
            await increment_stat(self.user_id, "fishing", stat_key, 1)
            
            # 3. Global Category Stat (Mapped)
            # e.g., risky_choices_made, charity_donations
            global_stat = self.STAT_MAPPINGS.get((event_key, choice_id))
            if global_stat:
                await increment_stat(self.user_id, "fishing", global_stat, 1)
            
            # 4. Win/Loss tracking for gambling events
            # Only track win/loss if it was a risky choice (not safe choice)
            # Use simple heuristic: if mapped to 'risky_choices_made' or specific event logic implies risk
            if global_stat == 'risky_choices_made' or event_key in ['haggle_master', 'investment_offer', 'fish_contest']:
                if is_win:
                    await increment_stat(self.user_id, "fishing", f"{event_key}_wins", 1)
                    
                    # Special Case: Investment Win (also track global investment wins if we had one)
                    if event_key == 'investment_offer':
                         await increment_stat(self.user_id, "fishing", "investment_wins", 1)
                    # Special Case: Contest Win
                    elif event_key == 'fish_contest':
                         await increment_stat(self.user_id, "fishing", "contest_wins", 1)
                         
                else:
                    await increment_stat(self.user_id, "fishing", f"{event_key}_losses", 1)
                    
                    # Special Case: Investment Loss
                    if event_key == 'investment_offer':
                         await increment_stat(self.user_id, "fishing", "investment_losses", 1)

        # 5. Generic Achievement Stats (Money, Sells)
            if final_value > 0:
                await increment_stat(self.user_id, "fishing", "total_money_earned", final_value)
            
            # 6. Legacy/Achievement Mapping Hooks
            # Map new internal keys to legacy keys in achievements.json
            
            # Haggle
            if event_key == 'haggle_master' and is_win:
                await increment_stat(self.user_id, "fishing", "successful_haggles", 1)
            
            # Black Market
            if event_key == 'black_market':
                if is_win:
                    await increment_stat(self.user_id, "fishing", "black_market_successes", 1)
                else:
                    await increment_stat(self.user_id, "fishing", "black_market_failures", 1)
            
            # Shark Tank (Investment)
            if event_key == 'investment_offer' and choice_id == 'invest':
                # "Shark Tank Gọi Vốn" achievement requires triggering the event? 
                # Description: "Kích hoạt sự kiện 'Shark Tank' khi bán cá"
                # If it means just encountering it: tracked via interactive_events_triggered?
                # But specific key is shark_tank_event.
                # Let's count it when they CHOOSE to invest (Interact).
                await increment_stat(self.user_id, "fishing", "shark_tank_event", 1)

            # 7. Check achievement unlocks for ALL modified stats
            # We check the specific key and the global key
            stats_to_check = [
                stat_key, 
                "interactive_events_triggered", 
                "total_money_earned",
                "successful_haggles",
                "black_market_successes",
                "black_market_failures",
                "shark_tank_event"
            ]
            if global_stat:
                stats_to_check.append(global_stat)
            if is_win:
                stats_to_check.append(f"{event_key}_wins")
                if event_key == 'investment_offer': stats_to_check.append("investment_wins")
                if event_key == 'fish_contest': stats_to_check.append("contest_wins")
            
            for check_stat in stats_to_check:
                current_value = await get_stat(self.user_id, "fishing", check_stat)
                await self.cog.bot.achievement_manager.check_unlock(
                    self.user_id, 
                    "fishing", 
                    check_stat, 
                    current_value, 
                    self.ctx.channel if hasattr(self.ctx, 'channel') else None
                )
            
        except Exception as e:
            logger.error(f"[STAT_TRACK_ERROR] {e}", exc_info=True)
    
    def _build_result_embed(self, final_value: int, message: str, username: str) -> discord.Embed:
        """Build result embed showing outcome.
        
        Args:
            final_value: Hạt earned
            message: Outcome message
            username: User's display name
            
        Returns:
            Discord embed
        """
        from ..constants import ALL_FISH
        
        event_name = self.event_data.get('name', 'Sự Kiện')
        
        # Determine color based on outcome
        if final_value > self.base_value:
            color = discord.Color.gold()
            title = f"✨ {event_name} - THẮNG!"
        elif final_value < self.base_value:
            color = discord.Color.red()
            title = f"💔 {event_name} - THUA!"
        else:
            color = discord.Color.blue()
            title = f"⚖️ {event_name}"
        
        embed = discord.Embed(
            title=title,
            description=message,
            color=color
        )
        
        # Show values
        embed.add_field(
            name="💰 Kết Quả",
            value=f"**+{final_value:,} Hạt**",
            inline=False
        )
        
        # Show fish sold
        fish_summary = ", ".join([
            f"{ALL_FISH.get(k, {}).get('name', k)} x{v}" 
            for k, v in list(self.fish_items.items())[:5]
        ])
        if len(self.fish_items) > 5:
            fish_summary += f" (+{len(self.fish_items) - 5} loại khác)"
        
        embed.add_field(
            name="🐟 Đã Bán",
            value=fish_summary,
            inline=False
        )
        
        embed.set_footer(text=f"{username} • Interactive Sell Event")
        
        return embed
    
    async def on_timeout(self):
        """Handle timeout - default to safest choice and execute.
        
        Automatically selects the choice with lowest risk (highest min value).
        CRITICAL: Executes transaction to prevent data loss.
        """
        if self.completed:
            return
        
        self.completed = True
        
        logger.info(f"[INTERACTIVE_SELL] Timeout for user {self.user_id}, auto-selecting safe choice")
        
        # Find safest choice (highest minimum outcome)
        choices = self.event_data.get('interactive', {}).get('choices', [])
        safest_choice = None
        safest_min_value = -float('inf')
        
        for choice in choices:
            # Calculate minimum possible outcome
            min_outcome = min(
                o.get('mul', 1.0) * self.base_value + o.get('flat', 0)
                for o in choice['outcomes']
            )
            
            if min_outcome > safest_min_value:
                safest_min_value = min_outcome
                safest_choice = choice
        
        if not safest_choice:
            # Fallback: just process normal sale
            safest_choice = {
                'id': 'timeout_default',
                'outcomes': [{'mul': 1.0, 'flat': 0, 'weight': 1.0, 'message': 'Timeout - Bán tự động'}]
            }
        
        # Roll outcome from safest choice
        outcome = self._roll_outcome(safest_choice.get('outcomes', []))
        multiplier = outcome.get('mul', 1.0)
        flat_bonus = outcome.get('flat', 0)
        final_value = int(self.base_value * multiplier) + flat_bonus
        final_value = max(0, final_value)
        
        # Execute transaction
        try:
            # ACQUIRE LOCK REMOVED (transaction() handles it)
            # [TIMEOUT ADDED] Prevent deadlock
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        consume_items = True
                        if safest_choice and 'consume_items' in safest_choice:
                            consume_items = safest_choice['consume_items']
                        else:
                            consume_items = self.event_data.get('interactive', {}).get('consume_items', True)
                        
                        if consume_items:
                            # Remove fish items
                            for fish_key, quantity in self.fish_items.items():
                                # Check availability
                                row = await conn.fetchrow(
                                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                                    (self.user_id, fish_key)
                                )
                                
                                if not row or row['quantity'] < quantity:
                                    raise ValueError(f"Timeout failed: Not enough {fish_key}")
                                
                                # Deduct
                                await conn.execute(
                                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                                    (quantity, self.user_id, fish_key)
                                )
                            
                            await conn.execute(
                                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                                (self.user_id,)
                            )
                        
                        # Add seeds
                        if final_value != 0:
                            await conn.execute(
                                "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                                (final_value, self.user_id)
                            )
                            # Manual Log for ACID Transaction
                            event_key = self.event_data.get('key', 'unknown')
                            await conn.execute(
                                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)",
                                (self.user_id, final_value, f"interactive_sell_timeout_{event_key}", "fishing")
                            )
                        
                        # Transaction auto-commits on success
            except asyncio.TimeoutError:
                logger.error(f"[INTERACTIVE_SELL] Timeout Handler DB Lock Timeout for user {self.user_id}")
                return
            
            # Caches auto-managed by InventoryCache - no manual clearing needed
            try:
                 if hasattr(self.cog.bot, 'inventory'):
                     await self.cog.bot.inventory.invalidate(self.user_id)
            except Exception:
                 pass
            
            # Track timeout stat
            event_key = self.event_data.get('key', 'unknown')
            await increment_stat(self.user_id, "fishing", f"{event_key}_timeout", 1)
            
            logger.info(
                f"[INTERACTIVE_SELL] Timeout auto-sell completed: user={self.user_id} "
                f"value={final_value} choice={safest_choice.get('id', 'unknown')} consumed={consume_items}"
            )
            
        except Exception as e:
            logger.error(f"[INTERACTIVE_SELL_TIMEOUT_ERROR] {e}", exc_info=True)

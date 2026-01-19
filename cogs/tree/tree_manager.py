"""Tree growth and harvest management.

Manages core tree mechanics including contributions, level ups, and harvest events.
"""

import discord
import asyncio
from typing import Optional
from core.logging import setup_logger
from database_manager import (
    get_user_balance,
    add_seeds,
    get_or_create_user,
    batch_update_seeds,
    db_manager
)

from .constants import TREE_UPDATE_DEBOUNCE_SECONDS
from .models import TreeData, HarvestBuff
from .helpers import create_tree_embed, create_contribution_success_embed, create_harvest_announcement_embed
from .views import TreeContributeView

logger = setup_logger("TreeManager", "logs/cogs/tree.log")


# PERFORMANCE FIX #15: Monitoring decorator
def log_performance(func):
    """Decorator to log execution time of critical methods.
    
    Logs timing information to help identify bottlenecks in production.
    """
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        import time
        start = time.time()
        method_name = func.__name__
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            
            # Log slow operations (>1s)
            if duration > 1.0:
                logger.warning(f"[PERF] {method_name} took {duration:.3f}s (SLOW)")
            else:
                logger.debug(f"[PERF] {method_name} took {duration:.3f}s")
            
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                f"[PERF] {method_name} FAILED after {duration:.3f}s: {e}",
                exc_info=True
            )
            raise
    
    return wrapper


class TreeManager:
    """Manages tree growth mechanics and harvest events.
    
    Handles:
    - Processing contributions
    - Tree level ups
    - Message updates with debounce
    - Harvest event execution
    """
    
    def __init__(self, bot, contributor_manager):
        """Initialize tree manager.
        
        Args:
            bot: Discord bot instance
            contributor_manager: ContributorManager instance
        """
        self.bot = bot
        self.contributor_manager = contributor_manager
        self.update_locks = {}  # Guild-level locks for message updates
        self.last_updates = {}  # Debounce tracking
        
        # Security: Per-user locks to prevent concurrent contribution race conditions
        self.user_contribution_locks = {}  # {user_id: asyncio.Lock}
        
        # Security: Per-guild locks to prevent concurrent harvest events
        self.harvest_locks = {}  # {guild_id: asyncio.Lock}
        
        # Performance: User object cache to prevent N+1 queries
        from .constants import USER_CACHE_TTL_SECONDS, CONTRIBUTION_COOLDOWN_SECONDS
        
        self.user_cache = {}  # {user_id: (user_obj, timestamp)}
        self.user_cache_ttl = USER_CACHE_TTL_SECONDS
        
        # PERFORMANCE FIX #10: Rate limiting for contributions
        self.user_last_contribution = {}  # {user_id: timestamp}
        self.contribution_cooldown = CONTRIBUTION_COOLDOWN_SECONDS
        
        # Start background cleanup task for memory leak prevention
        self.bot.loop.create_task(self._cleanup_old_data())
    
    async def get_user_cached(self, user_id: int):
        """Get Discord user with 5-minute cache to prevent N+1 queries.
        
        PERFORMANCE FIX #4: Cache user objects to avoid repeated API calls.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            discord.User object or None if not found
        """
        import time
        current_time = time.time()
        
        # Check cache
        if user_id in self.user_cache:
            user_obj, cached_at = self.user_cache[user_id]
            if current_time - cached_at < self.user_cache_ttl:
                return user_obj
        
        # Fetch and cache
        try:
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)
            self.user_cache[user_id] = (user, current_time)
            return user
        except Exception as e:
            logger.warning(f"[USER_CACHE] Could not fetch user {user_id}: {e}")
            return None
    
    async def _cleanup_old_data(self):
        """Periodic cleanup task to prevent memory leaks.
        
        MEMORY LEAK FIX #7: Clean up old entries from lock dictionaries
        and cache to prevent unbounded memory growth.
        """
        from .constants import (
            CLEANUP_INTERVAL_HOURS, 
            CLEANUP_CUTOFF_HOURS,
            CACHE_EXPIRY_MULTIPLIER,
            SECONDS_PER_HOUR,
            SECONDS_PER_DAY
        )
        
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_HOURS * SECONDS_PER_HOUR)
                
                import time
                current_time = time.time()
                
                # Clean up update timestamps older than cutoff
                cutoff = current_time - (CLEANUP_CUTOFF_HOURS * SECONDS_PER_HOUR)
                old_guilds = [
                    gid for gid, timestamp in self.last_updates.items()
                    if timestamp < cutoff
                ]
                
                for guild_id in old_guilds:
                    del self.last_updates[guild_id]
                
                # Clean up expired user cache entries
                cache_expiry = self.user_cache_ttl * CACHE_EXPIRY_MULTIPLIER
                expired_users = [
                    uid for uid, (_, cached_at) in self.user_cache.items()
                    if current_time - cached_at > cache_expiry
                ]
                
                for user_id in expired_users:
                    del self.user_cache[user_id]
                
                if old_guilds or expired_users:
                    logger.debug(
                        f"[CLEANUP] Removed {len(old_guilds)} old timestamps, "
                        f"{len(expired_users)} expired user cache entries"
                    )
                    
            except Exception as e:
                logger.error(f"[CLEANUP] Error in cleanup task: {e}", exc_info=True)
    
    @log_performance
    async def process_contribution(
        self,
        interaction: discord.Interaction,
        amount: int
    ) -> None:
        """Process a seed contribution from a user.
        
        Flow:
        1. Validate balance
        2. Deduct seeds
        3. Update tree progress
        4. Handle level ups (may level multiple times)
        5. Track contributor
        6. Send success message
        7. Update tree message
        
        Args:
            interaction: Discord interaction (already deferred)
            amount: Number of seeds to contribute
        """
        # Ensure deferred
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception as e:
                logger.error(f"Error deferring response: {e}", exc_info=True)
                return
        
        user_id = interaction.user.id
        
        # PERFORMANCE FIX #10: Rate limiting - check cooldown
        import time
        current_time = time.time()
        last_contrib = self.user_last_contribution.get(user_id, 0)
        
        if current_time - last_contrib < self.contribution_cooldown:
            remaining = self.contribution_cooldown - (current_time - last_contrib)
            await interaction.followup.send(
                f"⏰ Vui lòng đợi {remaining:.1f}s trước khi góp tiếp!",
                ephemeral=True
            )
            return
        
        # SECURITY FIX #2: Acquire per-user lock to prevent race conditions
        # This prevents concurrent contributions from same user bypassing balance check
        if user_id not in self.user_contribution_locks:
            self.user_contribution_locks[user_id] = asyncio.Lock()
        
        async with self.user_contribution_locks[user_id]:
            try:
                guild_id = interaction.guild.id
                
                # Check balance
                current_balance = await get_user_balance(user_id)
                
                if current_balance < amount:
                    await interaction.followup.send(
                        f"❌ Bạn không đủ hạt!\nCần: {amount:,} | Hiện có: {current_balance:,}",
                        ephemeral=True
                    )
                    return
                
                balance_before = current_balance
                new_balance = balance_before - amount
                
                # Deduct seeds
                await get_or_create_user(user_id, f"User#{user_id}")
                await add_seeds(user_id, -amount, reason='tree_contribute', category='social')
                
                logger.info(
                    f"[CONTRIB_DEBIT] user_id={user_id} seed_change=-{amount} "
                    f"balance_before={balance_before} balance_after={new_balance}"
                )
                
                # Get current tree state
                tree_data = await TreeData.load(guild_id)
                
                # Check if already max level
                if tree_data.current_level >= 6:
                    # Refund
                    await add_seeds(user_id, amount, reason='tree_refund', category='social')
                    await interaction.followup.send(
                        "🍎 Cây đã chín rồi! Hãy bảo Admin dùng lệnh `/thuhoach`!",
                        ephemeral=True
                    )
                    logger.info(f"[REFUND] user_id={user_id} seed_change=+{amount} reason=tree_maxed")
                    return
                
                # Calculate XP Bonus (VIP Tier 1+)
                vip_bonus_exp = 0
                from core.services.vip_service import VIPEngine
                vip_data = await VIPEngine.get_vip_data(user_id)
                
                if vip_data and vip_data['tier'] >= 1:
                    vip_bonus_exp = int(amount * 0.1)
                
                total_exp_added = amount + vip_bonus_exp
                
                # Update tree progress with Total EXP
                level_reqs = tree_data.get_level_requirements()
                req = level_reqs.get(tree_data.current_level + 1, level_reqs[6])
                new_progress = tree_data.current_progress + total_exp_added
                new_total = tree_data.total_contributed + total_exp_added
                new_level = tree_data.current_level
                leveled_up = False
                
                # Handle multiple level ups
                while new_progress >= req and new_level < 6:
                    new_level += 1
                    new_progress = new_progress - req
                    leveled_up = True
                    # Update req for next level
                    req = level_reqs.get(new_level + 1, level_reqs[6])
                
                # Update and save tree data
                tree_data.current_level = new_level
                tree_data.current_progress = new_progress
                tree_data.total_contributed = new_total
                await tree_data.save()
                
                # Track contribution (Pass Total EXP as amount if type is seeds, or handle inside?)
                # If we pass total_exp_added, ContributorManager will see it as "seeds".
                # Standard logic: 1 seed = 1 exp.
                # So passing total_exp_added works for ranking.
                await self.contributor_manager.add_contribution(
                    user_id,
                    guild_id,
                    tree_data.season,
                    total_exp_added,
                    contribution_type="seeds"
                )
                
                # Send success message
                embed = await create_contribution_success_embed(
                    user=interaction.user,
                    amount=amount,
                    new_progress=new_progress,
                    requirement=req,
                    leveled_up=leveled_up,
                    new_level=new_level,
                    item_name="Hạt",
                    quantity=amount,
                    action_title="Góp Hạt Cho Cây!",
                    bonus_exp=vip_bonus_exp
                )
                
                # Phase 3: Magic Fruit Drop (VIP 2+ only)
                # 5% chance
                # Using fetched vip_data
                if vip_data and vip_data['tier'] >= 2:
                    import random
                    if random.random() < 0.05: # 5% Chance
                        # Give Item
                        if hasattr(self.bot, 'inventory'):
                             # Assuming InventoryCache singleton
                             await self.bot.inventory.add_item(user_id, "magic_fruit", 1)
                        else:
                             # Fallback to direct DB
                             await db_manager.execute(
                                 "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, 'magic_fruit', 1) "
                                 "ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1",
                                 (user_id,)
                             )
                        
                        embed.description += "\n\n🍎 **QUẢ THẦN!!**\nBạn may mắn nhận được **1 Quả Thần** nhờ chăm sóc cây!"
                        embed.color = 0xf1c40f # Gold color for luck
                
                await interaction.followup.send(embed=embed, ephemeral=False)
                
                # Echo to tree channel if different
                if tree_data.tree_channel_id and interaction.channel_id != tree_data.tree_channel_id:
                    try:
                        tree_channel = self.bot.get_channel(tree_data.tree_channel_id)
                        if not tree_channel:
                            tree_channel = await self.bot.fetch_channel(tree_data.tree_channel_id)
                        
                        if tree_channel:
                            await tree_channel.send(embed=embed)
                    except Exception as e:
                        logger.warning(f"[TREE] Could not echo contribution to tree channel: {e}")

                # Update tree message
                if tree_data.tree_channel_id:
                    await self.update_tree_message(guild_id, tree_data.tree_channel_id)
                
                # Update cooldown timestamp
                self.user_last_contribution[user_id] = current_time
                
                logger.info(
                    f"[CONTRIB_SUCCESS] user={interaction.user.name} (id={user_id}) "
                    f"amount={amount} tree_level={new_level} total={new_total}"
                )
                
            except Exception as e:
                logger.error(f"Error in process_contribution: {e}", exc_info=True)
                try:
                    await interaction.followup.send(
                        f"❌ Có lỗi xảy ra: {str(e)}",
                        ephemeral=True
                    )
                except Exception:
                    pass
    
    @log_performance
    async def update_tree_message(
        self,
        guild_id: int,
        tree_channel_id: int,
        skip_if_latest: bool = False
    ) -> None:
        """Update tree message (delete old + create new).
        
        Uses lock to prevent concurrent updates and debounce to limit frequency.
        
        Args:
            guild_id: Discord guild ID
            tree_channel_id: Channel ID where tree message is displayed
            skip_if_latest: If True, skip update if old message is already the latest
                            (useful for startup to avoid unnecessary notification spam)
        """
        # Check debounce
        if not await self.should_update_message(guild_id):
            return
        
        # Get or create lock
        if guild_id not in self.update_locks:
            self.update_locks[guild_id] = asyncio.Lock()
        
        async with self.update_locks[guild_id]:
            try:
                channel = self.bot.get_channel(tree_channel_id)
                if not channel:
                    try:
                        channel = await self.bot.fetch_channel(tree_channel_id)
                    except Exception as e:
                        logger.warning(f"[TREE] Channel {tree_channel_id} not found: {e}")
                        return
                
                # Load tree data
                tree_data = await TreeData.load(guild_id)
                
                # Get existing message ID
                tree_message_id = tree_data.tree_message_id
                
                # Skip-if-latest check (for startup)
                # If skipped, we still need to EDIT the message to re-register the View (buttons)
                if skip_if_latest and tree_message_id:
                    try:
                        last_messages = [msg async for msg in channel.history(limit=1)]
                        if last_messages and last_messages[0].id == tree_message_id:
                            # Re-register View by editing the message
                            old_message = last_messages[0]
                            view = TreeContributeView(self)
                            await old_message.edit(view=view)
                            logger.info(f"[TREE] Skipped full update, re-registered View for message {tree_message_id}")
                            return
                    except Exception as e:
                        logger.warning(f"[TREE] Could not check/edit last message: {e}")

                
                # Create embed (use bot user for VIP styling since no specific user context)
                bot_user = self.bot.user
                embed = await create_tree_embed(bot_user, tree_data)
                
                # Add buff info if active
                if await HarvestBuff.is_active(guild_id):
                    buff = await db_manager.fetchone(
                        "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                        (guild_id,)
                    )
                    if buff and buff[0]:
                        from datetime import datetime
                        buff_until = buff[0]
                        # PostgreSQL returns datetime, legacy SQLite returns string
                        if isinstance(buff_until, str):
                            buff_until = datetime.fromisoformat(buff_until)
                        timestamp = int(buff_until.timestamp())
                        embed.add_field(
                            name="🌟 Buff Toàn Server",
                            value=f"X2 hạt còn <t:{timestamp}:R>",
                            inline=False
                        )
                
                # Add contributor lists
                current_season_contributors = await self.contributor_manager.get_top_contributors_season(
                    guild_id,
                    tree_data.season,
                    3
                )
                all_time_contributors = await self.contributor_manager.get_top_contributors_all_time(guild_id, 3)
                
                if current_season_contributors:
                    from .helpers import format_contributor_list
                    season_text = await format_contributor_list(current_season_contributors, self, show_exp=False)
                    embed.add_field(
                        name=f"🏆 Top 3 Người Góp mùa {tree_data.season}",
                        value=season_text,
                        inline=False
                    )
                
                if all_time_contributors:
                    from .helpers import format_all_time_contributors
                    all_time_text = await format_all_time_contributors(all_time_contributors, self)
                    embed.add_field(
                        name="🏆 Top 3 Người Góp toàn thời gian",
                        value=all_time_text,
                        inline=False
                    )
                
                view = TreeContributeView(self)
                
                # Delete old message
                if tree_message_id:
                    try:
                        old_message = await channel.fetch_message(tree_message_id)
                        await old_message.delete()
                        logger.debug(f"[TREE] Deleted old message {tree_message_id}")
                    except Exception as e:
                        logger.warning(f"[TREE] Could not delete old message: {e}")
                
                # Create new message
                new_message = await channel.send(embed=embed, view=view)
                
                # Update message ID in database
                await db_manager.modify(
                    "UPDATE server_tree SET tree_message_id = ? WHERE guild_id = ?",
                    (new_message.id, guild_id)
                )
                
                logger.info(f"[TREE] Updated tree message {new_message.id} in channel {tree_channel_id}")
                
            except Exception as e:
                logger.error(f"[TREE] Error updating tree message: {e}", exc_info=True)

    
    async def should_update_message(self, guild_id: int) -> bool:
        """Check if enough time has passed since last update (debounce).
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if should update
        """
        import time
        current_time = time.time()
        last_update = self.last_updates.get(guild_id, 0)
        
        if current_time - last_update < TREE_UPDATE_DEBOUNCE_SECONDS:
            return False
        
        self.last_updates[guild_id] = current_time
        return True
    
    @log_performance
    async def execute_harvest(
        self,
        interaction: discord.Interaction
    ) -> None:
        """Execute harvest event (admin only).
        
        Complex flow:
        1. Validate level 6
        2. Get all contributors
        3. Calculate tiered rewards
        4. Batch update seeds
        5. Give memorabilia items
        6. Create role for top1
        7. Activate 24h buff
        8. Reset tree to season+1
        9. Send announcements
        
        Args:
            interaction: Discord interaction (admin command)
        """
        guild_id = interaction.guild.id
        
        # SECURITY FIX #6: Check if harvest already in progress
        # Prevents admin double-click from distributing duplicate rewards
        if guild_id not in self.harvest_locks:
            self.harvest_locks[guild_id] = asyncio.Lock()
        
        if self.harvest_locks[guild_id].locked():
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(
                "⚠️ Thu hoạch đang trong quá trình! Vui lòng đợi harvest hiện tại hoàn thành.",
                ephemeral=True
            )
            logger.warning(f"[HARVEST_BLOCKED] Prevented duplicate harvest for guild {guild_id}")
            return
        
        async with self.harvest_locks[guild_id]:
            await interaction.response.defer(ephemeral=False)
            
            # SECURITY FIX #8: Wrap in try/except for transaction rollback
            try:
                # Load tree data
                tree_data = await TreeData.load(guild_id)
                
                # Validate level 6
                if tree_data.current_level < 6:
                    level_reqs = tree_data.get_level_requirements()
                    await interaction.followup.send(
                        f"❌ Cây chưa chín! Hiện tại: Level {tree_data.current_level}/6. "
                        f"Cần thêm {level_reqs[6] - tree_data.current_progress} Hạt.",
                        ephemeral=True
                    )
                    return
                
                await interaction.followup.send("**ĐANG THU HOẠCH...** Xin chờ một chút! 🌟")
                
                # Get all contributors for current season
                all_contributors = await self.contributor_manager.get_all_season_contributors(
                    guild_id,
                    tree_data.season
                )
                
                if not all_contributors:
                    await interaction.followup.send("❌ Không có ai đóng góp trong mùa này!", ephemeral=True)
                    return
                
                # Calculate rewards
                seed_rewards = self.contributor_manager.calculate_harvest_rewards(all_contributors)
                
                # <<< HOOK: Phase 3.1 Coral Reef Set Bonus (+5% Yield) >>>
                from cogs.aquarium.logic.housing import HousingEngine
                for uid in list(seed_rewards.keys()):
                    try:
                        # Check "dai_duong" set (Coral Reef)
                        if await HousingEngine.is_set_active(uid, "dai_duong"):
                            bonus = int(seed_rewards[uid] * 0.05)
                            if bonus > 0:
                                seed_rewards[uid] += bonus
                                logger.info(f"[HARVEST_BONUS] User {uid} (Coral Reef Set) +{bonus} seeds")
                    except Exception as e:
                        logger.warning(f"[HARVEST_BONUS] Check failed for {uid}: {e}")
                
                # Batch update seeds
                await batch_update_seeds(seed_rewards, reason='tree_harvest', category='social')
                logger.info(f"[HARVEST] Distributed seeds to {len(seed_rewards)} contributors")
                
                # Give memorabilia items
                await self.contributor_manager.give_memorabilia_items(all_contributors, tree_data.season)
                
                # Create role for top1
                top1_user_id = all_contributors[0][0]
                role_mention = await self.create_top1_role(interaction.guild, tree_data.season, top1_user_id)
                
                # Activate 24h buff
                await HarvestBuff.activate(guild_id)
                
                # Reset tree for next season
                await db_manager.modify(
                    """UPDATE server_tree 
                       SET current_level = 1, current_progress = 0, total_contributed = 0, 
                           season = season + 1, last_harvest = CURRENT_TIMESTAMP 
                       WHERE guild_id = ?""",
                    (guild_id,)
                )
                
                # Send harvest announcement
                embed = await create_harvest_announcement_embed(
                    tree_data.season,
                    all_contributors,
                    self.bot
                )
                await interaction.followup.send(embed=embed)
                
                # Role announcement
                if role_mention:
                    await interaction.followup.send(f"🌟 {role_mention}")
                
                # Tag everyone
                announce_msg = (
                    f"🎊 Yayyyy 🎊\n\n"
                    f"**MÙA THU HOẠCH CÂY HIÊN NHÀ ĐÃ KẾT THÚC!**\n\n"
                    f"Trong 24 giờ tới, mọi người sẽ nhận **X2 Hạt từ chat/voice**!\n"
                    f"Hãy tranh thủ online để tối đa hóa lợi nhuận!\n\n"
                    f"Chúc mừng những người đã đóng góp!"
                )
                await interaction.followup.send(announce_msg)
                
                # Update tree message
                if tree_data.tree_channel_id:
                    await self.update_tree_message(guild_id, tree_data.tree_channel_id)
                
                logger.info(
                    f"[HARVEST_COMPLETE] Season {tree_data.season} guild {guild_id} "
                    f"contributors={len(all_contributors)} top1={top1_user_id}"
                )
                
            except Exception as e:
                logger.error(f"[HARVEST_FAILED] Harvest failed for guild {guild_id}: {e}", exc_info=True)
                try:
                    await interaction.followup.send(
                        "❌ **Thu hoạch thất bại!**\n"
                        "Đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại sau.\n"
                        f"Lỗi: {str(e)}",
                        ephemeral=True
                    )
                except Exception:
                    pass
                raise  # Re-raise to ensure lock is released
    
    async def create_top1_role(
        self,
        guild: discord.Guild,
        season: int,
        user_id: int
    ) -> Optional[str]:
        """Create and assign Thần Nông role to top contributor.
        
        Args:
            guild: Discord guild
            season: Season number
            user_id: User to assign role to
            
        Returns:
            Success message string or None if failed
        """
        try:
            from .constants import HARVEST_REWARDS
            
            role_name = f"🌟 Thần Nông Mùa {season}"
            existing_role = discord.utils.get(guild.roles, name=role_name)
            
            if not existing_role:
                role = await guild.create_role(
                    name=role_name,
                    color=discord.Color.gold(),
                    hoist=True
                )
            else:
                role = existing_role
            
            # Assign role to top1 user
            member = await guild.fetch_member(user_id)
            if member:
                await member.add_roles(role)
                total_reward = HARVEST_REWARDS['top1'] + HARVEST_REWARDS['top1_bonus']
                return (
                    f"Đã cấp role **{role_name}** cho **{member.name}** "
                    f"và thưởng tổng cộng {total_reward:,} hạt "
                    f"({HARVEST_REWARDS['top1']:,} + {HARVEST_REWARDS['top1_bonus']:,} bonus)!"
                )
            else:
                return None
                
        except Exception as e:
            logger.error(f"[HARVEST] Error creating role: {e}", exc_info=True)
            return None

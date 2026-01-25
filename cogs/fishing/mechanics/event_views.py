"""Event-related views for fishing system.

Contains views for meteor shower wishes and NPC encounters.
"""
import random
import asyncio
from datetime import datetime
import discord

from core.logging import get_logger
from database_manager import add_seeds, get_stat, increment_stat, db_manager
from .legendary_quest_helper import increment_manh_sao_bang

logger = get_logger("fishing_event_views")


class MeteorWishView(discord.ui.View):
    """View for wishing on shooting stars during meteor shower events."""
    
    def __init__(self, cog):
        # FIX: Increase timeout to 10 mins (was 30s)
        super().__init__(timeout=600)
        self.cog = cog
        self.wished_users = set()
    
    @discord.ui.button(label="🙏 Ước Nguyện", style=discord.ButtonStyle.primary, emoji="💫")
    async def wish_on_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle wish button click."""
        user_id = interaction.user.id
        
        # No Daily Limit (User Request)
        # today_str = datetime.now().strftime('%Y-%m-%d')
        # stat_key = f'meteor_shards_today_{today_str}'
        stat_key = "total_wishes" # Just track total wishes instead

        
        # Prevent double-click
        if user_id in self.wished_users:
            await interaction.response.send_message("Bạn đã ước rồi!", ephemeral=True)
            return
        
        self.wished_users.add(user_id)
        
        # 10% chance for manh_sao_bang (User Request)
        # Defer immediately to prevent timeout during DB ops
        await interaction.response.defer()
        
        if random.random() < 0.2:
            await increment_manh_sao_bang(self.cog.bot, user_id, 1)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            
            message = (
                f"🌠 **{interaction.user.name}** chắp tay nguyện cầu khi sao băng vụt qua...\n"
                f"✨ Điều kỳ diệu đã đến! Một mảnh vỡ rực sáng rơi xuống tay bạn! Bạn nhận được **Mảnh Sao Băng**! 🌠✨"
            )
            logger.info(f"[METEOR] User {interaction.user.name} ({user_id}) got SHARD")
        else:
            seeds = random.randint(10, 50)
            await add_seeds(user_id, seeds, 'meteor_wish', 'social')
            await increment_stat(user_id, 'fishing', stat_key, 1)
            
            message = (
                f"🌠 **{interaction.user.name}** đã gửi một lời ước đến các vì sao...\n"
                f"🌱 Sao băng đã nghe thấy! Bạn nhận được **{seeds} hạt**! ✨"
            )
            logger.info(f"[METEOR] User {interaction.user.name} ({user_id}) got {seeds} SEEDS")
        
        await interaction.followup.send(message)
        
        # Disable button after 15s
        await asyncio.sleep(15)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            logger.error(f"Error editing meteor view: {e}")




from ..constants import ALL_FISH, ALL_ITEMS_DATA

from core.logging import get_logger
logger = get_logger("event_views")


class GenericActionView(discord.ui.View):
    """Universal View for configured button-based events.
    
    Reads configuration from 'mechanics.buttons' in event data.
    """
    
    def __init__(self, manager):
        super().__init__(timeout=600)  # Match event duration (10 min), prevent leak
        self.manager = manager
        # Get button config from current event of the MANAGER
        # Note: If manager.current_event is None, this will fail. 
        # But this view is created only when event is active.
        self.event_data = self.manager.current_event.get("data", {})
        # Config IS in data.data.mechanics.buttons (double nested structure is REAL!)
        self.buttons_config = self.event_data.get("data", {}).get("mechanics", {}).get("buttons", [])
        
        logger.debug("generic_view_init", event_key=self.manager.current_event.get('key', 'unknown'))
        logger.debug("generic_view_init", button_count=len(self.buttons_config))
        logger.debug("generic_view_init", buttons_config=str(self.buttons_config))
        
        self._setup_buttons()
        
    def _setup_buttons(self):
        logger.info(f"[GENERIC_VIEW] [SETUP_BUTTONS] Starting setup with {len(self.buttons_config)} buttons")
        for idx, btn_cfg in enumerate(self.buttons_config):
            try:
                logger.info(f"[GENERIC_VIEW] [SETUP_BUTTONS] Setting up button {idx}: {btn_cfg.get('label', 'NO_LABEL')}")
                style = getattr(discord.ButtonStyle, btn_cfg.get("style", "primary"), discord.ButtonStyle.primary)
                
                button = discord.ui.Button(
                    label=btn_cfg.get("label", "Click Me"),
                    style=style,
                    emoji=btn_cfg.get("emoji"),
                    custom_id=f"generic_btn_{idx}"
                )
                # Bind callback with index capture
                button.callback = self.create_callback(idx)
                self.add_item(button)
                logger.info(f"[GENERIC_VIEW] [SETUP_BUTTONS] Button {idx} added successfully")
            except Exception as e:
                logger.error(f"[GENERIC_VIEW] [SETUP_BUTTONS] Failed to add button {idx}: {e}", exc_info=True)
            
    def create_callback(self, idx):
        async def callback(interaction: discord.Interaction):
            logger.info(f"[GENERIC_VIEW] [CALLBACK_TRIGGERED] User {interaction.user.id} clicked button {idx}")
            try:
                # Defer to prevent Timeout
                await interaction.response.defer(ephemeral=True)
            except (discord.NotFound, discord.HTTPException) as e:
                logger.warning(f"[GENERIC_VIEW] Failed to defer interaction for user {interaction.user.id}: {e}")
                return

            logger.info(f"[GENERIC_VIEW] [DEFERRED] Calling _handle_click for user {interaction.user.id}")
            await self._handle_click(interaction, idx)
        return callback
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        """Override to capture exceptions that Discord ignores."""
        logger.error(
            f"[GENERIC_VIEW] [ON_ERROR] User {interaction.user.id} ({interaction.user.name}) "
            f"Button: {item.label if hasattr(item, 'label') else '?'} "
            f"Error: {type(error).__name__}: {error}",
            exc_info=error
        )
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Lỗi: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Lỗi: {error}", ephemeral=True)
        except discord.HTTPException:
            pass  # Interaction expired or already responded
    
    def _get_item_name(self, key):
        """Resolve item name from constants."""
        if key in ALL_FISH: return ALL_FISH[key].get("name", key)
        if key in ALL_ITEMS_DATA: return ALL_ITEMS_DATA[key].get("name", key)
        return key

    async def _handle_click(self, interaction: discord.Interaction, idx: int):
        # NOTE: interaction.response.defer() already called in create_callback()
        # Do NOT defer again - causes InteractionResponded error!
        
        user_id = interaction.user.id
        btn_config = self.buttons_config[idx]
        
        try:
            # ACID TRANSACTION - Use safe transaction() context
            # [TIMEOUT ADDED] Prevent deadlock if DB is busy/locked
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        try:
                            # 0. CHECK LIMIT (If Configured)
                            limit = btn_config.get("limit_per_user", 0)
                            logger.info(f"[GENERIC_VIEW] [LIMIT_DEBUG] user_id={user_id} limit_raw={limit} btn_config_keys={list(btn_config.keys())}")
                            
                            if limit > 0:
                                # CRITICAL FIX: Use event_key + DATE, not start_time
                                # start_time changes on bump -> limit reset bug
                                from datetime import datetime
                                today = datetime.now().strftime("%Y-%m-%d")
                                unique_limit_key = f"event_limit_{self.manager.current_event['key']}_{idx}_{today}"
                                logger.info(f"[GENERIC_VIEW] [LIMIT_CHECK] user_id={user_id} key={unique_limit_key} limit={limit}")
                                
                                row = await conn.fetchrow(
                                    "SELECT value FROM user_stats WHERE user_id = $1 AND game_id = 'global_event' AND stat_key = $2",
                                    (user_id, unique_limit_key)
                                )
                                current_usage = row[0] if row else 0
                                logger.info(f"[GENERIC_VIEW] [LIMIT_CHECK] user_id={user_id} current_usage={current_usage}/{limit}")
                                
                                if current_usage >= limit:
                                    logger.warning(f"[GENERIC_VIEW] [LIMIT_BLOCKED] user_id={user_id} exceeded limit {current_usage}/{limit}")
                                    raise ValueError(f"⛔ Bạn đã đạt giới hạn hôm nay ({limit}/{limit})!")

                            # 1. CHECK & PAY COST
                            cost = btn_config.get("cost", {})
                            # A. Money Cost
                            money_cost = cost.get("money", 0)
                            if money_cost > 0:
                                row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", (user_id,))
                                current_bal = row[0] if row else 0
                                
                                if current_bal < money_cost:
                                     raise ValueError(f"Không đủ tiền! Cần {money_cost} Hạt.")
                                     
                                await conn.execute(
                                    "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                                    (money_cost, user_id)
                                )
                                # Manual Log for ACID Transaction
                                await conn.execute(
                                    "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                    (user_id, -money_cost, f"event_buy_{btn_config.get('label', 'generic')}", "fishing")
                                )
                            
                            # B. Item Cost (Barter)
                            item_input = cost.get("item") # { "key": "trash_01", "amount": 1 }
                            item_type_input = cost.get("item_type") # { "type": "trash", "amount": 10 }
                            
                            if item_input:
                                req_key = item_input.get("key")
                                req_amt = item_input.get("amount", 1)
                                if req_key and req_amt > 0:
                                    row = await conn.fetchrow(
                                        "SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2",
                                        (user_id, req_key)
                                    )
                                    start_qty = row[0] if row else 0
                                    
                                    if start_qty < req_amt:
                                        raise ValueError(f"Không đủ vật phẩm! Cần {req_amt} {req_key}.")
                                    
                                    await conn.execute(
                                        "UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = $3",
                                        (req_amt, user_id, req_key)
                                    )

                            elif item_type_input:
                                req_type = item_type_input.get("type")
                                req_amt = item_type_input.get("amount", 10)
                                
                                if req_type and req_amt > 0:
                                    # 1. Load Item Definitions to find keys
                                    valid_keys = []
                                    try:
                                        # Import locally if needed or reuse ALL_ITEMS_DATA
                                        valid_keys = [k for k, v in ALL_ITEMS_DATA.items() if v.get("type") == req_type]
                                    except Exception as e:
                                        logger.error(f"Failed to filter items: {e}")
                                        raise ValueError("Lỗi hệ thống: Không tìm thấy vật phẩm.")
                                    
                                    if not valid_keys:
                                        raise ValueError(f"Không tìm thấy loại vật phẩm '{req_type}' trong hệ thống.")

                                    # 2. Check User Inventory for ANY of these keys
                                    # AsyncPG Dynamic Placeholders ($2, $3, ...)
                                    placeholders = ','.join(f"${i+2}" for i in range(len(valid_keys)))
                                    query = f"SELECT item_id, quantity FROM inventory WHERE user_id = $1 AND item_id IN ({placeholders})"
                                    
                                    # Params: user_id is $1, others follow
                                    rows = await conn.fetch(query, user_id, *valid_keys)
                                    
                                    total_qty = sum(r['quantity'] for r in rows)
                                    if total_qty < req_amt:
                                        raise ValueError(f"Không đủ vật phẩm loại '{req_type}'! Cần {req_amt} (Có {total_qty}).")
                                    
                                    # 3. Deduct Items
                                    remaining_deduct = req_amt
                                    for row in rows:
                                        if remaining_deduct <= 0: break
                                        i_id = row['item_id']
                                        i_qty = row['quantity']
                                        deduct_amt = min(remaining_deduct, i_qty)
                                        
                                        await conn.execute(
                                            "UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = $3",
                                            (deduct_amt, user_id, i_id)
                                        )
                                        remaining_deduct -= deduct_amt
                                    
                                    await conn.execute(
                                        "DELETE FROM inventory WHERE user_id = $1 AND quantity <= 0", 
                                        (user_id,)
                                    )

                            # 2. APPLY REWARDS
                            rewards = btn_config.get("rewards", [])
                            acquired_txt = []
                            fail_msg = None  # Track fail message from first failed reward
                            
                            for r in rewards:
                                # Rarity Check
                                if random.random() > r.get("rate", 1.0):
                                    # Capture fail message if provided
                                    if not fail_msg and r.get("fail_msg"):
                                        fail_msg = r.get("fail_msg")
                                    continue
                                    
                                rtype = r.get("type")
                                rkey = r.get("key")
                                ramount = r.get("amount", 1)
                                
                                if rtype == "item":
                                    # CRITICAL FIX: "seeds" is currency, not inventory item
                                    if rkey == "seeds":
                                        # MUST use raw SQL - add_seeds() opens its own transaction!
                                        reason = f"event_reward_{self.manager.current_event['key']}"
                                        await conn.execute(
                                            "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                                            (ramount, user_id)
                                        )
                                        await conn.execute(
                                            "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES (?, ?, ?, ?)",
                                            (user_id, ramount, reason, "fishing")
                                        )
                                        acquired_txt.append(f"{ramount:,} Hạt 💰")
                                        logger.info(f"[GENERIC_VIEW] User {user_id} got {ramount} seeds from event {self.manager.current_event['key']}")
                                    else:
                                        # Regular item
                                        await self.manager.bot.inventory.modify(user_id, rkey, ramount)
                                        name = self._get_item_name(rkey)
                                        acquired_txt.append(f"{ramount} {name}")
                                    
                                elif rtype == "money":
                                    # MUST use raw SQL - add_seeds() opens its own transaction!
                                    reason = f"event_reward_{rkey}" if rkey else f"event_reward_{self.manager.current_event['key']}"
                                    await conn.execute(
                                        "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                                        (ramount, user_id)
                                    )
                                    await conn.execute(
                                        "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                        (user_id, ramount, reason, "fishing")
                                    )
                                    acquired_txt.append(f"{ramount:,} Hạt 💰")
                                    logger.info(f"[GENERIC_VIEW] User {user_id} got {ramount} seeds from event")
                                    
                                elif rtype == "buff":
                                    duration = r.get("duration", 10)
                                    cog = self.manager.bot.get_cog("FishingCog")
                                    name = rkey
                                    if cog:
                                        await cog.emotional_state_manager.apply_emotional_state(user_id, rkey, duration)
                                        # Note: No .states dict anymore after DB refactor - use rkey as name
                                        
                                    acquired_txt.append(f"Buff {name} ({duration}p)")
                                    
                            # 3. INCREMENT LIMIT COUNTER
                            if limit > 0:
                                 await conn.execute(
                                    """INSERT INTO user_stats (user_id, game_id, stat_key, value) 
                                       VALUES ($1, 'global_event', $2, 1)
                                       ON CONFLICT(user_id, game_id, stat_key) 
                                       DO UPDATE SET value = user_stats.value + 1""",
                                    (user_id, unique_limit_key)
                                )
                            
                            # Transaction auto-commits on success (no manual commit needed)
                            
                            # 4. MESSAGE (Win or Loss)
                            if acquired_txt:
                                # WIN - Show success message
                                msg = btn_config.get("message", "Thành công!")
                                msg += "\n🎁 Nhận: " + ", ".join(acquired_txt)
                                await interaction.followup.send(f"✅ {msg}", ephemeral=True)
                                
                                # PUBLIC BROADCAST (Only on win)
                                public_msg = btn_config.get("public_message")
                                if public_msg:
                                    formatted_msg = public_msg.replace("{user}", f"<@{user_id}>")
                                    reward_str = ", ".join(acquired_txt)
                                    formatted_msg = formatted_msg.replace("{reward}", reward_str)
                                    await interaction.channel.send(formatted_msg)
                            else:
                                # LOSS - Send ephemeral ACK first
                                loss_msg = fail_msg or "⚠️ Bạn không nhận được gì cả... (Xui quá!)"
                                await interaction.followup.send(f"❌ {loss_msg}", ephemeral=True)
                                
                                # Then PUBLIC SHAME for everyone to laugh
                                public_loss_msg = f"😂 **<@{user_id}>** đã thua! {loss_msg}"
                                await interaction.channel.send(public_loss_msg)
                                
                        except ValueError as ve:
                            # Validation error (not enough items/money) - NOT a system error
                            logger.warning(f"[GENERIC_VIEW] Validation failed for user {user_id}: {ve}")
                            await interaction.followup.send(f"⚠️ {ve}", ephemeral=True)
                            return  # Transaction auto-rollbacks, no need to raise
            except asyncio.TimeoutError:
                logger.error(f"[GENERIC_VIEW] [CRITICAL] DB Transaction Timeout for user {user_id}")
                await interaction.followup.send("⚠️ Hệ thống đang bận (DB Locked). Vui lòng thử lại sau giây lát!", ephemeral=True)
                return
                    
        except Exception as e:
                    # Real system errors only
                    logger.error(f"[GENERIC_VIEW] System error for user {user_id}: {type(e).__name__}: {e}", exc_info=True)
                    raise e
                    
        except Exception as e:
             logger.error(f"[GENERIC_VIEW] Unhandled error for user {user_id}: {type(e).__name__}: {e}", exc_info=True)
             await interaction.followup.send("❌ Lỗi hệ thống!", ephemeral=True)

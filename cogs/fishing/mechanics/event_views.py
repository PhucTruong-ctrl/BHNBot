"""Event-related views for fishing system.

Contains views for meteor shower wishes and NPC encounters.
"""
import logging
import random
import asyncio
from datetime import datetime
import discord

from database_manager import add_seeds, get_stat, increment_stat, db_manager, add_item, remove_item
from .legendary_quest_helper import increment_manh_sao_bang

logger = logging.getLogger("fishing")


class MeteorWishView(discord.ui.View):
    """View for wishing on shooting stars during meteor shower events."""
    
    def __init__(self, cog):
        super().__init__(timeout=30)
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
        if random.random() < 0.2:
            await increment_manh_sao_bang(user_id, 1)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            
            message = (
                f"🌠 **{interaction.user.name}** chắp tay nguyện cầu khi sao băng vụt qua...\n"
                f"✨ Điều kỳ diệu đã đến! Một mảnh vỡ rực sáng rơi xuống tay bạn! Bạn nhận được **Mảnh Sao Băng**! 🌠✨"
            )
            logger.info(f"[METEOR] User {interaction.user.name} ({user_id}) got SHARD")
        else:
            seeds = random.randint(10, 50)
            await add_seeds(user_id, seeds)
            await increment_stat(user_id, 'fishing', stat_key, 1)
            
            message = (
                f"🌠 **{interaction.user.name}** đã gửi một lời ước đến các vì sao...\n"
                f"🌱 Sao băng đã nghe thấy! Bạn nhận được **{seeds} hạt**! ✨"
            )
            logger.info(f"[METEOR] User {interaction.user.name} ({user_id}) got {seeds} SEEDS")
        
        await interaction.response.send_message(message, ephemeral=False)
        
        # Disable button after 15s
        await asyncio.sleep(15)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            logger.error(f"Error editing meteor view: {e}")




class GenericActionView(discord.ui.View):
    """Universal View for configured button-based events.
    
    Reads configuration from 'mechanics.buttons' in event data.
    """
    
    def __init__(self, manager):
        super().__init__(timeout=None) # Persistent view? Or rely on manager
        self.manager = manager
        # Get button config from current event of the MANAGER
        # Note: If manager.current_event is None, this will fail. 
        # But this view is created only when event is active.
        self.event_data = self.manager.current_event.get("data", {})
        # Fix: buttons are in data.data.mechanics.buttons (nested structure)
        self.buttons_config = self.event_data.get("data", {}).get("mechanics", {}).get("buttons", [])
        
        self._setup_buttons()
        
    def _setup_buttons(self):
        for idx, btn_cfg in enumerate(self.buttons_config):
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
            
    def create_callback(self, idx):
        async def callback(interaction: discord.Interaction):
            await self._handle_click(interaction, idx)
        return callback
        
    async def _handle_click(self, interaction: discord.Interaction, idx: int):
        user_id = interaction.user.id
        btn_config = self.buttons_config[idx]
        
        try:
            # ACID TRANSACTION
            async with db_manager.lock:
                await db_manager.db.execute("BEGIN")
                try:
                    # 0. CHECK LIMIT (If Configured)
                    limit = btn_config.get("limit_per_user", 0)
                    limit_key = f"event_limit_{self.manager.current_event['key']}_{idx}"
                    
                    if limit > 0:
                        # Use user_stats to track persistent limit for this event instance
                        # Note: This persists forever unless cleared. 
                        # Ideally we include start_time in key, but let's stick to simple key event_key
                        # And we can clean it up effectively? 
                        # Actually simpler: limit is "per event instance". 
                        # Let's append timestamp to key to auto-expiration effectively (logic wise)
                        # key = f"{limit_key}_{int(self.manager.current_event['start_time'])}"
                        # But stat key max length? TEXT. It's fine.
                        
                        unique_limit_key = f"{limit_key}_{int(self.manager.current_event['start_time'])}"
                        
                        cursor = await db_manager.db.execute(
                            "SELECT value FROM user_stats WHERE user_id = ? AND game_id = 'global_event' AND stat_key = ?",
                            (user_id, unique_limit_key)
                        )
                        row = await cursor.fetchone()
                        current_usage = row[0] if row else 0
                        
                        if current_usage >= limit:
                            raise ValueError(f"⛔ Bạn đã đạt giới hạn mua ({limit}/{limit})!")

                    # 1. CHECK & PAY COST
                    cost = btn_config.get("cost", {})
                    # A. Money Cost
                    money_cost = cost.get("money", 0)
                    if money_cost > 0:
                        cursor = await db_manager.db.execute("SELECT seeds FROM users WHERE user_id = ?", (user_id,))
                        row = await cursor.fetchone()
                        current_bal = row[0] if row else 0
                        
                        if current_bal < money_cost:
                             raise ValueError(f"Không đủ tiền! Cần {money_cost} Hạt.")
                             
                        await db_manager.db.execute(
                            "UPDATE users SET seeds = seeds - ? WHERE user_id = ?",
                            (money_cost, user_id)
                        )
                    
                    # B. Item Cost (Barter)
                    item_input = cost.get("item") # { "key": "trash_01", "amount": 1 }
                    item_type_input = cost.get("item_type") # { "type": "trash", "amount": 10 }
                    
                    if item_input:
                        req_key = item_input.get("key")
                        req_amt = item_input.get("amount", 1)
                        if req_key and req_amt > 0:
                            cursor = await db_manager.db.execute(
                                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                                (user_id, req_key)
                            )
                            row = await cursor.fetchone()
                            start_qty = row[0] if row else 0
                            
                            if start_qty < req_amt:
                                raise ValueError(f"Không đủ vật phẩm! Cần {req_amt} {req_key}.")
                            
                            await db_manager.db.execute(
                                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                                (req_amt, user_id, req_key)
                            )

                    elif item_type_input:
                        # Handle cost by generic TYPE (e.g. "Any 10 Trash")
                        req_type = item_type_input.get("type")
                        req_amt = item_type_input.get("amount", 10)
                        
                        if req_type and req_amt > 0:
                            # 1. Load Item Definitions to find keys
                            import json
                            valid_keys = []
                            try:
                                with open("data/fishing_items.json", "r", encoding="utf-8") as f:
                                    f_data = json.load(f)
                                    items_dict = f_data.get("items", {})
                                    valid_keys = [k for k, v in items_dict.items() if v.get("type") == req_type]
                            except Exception as e:
                                logger.error(f"Failed to load fishing_items.json: {e}")
                                raise ValueError("Lỗi hệ thống: Không tải được danh sách vật phẩm.")
                            
                            if not valid_keys:
                                raise ValueError(f"Không tìm thấy loại vật phẩm '{req_type}' trong hệ thống.")

                            # 2. Check User Inventory for ANY of these keys
                            placeholders = ','.join('?' for _ in valid_keys)
                            query = f"SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id IN ({placeholders})"
                            params = [user_id] + valid_keys
                            
                            cursor = await db_manager.db.execute(query, params)
                            rows = await cursor.fetchall() # [(item_id, qty), ...]
                            
                            total_qty = sum(r[1] for r in rows)
                            if total_qty < req_amt:
                                raise ValueError(f"Không đủ vật phẩm loại '{req_type}'! Cần {req_amt} (Có {total_qty}).")
                            
                            # 3. Deduct Items (Greedy approach)
                            remaining_deduct = req_amt
                            for i_id, i_qty in rows:
                                if remaining_deduct <= 0:
                                    break
                                    
                                deduct_amt = min(remaining_deduct, i_qty)
                                
                                await db_manager.db.execute(
                                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                                    (deduct_amt, user_id, i_id)
                                )
                                remaining_deduct -= deduct_amt
                            
                            # Cleanup 0 quantity rows? Usually database_manager.remove_item handles it
                            # But raw SQL here might leave 0s. 
                            # Safe to run a cleanup or just leave it (get_inventory usually explicitly filters >0 or handles 0)
                            # Let's run a quick cleanup for cleanliness
                            await db_manager.db.execute(
                                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0", 
                                (user_id,)
                            )

                    # 2. APPLY REWARDS
                    rewards = btn_config.get("rewards", [])
                    acquired_txt = []
                    
                    for r in rewards:
                        # Rarity Check
                        if random.random() > r.get("rate", 1.0):
                            continue
                            
                        rtype = r.get("type")
                        rkey = r.get("key")
                        ramount = r.get("amount", 1)
                        
                        if rtype == "item":
                            await add_item(user_id, rkey, ramount)
                            acquired_txt.append(f"{ramount} {rkey}")
                            
                        elif rtype == "buff":
                            duration = r.get("duration", 10)
                            # Need access to EmotionalStateManager... 
                            # self.manager.bot.get_cog("FishingCog").emotional_state_manager
                            cog = self.manager.bot.get_cog("FishingCog")
                            if cog:
                                await cog.emotional_state_manager.apply_emotional_state(user_id, rkey, duration)
                            acquired_txt.append(f"Buff {rkey} ({duration}p)")
                            
                    # 3. MESSAGE
                    msg = btn_config.get("message", "Thành công!")
                    if acquired_txt:
                        msg += "\n🎁 Nhận: " + ", ".join(acquired_txt)
                    
                    if limit > 0:
                         await db_manager.db.execute(
                            """INSERT INTO user_stats (user_id, game_id, stat_key, value) 
                               VALUES (?, 'global_event', ?, 1)
                               ON CONFLICT(user_id, game_id, stat_key) 
                               DO UPDATE SET value = value + 1""",
                            (user_id, unique_limit_key)
                        )
                        
                    await db_manager.db.commit()
                    
                    # Ephemeral for user
                    await interaction.response.send_message(f"✅ {msg}", ephemeral=True)
                    
                    # 5. PUBLIC BROADCAST (Optional)
                    public_msg = btn_config.get("public_message")
                    if public_msg:
                        # Simple formatting
                        # Support {user} placeholder
                        formatted_msg = public_msg.replace("{user}", f"<@{user_id}>")
                        if acquired_txt:
                            formatted_msg = formatted_msg.replace("{reward}", ", ".join(acquired_txt))
                        
                        await interaction.channel.send(formatted_msg)
                        
                except Exception as e:
                    await db_manager.db.rollback()
                    raise e
                    
                except Exception as e:
                    await db_manager.db.rollback()
                    raise e
                    
        except ValueError as ve:
             await interaction.response.send_message(str(ve), ephemeral=True)
        except Exception as e:
             logger.error(f"[GENERIC_VIEW] Error: {e}")
             await interaction.response.send_message("❌ Lỗi hệ thống!", ephemeral=True)

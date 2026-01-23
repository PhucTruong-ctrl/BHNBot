"""Event-related views for fishing system."""

from core.logging import get_logger
import random
import asyncio
from datetime import datetime

import discord

from database_manager import add_seeds, get_stat, increment_stat, db_manager
from ..constants import ALL_FISH, ALL_ITEMS_DATA

logger = get_logger("fishing_ui_event_views")


class MeteorWishView(discord.ui.View):
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
        self.wished_users = set()
    
    @discord.ui.button(label="🙏 Ước Nguyện", style=discord.ButtonStyle.primary, emoji="💫")
    async def wish_on_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        stat_key = "total_wishes"
        
        if user_id in self.wished_users:
            await interaction.response.send_message("Bạn đã ước rồi!", ephemeral=True)
            return
        
        self.wished_users.add(user_id)
        
        await interaction.response.defer()
        
        if random.random() < 0.2:
            from ..mechanics.legendary_quest_helper import increment_manh_sao_bang
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
        
        await asyncio.sleep(15)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            logger.error(f"Error editing meteor view: {e}")


class GenericActionView(discord.ui.View):
    
    def __init__(self, manager):
        super().__init__(timeout=600)
        self.manager = manager
        self.event_data = self.manager.current_event.get("data", {})
        self.buttons_config = self.event_data.get("data", {}).get("mechanics", {}).get("buttons", [])
        self._setup_buttons()
        
    def _setup_buttons(self):
        for idx, btn_cfg in enumerate(self.buttons_config):
            try:
                style = getattr(discord.ButtonStyle, btn_cfg.get("style", "primary"), discord.ButtonStyle.primary)
                
                button = discord.ui.Button(
                    label=btn_cfg.get("label", "Click Me"),
                    style=style,
                    emoji=btn_cfg.get("emoji"),
                    custom_id=f"generic_btn_{idx}"
                )
                button.callback = self.create_callback(idx)
                self.add_item(button)
            except Exception as e:
                logger.error(f"[GENERIC_VIEW] Failed to add button {idx}: {e}", exc_info=True)
            
    def create_callback(self, idx):
        async def callback(interaction: discord.Interaction):
            try:
                await interaction.response.defer(ephemeral=True)
            except (discord.NotFound, discord.HTTPException) as e:
                logger.warning(f"[GENERIC_VIEW] Failed to defer: {e}")
                return

            await self._handle_click(interaction, idx)
        return callback
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        logger.error(f"[GENERIC_VIEW] Error: {type(error).__name__}: {error}", exc_info=error)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Lỗi: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Lỗi: {error}", ephemeral=True)
        except Exception as send_error:
            logger.debug(f"[EVENT_VIEW] Could not send error message: {send_error}")
    
    def _get_item_name(self, key):
        if key in ALL_FISH: 
            return ALL_FISH[key].get("name", key)
        if key in ALL_ITEMS_DATA: 
            return ALL_ITEMS_DATA[key].get("name", key)
        return key

    async def _handle_click(self, interaction: discord.Interaction, idx: int):
        user_id = interaction.user.id
        btn_config = self.buttons_config[idx]
        
        try:
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        limit = btn_config.get("limit_per_user", 0)
                        unique_limit_key = None
                        
                        if limit > 0:
                            today = datetime.now().strftime("%Y-%m-%d")
                            unique_limit_key = f"event_limit_{self.manager.current_event['key']}_{idx}_{today}"
                            
                            row = await conn.fetchrow(
                                "SELECT value FROM user_stats WHERE user_id = $1 AND game_id = 'global_event' AND stat_key = $2",
                                user_id, unique_limit_key
                            )
                            current_usage = row[0] if row else 0
                            
                            if current_usage >= limit:
                                raise ValueError(f"⛔ Bạn đã đạt giới hạn hôm nay ({limit}/{limit})!")

                        cost = btn_config.get("cost", {})
                        money_cost = cost.get("money", 0)
                        if money_cost > 0:
                            row = await conn.fetchrow("SELECT seeds FROM users WHERE user_id = $1", user_id)
                            current_bal = row[0] if row else 0
                            
                            if current_bal < money_cost:
                                raise ValueError(f"Không đủ tiền! Cần {money_cost} Hạt.")
                                
                            await conn.execute(
                                "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                                money_cost, user_id
                            )
                            await conn.execute(
                                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                user_id, -money_cost, f"event_buy_{btn_config.get('label', 'generic')}", "fishing"
                            )
                        
                        item_input = cost.get("item")
                        item_type_input = cost.get("item_type")
                        
                        if item_input:
                            req_key = item_input.get("key")
                            req_amt = item_input.get("amount", 1)
                            if req_key and req_amt > 0:
                                row = await conn.fetchrow(
                                    "SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2",
                                    user_id, req_key
                                )
                                start_qty = row[0] if row else 0
                                
                                if start_qty < req_amt:
                                    raise ValueError(f"Không đủ vật phẩm! Cần {req_amt} {req_key}.")
                                
                                await conn.execute(
                                    "UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = $3",
                                    req_amt, user_id, req_key
                                )

                        elif item_type_input:
                            req_type = item_type_input.get("type")
                            req_amt = item_type_input.get("amount", 10)
                            
                            if req_type and req_amt > 0:
                                valid_keys = [k for k, v in ALL_ITEMS_DATA.items() if v.get("type") == req_type]
                                
                                if not valid_keys:
                                    raise ValueError(f"Không tìm thấy loại vật phẩm '{req_type}'.")

                                placeholders = ','.join(f"${i+2}" for i in range(len(valid_keys)))
                                query = f"SELECT item_id, quantity FROM inventory WHERE user_id = $1 AND item_id IN ({placeholders})"
                                
                                rows = await conn.fetch(query, user_id, *valid_keys)
                                
                                total_qty = sum(r['quantity'] for r in rows)
                                if total_qty < req_amt:
                                    raise ValueError(f"Không đủ vật phẩm loại '{req_type}'! Cần {req_amt} (Có {total_qty}).")
                                
                                remaining_deduct = req_amt
                                for row in rows:
                                    if remaining_deduct <= 0: 
                                        break
                                    i_id = row['item_id']
                                    i_qty = row['quantity']
                                    deduct_amt = min(remaining_deduct, i_qty)
                                    
                                    await conn.execute(
                                        "UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = $3",
                                        deduct_amt, user_id, i_id
                                    )
                                    remaining_deduct -= deduct_amt
                                
                                await conn.execute(
                                    "DELETE FROM inventory WHERE user_id = $1 AND quantity <= 0", 
                                    user_id
                                )

                        rewards = btn_config.get("rewards", [])
                        acquired_txt = []
                        fail_msg = None
                        
                        for r in rewards:
                            if random.random() > r.get("rate", 1.0):
                                if not fail_msg and r.get("fail_msg"):
                                    fail_msg = r.get("fail_msg")
                                continue
                                
                            rtype = r.get("type")
                            rkey = r.get("key")
                            ramount = r.get("amount", 1)
                            
                            if rtype == "item":
                                if rkey == "seeds":
                                    reason = f"event_reward_{self.manager.current_event['key']}"
                                    await conn.execute(
                                        "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                                        ramount, user_id
                                    )
                                    await conn.execute(
                                        "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                        user_id, ramount, reason, "fishing"
                                    )
                                    acquired_txt.append(f"{ramount:,} Hạt 💰")
                                else:
                                    await self.manager.bot.inventory.modify(user_id, rkey, ramount)
                                    name = self._get_item_name(rkey)
                                    acquired_txt.append(f"{ramount} {name}")
                                
                            elif rtype == "money":
                                reason = f"event_reward_{rkey}" if rkey else f"event_reward_{self.manager.current_event['key']}"
                                await conn.execute(
                                    "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                                    ramount, user_id
                                )
                                await conn.execute(
                                    "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                    user_id, ramount, reason, "fishing"
                                )
                                acquired_txt.append(f"{ramount:,} Hạt 💰")
                                
                            elif rtype == "buff":
                                duration = r.get("duration", 10)
                                cog = self.manager.bot.get_cog("FishingCog")
                                name = rkey
                                if cog:
                                    await cog.emotional_state_manager.apply_emotional_state(user_id, rkey, duration)
                                    
                                acquired_txt.append(f"Buff {name} ({duration}p)")
                                
                        if limit > 0 and unique_limit_key:
                            await conn.execute(
                                """INSERT INTO user_stats (user_id, game_id, stat_key, value) 
                                   VALUES ($1, 'global_event', $2, 1)
                                   ON CONFLICT(user_id, game_id, stat_key) 
                                   DO UPDATE SET value = user_stats.value + 1""",
                                user_id, unique_limit_key
                            )
                        
                        if acquired_txt:
                            msg = btn_config.get("message", "Thành công!")
                            msg += "\n🎁 Nhận: " + ", ".join(acquired_txt)
                            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
                            
                            public_msg = btn_config.get("public_message")
                            if public_msg and interaction.channel:
                                formatted_msg = public_msg.replace("{user}", f"<@{user_id}>")
                                reward_str = ", ".join(acquired_txt)
                                formatted_msg = formatted_msg.replace("{reward}", reward_str)
                                await interaction.channel.send(formatted_msg)
                        else:
                            loss_msg = fail_msg or "⚠️ Bạn không nhận được gì cả... (Xui quá!)"
                            await interaction.followup.send(f"❌ {loss_msg}", ephemeral=True)
                            
                            if interaction.channel:
                                public_loss_msg = f"😂 **<@{user_id}>** đã thua! {loss_msg}"
                                await interaction.channel.send(public_loss_msg)
                                
            except asyncio.TimeoutError:
                logger.error(f"[GENERIC_VIEW] DB Transaction Timeout for user {user_id}")
                await interaction.followup.send("⚠️ Hệ thống đang bận. Vui lòng thử lại!", ephemeral=True)
                return
                    
        except ValueError as ve:
            logger.warning(f"[GENERIC_VIEW] Validation failed for user {user_id}: {ve}")
            await interaction.followup.send(f"⚠️ {ve}", ephemeral=True)
        except Exception as e:
            logger.error(f"[GENERIC_VIEW] Error for user {user_id}: {e}", exc_info=True)
            await interaction.followup.send("❌ Lỗi hệ thống!", ephemeral=True)

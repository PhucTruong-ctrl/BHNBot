"""Sell-related Views for fishing system."""

import discord
import random
import asyncio
from typing import Dict, Any
from discord.ui import View, Button

from database_manager import add_seeds, db_manager, increment_stat, get_stat
from core.logging import setup_logger
from ..constants import ALL_FISH, TRASH_ITEMS

logger = setup_logger("FishingSellViews", "cogs/fishing/fishing.log")


class FishSellView(discord.ui.View):
    """Display-only view for fishing results (sell buttons removed)."""
    
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
        self.sold = False
    
    async def on_timeout(self):
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(
                    content="⏰ **Hết thời gian!** Phiên hiển thị đã kết thúc.",
                    view=None
                )
        except:
            pass
        
        if self.user_id in self.cog.caught_items:
            try:
                del self.cog.caught_items[self.user_id]
            except Exception as e:
                logger.error(f"Unexpected error: {e}")


class HagglingView(discord.ui.View):
    """A view for the Haggling minigame."""
    
    def __init__(self, cog, user_id, caught_items, base_total, username):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.base_total = base_total
        self.username = username
        self.completed = False
    
    @discord.ui.button(label="🤝 Chốt Luôn", style=discord.ButtonStyle.green)
    async def accept_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            return
        
        if self.completed:
            return
        
        self.completed = True
        
        try:
            for fish_key, quantity in self.caught_items.items():
                await self.cog.bot.inventory.modify(self.user_id, fish_key, -quantity)
            
            await add_seeds(self.user_id, self.base_total, reason='haggle_accept', category='fishing')
            
            embed = discord.Embed(
                title="🤝 **CHỐT XONG!**",
                description=f"💰 Nhận: **{self.base_total} Hạt**\n\n✅ An toàn là trên hết!",
                color=discord.Color.green()
            )
            
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"[HAGGLE_ACCEPT] {self.username} (user_id={self.user_id}) earned {self.base_total} seeds")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)
    
    @discord.ui.button(label="😏 Đòi Thêm", style=discord.ButtonStyle.primary)
    async def demand_more(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            return
        
        if self.completed:
            return
        
        self.completed = True
        success = random.random() < 0.4
        
        if success:
            final_total = int(self.base_total * 1.3)
            message = f"💰 Nhận: **{final_total} Hạt** (+30%)\n\n😎 Thương lái khúc xương! Bạn làm ăn quá khéo!"
            color = discord.Color.gold()
            action = "SUCCESS"
        else:
            final_total = int(self.base_total * 0.8)
            message = f"💸 Chỉ nhận: **{final_total} Hạt** (-20%)\n\n😤 Thương lái dỗi bỏ đi rồi bán cho người khác với giá rẻ hơn!"
            color = discord.Color.red()
            action = "FAIL"
        
        try:
            for fish_key, quantity in self.caught_items.items():
                await self.cog.bot.inventory.modify(self.user_id, fish_key, -quantity)
            
            await add_seeds(self.user_id, final_total, reason='haggle_result', category='fishing')
            
            embed = discord.Embed(
                title=f"😏 **MẶC CÀ {action}!**",
                description=message,
                color=color
            )
            
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"[HAGGLE_{action}] {self.username} (user_id={self.user_id}) earned {final_total} seeds")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)


class TrashSellView(View):
    """View for Black Market trash selling."""
    
    def __init__(self, manager):
        super().__init__(timeout=600)
        self.manager = manager

    async def _process_sell(self, interaction: discord.Interaction, amount_mode: str):
        await interaction.response.defer(ephemeral=False)
        
        if not self.manager.current_event or self.manager.current_event["key"] != "scrap_yard":
            await interaction.followup.send("⚠️ Chú Ba đã lái xe đi mất rồi!", ephemeral=True)
            return

        user_id = interaction.user.id
        inventory = await self.manager.bot.inventory.get_all(user_id)
        
        trash_keys = [t["key"] for t in TRASH_ITEMS]
        user_trash = {k: v for k, v in inventory.items() if k in trash_keys and v > 0}
        
        if not user_trash:
            await interaction.followup.send("🗑️ Túi của bạn sạch bong! Không có rác để bán.", ephemeral=True)
            return

        to_sell = {}
        
        if amount_mode == "all":
            to_sell = user_trash.copy()
        else:
            limit = int(amount_mode)
            collected = 0
            for key, qty in user_trash.items():
                take = min(qty, limit - collected)
                to_sell[key] = take
                collected += take
                if collected >= limit:
                    break
        
        if not to_sell:
            await interaction.followup.send("❌ Không tìm thấy rác để bán.", ephemeral=True)
            return

        total_seeds = 0
        lines = []
        
        for key, qty in to_sell.items():
            evt_mech = self.manager.current_event.get("data", {}).get("mechanics", {})
            min_price = evt_mech.get("trash_price_min", 100)
            max_price = evt_mech.get("trash_price_max", 800)
            
            unit_price = random.randint(min_price, max_price)
            line_total = unit_price * qty
            total_seeds += line_total
            
            await self.manager.bot.inventory.modify(user_id, key, -qty)
            
            item_name = next((t["name"] for t in TRASH_ITEMS if t["key"] == key), key)
            lines.append(f"🗑️ **{item_name}** x{qty}: `{line_total:,} Hạt` ({unit_price}/c)")

        await add_seeds(user_id, total_seeds, reason='sell_trash', category='fishing')
        
        desc = "\n".join(lines)
        if len(desc) > 1000: 
            desc = desc[:1000] + "\n...(còn nữa)"
        
        username = interaction.user.name.upper()
        embed = discord.Embed(
            title=f"🧾 HÓA ĐƠN BÁN VE CHAI - {username}",
            description=f"{desc}\n\n💰 **TỔNG NHẬN:** `{total_seeds:,} Hạt`",
            color=discord.Color.green()
        )
        embed.set_footer(text="Chú Ba: 'Chai bao nhôm nhựa bán hông con??'")
        
        await interaction.followup.send(embed=embed, ephemeral=False)

    @discord.ui.button(label="Bán 1 Rác", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def sell_one(self, interaction: discord.Interaction, button: Button):
        await self._process_sell(interaction, "1")

    @discord.ui.button(label="Bán 10 Rác", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def sell_ten(self, interaction: discord.Interaction, button: Button):
        await self._process_sell(interaction, "10")

    @discord.ui.button(label="♻️ BÁN HẾT RÁC", style=discord.ButtonStyle.danger, emoji="💰")
    async def sell_all(self, interaction: discord.Interaction, button: Button):
        await self._process_sell(interaction, "all")


class InteractiveSellEventView(discord.ui.View):
    """Base class for interactive sell events."""
    
    STAT_MAPPINGS = {
        ('black_market', 'accept'): 'risky_choices_made',
        ('black_market', 'decline'): 'safe_choices_made',
        ('haggle_master', 'haggle'): 'haggle_attempts',
        ('haggle_master', 'accept'): 'safe_choices_made',
        ('risky_buyer', 'accept'): 'risky_choices_made',
        ('risky_buyer', 'decline'): 'safe_choices_made',
        ('auction_house', 'enter_auction'): 'risky_choices_made',
        ('auction_house', 'skip'): 'safe_choices_made',
        ('double_or_nothing', 'all_in'): 'risky_choices_made',
        ('double_or_nothing', 'play_safe'): 'safe_choices_made',
        ('quality_inspector', 'reroll'): 'risky_choices_made',
        ('quality_inspector', 'keep'): 'safe_choices_made',
        ('charity_donation', 'donate'): 'charity_donations',
        ('express_sale', 'express'): 'risky_choices_made',
        ('express_sale', 'normal'): 'safe_choices_made', 
        ('investment_offer', 'invest'): 'risky_choices_made',
        ('investment_offer', 'decline'): 'safe_choices_made',
        ('fish_contest', 'enter_contest'): 'risky_choices_made',
        ('fish_contest', 'sell_normal'): 'safe_choices_made',
    }
    
    def __init__(
        self, 
        cog, 
        user_id: int, 
        fish_items: Dict[str, int],
        base_value: int,
        event_data: Dict[str, Any],
        ctx_or_interaction
    ):
        timeout = event_data.get('interactive', {}).get('timeout', 30)
        super().__init__(timeout=timeout)
        
        self.cog = cog
        self.user_id = user_id
        self.fish_items = fish_items
        self.base_value = base_value
        self.event_data = event_data
        self.ctx = ctx_or_interaction
        self.completed = False
        
        self._add_choice_buttons()
    
    def _add_choice_buttons(self):
        choices = self.event_data.get('interactive', {}).get('choices', [])
        
        for choice in choices:
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
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Không phải cá của bạn!", ephemeral=True)
                return
            
            if self.completed:
                await interaction.response.send_message("❌ Đã chọn rồi!", ephemeral=True)
                return
            
            self.completed = True
            
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            
            await interaction.response.edit_message(view=self)
            
            outcome = self._roll_outcome(choice['outcomes'])
            
            multiplier = outcome.get('mul', 1.0)
            flat_bonus = outcome.get('flat', 0)
            final_value = int(self.base_value * multiplier) + flat_bonus
            
            await self._execute_sell(
                interaction, 
                final_value, 
                outcome.get('message', ''),
                choice['id'],
                selected_outcome=outcome
            )
        
        return callback
    
    def _roll_outcome(self, outcomes: list) -> Dict:
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
        try:
            consume_items = True
            
            choices = self.event_data.get('interactive', {}).get('choices', [])
            selected_choice = next((c for c in choices if c['id'] == choice_id), None)
            
            if selected_outcome and 'consume_items' in selected_outcome:
                consume_items = selected_outcome['consume_items']
            elif selected_choice and 'consume_items' in selected_choice:
                consume_items = selected_choice['consume_items']
            else:
                consume_items = self.event_data.get('interactive', {}).get('consume_items', True)
            
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        if consume_items:
                            for fish_key, item_data in self.fish_items.items():
                                if isinstance(item_data, dict):
                                    qty_to_deduct = item_data.get('quantity', 0)
                                else:
                                    qty_to_deduct = item_data
                                
                                row = await conn.fetchrow(
                                    "SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2",
                                    self.user_id, fish_key
                                )
                                
                                if not row or row['quantity'] < qty_to_deduct:
                                    raise ValueError(f"Không đủ cá {fish_key}! (Cần {qty_to_deduct}, Có {row['quantity'] if row else 0})")
                                
                                await conn.execute(
                                    "UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = $3",
                                    qty_to_deduct, self.user_id, fish_key
                                )
                            
                            await conn.execute(
                                "DELETE FROM inventory WHERE user_id = $1 AND quantity <= 0", 
                                self.user_id
                            )
                        
                        if final_value != 0:
                            await conn.execute(
                                "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                                final_value, self.user_id
                            )
                            event_key = self.event_data.get('key', 'unknown')
                            await conn.execute(
                                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                self.user_id, final_value, f"interactive_sell_{event_key}", "fishing"
                            )
            except asyncio.TimeoutError:
                await interaction.followup.send("⚠️ Giao dịch bị hủy do hệ thống bận. Vui lòng thử lại!", ephemeral=True)
                return
            
            try:
                if hasattr(self.cog.bot, 'inventory'):
                    await self.cog.bot.inventory.invalidate(self.user_id)
            except Exception:
                pass

            if final_value > 0:
                await self.cog.global_event_manager.process_raid_contribution(self.user_id, final_value)

            if selected_outcome and 'durability_change' in selected_outcome:
                change = selected_outcome['durability_change']
                from ..mechanics.rod_system import get_rod_data, update_rod_data
                rod_level, current_durability = await get_rod_data(self.user_id)
                new_durability = max(0, current_durability + change)
                await update_rod_data(self.user_id, new_durability)
                
            if selected_outcome and 'buff' in selected_outcome:
                buff_data = selected_outcome['buff']
                buff_type = buff_data.get('type')
                duration = buff_data.get('duration', 0)
                if buff_type:
                    await self.cog.emotional_state_manager.apply_emotional_state(
                        self.user_id, buff_type, duration
                    )
            
            event_key = self.event_data.get('key', 'unknown')
            await self._track_stats(event_key, choice_id, final_value > self.base_value, final_value)
            
            embed = self._build_result_embed(final_value, message, interaction.user.name)
            
            await interaction.followup.send(embed=embed, ephemeral=False)
            
            logger.info(
                f"[INTERACTIVE_SELL] {interaction.user.name} (user_id={self.user_id}) "
                f"sold via {event_key} choice={choice_id} value={final_value} items_consumed={consume_items}"
            )
            
        except ValueError as ve:
            msg = f"❌ **Giao dịch thất bại!**\n{str(ve)}\n\n_Có thể bạn đã bán số cá này ở lệnh khác._"
            
            try:
                await interaction.followup.send(msg, ephemeral=True)
                
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)
                self.stop()
            except Exception:
                pass
                
            logger.warning(f"[INTERACTIVE_SELL_FAIL] Transaction blocked: {ve}")
            self.completed = True
                
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi hệ thống: {e}", ephemeral=True)
            self.completed = False
            logger.error(f"[INTERACTIVE_SELL_ERROR] {e}", exc_info=True)

    async def _track_stats(self, event_key: str, choice_id: str, is_win: bool, final_value: int = 0):
        try:
            await increment_stat(self.user_id, "fishing", "interactive_events_triggered", 1)
            
            stat_key = f"{event_key}_{choice_id}"
            await increment_stat(self.user_id, "fishing", stat_key, 1)
            
            global_stat = self.STAT_MAPPINGS.get((event_key, choice_id))
            if global_stat:
                await increment_stat(self.user_id, "fishing", global_stat, 1)
            
            if global_stat == 'risky_choices_made' or event_key in ['haggle_master', 'investment_offer', 'fish_contest']:
                if is_win:
                    await increment_stat(self.user_id, "fishing", f"{event_key}_wins", 1)
                    if event_key == 'investment_offer':
                        await increment_stat(self.user_id, "fishing", "investment_wins", 1)
                    elif event_key == 'fish_contest':
                        await increment_stat(self.user_id, "fishing", "contest_wins", 1)
                else:
                    await increment_stat(self.user_id, "fishing", f"{event_key}_losses", 1)
                    if event_key == 'investment_offer':
                        await increment_stat(self.user_id, "fishing", "investment_losses", 1)

            if final_value > 0:
                await increment_stat(self.user_id, "fishing", "total_money_earned", final_value)
            
            if event_key == 'haggle_master' and is_win:
                await increment_stat(self.user_id, "fishing", "successful_haggles", 1)
            
            if event_key == 'black_market':
                if is_win:
                    await increment_stat(self.user_id, "fishing", "black_market_successes", 1)
                else:
                    await increment_stat(self.user_id, "fishing", "black_market_failures", 1)
            
            if event_key == 'investment_offer' and choice_id == 'invest':
                await increment_stat(self.user_id, "fishing", "shark_tank_event", 1)

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
                if event_key == 'investment_offer': 
                    stats_to_check.append("investment_wins")
                if event_key == 'fish_contest': 
                    stats_to_check.append("contest_wins")
            
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
        event_name = self.event_data.get('name', 'Sự Kiện')
        
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
        
        embed.add_field(
            name="💰 Kết Quả",
            value=f"**+{final_value:,} Hạt**",
            inline=False
        )
        
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
        if self.completed:
            return
        
        self.completed = True
        
        logger.info(f"[INTERACTIVE_SELL] Timeout for user {self.user_id}, auto-selecting safe choice")
        
        choices = self.event_data.get('interactive', {}).get('choices', [])
        safest_choice = None
        safest_min_value = -float('inf')
        
        for choice in choices:
            min_outcome = min(
                o.get('mul', 1.0) * self.base_value + o.get('flat', 0)
                for o in choice['outcomes']
            )
            
            if min_outcome > safest_min_value:
                safest_min_value = min_outcome
                safest_choice = choice
        
        if not safest_choice:
            safest_choice = {
                'id': 'timeout_default',
                'outcomes': [{'mul': 1.0, 'flat': 0, 'weight': 1.0, 'message': 'Timeout - Bán tự động'}]
            }
        
        outcome = self._roll_outcome(safest_choice.get('outcomes', []))
        multiplier = outcome.get('mul', 1.0)
        flat_bonus = outcome.get('flat', 0)
        final_value = int(self.base_value * multiplier) + flat_bonus
        final_value = max(0, final_value)
        
        try:
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        consume_items = True
                        if safest_choice and 'consume_items' in safest_choice:
                            consume_items = safest_choice['consume_items']
                        else:
                            consume_items = self.event_data.get('interactive', {}).get('consume_items', True)
                        
                        if consume_items:
                            for fish_key, quantity in self.fish_items.items():
                                row = await conn.fetchrow(
                                    "SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2",
                                    self.user_id, fish_key
                                )
                                
                                if not row or row['quantity'] < quantity:
                                    raise ValueError(f"Timeout failed: Not enough {fish_key}")
                                
                                await conn.execute(
                                    "UPDATE inventory SET quantity = quantity - $1 WHERE user_id = $2 AND item_id = $3",
                                    quantity, self.user_id, fish_key
                                )
                            
                            await conn.execute(
                                "DELETE FROM inventory WHERE user_id = $1 AND quantity <= 0",
                                self.user_id
                            )
                        
                        if final_value != 0:
                            await conn.execute(
                                "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                                final_value, self.user_id
                            )
                            event_key = self.event_data.get('key', 'unknown')
                            await conn.execute(
                                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                self.user_id, final_value, f"interactive_sell_timeout_{event_key}", "fishing"
                            )
            except asyncio.TimeoutError:
                logger.error(f"[INTERACTIVE_SELL] Timeout Handler DB Lock Timeout for user {self.user_id}")
                return
            
            try:
                if hasattr(self.cog.bot, 'inventory'):
                    await self.cog.bot.inventory.invalidate(self.user_id)
            except Exception:
                pass
            
            event_key = self.event_data.get('key', 'unknown')
            await increment_stat(self.user_id, "fishing", f"{event_key}_timeout", 1)
            
            logger.info(
                f"[INTERACTIVE_SELL] Timeout auto-sell completed: user={self.user_id} "
                f"value={final_value} choice={safest_choice.get('id', 'unknown')} consumed={consume_items}"
            )
            
        except Exception as e:
            logger.error(f"[INTERACTIVE_SELL_TIMEOUT_ERROR] {e}", exc_info=True)

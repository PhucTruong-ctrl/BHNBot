"""UI views for fishing system."""

import discord
import random
from database_manager import remove_item, add_seeds, get_inventory
from .constants import ALL_FISH, DB_PATH, LEGENDARY_FISH_KEYS
from .glitch import apply_display_glitch
from core.logger import setup_logger

logger = setup_logger("FishingViews", "cogs/fishing/fishing.log")

class FishSellView(discord.ui.View):
    """A view for handling fish selling interactions.

    Allows users to sell caught fish, access the black market, or haggle for better prices.
    """
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
        self.sold = False  # Flag to prevent double-selling
        
        # Calculate base total for haggle check
        self.base_total = 0
        for fish_key, quantity in self.caught_items.items():
            fish_info = ALL_FISH.get(fish_key)
            if fish_info:
                self.base_total += fish_info['sell_price'] * quantity
        
        # 10% chance to add Black Market button
        if random.random() < 0.1:
            black_market_btn = discord.ui.Button(
                label="🕵️ Bán Chợ Đen (x3 hoặc Mất Trắng)",
                style=discord.ButtonStyle.danger,
                custom_id="black_market_sell"
            )
            black_market_btn.callback = self.sell_black_market
            self.add_item(black_market_btn)
        
        # Add Haggle button if base_total > 1000
        if self.base_total > 1000:
            haggle_btn = discord.ui.Button(
                label="😏 Mặc Cả (Đánh Giá Lại)",
                style=discord.ButtonStyle.primary,
                custom_id="haggle_sell"
            )
            haggle_btn.callback = self.start_haggle
            self.add_item(haggle_btn)
    
    async def on_timeout(self):
        """Cleans up the view when it times out (5 minutes).

        Removes the user's caught items from the temporary cache to release memory.
        """
        # Remove caught_items cache since user didn't sell
        if self.user_id in self.cog.caught_items:
            try:
                del self.cog.caught_items[self.user_id]
            except:
                pass
    
    @discord.ui.button(label="💰 Bán Cá Vừa Câu", style=discord.ButtonStyle.green)
    async def sell_caught_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handles the standard sell action.

        Calculates the total value of caught fish and updates the user's balance.
        Applies buffs like 'Keo Ly' (x2) or 'Harvest Boost' if active.
        Uses an atomic transaction to prevent duplication.
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        # Check if already sold (CRITICAL: prevent race condition)
        if self.sold:
            await interaction.response.send_message("❌ Cá này đã bán rồi!", ephemeral=True)
            return
        
        # Mark as sold IMMEDIATELY (before any async operations)
        self.sold = True
        
        # Disable button IMMEDIATELY to prevent double-click
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send("⏳ Đang xử lý...", ephemeral=True)
        
        try:
            total_money = 0
            for fish_key, quantity in self.caught_items.items():
                # Skip legendary fish - they cannot be sold
                if fish_key in LEGENDARY_FISH_KEYS:
                    continue
                fish_info = ALL_FISH.get(fish_key)
                if fish_info:
                    base_price = fish_info['sell_price']
                    total_money += base_price * quantity
            
            # *** APPLY KECO LỲ BUFF (2x sell price for 10 minutes) ***
            keo_ly_message = ""
            if hasattr(self.cog, 'check_emotional_state') and self.cog.check_emotional_state(self.user_id, "keo_ly"):
                total_money = total_money * 2
                keo_ly_message = " (💅 **Keo Lỳ Buff x2**)"
                logger.info(f"[SELL] {interaction.user.name} applied keo_ly buff x2 multiplier")
            
            # Apply harvest boost (x2) if active in the server
            from database_manager import db_manager
            from datetime import datetime
            try:
                guild_id = interaction.guild.id if interaction.guild else None
                if guild_id:
                    result = await db_manager.fetchone(
                        "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                        (guild_id,)
                    )
                    if result and result[0]:
                        buff_until = datetime.fromisoformat(result[0])
                        if datetime.now() < buff_until:
                            # Only apply buff to positive earnings, not penalties
                            if total_money > 0:
                                total_money = total_money * 2  # Double the reward
                            logger.info(f"[SELL] Applied harvest boost x2 for guild {guild_id}")
            except:
                pass
            
            from database_manager import sell_items_atomic
            
            # Use ATOMIC TRANSACTION via sell_items_atomic
            success, message = await sell_items_atomic(self.user_id, self.caught_items, total_money)
            
            if not success:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                self.sold = False
                return
            
            # Log success
            logger.info(f"[SELL_TRANSACTION] COMMITTED - user_id={self.user_id} amount=+{total_money}")

            
            if self.user_id in self.cog.caught_items:
                del self.cog.caught_items[self.user_id]
            
            fish_summary = "\n".join([f"  • {apply_display_glitch(ALL_FISH[k]['name'])} x{v}" for k, v in self.caught_items.items() if k not in LEGENDARY_FISH_KEYS])
            embed = discord.Embed(
                title=f"**{interaction.user.name}** đã bán {sum(v for k, v in self.caught_items.items() if k not in LEGENDARY_FISH_KEYS)} con cá",
                description=f"\n{fish_summary}\n**Nhận: {total_money} Hạt**{keo_ly_message}",
                color=discord.Color.green()
            )
            
            # Disable all buttons to prevent further interactions
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            
            await interaction.followup.send(embed=embed, ephemeral=False, view=self)
            
            fish_count = sum(self.caught_items.values())
            logger.info(f"[SELL] {interaction.user.name} (user_id={self.user_id}) seed_change=+{total_money} fish_count={fish_count} fish_types={len(self.caught_items)}")
        
    
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

    # ==================== BLACK MARKET MECHANIC ====================
    
    async def sell_black_market(self, interaction: discord.Interaction):
        """Executes the Black Market sell action.

        Mechanic: 50% chance to triple the earnings (x3). 50% chance to lose all fish AND pay a fine.
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        if self.sold:
            await interaction.response.send_message("❌ Cá này đã bán rồi!", ephemeral=True)
            return
        
        self.sold = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        
        # 50/50 success
        success = random.random() < 0.5
        
        if success:
            # Success: x3 money
            total_money = self.base_total * 3
            try:
                from database_manager import db_manager
                
                # Prepare batch operations
                operations = []
                
                # Remove fish items
                for fish_key, quantity in self.caught_items.items():
                    operations.append((
                        "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                        (quantity, self.user_id, fish_key)
                    ))
                
                operations.append((
                    "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                    (self.user_id,)
                ))
                
                # Add seeds (x3)
                operations.append((
                    "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                    (total_money, self.user_id)
                ))
                
                # Execute transaction
                await db_manager.batch_modify(operations)
                
                # Clear caches
                db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
                db_manager.clear_cache_by_prefix(f"balance_{self.user_id}")
                db_manager.clear_cache_by_prefix("leaderboard")
                
                # Generate item summary
                fish_summary = ", ".join([f"{ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
                if len(fish_summary) > 200: 
                    fish_summary = fish_summary[:197] + "..."
                
                embed = discord.Embed(
                    title="😎 **GIAO DỊCH TRÓT LỌT!**",
                    description=f"🕵️ Dân chơi không sợ mưa rơi!\n\n**Đã bán:** {fish_summary}\n\n💰 Nhận: **{total_money} Hạt** (x3 giá gốc)\n\n✨ Hôm nay bạn là ông trùm chợ đen!",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                logger.info(f"[BLACK_MARKET_SUCCESS] {interaction.user.name} (user_id={self.user_id}) earned {total_money} seeds (x3)")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi transaction: {e}", ephemeral=True)
                self.sold = False
                logger.error(f"[BLACK_MARKET_ERROR] Transaction failed: {e}")
        
        else:
            # Failure: Lose all fish + 500 seed fine
            try:
                from database_manager import db_manager, get_user_balance
                
                # Prepare batch operations
                operations = []
                
                # Remove fish items without giving money
                for fish_key, quantity in self.caught_items.items():
                    operations.append((
                        "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                        (quantity, self.user_id, fish_key)
                    ))
                
                operations.append((
                    "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                    (self.user_id,)
                ))
                
                # Deduct 500 seeds as fine, but cap to prevent negative balance
                current_balance = await get_user_balance(self.user_id)
                fine = min(500, current_balance)
                
                operations.append((
                    "UPDATE users SET seeds = seeds - ? WHERE user_id = ?",
                    (fine, self.user_id)
                ))
                
                # Execute transaction
                await db_manager.batch_modify(operations)
                
                # Clear caches
                db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
                db_manager.clear_cache_by_prefix(f"balance_{self.user_id}")
                db_manager.clear_cache_by_prefix("leaderboard")
                
                # Generate item summary
                fish_summary = ", ".join([f"{ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
                if len(fish_summary) > 200: 
                    fish_summary = fish_summary[:197] + "..."
                
                embed = discord.Embed(
                    title="🚔 **O E O E!**",
                    description=f"Công an ập tới!\n\n💔 Mất sạch cá: {fish_summary}\n💸 Phạt {fine} Hạt tội buôn lậu\n\n😭 Lần sau không dám chơi xấu nữa!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                logger.info(f"[BLACK_MARKET_FAILURE] {interaction.user.name} (user_id={self.user_id}) lost all fish + {fine} seeds fine")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi transaction: {e}", ephemeral=True)
                self.sold = False
                logger.error(f"[BLACK_MARKET_ERROR] Transaction failed: {e}")
    
    # ==================== HAGGLE MECHANIC ====================
    
    async def start_haggle(self, interaction: discord.Interaction):
        """Initiates the Haggling minigame.

        Transitions the UI to the `HagglingView`.
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Chỉ có người câu cá mới được bán!", ephemeral=True)
            return
        
        if self.sold:
            await interaction.response.send_message("❌ Cá này đã bán rồi!", ephemeral=True)
            return
        
        self.sold = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Create haggle view
        haggle_view = HagglingView(self.cog, self.user_id, self.caught_items, self.base_total, interaction.user.name)
        
        embed = discord.Embed(
            title="🤝 **MẶC CÀ VỚI THƯƠNG LÁI**",
            description=f"**Thương lái:** 'Tôi trả giá {self.base_total} Hạt. Bạn có muốn đòi thêm không?'\n\n💭 Mạo hiểm hay an toàn?",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=haggle_view, ephemeral=False)


class HagglingView(discord.ui.View):
    """A view for the Haggling minigame.

    Allows the user to negotiate the sell price with a risk/reward mechanic.
    """
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
        """Accepts the current offer without further negotiation.

        Safely processes the transaction at the `base_total` price.
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            return
        
        if self.completed:
            return
        
        self.completed = True
        
        try:
            from database_manager import db_manager
            
            # Prepare batch operations
            operations = []
            
            # Remove fish items
            for fish_key, quantity in self.caught_items.items():
                operations.append((
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (quantity, self.user_id, fish_key)
                ))
            
            operations.append((
                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                (self.user_id,)
            ))
            
            # Add seeds
            operations.append((
                "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                (self.base_total, self.user_id)
            ))
            
            # Execute transaction
            await db_manager.batch_modify(operations)
            
            # Clear caches
            db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
            db_manager.clear_cache_by_prefix(f"balance_{self.user_id}")
            db_manager.clear_cache_by_prefix("leaderboard")
            
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
        """Attempts to negotiate a higher price.

        Mechanic:
        - 40% chance of success: Price increases by 30%.
        - 60% chance of failure: Price decreases by 20% (Merchant annoyed).
        """
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            return
        
        if self.completed:
            return
        
        self.completed = True
        success = random.random() < 0.4
        
        if success:
            # Success: +30%
            final_total = int(self.base_total * 1.3)
            message = f"💰 Nhận: **{final_total} Hạt** (+30%)\n\n😎 Thương lái khúc xương! Bạn làm ăn quá khéo!"
            color = discord.Color.gold()
            action = "SUCCESS"
        else:
            # Failure: -20%
            final_total = int(self.base_total * 0.8)
            message = f"💸 Chỉ nhận: **{final_total} Hạt** (-20%)\n\n😤 Thương lái dỗi bỏ đi rồi bán cho người khác với giá rẻ hơn!"
            color = discord.Color.red()
            action = "FAIL"
        
        try:
            from database_manager import db_manager
            
            # Prepare batch operations
            operations = []
            
            # Remove fish items
            for fish_key, quantity in self.caught_items.items():
                operations.append((
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (quantity, self.user_id, fish_key)
                ))
            
            operations.append((
                "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                (self.user_id,)
            ))
            
            # Add seeds
            operations.append((
                "UPDATE users SET seeds = seeds + ? WHERE user_id = ?",
                (final_total, self.user_id)
            ))
            
            # Execute transaction
            await db_manager.batch_modify(operations)
            
            # Clear caches
            db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
            db_manager.clear_cache_by_prefix(f"balance_{self.user_id}")
            db_manager.clear_cache_by_prefix("leaderboard")
            
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

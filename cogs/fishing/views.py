"""UI views for fishing system."""

import discord
from database_manager import remove_item, add_seeds, get_inventory
from .constants import ALL_FISH

class FishSellView(discord.ui.View):
    """View for selling caught fish."""
    def __init__(self, cog, user_id, caught_items, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.caught_items = caught_items
        self.guild_id = guild_id
        self.sold = False  # Flag to prevent double-selling
    
    async def on_timeout(self):
        """Cleanup when view times out (after 5 minutes)"""
        # Remove caught_items cache since user didn't sell
        if self.user_id in self.cog.caught_items:
            try:
                del self.cog.caught_items[self.user_id]
            except:
                pass
    
    @discord.ui.button(label="💰 Bán Cá Vừa Câu", style=discord.ButtonStyle.green)
    async def sell_caught_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            item.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send("⏳ Đang xử lý...", ephemeral=True)
        
        try:
            total_money = 0
            for fish_key, quantity in self.caught_items.items():
                fish_info = ALL_FISH.get(fish_key)
                if fish_info:
                    base_price = fish_info['sell_price']
                    total_money += base_price * quantity
            
            # *** APPLY KECO LỲ BUFF (2x sell price for 10 minutes) ***
            keo_ly_message = ""
            if hasattr(self.cog, 'check_emotional_state') and self.cog.check_emotional_state(self.user_id, "keo_ly"):
                total_money = total_money * 2
                keo_ly_message = " (💅 **Keo Lỳ Buff x2**)"
                print(f"[FISHING] [SELL] {interaction.user.name} applied keo_ly buff x2 multiplier")
            
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
                            total_money = total_money * 2  # Double the reward
                            print(f"[FISHING] [SELL] Applied harvest boost x2 for guild {guild_id}")
            except:
                pass
            
            # Use ATOMIC TRANSACTION to prevent exploits
            import aiosqlite
            from .constants import DB_PATH
            
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("BEGIN TRANSACTION")
                    
                    try:
                        # 1. VERIFY inventory quantities INSIDE transaction
                        for fish_key, quantity in self.caught_items.items():
                            cursor = await db.execute(
                                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                                (self.user_id, fish_key)
                            )
                            row = await cursor.fetchone()
                            actual_qty = row[0] if row else 0
                            
                            if actual_qty < quantity:
                                await db.execute("ROLLBACK")
                                self.sold = False  # Reset flag on insufficient inventory
                                await interaction.followup.send(
                                    f"❌ **Khôn vậy má!** Không đủ `{ALL_FISH[fish_key]['name']}` để bán.\n"
                                    f"Cần: {quantity}, Có: {actual_qty}\n"
                                    f"(Đã bán qua `/banca` rồi?)",
                                    ephemeral=True
                                )
                                return
                        
                        # 2. Remove all fish items (safe now - quantities verified)
                        for fish_key, quantity in self.caught_items.items():
                            await db.execute(
                                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?",
                                (quantity, self.user_id, fish_key)
                            )
                        
                        # 3. Delete items with quantity <= 0
                        await db.execute(
                            "DELETE FROM inventory WHERE user_id = ? AND quantity <= 0",
                            (self.user_id,)
                        )
                        
                        # 4. Add seeds to user
                        await db.execute(
                            "UPDATE economy_users SET seeds = seeds + ? WHERE user_id = ?",
                            (total_money, self.user_id)
                        )
                        
                        # Commit transaction
                        await db.commit()
                        
                        # CRITICAL: Invalidate inventory cache after successful transaction
                        from database_manager import db_manager
                        db_manager.clear_cache_by_prefix(f"inventory_{self.user_id}")
                        
                    except Exception as e:
                        await db.execute("ROLLBACK")
                        self.sold = False  # Reset flag on error
                        raise
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi transaction: {e}", ephemeral=True)
                self.sold = False  # Reset flag on error
                return
            
            if self.user_id in self.cog.caught_items:
                del self.cog.caught_items[self.user_id]
            
            fish_summary = "\n".join([f"  • {ALL_FISH[k]['name']} x{v}" for k, v in self.caught_items.items()])
            embed = discord.Embed(
                title=f"**{interaction.user.name}** đã bán {sum(self.caught_items.values())} con cá",
                description=f"\n{fish_summary}\n**Nhận: {total_money} Hạt**{keo_ly_message}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            
            fish_count = sum(self.caught_items.values())
            print(f"[FISHING] [SELL] {interaction.user.name} (user_id={self.user_id}) seed_change=+{total_money} fish_count={fish_count} fish_types={len(self.caught_items)}")
        
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

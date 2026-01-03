"""Consumable items usage system."""

from discord import app_commands
from discord.ext import commands
import discord
import random
import random
from database_manager import db_manager, get_user_balance
from .fishing.utils.consumables import CONSUMABLE_ITEMS, get_consumable_info, is_consumable
from .fishing.mechanics.legendary_quest_helper import is_legendary_caught

# Symbols for memory game
MEMORY_SYMBOLS = ["🌕", "🌟", "☄️", "🌍", "⭐", "🌌", "🌙", "💫"]

class MemoryGameView(discord.ui.View):
    """Mini-game for summoning Cá Ngân Hà"""
    def __init__(self, user_id, sequence, buttons, bot, channel, user):
        super().__init__(timeout=10)
        self.user_id = user_id
        self.sequence = sequence
        self.buttons = buttons  # dict label: symbol
        self.bot = bot
        self.channel = channel
        self.user = user
        self.clicked = []
        
        for label, symbol in buttons.items():
            btn = discord.ui.Button(label=f"{label}: {symbol}", style=discord.ButtonStyle.primary)
            btn.callback = self.make_callback(label)
            self.add_item(btn)
    
    def make_callback(self, label):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Đây không phải trò chơi của bạn!", ephemeral=True)
                return
            
            symbol = self.buttons[label]
            self.clicked.append(symbol)
            
            if len(self.clicked) == len(self.sequence):
                # Check result
                if self.clicked == self.sequence:
                    # Win
                    from .fishing.mechanics.legendary_quest_helper import set_has_tinh_cau, set_tinh_cau_cooldown
                    # Item already deducted at start
                    
                    # Set buff for guaranteed catch
                    self.bot.get_cog("FishingCog").guaranteed_catch_users[self.user_id] = True
                    print(f"[CONSUMABLE] Tinh cau success for {self.user_id}")
                    username = self.user.display_name if self.user else "Unknown"
                    embed = discord.Embed(
                        title=f"🎉 {username} - TRIỆU HỒI THÀNH CÔNG!",
                        description="Bạn đã nối đúng thứ tự các vì sao!\n\n🌟 **Cá Ngân Hà** sẽ xuất hiện ở lần câu tiếp theo!",
                        color=discord.Color.green()
                    )
                else:
                    # Lose
                    from .fishing.mechanics.legendary_quest_helper import set_has_tinh_cau, set_tinh_cau_cooldown
                    # Item already deducted at start
                    await set_tinh_cau_cooldown(self.user_id)  # Set cooldown
                    print(f"[CONSUMABLE] Tinh cau failure for {self.user_id}")
                    username = self.user.display_name if self.user else "Unknown"
                    embed = discord.Embed(
                        title=f"❌ {username} - TRIỆU HỒI THẤT BẠI",
                        description="Thứ tự sai! Tinh Cầu Không Gian đã tiêu tan vào hư không.\n\n⏰ **Cooldown 10 phút** trước khi có thể chế tạo lại.",
                        color=discord.Color.red()
                    )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                # Update progress
                progress = " ➡️ ".join(self.clicked + ["?"] * (len(self.sequence) - len(self.clicked)))
                embed = interaction.message.embeds[0]
                embed.description = f"Hãy nối các vì sao theo thứ tự đúng trong 10 giây!\n\n**Mẫu:** {' ➡️ '.join(self.sequence)}\n\n**Tiến độ:** {progress}"
                await interaction.response.edit_message(embed=embed)
        
        return callback
    
    async def on_timeout(self):
        if len(self.clicked) < len(self.sequence):
            from .fishing.mechanics.legendary_quest_helper import set_has_tinh_cau, set_tinh_cau_cooldown
            # Item already deducted
            await set_tinh_cau_cooldown(self.user_id)  # Set cooldown
            print(f"[CONSUMABLE] Tinh cau timeout failure for {self.user_id}")
            username = self.user.display_name if self.user else "Unknown"
            embed = discord.Embed(
                title=f"⏰ {username} - HẾT THỜI GIAN",
                description="Bạn không hoàn thành kịp! Tinh Cầu Không Gian đã tiêu tan.\n\n⏰ **Cooldown 10 phút** trước khi có thể chế tạo lại.",
                color=discord.Color.red()
            )
            try:
                await self.channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

class PhoenixEggView(discord.ui.View):
    """Ấp Trứng Phượng Hoàng (Push Your Luck)"""
    
    def __init__(self, user_id, bot, channel, user):
        super().__init__(timeout=180)  # 3 minutes
        self.user_id = user_id
        self.bot = bot
        self.channel = channel
        self.user = user
        self.energy = 0
        
        # Buttons
        light = discord.ui.Button(label="🔥 Nạp Nhẹ (5-15%)", style=discord.ButtonStyle.primary)
        light.callback = self.add_light
        self.add_item(light)
        
        heavy = discord.ui.Button(label="💥 Nạp Mạnh (15-30%)", style=discord.ButtonStyle.danger)
        heavy.callback = self.add_heavy
        self.add_item(heavy)
        
        activate = discord.ui.Button(label="✨ Kích Hoạt", style=discord.ButtonStyle.success)
        activate.callback = self.activate
        self.add_item(activate)
    
    def _make_embed(self, last_action=""):
        # Progress bar
        filled = self.energy // 10
        empty = 10 - filled
        if self.energy < 50:
            bar = "🟦" * filled + "⬜" * empty
        elif self.energy < 80:
            bar = "🟨" * filled + "⬜" * empty
        else:
            bar = "🟥" * filled + "⬜" * empty
        
        # Status
        if self.energy < 50:
            status = "✅ An toàn"
            color = discord.Color.blue()
        elif self.energy < 80:
            status = "⚠️ Cẩn thận"
            color = discord.Color.gold()
        elif self.energy < 95:
            status = "🎯 VÙ MỤC TIÊU"
            color = discord.Color.orange()
        else:
            status = "🔥 NGUY HIỂM!"
            color = discord.Color.red()
        
        desc = f"[{bar}] **{self.energy}%**\n\n{status}"
        if last_action:
            desc += f"\n\n💫 {last_action}"
        
        embed = discord.Embed(
            title=f"🥚 {self.user.display_name} - ẤP TRỨNG PHƯỢNG HOÀNG",
            description=desc,
            color=color
        )
        embed.add_field(
            name="📖 Hướng Dẫn",
            value="🔥 Nạp Nhẹ: +5-15% an toàn\n"
                  "💥 Nạp Mạnh: +15-30% mạo hiểm\n"
                  "✨ Kích Hoạt: Nở trứng (80-100%)\n"
                  "• Bust >100% ❌ | Perfect 100% 👑",
            inline=False
        )
        return embed
    
    async def add_light(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        
        gain = random.randint(5, 15)
        self.energy += gain
        
        if self.energy > 100:
            self.stop()
            return await self._bust(interaction)
        
        embed = self._make_embed(f"Nạp nhẹ: +{gain}%")
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def add_heavy(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        
        gain = random.randint(15, 30)
        self.energy += gain
        
        if self.energy > 100:
            self.stop()
            return await self._bust(interaction)
        
        embed = self._make_embed(f"Nạp mạnh: +{gain}%")
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def activate(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải của bạn!", ephemeral=True)
        
        self.stop()
        
        if self.energy < 80:
            await self._fail_low(interaction)
        elif self.energy == 100:
            await self._perfect(interaction)
        else:
            await self._success(interaction)
    
    async def on_timeout(self):
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_last_play
        
        try:
            # Item already deducted
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title=f"⏰ HẾT THỜI GIAN",
                description=f"Trứng đã nguội lạnh.\n**Năng lượng: {self.energy}%**",
                color=discord.Color.red()
            )
            await self.channel.send(embed=embed)
            logger.info(f"[PHOENIX] User {self.user_id} timed out at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Timeout error: {e}")
    
    async def _bust(self, interaction):
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_last_play
        
        try:
            # Item already deducted
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="💥 NỔ TUNG!",
                description=f"**{self.energy}%** - Quá tải!\n\nTrứng không chịu nổi áp lực.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} busted at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Bust error: {e}")
    
    async def _fail_low(self, interaction):
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_last_play
        
        try:
            # Item already deducted
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="❌ QUÁ YẾU",
                description=f"**{self.energy}%** - Cần tối thiểu 80%!\n\nTrứng vỡ.",
                color=discord.Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} too low at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Fail low error: {e}")
    
    async def _success(self, interaction):
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_buff, set_phoenix_last_play
        
        try:
            # [CACHE] Use bot.inventory.modify
            await self.bot.inventory.modify(self.user_id, "long_vu_lua", -1)
            await set_phoenix_buff(self.user_id, self.energy)  # Store energy value
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="🎉 TRỨNG NỞ THÀNH CÔNG!",
                description=f"**{self.energy}%** - Hoàn hảo!\n\n🔥 **Cá Phượng Hoàng** sẽ xuất hiện lần câu tiếp theo!",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} success at {self.energy}%")
        except Exception as e:
            logger.error(f"[PHOENIX] Success error: {e}")
    
    async def _perfect(self, interaction):
        from .fishing.mechanics.legendary_quest_helper import set_phoenix_buff, set_phoenix_last_play
        
        try:
            # Item already deducted
            await set_phoenix_buff(self.user_id, self.energy)  # Store energy value
            await set_phoenix_last_play(self.user_id)
            
            embed = discord.Embed(
                title="👑 PERFECT! PHƯỢNG HOÀNG CHÚA!",
                description="**100%** - HOÀN HẢO TUYỆT ĐỐI!\n\n"
                            "💎 Ánh sáng chói lọi!\n"
                            "✨ Guaranteed Legendary + Bonus!",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"[PHOENIX] {self.user_id} PERFECT 100%!")
        except Exception as e:
            logger.error(f"[PHOENIX] Perfect error: {e}")

class ConsumableCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Lưu các item đang được sử dụng để boost lần câu tiếp theo
        self.active_boosts = {}  # {user_id: {"item_key": str, "effect_type": str, "effect_value": float}}
        # Lưu các user đã phát hiện tín hiệu 52Hz
        self.detected_52hz = {}  # {user_id: True} - trigger 100% whale encounter

    # ==================== COMMANDS ====================

    @app_commands.command(name="sudung", description="Sử dụng vật phẩm tiêu thụ để có buff khi câu cá")
    @app_commands.describe(item="Item key: nuoc_tang_luc, gang_tay_xin, thao_tac_tinh_vi, hoặc tinh_yeu_ca (để trống xem danh sách)")
    async def use_consumable_slash(self, interaction: discord.Interaction, item: str = None):
        """Use a consumable item - slash version"""
        await interaction.response.defer(ephemeral=False)
        await self._use_consumable(interaction, item, is_slash=True)

    @commands.command(name="sudung", description="Sử dụng vật phẩm tiêu thụ - Dùng !sudung [item_key]")
    async def use_consumable_prefix(self, ctx, item: str = None):
        """Use a consumable item - prefix version"""
        await self._use_consumable(ctx, item, is_slash=False)

    async def _use_consumable(self, ctx_or_interaction, item_key: str, is_slash: bool):
        """Core logic to use a consumable item"""
        
        # Show help if no item provided
        if item_key is None:
            embed = discord.Embed(
                title="📖 Cách Sử Dụng Vật Phẩm Tiêu Thụ",
                description="Dùng `/sudung [item_key]` để sử dụng vật phẩm",
                color=discord.Color.blurple()
            )
            
            for key, item_info in CONSUMABLE_ITEMS.items():
                value = f"**{item_info['name']}**\n{item_info['description']}\n\n**Lệnh:** `/sudung {key}` hoặc `!sudung {key}`"
                embed.add_field(name=f"🎫 {key}", value=value, inline=False)
            
            embed.set_footer(text="Mua tại cửa hàng với /mua (nếu cần)")
            
            if is_slash:
                await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        user_id = ctx_or_interaction.user.id if is_slash else ctx_or_interaction.author.id
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        print(f"[CONSUMABLE] User {user_id} attempting to use {item_key}")
        
        # Validate item exists
        if not is_consumable(item_key):
            available = ", ".join([f"`{k}`" for k in CONSUMABLE_ITEMS.keys()])
            error_msg = f"❌ Không tìm thấy vật phẩm `{item_key}`!\n\n**Vật phẩm có sẵn:**\n{available}"
            
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
            return
        
        item_info = get_consumable_info(item_key)
        
        # =================================================================================================
        # CORE TRANSACTION LOGIC (ACID)
        # We deduct item FIRST.
        # =================================================================================================
        
        db_item_deducted = False
        
        # SPECIAL CASE: Tinh Cau is a QUEST FLAG, not an Inventory Item (Legacy)
        if item_key == "tinh_cau":
             from .fishing.mechanics.legendary_quest_helper import has_tinh_cau, set_has_tinh_cau
             if await has_tinh_cau(user_id):
                 await set_has_tinh_cau(user_id, False) # Consume it
                 db_item_deducted = True
             else:
                 db_item_deducted = False
        else:
            # Standard Inventory Item
            try:
                async with db_manager.transaction() as conn:
                    # Deduct 1 item where count >= 1
                    result = await conn.execute(
                        "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ? AND quantity >= ?",
                        (1, user_id, item_key, 1)
                    )
                    
                    # SQLite execute returns Cursor, rowcount property might be needed or check result
                    # aiosqlite/sqlite3 cursor.execute doesn't return string "UPDATE 0"
                    # We need to check rowcount. db_manager.execute wrapper might differ.
                    # Assuming db_manager.execute returns the cursor or rowcount.
                    # If db_manager structure is standard aiosqlite wrapper:
                    # It likely returns what the driver returns.
                    # Let's assume rowcount check is needed. 
                    # Note: Previous code checked result == "UPDATE 0" which suggests asyncpg behavior.
                    # For sqlite, we usually check cursor.rowcount.
                    
                    # However, db_manager.execute might just return the result of await cursor.execute().
                    
                    if result and hasattr(result, 'rowcount'):
                         if result.rowcount == 0:
                             db_item_deducted = False
                         else:
                             db_item_deducted = True
                    else:
                        # Fallback if wrapper differs (e.g. returns None on success?)
                        # Better strategy: Check if inventory changed?
                        # Or, Fetch first?
                        # Let's use the fetch-then-update approach for safety if we are unsure about return type wrapper
                        # But we are in a transaction.
                        pass 
                    
                    # RE-READ STRATEGY:
                    # Since we are converting from asyncpg, let's rely on fetch-check-update pattern inside transaction which is safe.
                    
                    check = await conn.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_key))
                    row = await check.fetchone()
                    if not row or row[0] < 1:
                        db_item_deducted = False
                    else:
                        await conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?", (user_id, item_key))
                        await conn.execute("DELETE FROM inventory WHERE user_id = ? AND quantity <= 0", (user_id,))
                        db_item_deducted = True

            except Exception as e:
                logger.error(f"[CONSUMABLE] Transaction check failed for {item_key}: {e}")
                db_item_deducted = False

        if not db_item_deducted:
            if item_key == "tinh_cau":
                 error_msg = "❌ Bạn không có **Tinh Cầu Không Gian** (hoặc đã sử dụng)!"
            else:
                 error_msg = f"❌ Bạn không đủ **{item_info['name']}** để sử dụng!"
                 
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return

        # If we got here, ITEM IS CONSUMED.
        # Now we execute the effect.
        
        # 3. Special Logic Routing (Consumed already)
        if item_key == "tinh_cau":
            # ... Game Logic ...
            sequence = random.sample(MEMORY_SYMBOLS, 4)
            shuffled = sequence.copy()
            while shuffled == sequence: # Ensure shuffled
                random.shuffle(shuffled)
                
            button_labels = ["A", "B", "C", "D"]
            buttons = {button_labels[i]: shuffled[i] for i in range(4)}
            
            embed = discord.Embed(
                title=f"🌌 {user.display_name} - TRIỆU HỒI CÁ NGÂN HÀ",
                description=f"Hãy nối các vì sao theo thứ tự đúng trong 10 giây! (Đã tiêu thụ 1 Tinh Cầu)\n\n**Mẫu:** {' ➡️ '.join(sequence)}\n\n**Tiến độ:** ? ➡️ ? ➡️ ? ➡️ ?",
                color=discord.Color.blue()
            )
            
            view = MemoryGameView(user_id, sequence, buttons, self.bot, ctx_or_interaction.channel if not is_slash else ctx_or_interaction.channel, user)
            
            if is_slash:
                await ctx_or_interaction.followup.send(embed=embed, view=view)
            else:
                await ctx.send(embed=embed, view=view)
            return

        elif item_key == "long_vu_lua":
             # ... Phoenix Game ...
             # Note: Original code checked long_vu_lua again via inventory.get.
             # We just consumed it. So we proceed.
             print(f"[CONSUMABLE] Starting long_vu_lua game for {user_id}")
             
             view = PhoenixEggView(user_id, self.bot, ctx_or_interaction.channel if not is_slash else ctx_or_interaction.channel, user)
             embed = view._make_embed()
             
             if is_slash:
                 await ctx_or_interaction.followup.send(embed=embed, view=view)
             else:
                 await ctx.send(embed=embed, view=view)
             return

        elif item_key == "ban_do_ham_am":
             # Activate Dark Map
             fishing_cog = self.bot.get_cog("FishingCog")
             if not fishing_cog:
                 await ctx.send("❌ Fishing Module unavailable!")
                 return
                 
             fishing_cog.dark_map_active[user_id] = True
             fishing_cog.dark_map_casts[user_id] = 10 # 10 casts
             fishing_cog.dark_map_cast_count[user_id] = 0
             
             print(f"[CONSUMABLE] ban_do_ham_am activated for {user_id}")
             
             embed = discord.Embed(
                 title="🗺️ BẢN ĐỒ HẮC ÁM ĐÃ MỞ!",
                 description="Bạn đã bước vào vùng biển tối tăm...\n\n🦑 **Cthulhu Non** đang rình rập!\n⚡ **10 lần câu tiếp theo** sẽ có cơ hội gặp hắn.\n\n⚠️ *Cẩn thận: Map sẽ biến mất sau 10 lần câu.*",
                 color=discord.Color.dark_grey()
             )
             
             if is_slash:
                 await ctx_or_interaction.followup.send(embed=embed)
             else:
                 await ctx.send(embed=embed)
             return

        # 4. Standard Effect (Boost)
        # Store active boost for this user
        self.active_boosts[user_id] = {
            "item_key": item_key,
            "effect_type": item_info["effect_type"],
            "effect_value": item_info["effect_value"],
        }
        
        print(f"[CONSUMABLE] Applied effect for {item_key} to {user_id}")
        
        embed = discord.Embed(
            title=f"✅ Đã Sử Dụng {item_info['name']}",
            description="Vật phẩm đã được kích hoạt thành công!",
            color=discord.Color.green()
        )
        embed.add_field(name="📖 Mô tả", value=item_info["description"], inline=False)
        embed.add_field(name="📦 Tình trạng", value="Đã sử dụng 1 cái", inline=False) # We don't know exact remaining without query, safe generic msg
        embed.add_field(
            name="⏱️ Thời gian hiệu lực",
            value="Có hiệu lực cho lần câu cá huyền thoại tiếp theo",
            inline=False
        )
        
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)



    # ==================== ADMIN COMMANDS ====================

    @commands.command(name="themconsumable", description="Thêm consumable item vào inventory (Admin Only)")
    @commands.has_permissions(administrator=True)
    async def add_consumable_prefix(self, ctx, item_key: str, quantity: int = 1, user: discord.User = None):
        """Add consumable item to user's inventory"""
        target_user = user or ctx.author
        
        if not is_consumable(item_key):
            available = ", ".join([f"`{k}`" for k in CONSUMABLE_ITEMS.keys()])
            await ctx.send(f"❌ Không tìm thấy item `{item_key}`!\n\n**Items có sẵn:**\n{available}")
            return
        
        item_info = get_consumable_info(item_key)
        # [CACHE] Use bot.inventory.modify
        await self.bot.inventory.modify(target_user.id, item_key, quantity)
        
        embed = discord.Embed(
            title="✅ Đã Thêm Consumable Item",
            description=f"User: {target_user.mention}\nItem: {item_info['name']} x{quantity}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    def get_active_boost(self, user_id: int) -> dict | None:
        """Get active boost for user (và xóa sau khi dùng)"""
        return self.active_boosts.pop(user_id, None)

    def peek_active_boost(self, user_id: int) -> dict | None:
        """Peek active boost for user without consuming it"""
        return self.active_boosts.get(user_id)

    def has_detected_52hz(self, user_id: int) -> bool:
        """Check if user has detected 52Hz signal"""
        return self.detected_52hz.get(user_id, False)

    def clear_52hz_signal(self, user_id: int):
        """Clear the 52Hz detection flag after spawning whale"""
        self.detected_52hz.pop(user_id, None)

async def setup(bot):
    await bot.add_cog(ConsumableCog(bot))

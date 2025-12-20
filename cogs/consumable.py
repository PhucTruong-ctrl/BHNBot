"""Consumable items usage system."""

from discord import app_commands
from discord.ext import commands
import discord
import random
import random
from database_manager import get_inventory, remove_item, add_item
from .fishing.consumables import CONSUMABLE_ITEMS, get_consumable_info, is_consumable
from .fishing.legendary_quest_helper import is_legendary_caught

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
                    from .fishing.legendary_quest_helper import set_has_tinh_cau, set_tinh_cau_cooldown
                    await set_has_tinh_cau(self.user_id, False)  # Mất tinh cầu
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
                    from .fishing.legendary_quest_helper import set_has_tinh_cau, set_tinh_cau_cooldown
                    await set_has_tinh_cau(self.user_id, False)  # Mất tinh cầu
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
            from .fishing.legendary_quest_helper import set_has_tinh_cau, set_tinh_cau_cooldown
            await set_has_tinh_cau(self.user_id, False)  # Mất tinh cầu
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
            except:
                pass

class KeepFireView(discord.ui.View):
    """Mini-game for Cá Phượng Hoàng - Giữ Lửa"""
    def __init__(self, user_id, bot, channel, user):
        super().__init__(timeout=5)  # 5 giây mỗi round
        self.user_id = user_id
        self.bot = bot
        self.channel = channel
        self.user = user
        self.temperature = 50  # Bắt đầu từ 50 độ
        self.round = 1
        self.max_rounds = 3
        self.blows = 0  # Số lần thổi lửa trong round này
        
        # Thêm nút thổi lửa
        blow_btn = discord.ui.Button(label="🔥 Thổi Lửa (+10°)", style=discord.ButtonStyle.primary)
        blow_btn.callback = self.blow_fire
        self.add_item(blow_btn)
    
    def get_temperature_display(self):
        """Tạo thanh nhiệt độ"""
        temp = self.temperature
        if temp < 70:
            status = "❄️ Quá lạnh! Lửa sắp tắt."
            color = "🥶"
        elif temp > 90:
            status = "💥 Quá nóng! Lông vũ cháy thành tro."
            color = "🔥"
        else:
            status = "✅ Nhiệt độ hoàn hảo!"
            color = "🌟"
        
        # Thanh nhiệt độ đơn giản
        bar = ""
        for i in range(0, 101, 10):
            if temp >= i:
                if i < 70:
                    bar += "❄️"
                elif i <= 90:
                    bar += "✅"
                else:
                    bar += "💥"
            else:
                bar += "⬜"
        
        return f"{bar}\n**Nhiệt độ hiện tại: {temp}°** - {status}"
    
    async def blow_fire(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Đây không phải trò chơi của bạn!", ephemeral=True)
            return
        
        self.temperature += 10
        self.blows += 1
        
        embed = interaction.message.embeds[0]
        embed.description = f"**Hiệp {self.round}/{self.max_rounds}**\n\n{self.get_temperature_display()}\n\nBạn đã thổi **{self.blows}** lần trong hiệp này."
        await interaction.response.edit_message(embed=embed)
    
    async def on_timeout(self):
        # Kết thúc round: trừ 20 độ
        self.temperature -= 20
        self.temperature = max(0, self.temperature)
        
        success = 70 <= self.temperature <= 90
        
        if success and self.round < self.max_rounds:
            # Qua round tiếp theo
            self.round += 1
            self.blows = 0
            embed = discord.Embed(
                title="🔥 NGHI LỄ GIỮ LỬA - HIỆP TIẾP THEO",
                description=f"**Hiệp {self.round}/{self.max_rounds}**\n\n{self.get_temperature_display()}\n\nGió thổi mạnh! Nhiệt độ giảm 20°.\nBắt đầu hiệp mới...",
                color=discord.Color.orange()
            )
            try:
                msg = await self.channel.send(embed=embed, view=KeepFireView(self.user_id, self.bot, self.channel))
                # Reset timeout cho round mới
                self.stop()
            except:
                pass
        elif success and self.round == self.max_rounds:
            # Thắng
            from database_manager import remove_item
            from .fishing.legendary_quest_helper import set_phoenix_buff, set_phoenix_last_play
            await remove_item(self.user_id, "long_vu_lua", 1)  # Trừ 1 lông vũ từ inventory
            await set_phoenix_buff(self.user_id, True)  # Kích hoạt buff
            await set_phoenix_last_play(self.user_id)  # Set thời gian chơi
            print(f"[CONSUMABLE] Long vu lua success for {self.user_id}")
            username = self.user.display_name if self.user else "Unknown"
            embed = discord.Embed(
                title=f"🎉 {username} - THÀNH CÔNG! PHƯỢNG HOÀNG TÁI SINH",
                description="Bạn đã giữ được ngọn lửa hoàn hảo!\n\n🔥 Lông Vũ Lửa hóa thành Phượng Hoàng!\n\n🌟 **Cá Phượng Hoàng** sẽ xuất hiện ở lần câu tiếp theo!",
                color=discord.Color.gold()
            )
            try:
                await self.channel.send(embed=embed)
            except:
                pass
        else:
            # Thất bại
            from database_manager import remove_item
            from .fishing.legendary_quest_helper import set_phoenix_last_play
            await remove_item(self.user_id, "long_vu_lua", 1)  # Trừ 1 lông vũ từ inventory
            await set_phoenix_last_play(self.user_id)  # Set thời gian chơi
            print(f"[CONSUMABLE] Long vu lua failure for {self.user_id}")
            username = self.user.display_name if self.user else "Unknown"
            embed = discord.Embed(
                title=f"❌ {username} - THẤT BẠI! LỬA ĐÃ TẮT",
                description=f"Lông Vũ Lửa đã tan biến thành tro bụi.\n\nNhiệt độ cuối: {self.temperature}°\n\n💡 Hãy thử lại với chiếc lông vũ khác!",
                color=discord.Color.red()
            )
            try:
                await self.channel.send(embed=embed)
            except:
                pass

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
        await interaction.response.defer(ephemeral=True)
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
        
        # Check inventory
        inventory = await get_inventory(user_id)
        quantity = inventory.get(item_key, 0)
        
        if quantity < 1:
            error_msg = f"❌ Bạn không có **{item_info['name']}**!"
            print(f"[CONSUMABLE] Quantity check failed for {item_key} - quantity: {quantity}")
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
            return
        
        print(f"[CONSUMABLE] Quantity check passed for {item_key} - quantity: {quantity}")
        
        # Check if legendary fish already caught
        legendary_checks = {
            "tinh_cau": "ca_ngan_ha",
            "long_vu_lua": "ca_phuong_hoang",
            "ban_do_ham_am": "cthulhu_con",
            "may_do_song": "ca_voi_52hz"
        }
        legendary_messages = {
            "ca_ngan_ha": "🌌 **KẾT NỐI VÔ HIỆU!**\n\n\"Tinh Cầu Không Gian lóe sáng rồi vụt tắt. Các vì sao thì thầm rằng định mệnh đã an bài. Sinh vật huyền bí từ dải ngân hà đang bơi lội trong bể cá của bạn rồi, cánh cổng không gian sẽ không mở ra lần thứ hai.\"",
            "ca_phuong_hoang": "🔥 **NGỌN LỬA ĐÃ AN BÀI!**\n\n\"Chiếc lông vũ chỉ tỏa ra hơi ấm nhẹ rồi nguội lạnh. Loài chim lửa bất tử chỉ tái sinh một lần duy nhất với người xứng đáng. Bạn đã sở hữu sức mạnh của nó, không cần phải thực hiện nghi lễ thêm lần nào nữa.\"",
            "cthulhu_con": "🌑 **TIẾNG GỌI TỪ VỰC THẲM**\n\n\"Bạn nhìn vào bản đồ nhưng các ký tự bỗng nhiên nhảy múa và biến mất... Cổ Thần đã thức giấc và đáp lại lời kêu gọi của bạn từ trước. Đừng cố gắng nhìn sâu vào bóng tối nữa, hoặc bạn sẽ phát điên đấy!\"",
            "ca_voi_52hz": "📡 **TẦN SỐ ĐÃ ĐƯỢC KẾT NỐI**\n\n\"Máy dò sóng chỉ phát ra những tiếng rè tĩnh lặng... Tần số 52Hz cô đơn nhất đại dương không còn lạc lõng nữa, vì nó đã tìm thấy bạn. Không còn tín hiệu nào khác để dò tìm.\""
        }
        if item_key in legendary_checks:
            fish_key = legendary_checks[item_key]
            if await is_legendary_caught(user_id, fish_key):
                error_msg = legendary_messages[fish_key]
                print(f"[CONSUMABLE] Legendary check failed for {item_key} - {fish_key} already caught")
                if is_slash:
                    await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(error_msg)
                return
        
        print(f"[CONSUMABLE] Legendary check passed for {item_key}")
        
        # Special handling for tinh_cau
        if item_key == "tinh_cau":
            from .fishing.legendary_quest_helper import has_tinh_cau, get_tinh_cau_cooldown
            import datetime
            
            # Check if user has tinh cau
            if not await has_tinh_cau(user_id):
                error_msg = "❌ Bạn không có **Tinh Cầu Không Gian**!"
                print(f"[CONSUMABLE] Tinh cau check failed - not crafted")
                if is_slash:
                    await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(error_msg)
                return
            
            # Check cooldown
            cooldown_time = await get_tinh_cau_cooldown(user_id)
            if cooldown_time:
                # Check if 10 minutes have passed
                # Check if 10 minutes have passed
                cooldown_datetime = datetime.datetime.fromisoformat(cooldown_time)
                now = datetime.datetime.now()
                if (now - cooldown_datetime).total_seconds() < 600:  # 10 minutes
                    remaining = 600 - (now - cooldown_datetime).total_seconds()
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    error_msg = f"⏰ **Cooldown đang hoạt động!** Còn {minutes} phút {seconds} giây."
                    if is_slash:
                        await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx_or_interaction.send(error_msg)
                    return
            
            # Start memory game
            sequence = random.sample(MEMORY_SYMBOLS, 4)
            shuffled = sequence.copy()
            random.shuffle(shuffled)
            button_labels = ["A", "B", "C", "D"]
            buttons = {button_labels[i]: shuffled[i] for i in range(4)}
            
            embed = discord.Embed(
                title=f"🌌 {user.display_name} - TRIỆU HỒI CÁ NGÂN HÀ",
                description=f"Hãy nối các vì sao theo thứ tự đúng trong 10 giây!\n\n**Mẫu:** {' ➡️ '.join(sequence)}\n\n**Tiến độ:** ? ➡️ ? ➡️ ? ➡️ ?",
                color=discord.Color.blue()
            )
            
            view = MemoryGameView(user_id, sequence, buttons, self.bot, ctx_or_interaction.channel if not is_slash else ctx_or_interaction.channel, user)
            
            if is_slash:
                await ctx_or_interaction.followup.send(embed=embed, view=view, ephemeral=False)
            else:
                await ctx_or_interaction.send(embed=embed, view=view)
            return
        
        # Special handling for long_vu_lua
        if item_key == "long_vu_lua":
            # Check if user has long vu lua in inventory
            inventory = await get_inventory(user_id)
            quantity = inventory.get("long_vu_lua", 0)
            if quantity < 1:
                error_msg = "❌ Bạn không có **Lông Vũ Lửa**!"
                print(f"[CONSUMABLE] Long vu lua check failed - quantity: {quantity}")
                if is_slash:
                    await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await ctx_or_interaction.send(error_msg)
                return
            
            print(f"[CONSUMABLE] Starting long_vu_lua game for {user_id}")
            
            # Start keep fire game
            embed = discord.Embed(
                title=f"🔥 {user.display_name} - NGHI LỄ GIỮ LỬA",
                description="**Hiệp 1/3**\n\n[❄️❄️❄️❄️❄️✅✅✅✅✅💥💥]\n**Nhiệt độ hiện tại: 50°** - ❄️ Quá lạnh! Lửa sắp tắt.\n\nBạn đã thổi **0** lần trong hiệp này.\n\n⏰ **5 giây** để cân bằng nhiệt độ!",
                color=discord.Color.orange()
            )
            
            view = KeepFireView(user_id, self.bot, ctx_or_interaction.channel if not is_slash else ctx_or_interaction.channel, user)
            
            if is_slash:
                await ctx_or_interaction.followup.send(embed=embed, view=view, ephemeral=False)
            else:
                await ctx_or_interaction.send(embed=embed, view=view)
            return
        
        # Use the item - remove from inventory (for regular items)
        success = await remove_item(user_id, item_key, 1)
        if not success:
            error_msg = "❌ Lỗi khi sử dụng vật phẩm!"
            if is_slash:
                await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
            return
        
        print(f"[CONSUMABLE] Removed {item_key} from {user_id}")
        
        # Store active boost for this user (for normal consumables)
        self.active_boosts[user_id] = {
            "item_key": item_key,
            "effect_type": item_info["effect_type"],
            "effect_value": item_info["effect_value"],
        }
        
        print(f"[CONSUMABLE] Applied effect for {item_key} to {user_id}")
        
        # Send success message
        embed = discord.Embed(
            title=f"✅ Đã Sử Dụng {item_info['name']}",
            description="Vật phẩm đã được kích hoạt thành công!",
            color=discord.Color.green()
        )
        embed.add_field(name="📖 Mô tả", value=item_info["description"], inline=False)
        embed.add_field(name="📦 Còn lại", value=f"x{quantity - 1}", inline=False)
        embed.add_field(
            name="⏱️ Thời gian hiệu lực",
            value="Có hiệu lực cho lần câu cá huyền thoại tiếp theo",
            inline=False
        )
        
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)



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
        await add_item(target_user.id, item_key, quantity)
        
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

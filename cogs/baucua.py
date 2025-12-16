import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import asyncio
import time
from database_manager import (
    db_manager,
    get_user_balance,
    add_seeds,
    get_or_create_user,
    batch_update_seeds
)

DB_PATH = "./data/database.db"

# 6 Linh vật
ANIMALS = {
    "bau": {"name": "Bầu", "emoji": "🎃"},
    "cua": {"name": "Cua", "emoji": "🦀"},
    "tom": {"name": "Tôm", "emoji": "🦐"},
    "ca": {"name": "Cá", "emoji": "🐟"},
    "ga": {"name": "Gà", "emoji": "🐔"},
    "nai": {"name": "Nai", "emoji": "🦌"},
}

ANIMAL_LIST = list(ANIMALS.keys())

class BauCuaBetModal(discord.ui.Modal):
    """Modal for inputting bet amount"""
    def __init__(self, game_cog, game_id: str, animal_key: str):
        super().__init__(title=f"Cược {ANIMALS[animal_key]['name']}")
        self.game_cog = game_cog
        self.game_id = game_id
        self.animal_key = animal_key
        
        self.amount_input = discord.ui.TextInput(
            label="Số hạt muốn cược",
            placeholder="Nhập số từ 1 trở lên",
            min_length=1,
            max_length=6
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            amount = int(self.amount_input.value)
            if amount <= 0:
                await interaction.followup.send("Số lượng phải lớn hơn 0!", ephemeral=True)
                return
            
            # Process the bet
            await self.game_cog.add_bet(interaction, self.game_id, self.animal_key, amount)
        except ValueError:
            try:
                await interaction.followup.send("Vui lòng nhập số nguyên hợp lệ!", ephemeral=True)
            except:
                pass

class BauCuaBetView(discord.ui.View):
    """View with 6 bet buttons in 3x2 grid"""
    def __init__(self, game_cog, game_id: str):
        super().__init__(timeout=None)
        self.game_cog = game_cog
        self.game_id = game_id
    
    @discord.ui.button(label="🎃 Bầu", style=discord.ButtonStyle.primary, custom_id="baucua_bau", row=0)
    async def bet_bau(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BauCuaBetModal(self.game_cog, self.game_id, "bau")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🦀 Cua", style=discord.ButtonStyle.primary, custom_id="baucua_cua", row=0)
    async def bet_cua(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BauCuaBetModal(self.game_cog, self.game_id, "cua")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🦐 Tôm", style=discord.ButtonStyle.primary, custom_id="baucua_tom", row=0)
    async def bet_tom(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BauCuaBetModal(self.game_cog, self.game_id, "tom")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🐟 Cá", style=discord.ButtonStyle.primary, custom_id="baucua_ca", row=1)
    async def bet_ca(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BauCuaBetModal(self.game_cog, self.game_id, "ca")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🐔 Gà", style=discord.ButtonStyle.primary, custom_id="baucua_ga", row=1)
    async def bet_ga(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BauCuaBetModal(self.game_cog, self.game_id, "ga")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🦌 Nai", style=discord.ButtonStyle.primary, custom_id="baucua_nai", row=1)
    async def bet_nai(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BauCuaBetModal(self.game_cog, self.game_id, "nai")
        await interaction.response.send_modal(modal)

class BauCuaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # {channel_id: {'game_id': str, 'start_time': float, 'bets': {user_id: [(animal, amount), ...]}}}
    
    # ==================== HELPER FUNCTIONS ====================
    
    def generate_game_id(self):
        """Generate unique game ID"""
        return f"game_{int(time.time() * 1000)}"
    
    async def get_user_seeds(self, user_id: int) -> int:
        """Get user's current seeds with caching"""
        return await get_user_balance(user_id)
    
    async def update_seeds(self, user_id: int, amount: int):
        """Update user's seeds (can be negative)"""
        # Ensure user exists first
        await get_or_create_user(user_id, f"User#{user_id}")
        # Then update seeds
        await add_seeds(user_id, amount)
    
    def create_betting_embed(self, time_remaining: int):
        """Create embed for betting phase"""
        embed = discord.Embed(
            title="🎰 BẦU CUA TÔM CÁ GÀ NAI 🎰",
            description=f"⏳ **Cược trong {time_remaining}s**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Cách chơi",
            value="Bấm vào 1 nút để chọn linh vật, nhập số hạt muốn cược (max 250k)\n"
                  "Ví dụ: Cược 100 thì xuất hiện 1 lần = nhận 200 (lời 100) | 2 lần = nhận 300 (lời 200) | 3 lần = nhận 400 (lời 300)",
            inline=False
        )
        
        return embed
    
    def create_rolling_text(self, result1: str, result2: str, result3: str) -> str:
        """Create text display for rolling animation"""
        emoji1 = ANIMALS[result1]["emoji"]
        emoji2 = ANIMALS[result2]["emoji"]
        emoji3 = ANIMALS[result3]["emoji"]
        
        return f"{emoji1} {emoji2} {emoji3}"
    
    def create_result_display(self, result1: str, result2: str, result3: str) -> str:
        """Create text display for final results with large emojis"""
        emoji1 = ANIMALS[result1]["emoji"]
        emoji2 = ANIMALS[result2]["emoji"]
        emoji3 = ANIMALS[result3]["emoji"]
        
        return f"{emoji1} {emoji2} {emoji3}"
    
    async def add_bet(self, interaction: discord.Interaction, game_id: str, animal_key: str, bet_amount: int):
        """Add a bet for the user"""
        channel_id = interaction.channel.id
        user_id = interaction.user.id
        
        # Check if game still active
        if channel_id not in self.active_games or self.active_games[channel_id]['game_id'] != game_id:
            await interaction.followup.send("❌ Game đã kết thúc!", ephemeral=True)
            return
        
        # Check betting time remaining (must have at least 5 seconds left)
        time_remaining = 30 - int(time.time() - self.active_games[channel_id]['start_time'])
        if time_remaining < 5:
            await interaction.followup.send("⏰ Hết thời gian cược rồi! (Còn dưới 5 giây)", ephemeral=True)
            return
        
        # Validate bet amount (max 250k)
        if bet_amount > 250000:
            await interaction.followup.send(
                f"❌ Số tiền cược quá lớn!\nTối đa: 250000 | Bạn cược: {bet_amount}",
                ephemeral=True
            )
            return
        
        if bet_amount <= 0:
            await interaction.followup.send("❌ Số tiền cược phải lớn hơn 0!", ephemeral=True)
            return
        
        # Check if user has enough seeds
        user_seeds = await self.get_user_seeds(user_id)
        if user_seeds < bet_amount:
            await interaction.followup.send(
                f"❌ Bạn không đủ hạt!\nCần: {bet_amount} | Hiện có: {user_seeds}",
                ephemeral=True
            )
            return
        
        # Deduct seeds FIRST
        await self.update_seeds(user_id, -bet_amount)
        
        # THEN add to bets dictionary with safety check
        try:
            if channel_id in self.active_games:  # Verify game still exists
                if user_id not in self.active_games[channel_id]['bets']:
                    self.active_games[channel_id]['bets'][user_id] = []
                
                self.active_games[channel_id]['bets'][user_id].append((animal_key, bet_amount))
            else:
                # Game was deleted, refund the user
                await self.update_seeds(user_id, bet_amount)
                await interaction.followup.send("❌ Game đã kết thúc khi bạn cược! Tiền đã hoàn lại.", ephemeral=True)
                return
        except Exception as e:
            # If bets dict update fails, refund the user
            await self.update_seeds(user_id, bet_amount)
            print(f"[BAUCUA] Error adding bet: {e}")
            await interaction.followup.send("❌ Lỗi khi xử lý cược! Tiền đã hoàn lại.", ephemeral=True)
            return
        
        await interaction.followup.send(
            f"Bạn đã cược **{bet_amount} hạt** vào **{ANIMALS[animal_key]['name']}** {ANIMALS[animal_key]['emoji']}",
            ephemeral=True
        )
        print(f"[BAUCUA] {interaction.user.name} bet {bet_amount} seeds on {ANIMALS[animal_key]['name']}")
    
    async def animate_roll(self, message: discord.Message, duration: float = 6.0):
        """Animate the roll for duration seconds"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Random 3 animals
            r1, r2, r3 = random.choices(ANIMAL_LIST, k=3)
            
            rolling_text = self.create_rolling_text(r1, r2, r3)
            
            try:
                await message.edit(content=rolling_text, embed=None)
            except:
                pass
            
            await asyncio.sleep(0.3)  # Update every 0.3 seconds
        
        return r1, r2, r3  # Return final result
    
    async def calculate_results(self, channel_id: int, result1: str, result2: str, result3: str):
        """Calculate results for all bets - OPTIMIZED: No DB writes here, only prepare data"""
        final_result = [result1, result2, result3]
        bets = self.active_games[channel_id]['bets']
        
        results_text = []
        
        for user_id, bet_list in bets.items():
            user_mention = f"<@{user_id}>"  # Use ID mention, no fetch
            
            for animal_key, bet_amount in bet_list:
                matches = sum(1 for r in final_result if r == animal_key)
                
                if matches == 0:
                    result_text = f"❌ {user_mention} cược {bet_amount} hạt vào **{ANIMALS[animal_key]['name']}** - **THUA {bet_amount} hạt**"
                else:
                    # Formula: bet_amount * (matches + 1) = winnings, but display net profit
                    winnings = bet_amount * (matches + 1)
                    net_profit = winnings - bet_amount
                    result_text = f"✅ {user_mention} cược {bet_amount} hạt vào **{ANIMALS[animal_key]['name']}** - **THẮNG {net_profit} hạt** ({matches}x) → nhận {winnings}"
                
                results_text.append(result_text)
        
        return results_text
    
    async def update_game_results_batch(self, channel_id: int, result1: str, result2: str, result3: str, bets_data: dict = None):
        """OPTIMIZED: Update all game results in a SINGLE BATCH transaction"""
        final_result = [result1, result2, result3]
        bets = bets_data if bets_data is not None else {}
        
        # Prepare batch updates (calculate all updates first, then execute once)
        updates = {}  # {user_id: net_change}
        
        for user_id, bet_list in bets.items():
            user_change = 0
            
            for animal_key, bet_amount in bet_list:
                matches = sum(1 for r in final_result if r == animal_key)
                
                if matches > 0:
                    # Formula: bet_amount * (matches + 1)
                    winnings = bet_amount * (matches + 1)
                    user_change += winnings
                else:
                    # Already deducted at bet time, no additional change
                    user_change += 0
            
            if user_change > 0:
                updates[user_id] = user_change
        
        # Execute all updates in single batch operation
        if updates:
            await batch_update_seeds(updates)
            print(f"[BAUCUA] Batch updated {len(updates)} users")
    
    async def create_summary_text(self, result1: str, result2: str, result3: str, bets_data: dict = None):
        """Create detailed summary text of results per user"""
        final_result = [result1, result2, result3]
        # Use passed bets_data parameter
        bets = bets_data if bets_data is not None else {}
        
        summary_lines = []
        
        for user_id, bet_list in bets.items():
            # Use user ID mention format (no fetch needed, instant)
            user_mention = f"<@{user_id}>"
            
            # Build detailed bet breakdown
            bet_details = []
            total_winnings = 0
            total_loss = 0
            
            for animal_key, bet_amount in bet_list:
                matches = sum(1 for r in final_result if r == animal_key)
                
                # Add animal name and amount
                animal_name = ANIMALS[animal_key]['name']
                bet_details.append(f"{animal_name} {bet_amount}")
                
                if matches > 0:
                    # Formula: bet_amount * (matches + 1)
                    # cược 10 ăn 1 = 10 * 2 = 20 (lời 10)
                    # cược 10 ăn 2 = 10 * 3 = 30 (lời 20)
                    # cược 10 ăn 3 = 10 * 4 = 40 (lời 30)
                    total_winnings += bet_amount * (matches + 1)
                else:
                    total_loss += bet_amount
            
            # Build summary for this user
            bet_str = ", ".join(bet_details)
            
            # Build result string with both wins and losses
            result_parts = []
            if total_winnings > 0:
                result_parts.append(f"thắng {total_winnings}")
            if total_loss > 0:
                result_parts.append(f"thua {total_loss}")
            
            result_str = ", ".join(result_parts) if result_parts else "hoà"
            
            summary = f"{user_mention} đã cược {bet_str} 🌱 và {result_str} 🌱"
            summary_lines.append(summary)
        
        return "\n".join(summary_lines)
    
    # ==================== COMMANDS ====================
    
    @app_commands.command(name="baucua", description="Chơi game Bầu Cua Tôm Cá Gà Nai")
    async def play_baucua_slash(self, interaction: discord.Interaction):
        """Start Bầu Cua game via slash command"""
        await self._start_game(interaction)
    
    @commands.command(name="baucua", description="Chơi game Bầu Cua Tôm Cá Gà Nai")
    async def play_baucua_prefix(self, ctx):
        """Start Bầu Cua game via prefix command"""
        await self._start_game(ctx)
    
    async def _start_game(self, ctx_or_interaction):
        """Start the Bầu Cua game"""
        try:
            # Determine if it's slash command or prefix command
            is_slash = isinstance(ctx_or_interaction, discord.Interaction)
            
            if is_slash:
                channel = ctx_or_interaction.channel
                interaction = ctx_or_interaction
                await interaction.response.defer(ephemeral=False)
            else:
                channel = ctx_or_interaction.channel
                ctx = ctx_or_interaction
            
            channel_id = channel.id
            
            # Check if there's already a game in this channel
            if channel_id in self.active_games:
                msg = "❌ Kênh này đã có game đang chơi! Chờ kết thúc trước khi tạo game mới."
                if is_slash:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
            
            # Create game
            game_id = self.generate_game_id()
            self.active_games[channel_id] = {
                'game_id': game_id,
                'start_time': time.time(),
                'bets': {}
            }
            
            # Send betting embed
            embed = self.create_betting_embed(30)
            view = BauCuaBetView(self, game_id)
            
            if is_slash:
                game_message = await interaction.followup.send(embed=embed, view=view)
            else:
                game_message = await ctx.send(embed=embed, view=view)
            
            print(f"[BAUCUA] Game {game_id} started in channel {channel.name}")
            
            # Countdown betting phase (30 seconds)
            betting_duration = 30
            start_time = time.time()
            last_update = 0
            
            while time.time() - start_time < betting_duration:
                current_time = time.time() - start_time
                time_remaining = betting_duration - int(current_time)
                
                # Only update embed every 1 second to reduce API calls
                if int(current_time) != last_update and time_remaining > 0:
                    embed = self.create_betting_embed(time_remaining)
                    try:
                        await game_message.edit(embed=embed, view=view)
                    except:
                        pass
                    last_update = int(current_time)
                
                await asyncio.sleep(0.1)  # Check more frequently for cleaner cutoff
            
            # Betting phase ended - disable buttons
            try:
                for item in view.children:
                    item.disabled = True
                
                embed = self.create_betting_embed(0)
                await game_message.edit(embed=embed, view=view)
            except:
                pass
            
            # Check if anyone bet
            if not self.active_games[channel_id]['bets']:
                await channel.send("⚠️ Không ai cược! Game bị hủy.")
                print(f"[BAUCUA] Game {game_id} cancelled - no bets received")
                del self.active_games[channel_id]
                return
            
            bets_count = sum(len(bets) for bets in self.active_games[channel_id]['bets'].values())
            print(f"[BAUCUA] Game {game_id} - Received {len(self.active_games[channel_id]['bets'])} players with {bets_count} total bets")
            
            # Start rolling animation
            await asyncio.sleep(1)  # Small delay before rolling
            
            result1, result2, result3 = random.choices(ANIMAL_LIST, k=3)
            rolling_text = self.create_rolling_text(result1, result2, result3)
            rolling_message = await channel.send(rolling_text)
            
            # Animate for 10 seconds
            result1, result2, result3 = await self.animate_roll(rolling_message, duration=10.0)
            
            # Get bets data before cleanup
            bets_data = self.active_games[channel_id]['bets'].copy() if channel_id in self.active_games else {}
            
            # Create summary immediately with bets data (no active_games access needed)
            summary_text = await self.create_summary_text(result1, result2, result3, bets_data)
            
            # Show final results and send summary in parallel (not sequential)
            result_stop_time = time.time()
            result_display = self.create_result_display(result1, result2, result3)
            
            # Start both tasks simultaneously
            await asyncio.gather(
                rolling_message.edit(content=result_display),
                channel.send(f"**TỔNG KẾT:**\n{summary_text}")
            )
            summary_send_time = time.time()
            delay_ms = (summary_send_time - result_stop_time) * 1000
            print(f"[BAUCUA] 📊 Summary sent! Delay: {delay_ms:.1f}ms")
            
            # Clean up game state immediately
            if channel_id in self.active_games:
                del self.active_games[channel_id]
            
            # Update game results in background with bets data (OPTIMIZED: batch update)
            asyncio.create_task(self.update_game_results_batch(channel_id, result1, result2, result3, bets_data))
            
            print(f"[BAUCUA] Game {game_id} finished in channel {channel.name}")
        
        except Exception as e:
            print(f"[BAUCUA] Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up on error
            if is_slash:
                try:
                    await interaction.followup.send(f"❌ Lỗi: {str(e)}", ephemeral=True)
                except:
                    pass
            else:
                try:
                    await ctx.send(f"❌ Lỗi: {str(e)}")
                except:
                    pass
            
            # Remove active game if exists
            if channel_id in self.active_games:
                del self.active_games[channel_id]

async def setup(bot):
    await bot.add_cog(BauCuaCog(bot))

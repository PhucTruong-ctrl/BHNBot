"""
Werewolf Game Cog
Main Discord bot integration
"""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiosqlite
from typing import Optional, List
from datetime import datetime
import random

from .models import (
    GameWerewolf, GamePlayer, GameState, Role, Faction, Alignment,
    ROLE_METADATA, get_role_by_alias
)
from .game_logic import GameLogic
from .views import (
    GameLobbyView, JoinButtonView, RoleSelectView, VoteSelectView,
    SkipActionButton, ConfirmView, GameControlView, DebugRoleSelectView
)
from .night_phase import NightPhaseHandler
from .day_phase import DayPhaseHandler


def log(msg: str):
    """Log message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Werewolf] {msg}")


class WerewolfCog(commands.Cog):
    """Cog quản lý game Ma Sói"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logic = GameLogic()
        self.night_handler = NightPhaseHandler(bot)
        self.day_handler = DayPhaseHandler(bot)
    
    @commands.Cog.listener()
    async def on_ready(self):
        log(f"Werewolf Cog loaded - {self.bot.user}")
    
    # ================ LOBBY PHASE ================
    
    @app_commands.command(name="werewolf", description="Lệnh Ma Sói")
    @app_commands.describe(
        action="create=tạo game, join=tham gia, start=bắt đầu, status=xem trạng thái, quit=thoát",
        num_players="Số người chơi tối thiểu (default: 4)"
    )
    async def werewolf_slash(
        self,
        interaction: discord.Interaction,
        action: str,
        num_players: int = 4
    ):
        """Main Werewolf slash command"""
        action = action.lower()
        
        if action == "create":
            await self._handle_create(interaction, num_players)
        elif action == "join":
            await self._handle_join(interaction)
        elif action == "start":
            await self._handle_start(interaction)
        elif action == "status":
            await self._handle_status(interaction)
        elif action == "quit":
            await self._handle_quit(interaction)
        else:
            await interaction.response.send_message(
                "❌ Hành động không hợp lệ. Dùng: create, join, start, status, quit",
                ephemeral=True
            )
    
    @commands.command(name="werewolf")
    async def werewolf_prefix(self, ctx, action: str = None, num_players: int = 4):
        """Prefix command cho werewolf"""
        if not action:
            await ctx.send("❌ Dùng: `!werewolf create|join|start|status|quit`")
            return
        
        action = action.lower()
        
        if action == "create":
            await self._handle_create_prefix(ctx, num_players)
        elif action == "join":
            await self._handle_join_prefix(ctx)
        elif action == "start":
            await self._handle_start_prefix(ctx)
        elif action == "status":
            await self._handle_status_prefix(ctx)
        elif action == "quit":
            await self._handle_quit_prefix(ctx)
        else:
            await ctx.send("❌ Hành động không hợp lệ. Dùng: create, join, start, status, quit")
    
    async def _handle_create(self, interaction: discord.Interaction, min_players: int):
        """Tạo game mới"""
        await interaction.response.defer()
        
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        
        # Check nếu đã có game
        if self.logic.get_game(guild_id):
            await interaction.followup.send("FAIL Da co game dang chay!")
            return
        
        # Tạo game với min_players
        game = self.logic.create_game(guild_id, channel_id, min_players)
        game.state = GameState.WAITING
        
        # Tạo embed duy nhất với join button + control buttons
        embed = discord.Embed(
            title="GAME MA SOI",
            description=f"Tối thiểu {min_players} người chơi\n\nBấm nút **Tham gia** để tham gia game!",
            color=discord.Color.red()
        )
        embed.add_field(name="Người chơi", value=f"0/{min_players}", inline=False)
        embed.set_footer(text="Admin có thể bấm 'Bắt đầu Game' khi đủ người")
        
        # Tạo view với cả join button + control buttons
        view = GameLobbyView(
            on_join=self._on_join_button,
            on_start=self._on_start_button,
            on_cancel=self._on_cancel_button
        )
        
        # Send lobby message
        msg = await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=False
        )
        
        game.main_channel_msg_id = msg.id
        
        log(f"Game created in guild {guild_id}")
    
    async def _on_join_button(self, interaction: discord.Interaction):
        """Xử lý khi người chơi bấm join"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        username = interaction.user.name
        
        game = self.logic.get_game(guild_id)
        if not game:
            await interaction.followup.send("❌ Game không tồn tại!", ephemeral=True)
            return
        
        if game.state != GameState.WAITING:
            await interaction.followup.send("❌ Game đã bắt đầu!", ephemeral=True)
            return
        
        # Add player
        if self.logic.add_player(game, user_id, username):
            await interaction.followup.send(
                f"✅ {username} đã tham gia! ({len(game.players)}/{game.min_players})",
                ephemeral=True
            )
            log(f"Player {username} joined. Total: {len(game.players)}")
            
            # Update lobby message with player count every 3 seconds
            try:
                channel = interaction.guild.get_channel(game.channel_id)
                if channel and game.main_channel_msg_id:
                    msg = await channel.fetch_message(game.main_channel_msg_id)
                    if msg:
                        # Update embed field
                        for embed in msg.embeds:
                            for i, field in enumerate(embed.fields):
                                if field.name == "Người chơi":
                                    embed.set_field_at(
                                        i,
                                        name="Người chơi",
                                        value=f"{len(game.players)}/{game.min_players}",
                                        inline=False
                                    )
                        await msg.edit(embed=embed)
                        log(f"Updated lobby message: {len(game.players)}/{game.min_players}")
            except Exception as e:
                log(f"WARN Failed to update lobby message: {e}")
        else:
            await interaction.followup.send(
                f"❌ {username} đã tham gia rồi!",
                ephemeral=True
            )
    
    async def _on_start_button(self, interaction: discord.Interaction):
        """Xử lý khi admin bấm start"""
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Chỉ admin có thể bắt đầu game!", ephemeral=True)
            return
        
        await self._handle_start(interaction)
    
    async def _on_cancel_button(self, interaction: discord.Interaction):
        """Xử lý khi admin bấm cancel"""
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Chỉ admin có thể hủy game!", ephemeral=True)
            return
        
        await self._handle_quit(interaction)
    
    async def _handle_join(self, interaction: discord.Interaction):
        """Xử lý lệnh join"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        
        game = self.logic.get_game(guild_id)
        if not game:
            await interaction.followup.send("❌ Không có game nào!", ephemeral=True)
            return
        
        if self.logic.add_player(game, user_id, interaction.user.name):
            await interaction.followup.send(
                f"✅ Bạn đã tham gia! ({len(game.players)} người)",
                ephemeral=True
            )
        else:
            await interaction.followup.send("❌ Bạn đã tham gia rồi!", ephemeral=True)
    
    async def _handle_start(self, interaction: discord.Interaction):
        """Xử lý bắt đầu game"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        game = self.logic.get_game(guild_id)
        
        if not game:
            await interaction.followup.send("❌ Không có game nào!", ephemeral=True)
            return
        
        if len(game.players) < game.min_players:
            await interaction.followup.send(
                f"FAIL: Need minimum {game.min_players} players (current: {len(game.players)})",
                ephemeral=True
            )
            return
        
        log(f"GAME_START: Starting game with {len(game.players)} players")
        
        # Change state
        game.state = GameState.GAME_START
        
        # DEBUG: Show role selection UI (disabled by default)
        DEBUG_ROLE_SELECTION = False
        if DEBUG_ROLE_SELECTION:
            # Show debug role selection before starting
            embed = discord.Embed(
                title="🔧 DEBUG: Chọn vai trò tùy chỉnh",
                description="Sử dụng menu dưới để gán vai trò thủ công cho người chơi",
                color=discord.Color.orange()
            )
            view = DebugRoleSelectView(game, self._on_debug_role_select)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Normal: Distribute roles - build diverse role list
        # (DEBUG: Random role assignment is commented out and disabled)
        num_players = len(game.players)
        print(f"[COG_DEBUG] About to call build_role_list with num_players={num_players}")
        roles = self.logic.build_role_list(num_players)
        print(f"[COG_DEBUG] build_role_list returned: {[r.value for r in roles]}")
        log(f"ROLE_LIST: Building {len(roles)} roles: {[r.value for r in roles]}")
        # === COMMENTED OUT: Random role assignment ===
        # self.logic.distribute_roles(game, roles)
        # =============================================
        
        await interaction.followup.send("⏳ Xin chờ, đang chuẩn bị...", ephemeral=True)
        
        # Send DM to each player
        for player in game.players.values():
            try:
                user = await self.bot.fetch_user(player.user_id)
                await user.send(
                    f"Vai trò của bạn: **{player.role.value if player.role else 'Chưa gán'}**\n\n"
                    f"{ROLE_METADATA[player.role].description if player.role else 'Đang chờ gán vai trò...'}"
                )
            except Exception as e:
                log(f"Error sending DM to {player.username}: {e}")
        
        # Start first night
        await self._start_night_phase(game, interaction)
    
    async def _on_debug_role_select(self, interaction: discord.Interaction, player_id: int, role: Role):
        """Callback khi debug select vai trò"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        game = self.logic.get_game(guild_id)
        
        if not game or player_id not in game.players:
            await interaction.followup.send("❌ Người chơi không tồn tại!", ephemeral=True)
            return
        
        player = game.players[player_id]
        player.role = role
        
        await interaction.followup.send(
            f"✅ Gán vai trò **{role.value}** cho **{player.username}**",
            ephemeral=True
        )
        log(f"DEBUG: Assigned role {role.value} to {player.username}")
    
    async def _start_night_phase(self, game: GameWerewolf, interaction: discord.Interaction):
        """Bắt đầu giai đoạn ban đêm"""
        game.state = GameState.NIGHT_PHASE
        game.night_count += 1
        
        channel = interaction.channel
        
        # Run night phase
        night_result = await self.night_handler.run_night_phase(game, channel)
        
        # Mute dead players from night kills
        await self._mute_dead_players(game, channel)
        
        # Check win condition after night
        win_condition = self.logic.check_win_condition(game)
        if win_condition:
            await self._end_game(game, channel, win_condition)
            return
        
        # Move to day phase
        game.day_count += 1
        lynched = await self.day_handler.run_day_phase(game, channel, night_result)
        
        # Check win condition after lynch
        win_condition = self.logic.check_win_condition(game)
        if win_condition:
            await self._end_game(game, channel, win_condition)
            return
        
        # Reset actions for next round
        self.logic.reset_night_actions(game)
        self.logic.reset_day_votes(game)
        
        # Show status
        await self.day_handler.display_status(game, channel)
        
        # Wait before next night
        await asyncio.sleep(5)
        
        # Loop back to night phase
        await self._start_night_phase(game, interaction)
    
    async def _end_game(self, game: GameWerewolf, channel: discord.TextChannel, win_condition: dict):
        """Kết thúc game"""
        game.state = GameState.ENDED
        
        # Create victory embed
        embed = discord.Embed(
            title="GAME KET THUC",
            description=win_condition["reason"],
            color=discord.Color.green() if win_condition["winner"] == "VILLAGE" else discord.Color.red()
        )
        
        # List winners
        winner_names = []
        for uid in win_condition.get("winners", []):
            if uid in game.players:
                winner_names.append(f"{game.players[uid].username} ({game.players[uid].role.value})")
        
        if winner_names:
            embed.add_field(
                name="Nhung Nguoi Thang",
                value="\n".join(winner_names),
                inline=False
            )
        
        await channel.send(embed=embed)
        
        log(f"Game ended: {win_condition['winner']} won")
        
        # Delete wolf thread if exists
        if game.wolf_thread_id:
            try:
                wolf_thread = self.bot.get_channel(game.wolf_thread_id)
                if wolf_thread:
                    await wolf_thread.delete()
                    log(f"Deleted wolf thread {game.wolf_thread_id}")
            except Exception as e:
                log(f"Failed to delete wolf thread: {e}")
        
        # Delete game
        self.logic.delete_game(game.guild_id)
    
    # ================ UTILITY METHODS ================
    
    async def _mute_dead_players(self, game: GameWerewolf, channel: discord.TextChannel):
        """Mute dead players in game channel"""
        try:
            guild = channel.guild
            dead_players = game.get_dead_players()
            
            if not dead_players:
                return
            
            log(f"MUTE: Muting {len(dead_players)} dead players in #{channel.name}")
            
            # Create deny overwrite
            deny_overwrite = discord.PermissionOverwrite(send_messages=False)
            
            for dead_player in dead_players:
                try:
                    member = guild.get_member(dead_player.user_id)
                    if member:
                        await channel.set_permissions(member, overwrite=deny_overwrite)
                        log(f"OK DEAD_MUTE [{dead_player.username}] Muted")
                    else:
                        log(f"WARN DEAD_MUTE [{dead_player.username}] Member not found")
                except Exception as e:
                    log(f"FAIL DEAD_MUTE_ERROR [{dead_player.username}]: {e}")
        except Exception as e:
            log(f"FAIL DEAD_MUTE_ERROR: {e}")
    
    async def _handle_status(self, interaction: discord.Interaction):
        """Xem trạng thái game"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        game = self.logic.get_game(guild_id)
        
        if not game:
            await interaction.followup.send("❌ Không có game nào!", ephemeral=True)
            return
        
        alive = len(game.get_alive_players())
        dead = len(game.get_dead_players())
        
        embed = discord.Embed(
            title="📊 Trạng thái Game",
            color=discord.Color.blue()
        )
        embed.add_field(name="Trạng thái", value=game.state.value, inline=False)
        embed.add_field(name="👥 Còn sống", value=str(alive), inline=True)
        embed.add_field(name="💀 Chết", value=str(dead), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _handle_quit(self, interaction: discord.Interaction):
        """Xóa game"""
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Chỉ admin có thể hủy game!", ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        self.logic.delete_game(guild_id)
        
        await interaction.followup.send("✅ Game đã bị hủy!", ephemeral=True)
        log(f"Game deleted in guild {guild_id}")
    
    # ================ PREFIX HANDLERS ================
    
    async def _handle_create_prefix(self, ctx, num_players: int):
        """Tạo game (prefix)"""
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        
        if self.logic.get_game(guild_id):
            await ctx.send("❌ Đã có game đang chạy!")
            return
        
        game = self.logic.create_game(guild_id, channel_id)
        game.state = GameState.WAITING
        
        embed = discord.Embed(
            title="🐺 GAME MA SÓI 🐺",
            description=f"Tối thiểu {num_players} người chơi\n\nBấm nút **Tham gia** để tham gia game!",
            color=discord.Color.red()
        )
        embed.set_footer(text="Admin có thể bấm 'Bắt đầu Game' khi đủ người")
        
        view = JoinButtonView(on_join=self._on_join_button)
        control_view = GameControlView(
            on_start=self._on_start_button_prefix(ctx),
            on_cancel=self._on_cancel_button_prefix(ctx)
        )
        
        msg = await ctx.send(embed=embed, view=view)
        game.main_channel_msg_id = msg.id
        
        log(f"Game created in guild {guild_id} (prefix)")
    
    async def _handle_join_prefix(self, ctx):
        """Join game (prefix)"""
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        username = ctx.author.name
        
        game = self.logic.get_game(guild_id)
        if not game:
            await ctx.send("❌ Không có game nào!")
            return
        
        if game.state != GameState.WAITING:
            await ctx.send("❌ Game đã bắt đầu!")
            return
        
        if self.logic.add_player(game, user_id, username):
            await ctx.send(f"✅ {username} đã tham gia game! ({len(game.players)} người)")
        else:
            await ctx.send(f"❌ {username} đã tham gia rồi!")
    
    async def _handle_start_prefix(self, ctx):
        """Start game (prefix)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Chỉ admin có thể bắt đầu game!")
            return
        
        guild_id = ctx.guild.id
        game = self.logic.get_game(guild_id)
        
        if not game:
            await ctx.send("FAIL: No game running!")
            return
        
        if len(game.players) < game.min_players:
            await ctx.send(f"FAIL: Need minimum {game.min_players} players (current: {len(game.players)})")
            return
        
        game.state = GameState.GAME_START
        
        num_players = len(game.players)
        roles = self.logic.build_role_list(num_players)
        self.logic.distribute_roles(game, roles)
        
        await ctx.send("Game bắt đầu! Đang gửi vai trò...")
        
        for player in game.players.values():
            try:
                dm = await self.bot.fetch_user(player.user_id)
                await dm.send(
                    f"🎮 Vai trò của bạn: **{player.role.value}**\n\n"
                    f"{ROLE_METADATA[player.role].description}"
                )
            except Exception as e:
                log(f"Error sending DM to {player.username}: {e}")
        
        await self._start_night_phase_prefix(game, ctx)
    
    async def _handle_status_prefix(self, ctx):
        """Xem trạng thái (prefix)"""
        guild_id = ctx.guild.id
        game = self.logic.get_game(guild_id)
        
        if not game:
            await ctx.send("❌ Không có game nào!")
            return
        
        alive = len(game.get_alive_players())
        dead = len(game.get_dead_players())
        
        embed = discord.Embed(
            title="📊 Trạng thái Game",
            color=discord.Color.blue()
        )
        embed.add_field(name="Trạng thái", value=game.state.value, inline=False)
        embed.add_field(name="👥 Còn sống", value=str(alive), inline=True)
        embed.add_field(name="💀 Chết", value=str(dead), inline=True)
        
        await ctx.send(embed=embed)
    
    async def _handle_quit_prefix(self, ctx):
        """Quit game (prefix)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Chỉ admin có thể hủy game!")
            return
        
        guild_id = ctx.guild.id
        self.logic.delete_game(guild_id)
        
        await ctx.send("✅ Game đã bị hủy!")
    
    def _on_start_button_prefix(self, ctx):
        """Factory để tạo callback cho prefix"""
        async def callback(interaction):
            await interaction.response.defer(ephemeral=True)
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("❌ Chỉ admin có thể bắt đầu game!", ephemeral=True)
                return
            await self._handle_start_prefix(ctx)
        return callback
    
    def _on_cancel_button_prefix(self, ctx):
        """Factory để tạo callback cho prefix"""
        async def callback(interaction):
            await interaction.response.defer(ephemeral=True)
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("❌ Chỉ admin có thể hủy game!", ephemeral=True)
                return
            await self._handle_quit_prefix(ctx)
        return callback
    
    async def _start_night_phase_prefix(self, game: GameWerewolf, ctx):
        """Ban đêm (prefix)"""
        game.state = GameState.NIGHT_PHASE
        game.night_count += 1
        
        # Run night phase
        night_result = await self.night_handler.run_night_phase(game, ctx.channel)
        
        # Check win condition after night
        win_condition = self.logic.check_win_condition(game)
        if win_condition:
            await self._end_game(game, ctx.channel, win_condition)
            return
        
        # Move to day phase
        game.day_count += 1
        lynched = await self.day_handler.run_day_phase(game, ctx.channel, night_result)
        
        # Check win condition after lynch
        win_condition = self.logic.check_win_condition(game)
        if win_condition:
            await self._end_game(game, ctx.channel, win_condition)
            return
        
        # Reset actions
        self.logic.reset_night_actions(game)
        self.logic.reset_day_votes(game)
        
        # Show status
        await self.day_handler.display_status(game, ctx.channel)
        
        # Wait
        await asyncio.sleep(5)
        
        # Loop
        await self._start_night_phase_prefix(game, ctx)
    
    # ================ CONFIG COMMANDS ================
    
    @commands.command(name="config_admin")
    async def config_admin(self, ctx, channel_id: int = None):
        """Set admin channel for werewolf config
        Usage: !config_admin CHANNEL_ID
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Chỉ admin có thể cấu hình!")
            return
        
        guild_id = ctx.guild.id
        
        if channel_id is None:
            await ctx.send("❌ Cần nhập Channel ID. Dùng: `!config_admin CHANNEL_ID`")
            return
        
        try:
            DB_PATH = "./data/database.db"
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if guild exists in config
                async with db.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    # Update existing
                    await db.execute(
                        "UPDATE server_config SET admin_channel_id = ? WHERE guild_id = ?",
                        (channel_id, guild_id)
                    )
                else:
                    # Insert new
                    await db.execute(
                        "INSERT INTO server_config (guild_id, admin_channel_id) VALUES (?, ?)",
                        (guild_id, channel_id)
                    )
                
                await db.commit()
            
            channel = ctx.guild.get_channel(channel_id)
            channel_name = f"#{channel.name}" if channel else f"ID: {channel_id}"
            await ctx.send(f"✅ Cấu hình admin channel: {channel_name}")
            log(f"📋 CONFIG: Admin channel set to {channel_id} for guild {guild_id}")
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")
            log(f"❌ CONFIG_ERROR: {e}")
    
    @commands.command(name="config_noitu")
    async def config_noitu(self, ctx, channel_id: int = None):
        """Set Nối Từ channel
        Usage: !config_noitu CHANNEL_ID
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Chỉ admin có thể cấu hình!")
            return
        
        guild_id = ctx.guild.id
        
        if channel_id is None:
            await ctx.send("❌ Cần nhập Channel ID. Dùng: `!config_noitu CHANNEL_ID`")
            return
        
        try:
            DB_PATH = "./data/database.db"
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if guild exists in config
                async with db.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    # Update existing
                    await db.execute(
                        "UPDATE server_config SET noitu_channel_id = ? WHERE guild_id = ?",
                        (channel_id, guild_id)
                    )
                else:
                    # Insert new
                    await db.execute(
                        "INSERT INTO server_config (guild_id, noitu_channel_id) VALUES (?, ?)",
                        (guild_id, channel_id)
                    )
                
                await db.commit()
            
            channel = ctx.guild.get_channel(channel_id)
            channel_name = f"#{channel.name}" if channel else f"ID: {channel_id}"
            await ctx.send(f"✅ Cấu hình Nối Từ channel: {channel_name}")
            log(f"📋 CONFIG: Nối Từ channel set to {channel_id} for guild {guild_id}")
        except Exception as e:
            await ctx.send(f"❌ Lỗi: {e}")
            log(f"❌ CONFIG_ERROR: {e}")
    
    @commands.command(name="config_wolf")
    async def config_wolf(self, ctx, channel_id: int = None):
        """Set Wolf meeting channel for werewolf
        Usage: !config_wolf CHANNEL_ID
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("FAIL: Only admin can configure!")
            return
        
        guild_id = ctx.guild.id
        
        if channel_id is None:
            await ctx.send("FAIL: Need Channel ID. Use: `!config_wolf CHANNEL_ID`")
            return
        
        try:
            DB_PATH = "./data/database.db"
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if guild exists in config
                async with db.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    # Update existing
                    await db.execute(
                        "UPDATE server_config SET wolf_channel_id = ? WHERE guild_id = ?",
                        (channel_id, guild_id)
                    )
                    log(f"CONFIG_WOLF: UPDATE guild {guild_id} wolf_channel_id={channel_id}")
                else:
                    # Insert new
                    await db.execute(
                        "INSERT INTO server_config (guild_id, wolf_channel_id) VALUES (?, ?)",
                        (guild_id, channel_id)
                    )
                    log(f"CONFIG_WOLF: INSERT guild {guild_id} wolf_channel_id={channel_id}")
                
                await db.commit()
                
                # Verify write
                async with db.execute("SELECT wolf_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as verify_cursor:
                    verify_row = await verify_cursor.fetchone()
                    if verify_row:
                        saved_id = verify_row[0]
                        log(f"CONFIG_VERIFY: Read back wolf_channel_id={saved_id} for guild {guild_id}")
                    else:
                        log(f"CONFIG_VERIFY: FAIL - Guild {guild_id} not found after write!")
            
            channel = ctx.guild.get_channel(channel_id)
            channel_name = f"#{channel.name}" if channel else f"ID: {channel_id}"
            await ctx.send(f"OK Wolf channel configured: {channel_name}")
            log(f"CONFIG_WOLF: Wolf channel set to {channel_id} for guild {guild_id}")
        except Exception as e:
            await ctx.send(f"FAIL: {e}")
            log(f"FAIL CONFIG_WOLF: {e}")
    
    @commands.command(name="config_wolf_check")
    async def config_wolf_check(self, ctx):
        """Check current wolf channel configuration
        Usage: !config_wolf_check
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("FAIL: Only admin can check config!")
            return
        
        guild_id = ctx.guild.id
        
        try:
            DB_PATH = "./data/database.db"
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT wolf_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row is None:
                        await ctx.send(f"CONFIG_CHECK: No config for guild {guild_id}")
                        log(f"CONFIG_CHECK: Guild {guild_id} has NO config row")
                    else:
                        wolf_id = row[0]
                        if wolf_id:
                            channel = ctx.guild.get_channel(wolf_id)
                            channel_name = f"#{channel.name}" if channel else f"ID: {wolf_id}"
                            await ctx.send(f"OK Current wolf channel: {channel_name}")
                            log(f"CONFIG_CHECK: Guild {guild_id} wolf_channel_id={wolf_id}")
                        else:
                            await ctx.send(f"CONFIG_CHECK: wolf_channel_id is NULL for guild {guild_id}")
                            log(f"CONFIG_CHECK: Guild {guild_id} wolf_channel_id=NULL")
        except Exception as e:
            await ctx.send(f"FAIL: {e}")
            log(f"FAIL CONFIG_CHECK: {e}")


async def setup(bot):
    """Load Cog"""
    await bot.add_cog(WerewolfCog(bot))

import discord
from discord import app_commands
from discord.ext import commands
import traceback
import json

from database_manager import db_manager  # Use singleton instead of direct connections
from core.logger import setup_logger

logger = setup_logger("ConfigCog", "cogs/config.log")

DB_PATH = "./data/database.db"

class ApprovalView(discord.ui.View):
    def __init__(self, bot, word, suggester_id):
        super().__init__(timeout=1800)  # 30 min for word approval
        self.bot = bot
        self.word = word
        self.suggester_id = suggester_id

    @discord.ui.button(label="Duyệt", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Postgres: $1
            await db_manager.execute(
                "INSERT INTO dictionary (word) VALUES ($1) ON CONFLICT DO NOTHING",
                (self.word,)
            )
        except Exception as e:
            logger.error(f"Error approving word: {e}")
            pass
            
        await db_manager.execute("DELETE FROM pending_words WHERE word = $1", (self.word,))
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Trạng thái", value=f"✅ Đã duyệt bởi {interaction.user.mention}")
        
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        
        try:
            user = await self.bot.fetch_user(self.suggester_id)
            await user.send(f"🎉 Từ **{self.word}** bạn đóng góp đã được duyệt!")
        except: pass

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger, emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db_manager.execute("DELETE FROM pending_words WHERE word = $1", (self.word,))
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Trạng thái", value=f"❌ Đã từ chối bởi {interaction.user.mention}")
        
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="Cài đặt hệ thống Bot")

    # Slash command: /reset
    @app_commands.command(name="reset", description="Reset game trong kênh hiện tại")
    async def reset_slash(self, interaction: discord.Interaction):
        """Reset game in current channel"""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            return
        await self._handle_reset(interaction.guild_id, interaction.channel_id, interaction)

    # Prefix command: !reset
    @commands.command(name="reset", description="Reset game trong kênh hiện tại")
    async def reset_prefix(self, ctx):
        """Reset game in current channel"""
        await self._handle_reset(ctx.guild.id, ctx.channel.id, ctx)

    async def _handle_reset(self, guild_id, channel_id, response_obj):
        """Handle reset logic for both slash and prefix commands - supports Werewolf, NoiTu, and Tree games"""
        try:
            # Check for Werewolf game in current channel first
            werewolf_manager = None
            werewolf_cog = self.bot.get_cog("WerewolfCog")
            if werewolf_cog:
                werewolf_manager = werewolf_cog.manager
                game = await werewolf_manager.get_game(guild_id)
                
                if game and not game.is_finished:
                    # Found an active werewolf game
                    if game.channel.id == channel_id:
                        # Reset werewolf game in this channel
                        await werewolf_manager.remove_game(guild_id)
                        msg = "Đã huỷ bàn Ma Sói"
                        if isinstance(response_obj, commands.Context):
                            await response_obj.send(msg, delete_after=3)
                        else:
                            await response_obj.followup.send(msg)
                        return
            
            # Check for Tree channel
            # Postgres: $1 placeholder, fetchrow returns Row or None
            tree_row = await db_manager.fetchrow(
                "SELECT tree_channel_id, tree_message_id FROM server_tree WHERE guild_id = $1",
                (int(guild_id),)
            )
            
            noitu_row = await db_manager.fetchrow(
                "SELECT noitu_channel_id FROM server_config WHERE guild_id = $1", 
                (int(guild_id),)
            )
            
            # Check if current channel is tree channel
            if tree_row and tree_row['tree_channel_id'] and channel_id == tree_row['tree_channel_id']:
                # This is the tree channel - refresh the tree message
                tree_cog = self.bot.get_cog("Tree")
                if tree_cog:
                    # Delete old pinned message if it exists
                    if tree_row['tree_message_id']:
                        try:
                            channel = self.bot.get_channel(tree_row['tree_channel_id'])
                            if channel:
                                message = await channel.fetch_message(tree_row['tree_message_id'])
                                if message:
                                    await message.delete()
                        except Exception as e:
                            logger.error(f"Unexpected error: {e}")
                    
                    # Create and pin new message with same data
                    await tree_cog.update_or_create_pin_message(guild_id, tree_row['tree_channel_id'])
                    msg = "Đã làm mới tin nhắn cây"
                else:
                    msg = "Ko tìm thấy tree cog"
                
                if isinstance(response_obj, commands.Context):
                    await response_obj.send(msg, delete_after=3)
                else:
                    await response_obj.followup.send(msg)
                return
            
            # Check for NoiTu game in current channel
            if not noitu_row or not noitu_row['noitu_channel_id']:
                msg = "Kênh này ko có game nào hoạt động"
                if isinstance(response_obj, commands.Context):
                    await response_obj.send(msg, delete_after=3)
                else:
                    await response_obj.followup.send(msg)
                return

            noitu_channel_id = noitu_row['noitu_channel_id']

            # Check if current channel matches noitu game channel
            if channel_id == noitu_channel_id:
                # Reset nối từ game
                game_cog = self.bot.get_cog("GameNoiTu")
                if game_cog:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await game_cog.start_new_round(guild_id, channel)
                        msg = "Đã reset game nối từ"
                    else:
                        msg = "Ko tìm thấy kênh"
                else:
                    msg = "Ko tìm thấy game cog"
            else:
                msg = "Ko có game nào hoạt động trong kênh này"

            # Send response
            if isinstance(response_obj, commands.Context):
                await response_obj.send(msg, delete_after=3)
            else:
                await response_obj.followup.send(msg)

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"❌ Lỗi: {str(e)}"
            if isinstance(response_obj, commands.Context):
                await response_obj.send(error_msg)
            else:
                await response_obj.followup.send(error_msg)

    @config_group.command(name="set", description="Cài đặt các kênh chức năng (Admin Only)")
    @app_commands.describe(
        kenh_noitu="Kênh chơi nối từ (Game Channel)",
        kenh_logs="Kênh ghi log admin (Log Channel)",
        kenh_cay="Kênh trồng cây server (Tree Channel)",
        kenh_fishing="Kênh thông báo sự kiện câu cá (Fishing Channel)",
        kenh_bump="Kênh nhắc bump Disboard",
        kenh_log_bot="Kênh gửi log lỗi bot lên Discord",
        log_ping_user="Người nhận ping khi có lỗi ERROR/CRITICAL",
        log_level="Mức độ log gửi lên Discord (INFO/WARNING/ERROR/CRITICAL)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set(self, interaction: discord.Interaction, 
                         kenh_noitu: discord.TextChannel = None, 
                         kenh_logs: discord.TextChannel = None,
                         kenh_cay: discord.TextChannel = None,
                         kenh_fishing: discord.TextChannel = None,
                         kenh_bump: discord.TextChannel = None,
                         kenh_log_bot: discord.TextChannel = None,
                         log_ping_user: discord.Member = None,
                         log_level: str = None):
        
        # 1. Check permission
        if not interaction.user.guild_permissions.administrator:
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.errors.NotFound:
                return
            return await interaction.followup.send("Ko có quyền admin để dùng lệnh này")
        
        # 2. Defer ngay lập tức để tránh timeout 3s
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            return

        if not any([kenh_noitu, kenh_logs, kenh_cay, kenh_fishing, kenh_bump, kenh_log_bot, log_ping_user, log_level]):
            return await interaction.followup.send("Ko nhập thay đổi gì cả")

        try:
            guild_id = interaction.guild.id
            
            print(f"CONFIG [Guild {guild_id}] Setting channels")
            # Postgres: No context manager needed for updates
            
            # Get old config
            row = await db_manager.fetchrow(
                "SELECT logs_channel_id, noitu_channel_id, fishing_channel_id FROM server_config WHERE guild_id = $1", 
                (int(guild_id),)
            )
            old_logs = row['logs_channel_id'] if row else None
            old_noitu = row['noitu_channel_id'] if row else None
            old_fishing = row['fishing_channel_id'] if row else None

            # Merge
            new_logs = kenh_logs.id if kenh_logs else old_logs
            new_noitu = kenh_noitu.id if kenh_noitu else old_noitu
            new_fishing = kenh_fishing.id if kenh_fishing else old_fishing
            
            # Handle tree channel
            if kenh_cay:
                new_tree = kenh_cay.id
                
                # Get tree cog
                tree_cog = self.bot.get_cog("Tree")
                if tree_cog:
                    # Create or update pinned message
                    await tree_cog.update_or_create_pin_message(guild_id, kenh_cay.id)
            else:
                new_tree = None
            
            # Save using UPSERT
            from datetime import datetime
            
            # Prepare bump_start_time for new bump channel
            bump_start_time = datetime.now() if kenh_bump else None
            new_bump = kenh_bump.id if kenh_bump else None
            new_log_bot = kenh_log_bot.id if kenh_log_bot else None
            new_ping_user = log_ping_user.id if log_ping_user else None
            new_log_level = log_level.upper() if log_level else None
            
            # Postgres UPSERT syntax
            # Note: Postgres doesn't support 'CASE WHEN excluded.bump_channel_id ...' inside ON CONFLICT DO UPDATE cleanly alias 
            # as SQLite does if referencing `excluded` in complex ways without strict typing.
            # But the syntax is generally compatible.
            # However, `bump_start_time` logic:
            # CASE WHEN excluded.bump_channel_id IS NOT NULL THEN excluded.bump_start_time ELSE server_config.bump_start_time END
            
            await db_manager.execute("""
                INSERT INTO server_config (
                    guild_id, logs_channel_id, noitu_channel_id, fishing_channel_id, 
                    bump_channel_id, bump_start_time, log_discord_channel_id, 
                    log_ping_user_id, log_discord_level
                ) 
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT(guild_id) DO UPDATE SET
                    logs_channel_id = COALESCE(EXCLUDED.logs_channel_id, server_config.logs_channel_id),
                    noitu_channel_id = COALESCE(EXCLUDED.noitu_channel_id, server_config.noitu_channel_id),
                    fishing_channel_id = COALESCE(EXCLUDED.fishing_channel_id, server_config.fishing_channel_id),
                    bump_channel_id = COALESCE(EXCLUDED.bump_channel_id, server_config.bump_channel_id),
                    bump_start_time = CASE WHEN EXCLUDED.bump_channel_id IS NOT NULL THEN EXCLUDED.bump_start_time ELSE server_config.bump_start_time END,
                    log_discord_channel_id = COALESCE(EXCLUDED.log_discord_channel_id, server_config.log_discord_channel_id),
                    log_ping_user_id = COALESCE(EXCLUDED.log_ping_user_id, server_config.log_ping_user_id),
                    log_discord_level = COALESCE(EXCLUDED.log_discord_level, server_config.log_discord_level)
            """, (
                int(guild_id), new_logs, new_noitu, new_fishing, new_bump, 
                bump_start_time, new_log_bot, new_ping_user, new_log_level
            ))
            
            if kenh_cay:
                # UPSERT for server_tree
                await db_manager.execute("""
                    INSERT INTO server_tree (guild_id, tree_channel_id)
                    VALUES ($1, $2)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        tree_channel_id = EXCLUDED.tree_channel_id
                """, (int(guild_id), kenh_cay.id))
            
            print(f"CONFIG_SAVED [Guild {guild_id}]")

            msg = "✅ Setup ok:\n"
            if kenh_noitu: msg += f"📝 Nối Từ: {kenh_noitu.mention}\n"
            if kenh_logs: msg += f"📋 Logs Admin: {kenh_logs.mention}\n"
            if kenh_cay: msg += f"🌳 Cây: {kenh_cay.mention}\n"
            if kenh_fishing: msg += f"🎣 Câu Cá: {kenh_fishing.mention}\n"
            if kenh_bump: msg += f"⏰ Bump Disboard: {kenh_bump.mention}\n"
            if kenh_log_bot: msg += f"🤖 Log Bot: {kenh_log_bot.mention}\n"
            if log_ping_user: msg += f"🔔 Ping User: {log_ping_user.mention}\n"
            if log_level: msg += f"📊 Log Level: {log_level.upper()}\n"
            
            await interaction.followup.send(msg)
            
            # Reload Discord Logger if any log setting changed
            if kenh_log_bot or log_ping_user or log_level:
                try:
                    from core.logger import attach_discord_handler, get_log_config_from_db
                    channel_id, ping_user_id, level = await get_log_config_from_db(guild_id)
                    if channel_id > 0:
                        attach_discord_handler(self.bot, channel_id, ping_user_id, level)
                        print(f"[CONFIG] Discord logger: channel={channel_id}, ping={ping_user_id}, level={level}")
                except Exception as e:
                    print(f"[CONFIG] Failed to attach Discord logger: {e}")

            # Reload Game
            if kenh_noitu:
                game_cog = self.bot.get_cog("GameNoiTu")
                if game_cog:
                    # Stop old game if channel changed
                    if old_noitu and old_noitu != kenh_noitu.id:
                        if guild_id in game_cog.games:
                            del game_cog.games[guild_id]
                            # Also clean up lock
                            if guild_id in game_cog.game_locks:
                                del game_cog.game_locks[guild_id]
                            print(f"GAME_STOP [Guild {guild_id}] Stopped old game at channel {old_noitu}")
                    
                    # Start new game
                    await game_cog.start_new_round(guild_id, kenh_noitu)
                    print(f"GAME_START [Guild {guild_id}] Started new game at channel {kenh_noitu.id}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Lỗi: {str(e)}")

    # --- Prefix commands for easier access ---
    @commands.command(name="config", description="Cài đặt các kênh chức năng")
    @commands.has_permissions(administrator=True)
    async def config_prefix(self, ctx, key: str = None, channel: discord.TextChannel = None):
        """Configure channels via prefix command.
        
        Usage:
            !config kenh_noitu #channel
            !config kenh_logs #channel
        """
        if not key:
            msg = "**Các option cấu hình:**\n"
            msg += "• `!config kenh_noitu #channel` - Kênh chơi nối từ\n"
            msg += "• `!config kenh_logs #channel` - Kênh logs (admin channel)\n"
            msg += "• `!config kenh_fishing #channel` - Kênh thông báo sự kiện câu cá\n"
            await ctx.send(msg)
            return
        
        if not channel:
            await ctx.send("❌ Vui lòng chỉ định kênh: `!config kenh_noitu #channel`")
            return
        
        guild_id = ctx.guild.id
        
        try:
            # Get current config
            row = await db_manager.fetchrow(
                "SELECT logs_channel_id, noitu_channel_id, fishing_channel_id FROM server_config WHERE guild_id = $1", 
                (int(guild_id),)
            )
            
            current_logs = row['logs_channel_id'] if row else None
            current_noitu = row['noitu_channel_id'] if row else None
            current_fishing = row['fishing_channel_id'] if row else None
            
            # Update based on key
            if key == "kenh_noitu":
                new_logs, new_noitu, new_fishing = current_logs, channel.id, current_fishing
                msg_key = "Nối Từ"
            elif key == "kenh_logs":
                new_logs, new_noitu, new_fishing = channel.id, current_noitu, current_fishing
                msg_key = "Logs"
            elif key == "kenh_fishing":
                new_logs, new_noitu, new_fishing = current_logs, current_noitu, channel.id
                msg_key = "Câu Cá"
            else:
                await ctx.send(f"❌ Option không hợp lệ: {key}. Dùng: kenh_noitu, kenh_logs, kenh_fishing")
                return
            
            # Save using UPSERT to preserve other columns (bump_channel_id, exclude_chat, etc.)
            await db_manager.execute("""
                INSERT INTO server_config (guild_id, logs_channel_id, noitu_channel_id, fishing_channel_id) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT(guild_id) DO UPDATE SET
                    logs_channel_id = EXCLUDED.logs_channel_id,
                    noitu_channel_id = EXCLUDED.noitu_channel_id,
                    fishing_channel_id = EXCLUDED.fishing_channel_id
            """, (int(guild_id), new_logs, new_noitu, new_fishing))
            
            # Get channel mention for confirmation
            channel_mention = f"<#{channel.id}>"
            
            await ctx.send(f"✅ **{msg_key}** được đặt thành {channel_mention}")
            print(f"CONFIG [Guild {guild_id}] Set {key} to {channel_mention}")
            
            # Start game if setting kenh_noitu
            if key == "kenh_noitu":
                game_cog = self.bot.get_cog("GameNoiTu")
                if game_cog:
                    # Stop old game if channel changed
                    if current_noitu and current_noitu != channel.id:
                        if guild_id in game_cog.games:
                            del game_cog.games[guild_id]
                            # Also clean up lock
                            if guild_id in game_cog.game_locks:
                                del game_cog.game_locks[guild_id]
                            print(f"GAME_STOP [Guild {guild_id}] Stopped old game at channel {current_noitu}")
                    
                    # Start new game
                    await game_cog.start_new_round(guild_id, channel)
                    print(f"GAME_START [Guild {guild_id}] Started new game at channel {channel.id}")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ Lỗi: {str(e)}")

    # ==================== EXCLUDE CHANNELS ====================

    @app_commands.command(name="exclude", description="Quản lý kênh không nhận seed từ chat")
    @app_commands.describe(
        action="add (thêm) hoặc remove (xoá)",
        channel="Kênh muốn thêm/xoá"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def exclude_channel(self, interaction: discord.Interaction, action: str, channel: discord.TextChannel):
        """Add or remove channel from chat reward exclusion list"""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction already timed out, cannot respond
            return
        
        action = action.lower()
        if action not in ["add", "remove"]:
            await interaction.followup.send("❌ Action phải là 'add' hoặc 'remove'", ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        
        try:
            # Get current exclude list
            row = await db_manager.fetchrow(
                "SELECT exclude_chat_channels FROM server_config WHERE guild_id = $1",
                (int(guild_id),)
            )
            
            excluded = []
            if row and row['exclude_chat_channels']:
                try:
                    excluded = json.loads(row['exclude_chat_channels'])
                except Exception as e:
                    excluded = []
            
            if action == "add":
                if channel.id in excluded:
                    await interaction.followup.send(
                        f"⚠️ Kênh {channel.mention} đã trong danh sách loại trừ rồi",
                        ephemeral=True
                    )
                    return
                
                excluded.append(channel.id)
                msg = f"✅ Thêm {channel.mention} vào danh sách loại trừ"
            
            else:  # remove
                if channel.id not in excluded:
                    await interaction.followup.send(
                        f"⚠️ Kênh {channel.mention} không trong danh sách loại trừ",
                        ephemeral=True
                    )
                    return
                
                excluded.remove(channel.id)
                msg = f"✅ Xoá {channel.mention} khỏi danh sách loại trừ"
            
            # Update database
            # Postgres: UPSERT or UPDATE
            # Since server_config might not exist, we should use UPSERT (INSERT ... ON CONFLICT)
            await db_manager.execute("""
                INSERT INTO server_config (guild_id, exclude_chat_channels) VALUES ($1, $2)
                ON CONFLICT(guild_id) DO UPDATE SET exclude_chat_channels = EXCLUDED.exclude_chat_channels
            """, (int(guild_id), json.dumps(excluded)))
            
            await interaction.followup.send(msg, ephemeral=True)
            print(f"[EXCLUDE] {interaction.user.name} {action}ed {channel.name}")
        
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ Lỗi: {str(e)}", ephemeral=True)

    @app_commands.command(name="exclude_list", description="Xem danh sách kênh loại trừ")
    async def exclude_list(self, interaction: discord.Interaction):
        """Show excluded channels list"""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction already timed out, cannot respond
            return
        
        guild_id = interaction.guild.id
        
        try:
            row = await db_manager.fetchrow(
                "SELECT exclude_chat_channels FROM server_config WHERE guild_id = $1",
                (int(guild_id),)
            )
            
            excluded = []
            if row and row['exclude_chat_channels']:
                try:
                    excluded = json.loads(row['exclude_chat_channels'])
                except Exception as e:
                    excluded = []
            
            embed = discord.Embed(
                title="🚫 Danh sách kênh loại trừ (không nhận seed)",
                color=discord.Color.red()
            )
            
            if not excluded:
                embed.description = "Không có kênh nào bị loại trừ"
            else:
                channels_text = ""
                for channel_id in excluded:
                    channel = interaction.guild.get_channel(channel_id)
                    if channel:
                        channels_text += f"• {channel.mention}\n"
                    else:
                        channels_text += f"• ❌ Kênh ID: {channel_id} (không tìm thấy)\n"
                
                embed.description = channels_text
            
            embed.set_footer(text="Dùng /exclude add/remove để quản lý")
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ Lỗi: {str(e)}", ephemeral=True)
    

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
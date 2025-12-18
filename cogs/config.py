import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import traceback
import json

DB_PATH = "./data/database.db"
class ApprovalView(discord.ui.View):
    def __init__(self, bot, word, suggester_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.word = word
        self.suggester_id = suggester_id

    @discord.ui.button(label="Duyệt", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("INSERT OR IGNORE INTO dictionary (word) VALUES (?)", (self.word,))
            except: pass
            await db.execute("DELETE FROM pending_words WHERE word = ?", (self.word,))
            await db.commit()
        
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
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM pending_words WHERE word = ?", (self.word,))
            await db.commit()
        
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
                game = werewolf_manager.get_game(guild_id)
                
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
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT tree_channel_id, tree_message_id FROM server_tree WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    tree_row = await cursor.fetchone()
                
                async with db.execute(
                    "SELECT noitu_channel_id FROM server_config WHERE guild_id = ?", 
                    (guild_id,)
                ) as cursor:
                    noitu_row = await cursor.fetchone()
            
            # Check if current channel is tree channel
            if tree_row and tree_row[0] and channel_id == tree_row[0]:
                # This is the tree channel - refresh the tree message
                tree_cog = self.bot.get_cog("CommunityCog")
                if tree_cog:
                    # Delete old pinned message if it exists
                    if tree_row[1]:
                        try:
                            channel = self.bot.get_channel(tree_row[0])
                            if channel:
                                message = await channel.fetch_message(tree_row[1])
                                if message:
                                    await message.delete()
                        except:
                            pass
                    
                    # Create and pin new message with same data
                    await tree_cog.update_or_create_pin_message(guild_id, tree_row[0])
                    msg = "Đã làm mới tin nhắn cây"
                else:
                    msg = "Ko tìm thấy tree cog"
                
                if isinstance(response_obj, commands.Context):
                    await response_obj.send(msg, delete_after=3)
                else:
                    await response_obj.followup.send(msg)
                return
            
            # Check for NoiTu game in current channel
            if not noitu_row or not noitu_row[0]:
                msg = "Kênh này ko có game nào hoạt động"
                if isinstance(response_obj, commands.Context):
                    await response_obj.send(msg, delete_after=3)
                else:
                    await response_obj.followup.send(msg)
                return

            noitu_channel_id = noitu_row[0]

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
        kenh_logs="Kênh ghi log (Log Channel)",
        kenh_soi="Kênh voice họp sói (Wolf Voice Channel)",
        kenh_cay="Kênh trồng cây server (Tree Channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set(self, interaction: discord.Interaction, 
                         kenh_noitu: discord.TextChannel = None, 
                         kenh_logs: discord.TextChannel = None,
                         kenh_soi: discord.VoiceChannel = None,
                         kenh_cay: discord.TextChannel = None):
        
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

        if not any([kenh_noitu, kenh_logs, kenh_soi, kenh_cay]):
            return await interaction.followup.send("Ko nhập thay đổi gì cả")

        try:
            guild_id = interaction.guild.id
            
            print(f"CONFIG [Guild {guild_id}] Setting channels")
            async with aiosqlite.connect(DB_PATH) as db:
                # Get old config
                async with db.execute("SELECT logs_channel_id, noitu_channel_id, wolf_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                old_logs = row[0] if row else None
                old_noitu = row[1] if row else None
                old_wolf = row[2] if row else None

                # Merge
                new_logs = kenh_logs.id if kenh_logs else old_logs
                new_noitu = kenh_noitu.id if kenh_noitu else old_noitu
                new_wolf = kenh_soi.id if kenh_soi else old_wolf
                
                # Validate: một kênh không được có nhiều hơn 1 game
                if kenh_noitu and kenh_soi:
                    if kenh_noitu.id == kenh_soi.id:
                        return await interaction.followup.send("Kênh không được vừa là kênh Nối Từ vừa là kênh voice Sói")
                
                # Check if new_noitu conflicts with existing wolf channel
                if new_noitu and new_wolf and new_noitu == new_wolf:
                    return await interaction.followup.send("Kênh không được vừa là kênh Nối Từ vừa là kênh voice Sói")
                
                # If setting kenh_noitu to a channel that was wolf channel, clear wolf channel
                if kenh_noitu and new_wolf and kenh_noitu.id == new_wolf:
                    new_wolf = None
                    await interaction.followup.send("Kênh voice Sói đã bị xoá vì xung đột với kênh Nối Từ")
                
                # If setting kenh_soi to a channel that was noitu channel, clear noitu channel
                if kenh_soi and new_noitu and kenh_soi.id == new_noitu:
                    new_noitu = None
                    await interaction.followup.send("Kênh Nối Từ đã bị xoá vì xung đột với kênh voice Sói")
                
                # Handle tree channel
                if kenh_cay:
                    new_tree = kenh_cay.id
                    
                    # Get tree cog
                    tree_cog = self.bot.get_cog("CommunityCog")
                    if tree_cog:
                        # Create or update pinned message
                        await tree_cog.update_or_create_pin_message(guild_id, kenh_cay.id)
                else:
                    new_tree = None
                
                # Save
                await db.execute("UPDATE server_config SET logs_channel_id = ?, noitu_channel_id = ?, wolf_channel_id = ? WHERE guild_id = ?", 
                                 (new_logs, new_noitu, new_wolf, guild_id))
                
                if kenh_cay:
                    await db.execute("UPDATE server_tree SET tree_channel_id = ? WHERE guild_id = ?",
                                     (kenh_cay.id, guild_id))
                
                await db.commit()
                print(f"CONFIG_SAVED [Guild {guild_id}]")

            msg = "✅ Setup ok:\n"
            if kenh_noitu: msg += f"📝 Nối Từ: {kenh_noitu.mention}\n"
            if kenh_logs: msg += f"📋 Logs: {kenh_logs.mention}\n"
            if kenh_soi: msg += f"🐺 Sói Voice: {kenh_soi.mention}\n"
            if kenh_cay: msg += f"🌳 Cây: {kenh_cay.mention}\n"
            
            await interaction.followup.send(msg)

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
            !config kenh_soi #voice_channel (voice channel)
        """
        if not key:
            msg = "**Các option cấu hình:**\n"
            msg += "• `!config kenh_noitu #channel` - Kênh chơi nối từ\n"
            msg += "• `!config kenh_logs #channel` - Kênh logs (admin channel)\n"
            msg += "• `!config kenh_soi #voice_channel` - Kênh voice sói\n"
            await ctx.send(msg)
            return
        
        if not channel and key != "kenh_soi":
            await ctx.send("❌ Vui lòng chỉ định kênh: `!config kenh_noitu #channel`")
            return
        
        guild_id = ctx.guild.id
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Get current config
                async with db.execute("SELECT logs_channel_id, noitu_channel_id, wolf_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                
                current_logs = row[0] if row else None
                current_noitu = row[1] if row else None
                current_wolf = row[2] if row else None
                
                # Update based on key
                if key == "kenh_noitu":
                    # Check if this channel is already set as wolf channel
                    if current_wolf and channel.id == current_wolf:
                        await ctx.send("❌ Kênh này đang được dùng cho Ma Sói. Xoá kenh_soi trước!")
                        return
                    new_logs, new_noitu, new_wolf = current_logs, channel.id, current_wolf
                    msg_key = "Nối Từ"
                elif key == "kenh_logs":
                    new_logs, new_noitu, new_wolf = channel.id, current_noitu, current_wolf
                    msg_key = "Logs"
                elif key == "kenh_soi":
                    # Check if this channel is already set as noitu channel
                    if current_noitu:
                        try:
                            voice_channel = await commands.VoiceChannelConverter().convert(ctx, ctx.message.content.split()[-1])
                            if voice_channel.id == current_noitu:
                                await ctx.send("❌ Kênh này đang được dùng cho Nối Từ. Xoá kenh_noitu trước!")
                                return
                            new_logs, new_noitu, new_wolf = current_logs, current_noitu, voice_channel.id
                            msg_key = "Sói Voice"
                        except:
                            await ctx.send("❌ Kênh voice không hợp lệ. Dùng: `!config kenh_soi 1449580372705677312` (ID)")
                            return
                    else:
                        try:
                            voice_channel = await commands.VoiceChannelConverter().convert(ctx, ctx.message.content.split()[-1])
                            new_logs, new_noitu, new_wolf = current_logs, current_noitu, voice_channel.id
                            msg_key = "Sói Voice"
                        except:
                            await ctx.send("❌ Kênh voice không hợp lệ. Dùng: `!config kenh_soi 1449580372705677312` (ID)")
                            return
                else:
                    await ctx.send(f"❌ Option không hợp lệ: {key}. Dùng: kenh_noitu, kenh_logs, kenh_soi")
                    return
                
                # Save
                await db.execute("INSERT OR REPLACE INTO server_config (guild_id, logs_channel_id, noitu_channel_id, wolf_channel_id) VALUES (?, ?, ?, ?)", 
                                 (guild_id, new_logs, new_noitu, new_wolf))
                await db.commit()
                
                # Get channel mention for confirmation
                if key == "kenh_noitu":
                    channel_mention = f"<#{channel.id}>"
                elif key == "kenh_logs":
                    channel_mention = f"<#{channel.id}>"
                else:  # kenh_soi
                    channel_mention = f"<#{new_wolf}>"
                
                await ctx.send(f"✅ **{msg_key}** được đặt thành {channel_mention}")
                print(f"CONFIG [Guild {guild_id}] Set {key} to {channel_mention if key != 'kenh_soi' else new_wolf}")
                
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
            async with aiosqlite.connect(DB_PATH) as db:
                # Get current exclude list
                async with db.execute(
                    "SELECT exclude_chat_channels FROM server_config WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                
                excluded = []
                if row and row[0]:
                    try:
                        excluded = json.loads(row[0])
                    except:
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
                await db.execute(
                    "INSERT OR REPLACE INTO server_config (guild_id, exclude_chat_channels) VALUES (?, ?)",
                    (guild_id, json.dumps(excluded))
                )
                await db.commit()
                
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
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT exclude_chat_channels FROM server_config WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
            
            excluded = []
            if row and row[0]:
                try:
                    excluded = json.loads(row[0])
                except:
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
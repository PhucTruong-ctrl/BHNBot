import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite

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
        await interaction.response.defer(ephemeral=True)
        await self._handle_reset(interaction.guild_id, interaction.channel_id, interaction)

    # Prefix command: !reset
    @commands.command(name="reset", description="Reset game trong kênh hiện tại")
    async def reset_prefix(self, ctx):
        """Reset game in current channel"""
        await self._handle_reset(ctx.guild.id, ctx.channel.id, ctx)

    async def _handle_reset(self, guild_id, channel_id, response_obj):
        """Handle reset logic for both slash and prefix commands"""
        try:
            # Get all configured channels for this guild
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT noitu_channel_id FROM server_config WHERE guild_id = ?", 
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
            
            if not row or not row[0]:
                if isinstance(response_obj, commands.Context):
                    await response_obj.send("Ko có game nào setup ở server này")
                else:
                    await response_obj.followup.send("Ko có game nào setup ở server này")
                return

            noitu_channel_id = row[0]

            # Check if current channel matches any game channel
            if channel_id == noitu_channel_id:
                # Reset nối từ game
                game_cog = self.bot.get_cog("GameNoiTu")
                if game_cog:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await game_cog.start_new_round(guild_id, channel)
                        msg = "Reset game nối từ ok"
                    else:
                        msg = "Ko tìm thấy kênh"
                else:
                    msg = "Ko tìm thấy game cog"
            else:
                msg = "Kênh này ko có game nào"

            # Send response
            if isinstance(response_obj, commands.Context):
                await response_obj.send(msg, delete_after=3)
            else:
                await response_obj.followup.send(msg, delete_after=3)

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"Lỗi: {str(e)}"
            if isinstance(response_obj, commands.Context):
                await response_obj.send(error_msg)
            else:
                await response_obj.followup.send(error_msg)

    @config_group.command(name="set", description="Thiet lap cac kenh chuc nang (Admin Only)")
    @app_commands.describe(
        kenh_noitu="Kenh choi noi tu (Game Channel)",
        kenh_admin="Kenh thong bao duyet tu (Admin Channel)",
        kenh_giveaway="Kenh thong bao Giveaway",
        kenh_soi="Kenh hop soi (Wolf Meeting Channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set(self, interaction: discord.Interaction, 
                         kenh_noitu: discord.TextChannel = None, 
                         kenh_admin: discord.TextChannel = None,
                         kenh_giveaway: discord.TextChannel = None,
                         kenh_soi: discord.TextChannel = None):
        
        # 1. Check permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.defer(ephemeral=True)
            return await interaction.followup.send("Ko có quyền admin để dùng lệnh này")
        
        # 2. Defer ngay lập tức để tránh timeout 3s
        await interaction.response.defer(ephemeral=True)

        if not any([kenh_noitu, kenh_admin, kenh_giveaway, kenh_soi]):
            return await interaction.followup.send("Ko nhập thay đổi gì cả")

        try:
            guild_id = interaction.guild.id
            
            print(f"CONFIG [Guild {guild_id}] Setting channels")
            async with aiosqlite.connect(DB_PATH) as db:
                # Get old config
                async with db.execute("SELECT admin_channel_id, noitu_channel_id, wolf_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                old_admin = row[0] if row else None
                old_noitu = row[1] if row else None
                old_wolf = row[2] if row else None

                # Merge
                new_admin = kenh_admin.id if kenh_admin else old_admin
                new_noitu = kenh_noitu.id if kenh_noitu else old_noitu
                new_wolf = kenh_soi.id if kenh_soi else old_wolf
                
                # Save
                await db.execute("INSERT OR REPLACE INTO server_config (guild_id, admin_channel_id, noitu_channel_id, wolf_channel_id) VALUES (?, ?, ?, ?)", 
                                 (guild_id, new_admin, new_noitu, new_wolf))
                await db.commit()
                print(f"CONFIG_SAVED [Guild {guild_id}]")

            msg = "Setup ok:\n"
            if kenh_noitu: msg += f"- Noi Tu: {kenh_noitu.mention}\n"
            if kenh_admin: msg += f"- Admin: {kenh_admin.mention}\n"
            if kenh_soi: msg += f"- Wolf Meeting: {kenh_soi.mention}\n"
            
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
            await interaction.followup.send(f"Lỗi: {str(e)}")

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
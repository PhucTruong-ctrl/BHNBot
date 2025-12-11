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

    reset_group = app_commands.Group(name="reset", description="Reset các trò chơi")

    @reset_group.command(name="noitu", description="Reset game noi tu sang tu khac")
    async def reset_noitu(self, interaction: discord.Interaction):
        """Reset word chain game - no admin required"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_id = interaction.guild.id
            
            # Get current game config
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT noitu_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    row = await cursor.fetchone()
            
            if not row or not row[0]:
                return await interaction.followup.send("Chưa setup kênh nối từ, dùng /config set trước")
            
            channel = self.bot.get_channel(row[0])
            if not channel:
                return await interaction.followup.send("Ko tìm thấy kênh nối từ")
            
            # Reset game
            game_cog = self.bot.get_cog("GameNoiTu")
            if game_cog:
                await game_cog.start_new_round(guild_id, channel)
                await interaction.followup.send(f"Reset game ok, check {channel.mention}")
            else:
                await interaction.followup.send("Lỗi: Ko tìm thấy game cog")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"Lỗi: {str(e)}")

    @config_group.command(name="set", description="Thiet lap cac kenh chuc nang (Admin Only)")
    @app_commands.describe(
        kenh_noitu="Kenh choi noi tu (Game Channel)",
        kenh_admin="Kenh thong bao duyet tu (Admin Channel)",
        kenh_giveaway="Kenh thong bao Giveaway"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set(self, interaction: discord.Interaction, 
                         kenh_noitu: discord.TextChannel = None, 
                         kenh_admin: discord.TextChannel = None,
                         kenh_giveaway: discord.TextChannel = None):
        
        # 1. Check permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.defer(ephemeral=True)
            return await interaction.followup.send("Ko có quyền admin để dùng lệnh này")
        
        # 2. Defer ngay lập tức để tránh timeout 3s
        await interaction.response.defer(ephemeral=True)

        if not any([kenh_noitu, kenh_admin, kenh_giveaway]):
            return await interaction.followup.send("Ko nhập thay đổi gì cả")

        try:
            guild_id = interaction.guild.id
            
            print(f"CONFIG [Guild {guild_id}] Setting channels")
            async with aiosqlite.connect(DB_PATH) as db:
                # Get old config
                async with db.execute("SELECT admin_channel_id, noitu_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                old_admin = row[0] if row else None
                old_noitu = row[1] if row else None

                # Merge
                new_admin = kenh_admin.id if kenh_admin else old_admin
                new_noitu = kenh_noitu.id if kenh_noitu else old_noitu
                
                # Save
                await db.execute("INSERT OR REPLACE INTO server_config (guild_id, admin_channel_id, noitu_channel_id) VALUES (?, ?, ?)", 
                                 (guild_id, new_admin, new_noitu))
                await db.commit()
                print(f"CONFIG_SAVED [Guild {guild_id}]")

            msg = "Setup ok:\n"
            if kenh_noitu: msg += f"- Noi Tu: {kenh_noitu.mention}\n"
            if kenh_admin: msg += f"- Admin: {kenh_admin.mention}\n"
            
            await interaction.followup.send(msg)

            # Reload Game
            if kenh_noitu:
                game_cog = self.bot.get_cog("GameNoiTu")
                if game_cog:
                    await game_cog.start_new_round(guild_id, kenh_noitu)
                    print(f"GAME_RELOAD [Guild {guild_id}]")

        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"Lỗi: {str(e)}")

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
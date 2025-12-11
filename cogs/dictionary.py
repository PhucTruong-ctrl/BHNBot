import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite

DB_PATH = "./data/database.db"

# View for Approval Buttons
class ApprovalView(discord.ui.View):
    def __init__(self, bot, word, suggester_id):
        super().__init__(timeout=None) # Buttons never expire
        self.bot = bot
        self.word = word
        self.suggester_id = suggester_id

    @discord.ui.button(label="Duyệt", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic: Move from pending to dictionary
        async with aiosqlite.connect(DB_PATH) as db:
            # 1. Add to dictionary
            try:
                await db.execute("INSERT OR IGNORE INTO dictionary (word) VALUES (?)", (self.word,))
            except:
                pass # Already exists
            
            # 2. Remove from pending
            await db.execute("DELETE FROM pending_words WHERE word = ?", (self.word,))
            await db.commit()
        
        # Update Admin Message
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Trạng thái", value=f"Đã được duyệt bởi {interaction.user.mention}")
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Notify User (Optional)
        try:
            user = await self.bot.fetch_user(self.suggester_id)
            await user.send(f"Từ **{self.word}** bạn đóng góp đã được Admin duyệt! Cảm ơn bạn đã góp phần làm phong phú từ điển!")
        except:
            pass

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger, emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM pending_words WHERE word = ?", (self.word,))
            await db.commit()
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Trạng thái", value=f"Đã bị từ chối bởi {interaction.user.mention}")
        
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)

class DictionaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Group command /config
    config_group = app_commands.Group(name="config", description="Cấu hình bot")

    @config_group.command(name="channel", description="Chọn kênh để nhận thông báo duyệt từ")
    @app_commands.describe(channel="Kênh text để gửi yêu cầu duyệt")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO server_config (guild_id, admin_channel_id) VALUES (?, ?)", 
                             (interaction.guild.id, channel.id))
            await db.commit()
        
        await interaction.response.send_message(f"Đã cấu hình kênh duyệt từ là: {channel.mention}", ephemeral=True)

    @app_commands.command(name="themtu", description="Góp ý thêm từ mới vào từ điển")
    @app_commands.describe(word="Từ bạn muốn thêm (Ví dụ: xe đạp)")
    async def suggest_word(self, interaction: discord.Interaction, word: str):
        clean_word = word.strip().lower()
        
        # Basic validation
        if len(clean_word.split()) != 2:
             return await interaction.response.send_message("Chỉ chấp nhận từ ghép có đúng 2 âm tiết (VD: nhà cửa).", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            # 1. Check dictionary
            async with db.execute("SELECT 1 FROM dictionary WHERE word = ?", (clean_word,)) as cursor:
                if await cursor.fetchone():
                    return await interaction.response.send_message(f"Từ **{clean_word}** đã có trong từ điển rồi!", ephemeral=True)
            
            # 2. Check pending
            try:
                await db.execute("INSERT INTO pending_words (word, user_id) VALUES (?, ?)", (clean_word, interaction.user.id))
                await db.commit()
            except:
                return await interaction.response.send_message("Từ này đang chờ duyệt rồi!", ephemeral=True)
            
            # 3. Get Admin Channel
            async with db.execute("SELECT admin_channel_id FROM server_config WHERE guild_id = ?", (interaction.guild.id,)) as cursor:
                row = await cursor.fetchone()
                channel_id = row[0] if row else None

        # Reply to user
        await interaction.response.send_message(f"Đã gửi yêu cầu thêm từ **{clean_word}**. Cảm ơn bạn nha!", ephemeral=True)

        # Send to Admin Channel
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(title="Yêu cầu thêm từ mới", color=discord.Color.gold())
                embed.add_field(name="Từ vựng", value=f"**{clean_word}**", inline=False)
                embed.add_field(name="Người đề xuất", value=interaction.user.mention, inline=False)
                
                view = ApprovalView(self.bot, clean_word, interaction.user.id)
                await channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(DictionaryCog(bot))
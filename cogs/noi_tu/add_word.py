import discord
from discord import app_commands
from discord.ext import commands
import json
import tempfile
import shutil
import os
from database_manager import get_server_config

from core.logging import get_logger
logger = get_logger("noi_tu")


DB_PATH = "./data/database.db"
WORDS_DICT_PATH = "./data/words_dict.json"
TU_DIEN_PATH = "./data/tu_dien.txt"

def add_word_to_tu_dien(word: str):
    """Add word to tu_dien.txt file for persistence"""
    try:
        with open(TU_DIEN_PATH, "a", encoding="utf-8") as f:
            f.write(f'{{"text": "{word}", "source": ["user_added"]}}\n')
        logger.debug("[add_word]_added_to_tu_dien.tx", word=word)
    except Exception as e:
        logger.debug("[add_word]_error_adding_to_tu_", e=e)

class QuickAddWordView(discord.ui.View):
    """Quick add word view for game players - 25s timeout"""
    def __init__(self, word, proposer_user, bot):
        super().__init__(timeout=25)
        self.word = word
        self.proposer_user = proposer_user
        self.bot = bot
    
    @discord.ui.button(label="Thêm từ", style=discord.ButtonStyle.blurple)
    async def quick_add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow the proposer to click
        if interaction.user.id != self.proposer_user.id:
            await interaction.response.send_message("Chỉ người nhắn mới có thể bấm nút này", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Load words dictionary to check if word already exists
            with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                words_dict = json.load(f)
            
            first, second = self.word.split()
            
            # Check if word already exists
            if first in words_dict and second in words_dict[first]:
                await interaction.followup.send(f"Từ `{self.word}` đã có sẵn trong từ điển", ephemeral=True)
                return
            
            # Check if user is admin - if so, add directly without approval
            if interaction.user.guild_permissions.administrator:
                # Add word directly
                if first not in words_dict:
                    words_dict[first] = []
                
                if second not in words_dict[first]:
                    words_dict[first].append(second)
                    
                    # Atomic write to words_dict.json
                    try:
                        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=os.path.dirname(WORDS_DICT_PATH)) as tmp:
                            json.dump(words_dict, tmp, ensure_ascii=False, indent=2)
                            tmp_path = tmp.name
                        shutil.move(tmp_path, WORDS_DICT_PATH)
                    except Exception as e:
                        logger.debug("[add_word]_error_writing_to_fi", e=e)
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                        raise
                    
                    # Also add to tu_dien.txt for persistence
                    add_word_to_tu_dien(self.word)
                    
                    # Reload dictionary in NoiTu cog
                    try:
                        from cogs.noitu import GameNoiTu
                        noitu_cog = interaction.client.get_cog("GameNoiTu")
                        if noitu_cog:
                            await noitu_cog.reload_words_dict()
                            logger.debug("[add_word]_dictionary_reloaded")
                    except Exception as e:
                        logger.warning("dictionary_reload_failed", error=str(e))
                    
                    await interaction.followup.send(f"Từ `{self.word}` đã được thêm vào từ điển (admin auto-approve)", ephemeral=True)
                    logger.debug("[add_word]_admin_auto_approve", username=interaction.user.name)
                else:
                    await interaction.followup.send(f"Từ `{self.word}` đã tồn tại", ephemeral=True)
                return
            
            # Get admin channel from config
            logs_channel_id = await get_server_config(interaction.guild.id, "logs_channel_id")
            
            if not logs_channel_id:
                await interaction.followup.send("Kênh admin chưa được cấu hình", ephemeral=True)
                return
            
            admin_channel = self.bot.get_channel(row[0])
            if not admin_channel:
                await interaction.followup.send("Kênh admin không tìm thấy", ephemeral=True)
                return
            
            # Create embed for admin review
            embed = discord.Embed(
                title="Yêu cầu thêm từ mới cho nối từ",
                description=f"Từ: **{self.word}**\nNgười đề xuất: **{self.proposer_user.mention}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"User ID: {self.proposer_user.id}")
            
            # Send to admin channel with approval buttons
            view = PendingWordView(self.proposer_user.id, self.word, self.proposer_user.mention, admin_channel)
            await admin_channel.send(embed=embed, view=view)
            
            await interaction.followup.send(f"Từ `{self.word}` đã được gửi tới admin phê duyệt", ephemeral=True)
            logger.debug("[add_word]_proposed_word", proposer=self.proposer_user.name)
            
        except Exception as e:
            await interaction.followup.send(f"Lỗi: {e}", ephemeral=True)
            logger.debug("[add_word]_error_quick_adding_", e=e)
    
    async def on_timeout(self):
        # Disable button on timeout
        for item in self.children:
            item.disabled = True

class PendingWordView(discord.ui.View):
    def __init__(self, user_id, word, proposer_mention, admin_channel):
        super().__init__(timeout=3600)  # 1 hour for admin review
        self.user_id = user_id
        self.word = word
        self.proposer_mention = proposer_mention
        self.admin_channel = admin_channel
    
    @discord.ui.button(label="Thêm", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Ko có quyền", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Add word to words_dict.json
        try:
            with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                words_dict = json.load(f)
            
            # Normalize to lowercase
            word_normalized = self.word.lower().strip()
            first, second = word_normalized.split()
            
            if first not in words_dict:
                words_dict[first] = []
            
            if second not in words_dict[first]:
                words_dict[first].append(second)
                
                # Atomic write: write to temp file first, then move
                try:
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=os.path.dirname(WORDS_DICT_PATH)) as tmp:
                        json.dump(words_dict, tmp, ensure_ascii=False, indent=2)
                        tmp_path = tmp.name
                    shutil.move(tmp_path, WORDS_DICT_PATH)
                except Exception as e:
                    logger.debug("[add_word]_error_writing_to_fi", e=e)
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    raise
                
                # Also add to tu_dien.txt for persistence
                add_word_to_tu_dien(word_normalized)
                
                # Reload dictionary in NoiTu cog
                try:
                    from cogs.noitu import GameNoiTu
                    noitu_cog = interaction.client.get_cog("GameNoiTu")
                    if noitu_cog:
                        await noitu_cog.reload_words_dict()
                        logger.debug("[add_word]_dictionary_reloaded")
                except Exception as e:
                    logger.warning("dictionary_reload_failed", error=str(e))
                
                # Disable button
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)
                
                # Notify in admin channel
                embed = discord.Embed(
                    title="Từ này đã được thêm vào",
                    description=f"**Từ:** {word_normalized}\n**Người đề xuất:** {self.proposer_mention}",
                    color=discord.Color.green()
                )
                await self.admin_channel.send(embed=embed)
                
                logger.debug("[add_word]_added_word_''_from_", word_normalized=word_normalized)
            else:
                # Disable button
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)
                
                embed = discord.Embed(
                    title="Từ này đã tồn tại",
                    description=f"**Từ:** {self.word}\n**Người đề xuất:** {self.proposer_mention}",
                    color=discord.Color.orange()
                )
                await self.admin_channel.send(embed=embed)
                
        except Exception as e:
            await interaction.message.reply(f"Lỗi: {e}")
            logger.debug("[add_word]_error:_", e=e)
    
    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Ko có quyền", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Disable button
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Notify in admin channel
        embed = discord.Embed(
            title="Từ này đã bị từ chối",
            description=f"**Từ:** {self.word}\n**Người đề xuất:** {self.proposer_mention}",
            color=discord.Color.red()
        )
        await self.admin_channel.send(embed=embed)

class AddWordCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="themtu")
    async def add_word_prefix(self, ctx, *, word: str = None):
        """Thêm từ nối từ (!themtu từ1 từ2)"""
        if not word:
            await ctx.send("❌ Cách dùng: `!themtu từ1 từ2`")
            return
        
        word = word.strip().lower()
        
        # Skip if it's a command (starts with ! or /)
        if word.startswith(('!', '/')):
            return
        
        # Validate format: must be exactly 2 words
        words = word.split()
        if len(words) != 2:
            await ctx.send(f"Từ phải có đúng **2 chữ**. Bạn nhập: `{len(words)} chữ`")
            return
        
        # Validate each word is not empty
        if not words[0] or not words[1]:
            await ctx.send("Từ không được rỗng")
            return
        
        await self._process_add_word(ctx.guild, ctx.author, word, ctx.channel, ctx)
    
    @app_commands.command(name="themtu", description="Thêm từ nối từ")
    @app_commands.describe(word="Từ muốn thêm (2 chữ, ví dụ: xin chào)")
    async def add_word_slash(self, interaction: discord.Interaction, word: str):
        """Thêm từ nối từ"""
        word = word.strip().lower()
        
        # Skip if it's a command (starts with ! or /)
        if word.startswith(('!', '/')):
            await interaction.response.send_message("Không được nhập lệnh", ephemeral=True)
            return
        
        # Validate format: must be exactly 2 words
        words = word.split()
        if len(words) != 2:
            await interaction.response.send_message(f"Từ phải có đúng **2 chữ**. Bạn nhập: `{len(words)} chữ`", ephemeral=True)
            return
        
        # Validate each word is not empty
        if not words[0] or not words[1]:
            await interaction.response.send_message("Từ không được rỗng", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        await self._process_add_word(interaction.guild, interaction.user, word, interaction.channel, interaction)
        await interaction.followup.send("Từ đã được gửi tới admin phê duyệt", ephemeral=True)
    
    async def _process_add_word(self, guild, user, word, channel, ctx_or_interaction):
        """Process word addition and send to admin channel"""
        try:
            # Load words dictionary to check if word already exists
            with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                words_dict = json.load(f)
            
            first, second = word.split()
            
            # Check if word already exists
            if first in words_dict and second in words_dict[first]:
                msg = f"Từ `{word}` đã có sẵn trong từ điển"
                if isinstance(ctx_or_interaction, commands.Context):
                    await ctx_or_interaction.send(msg)
                else:
                    await ctx_or_interaction.followup.send(msg, ephemeral=True)
                logger.debug("[add_word]_word_''_already_exi", word=word)
                return
            
            # Get admin channel from config
            logs_channel_id = await get_server_config(guild.id, "logs_channel_id")
            
            if not logs_channel_id:
                if isinstance(ctx_or_interaction, commands.Context):
                    await ctx_or_interaction.send("Kênh admin chưa được cấu hình. Dùng `/config set kenh_admin`")
                return
            
            admin_channel = self.bot.get_channel(logs_channel_id)
            if not admin_channel:
                if isinstance(ctx_or_interaction, commands.Context):
                    await ctx_or_interaction.send("Kênh admin không tìm thấy")
                return
            
            # Create embed for admin review
            embed = discord.Embed(
                title="Yêu cầu thêm từ mới",
                description=f"Từ: **{word}**\nNgười đề xuất: **{user.mention}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"User ID: {user.id}")
            
            # Send to admin channel with approval buttons
            view = PendingWordView(user.id, word, user.mention, admin_channel)
            await admin_channel.send(embed=embed, view=view)
            
            # Notify user
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(f"Từ **{word}** đã được gửi tới admin phê duyệt")
            
            logger.debug("[add_word]_proposed_word", username=user.name)
            
        except Exception as e:
            logger.debug("[add_word]_error:_", e=e)
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(f"Lỗi: {e}")

async def setup(bot):
    await bot.add_cog(AddWordCog(bot))

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import asyncio
import random

DB_PATH = "./data/database.db"

class GameNoiTu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = []

    async def get_random_word(self):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT word FROM dictionary WHERE word LIKE '% %' AND word NOT LIKE '% % %' ORDER BY RANDOM() LIMIT 1") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def check_word_in_db(self, word):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM dictionary WHERE word = ?", (word.lower(),)) as cursor:
                return await cursor.fetchone() is not None

    async def check_if_word_has_next(self, current_word, used_words):
        last_syllable = current_word.split()[-1]
        search_pattern = f"{last_syllable} %"
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT word FROM dictionary WHERE word LIKE ? AND word NOT LIKE '% % %'", (search_pattern,)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    if row[0] not in used_words:
                        return True
        return False

    @app_commands.command(name="noitu", description="Bắt đầu trò chơi nối từ (2 chữ)")
    async def noitu_slash(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction) # Compatibility wrapper
        
        if interaction.channel_id in self.active_channels:
            await interaction.response.send_message("Game đang chạy ở kênh này rồi!", ephemeral=True)
            return

        self.active_channels.append(interaction.channel_id)
        
        current_word = await self.get_random_word()
        if not current_word:
            await interaction.response.send_message("Lỗi: Từ điển trống.")
            self.active_channels.remove(interaction.channel_id)
            return

        used_words = set()
        used_words.add(current_word)
        last_winner = None
        turn_count = 0
        
        # Respond to slash command to start
        await interaction.response.send_message(f"**BẮT ĐẦU NỐI TỪ**\nTừ khởi đầu: **{current_word.upper()}**\n Thời gian: 10 giây/lượt")

        while True:
            def check(m):
                return m.channel.id == interaction.channel_id and not m.author.bot

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=10.0)
                content = msg.content.lower().strip()
                
                # Validation checks (Length, Syllable, Used, Dict)
                if len(content.split()) != 2:
                    await msg.add_reaction("❌")
                    continue

                last_syllable = current_word.split()[-1]
                first_syllable = content.split()[0]

                if first_syllable != last_syllable:
                    await msg.add_reaction("❌")
                    await interaction.followup.send(f"Sai rồi! Phải bắt đầu bằng chữ **{last_syllable}**.", ephemeral=True)
                    continue 

                if content in used_words:
                    await msg.add_reaction("❌")
                    await interaction.followup.send(f"Từ **{content}** đã dùng rồi.", ephemeral=True)
                    continue

                if not await self.check_word_in_db(content):
                    await msg.add_reaction("❓")
                    # Suggestion prompt could be added here
                    await interaction.followup.send(f"Từ **{content}** không có trong từ điển. Dùng `/themtu` để đề xuất nhé!", ephemeral=True)
                    continue

                # Valid Move
                current_word = content
                used_words.add(content)
                last_winner = msg.author
                turn_count += 1
                await msg.add_reaction("✅")

                # Check Dead End
                if not await self.check_if_word_has_next(current_word, used_words):
                    await interaction.channel.send(f"Bí từ rồi! Không còn từ nào bắt đầu bằng **{current_word.split()[-1]}**.\nNgười chiến thắng: {last_winner.mention}!")
                    break

            except asyncio.TimeoutError:
                if turn_count == 0:
                    await interaction.followup.send("Hủy game vì không ai chơi.")
                else:
                    await interaction.channel.send(f"Hết giờ! Người chiến thắng là {last_winner.mention} với từ **{current_word}**!")
                break
        
        if interaction.channel_id in self.active_channels:
            self.active_channels.remove(interaction.channel_id)

async def setup(bot):
    await bot.add_cog(GameNoiTu(bot))
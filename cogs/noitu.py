import discord
from discord.ext import commands
import aiosqlite
import asyncio
import random
from datetime import datetime

DB_PATH = "./data/database.db"

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [NoiTu] {message}")

class GameNoiTu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Game state per server (Guild ID -> Data)
        self.games = {}
        # Lock to prevent race condition (Guild ID -> asyncio.Lock)
        self.game_locks = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Auto-initialize games for all configured servers on bot startup"""
        log("Bot started - Auto-initializing games for configured servers")
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT guild_id, noitu_channel_id FROM server_config WHERE noitu_channel_id IS NOT NULL") as cursor:
                rows = await cursor.fetchall()
        
        for guild_id, channel_id in rows:
            channel = self.bot.get_channel(channel_id)
            if channel and guild_id not in self.games:
                try:
                    await self.start_new_round(guild_id, channel)
                    log(f"Game initialized for guild {guild_id}")
                except Exception as e:
                    log(f"Failed to initialize game for guild {guild_id}: {e}")

    # --- Helper Functions ---
    async def get_config_channel(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT noitu_channel_id FROM server_config WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

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

    def get_game_lock(self, guild_id):
        """Get or create a lock for this guild"""
        if guild_id not in self.game_locks:
            self.game_locks[guild_id] = asyncio.Lock()
        return self.game_locks[guild_id]

    async def start_new_round(self, guild_id, channel):
        """Initialize new round"""
        word = await self.get_random_word()
        if not word:
            log(f"ERROR: Dictionary empty for guild {guild_id}")
            return

        self.games[guild_id] = {
            "channel_id": channel.id,
            "current_word": word,
            "used_words": {word},
            "last_author_id": None,
            "timer_task": None,
            "player_count": 0
        }
        
        log(f"GAME_START [Guild {guild_id}] Starting word: '{word}'")
        await channel.send(f"Từ khởi đầu: **{word}**\nChờ người chơi nhập vào...")

    async def game_timer(self, guild_id, channel):
        """Timer 15s"""
        try:
            await asyncio.sleep(15)
            
            game_data = self.games.get(guild_id)
            if game_data and game_data['last_author_id']:
                winner_id = game_data['last_author_id']
                word = game_data['current_word']
                
                log(f"TIMEOUT [Guild {guild_id}] Winner: {winner_id} with word '{word}'")
                await channel.send(f"Hết giờ! <@{winner_id}> win với từ **{word}**")
                
                await self.start_new_round(guild_id, channel)
            
        except asyncio.CancelledError:
            log(f"TIMER_CANCEL [Guild {guild_id}] Next player made move")
            pass

    # --- Events (Core Logic) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = message.guild.id
        
        # 1. Check if game is running in memory
        if guild_id not in self.games:
            # Attempt to load from DB config (e.g. after restart)
            channel_id = await self.get_config_channel(guild_id)
            if channel_id and message.channel.id == channel_id:
                log(f"GAME_RELOAD [Guild {guild_id}] Loading from DB after restart")
                await self.start_new_round(guild_id, message.channel)
                return 
            else:
                return

        game = self.games[guild_id]
        
        # 2. Check channel
        if message.channel.id != game['channel_id']:
            return

        # Use lock to prevent race condition when multiple users send messages at the same time
        lock = self.get_game_lock(guild_id)
        async with lock:
            try:
                # Re-check game state after acquiring lock (game might have ended)
                if guild_id not in self.games:
                    return
                
                game = self.games[guild_id]

                # --- GAME LOGIC ---
                
                content = message.content.lower().strip()
                
                # Validation checks
                if len(content.split()) != 2:
                    log(f"INVALID_FORMAT [Guild {guild_id}] {message.author.name}: '{content}'")
                    try:
                        await message.add_reaction("❌")
                    except:
                        pass
                    return 

                # Anti-Self-Play
                if message.author.id == game['last_author_id']:
                    log(f"SELF_PLAY [Guild {guild_id}] {message.author.name} tried self-play")
                    try:
                        await message.add_reaction("❌")
                    except:
                        pass
                    await message.reply("Ko được tự reply, chờ người khác nhé", delete_after=5)
                    return

                current_word = game['current_word']
                last_syllable = current_word.split()[-1]
                first_syllable = content.split()[0]

                # Check connection
                if first_syllable != last_syllable:
                    log(f"WRONG_CONNECTION [Guild {guild_id}] {message.author.name}: '{content}' needs to start with '{last_syllable}'")
                    try:
                        await message.add_reaction("❌")
                    except:
                        pass
                    return

                # Check used
                if content in game['used_words']:
                    log(f"ALREADY_USED [Guild {guild_id}] {message.author.name}: '{content}'")
                    try:
                        await message.add_reaction("❌")
                    except:
                        pass
                    await message.reply("Từ này dùng rồi, tìm từ khác đi", delete_after=3)
                    return

                # Check dictionary
                if not await self.check_word_in_db(content):
                    log(f"NOT_IN_DICT [Guild {guild_id}] {message.author.name}: '{content}'")
                    try:
                        await message.add_reaction("❌")
                    except:
                        pass
                    await message.reply("Từ này ko có trong từ điển, sorry", delete_after=3)
                    return

                # === VALID MOVE ===
                try:
                    await message.add_reaction("✅")
                except:
                    pass
                log(f"VALID_MOVE [Guild {guild_id}] {message.author.name}: '{content}' (player #{game['player_count'] + 1})")
                
                # 1. Cancel old timer
                if game['timer_task']:
                    game['timer_task'].cancel()
                
                # 2. Update player count
                game['player_count'] += 1
                
                # 3. Check Dead End
                has_next = await self.check_if_word_has_next(content, game['used_words'])
                
                if not has_next:
                    log(f"DEAD_END [Guild {guild_id}] No words starting with '{content.split()[-1]}' - Winner: {message.author.name}")
                    await message.channel.send(f"Bí từ! Ko có từ nào bắt đầu bằng **{content.split()[-1]}**. {message.author.mention} win")
                    await self.start_new_round(guild_id, message.channel)
                    return

                # 4. Update State
                game['current_word'] = content
                game['used_words'].add(content)
                game['last_author_id'] = message.author.id
                
                # 5. Start timer only after 2nd player joins
                if game['player_count'] >= 2:
                    log(f"TIMER_START [Guild {guild_id}] ({game['player_count']} players)")
                    game['timer_task'] = asyncio.create_task(self.game_timer(guild_id, message.channel))
                else:
                    log(f"WAITING_P2 [Guild {guild_id}] ({game['player_count']}/2)")
                    await message.channel.send(f"Chờ người chơi thứ 2 vào nha ({game['player_count']}/2)")
            
            except Exception as e:
                log(f"ERROR [Guild {guild_id}] Exception: {str(e)}")
                import traceback
                traceback.print_exc()

async def setup(bot):
    await bot.add_cog(GameNoiTu(bot))
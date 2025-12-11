import discord
from discord.ext import commands
import aiosqlite
import asyncio
import random
import json
from datetime import datetime

DB_PATH = "./data/database.db"
WORDS_DICT_PATH = "./data/words_dict.json"

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
        # Words dictionary (memory-based): {first_syllable: [possible_second_syllables]}
        self.words_dict = {}
        # All words for random selection
        self.all_words = set()
        # Cached list for faster random selection (avoid O(n) conversion)
        self.all_words_list = []

    @commands.Cog.listener()
    async def on_ready(self):
        """Auto-initialize games for all configured servers on bot startup"""
        log("Bot started - Loading words dictionary")
        
        # Load words dictionary from file
        try:
            with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                self.words_dict = json.load(f)
            
            # Build set of all words for random selection
            for first, seconds in self.words_dict.items():
                for second in seconds:
                    word = f"{first} {second}"
                    self.all_words.add(word)
                    self.all_words_list.append(word)
            
            log(f"Loaded words dict: {len(self.words_dict)} starting syllables, {len(self.all_words)} total words")
        except FileNotFoundError:
            log(f"ERROR: {WORDS_DICT_PATH} not found. Run: python build_words_dict.py")
            return
        except Exception as e:
            log(f"ERROR loading words dict: {e}")
            return
        
        # Auto-initialize games for configured servers
        log("Auto-initializing games for configured servers")
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
        """Get random 2-syllable word from memory dictionary"""
        if not self.all_words_list:
            return None
        return random.choice(self.all_words_list)

    async def get_valid_start_word(self):
        """Get random start word that has at least one continuation (no dead-end)"""
        max_attempts = 50
        for _ in range(max_attempts):
            word = await self.get_random_word()
            if not word:
                return None
            
            # Check if this word has a possible next word
            if await self.check_if_word_has_next(word, {word}):
                return word
        
        # Fallback: return any random word
        return await self.get_random_word()

    async def check_word_in_db(self, word):
        """Check if word exists in dictionary (memory-based)"""
        return word in self.all_words

    async def check_if_word_has_next(self, current_word, used_words):
        """Check if there's any valid next word (memory-based lookup)"""
        last_syllable = current_word.split()[-1]
        
        # Check if last syllable exists in dictionary
        if last_syllable not in self.words_dict:
            return False
        
        # Check if any next word hasn't been used
        for next_second in self.words_dict[last_syllable]:
            next_full_word = f"{last_syllable} {next_second}"
            if next_full_word not in used_words:
                return True
        
        return False

    def get_game_lock(self, guild_id):
        """Get or create a lock for this guild"""
        if guild_id not in self.game_locks:
            self.game_locks[guild_id] = asyncio.Lock()
        return self.game_locks[guild_id]
    
    async def reload_words_dict(self):
        """Reload dictionary from file (after new words added)"""
        try:
            with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                self.words_dict = json.load(f)
            
            # Rebuild set and list
            self.all_words.clear()
            self.all_words_list.clear()
            
            for first, seconds in self.words_dict.items():
                for second in seconds:
                    word = f"{first} {second}"
                    self.all_words.add(word)
                    self.all_words_list.append(word)
            
            log(f"Reloaded words dict: {len(self.all_words)} total words")
        except Exception as e:
            log(f"ERROR reloading words dict: {e}")
    
    def cleanup_game_lock(self, guild_id):
        """Clean up lock after game ends (prevent memory leak)"""
        if guild_id in self.game_locks:
            del self.game_locks[guild_id]
    
    async def update_player_stats(self, user_id, username, is_winner=False):
        """Update player stats: wins and correct words count"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if user exists
                async with db.execute("SELECT wins, correct_words FROM player_stats WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                
                if row:
                    # User exists, update stats
                    wins = row[0] + (1 if is_winner else 0)
                    correct_words = row[1] + 1
                    await db.execute(
                        "UPDATE player_stats SET wins = ?, correct_words = ?, username = ?, last_updated = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (wins, correct_words, username, user_id)
                    )
                else:
                    # New user, insert
                    wins = 1 if is_winner else 0
                    correct_words = 1
                    await db.execute(
                        "INSERT INTO player_stats (user_id, username, wins, correct_words) VALUES (?, ?, ?, ?)",
                        (user_id, username, wins, correct_words)
                    )
                
                await db.commit()
                log(f"STATS_UPDATE [User {username}] Wins: +{'1' if is_winner else '0'}, CorrectWords: +1")
        except Exception as e:
            log(f"ERROR updating player stats: {e}")
    
    async def update_ranking_roles(self, guild):
        """Update ranking roles based on current standings"""
        # Role IDs for top 3
        TOP_1_ROLE_ID = 1448605926067273831
        TOP_2_ROLE_ID = 1448605983289905244
        TOP_3_ROLE_ID = 1448606089447866478
        
        try:
            # Get bot member and check permissions
            bot_member = guild.me
            if not bot_member:
                log(f"ERROR: Bot not found in guild {guild.id}")
                return
            
            if not bot_member.guild_permissions.manage_roles:
                log(f"ERROR: Bot missing MANAGE_ROLES permission in guild {guild.id}")
                return
            
            # Get top 3 players
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT user_id FROM player_stats ORDER BY wins DESC, correct_words DESC LIMIT 3"
                ) as cursor:
                    rows = await cursor.fetchall()
            
            top_players = [row[0] for row in rows]
            role_ids = [TOP_1_ROLE_ID, TOP_2_ROLE_ID, TOP_3_ROLE_ID]
            
            # Remove all ranking roles from all members
            for role_id in role_ids:
                role = guild.get_role(role_id)
                if not role:
                    log(f"WARNING: Role {role_id} not found in guild {guild.id}")
                    continue
                
                # Check if role is above bot
                if role.position >= bot_member.top_role.position:
                    log(f"ERROR: Role {role.name} ({role_id}) is above or equal to bot's highest role in guild {guild.id}")
                    continue
                
                for member in role.members:
                    try:
                        await member.remove_roles(role)
                        log(f"ROLE_REMOVE [Guild {guild.id}] Removed {role.name} from {member.name}")
                    except discord.Forbidden:
                        log(f"ERROR: No permission to remove {role.name} from {member.name}")
                    except Exception as e:
                        log(f"ERROR removing role from {member.name}: {e}")
            
            # Assign roles to top 3
            for idx, user_id in enumerate(top_players):
                try:
                    member = guild.get_member(user_id)
                    if not member:
                        log(f"WARNING: User {user_id} not found in guild {guild.id}")
                        continue
                    
                    role = guild.get_role(role_ids[idx])
                    if not role:
                        log(f"WARNING: Role {role_ids[idx]} not found in guild {guild.id}")
                        continue
                    
                    # Check if role is above bot
                    if role.position >= bot_member.top_role.position:
                        log(f"ERROR: Role {role.name} is above or equal to bot's highest role")
                        continue
                    
                    await member.add_roles(role)
                    log(f"ROLE_ASSIGN [Guild {guild.id}] Top {idx+1}: {member.name} <- {role.name}")
                except discord.Forbidden as e:
                    log(f"ERROR: No permission to assign role: {e}")
                except Exception as e:
                    log(f"ERROR assigning role: {e}")
            
        except Exception as e:
            log(f"ERROR updating ranking roles: {e}")

    async def start_new_round(self, guild_id, channel):
        """Initialize new round"""
        word = await self.get_valid_start_word()
        if not word:
            log(f"ERROR: Dictionary empty for guild {guild_id}")
            return

        self.games[guild_id] = {
            "channel_id": channel.id,
            "current_word": word,
            "used_words": {word},
            "last_author_id": None,
            "timer_task": None,
            "timer_message": None,
            "player_count": 0,
            "last_message_time": None,
            "start_message": None,  # Track the start message for sticky behavior
            "start_message_content": f"Từ khởi đầu: **{word}**\nChờ người chơi nhập vào..."
        }
        
        log(f"GAME_START [Guild {guild_id}] Starting word: '{word}'")
        msg = await channel.send(self.games[guild_id]["start_message_content"])
        self.games[guild_id]["start_message"] = msg
        
        # Update ranking roles after game ends
        try:
            guild = channel.guild
            await self.update_ranking_roles(guild)
        except Exception as e:
            log(f"ERROR updating roles: {e}")

    async def game_timer(self, guild_id, channel, start_time):
        """Timer 25s từ tin nhắn cuối cùng với visual countdown"""
        try:
            import time
            
            # Record the time when timer starts
            timer_start_time = time.time()
            
            # Send initial 25 second countdown message
            game_data = self.games.get(guild_id)
            if not game_data:
                return
            
            timer_msg = await channel.send("25 giây...")
            game_data['timer_message'] = timer_msg
            
            # Countdown loop
            for countdown in range(24, -1, -1):
                await asyncio.sleep(1)
                
                game_data = self.games.get(guild_id)
                if not game_data:
                    return
                
                # Check nếu có tin nhắn mới TRONG khoảng thời gian timer đang chạy
                # Nếu last_message_time được cập nhật SAU khi timer bắt đầu, nghĩa là có move mới
                if game_data['last_message_time'] and game_data['last_message_time'] > timer_start_time:
                    # Có tin nhắn mới, hủy timer
                    try:
                        await timer_msg.delete()
                    except:
                        pass
                    log(f"TIMER_SKIP [Guild {guild_id}] New message received, timer cancelled")
                    return
                
                # Edit message with countdown
                try:
                    if countdown > 0:
                        await timer_msg.edit(content=f"{countdown} giây...")
                    else:
                        await timer_msg.edit(content="Hết giờ!")
                except:
                    pass
            
            # Timer ended - calculate winner
            game_data = self.games.get(guild_id)
            if game_data and game_data['last_author_id']:
                winner_id = game_data['last_author_id']
                word = game_data['current_word']
                
                log(f"TIMEOUT [Guild {guild_id}] Winner: {winner_id} with word '{word}'")
                
                # Edit timer message to show timeout
                try:
                    await timer_msg.edit(content="Hết giờ!")
                except:
                    pass
                
                # Send new message with winner info
                winner = await self.bot.fetch_user(winner_id)
                await channel.send(f"Hết giờ! <@{winner_id}> win với từ **{word}**")
                
                # Update winner stats
                await self.update_player_stats(winner_id, winner.name, is_winner=True)
                
                await self.start_new_round(guild_id, channel)
            
        except asyncio.CancelledError:
            log(f"TIMER_CANCEL [Guild {guild_id}] Next player made move")
            # Clean up timer message
            try:
                game_data = self.games.get(guild_id)
                if game_data and game_data.get('timer_message'):
                    await game_data['timer_message'].delete()
            except:
                pass
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
                
                # Validation: Only process 2-word inputs (ignore commands and other formats)
                if len(content.split()) != 2:
                    log(f"SKIP [Guild {guild_id}] {message.author.name}: '{content}' (not 2 words)")
                    # Refresh sticky start message if game is in round 1
                    if game['player_count'] == 0:
                        try:
                            if game.get('start_message'):
                                await game['start_message'].delete()
                        except:
                            pass
                        msg = await message.channel.send(game["start_message_content"])
                        game['start_message'] = msg
                    return
                
                # Skip if starts with command prefix
                if content.startswith(('!', '/')):
                    log(f"SKIP [Guild {guild_id}] {message.author.name}: '{content}' (command prefix)")
                    # Refresh sticky start message if game is in round 1
                    if game['player_count'] == 0:
                        try:
                            if game.get('start_message'):
                                await game['start_message'].delete()
                        except:
                            pass
                        msg = await message.channel.send(game["start_message_content"])
                        game['start_message'] = msg
                    return

                # Anti-Self-Play
                if message.author.id == game['last_author_id']:
                    log(f"SELF_PLAY [Guild {guild_id}] {message.author.name} tried self-play")
                    try:
                            await message.add_reaction("🛑")
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
                            await message.add_reaction("❗")
                    except:
                        pass
                    await message.reply(f"Từ phải bắt đầu bằng **{last_syllable}**", delete_after=3)
                    return

                # Check used
                if content in game['used_words']:
                    log(f"ALREADY_USED [Guild {guild_id}] {message.author.name}: '{content}'")
                    try:
                            await message.add_reaction("⛔")
                    except:
                        pass
                    await message.reply("Từ này dùng rồi, tìm từ khác đi", delete_after=3)
                    return

                # Check dictionary
                if not await self.check_word_in_db(content):
                    log(f"NOT_IN_DICT [Guild {guild_id}] {message.author.name}: '{content}'")
                    try:
                            await message.add_reaction("❓")
                    except:
                        pass
                    
                    # Import QuickAddWordView from add_word cog
                    try:
                        from cogs.add_word import QuickAddWordView
                        view = QuickAddWordView(content, message.author, self.bot)
                        await message.reply(
                            f"Từ **{content}** không có trong từ điển. Bạn muốn gửi admin thêm từ này?",
                            view=view,
                            delete_after=5
                        )
                    except Exception as e:
                        await message.reply("Từ này ko có trong từ điển, bruh", delete_after=3)
                    return

                # === VALID MOVE ===
                try:
                        await message.add_reaction("✅")
                except:
                    pass
                log(f"VALID_MOVE [Guild {guild_id}] {message.author.name}: '{content}' (player #{game['player_count'] + 1})")
                
                # Update player stats (correct word count)
                await self.update_player_stats(message.author.id, message.author.name, is_winner=False)
                
                # 1. Cancel old timer and delete timer message
                if game['timer_task']:
                    game['timer_task'].cancel()
                    # Delete timer message
                    try:
                        if game.get('timer_message'):
                            await game['timer_message'].delete()
                            game['timer_message'] = None
                    except:
                        pass
                    log(f"TIMER_RESET [Guild {guild_id}] Old timer cancelled")
                
                # 2. Update player count
                game['player_count'] += 1
                
                # Notify when Player 2 joins
                if game['player_count'] == 2:
                    try:
                        await message.channel.send("Nối từ bắt đầu!")
                    except:
                        pass
                
                # 3. Update State trước (add từ vào used_words)
                game['current_word'] = content
                game['used_words'].add(content)
                game['last_author_id'] = message.author.id
                
                # 4. Update last_message_time
                import time
                game['last_message_time'] = time.time()
                
                # 5. Check Dead End (kiểm tra với từ mới đã thêm vào used_words)
                has_next = await self.check_if_word_has_next(content, game['used_words'])
                
                if not has_next:
                    log(f"DEAD_END [Guild {guild_id}] No words starting with '{content.split()[-1]}' - Winner: {message.author.name}")
                    
                    # Update winner stats
                    await self.update_player_stats(message.author.id, message.author.name, is_winner=True)
                    
                    # Special message if player count is 1 (first player)
                    if game['player_count'] == 1:
                        await message.channel.send(f"Chơi 1 mình luôn đi ba! {message.author.mention} win")
                    else:
                        await message.channel.send(f"Bí từ! Ko có từ nào bắt đầu bằng **{content.split()[-1]}**. {message.author.mention} win")
                    
                    # Cleanup lock before starting new round
                    self.cleanup_game_lock(guild_id)
                    await self.start_new_round(guild_id, message.channel)
                    return
                
                # 6. Start timer only after 2nd player joins
                if game['player_count'] >= 2:
                    log(f"TIMER_START [Guild {guild_id}] ({game['player_count']} players) - 25s countdown")
                    game['timer_task'] = asyncio.create_task(self.game_timer(guild_id, message.channel, game['last_message_time']))
                else:
                    log(f"WAITING_P2 [Guild {guild_id}] ({game['player_count']}/2)")
                    await message.channel.send(f"Chờ người chơi thứ 2 vào nha ({game['player_count']}/2)")
            
            except Exception as e:
                log(f"ERROR [Guild {guild_id}] Exception: {str(e)}")
                import traceback
                traceback.print_exc()

async def setup(bot):
    await bot.add_cog(GameNoiTu(bot))
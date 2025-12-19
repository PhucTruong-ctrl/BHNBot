import discord
from discord.ext import commands
import aiosqlite
import asyncio
import random
import json
import time
import traceback
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
        # Flag to track if dictionary is loaded
        self.dict_loaded = False
        # Lock for dictionary loading to prevent race conditions
        self.dict_load_lock = asyncio.Lock()
        # Co-op Streak tracking: {guild_id: current_streak_count}
        self.streak = {}
        # Track if we've already initialized
        self._initialized = False

    async def cog_load(self):
        """Called when the cog is loaded - initialize games here"""
        log("Cog loaded, scheduling game initialization")
        # Schedule initialization as a background task
        asyncio.create_task(self._initialize_games_on_load())

    async def _initialize_games_on_load(self):
        """Initialize games after cog is loaded - called as background task"""
        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            log("Bot is ready - initializing NoiTu games")
            
            # Load dictionary
            async with self.dict_load_lock:
                await self._load_dictionary()
            
            if not self.dict_loaded:
                log("⚠️  Dictionary not loaded, skipping game initialization")
                return
            
            # Initialize games
            log("Auto-initializing games for configured servers")
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute("SELECT guild_id, noitu_channel_id FROM server_config WHERE noitu_channel_id IS NOT NULL") as cursor:
                        rows = await cursor.fetchall()
                
                if not rows:
                    log("⚠️  No NoiTu channels configured in database")
                    return
                
                initialized_count = 0
                for guild_id, channel_id in rows:
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        log(f"⚠️  Channel {channel_id} not found for guild {guild_id}")
                        continue
                    
                    if guild_id in self.games:
                        log(f"⏭️  Game already initialized for guild {guild_id}, skipping")
                        continue
                    
                    try:
                        # Try to restore game state from database first
                        is_restored = await self.restore_game_state(guild_id, channel)
                        if not is_restored:
                            # If no saved state, start fresh
                            await self.start_new_round(guild_id, channel)
                        log(f"✅ Game initialized for guild {guild_id} (restored={is_restored})")
                        initialized_count += 1
                    except Exception as e:
                        log(f"❌ Failed to initialize game for guild {guild_id}: {e}")
                
                log(f"Auto-initialization complete: {initialized_count}/{len(rows)} games initialized")
                self._initialized = True
            except Exception as e:
                log(f"ERROR in initialization loop: {e}")
        except Exception as e:
            log(f"FATAL ERROR in _initialize_games_on_load: {e}")
            import traceback
            traceback.print_exc()

    async def _load_dictionary(self):
        """Load words dictionary from file"""
        try:
            with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                self.words_dict = json.load(f)
            
            # Clear old lists
            self.all_words.clear()
            self.all_words_list.clear()
            
            # Build set of all words for random selection
            for first, seconds in self.words_dict.items():
                for second in seconds:
                    word = f"{first} {second}"
                    self.all_words.add(word)
                    self.all_words_list.append(word)
            
            self.dict_loaded = True
            log(f"✅ Loaded words dict: {len(self.words_dict)} starting syllables, {len(self.all_words)} total words")
            return True
        except FileNotFoundError:
            log(f"❌ ERROR: {WORDS_DICT_PATH} not found. Run: python build_words_dict.py")
            self.dict_loaded = False
            return False
        except Exception as e:
            log(f"❌ ERROR loading words dict: {e}")
            self.dict_loaded = False
            return False


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
        word_lower = word.lower().strip()
        return word_lower in self.all_words

    async def check_if_word_has_next(self, current_word, used_words):
        """Check if there's any valid next word (memory-based lookup)"""
        current_word_lower = current_word.lower().strip()
        last_syllable = current_word_lower.split()[-1]
        
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
    
    async def save_game_state(self, guild_id, channel_id):
        """Save NoiTu game state to database for resume after restart"""
        try:
            if guild_id not in self.games:
                return
            
            game = self.games[guild_id]
            game_state_json = json.dumps({
                "current_word": game.get("current_word"),
                "used_words": list(game.get("used_words", set())),
                "last_author_id": game.get("last_author_id"),
                "players": game.get("players", {}),
                "start_message_id": game.get("start_message").id if game.get("start_message") else None
            })
            
            async with aiosqlite.connect(DB_PATH) as db:
                # Check if session exists
                async with db.execute(
                    "SELECT id FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                    (guild_id, "noitu")
                ) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    # Update existing session
                    await db.execute(
                        "UPDATE game_sessions SET channel_id = ?, game_state = ?, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ? AND game_type = ?",
                        (channel_id, game_state_json, guild_id, "noitu")
                    )
                else:
                    # Insert new session
                    await db.execute(
                        "INSERT INTO game_sessions (guild_id, game_type, channel_id, game_state) VALUES (?, ?, ?, ?)",
                        (guild_id, "noitu", channel_id, game_state_json)
                    )
                await db.commit()
            
            log(f"GAME_SAVED [Guild {guild_id}] Current word: {game.get('current_word')}, Used: {len(game.get('used_words', set()))}")
        except Exception as e:
            log(f"ERROR saving game state: {e}")
    
    async def restore_game_state(self, guild_id, channel):
        """Restore NoiTu game state from database after bot restart"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT game_state FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                    (guild_id, "noitu")
                ) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                log(f"NO_SAVE_FOUND [Guild {guild_id}] Starting fresh game")
                return False
            
            game_state = json.loads(row[0])
            
            # Delete old resume message if exists
            old_message_id = game_state.get("start_message_id")
            if old_message_id:
                try:
                    old_msg = await channel.fetch_message(old_message_id)
                    await old_msg.delete()
                    log(f"DELETED_OLD_RESUME_MSG [Guild {guild_id}] Message ID: {old_message_id}")
                except Exception as e:
                    log(f"COULD_NOT_DELETE_OLD_MSG [Guild {guild_id}] Message ID: {old_message_id}, Error: {e}")
            
            # Restore game state
            # Convert old players format (just usernames) to new format (with word counts)
            old_players = game_state.get("players", {})
            new_players = {}
            for user_id, username in old_players.items():
                if isinstance(username, dict):
                    new_players[int(user_id)] = username
                else:
                    new_players[int(user_id)] = {"username": username, "correct_words": 0}
            
            self.games[guild_id] = {
                "channel_id": channel.id,
                "current_word": game_state.get("current_word"),
                "used_words": set(game_state.get("used_words", [])),
                "last_author_id": game_state.get("last_author_id"),
                "timer_task": None,
                "timer_message": None,
                "player_count": len(new_players),
                "last_message_time": None,
                "start_message": None,
                "start_message_content": f"Từ hiện tại: **{game_state.get('current_word')}**\n[Game được resume từ lần restart trước]",
                "players": new_players
            }
            
            # Send resume message
            msg = await channel.send(self.games[guild_id]["start_message_content"])
            self.games[guild_id]["start_message"] = msg
            
            # Save updated game state with new message ID
            await self.save_game_state(guild_id, channel.id)
            
            log(f"GAME_RESUMED [Guild {guild_id}] Current word: {game_state.get('current_word')}, Used: {len(game_state.get('used_words', []))}")
            return True
        except Exception as e:
            log(f"ERROR restoring game state: {e}")
            return False
    
    async def update_player_stats(self, user_id, username, is_winner=False):
        """Update player stats: wins and correct words count"""
        try:
            from database_manager import get_stat, increment_stat
            
            # Get current stats
            wins = await get_stat(user_id, 'noitu', 'wins', default=0)
            correct_words = await get_stat(user_id, 'noitu', 'correct_words', default=0)
            
            # Update stats
            wins += 1 if is_winner else 0
            correct_words += 1
            
            await increment_stat(user_id, 'noitu', 'wins', 1 if is_winner else 0)
            await increment_stat(user_id, 'noitu', 'correct_words', 1)
            
            log(f"STATS_UPDATE [User {username}] Wins: +{'1' if is_winner else '0'}, CorrectWords: +1")
        except Exception as e:
            log(f"ERROR updating player stats: {e}")
    
    
    async def distribute_streak_rewards(self, guild_id, all_players, final_streak, channel):
        """Distribute rewards based on community streak (Co-op system)
        - Base reward: 2 hạt × streak (minimum 10 hạt)
        - Bonus: 1 hạt per correct word per player
        - All rewards multiplied by buff if active
        """
        try:
            economy_cog = self.bot.get_cog("EconomyCog")
            if not economy_cog:
                log(f"ERROR: EconomyCog not found")
                return
            
            # Check if harvest buff is active
            is_buff_active = await economy_cog.is_harvest_buff_active(guild_id)
            buff_multiplier = 2 if is_buff_active else 1
            
            # Calculate base reward: 2 seeds per word in final streak
            base_reward = max(10, final_streak * 2) * buff_multiplier
            
            # Distribute rewards to all participants
            player_display_list = []
            for user_id, player_data in all_players.items():
                try:
                    # Handle both old format (string) and new format (dict)
                    if isinstance(player_data, dict):
                        username = player_data.get("username", "Unknown")
                        correct_words = player_data.get("correct_words", 0)
                    else:
                        username = player_data
                        correct_words = 0
                    
                    # Calculate reward: base + bonus for each correct word
                    bonus_reward = correct_words * buff_multiplier
                    total_reward = base_reward + bonus_reward
                    
                    await economy_cog.add_seeds_local(user_id, total_reward)
                    
                    # Format for display: @mention - X từ (Y Hạt)
                    try:
                        user = await self.bot.fetch_user(user_id)
                        player_display_list.append(f"{user.mention} - {correct_words} từ")
                    except:
                        player_display_list.append(f"{username} - {correct_words} từ")
                    
                    log(f"REWARD [Guild {guild_id}] {username}: {base_reward} base + {bonus_reward} bonus = {total_reward} total")
                except Exception as e:
                    log(f"ERROR distributing reward: {e}")
            
            # Create reward notification embed
            embed = discord.Embed(
                title="🎮 Phần Thưởng Nối Từ - Cộng Đồng",
                description=f"Chuỗi {final_streak} từ kết thúc! Mọi người được thưởng.",
                colour=discord.Colour.gold()
            )
            
            # Display all players with their word counts and mentions
            if player_display_list:
                embed.add_field(
                    name="👥 Tất cả tham gia",
                    value="\n".join(player_display_list),
                    inline=False
                )
            
            embed.add_field(
                name="🌱 Phần Thưởng Cơ Bản/Người",
                value=f"+{base_reward} Hạt (từ chuỗi {final_streak})",
                inline=False
            )
            
            embed.add_field(
                name="💚 Phần Thưởng Bổ Sung",
                value=f"+{buff_multiplier} Hạt mỗi từ nối đúng",
                inline=False
            )
            
            if is_buff_active:
                embed.add_field(
                    name="🔥 Cộng Hưởng Sinh Lực (Harvest Buff)",
                    value=f"Tất cả phần thưởng được nhân 2x!",
                    inline=False
                )
            
            await channel.send(embed=embed)
        
        except Exception as e:
            log(f"ERROR distributing streak rewards: {e}")
    
    async def distribute_rewards(self, guild_id, winner_id, all_players, channel):
        """Distribute seeds rewards after game ends"""
        try:
            economy_cog = self.bot.get_cog("EconomyCog")
            if not economy_cog:
                log(f"ERROR: EconomyCog not found")
                return
            
            # Check if harvest buff is active
            is_buff_active = await economy_cog.is_harvest_buff_active(guild_id)
            buff_multiplier = 2 if is_buff_active else 1
            
            # Calculate rewards
            winner_reward = 15 * buff_multiplier
            loser_reward = 5 * buff_multiplier
            
            winner_name = None
            loser_names = []
            
            # Distribute rewards
            for user_id, username in all_players.items():
                if user_id == winner_id:
                    await economy_cog.add_seeds_local(user_id, winner_reward)
                    winner_name = username
                else:
                    await economy_cog.add_seeds_local(user_id, loser_reward)
                    loser_names.append(username)
            
            # Create reward notification embed
            embed = discord.Embed(
                title="🎮 Phần Thưởng Nối Từ",
                description="Game kết thúc! Phần thưởng đã được phát.",
                colour=discord.Colour.gold()
            )
            
            # Winner info
            winner_display = f"🥇 {winner_name}" if winner_name else "🥇 Unknown"
            embed.add_field(
                name="👑 Người Thắng",
                value=f"{winner_display}\n+{winner_reward} 🌱",
                inline=False
            )
            
            # Loser info (if any)
            if loser_names:
                loser_display = ", ".join(loser_names)
                embed.add_field(
                    name="🤝 Những Người Tham Gia",
                    value=f"{loser_display}\n+{loser_reward} 🌱 mỗi người",
                    inline=False
                )
            
            # Buff info
            if is_buff_active:
                embed.add_field(
                    name="🔥 Cộng Hưởng Sinh Lực (Harvest Buff)",
                    value=f"Phần thưởng được nhân 2x!",
                    inline=False
                )
            
            try:
                await channel.send(embed=embed)
            except Exception as e:
                log(f"ERROR sending reward embed: {e}")
        
        except Exception as e:
            log(f"ERROR distributing rewards: {e}")
    
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
                    "SELECT user_id, value FROM user_stats WHERE game_id = 'noitu' AND stat_key = 'wins' ORDER BY value DESC LIMIT 3"
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
        # Ensure dictionary is loaded
        if not self.dict_loaded or not self.all_words_list:
            log(f"❌ ERROR: Dictionary empty for guild {guild_id} (loaded={self.dict_loaded}, words={len(self.all_words_list)})")
            # Try to reload dictionary
            async with self.dict_load_lock:
                await self._load_dictionary()
            
            # If still empty, can't start game
            if not self.all_words_list:
                await channel.send("❌ Lỗi: Từ điển chưa được load. Vui lòng thử lại sau!")
                return
        
        word = await self.get_valid_start_word()
        if not word:
            log(f"❌ ERROR: Could not get start word for guild {guild_id}")
            await channel.send("❌ Lỗi: Không tìm được từ bắt đầu. Vui lòng thử lại sau!")
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
            "start_message_content": f"Từ khởi đầu: **{word}**\nChờ người chơi nhập vào...",
            "players": {}  # Track players: {user_id: {'username': name, 'correct_words': count}}
        }
        
        log(f"GAME_START [Guild {guild_id}] Starting word: '{word}'")
        msg = await channel.send(self.games[guild_id]["start_message_content"])
        self.games[guild_id]["start_message"] = msg
        
        # Save game state with message ID
        await self.save_game_state(guild_id, channel.id)
        
        # Update ranking roles after game ends
        try:
            guild = channel.guild
            await self.update_ranking_roles(guild)
        except Exception as e:
            log(f"ERROR updating roles: {e}")

    async def game_timer(self, guild_id, channel, start_time):
        """Timer 25s từ tin nhắn cuối cùng với visual countdown"""
        try:
            # Record the time when timer starts
            timer_start_time = time.time()
            
            # Send initial 60 second countdown message
            game_data = self.games.get(guild_id)
            if not game_data:
                return
            
            timer_msg = await channel.send("60 giây...")
            game_data['timer_message'] = timer_msg
            
            # Countdown loop
            for countdown in range(59, -1, -1):
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
                current_streak = self.streak.get(guild_id, 0)
                word = game_data['current_word']
                
                log(f"TIMEOUT [Guild {guild_id}] Streak ended at {current_streak} words, last word: '{word}'")
                
                # Delete old timer message
                try:
                    await timer_msg.delete()
                except:
                    pass
                
                # Create timeout embed
                embed = discord.Embed(
                    title="⌛ HẾT GIỜ!",
                    description=f"Không ai nối được từ **{word}**!",
                    color=discord.Color.red()
                )
                
                try:
                    last_player = await self.bot.fetch_user(game_data['last_author_id'])
                    embed.add_field(name="👤 Người giữ lượt cuối", value=last_player.mention, inline=False)
                except:
                    pass
                
                embed.add_field(name="🔥 Chuỗi Cộng Đồng", value=f"**{current_streak}** từ nối thành công", inline=False)
                
                # Send embed
                await channel.send(embed=embed)
                
                # Give rewards to all players who participated
                if game_data.get('players'):
                    await self.distribute_streak_rewards(guild_id, game_data['players'], current_streak, channel)
                
                # Reset streak and start new round
                self.streak[guild_id] = 0
                await self.start_new_round(guild_id, channel)
                await self.save_game_state(guild_id, channel.id)
            
        except asyncio.CancelledError:
            log(f"TIMER_CANCEL [Guild {guild_id}] Next player made move")
            # Clean up timer message
            try:
                game_data = self.games.get(guild_id)
                if game_data and game_data.get('timer_message'):
                    await game_data['timer_message'].delete()
            except:
                pass
        except Exception as e:
            log(f"Timer error [Guild {guild_id}]: {e}")

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
            # Process word validation and game logic
            result = await self._process_word(message, guild_id, game)
            
            # Auto-save game state after each valid move (persistence)
            if result == "valid_move":
                try:
                    await self.save_game_state(guild_id, message.channel.id)
                except Exception as e:
                    log(f"ERROR auto-saving game state: {e}")
    
    async def _process_word(self, message, guild_id, game):
        """Process word validation and game logic. Returns 'valid_move' if word was accepted."""
        try:
            # Re-check game state after acquiring lock (game might have ended)
            if guild_id not in self.games:
                return "game_ended"
            
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
                return "invalid_format"
            
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
                return "command_prefix"

            # Anti-Self-Play
            if message.author.id == game['last_author_id']:
                log(f"SELF_PLAY [Guild {guild_id}] {message.author.name} tried self-play")
                try:
                    await message.add_reaction("❌")
                except:
                    pass
                await message.reply("Ko được tự reply, chờ người khác nhé", delete_after=5)
                return "self_play"

            current_word = game['current_word']
            last_syllable = current_word.split()[-1].lower()
            first_syllable = content.split()[0].lower()

            # Check connection
            if first_syllable != last_syllable:
                log(f"WRONG_CONNECTION [Guild {guild_id}] {message.author.name}: '{content}' needs to start with '{last_syllable}'")
                try:
                    await message.add_reaction("❌")
                except:
                    pass
                await message.reply(f"Từ phải bắt đầu bằng **{last_syllable}**", delete_after=3)
                return "wrong_connection"

            # Check used
            if content in game['used_words']:
                log(f"ALREADY_USED [Guild {guild_id}] {message.author.name}: '{content}'")
                try:
                    await message.add_reaction("❌")
                except:
                    pass
                await message.reply("Từ này dùng rồi, tìm từ khác đi", delete_after=3)
                return "already_used"

            # Check dictionary
            if not await self.check_word_in_db(content):
                log(f"NOT_IN_DICT [Guild {guild_id}] {message.author.name}: '{content}'")
                try:
                    await message.add_reaction("❌")
                except:
                    pass
                
                # Import QuickAddWordView from add_word cog
                try:
                    from cogs.noi_tu.add_word import QuickAddWordView
                    view = QuickAddWordView(content, message.author, self.bot)
                    await message.reply(
                        f"Từ **{content}** không có trong từ điển. Bạn muốn gửi admin thêm từ này?",
                        view=view,
                        delete_after=10
                    )
                except Exception as e:
                    log(f"ERROR showing add word view: {e}")
                    await message.reply("Từ này ko có trong từ điển, bruh", delete_after=3)
                return "not_in_dict"

            # === VALID MOVE ===
            try:
                await message.add_reaction("✅")
            except:
                pass
            
            # Initialize streak counter if not exists
            if guild_id not in self.streak:
                self.streak[guild_id] = 0
            
            # Increment streak on valid move
            self.streak[guild_id] += 1
            current_streak = self.streak[guild_id]
            
            log(f"VALID_MOVE [Guild {guild_id}] {message.author.name}: '{content}' (Streak: {current_streak}, Players: {game['player_count'] + 1})")
            
            # Track player with word count
            if message.author.id not in game['players']:
                game['players'][message.author.id] = {"username": message.author.name, "correct_words": 0}
            
            # Increment correct word count for this player (only for end-of-game bonus, not for immediate reward)
            game['players'][message.author.id]["correct_words"] += 1
            
            # Update player stats (correct word count)
            await self.update_player_stats(message.author.id, message.author.name, is_winner=False)
            
            # Cancel old timer
            if game['timer_task']:
                game['timer_task'].cancel()
                try:
                    if game.get('timer_message'):
                        await game['timer_message'].delete()
                        game['timer_message'] = None
                except:
                    pass
                log(f"TIMER_RESET [Guild {guild_id}] Old timer cancelled")
            
            # Update player count
            game['player_count'] += 1
            
            # Notify when Player 2 joins
            if game['player_count'] == 2:
                try:
                    await message.channel.send("🎮 Nối từ bắt đầu!")
                except:
                    pass
            
            # Update game state
            game['current_word'] = content
            game['used_words'].add(content)
            game['last_author_id'] = message.author.id
            game['last_message_time'] = time.time()
            
            # === MILESTONE REWARD (Cứ 10 từ thành công) ===
            if current_streak > 0 and current_streak % 10 == 0:
                try:
                    economy_cog = self.bot.get_cog("EconomyCog")
                    is_buff_active = await economy_cog.is_harvest_buff_active(guild_id)
                    milestone_reward = 20 * (2 if is_buff_active else 1)
                    
                    await message.channel.send(f"🔥 **MILESTONE! Chuỗi {current_streak}!** Cả phòng nhận được **{milestone_reward} Hạt**! 🎉")
                    # Distribute milestone reward to all players
                    for player_id in game['players'].keys():
                        await economy_cog.add_seeds_local(player_id, milestone_reward)
                except Exception as e:
                    log(f"ERROR awarding milestone: {e}")
            
            # Save game state
            await self.save_game_state(guild_id, message.channel.id)
            
            # Check Dead End
            has_next = await self.check_if_word_has_next(content, game['used_words'])
            
            if not has_next:
                last_syllable = content.split()[-1]
                log(f"DEAD_END [Guild {guild_id}] No words starting with '{last_syllable}' - Streak ended at {current_streak}")
                
                # Embed for end-of-streak
                embed = discord.Embed(
                    title="🛑 BÍ TỪ!",
                    description=f"Không có từ nào bắt đầu bằng **{last_syllable}**.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="🔥 Chuỗi Cộng Đồng",
                    value=f"Chuỗi **{current_streak}** từ kết thúc!",
                    inline=False
                )
                embed.add_field(
                    name="👤 Người cuối cùng",
                    value=message.author.mention,
                    inline=False
                )
                
                await message.channel.send(embed=embed)
                
                # Distribute rewards to all participants
                if game.get('players'):
                    await self.distribute_streak_rewards(guild_id, game['players'], current_streak, message.channel)
                
                # Reset and start new round
                self.streak[guild_id] = 0
                self.cleanup_game_lock(guild_id)
                await self.start_new_round(guild_id, message.channel)
                await self.save_game_state(guild_id, message.channel.id)
                return "valid_move"
            
            # Start timer only after 2nd player joins
            if game['player_count'] >= 2:
                log(f"TIMER_START [Guild {guild_id}] ({game['player_count']} players) - 25s countdown")
                game['timer_task'] = asyncio.create_task(self.game_timer(guild_id, message.channel, time.time()))
            else:
                log(f"WAITING_P2 [Guild {guild_id}] ({game['player_count']}/2)")
                try:
                    await message.channel.send(f"👥 Chờ người chơi thứ 2... ({game['player_count']}/2)")
                except:
                    pass
            
            return "valid_move"
        
        except Exception as e:
            log(f"ERROR [Guild {guild_id}] Exception in _process_word: {str(e)}")
            import traceback
            traceback.print_exc()
            return "error"

async def setup(bot):
    await bot.add_cog(GameNoiTu(bot))
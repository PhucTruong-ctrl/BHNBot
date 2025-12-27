import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio
import random
import json
import time
import os
import traceback
from datetime import datetime
from database_manager import db_manager, get_stat, get_or_create_user
from core.logger import setup_logger

logger = setup_logger("NoiTu", "cogs/noitu.log")

DB_PATH = os.path.abspath("./data/database.db")
WORDS_DICT_PATH = os.path.abspath("./data/words_dict.json")

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
        logger.info("Cog loaded, scheduling game initialization")
        # Schedule initialization as a background task
        asyncio.create_task(self._initialize_games_on_load())

    async def _initialize_games_on_load(self):
        """Initialize games after cog is loaded - called as background task"""
        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            logger.info("Bot is ready - initializing NoiTu games")
            
            # Load dictionary
            async with self.dict_load_lock:
                await self._load_dictionary()
            
            if not self.dict_loaded:
                logger.info("⚠️  Dictionary not loaded, skipping game initialization")
                return
            
            # Initialize games
            logger.info("Auto-initializing games for configured servers")
            try:
                rows = await db_manager.execute("SELECT guild_id, noitu_channel_id FROM server_config WHERE noitu_channel_id IS NOT NULL")
                
                if not rows:
                    logger.info("⚠️  No NoiTu channels configured in database")
                    return
                
                initialized_count = 0
                for guild_id, channel_id in rows:
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        logger.info(f"⚠️  Channel {channel_id} not found for guild {guild_id}")
                        continue
                    
                    if guild_id in self.games:
                        logger.info(f"⏭️  Game already initialized for guild {guild_id}, skipping")
                        continue
                    
                    try:
                        # Try to restore game state from database first
                        is_restored = await self.restore_game_state(guild_id, channel)
                        if not is_restored:
                            # If no saved state, start fresh
                            await self.start_new_round(guild_id, channel)
                        logger.info(f"✅ Game initialized for guild {guild_id} (restored={is_restored})")
                        initialized_count += 1
                    except Exception as e:
                        logger.info(f"❌ Failed to initialize game for guild {guild_id}: {e}")
                
                logger.info(f"Auto-initialization complete: {initialized_count}/{len(rows)} games initialized")
                self._initialized = True
            except Exception as e:
                logger.error(f"ERROR in initialization loop: {e}")
        except Exception as e:
            logger.error(f"FATAL ERROR in _initialize_games_on_load: {e}", exc_info=True)

    async def _load_dictionary(self):
        """Load words dictionary from file (non-blocking)"""
        try:
            def load_json():
                with open(WORDS_DICT_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)

            loop = asyncio.get_running_loop()
            self.words_dict = await loop.run_in_executor(None, load_json)
            
            # Clear old lists
            self.all_words.clear()
            self.all_words_list.clear()
            
            # Build set of all words for random selection (CPU intensive, run in executor too?)
            # Ideally yes, but let's do it in the same executor call for simplicity next time. 
            # For now, we'll keep it here but note it might be slightly blocking if dict is HUGE.
            # actually better to move all processing to executor
            
            def process_words(words_dict):
                all_words = set()
                all_words_list = []
                for first, seconds in words_dict.items():
                    for second in seconds:
                        word = f"{first} {second}"
                        all_words.add(word)
                        all_words_list.append(word)
                return all_words, all_words_list

            self.all_words, self.all_words_list = await loop.run_in_executor(None, process_words, self.words_dict)
            
            self.dict_loaded = True
            logger.info(f"✅ Loaded words dict: {len(self.words_dict)} starting syllables, {len(self.all_words)} total words")
            return True
        except FileNotFoundError:
            logger.error(f"❌ ERROR: {WORDS_DICT_PATH} not found. Run: python build_words_dict.py")
            self.dict_loaded = False
            return False
        except Exception as e:
            logger.error(f"❌ ERROR loading words dict: {e}")
            self.dict_loaded = False
            return False


    # --- Helper Functions ---
    async def get_config_channel(self, guild_id):
        from database_manager import get_server_config
        return await get_server_config(guild_id, "noitu_channel_id")

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
            
            logger.info(f"Reloaded words dict: {len(self.all_words)} total words")
        except Exception as e:
            logger.error(f"ERROR reloading words dict: {e}")
    
    def cleanup_game_lock(self, guild_id):
        """Clean up lock after game ends (prevent memory leak)
        
        NOTE: Actually, deleting locks is dangerous while async operations might be waiting on them.
        For now, we will NOT delete them. A few lock objects (one per active guild) is negligible memory.
        """
        pass
        # if guild_id in self.game_locks:
        #     del self.game_locks[guild_id]
    
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
            
            # Check if session exists
            existing = await db_manager.fetchone(
                "SELECT id FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                (guild_id, "noitu")
            )
            
            if existing:
                # Update existing session
                await db_manager.modify(
                    "UPDATE game_sessions SET channel_id = ?, game_state = ?, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ? AND game_type = ?",
                    (channel_id, game_state_json, guild_id, "noitu")
                )
            else:
                # Insert new session
                await db_manager.modify(
                    "INSERT INTO game_sessions (guild_id, game_type, channel_id, game_state) VALUES (?, ?, ?, ?)",
                    (guild_id, "noitu", channel_id, game_state_json)
                )
            
            logger.info(f"GAME_SAVED [Guild {guild_id}] Current word: {game.get('current_word')}, Used: {len(game.get('used_words', set()))}")
        except Exception as e:
            logger.error(f"ERROR saving game state: {e}")
    
    async def restore_game_state(self, guild_id, channel):
        """Restore NoiTu game state from database after bot restart.
        
        Uses smart message handling:
        - If old message is the LATEST in channel -> EDIT it (no notification spam)
        - If other messages came after -> Delete old, send new
        """
        try:
            row = await db_manager.fetchone(
                "SELECT game_state FROM game_sessions WHERE guild_id = ? AND game_type = ?",
                (guild_id, "noitu")
            )
            
            if not row:
                logger.info(f"NO_SAVE_FOUND [Guild {guild_id}] Starting fresh game")
                return False
            
            game_state = json.loads(row[0])
            old_message_id = game_state.get("start_message_id")
            resume_content = f"Từ hiện tại: **{game_state.get('current_word')}**\n[Game được resume từ lần restart trước]"
            
            # Restore game state first
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
                "start_message_content": resume_content,
                "players": new_players
            }
            
            # Smart message handling
            resume_msg = None
            
            if old_message_id:
                try:
                    # Check if old message is the latest in channel
                    last_messages = [msg async for msg in channel.history(limit=1)]
                    
                    if last_messages and last_messages[0].id == old_message_id:
                        # Old message IS the latest -> just EDIT it
                        old_msg = await channel.fetch_message(old_message_id)
                        await old_msg.edit(content=resume_content)
                        resume_msg = old_msg
                        logger.info(f"RESUME_EDIT [Guild {guild_id}] Edited existing message {old_message_id}")
                    else:
                        # Other messages came after -> delete old, send new
                        try:
                            old_msg = await channel.fetch_message(old_message_id)
                            await old_msg.delete()
                            logger.info(f"DELETED_OLD_MSG [Guild {guild_id}] Message {old_message_id} (not latest)")
                        except discord.NotFound:
                            logger.info(f"OLD_MSG_NOT_FOUND [Guild {guild_id}] Message {old_message_id}")
                        except Exception as e:
                            logger.warning(f"COULD_NOT_DELETE [Guild {guild_id}] {old_message_id}: {e}")
                        
                        # Send new message
                        resume_msg = await channel.send(resume_content)
                        logger.info(f"SENT_NEW_RESUME_MSG [Guild {guild_id}] Message {resume_msg.id}")
                        
                except discord.NotFound:
                    # Old message doesn't exist -> send new
                    resume_msg = await channel.send(resume_content)
                    logger.info(f"OLD_MSG_DELETED_SEND_NEW [Guild {guild_id}]")
                except Exception as e:
                    logger.error(f"ERROR checking message: {e}")
                    resume_msg = await channel.send(resume_content)
            else:
                # No old message ID -> send new
                resume_msg = await channel.send(resume_content)
                logger.info(f"NO_OLD_MSG_SEND_NEW [Guild {guild_id}]")
            
            self.games[guild_id]["start_message"] = resume_msg
            
            # Save updated game state with new message ID
            await self.save_game_state(guild_id, channel.id)
            
            logger.info(f"GAME_RESUMED [Guild {guild_id}] Current word: {game_state.get('current_word')}, Used: {len(game_state.get('used_words', []))}")
            return True
        except Exception as e:
            logger.error(f"ERROR restoring game state: {e}")
            return False

    
    async def update_player_stats(self, user_id, username, is_winner=False):
        """Update player stats: wins and correct words count"""
        try:
            # Ensure user exists in database
            user = await get_or_create_user(user_id, username)
            if not user:
                logger.error(f"ERROR: Failed to create/get user {username} ({user_id})")
                return
            
            # Update correct_words
            await self.increment_stat(user_id, 'correct_words', 1)
            
            logger.info(f"STATS_UPDATE [User {username}] WordsCorrect: +1")
        except Exception as e:
            logger.error(f"ERROR updating player stats: {e}")
    
    
    async def distribute_streak_rewards(self, guild_id, all_players, final_streak, channel):
        """Distribute rewards based on community streak (Co-op system)
        - Base reward: 5 hạt × streak (minimum 20 hạt) - INCREASED from 2
        - Bonus: 3 hạt per correct word per player - INCREASED from 1
        - All rewards multiplied by buff if active
        """
        try:
            economy_cog = self.bot.get_cog("EconomyCog")
            if not economy_cog:
                logger.error(f"ERROR: EconomyCog not found")
                return
            
            # Check if harvest buff is active
            is_buff_active = await economy_cog.is_harvest_buff_active(guild_id)
            buff_multiplier = 2 if is_buff_active else 1
            
            # Calculate base reward: 5 seeds per word in final streak (INCREASED from 2)
            base_reward = max(20, final_streak * 5) * buff_multiplier
            
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
                    
                    # Calculate reward: base + bonus for each correct word (INCREASED x3)
                    bonus_reward = correct_words * 3 * buff_multiplier
                    total_reward = base_reward + bonus_reward
                    
                    await economy_cog.add_seeds_local(user_id, total_reward)
                    
                    # Format for display: @mention - X từ (Y Hạt)
                    try:
                        user = await self.bot.fetch_user(user_id)
                        player_display_list.append(f"{user.mention} - {correct_words} từ")
                    except Exception as e:
                        player_display_list.append(f"{username} - {correct_words} từ")
                    
                    logger.info(f"REWARD [Guild {guild_id}] {username}: {base_reward} base + {bonus_reward} bonus = {total_reward} total")
                except Exception as e:
                    logger.error(f"ERROR distributing reward: {e}")
            
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
                value=f"+{3 * buff_multiplier} Hạt mỗi từ nối đúng",
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
            logger.error(f"ERROR distributing streak rewards: {e}")
    
    async def distribute_rewards(self, guild_id, winner_id, all_players, channel):
        """Distribute seeds rewards after game ends"""
        try:
            economy_cog = self.bot.get_cog("EconomyCog")
            if not economy_cog:
                logger.error(f"ERROR: EconomyCog not found")
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
                logger.error(f"ERROR sending reward embed: {e}")
        
        except Exception as e:
            logger.error(f"ERROR distributing rewards: {e}")
    
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
                logger.error(f"ERROR: Bot not found in guild {guild.id}")
                return
            
            if not bot_member.guild_permissions.manage_roles:
                logger.error(f"ERROR: Bot missing MANAGE_ROLES permission in guild {guild.id}")
                return
            
            # Get top 3 players based on correct words
            rows = await db_manager.execute(
                "SELECT user_id, value FROM user_stats WHERE game_id = 'noitu' AND stat_key = 'correct_words' ORDER BY value DESC LIMIT 3"
            )
            
            top_players = [row[0] for row in rows]
            role_ids = [TOP_1_ROLE_ID, TOP_2_ROLE_ID, TOP_3_ROLE_ID]
            
            # Remove all ranking roles from all members
            for role_id in role_ids:
                role = guild.get_role(role_id)
                if not role:
                    logger.info(f"WARNING: Role {role_id} not found in guild {guild.id}")
                    continue
                
                # Check if role is above bot
                if role.position >= bot_member.top_role.position:
                    logger.error(f"ERROR: Role {role.name} ({role_id}) is above or equal to bot's highest role in guild {guild.id}")
                    continue
                
                for member in role.members:
                    try:
                        await member.remove_roles(role)
                        logger.info(f"ROLE_REMOVE [Guild {guild.id}] Removed {role.name} from {member.name}")
                    except discord.Forbidden:
                        logger.error(f"ERROR: No permission to remove {role.name} from {member.name}")
                    except Exception as e:
                        logger.error(f"ERROR removing role from {member.name}: {e}")
            
            # Assign roles to top 3
            for idx, user_id in enumerate(top_players):
                try:
                    member = guild.get_member(user_id)
                    if not member:
                        logger.info(f"WARNING: User {user_id} not found in guild {guild.id}")
                        continue
                    
                    role = guild.get_role(role_ids[idx])
                    if not role:
                        logger.info(f"WARNING: Role {role_ids[idx]} not found in guild {guild.id}")
                        continue
                    
                    # Check if role is above bot
                    if role.position >= bot_member.top_role.position:
                        logger.error(f"ERROR: Role {role.name} is above or equal to bot's highest role")
                        continue
                    
                    await member.add_roles(role)
                    logger.info(f"ROLE_ASSIGN [Guild {guild.id}] Top {idx+1}: {member.name} <- {role.name}")
                except discord.Forbidden as e:
                    logger.error(f"ERROR: No permission to assign role: {e}")
                except Exception as e:
                    logger.error(f"ERROR assigning role: {e}")
            
        except Exception as e:
            logger.error(f"ERROR updating ranking roles: {e}")

    async def start_new_round(self, guild_id, channel):
        """Initialize new round"""
        # Ensure dictionary is loaded
        if not self.dict_loaded or not self.all_words_list:
            logger.error(f"❌ ERROR: Dictionary empty for guild {guild_id} (loaded={self.dict_loaded}, words={len(self.all_words_list)})")
            # Try to reload dictionary
            async with self.dict_load_lock:
                await self._load_dictionary()
            
            # If still empty, can't start game
            if not self.all_words_list:
                await channel.send("❌ Lỗi: Từ điển chưa được load. Vui lòng thử lại sau!")
                return
        
        word = await self.get_valid_start_word()
        if not word:
            logger.error(f"❌ ERROR: Could not get start word for guild {guild_id}")
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
        
        logger.info(f"GAME_START [Guild {guild_id}] Starting word: '{word}'")
        msg = await channel.send(self.games[guild_id]["start_message_content"])
        self.games[guild_id]["start_message"] = msg
        
        # Save game state with message ID
        await self.save_game_state(guild_id, channel.id)
        
        # Update ranking roles after game ends
        try:
            guild = channel.guild
            await self.update_ranking_roles(guild)
        except Exception as e:
            logger.error(f"ERROR updating roles: {e}")

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
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
                    logger.info(f"TIMER_SKIP [Guild {guild_id}] New message received, timer cancelled")
                    return
                
                # Edit message with countdown
                try:
                    if countdown > 0:
                        await timer_msg.edit(content=f"{countdown} giây...")
                    else:
                        await timer_msg.edit(content="Hết giờ!")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
            
            # Timer ended - calculate winner
            game_data = self.games.get(guild_id)
            if game_data and game_data['last_author_id']:
                current_streak = self.streak.get(guild_id, 0)
                word = game_data['current_word']
                
                logger.info(f"TIMEOUT [Guild {guild_id}] Streak ended at {current_streak} words, last word: '{word}'")
                
                # Delete old timer message
                try:
                    await timer_msg.delete()
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                
                # Create timeout embed
                embed = discord.Embed(
                    title="⌛ HẾT GIỜ!",
                    description=f"Không ai nối được từ **{word}**!",
                    color=discord.Color.red()
                )
                
                try:
                    last_player = await self.bot.fetch_user(game_data['last_author_id'])
                    embed.add_field(name="👤 Người giữ lượt cuối", value=last_player.mention, inline=False)
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                
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
            logger.info(f"TIMER_CANCEL [Guild {guild_id}] Next player made move")
            # Clean up timer message
            try:
                game_data = self.games.get(guild_id)
                if game_data and game_data.get('timer_message'):
                    await game_data['timer_message'].delete()
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
        except Exception as e:
            logger.error(f"Timer error [Guild {guild_id}]: {e}")

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
                logger.info(f"GAME_RELOAD [Guild {guild_id}] Loading from DB after restart")
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
                    logger.error(f"ERROR auto-saving game state: {e}")
    
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
                logger.info(f"SKIP [Guild {guild_id}] {message.author.name}: '{content}' (not 2 words)")
                # Refresh sticky start message if game is in round 1
                if game['player_count'] == 0:
                    try:
                        if game.get('start_message'):
                            await game['start_message'].delete()
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
                    msg = await message.channel.send(game["start_message_content"])
                    game['start_message'] = msg
                return "invalid_format"
            
            # Skip if starts with command prefix
            if content.startswith(('!', '/')):
                logger.info(f"SKIP [Guild {guild_id}] {message.author.name}: '{content}' (command prefix)")
                # Refresh sticky start message if game is in round 1
                if game['player_count'] == 0:
                    try:
                        if game.get('start_message'):
                            await game['start_message'].delete()
                    except Exception as e:
                        logger.error(f"Unexpected error: {e}")
                    msg = await message.channel.send(game["start_message_content"])
                    game['start_message'] = msg
                return "command_prefix"

            # Anti-Self-Play
            if message.author.id == game['last_author_id']:
                logger.info(f"SELF_PLAY [Guild {guild_id}] {message.author.name} tried self-play")
                try:
                    await message.add_reaction("❌")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                await message.reply("Ko được tự reply, chờ người khác nhé", delete_after=5)
                return "self_play"

            current_word = game['current_word']
            last_syllable = current_word.split()[-1].lower()
            first_syllable = content.split()[0].lower()

            # Check connection
            if first_syllable != last_syllable:
                logger.info(f"WRONG_CONNECTION [Guild {guild_id}] {message.author.name}: '{content}' needs to start with '{last_syllable}'")
                try:
                    await message.add_reaction("❌")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                await message.reply(f"Từ phải bắt đầu bằng **{last_syllable}**", delete_after=3)
                return "wrong_connection"

            # Check used
            if content in game['used_words']:
                logger.info(f"ALREADY_USED [Guild {guild_id}] {message.author.name}: '{content}'")
                try:
                    await message.add_reaction("❌")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                await message.reply("Từ này dùng rồi, tìm từ khác đi", delete_after=3)
                return "already_used"

            # Check dictionary
            if not await self.check_word_in_db(content):
                logger.info(f"NOT_IN_DICT [Guild {guild_id}] {message.author.name}: '{content}'")
                try:
                    await message.add_reaction("❌")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                
                # Track invalid words for achievement
                await self.increment_stat(message.author.id, 'invalid_words', 1)
                
                # Check invalid words achievement
                try:
                    current_invalid = await get_stat(message.author.id, 'noitu', 'invalid_words')
                    await self.bot.achievement_manager.check_unlock(message.author.id, "noitu", "invalid_words", current_invalid, message.channel)
                except Exception as e:
                    logger.error(f"ERROR checking invalid_words achievement: {e}")
                
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
                    logger.error(f"ERROR showing add word view: {e}")
                    await message.reply("Từ này ko có trong từ điển, bruh", delete_after=3)
                return "not_in_dict"

            # === VALID MOVE ===
            try:
                await message.add_reaction("✅")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            # Initialize streak counter if not exists
            if guild_id not in self.streak:
                self.streak[guild_id] = 0
            
            # Increment streak on valid move
            self.streak[guild_id] += 1
            current_streak = self.streak[guild_id]
            
            logger.info(f"VALID_MOVE [Guild {guild_id}] {message.author.name}: '{content}' (Streak: {current_streak}, Players: {game['player_count'] + 1})")
            
            # Track player with word count
            if message.author.id not in game['players']:
                game['players'][message.author.id] = {"username": message.author.name, "correct_words": 0}
            
            # Increment correct word count for this player (only for end-of-game bonus, not for immediate reward)
            game['players'][message.author.id]["correct_words"] += 1
            
            # Update player stats (correct word count)
            await self.update_player_stats(message.author.id, message.author.name, is_winner=False)
            
            # Track additional achievement stats
            user_id = message.author.id
            
            # 1. Track game starters (first player in new game)
            if game['player_count'] == 0:  # First player
                await self.increment_stat(user_id, 'game_starters', 1)
            
            # 2. Track low time answers (clutch moments) - under 3 seconds left (Timer is 60s)
            if game.get('last_message_time'):
                time_since_last = time.time() - game['last_message_time']
                if time_since_last > 57.0:  # More than 57 seconds passed (less than 3s left)
                    await self.increment_stat(user_id, 'low_time_answers', 1)
            
            # 2.5. Track fast answers - under 5 seconds
            if game.get('last_message_time'):
                time_since_last = time.time() - game['last_message_time']
                if time_since_last < 5.0:  # Less than 5 seconds
                    await self.increment_stat(user_id, 'fast_answers', 1)
            
            # 3. Track night answers (0-5 AM)
            current_hour = datetime.now().hour
            if current_hour >= 0 and current_hour <= 5:
                await self.increment_stat(user_id, 'night_answers', 1)
            
            # 4. Track reduplicative words (từ láy)
            if await self.is_reduplicative_word(content):
                await self.increment_stat(user_id, 'reduplicative_words', 1)
            
            # Check achievements
            try:
                current_words = await get_stat(user_id, 'noitu', 'correct_words')
                await self.bot.achievement_manager.check_unlock(user_id, "noitu", "correct_words", current_words, message.channel)
                
                if game['player_count'] == 0:  # First player
                    current_starters = await get_stat(user_id, 'noitu', 'game_starters')
                    await self.bot.achievement_manager.check_unlock(user_id, "noitu", "game_starters", current_starters, message.channel)
                
                if game.get('last_message_time') and (time.time() - game['last_message_time']) > 57.0:
                    current_low_time = await get_stat(user_id, 'noitu', 'low_time_answers')
                    await self.bot.achievement_manager.check_unlock(user_id, "noitu", "low_time_answers", current_low_time, message.channel)
                
                if game.get('last_message_time') and (time.time() - game['last_message_time']) < 5.0:
                    current_fast = await get_stat(user_id, 'noitu', 'fast_answers')
                    await self.bot.achievement_manager.check_unlock(user_id, "noitu", "fast_answers", current_fast, message.channel)
                
                if current_hour >= 0 and current_hour <= 5:
                    current_night = await get_stat(user_id, 'noitu', 'night_answers')
                    await self.bot.achievement_manager.check_unlock(user_id, "noitu", "night_answers", current_night, message.channel)
                
                if await self.is_reduplicative_word(content):
                    current_reduplicative = await get_stat(user_id, 'noitu', 'reduplicative_words')
                    await self.bot.achievement_manager.check_unlock(user_id, "noitu", "reduplicative_words", current_reduplicative, message.channel)
                    
            except Exception as e:
                logger.error(f"ERROR checking achievements for {user_id}: {e}")
            
            # Cancel old timer
            if game['timer_task']:
                game['timer_task'].cancel()
                try:
                    if game.get('timer_message'):
                        await game['timer_message'].delete()
                        game['timer_message'] = None
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                logger.info(f"TIMER_RESET [Guild {guild_id}] Old timer cancelled")
            
            # Update player count
            game['player_count'] += 1
            
            # Notify when Player 2 joins
            if game['player_count'] == 2:
                try:
                    await message.channel.send("🎮 Nối từ bắt đầu!")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
            
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
                    logger.error(f"ERROR awarding milestone: {e}")
            
            # Save game state
            await self.save_game_state(guild_id, message.channel.id)
            
            # Check Dead End
            has_next = await self.check_if_word_has_next(content, game['used_words'])
            
            if not has_next:
                last_syllable = content.split()[-1]
                logger.info(f"DEAD_END [Guild {guild_id}] No words starting with '{last_syllable}' - Streak ended at {current_streak}")
                
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
                
                # Track game ending words for the last player
                await self.increment_stat(message.author.id, 'game_ending_words', 1)
                
                # Check game ending words achievement
                try:
                    current_ending = await get_stat(message.author.id, 'noitu', 'game_ending_words')
                    await self.bot.achievement_manager.check_unlock(message.author.id, "noitu", "game_ending_words", current_ending, message.channel)
                except Exception as e:
                    logger.error(f"ERROR checking game_ending_words achievement: {e}")
                
                # Track long chain participation if streak >= 50
                if current_streak >= 50:
                    for player_id in game['players'].keys():
                        await self.increment_stat(player_id, 'long_chain_participation', 1)
                        # Check long chain participation achievement
                        try:
                            current_long_chain = await get_stat(player_id, 'noitu', 'long_chain_participation')
                            await self.bot.achievement_manager.check_unlock(player_id, "noitu", "long_chain_participation", current_long_chain, message.channel)
                        except Exception as e:
                            logger.error(f"ERROR checking long_chain_participation achievement for {player_id}: {e}")
                
                
                # Update max_streak ONLY for the winner (last player standing)
                try:
                    winner_id = message.author.id
                    updated = await self.update_max_stat(winner_id, 'max_streak', current_streak)
                    if updated:
                        # Check max_streak achievement for winner only
                        new_max_streak = await get_stat(winner_id, 'noitu', 'max_streak')
                        await self.bot.achievement_manager.check_unlock(winner_id, "noitu", "max_streak", new_max_streak, message.channel)
                except Exception as e:
                    logger.error(f"ERROR updating max_streak for winner {winner_id}: {e}")

                
                # Distribute rewards to all participants
                if game.get('players'):
                    await self.distribute_streak_rewards(guild_id, game['players'], current_streak, message.channel)
                
                # Reset and start new round
                self.streak[guild_id] = 0
                self.cleanup_game_lock(guild_id)
                await self.start_new_round(guild_id, message.channel)
                await self.save_game_state(guild_id, message.channel.id)
                return "valid_move"
            
            # DISABLED: 60s timer removed per user request - game only ends on dead-end word
            # Timer was causing pressure on small servers
            # if game['player_count'] >= 2:
            #     logger.info(f"TIMER_START [Guild {guild_id}] ({game['player_count']} players) - 60s countdown")
            #     game['timer_task'] = asyncio.create_task(self.game_timer(guild_id, message.channel, time.time()))
            # else:
            #     logger.info(f"WAITING_P2 [Guild {guild_id}] ({game['player_count']}/2)")
            #     try:
            #         await message.channel.send(f"👥 Chờ người chơi thứ 2... ({game['player_count']}/2)")
            #     except Exception as e:
            #         logger.error(f"Unexpected error: {e}")
            
            # Just log player count without timer
            logger.info(f"PLAYER_JOINED [Guild {guild_id}] ({game['player_count']} players) - No timer")
            
            return "valid_move"
        
        except Exception as e:
            logger.error(f"ERROR [Guild {guild_id}] Exception in _process_word: {str(e)}", exc_info=True)
            return "error"

    # Helper functions for achievement stats tracking
    async def increment_stat(self, user_id, stat_key, value):
        """Tăng giá trị stat cho user trong game noitu"""
        try:
            game_id = 'noitu'
            logger.info(f"[NoiTu] Incrementing stat {stat_key} for user {user_id} by {value}")
            
            # Đảm bảo record tồn tại
            sql_check = "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?"
            row = await db_manager.fetchone(sql_check, (user_id, game_id, stat_key))
            
            if row:
                current_value = row[0]
                new_value = current_value + value
                sql_update = "UPDATE user_stats SET value = value + ? WHERE user_id = ? AND game_id = ? AND stat_key = ?"
                await db_manager.modify(sql_update, (value, user_id, game_id, stat_key))
                logger.info(f"[NoiTu] Updated stat {stat_key} from {current_value} to {new_value}")
            else:
                sql_insert = "INSERT INTO user_stats (user_id, game_id, stat_key, value) VALUES (?, ?, ?, ?)"
                await db_manager.modify(sql_insert, (user_id, game_id, stat_key, value))
                logger.info(f"[NoiTu] Inserted new stat {stat_key} with value {value}")
        except Exception as e:
            logger.error(f"[NoiTu] Error updating stat {stat_key} for {user_id}: {e}")
    
    async def update_max_stat(self, user_id, stat_key, new_value):
        """Update stat to max value (only if new_value > current_value)"""
        try:
            game_id = 'noitu'
            logger.info(f"[NoiTu] Updating max stat {stat_key} for user {user_id} to {new_value}")
            
            # Check current value
            sql_check = "SELECT value FROM user_stats WHERE user_id = ? AND game_id = ? AND stat_key = ?"
            row = await db_manager.fetchone(sql_check, (user_id, game_id, stat_key))
            
            if row:
                current_value = row[0]
                if new_value > current_value:
                    sql_update = "UPDATE user_stats SET value = ? WHERE user_id = ? AND game_id = ? AND stat_key = ?"
                    await db_manager.modify(sql_update, (new_value, user_id, game_id, stat_key))
                    logger.info(f"[NoiTu] Updated max stat {stat_key} from {current_value} to {new_value}")
                    return True
                else:
                    logger.info(f"[NoiTu] Max stat {stat_key} not updated (current: {current_value}, new: {new_value})")
                    return False
            else:
                sql_insert = "INSERT INTO user_stats (user_id, game_id, stat_key, value) VALUES (?, ?, ?, ?)"
                await db_manager.modify(sql_insert, (user_id, game_id, stat_key, new_value))
                logger.info(f"[NoiTu] Inserted new max stat {stat_key} with value {new_value}")
                return True
        except Exception as e:
            logger.error(f"[NoiTu] Error updating max stat {stat_key} for {user_id}: {e}")
            return False
    
    async def is_reduplicative_word(self, word):
        """Check if word is reduplicative (từ láy) like 'xinh xắn', 'lung linh'"""
        try:
            parts = word.split()
            if len(parts) != 2:
                return False
            
            first, second = parts
            # Simple check: if both parts have same consonants and similar vowels
            # This is a basic implementation - can be improved
            if len(first) == len(second) and first[0] == second[0]:  # Same starting consonant
                return True
            return False
        except Exception as e:
            return False

    @app_commands.command(name="resetnoitu", description="Reset game nối từ (mọi người đều dùng được)")
    async def reset_noitu(self, interaction: discord.Interaction):
        """Reset game nối từ - available to everyone with 5min anti-troll protection."""
        guild_id = interaction.guild_id
        
        # Check if game exists
        if guild_id not in self.games:
            await interaction.response.send_message(
                "❌ Không có game nào đang chạy trong server này!",
                ephemeral=True
            )
            return
        
        game = self.games[guild_id]
        
        # Anti-troll: Check if game is active (last message within 5 minutes)
        if game.get('last_message_time'):
            time_since_last = time.time() - game['last_message_time']
            if time_since_last < 300:  # 5 minutes = 300 seconds
                remaining = int(300 - time_since_last)
                await interaction.response.send_message(
                    f"🛑 **Không thể reset!** Game đang sôi động.\n"
                    f"Chờ thêm **{remaining}s** không có ai chơi mới được reset.\n"
                    f"*(Tránh phá đám người khác đang chơi)*",
                    ephemeral=True
                )
                return
        
        # Get channel and reset
        channel_id = game.get('channel_id')
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            await interaction.response.send_message(
                "❌ Không tìm thấy channel game!",
                ephemeral=True
            )
            return
        
        # Distribute rewards before reset if any players
        if game.get('players'):
            current_streak = self.streak.get(guild_id, 0)
            if current_streak > 0:
                await self.distribute_streak_rewards(guild_id, game['players'], current_streak, channel)
        
        # Reset streak and start new round
        self.streak[guild_id] = 0
        await self.start_new_round(guild_id, channel)
        await self.save_game_state(guild_id, channel_id)
        
        await interaction.response.send_message(
            f"🔄 **Game đã được reset bởi {interaction.user.display_name}!**\n"
            f"Từ mới đã được chọn. Chúc vui vẻ~",
            ephemeral=False
        )
        
        logger.info(f"[RESET_NOITU] User {interaction.user.id} reset game in guild {guild_id}")

async def setup(bot):
    await bot.add_cog(GameNoiTu(bot))
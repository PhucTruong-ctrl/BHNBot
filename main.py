import discord
import os
import asyncio
import subprocess
import logging
from discord.ext import commands
from dotenv import load_dotenv
from core.achievement_system import AchievementManager

# Load biến môi trường từ file .env
load_dotenv()

from core.logger import setup_logger
from core.timeout_monitor import get_monitor as get_timeout_monitor
from core.database import db_manager
from core.inventory_cache import InventoryCache

# 1. SETUP LOGGING
setup_logger("Main", "main.log")
logger = logging.getLogger("Main")

# 2. CREATE BOT
intents = discord.Intents.all()
# Optimize for USB tethering / unstable connections
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    heartbeat_timeout=90.0,  # Default 60s → 90s (more tolerant of lag spikes)
    chunk_guilds_at_startup=False  # Reduce initial load (only 1 server)
)

# 3. ATTACH DATABASE & INVENTORY CACHE
bot.db = db_manager
bot.inventory = InventoryCache(bot.db) # Singleton Injection
bot.achievement_manager = None # Will be set in setup_hooks.getenv("OWNER_ID", "0"))  # Load from .env
bot.owner_id = int(os.getenv("OWNER_ID", "0"))  # Load from .env
bot.cogs_loaded = False  # Flag to track if cogs are already loaded

# Command error handler with timeout monitoring
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors with timeout monitoring."""
    # Track timeout errors
    if isinstance(error, asyncio.TimeoutError):
        timeout_monitor = get_timeout_monitor()
        timeout_monitor.record_timeout(
            context="command_execution",
            user_id=ctx.author.id if ctx.author else None,
            command=ctx.command.name if ctx.command else "unknown"
        )
        logger.error(f"[TIMEOUT] Command timeout: {ctx.command} by user {ctx.author.id}")

# Bot ready event
@bot.event
async def on_ready():
    logger.info(f'Login successfully as: {bot.user} (ID: {bot.user.id})')
    logger.info('------')
    # Set trạng thái cho bot
    await bot.change_presence(activity=discord.Game(name="Cuộn len bên hiên nhà 🧶"))
    
    # Initialize Achievement Manager
    bot.achievement_manager = AchievementManager(bot)
    logger.info("✓ Achievement Manager initialized")
    
    # Preload Xi Dach Assets (to prevent render timeouts)
    try:
        from cogs.xi_dach.ui.render import assets as card_assets
        logger.info("Loading Xi Dach assets...")
        card_assets.load_assets()
        logger.info("✓ Xi Dach assets loaded")
    except Exception as e:
        logger.error(f"Failed to load Xi Dach assets: {e}")
    
    # Attach Discord logging handler (reads config from database)
    try:
        from core.logger import attach_discord_handler, get_log_config_from_db
        log_channel_id, ping_user_id, log_level = await get_log_config_from_db()
        if log_channel_id:
            attach_discord_handler(bot, log_channel_id, ping_user_id, log_level)
    except Exception as e:
        logger.error(f"Failed to attach Discord logging handler: {e}")

    # Load cogs on first ready only
    if not bot.cogs_loaded:
        await load_cogs()
        bot.cogs_loaded = True
    
    # NOTE: Slash commands sync manually via /sync or !sync command (see admin.py)
    # This prevents rate limits and gives control over when/where commands sync
    # After adding new slash commands, use: /sync guild (to sync to current server)
    # Or: /sync global (to sync globally to all servers)
    # Then restart Discord client (Ctrl+R) to see changes

# Hàm load các Cogs (Module)
async def load_cogs():
    logger.info("\n[LOADING COGS]")
    cogs_dir = './cogs'
    
    # Load top-level cogs
    # Note: admin cogs are now in cogs/admin/ subdirectory
    priority_cogs = []  # No priority cogs currently needed
    
    # Load priority cogs first
    for filename in priority_cogs:
        if os.path.exists(os.path.join(cogs_dir, filename)):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f'Loaded: {filename}')
            except Exception as e:
                logger.error(f'Error: {filename} - {e}')
    
    # Load remaining top-level cogs
    for filename in os.listdir(cogs_dir):
        filepath = os.path.join(cogs_dir, filename)
        if filename.endswith('.py') and filename != '__init__.py' and filename not in priority_cogs:
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f'Loaded: {filename}')
            except Exception as e:
                logger.error(f'Error: {filename} - {e}')
    
    # Load sub-module cogs (e.g., werewolf, noi_tu)
    for subdir in os.listdir(cogs_dir):
        subdir_path = os.path.join(cogs_dir, subdir)
        if os.path.isdir(subdir_path) and not subdir.startswith('__'):
            # Try loading cog.py first (for werewolf, fishing)
            cog_file = os.path.join(subdir_path, 'cog.py')
            if os.path.exists(cog_file):
                try:
                    await bot.load_extension(f'cogs.{subdir}.cog')
                    logger.info(f'Loaded: cogs.{subdir}.cog')
                except Exception as e:
                    logger.error(f'Error loading cogs.{subdir}.cog: {e}')
            
            # Skip helper files that don't have setup functions
            skip_files = {'__init__.py', 'cog.py', 'constants.py', 'helpers.py', 'events.py', 
                         'legendary.py', 'models.py', 'rod_system.py', 'views.py', 'consumables.py', 
                         'glitch.py', 'legendary_quest_helper.py', 'detector.py', 'task.py',
                         'statistics.py', 'game_logic.py', 'tree_manager.py', 'contributor_manager.py',
                         'game.py', 'card_renderer.py'}
            
            # Load additional module files in subdirectory (for noi_tu: noitu.py, add_word.py)
            for filename in os.listdir(subdir_path):
                if filename.endswith('.py') and filename not in skip_files:
                    module_name = filename[:-3]
                    try:
                        await bot.load_extension(f'cogs.{subdir}.{module_name}')
                        logger.info(f'Loaded: cogs.{subdir}.{module_name}')
                    except Exception as e:
                        logger.error(f'Error loading cogs.{subdir}.{module_name}: {e}')
    
    # List all commands in bot.tree after loading cogs
    logger.info("\n[SLASH COMMANDS REGISTERED]")
    all_commands = bot.tree.get_commands()
    
    # DEBUG: Also check cogs for app_commands
    logger.info(f"\nCogs loaded: {len(bot.cogs)}")
    slash_command_count = 0
    for cog_name, cog in bot.cogs.items():
        cog_slash_commands = 0
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if hasattr(attr, '__discord_app_commands__'):
                cog_slash_commands += 1
                slash_command_count += 1
        if cog_slash_commands > 0:
            logger.info(f"  - {cog_name}: {cog_slash_commands} slash command(s)")
    
    logger.info(f"\nbot.tree.get_commands(): {len(all_commands)} commands")
    if all_commands:
        for cmd in all_commands:
            logger.info(f"  - /{cmd.name}")
    else:
        logger.info("  (Ko có commands)")
    logger.info(f"  Total: {len(all_commands)}\n")

# Chạy bot
async def main():
    # Note: Database initialization is now done manually via command, not automatically on startup
    # This prevents data loss from repeated migrations on bot restart
    # To initialize database manually, run: python3 setup_data.py
    
    async with bot:
        # PHASE 1 OPTIMIZATION: Skip words dict rebuild if up-to-date
        dict_file = 'data/words_dict.json'
        source_file = 'data/tu_dien.txt'
        
        should_rebuild = True
        if os.path.exists(dict_file) and os.path.exists(source_file):
            dict_mtime = os.path.getmtime(dict_file)
            source_mtime = os.path.getmtime(source_file)
            
            if dict_mtime > source_mtime:
                logger.info("\n[WORDS_DICT] Up-to-date, skipping rebuild (-1s startup time)")
                should_rebuild = False
        
        if should_rebuild:
            logger.info("\n[REBUILDING WORDS DICT]")
            try:
                # Get the absolute path to the script
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_words_dict.py')
                result = subprocess.run([os.sys.executable, script_path], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
                logger.info(result.stdout)
                if result.returncode != 0:
                    logger.error(f"Error: {result.stderr}")
            except Exception as e:
                logger.error(f"Error building words dict: {e}")
        
        # Start bot (cogs will be loaded in on_ready)
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
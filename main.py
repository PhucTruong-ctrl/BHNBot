import discord
import os
import asyncio
import subprocess
import logging
from discord.ext import commands
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Configure logging centrally (used by werewolf and other modules)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Cấu hình Intent (Quyền hạn)
intents = discord.Intents.default()
intents.message_content = True # Bắt buộc để đọc tin nhắn nối từ
intents.members = True         # Bắt buộc để check Invite/Welcome

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot.owner_id = 598046112959430657  # Your Discord User ID
bot.cogs_loaded = False  # Flag to track if cogs are already loaded

# Hàm chạy khi Bot khởi động
@bot.event
async def on_ready():
    print(f'Login successfully as: {bot.user} (ID: {bot.user.id})')
    print('------')
    # Set trạng thái cho bot
    await bot.change_presence(activity=discord.Game(name="Cuộn len bên hiên nhà 🧶"))
    
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
    print("\n[LOADING COGS]")
    cogs_dir = './cogs'
    
    # Load top-level cogs (prioritize admin.py first for sync functionality)
    priority_cogs = ['admin.py']
    
    # Load priority cogs first
    for filename in priority_cogs:
        if os.path.exists(os.path.join(cogs_dir, filename)):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded: {filename}')
            except Exception as e:
                print(f'Error: {filename} - {e}')
    
    # Load remaining top-level cogs
    for filename in os.listdir(cogs_dir):
        filepath = os.path.join(cogs_dir, filename)
        if filename.endswith('.py') and filename != '__init__.py' and filename not in priority_cogs:
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded: {filename}')
            except Exception as e:
                print(f'Error: {filename} - {e}')
    
    # Load sub-module cogs (e.g., werewolf, noi_tu)
    for subdir in os.listdir(cogs_dir):
        subdir_path = os.path.join(cogs_dir, subdir)
        if os.path.isdir(subdir_path) and not subdir.startswith('__'):
            # Try loading cog.py first (for werewolf, fishing)
            cog_file = os.path.join(subdir_path, 'cog.py')
            if os.path.exists(cog_file):
                try:
                    await bot.load_extension(f'cogs.{subdir}.cog')
                    print(f'Loaded: cogs.{subdir}.cog')
                except Exception as e:
                    print(f'Error loading cogs.{subdir}.cog: {e}')
            
            # Skip helper files that don't have setup functions
            skip_files = {'__init__.py', 'cog.py', 'constants.py', 'helpers.py', 'events.py', 
                         'legendary.py', 'models.py', 'rod_system.py', 'views.py'}
            
            # Load additional module files in subdirectory (for noi_tu: noitu.py, add_word.py)
            for filename in os.listdir(subdir_path):
                if filename.endswith('.py') and filename not in skip_files:
                    module_name = filename[:-3]
                    try:
                        await bot.load_extension(f'cogs.{subdir}.{module_name}')
                        print(f'Loaded: cogs.{subdir}.{module_name}')
                    except Exception as e:
                        print(f'Error loading cogs.{subdir}.{module_name}: {e}')
    
    # List all commands in bot.tree after loading cogs
    print("\n[SLASH COMMANDS REGISTERED]")
    all_commands = bot.tree.get_commands()
    
    # DEBUG: Also check cogs for app_commands
    print(f"\nCogs loaded: {len(bot.cogs)}")
    slash_command_count = 0
    for cog_name, cog in bot.cogs.items():
        cog_slash_commands = 0
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if hasattr(attr, '__discord_app_commands__'):
                cog_slash_commands += 1
                slash_command_count += 1
        if cog_slash_commands > 0:
            print(f"  - {cog_name}: {cog_slash_commands} slash command(s)")
    
    print(f"\nbot.tree.get_commands(): {len(all_commands)} commands")
    if all_commands:
        for cmd in all_commands:
            print(f"  - /{cmd.name}")
    else:
        print("  (Ko có commands)")
    print(f"  Total: {len(all_commands)}\n")

# Chạy bot
async def main():
    # Note: Database initialization is now done manually via command, not automatically on startup
    # This prevents data loss from repeated migrations on bot restart
    # To initialize database manually, run: python3 setup_data.py
    
    async with bot:
        # Rebuild words dictionary before starting
        print("\n[REBUILDING WORDS DICT]")
        try:
            # Get the absolute path to the script
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_words_dict.py')
            result = subprocess.run([os.sys.executable, script_path], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
            print(result.stdout)
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"Error building words dict: {e}")
        
        # Start bot (cogs will be loaded in on_ready)
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
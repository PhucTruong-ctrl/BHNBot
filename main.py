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
    await bot.change_presence(activity=discord.Game(name="Chức năng khả dụng: Nối từ, Ma Sói."))
    
    # Load cogs on first ready only
    if not bot.cogs_loaded:
        await load_cogs()
        bot.cogs_loaded = True
    
    # NOTE: Slash commands sync manually only via /sync command (see admin.py)
    # This prevents rate limits and gives control over when/where commands sync
    # After adding new slash commands, use: /sync guild (test server) or /sync global (all servers)
    # Then restart Discord client (Ctrl+R) to see changes

# Hàm load các Cogs (Module)
async def load_cogs():
    print("\n[LOADING COGS]")
    cogs_dir = './cogs'
    
    # Load top-level cogs
    for filename in os.listdir(cogs_dir):
        filepath = os.path.join(cogs_dir, filename)
        if filename.endswith('.py') and filename != '__init__.py':
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded: {filename}')
            except Exception as e:
                print(f'Error: {filename} - {e}')
    
    # Load sub-module cogs (e.g., werewolf)
    for subdir in os.listdir(cogs_dir):
        subdir_path = os.path.join(cogs_dir, subdir)
        if os.path.isdir(subdir_path) and not subdir.startswith('__'):
            # Check if it has a cog.py file
            cog_file = os.path.join(subdir_path, 'cog.py')
            if os.path.exists(cog_file):
                try:
                    await bot.load_extension(f'cogs.{subdir}.cog')
                    print(f'Loaded: cogs.{subdir}.cog')
                except Exception as e:
                    print(f'Error loading cogs.{subdir}.cog: {e}')
    
    # List all commands in bot.tree after loading cogs
    print("\n[SLASH COMMANDS REGISTERED]")
    all_commands = bot.tree.get_commands()
    if all_commands:
        for cmd in all_commands:
            print(f"  - /{cmd.name}")
    else:
        print("  (Ko có commands)")
    print(f"  Total: {len(all_commands)}\n")

# Chạy bot
async def main():
    async with bot:
        # Rebuild words dictionary before starting
        print("\n[REBUILDING WORDS DICT]")
        try:
            result = subprocess.run(['python', 'build_words_dict.py'], capture_output=True, text=True)
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
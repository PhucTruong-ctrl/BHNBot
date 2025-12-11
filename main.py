import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Intent (Quyền hạn)
intents = discord.Intents.default()
intents.message_content = True # Bắt buộc để đọc tin nhắn nối từ
intents.members = True         # Bắt buộc để check Invite/Welcome

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Hàm chạy khi Bot khởi động
@bot.event
async def on_ready():
    print(f'✅ Đăng nhập thành công: {bot.user} (ID: {bot.user.id})')
    print('------')
    # Set trạng thái cho bot
    await bot.change_presence(activity=discord.Game(name="Tôi tên Thắng"))

# Hàm load các Cogs (Module)
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and filename != '__init__.py':
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'⚙️  Đã load module: {filename}')
            except Exception as e:
                print(f'❌ Lỗi load module {filename}: {e}')

# Chạy bot
async def main():
    async with bot:
        await load_cogs()
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Cho phép tắt bot bằng Ctrl+C
        pass

import discord
from discord.ext import commands
import logging

from database_manager import db_manager
from .views import ShopLauncher

logger = logging.getLogger("UnifiedShopCog")

class UnifiedShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Register Persistent View
        # We need to register it for the bot to listen to interactions after restart
        self.bot.add_view(ShopLauncher())
        
    async def cog_load(self):
        logger.info("UnifiedShopCog loaded & Persistent View registered.")

    async def deploy_interface(self, guild_id: int, channel_id: int):
        """
        Deploys or Updates the Shop Interface in the specified channel.
        """
        channel = self.bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except:
                logger.error(f"Cannot fetch shop channel {channel_id}")
                return False

        # Prepare Embed
        embed = discord.Embed(
            title="🏪 TẠP HÓA BÊN HIÊN NHÀ",
            description=(
                "Chào bạn! Đây là nơi bạn có thể tìm thấy mọi thứ.\n"
                "Từ cần câu, mồi cá, đến đồ trang trí nhà cửa.\n\n"
                "**Hướng dẫn:**\n"
                "1. Chọn danh mục ở menu bên dưới.\n"
                "2. Duyệt và mua vật phẩm.\n"
                "3. Kiểm tra túi đồ bằng lệnh `/tuido` hoặc nút bên dưới.\n\n"
                "*Chúc bạn mua sắm vui vẻ!*"
            ),
            color=0xf39c12
        )
        embed.set_image(url="https://media.discordapp.net/attachments/1118182745778249768/1126135899476004944/shop_banner.png?width=1200&height=400")
        
        # Check if message exists to update
        row = await db_manager.fetchrow(
            "SELECT shop_message_id FROM server_config WHERE guild_id = $1", 
            (guild_id,)
        )
        
        view = ShopLauncher()
        msg = None
        
        if row and row['shop_message_id']:
            try:
                old_msg = await channel.fetch_message(row['shop_message_id'])
                await old_msg.edit(embed=embed, view=view)
                msg = old_msg
                logger.info(f"Updated existing shop message {row['shop_message_id']}")
            except discord.NotFound:
                # Message deleted, send new
                pass
            except Exception as e:
                logger.error(f"Error editing shop message: {e}")
                
        if not msg:
            # Send new
            try:
                # Purge channel? Optional. Let's not be destructive unless requested.
                msg = await channel.send(embed=embed, view=view)
                
                # Save ID
                await db_manager.execute(
                    """
                    INSERT INTO server_config (guild_id, shop_channel_id, shop_message_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        shop_channel_id = EXCLUDED.shop_channel_id,
                        shop_message_id = EXCLUDED.shop_message_id
                    """,
                    (guild_id, channel_id, msg.id)
                )
                logger.info(f"Deployed new shop message {msg.id}")
            except Exception as e:
                logger.error(f"Failed to send shop message: {e}")
                return False
                
        return True

async def setup(bot):
    await bot.add_cog(UnifiedShopCog(bot))

import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import datetime
# from database_manager import remove_item (Removed)
# Replaced import: SHOP_ITEMS is gone.
from cogs.fishing.constants import ALL_ITEMS_DATA
from .constants import GIFT_MESSAGES, COLOR_RELATIONSHIP, GIFT_CHARM_VALUES
from core.logger import setup_logger
from core.database import db_manager

logger = setup_logger("RelationshipCog", "cogs/relationship.log")

# Build local mapping for relationship items
# We only care about buyable items or explicit gifts
VIETNAMESE_TO_ITEM_KEY = {}
for key, item_data in ALL_ITEMS_DATA.items():
    # Only include buyable items or items with type=gift to be safe
    # Relationship tangqua allows giving any buyable item probably
    flags = item_data.get("flags", {})
    if flags.get("buyable", False) or item_data.get("type") == "gift":
        VIETNAMESE_TO_ITEM_KEY[item_data["name"].lower()] = key

class RelationshipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_rank_check.start()
        
    def cog_unload(self):
        self.daily_rank_check.cancel()

    @tasks.loop(minutes=1.0)
    async def daily_rank_check(self):
        """Check time every minute to update rank at 23:55"""
        now = datetime.datetime.now()
        if now.hour == 23 and now.minute == 55:
            await self.update_top_charm_role()

    async def update_top_charm_role(self):
        """Find top charm user and assign role"""
        logger.info("[CHARM_RANK] Starting daily role update...")
        try:
            # 1. Get Configured Guilds & Roles
            # We process for each guild in config that has charm_rank_role_id
            rows = await db_manager.execute("SELECT guild_id, charm_rank_role_id, logs_channel_id FROM server_config WHERE charm_rank_role_id IS NOT NULL")
            
            for row in rows:
                guild_id = row[0]
                role_id = row[1]
                log_channel_id = row[2]
                
                guild = self.bot.get_guild(guild_id)
                if not guild: continue
                
                role = guild.get_role(role_id)
                if not role:
                    logger.warning(f"[CHARM_RANK] Role {role_id} not found in guild {guild_id}")
                    continue
                
                # 2. Find Top Logic
                # Only count users in this guild? The DB is global users, but we should verify membership.
                # However, SQL logic is simpler: Get top global users, check if in guild.
                
                # Fetch top 10 to be safe (in case top 1 left server)
                top_users = await db_manager.execute("SELECT user_id, charm_point FROM users ORDER BY charm_point DESC LIMIT 10")
                
                winner_member = None
                winner_points = 0
                
                for u_row in top_users:
                    uid = u_row[0]
                    points = u_row[1]
                    member = guild.get_member(uid)
                    if member:
                        winner_member = member
                        winner_points = points
                        break
                
                if not winner_member:
                    logger.info(f"[CHARM_RANK] No valid member found for guild {guild_id}")
                    continue
                
                # 3. Update Roles
                # Remove from current holders
                for member in role.members:
                    if member.id != winner_member.id:
                        try:
                            await member.remove_roles(role, reason="Lost Top Charm Rank")
                            logger.info(f"[CHARM_RANK] Removed role from {member.name}")
                        except Exception as e:
                            logger.error(f"[CHARM_RANK] Failed to remove role from {member.name}: {e}")
                
                # Add to winner
                if role not in winner_member.roles:
                    try:
                        await winner_member.add_roles(role, reason="Won Top Charm Rank")
                        logger.info(f"[CHARM_RANK] Added role to {winner_member.name}")
                        
                        # Notify
                        if log_channel_id:
                            channel = guild.get_channel(log_channel_id)
                            if channel:
                                await channel.send(f"👑 **Chúc mừng {winner_member.mention}** đã đạt Top 1 Charm ({winner_points} điểm) và nhận role {role.mention}!")
                    except Exception as e:
                        logger.error(f"[CHARM_RANK] Failed to add role to {winner_member.name}: {e}")

        except Exception as e:
            logger.error(f"[CHARM_RANK] Error: {e}", exc_info=True)

    @daily_rank_check.before_loop
    async def before_daily_rank_check(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="tangqua", description="Tặng quà healing cho người khác (Cà phê, Hoa, Quà...)")
    @app_commands.describe(
        user="Người nhận",
        item="Tên vật phẩm (cafe, flower, ring, gift, chocolate, card)",
        message="Lời nhắn gửi kèm (Nếu để trống sẽ dùng lời nhắn ngẫu nhiên)",
        an_danh="Gửi ẩn danh (True/False)"
    )
    async def tangqua(self, interaction: discord.Interaction, user: discord.User, item: str, message: str = None, an_danh: bool = False):
        # Defer ephemerally if anonymous to hide usage
        await interaction.response.defer(ephemeral=an_danh)

        if user.id == interaction.user.id:
            return await interaction.followup.send("❌ Hãy thương lấy chính mình trước khi thương người khác nhé! (Nhưng tặng quà cho mình thì hơi kỳ)")
        
        if user.bot:
            return await interaction.followup.send("❌ Bot không biết uống cà phê đâu, cảm ơn tấm lòng nhé!")

        # Normalization & Mapping
        item_lower = item.lower()
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item_lower)
        
        if not item_key:
            # Try direct key match
            if item_lower in ALL_ITEMS_DATA:
                item_key = item_lower
            else:
                 # Fallback: Check if user typed exact name but case insensitive?
                 # VIETNAMESE_TO_ITEM_KEY handles names.
                 return await interaction.followup.send(f"❌ Không tìm thấy món quà tên '{item}'. Hãy xem lại `/shop` nhé.")
        
        # Check if item is giftable (should be in GIFT_MESSAGES or just generic gift)
        # Relationship cog likely supports any item, but GIFT_MESSAGES has templates.
        
        # Check inventory
        # [CACHE] Check inventory
        current_qty = await self.bot.inventory.get(interaction.user.id, item_key)
        if current_qty < 1:
             item_name = ALL_ITEMS_DATA.get(item_key, {}).get("name", item_key)
             return await interaction.followup.send(f"❌ Bạn không có sẵn **{item_name}** trong túi đồ.")
        
        # Deduct item
        await self.bot.inventory.modify(interaction.user.id, item_key, -1)
        
        # [NEW] Add Charm Points
        charm_value = GIFT_CHARM_VALUES.get(item_key, 10) # Default 10 if unknown
        
        from core.database import db_manager
        await db_manager.execute(
            "UPDATE users SET charm_point = charm_point + ? WHERE user_id = ?",
            (charm_value, user.id)
        )

        logger.info(f"Gift: {interaction.user.id} -> {user.id}, item: {item_key}, charm: +{charm_value}, anonymous: {an_danh}")
        
        # Construct Embed
        sender_name = "Một người giấu tên" if an_danh else interaction.user.display_name
        sender_avatar = "https://cdn.discordapp.com/embed/avatars/0.png" if an_danh else interaction.user.display_avatar.url
        
        # Select Message
        if message:
            final_msg = f'"{message}"'
        else:
            # Use random template
            msgs = GIFT_MESSAGES.get(item_key, [f"**{sender_name}** đã tặng **{user.display_name}** một món quà!"])
            msg_template = random.choice(msgs)
            final_msg = msg_template.format(sender=sender_name, receiver=user.display_name)
        
        embed = discord.Embed(
            description=f"{final_msg}", 
            color=COLOR_RELATIONSHIP
        )
        
        if not an_danh:
            embed.set_author(name=f"Quà tặng từ {sender_name}", icon_url=sender_avatar)
        else:
            embed.set_author(name="Quà tặng bí mật", icon_url=sender_avatar)

        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Get item info
        item_info = ALL_ITEMS_DATA.get(item_key, {})
        embed.set_footer(text=f"Vật phẩm: {item_info.get('name', item_key)} {item_info.get('emoji', '🎁')} | +{charm_value} Charm")
        
        # Send to channel
        if an_danh:
            # Ephemeral confirm first
            await interaction.followup.send("✅ Đã gửi quà bí mật thành công! (Tin nhắn sẽ xuất hiện trong giây lát)", ephemeral=True)
            # Wait then send public message disconnected from interaction
            import asyncio
            await asyncio.sleep(2)
            if interaction.channel:
                await interaction.channel.send(content=user.mention, embed=embed)
        else:
            # Normal reply
            await interaction.followup.send(content=user.mention, embed=embed)

async def setup(bot):
    await bot.add_cog(RelationshipCog(bot))
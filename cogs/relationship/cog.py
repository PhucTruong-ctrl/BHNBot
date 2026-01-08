import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timedelta
from cogs.fishing.constants import ALL_ITEMS_DATA
from .constants import GIFT_MESSAGES, COLOR_RELATIONSHIP
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
        self.gift_cooldowns = {}

    @app_commands.command(name="tangqua", description="Tặng quà healing cho người khác (Cà phê, Hoa, Quà...)")
    @app_commands.describe(
        user="Người nhận",
        item="Tên vật phẩm (cafe, flower, ring, gift, chocolate, card)",
        message="Lời nhắn gửi kèm (Nếu để trống sẽ dùng lời nhắn ngẫu nhiên)",
        an_danh="Gửi ẩn danh (True/False)"
    )
    async def tangqua(self, interaction: discord.Interaction, user: discord.User, item: str, message: str = None, an_danh: bool = False):
        sender_id = interaction.user.id
        now = datetime.now()
        
        if sender_id in self.gift_cooldowns:
            recent_gifts = [t for t in self.gift_cooldowns[sender_id] if (now - t).total_seconds() < 3600]
            
            if len(recent_gifts) >= 10:
                oldest_gift = min(recent_gifts)
                wait_time = 3600 - (now - oldest_gift).total_seconds()
                wait_minutes = int(wait_time / 60) + 1
                
                return await interaction.response.send_message(
                    f"⏳ Bạn đã tặng quá nhiều! Vui lòng đợi **{wait_minutes} phút** nữa.",
                    ephemeral=True
                )
            
            self.gift_cooldowns[sender_id] = recent_gifts
        else:
            self.gift_cooldowns[sender_id] = []
        
        await interaction.response.defer(ephemeral=an_danh)
        
        self.gift_cooldowns[sender_id].append(now)

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

        logger.info(f"Gift: {interaction.user.id} -> {user.id}, item: {item_key}, anonymous: {an_danh}")
        
        item_info = ALL_ITEMS_DATA.get(item_key, {})
        item_name = item_info.get('name', item_key)
        
        await db_manager.modify(
            "INSERT INTO gift_history (sender_id, receiver_id, item_key, item_name, is_anonymous, message) VALUES (?, ?, ?, ?, ?, ?)",
            (interaction.user.id, user.id, item_key, item_name, an_danh, message)
        )
        
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
        embed.set_footer(text=f"Vật phẩm: {item_info.get('name', item_key)} {item_info.get('emoji', '🎁')}")
        
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
            await interaction.followup.send(content=user.mention, embed=embed)

    @app_commands.command(name="qua-thongke", description="Xem thống kê tặng quà (leaderboard, lịch sử)")
    @app_commands.describe(loai="Loại thống kê")
    @app_commands.choices(loai=[
        app_commands.Choice(name="🏆 Bảng xếp hạng người tặng nhiều nhất", value="bangxephang"),
        app_commands.Choice(name="📜 Lịch sử quà đã tặng", value="lichsu"),
        app_commands.Choice(name="🎁 Quà đã nhận được", value="nhanduoc"),
    ])
    async def qua_thongke(self, interaction: discord.Interaction, loai: str = "bangxephang"):
        await interaction.response.defer()
        
        if loai == "bangxephang":
            rows = await db_manager.fetchall(
                """SELECT sender_id, COUNT(*) as total_gifts 
                   FROM gift_history 
                   GROUP BY sender_id 
                   ORDER BY total_gifts DESC 
                   LIMIT 10"""
            )
            
            if not rows:
                return await interaction.followup.send("📭 Chưa có ai tặng quà nào cả!")
            
            embed = discord.Embed(
                title="🏆 Bảng Xếp Hạng Người Tặng Quà",
                color=COLOR_RELATIONSHIP
            )
            
            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for i, (sender_id, total) in enumerate(rows):
                medal = medals[i] if i < 3 else f"`{i+1}.`"
                try:
                    user = await self.bot.fetch_user(sender_id)
                    name = user.display_name
                except Exception:
                    name = f"User#{sender_id}"
                lines.append(f"{medal} **{name}** — {total} quà")
            
            embed.description = "\n".join(lines)
            embed.set_footer(text="Tặng quà để leo hạng! Dùng /tangqua")
            await interaction.followup.send(embed=embed)
            
        elif loai == "lichsu":
            rows = await db_manager.fetchall(
                """SELECT receiver_id, item_name, is_anonymous, sent_at 
                   FROM gift_history 
                   WHERE sender_id = ? 
                   ORDER BY sent_at DESC 
                   LIMIT 15""",
                (interaction.user.id,)
            )
            
            if not rows:
                return await interaction.followup.send("📭 Bạn chưa tặng quà cho ai cả! Dùng `/tangqua` để bắt đầu.")
            
            embed = discord.Embed(
                title="📜 Lịch Sử Quà Đã Tặng",
                color=COLOR_RELATIONSHIP
            )
            
            lines = []
            for receiver_id, item_name, is_anon, sent_at in rows:
                try:
                    recv_user = await self.bot.fetch_user(receiver_id)
                    receiver_name = recv_user.display_name
                except Exception:
                    receiver_name = f"User#{receiver_id}"
                anon_tag = " 🎭" if is_anon else ""
                time_str = sent_at.strftime("%d/%m") if sent_at else "N/A"
                lines.append(f"• **{item_name}** → {receiver_name}{anon_tag} ({time_str})")
            
            embed.description = "\n".join(lines)
            
            total = await db_manager.fetchone(
                "SELECT COUNT(*) FROM gift_history WHERE sender_id = ?",
                (interaction.user.id,)
            )
            embed.set_footer(text=f"Tổng cộng: {total[0] if total else 0} quà đã tặng")
            await interaction.followup.send(embed=embed)
            
        elif loai == "nhanduoc":
            rows = await db_manager.fetchall(
                """SELECT sender_id, item_name, is_anonymous, sent_at 
                   FROM gift_history 
                   WHERE receiver_id = ? 
                   ORDER BY sent_at DESC 
                   LIMIT 15""",
                (interaction.user.id,)
            )
            
            if not rows:
                return await interaction.followup.send("📭 Bạn chưa nhận được quà nào! Hãy tốt bụng và chờ đợi nhé 💝")
            
            embed = discord.Embed(
                title="🎁 Quà Bạn Đã Nhận",
                color=COLOR_RELATIONSHIP
            )
            
            lines = []
            for sender_id, item_name, is_anon, sent_at in rows:
                if is_anon:
                    sender_name = "Ẩn danh 🎭"
                else:
                    try:
                        send_user = await self.bot.fetch_user(sender_id)
                        sender_name = send_user.display_name
                    except Exception:
                        sender_name = f"User#{sender_id}"
                time_str = sent_at.strftime("%d/%m") if sent_at else "N/A"
                lines.append(f"• **{item_name}** từ {sender_name} ({time_str})")
            
            embed.description = "\n".join(lines)
            
            total = await db_manager.fetchone(
                "SELECT COUNT(*) FROM gift_history WHERE receiver_id = ?",
                (interaction.user.id,)
            )
            embed.set_footer(text=f"Tổng cộng: {total[0] if total else 0} quà đã nhận")
            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RelationshipCog(bot))
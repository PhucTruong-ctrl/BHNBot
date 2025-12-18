import discord
from discord import app_commands
from discord.ext import commands
import datetime
import random
import asyncio
from typing import Optional
from database_manager import db_manager, remove_item, add_item, get_top_affinity_friends
from cogs.shop import SHOP_ITEMS, VIETNAMESE_TO_ITEM_KEY
from .constants import *
from .helpers import get_affinity_title, get_pet_state, calculate_next_level_xp

class ConfirmView(discord.ui.View):
    def __init__(self, inviter, invitee):
        super().__init__(timeout=60)
        self.inviter = inviter
        self.invitee = invitee
        self.value = None

    @discord.ui.button(label="Đồng ý", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invitee.id:
            return await interaction.response.send_message("Không phải lượt của bạn!", ephemeral=True)
        self.value = True
        self.stop()

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
         if interaction.user.id != self.invitee.id:
            return await interaction.response.send_message("Không phải lượt của bạn!", ephemeral=True)
         self.value = False
         self.stop()

class RelationshipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================
    async def get_affinity(self, user1_id, user2_id):
        # Sort IDs to ensure consistent key
        u1, u2 = sorted([user1_id, user2_id])
        row = await db_manager.fetchone(
            "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
            (u1, u2)
        )
        return row[0] if row else 0

    async def add_affinity(self, user1_id, user2_id, amount):
        u1, u2 = sorted([user1_id, user2_id])
        # Check if row exists
        row = await db_manager.fetchone(
            "SELECT affinity FROM relationships WHERE user_id_1 = ? AND user_id_2 = ?",
            (u1, u2)
        )
        if row:
            await db_manager.execute(
                "UPDATE relationships SET affinity = affinity + ?, last_interaction = CURRENT_TIMESTAMP WHERE user_id_1 = ? AND user_id_2 = ?",
                (amount, u1, u2)
            )
        else:
            await db_manager.execute(
                "INSERT INTO relationships (user_id_1, user_id_2, affinity, last_interaction, start_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (u1, u2, amount)
            )

    async def get_pet(self, user1_id, user2_id):
        u1, u2 = sorted([user1_id, user2_id])
        row = await db_manager.fetchone(
            "SELECT * FROM shared_pets WHERE user_id_1 = ? AND user_id_2 = ?",
            (u1, u2)
        )
        # Row: id, u1, u2, name, level, exp, last_fed, start_date
        return row
        
    async def update_last_fed(self, pet_id):
        await db_manager.execute(
            "UPDATE shared_pets SET last_fed = CURRENT_TIMESTAMP WHERE id = ?",
            (pet_id,)
        )

    # ==================== COMMANDS ====================

    @app_commands.command(name="tangqua", description="Tặng quà healing & chill cho người khác")
    @app_commands.describe(
        user="Người nhận",
        item="Tên vật phẩm (cafe, hoa, nhan...)",
        message="Lời nhắn gửi kèm (Nếu không nhập sẽ dùng lời nhắn mặc định)",
        an_danh="Gửi ẩn danh (True/False)"
    )
    async def tangqua(self, interaction: discord.Interaction, user: discord.User, item: str, message: str = None, an_danh: bool = False):
        await interaction.response.defer()

        if user.id == interaction.user.id:
            return await interaction.followup.send("❌ Hãy thương lấy chính mình trước khi thương người khác nhé! (Nhưng tặng quà cho mình thì không được tính điểm đâu)")
        
        # Mapping item
        item_key = VIETNAMESE_TO_ITEM_KEY.get(item)
        if not item_key:
            # Try direct key
            if item.lower() in SHOP_ITEMS:
                item_key = item.lower()
            else:
                 return await interaction.followup.send(f"❌ Không tìm thấy món quà tên '{item}'. Hãy xem lại `/shop` nhé.")

        # Check inventory
        success = await remove_item(interaction.user.id, item_key, 1)
        if not success:
             return await interaction.followup.send(f"❌ Bạn không có sẵn **{SHOP_ITEMS[item_key]['name']}** trong túi đồ.")

        # Add affinity
        base_points = AFFINITY_VALUES.get(item_key, 5)
        await self.add_affinity(interaction.user.id, user.id, base_points)
        
        # Create Embed
        # Visual & Fame
        sender_name = "Một người giấu tên" if an_danh else interaction.user.display_name
        sender_avatar = "https://cdn.discordapp.com/embed/avatars/0.png" if an_danh else interaction.user.display_avatar.url
        
        # Pick random healing message OR use custom message
        if message:
            final_msg = message
        else:
            msgs = GIFT_MESSAGES.get(item_key, [f"{sender_name} đã tặng {user.display_name} một món quà!"])
            msg_template = random.choice(msgs)
            final_msg = msg_template.format(sender=sender_name, receiver=user.display_name)
        
        embed = discord.Embed(description=f"### {final_msg}", color=COLOR_RELATIONSHIP)
        embed.set_author(name=f"Quà tặng từ {sender_name}", icon_url=sender_avatar)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.set_footer(text=f"Món quà: {SHOP_ITEMS[item_key]['name']} {SHOP_ITEMS[item_key]['emoji']}")
        
        # Send to channel (Public Event)
        await interaction.followup.send(content=user.mention, embed=embed)


    @app_commands.command(name="kethop", description="Mời ai đó cùng nuôi thú cưng (Cần độ thân thiết cao)")
    async def kethop(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        
        if user.id == interaction.user.id:
            return await interaction.followup.send("❌ Bạn không thể kết hợp với chính mình.")

        # Check affinity
        affinity = await self.get_affinity(interaction.user.id, user.id)
        if affinity < 100:
             return await interaction.followup.send(f"❌ Độ thân thiết giữa bạn và {user.name} chưa đủ! (Cần 100, hiện có {affinity}).\nHãy tặng quà hoặc trò chuyện thêm nhé.")

        # Check if already have pet
        pet = await self.get_pet(interaction.user.id, user.id)
        if pet:
             return await interaction.followup.send(f"❌ Hai bạn đã có thú cưng chung là **{pet[3]}** rồi!")

        # Confirmation View
        view = ConfirmView(interaction.user, user)
        msg = await interaction.followup.send(f"{user.mention}, **{interaction.user.name}** muốn cùng bạn nuôi một bé thú cưng! 🐱\nBạn có đồng ý không?", view=view)
        
        await view.wait() 
        
        if view.value:
            # Create pet
            u1, u2 = sorted([interaction.user.id, user.id])
            await db_manager.execute(
                "INSERT INTO shared_pets (user_id_1, user_id_2, name, level, exp, last_fed, start_date) VALUES (?, ?, ?, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (u1, u2, PET_DEFAULT_NAME)
            )
            await interaction.followup.send(f"🎉 Chúc mừng! **{interaction.user.name}** và **{user.name}** đã nhận nuôi một bé **{PET_DEFAULT_NAME}**!\nDùng lệnh `/nuoi` để chăm sóc bé nhé.")
        elif view.value is False:
            await interaction.followup.send(f"💔 {user.name} đã từ chối lời mời...")
        else:
             await interaction.followup.send("⏳ Lời mời đã hết hạn.")


    @app_commands.command(name="nuoi", description="Chăm sóc thú cưng chung (Cho ăn, Vuốt ve, Tưới nước...)")
    @app_commands.describe(action="Hành động: choan (fish/trash), uongnuoc (water), vitamin, vuotve")
    async def nuoi(self, interaction: discord.Interaction, action: str = "vuotve"):
        await interaction.response.defer()
        
        # Find partner/pet
        rows = await db_manager.execute(
            "SELECT * FROM shared_pets WHERE user_id_1 = ? OR user_id_2 = ?",
            (interaction.user.id, interaction.user.id)
        )
        pets = await rows.fetchall()
        
        if not pets:
             return await interaction.followup.send("❌ Bạn chưa nuôi thú cưng với ai cả! Hãy dùng `/kethop` với bạn thân nhé.")
        
        # Use the first pet found for now (MVP)
        pet = pets[0] 
        pet_id = pet[0]
        partner_id = pet[2] if pet[1] == interaction.user.id else pet[1]
        partner = await self.bot.fetch_user(partner_id)
        partner_name = partner.name if partner else "Unknown"
        
        pet_name = pet[3]
        level = pet[4]
        current_exp = pet[5]
        last_fed = pet[6] # string or datetime

        # Action Handling
        msg_response = ""
        exp_gain = 0
        
        if action == "vuotve":
            msg_response = "Meow~ Dễ chịu quá... Cậu vất vả rồi, nghỉ ngơi xíu đi. ❤️"
            exp_gain = 2
            
        elif action in ["choan", "fish", "trash"]:
            # Simple trash support for now
            if action == "trash":
                 if await remove_item(interaction.user.id, "trash", 1):
                     msg_response = "Meow... (Mèo ăn rác tái chế, hơi kì nhưng cũng no). Cảm ơn cậu!"
                     exp_gain = PET_FOOD_VALUES["trash"]
                     await self.update_last_fed(pet_id)
                 else:
                     return await interaction.followup.send("❌ Bạn không có Rác!")
            else:
                 return await interaction.followup.send("❌ Hiện tại chỉ hỗ trợ cho ăn 'trash', 'water', 'vitamin'.")

        elif action in ["uongnuoc", "water", "nuoc"]:
            if await remove_item(interaction.user.id, "nuoc", 1):
                msg_response = "Mát quá đi! Cậu cũng nhớ uống đủ nước nhé! 💧"
                exp_gain = PET_FOOD_VALUES["water"]
                await self.update_last_fed(pet_id)
            else:
                return await interaction.followup.send("❌ Bạn không có Nước (Mua trong `/shop`)!")
                
        elif action in ["vitamin"]:
            if await remove_item(interaction.user.id, "vitamin", 1):
                msg_response = "Khỏe khoắn hẳn ra! Cảm ơn cậu nha! 💊"
                exp_gain = PET_FOOD_VALUES["vitamin"]
                await self.update_last_fed(pet_id)
            else:
                return await interaction.followup.send("❌ Bạn không có Vitamin (Mua trong `/shop`)!")
        
        else:
             return await interaction.followup.send("❌ Hành động không hợp lệ. Thử: vuotve, uongnuoc, vitamin")

        # Update EXP
        new_exp = current_exp + exp_gain
        req_exp = calculate_next_level_xp(level)
        level_up_msg = ""
        
        if new_exp >= req_exp:
            level += 1
            new_exp -= req_exp
            level_up_msg = f"\n🎉 **{pet_name}** đã lên cấp {level}! Bé lớn nhanh quá!"
            
            # Update DB
            await db_manager.execute(
                "UPDATE shared_pets SET level = ?, exp = ? WHERE id = ?",
                (level, new_exp, pet_id)
            )
        else:
            await db_manager.execute(
                "UPDATE shared_pets SET exp = ? WHERE id = ?",
                (new_exp, pet_id)
            )

        # Generate Embed
        state = get_pet_state(level, last_fed)
        # Visual feedback override
        if exp_gain > 5:
             state = "eating"
        elif action == "vuotve":
             state = "play"

        state_emojis = {
            "idle": "🐈",
            "sleep": "💤 🐈",
            "eating": "🐟 🐈",
            "play": "🧶 🐈",
            "sad": "😿"
        }
        
        embed = discord.Embed(title=f"🐱 {pet_name} (Lv.{level})", description=f"Cùng nuôi với: **{partner_name}**", color=COLOR_PET)
        embed.add_field(name="💬 Mèo nói:", value=f'"{msg_response}"', inline=False)
        embed.add_field(name="📊 Trạng thái:", value=f"EXP: {new_exp}/{req_exp}\nNo bụng: {{'✅' if state != 'sad' else '❌ (Đói lắm rồi!)'}}", inline=True)
        
        if level_up_msg:
             embed.add_field(name="🌟 Level Up!", value=level_up_msg, inline=False)

        # Set Pet Image based on State and Level
        pet_image_url = PET_IMAGES.get(level, {}).get(state, PET_IMAGES.get(1, {}).get("idle", ""))
        embed.set_thumbnail(url=pet_image_url)
        
        embed.set_footer(text=f"Trạng thái: {state.upper()} {state_emojis.get(state, '')}")
        
        await interaction.followup.send(embed=embed)
        
        
    @app_commands.command(name="thanthiet", description="Xem mức độ thân thiết với ai")
    @app_commands.describe(user="Người muốn check (để trống để xem người thân nhất)")
    async def check_affinity_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Check affinity with another user"""
        await interaction.response.defer(ephemeral=False)
        
        if user and user.id == interaction.user.id:
            await interaction.followup.send("❌ Bạn không thể check thân thiết với chính mình!", ephemeral=True)
            return
        
        if user:
            # Check affinity with specific user
            affinity = await self.get_affinity(interaction.user.id, user.id)
            title = get_affinity_title(affinity)
            
            embed = discord.Embed(
                title="💕 Mức độ Thân thiết",
                color=COLOR_RELATIONSHIP
            )
            embed.add_field(name="Giữa", value=f"{interaction.user.mention} ❤️ {user.mention}", inline=False)
            embed.add_field(name="Điểm", value=f"**{affinity}**", inline=False)
            embed.set_footer(text=f"Danh hiệu: {title}")
            
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            # Show top affinity friends
            top_friends = await get_top_affinity_friends(interaction.user.id, 5)
            
            embed = discord.Embed(
                title="💕 Top người thân nhất của bạn",
                color=COLOR_RELATIONSHIP
            )
            
            if not top_friends:
                embed.description = "Bạn chưa có ai thân cả 😢"
            else:
                friends_text = ""
                for idx, (friend_id, affinity) in enumerate(top_friends, 1):
                    try:
                        friend = await self.bot.fetch_user(friend_id)
                        medals = ["🥇", "🥈", "🥉"]
                        medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                        friends_text += f"{medal} **{friend.name}** - {affinity} điểm\n"
                    except:
                        pass
                
                embed.description = friends_text if friends_text else "Bạn chưa có ai thân cả 😢"
            
            await interaction.followup.send(embed=embed, ephemeral=False)

    @commands.command(name="thanthiet", description="Xem mức độ thân thiết với ai")
    async def check_affinity_prefix(self, ctx, user: discord.User = None):
        """Check affinity with another user via prefix"""
        if user and user.id == ctx.author.id:
            await ctx.send("❌ Bạn không thể check thân thiết với chính mình!")
            return
        
        if user:
            affinity = await self.get_affinity(ctx.author.id, user.id)
            title = get_affinity_title(affinity)
            
            embed = discord.Embed(
                title="💕 Mức độ Thân thiết",
                color=COLOR_RELATIONSHIP
            )
            embed.add_field(name="Giữa", value=f"{ctx.author.mention} ❤️ {user.mention}", inline=False)
            embed.add_field(name="Điểm", value=f"**{affinity}**", inline=False)
            embed.set_footer(text=f"Danh hiệu: {title}")
            
            await ctx.send(embed=embed)
        else:
            top_friends = await get_top_affinity_friends(ctx.author.id, 5)
            embed = discord.Embed(
                title="💕 Top người thân nhất của bạn",
                color=COLOR_RELATIONSHIP
            )
            
            if not top_friends:
                embed.description = "Bạn chưa có ai thân cả 😢"
            else:
                friends_text = ""
                for idx, (friend_id, affinity) in enumerate(top_friends, 1):
                    try:
                        friend = await self.bot.fetch_user(friend_id)
                        medals = ["🥇", "🥈", "🥉"]
                        medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                        friends_text += f"{medal} **{friend.name}** - {affinity} điểm\n"
                    except:
                        pass
                embed.description = friends_text if friends_text else "Bạn chưa có ai thân cả 😢"
            await ctx.send(embed=embed)

    # ==================== EVENTS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto add affinity when users interact (reply/mention)"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # Check if message is a reply
        if message.reference:
            try:
                replied_msg = await message.channel.fetch_message(message.reference.message_id)
                if not replied_msg.author.bot and replied_msg.author.id != message.author.id:
                    # Add small affinity (2 points)
                    await self.add_affinity(message.author.id, replied_msg.author.id, 2)
                    print(
                        f"[AFFINITY] [REPLY] actor_id={message.author.id} actor={message.author.name} "
                        f"target_id={replied_msg.author.id} target={replied_msg.author.name} affinity_change=+2"
                    )
            except:
                pass
        
        # Check if message mentions someone
        for mentioned_user in message.mentions:
            if not mentioned_user.bot and mentioned_user.id != message.author.id:
                # Add small affinity (1 point)
                await self.add_affinity(message.author.id, mentioned_user.id, 1)
                print(
                    f"[AFFINITY] [MENTION] actor_id={message.author.id} actor={message.author.name} "
                    f"target_id={mentioned_user.id} target={mentioned_user.name} affinity_change=+1"
                )

async def setup(bot):
    await bot.add_cog(RelationshipCog(bot))
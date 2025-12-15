import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta
import asyncio

DB_PATH = "./data/database.db"

# Tree Level Requirements (Hạt cần thêm)
# Base requirements for season 1
BASE_LEVEL_REQS = {
    1: 0,      # 🌱 Hạt mầm
    2: 1000,   # 🌿 Nảy mầm
    3: 2000,   # 🎋 Cây non
    4: 3000,   # 🌳 Trưởng thành
    5: 4000,   # 🌸 Ra hoa
    6: 5000    # 🍎 Kết trái (MAX)
}

# Scaling factor per season (25% increase each season)
SEASON_SCALING = 1.25

# Tree Images (Replace with your own image URLs)
TREE_IMAGES = {
    1: "https://imgur.com/seed.png",      # 🌱 Hạt mầm
    2: "https://imgur.com/sprout.png",    # 🌿 Nảy mầm
    3: "https://imgur.com/sapling.png",   # 🎋 Cây non
    4: "https://imgur.com/tree.png",      # 🌳 Trưởng thành
    5: "https://imgur.com/flower.png",    # 🌸 Ra hoa
    6: "https://imgur.com/fruit.png"      # 🍎 Kết trái
}

TREE_NAMES = {
    1: "🌱 Hạt mầm",
    2: "🌿 Nảy mầm",
    3: "🎋 Cây non",
    4: "🌳 Trưởng thành",
    5: "🌸 Ra hoa",
    6: "🍎 Kết trái"
}

TREE_DESCRIPTIONS = {
    1: "Một mầm sống nhỏ bé đang ngủ yên...",
    2: "Mầm non đã vươn lên đón nắng!",
    3: "Cây bắt đầu ra những cành lá đầu tiên.",
    4: "Cây đã cao lớn, tỏa bóng mát cho Hiên Nhà.",
    5: "Những đóa hoa rực rỡ báo hiệu mùa quả ngọt.",
    6: "Cây trĩu quả! Dùng lệnh /thuhoach ngay!"
}

HARVEST_REWARDS = {
    "seeds": 2000  # Reward for all members
}

# ==================== UI COMPONENTS ====================

class ContributeModal(discord.ui.Modal):
    """Modal for custom seed contribution input"""
    def __init__(self, tree_cog):
        super().__init__(title="Góp Hạt Cho Cây")
        self.tree_cog = tree_cog
        
        self.amount_input = discord.ui.TextInput(
            label="Số hạt muốn góp",
            placeholder="Nhập số từ 1 trở lên",
            min_length=1,
            max_length=6
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            if amount <= 0:
                await interaction.response.send_message("❌ Số lượng phải lớn hơn 0!", ephemeral=True)
                return
            
            await self.tree_cog.process_contribution(interaction, amount)
        except ValueError:
            await interaction.response.send_message("❌ Vui lòng nhập số nguyên hợp lệ!", ephemeral=True)

class TreeContributeView(discord.ui.View):
    """View with quick contribute buttons"""
    def __init__(self, tree_cog):
        super().__init__(timeout=None)
        self.tree_cog = tree_cog
    
    @discord.ui.button(label="🌱 10 Hạt", style=discord.ButtonStyle.green, custom_id="tree_10")
    async def contribute_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.tree_cog.process_contribution(interaction, 10)
    
    @discord.ui.button(label="🌿 100 Hạt", style=discord.ButtonStyle.blurple, custom_id="tree_100")
    async def contribute_100(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.tree_cog.process_contribution(interaction, 100)
    
    @discord.ui.button(label="🌳 1000 Hạt", style=discord.ButtonStyle.blurple, custom_id="tree_1000")
    async def contribute_1000(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.tree_cog.process_contribution(interaction, 1000)
    
    @discord.ui.button(label="✏️ Tuỳ ý", style=discord.ButtonStyle.secondary, custom_id="tree_custom")
    async def contribute_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ContributeModal(self.tree_cog)
        await interaction.response.send_modal(modal)

class CommunityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== HELPER FUNCTIONS ====================

    def get_level_reqs(self, season: int) -> dict:
        """Calculate level requirements for a given season
        
        Each season increases requirements by 25%:
        Season 1: 1000, 2000, 3000, 4000, 5000
        Season 2: 1250, 2500, 3750, 5000, 6250
        Season 3: 1563, 3125, 4688, 6250, 7813
        """
        multiplier = SEASON_SCALING ** (season - 1)
        return {
            level: int(BASE_LEVEL_REQS[level] * multiplier) if level > 1 else 0
            for level in BASE_LEVEL_REQS
        }

    async def get_tree_data(self, guild_id: int):
        """Get current tree data for guild"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT current_level, current_progress, total_contributed, season, tree_channel_id, tree_message_id FROM server_tree WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                await db.execute(
                    "INSERT INTO server_tree (guild_id) VALUES (?)",
                    (guild_id,)
                )
                await db.commit()
                return 1, 0, 0, 1, None, None
            
            return row

    async def update_tree_progress(self, guild_id: int, level: int, progress: int, total: int):
        """Update tree level and progress"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE server_tree SET current_level = ?, current_progress = ?, total_contributed = ? WHERE guild_id = ?",
                (level, progress, total, guild_id)
            )
            await db.commit()

    async def add_contributor(self, user_id: int, guild_id: int, amount: int):
        """Add to contributor's total"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT amount FROM tree_contributors WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                await db.execute(
                    "UPDATE tree_contributors SET amount = amount + ? WHERE user_id = ? AND guild_id = ?",
                    (amount, user_id, guild_id)
                )
            else:
                await db.execute(
                    "INSERT INTO tree_contributors (user_id, guild_id, amount) VALUES (?, ?, ?)",
                    (user_id, guild_id, amount)
                )
            
            await db.commit()

    async def get_top_contributors(self, guild_id: int, limit: int = 3):
        """Get top 3 contributors"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT user_id, amount FROM tree_contributors WHERE guild_id = ? ORDER BY amount DESC LIMIT ?",
                (guild_id, limit)
            ) as cursor:
                return await cursor.fetchall()

    async def create_tree_embed(self, guild_id: int):
        """Create tree display embed"""
        lvl, prog, total, season, _, _ = await self.get_tree_data(guild_id)
        
        # Get level requirements for current season
        level_reqs = self.get_level_reqs(season)
        
        # Calculate progress bar
        req = level_reqs.get(lvl + 1, level_reqs[6])
        if lvl >= 6:
            bar = "🟩" * 10
            footer_text = f"🍎 Cây đã trĩu quả! Chờ thu hoạch • Tổng: {total} Hạt"
            percent = 100
        else:
            percent = min(100, int((prog / req) * 100)) if req > 0 else 0
            filled = int(percent / 10)
            bar = "🟩" * filled + "⬜" * (10 - filled)
            footer_text = f"Mùa {season} • Level {lvl}/6 • {prog}/{req} Hạt • Tổng: {total}"
        
        embed = discord.Embed(
            title="🌳 Cây Hiên Nhà",
            description=TREE_DESCRIPTIONS.get(lvl, "..."),
            color=discord.Color.green()
        )
        embed.set_image(url=TREE_IMAGES.get(lvl, TREE_IMAGES[1]))
        embed.add_field(
            name=f"Trạng thái: {TREE_NAMES.get(lvl, '???')}",
            value=f"```\n{bar}\n```",
            inline=False
        )
        embed.add_field(name="Tiến độ", value=f"**{percent}%**", inline=True)
        embed.add_field(name="Level", value=f"**{lvl}/6**", inline=True)
        embed.add_field(name="💡 Cách Góp", value="Bấm nút dưới đây để góp hạt cho cây!", inline=False)
        embed.set_footer(text=footer_text)
        
        return embed

    async def update_or_create_pin_message(self, guild_id: int, tree_channel_id: int):
        """Update or create pinned tree message"""
        try:
            channel = self.bot.get_channel(tree_channel_id)
            if not channel:
                print(f"[TREE] Channel {tree_channel_id} not found")
                return
            
            embed = await self.create_tree_embed(guild_id)
            view = TreeContributeView(self)
            
            # Try to get existing pinned message
            try:
                pinned_messages = await channel.pins()
                tree_message = None
                
                for msg in pinned_messages:
                    if msg.author.id == self.bot.user.id and "🌳 Cây Hiên Nhà" in msg.embeds[0].title if msg.embeds else False:
                        tree_message = msg
                        break
                
                if tree_message:
                    # Edit existing message
                    await tree_message.edit(embed=embed, view=view)
                    print(f"[TREE] Updated pinned tree message in {channel.name}")
                else:
                    # Create new pinned message
                    new_message = await channel.send(embed=embed, view=view)
                    await new_message.pin()
                    
                    # Store message ID in database
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "UPDATE server_tree SET tree_message_id = ? WHERE guild_id = ?",
                            (new_message.id, guild_id)
                        )
                        await db.commit()
                    
                    print(f"[TREE] Pinned new tree message in {channel.name}")
            except:
                # Create new pinned message if error
                new_message = await channel.send(embed=embed, view=view)
                await new_message.pin()
                
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE server_tree SET tree_message_id = ? WHERE guild_id = ?",
                        (new_message.id, guild_id)
                    )
                    await db.commit()
        
        except Exception as e:
            print(f"[TREE] Error updating pin message: {e}")

    async def process_contribution(self, interaction: discord.Interaction, amount: int):
        """Process seed contribution"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check user balance
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT seeds FROM economy_users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row or row[0] < amount:
            current = row[0] if row else 0
            await interaction.followup.send(
                f"❌ Bạn không đủ hạt!\nCần: {amount} | Hiện có: {current}",
                ephemeral=True
            )
            return
        
        # Deduct seeds
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE economy_users SET seeds = seeds - ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()
        
        # Get current tree state
        lvl, prog, total, season, tree_channel_id, _ = await self.get_tree_data(guild_id)
        
        if lvl >= 6:
            # Refund and show message
            await interaction.followup.send(
                "🍎 Cây đã chín rồi! Hãy bảo Admin dùng lệnh `/thuhoach`!",
                ephemeral=True
            )
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE economy_users SET seeds = seeds + ? WHERE user_id = ?",
                    (amount, user_id)
                )
                await db.commit()
            return
        
        # Update tree progress
        level_reqs = self.get_level_reqs(season)
        req = level_reqs.get(lvl + 1, level_reqs[6])
        new_progress = prog + amount
        new_total = total + amount
        leveled_up = False
        
        if new_progress >= req and lvl < 6:
            lvl += 1
            new_progress = new_progress - req
            leveled_up = True
        
        await self.update_tree_progress(guild_id, lvl, new_progress, new_total)
        await self.add_contributor(user_id, guild_id, amount)
        
        # Response embed
        embed = discord.Embed(
            title="🌱 Góp Hạt Thành Công!",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Người góp", value=f"**{interaction.user.name}**", inline=False)
        embed.add_field(name="🌱 Hạt góp", value=f"**+{amount}**", inline=True)
        embed.add_field(name="💰 Còn lại", value=f"**{row[0] - amount}**", inline=True)
        
        if leveled_up:
            embed.add_field(
                name="🎉 CÂY LỚN LÊN CẤP!",
                value=f"**{TREE_NAMES[lvl]}** - Cấp {lvl}/6",
                inline=False
            )
            embed.color = discord.Color.gold()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Update pinned message
        if tree_channel_id:
            await self.update_or_create_pin_message(guild_id, tree_channel_id)
        
        print(f"[TREE] {interaction.user.name} contributed {amount} seeds (Tree now Level {lvl})")

    # ==================== COMMANDS ====================

    @app_commands.command(name="gophat", description="Góp Hạt nuôi cây server")
    @app_commands.describe(amount="Số hạt muốn góp (tuỳ chọn)")
    async def contribute_tree(self, interaction: discord.Interaction, amount: int = None):
        """Contribute seeds to the community tree"""
        if amount is None:
            # Show modal for custom input
            modal = ContributeModal(self)
            await interaction.response.send_modal(modal)
        else:
            if amount <= 0:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("❌ Số lượng phải lớn hơn 0!", ephemeral=True)
                return
            
            await self.process_contribution(interaction, amount)

    @app_commands.command(name="cay", description="Xem trạng thái cây server")
    async def show_tree(self, interaction: discord.Interaction):
        """Show current tree status"""
        await interaction.response.defer(ephemeral=True)
        
        embed = await self.create_tree_embed(interaction.guild.id)
        
        # Add contributor info
        contributors = await self.get_top_contributors(interaction.guild.id, 3)
        
        if contributors:
            contrib_text = ""
            for idx, (uid, amt) in enumerate(contributors, 1):
                try:
                    user = await self.bot.fetch_user(uid)
                    contrib_text += f"{idx}. **{user.name}** - {amt} Hạt\n"
                except:
                    contrib_text += f"{idx}. **User #{uid}** - {amt} Hạt\n"
            
            embed.add_field(name="🏆 Top 3 Người Góp", value=contrib_text, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="thuhoach", description="Thu hoạch cây (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def harvest_tree(self, interaction: discord.Interaction):
        """Harvest the tree when at max level - CLIMAX EVENT"""
        await interaction.response.defer(ephemeral=False)
        
        guild_id = interaction.guild.id
        
        lvl, prog, total, season, tree_channel_id, _ = await self.get_tree_data(guild_id)
        
        # Get level requirements for current season
        level_reqs = self.get_level_reqs(season)
        max_req = level_reqs[6]
        
        if lvl < 6:
            await interaction.followup.send(
                f"❌ Cây chưa chín! Hiện tại: Level {lvl}/6. Cần thêm {max_req - prog} Hạt.",
                ephemeral=True
            )
            return
        
        # === CLIMAX EVENT STARTS ===
        await interaction.followup.send("🍎 **ĐANG THU HOẠCH...** Xin chờ một chút! 🌟")
        
        # Get top 3 contributors
        contributors = await self.get_top_contributors(guild_id, 3)
        
        # Calculate rewards
        top1_reward = 5000
        top23_reward = 2000
        global_reward = 2000  # For all members
        
        # === BUILD VINH DANH TEXT ===
        honor_text = ""
        top1_user = None
        top1_user_obj = None
        
        for idx, (uid, amt) in enumerate(contributors):
            medal = ["🥇", "🥈", "🥉"][idx]
            reward_amt = top1_reward if idx == 0 else top23_reward
            
            try:
                user = await self.bot.fetch_user(uid)
                honor_text += f"{medal} **Top {idx+1}: {user.name}** - Góp {amt} Hạt → Nhận {reward_amt} Hạt 💪\n"
                if idx == 0:
                    top1_user = uid
                    top1_user_obj = user
            except:
                honor_text += f"{medal} **Top {idx+1}: User #{uid}** - Góp {amt} Hạt → Nhận {reward_amt} Hạt\n"
                if idx == 0:
                    top1_user = uid
        
        # === DATABASE TRANSACTIONS ===
        async with aiosqlite.connect(DB_PATH) as db:
            # 1. REWARD TOP CONTRIBUTORS
            for idx, (uid, amt) in enumerate(contributors):
                reward_amt = top1_reward if idx == 0 else top23_reward
                await db.execute(
                    "UPDATE economy_users SET seeds = seeds + ? WHERE user_id = ?",
                    (reward_amt, uid)
                )
            
            # 2. REWARD ALL ACTIVE MEMBERS with global buff
            async with db.execute("SELECT user_id FROM economy_users") as cursor:
                all_users = await cursor.fetchall()
            
            for (uid,) in all_users:
                await db.execute(
                    "UPDATE economy_users SET seeds = seeds + ? WHERE user_id = ?",
                    (global_reward, uid)
                )
            
            # 3. GIVE MEMORABILIA TO ALL CONTRIBUTORS
            async with db.execute(
                "SELECT user_id FROM tree_contributors WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                contributor_ids = await cursor.fetchall()
            
            memorabilia_name = f"Quả Ngọt Mùa {season}"
            for (cid,) in contributor_ids:
                # Check if already has this item
                async with db.execute(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                    (cid, memorabilia_name)
                ) as cursor:
                    inv_row = await cursor.fetchone()
                
                if inv_row:
                    await db.execute(
                        "UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?",
                        (cid, memorabilia_name)
                    )
                else:
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)",
                        (cid, memorabilia_name)
                    )
            
            # 4. ACTIVATE 24H BUFF by updating server_config
            await db.execute(
                "UPDATE server_config SET harvest_buff_until = datetime('now', '+24 hours') WHERE guild_id = ?",
                (guild_id,)
            )
            
            # 5. RESET TREE FOR NEXT SEASON
            await db.execute(
                "UPDATE server_tree SET current_level = 1, current_progress = 0, total_contributed = 0, season = season + 1, last_harvest = CURRENT_TIMESTAMP WHERE guild_id = ?",
                (guild_id,)
            )
            
            # 6. CLEAR CONTRIBUTORS
            await db.execute("DELETE FROM tree_contributors WHERE guild_id = ?", (guild_id,))
            
            await db.commit()
        
        # === CREATE ROLE FOR TOP 1 (if exists and is a valid guild member) ===
        role_mention = ""
        if top1_user_obj and interaction.guild:
            try:
                # Check if role already exists
                role_name = f"🌟 Thần Nông Mùa {season}"
                existing_role = discord.utils.get(interaction.guild.roles, name=role_name)
                
                if not existing_role:
                    role = await interaction.guild.create_role(
                        name=role_name,
                        color=discord.Color.gold(),
                        hoist=True
                    )
                else:
                    role = existing_role
                
                # Assign role to top1 user
                member = await interaction.guild.fetch_member(top1_user)
                if member:
                    await member.add_roles(role)
                    role_mention = f"\n🌟 Đã cấp role **{role_name}** cho **{top1_user_obj.name}**"
            except Exception as e:
                print(f"[TREE] Error creating role: {e}")
                role_mention = ""
        
        # === MAIN ANNOUNCEMENT EMBED ===
        embed = discord.Embed(
            title=f"🎉 THU HOẠCH THÀNH CÔNG - MÙA {season}! 🎉",
            description="Cây Đại Thụ đã hiến dâng những trái ngọt nhất cho Bên Hiên Nhà.\n\nPhước lành rực rỡ nung nấu trên toàn server!",
            color=discord.Color.gold()
        )
        embed.set_image(url=TREE_IMAGES[6])
        
        # Field 1: Global Buff
        embed.add_field(
            name="✨ TOÀN SERVER BỰC LỪA (24 Giờ)",
            value=f"🔥 **X2 Tỷ lệ Hạt** khi chat/voice\n🔥 **X2 XP** cho mọi activity\n"
                  f"💫 Tất cả member nhận **{global_reward} Hạt** ngay lập tức!",
            inline=False
        )
        
        # Field 2: Top Contributors
        embed.add_field(
            name="🏆 VINH DANH NGƯỜI LÀM VƯỜN",
            value=honor_text if honor_text else "_(Chưa có ai góp)_",
            inline=False
        )
        
        # Field 3: Memorabilia
        embed.add_field(
            name="🎁 TẶNG QUÀ LƯU NIỆM",
            value=f"Tất cả người đã góp được nhận **'{memorabilia_name}'** vào Túi đồ\n"
                  f"💎 Vật phẩm này chứng tỏ bạn là người lập công xây dựng server!",
            inline=False
        )
        
        # Field 4: Season Reset
        embed.add_field(
            name="🌱 MÙA MỚI BẮT ĐẦU",
            value=f"Cây đã tái sinh Level 1\n"
                  f"Mùa {season + 1} chính thức khai mạc!\n"
                  f"Hãy chuẩn bị cho cuộc đua góp hạt mới",
            inline=False
        )
        
        embed.set_footer(text=f"Cảm ơn tất cả! 🙏 | Mùa tiếp theo sẽ còn huy hoàng hơn!")
        
        await interaction.followup.send(embed=embed)
        
        # === ROLE ANNOUNCEMENT ===
        if role_mention:
            await interaction.followup.send(role_mention)
        
        # === TAG EVERYONE ===
        try:
            announce_msg = (
                f"🎊 @everyone 🎊\n\n"
                f"**MÙA THU HOẠCH CÂY HIÊN NHÀ ĐÃ KẾT THÚC!**\n\n"
                f"🔥 Trong 24 giờ tới, mọi người sẽ nhận **X2 Hạt từ chat/voice**!\n"
                f"💨 Hãy tranh thủ online để tối đa hóa lợi nhuận!\n\n"
                f"🏆 Chúc mừng {honor_text.split('**')[1] if honor_text else 'những người đã cống hiến'} 🏆"
            )
            await interaction.followup.send(announce_msg)
        except:
            pass
        
        print(f"[TREE] HARVEST EVENT - Season {season} completed! Top1: {top1_user}, Total: {total}")

    @app_commands.command(name="settreechannel", description="Set tree display channel (Admin Only)")
    @app_commands.describe(channel="Kênh để hiển thị cây")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_tree_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel where tree will be displayed"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE server_tree SET tree_channel_id = ? WHERE guild_id = ?",
                (channel.id, guild_id)
            )
            await db.commit()
        
        await interaction.followup.send(
            f"✅ Đã set kênh cây thành {channel.mention}",
            ephemeral=True
        )
        
        # Create pinned message
        await self.update_or_create_pin_message(guild_id, channel.id)
        
        print(f"[TREE] Tree channel set to {channel.name} ({channel.id})")

async def setup(bot):
    await bot.add_cog(CommunityCog(bot))

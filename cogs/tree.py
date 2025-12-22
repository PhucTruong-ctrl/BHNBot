import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta
import asyncio
import json
from configs.settings import DB_PATH, DATA_DIR
from database_manager import db_manager, get_tree_data, update_tree_progress, get_top_contributors
from core.logger import setup_logger

logger = setup_logger("TreeCog", "cogs/tree.log")

# Load tree configuration from data file
with open(f"{DATA_DIR}/tree_config.json", 'r', encoding='utf-8') as f:
    TREE_CONFIG = json.load(f)

# Tree Level Requirements (Hạt cần thêm)
# Base requirements for season 1
BASE_LEVEL_REQS = TREE_CONFIG['base_level_reqs']

# Scaling factor per season (25% increase each season)
SEASON_SCALING = 1.25

# Tree Images (Replace with your own image URLs)
TREE_IMAGES = {
    1: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(1).png",      # 🌱 Hạt mầm
    2: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(2).png",    # 🌿 Nảy mầm
    3: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(3).png",   # 🎋 Cây non
    4: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(4).png",      # 🌳 Trưởng thành
    5: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(5).png",    # 🌸 Ra hoa
    6: "https://file.garden/aTXEm7Ax-DfpgxEV/B%C3%AAn%20Hi%C3%AAn%20Nh%C3%A0%20-%20Discord%20Server/tree/image(6).png"      # 🍎 Kết trái
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
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
            
            amount = int(self.amount_input.value)
            if amount <= 0:
                await interaction.followup.send("Số lượng không hợp lệ!", ephemeral=True)
                return
            
            # Now call the process method which expects deferred response
            # Create a mock interaction with already-deferred response
            await self.tree_cog.process_contribution(interaction, amount)
        except ValueError:
            try:
                await interaction.followup.send("Vui lòng nhập số nguyên hợp lệ!", ephemeral=True)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

class TreeContributeView(discord.ui.View):
    """View with quick contribute buttons"""
    def __init__(self, tree_cog):
        super().__init__(timeout=None)
        self.tree_cog = tree_cog
    
    @discord.ui.button(label="🌱 10 Hạt", style=discord.ButtonStyle.green, custom_id="tree_10")
    async def contribute_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer immediately before any await
        try:
            await interaction.response.defer(ephemeral=False)
        except Exception as e:
            logger.error(f"[TREE] Error deferring response: {e}", exc_info=True)
            return
        
        await self.tree_cog.process_contribution(interaction, 10)
    
    @discord.ui.button(label="🌿 100 Hạt", style=discord.ButtonStyle.blurple, custom_id="tree_100")
    async def contribute_100(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer immediately before any await
        try:
            await interaction.response.defer(ephemeral=False)
        except Exception as e:
            logger.error(f"[TREE] Error deferring response: {e}", exc_info=True)
            return
        
        await self.tree_cog.process_contribution(interaction, 100)
    
    @discord.ui.button(label="✏️ Tuỳ ý", style=discord.ButtonStyle.secondary, custom_id="tree_custom")
    async def contribute_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ContributeModal(self.tree_cog)
        await interaction.response.send_modal(modal)

class CommunityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Debounce to prevent excessive tree message updates
        self.last_tree_update = {}
        # Lock to prevent concurrent tree message updates
        self.tree_update_locks = {}

    async def cog_load(self):
        await super().cog_load()
        logger.info("[TREE] Cog loaded, updating tree messages for all guilds...")
        for guild in self.bot.guilds:
            try:
                tree_data = await self.get_tree_data(guild.id)
                if tree_data and tree_data[4]:  # tree_channel_id
                    await self.update_or_create_pin_message(guild.id, tree_data[4])
            except Exception as e:
                logger.error(f"[TREE] Error updating tree on load for guild {guild.id}: {e}", exc_info=True)

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
            int(level): int(float(BASE_LEVEL_REQS[level]) * multiplier) if int(level) > 1 else 0
            for level in BASE_LEVEL_REQS
        }

    async def is_harvest_buff_active(self, guild_id: int) -> bool:
        """Check if 24h harvest buff is active"""
        try:
            result = await db_manager.fetchone(
                "SELECT harvest_buff_until FROM server_config WHERE guild_id = ?",
                (guild_id,),
                use_cache=True,
                cache_key=f"harvest_buff_{guild_id}",
                cache_ttl=60
            )
            
            if not result or not result[0]:
                return False
            
            buff_until = datetime.fromisoformat(result[0])
            return datetime.now() < buff_until
        except Exception as e:
            return False

    async def get_tree_data(self, guild_id: int):
        """Get current tree data for guild"""
        row = await get_tree_data(guild_id)
        
        if not row:
            # Insert default if not exists
            await db_manager.modify(
                "INSERT INTO server_tree (guild_id) VALUES (?)",
                (guild_id,)
            )
            return 1, 0, 0, 1, None, None
        
        return row

    async def update_tree_progress(self, guild_id: int, level: int, progress: int, total: int):
        """Update tree level and progress"""
        await update_tree_progress(guild_id, level, progress, total)

    async def add_contributor(self, user_id: int, guild_id: int, amount: int, contribution_type: str = "seeds"):
        """Add to contributor's total with experience points for CURRENT season.
        
        contribution_type: 'seeds' (hạt góp) or 'phan_bon' (bón phân)
        Seeds: 1 hạt = 1 exp
        phan_bon: 1 bón phân = 50-100 exp (tính từ boost_amount)
        """
        # Calculate experience based on contribution type
        if contribution_type == "phan_bon":
            exp_amount = amount  # amount is boost_amount (50-100)
        else:  # seeds
            exp_amount = amount  # 1 seed = 1 exp
        
        # Get current season
        _, _, _, current_season, _, _ = await self.get_tree_data(guild_id)
        
        try:
            # Check if contributor exists for this season
            result = await db_manager.fetchone(
                "SELECT amount, contribution_exp FROM tree_contributors WHERE user_id = ? AND guild_id = ? AND season = ?",
                (user_id, guild_id, current_season)
            )
            if result:
                # Update existing
                current_amount, current_exp = result
                new_amount = current_amount + amount
                new_exp = current_exp + exp_amount
                await db_manager.modify(
                    "UPDATE tree_contributors SET amount = ?, contribution_exp = ? WHERE user_id = ? AND guild_id = ? AND season = ?",
                    (new_amount, new_exp, user_id, guild_id, current_season)
                )
            else:
                # Insert new
                await db_manager.modify(
                    "INSERT INTO tree_contributors (user_id, guild_id, amount, contribution_exp, season) VALUES (?, ?, ?, ?, ?)",
                    (user_id, guild_id, amount, exp_amount, current_season)
                )
        except Exception as e:
            logger.error(f"[TREE] Error adding contributor: {e}", exc_info=True)
            raise

    async def get_top_contributors(self, guild_id: int, limit: int = 3):
        """Get top contributors by contribution experience for CURRENT season"""
        # Get current season
        _, _, _, current_season, _, _ = await self.get_tree_data(guild_id)
        
        result = await db_manager.execute(
            "SELECT user_id, amount, contribution_exp FROM tree_contributors WHERE guild_id = ? AND season = ? ORDER BY amount DESC LIMIT ?",
            (guild_id, current_season, limit)
        )
        return result

    async def get_top_contributors_all_time(self, guild_id: int, limit: int = 3):
        """Get top contributors by total contribution experience across ALL seasons"""
        result = await db_manager.execute(
            "SELECT user_id, SUM(contribution_exp) as total_exp FROM tree_contributors WHERE guild_id = ? GROUP BY user_id ORDER BY total_exp DESC LIMIT ?",
            (guild_id, limit)
        )
        return result

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
            filled = int(percent * 14 / 100)
            bar = "🟩" * filled + "⬜" * (14 - filled)
            footer_text = f"Mùa {season} • Level {lvl}/6 • {prog}/{req} Hạt • Tổng: {total}"
        
        embed = discord.Embed(
            title="Cây Bên Hiên Nhà",
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
        """Delete old tree message and create new one (no pinning)"""
        logger.info(f"[TREE] Updating tree message for guild {guild_id} in channel {tree_channel_id}")
        # Get or create lock for this guild
        if guild_id not in self.tree_update_locks:
            self.tree_update_locks[guild_id] = asyncio.Lock()
        
        # Acquire lock to prevent concurrent updates
        async with self.tree_update_locks[guild_id]:
            try:
                channel = self.bot.get_channel(tree_channel_id)
                if not channel:
                    # Try fetching if get returns None
                    try:
                        channel = await self.bot.fetch_channel(tree_channel_id)
                    except Exception as e:
                        logger.warning(f"[TREE] Channel ... not found: {e}")
                        return
                
                embed = await self.create_tree_embed(guild_id)
                
                # Add buff info if active
                if await self.is_harvest_buff_active(guild_id):
                    result = await db_manager.fetchone("SELECT harvest_buff_until FROM server_config WHERE guild_id = ?", (guild_id,))
                    if result and result[0]:
                        buff_until = datetime.fromisoformat(result[0])
                        timestamp = int(buff_until.timestamp())
                        embed.add_field(name="🌟 Buff Toàn Server", value=f"X2 hạt còn <t:{timestamp}:R>", inline=False)
                
                # Add contributor info
                current_season_contributors = await self.get_top_contributors(guild_id, 3)
                all_time_contributors = await self.get_top_contributors_all_time(guild_id, 3)
                
                # Get current season
                _, _, _, current_season, _, _ = await self.get_tree_data(guild_id)
                
                if current_season_contributors:
                    season_text = ""
                    for idx, (uid, amount_val, exp_val) in enumerate(current_season_contributors, 1):
                        try:
                            user = await self.bot.fetch_user(uid)
                            season_text += f"{idx}. **{user.name}** - {amount_val} Hạt\n"
                        except Exception as e:
                            season_text += f"{idx}. **User #{uid}** - {amount_val} Hạt\n"
                    
                    embed.add_field(name=f"🏆 Top 3 Người Góp mùa {current_season}", value=season_text, inline=False)
                
                if all_time_contributors:
                    all_time_text = ""
                    for idx, (uid, total_exp) in enumerate(all_time_contributors, 1):
                        try:
                            user = await self.bot.fetch_user(uid)
                            all_time_text += f"{idx}. **{user.name}** - {total_exp} Kinh Nghiệm\n"
                        except Exception as e:
                            all_time_text += f"{idx}. **User #{uid}** - {total_exp} Kinh Nghiệm\n"
                    
                    embed.add_field(name="🏆 Top 3 Người Góp toàn thời gian", value=all_time_text, inline=False)
                
                view = TreeContributeView(self)
                
                # Try to get existing tree message
                tree_message_id = None
                result = await db_manager.fetchone(
                    "SELECT tree_message_id FROM server_tree WHERE guild_id = ?",
                    (guild_id,)
                )
                tree_message_id = result[0] if result else None
                
                # Delete old message if exists
                if tree_message_id:
                    try:
                        old_message = await channel.fetch_message(tree_message_id)
                        await old_message.delete()
                        logger.info(f"[TREE] Deleted old tree message {tree_message_id} in {channel.name}")
                    except Exception as e:
                        logger.warning(f"[TREE] Could not delete old message: {e}")
                
                # Create new message (without pinning)
                new_message = await channel.send(embed=embed, view=view)
                
                # Store message ID in database
                await db_manager.modify(
                    "UPDATE server_tree SET tree_message_id = ? WHERE guild_id = ?",
                    (new_message.id, guild_id)
                )
                
                logger.info(f"[TREE] Created new tree message {new_message.id} in {channel.name}")
            
            except Exception as e:
                logger.error(f"[TREE] Error updating tree message: {e}", exc_info=True)

    async def process_contribution(self, interaction: discord.Interaction, amount: int):
        """Process seed contribution"""
        # Only defer if not already deferred (from modal it's already deferred)
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception as e:
                logger.error(f"[TREE] Error deferring response: {e}", exc_info=True)
                return
        
        try:
            user_id = interaction.user.id
            guild_id = interaction.guild.id
            
            # Check user balance
            from database_manager import get_user_balance
            current_balance = await get_user_balance(user_id)
            
            if current_balance < amount:
                await interaction.followup.send(
                    f"Bạn không đủ hạt!\nCần: {amount} | Hiện có: {current_balance}",
                    ephemeral=True
                )
                return
            
            balance_before = current_balance
            new_balance = balance_before - amount

            # Deduct seeds
            from database_manager import add_seeds
            await add_seeds(user_id, -amount)
            logger.info(
                f"[TREE] [CONTRIBUTE_DEBIT] user_id={user_id} seed_change=-{amount} "
                f"balance_before={balance_before} balance_after={new_balance}"
            )
            logger.info(
                f"[TREE] [CONTRIBUTE_DEBIT] user_id={user_id} seed_change=-{amount} "
                f"balance_before={balance_before} balance_after={new_balance}"
            )
            
            # Get current tree state
            lvl, prog, total, season, tree_channel_id, _ = await self.get_tree_data(guild_id)
            
            if lvl >= 6:
                # Refund and show message
                await interaction.followup.send(
                    "🍎 Cây đã chín rồi! Hãy bảo Admin dùng lệnh `/thuhoach`!",
                    ephemeral=True
                )
                await add_seeds(user_id, amount)
                logger.info(
                    f"[TREE] [REFUND] user_id={user_id} seed_change=+{amount} reason=tree_maxed"
                )
                return
            
            # Update tree progress
            level_reqs = self.get_level_reqs(season)
            req = level_reqs.get(lvl + 1, level_reqs[6])
            new_progress = prog + amount
            new_total = total + amount
            new_level = lvl
            leveled_up = False
            
            # Handle level ups (may level up multiple times if large amount)
            while new_progress >= req and new_level < 6:
                new_level += 1
                new_progress = new_progress - req
                leveled_up = True
                # Update req for next level
                req = level_reqs.get(new_level + 1, level_reqs[6])
            
            await self.update_tree_progress(guild_id, new_level, new_progress, new_total)
            await self.add_contributor(user_id, guild_id, amount, contribution_type="seeds")
            
            # Response embed - PUBLIC announcement
            embed = discord.Embed(
                title="Góp Hạt Thành Công!",
                color=discord.Color.green()
            )
            embed.add_field(name="Người góp", value=f"**{interaction.user.name}**", inline=False)
            embed.add_field(name="Hạt góp", value=f"**+{amount}**", inline=True)
            embed.add_field(name="Tiến độ", value=f"**{int((new_progress / req) * 100) if req > 0 else 0}%** ({new_progress}/{req})", inline=True)
            
            if leveled_up:
                embed.add_field(
                    name="CÂY ĐÃ LÊN CẤP!",
                    value=f"**{TREE_NAMES[new_level]}** - Cấp {new_level}/6",
                    inline=False
                )
                embed.color = discord.Color.gold()
            
            await interaction.followup.send(embed=embed, ephemeral=False)
            
            # Update pinned message
            if tree_channel_id:
                await self.update_or_create_pin_message(guild_id, tree_channel_id)
            
            logger.info(
                f"[TREE] [CONTRIBUTE] user_id={user_id} username={interaction.user.name} "
                f"seed_change=-{amount} balance_after={new_balance} tree_level={new_level} total_contrib={new_total}"
            )
        
        except Exception as e:
            logger.error(f"[TREE] Error in process_contribution: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"Có lỗi xảy ra: {str(e)}",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

    # ==================== COMMANDS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Update tree message when any message is sent in tree channel"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message is in a tree channel
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return
        
        try:
            # Get tree channel for this guild
            tree_data = await self.get_tree_data(guild_id)
            if not tree_data:
                return
            _, _, _, _, tree_channel_id, _ = tree_data
            
            if not tree_channel_id or message.channel.id != tree_channel_id:
                return
            if message.channel.id != tree_channel_id:
                return
            
            # Debounce: only update tree message every 5 seconds max per guild
            import time
            current_time = time.time()
            last_update = self.last_tree_update.get(guild_id, 0)
            
            if current_time - last_update < 5:
                return
            
            self.last_tree_update[guild_id] = current_time
            
            # Update tree message (delete old + create new)
            await self.update_or_create_pin_message(guild_id, tree_channel_id)
        
        except Exception as e:
            logger.error(f"[TREE] Error in on_message: {e}", exc_info=True)

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
                await interaction.followup.send("Số lượng không hợp lệ!", ephemeral=True)
                return
            
            await self.process_contribution(interaction, amount)

    @app_commands.command(name="cay", description="Xem trạng thái cây server")
    async def show_tree(self, interaction: discord.Interaction):
        """Show current tree status"""
        await interaction.response.defer(ephemeral=True)
        
        embed = await self.create_tree_embed(interaction.guild.id)
        
        # Add buff info if active
        if await self.is_harvest_buff_active(interaction.guild.id):
            result = await db_manager.fetchone("SELECT harvest_buff_until FROM server_config WHERE guild_id = ?", (interaction.guild.id,))
            if result and result[0]:
                buff_until = datetime.fromisoformat(result[0])
                timestamp = int(buff_until.timestamp())
                embed.add_field(name="🌟 Buff Toàn Server", value=f"X2 hạt còn <t:{timestamp}:R>", inline=False)
        
        # Add contributor info
        current_season_contributors = await self.get_top_contributors(interaction.guild.id, 3)
        all_time_contributors = await self.get_top_contributors_all_time(interaction.guild.id, 3)
        
        # Get current season
        _, _, _, current_season, _, _ = await self.get_tree_data(interaction.guild.id)
        
        if current_season_contributors:
            season_text = ""
            for idx, (uid, amount_val, exp_val) in enumerate(current_season_contributors, 1):
                try:
                    user = await self.bot.fetch_user(uid)
                    season_text += f"{idx}. **{user.name}** - {amount_val} Hạt\n"
                except Exception as e:
                    season_text += f"{idx}. **User #{uid}** - {amount_val} Hạt\n"
            
            embed.add_field(name=f"🏆 Top 3 Người Góp mùa {current_season}", value=season_text, inline=False)
        
        if all_time_contributors:
            all_time_text = ""
            for idx, (uid, total_exp) in enumerate(all_time_contributors, 1):
                try:
                    user = await self.bot.fetch_user(uid)
                    all_time_text += f"{idx}. **{user.name}** - {total_exp} Kinh Nghiệm\n"
                except Exception as e:
                    all_time_text += f"{idx}. **User #{uid}** - {total_exp} Kinh Nghiệm\n"
            
            embed.add_field(name="🏆 Top 3 Người Góp toàn thời gian", value=all_time_text, inline=False)
        
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
                f"Cây chưa chín! Hiện tại: Level {lvl}/6. Cần thêm {max_req - prog} Hạt.",
                ephemeral=True
            )
            return
        
        # === CLIMAX EVENT STARTS ===
        await interaction.followup.send("**ĐANG THU HOẠCH...** Xin chờ một chút! 🌟")
        
        # Get all contributors for current season
        all_contributors = await db_manager.execute(
            "SELECT user_id, contribution_exp FROM tree_contributors WHERE guild_id = ? AND season = ? ORDER BY contribution_exp DESC",
            (guild_id, season)
        )
        
        if not all_contributors:
            await interaction.followup.send("❌ Không có ai đóng góp trong mùa này!", ephemeral=True)
            return
        
        # Top contributor
        top1_user_id, top1_exp = all_contributors[0]
        top1_user_obj = None
        try:
            top1_user_obj = await self.bot.fetch_user(top1_user_id)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        # === DATABASE TRANSACTIONS ===
        from database_manager import batch_update_seeds, add_item, set_server_config
        
        # 1. REWARD ALL CONTRIBUTORS: seeds + memorabilia item
        memorabilia_key = f"qua_ngot_mua_{season}"
        contributor_rewards = []
        seed_updates = {}
        
        for idx, (cid, exp) in enumerate(all_contributors):
            # Calculate reward based on rank
            if idx == 0:  # Top 1
                reward_seeds = 10000
            elif idx == 1:  # Top 2
                reward_seeds = 5000
            elif idx == 2:  # Top 3
                reward_seeds = 3000
            else:  # Other contributors
                reward_seeds = 1500
            
            # Collect seed updates
            if cid in seed_updates:
                seed_updates[cid] += reward_seeds
            else:
                seed_updates[cid] = reward_seeds
            
            # Add memorabilia item
            await add_item(cid, memorabilia_key, 1)
            
            contributor_rewards.append((cid, exp, reward_seeds))
        
        # 2. BONUS FOR TOP CONTRIBUTOR: extra seeds (e.g., 3000 more)
        top1_bonus = 3000
        if top1_user_id in seed_updates:
            seed_updates[top1_user_id] += top1_bonus
        else:
            seed_updates[top1_user_id] = top1_bonus
        
        # Apply all seed updates
        await batch_update_seeds(seed_updates)
        
        # 3. ACTIVATE 24H BUFF
        from datetime import datetime, timedelta
        buff_until = datetime.now() + timedelta(hours=24)
        await set_server_config(guild_id, 'harvest_buff_until', buff_until.isoformat())
        
        # 4. RESET TREE FOR NEXT SEASON
        await db_manager.modify(
            "UPDATE server_tree SET current_level = 1, current_progress = 0, total_contributed = 0, season = season + 1, last_harvest = CURRENT_TIMESTAMP WHERE guild_id = ?",
            (guild_id,)
        )
        
        # === CREATE ROLE FOR TOP 1 ===
        role_mention = ""
        if top1_user_obj and interaction.guild:
            try:
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
                member = await interaction.guild.fetch_member(top1_user_id)
                if member:
                    await member.add_roles(role)
                    role_mention = f"Đã cấp role **{role_name}** cho **{top1_user_obj.name}** và thưởng tổng cộng 13000 hạt (10000 + 3000 bonus)!"
            except Exception as e:
                logger.error(f"[TREE] Error creating role: {e}", exc_info=True)
                role_mention = f"Không thể cấp role cho {top1_user_obj.name if top1_user_obj else f'User {top1_user_id}'}"
        
        # Create top contributors text
        top_contrib_text = "\n".join([
            f"**{self.bot.get_user(uid).name if self.bot.get_user(uid) else f'User #{uid}'}** - {exp} Kinh Nghiệm"
            for uid, exp in all_contributors[:3]
        ])
        
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
            value="**X2 Hạt** khi chat/voice\n**X2 Hạt** cho mọi activity",
            inline=False
        )
        
        # Field 2: Contributors Reward
        embed.add_field(
            name="🎁 PHẦN THƯỞNG CHO NGƯỜI ĐÓNG GÓP",
            value=f"• **Top 1**: 10000 Hạt + Quả Ngọt Mùa {season}\n"
                  f"• **Top 2**: 5000 Hạt + Quả Ngọt Mùa {season}\n"
                  f"• **Top 3**: 3000 Hạt + Quả Ngọt Mùa {season}\n"
                  f"• **Những người khác**: 1500 Hạt + Quả Ngọt Mùa {season}",
            inline=False
        )
        
        # Field 3: Top Contributors
        embed.add_field(
            name="🏆 Top 3 Người Đóng Góp Nhiều Nhất",
            value=top_contrib_text,
            inline=False
        )
        
        # Field 4: Season Reset
        embed.add_field(
            name="MÙA MỚI BẮT ĐẦU",
            value=f"Cây đã tái sinh Level 1\n"
                  f"Mùa {season + 1} chính thức khai mạc!\n"
                  f"Hãy chuẩn bị cho cuộc đua góp hạt mới",
            inline=False
        )
        
        embed.set_footer(text=f"Cảm ơn tất cả! 🙏 | Mùa tiếp theo sẽ còn huy hoàng hơn!")
        
        await interaction.followup.send(embed=embed)
        
        # === ROLE ANNOUNCEMENT ===
        if role_mention:
            await interaction.followup.send(f"🌟 {role_mention}")
        
        # === TAG EVERYONE ===
        try:
            announce_msg = (
                f"🎊 Yayyyy 🎊\n\n"
                f"**MÙA THU HOẠCH CÂY HIÊN NHÀ ĐÃ KẾT THÚC!**\n\n"
                f"Trong 24 giờ tới, mọi người sẽ nhận **X2 Hạt từ chat/voice**!\n"
                f"Hãy tranh thủ online để tối đa hóa lợi nhuận!\n\n"
                f"Chúc mừng những người đã đóng góp!"
            )
            await interaction.followup.send(announce_msg)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        logger.info(f"[TREE] HARVEST EVENT - Season {season} completed! Top1: {top1_user_id} ({top1_exp} exp), Contributors: {len(all_contributors)}")

async def setup(bot):
    await bot.add_cog(CommunityCog(bot))
